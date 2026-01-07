import simpy

# 1. Local Modules (The Brains)
from .indexer import Indexer, MachineCycle
from .config import (
    WINDOW_WIDTH, CLAMP_OVERLAP, TRANSITION_COSTS,
    DEFAULT_MATERIAL, DEFAULT_KERF_MM, DEFAULT_PROCESS_EFFICIENCY,
    ROBOT_SAFE_Z
)

# 2. Shared Subsystems (The Hardware)
# Note the relative imports to jump up to the sibling 'subsystems' directory
from ..subsystems.conveyors.push_rod_feeder import LinearActuator
from ..subsystems.eoa_tools.fiber_laser import FiberLaser, ProcessEnergyCalculator
from ..subsystems.robots.robot_arm import RobotArm
from ..subsystems.logic.safety_plc import SafetyPLC

# 3. Core Utilities
from ...logging.logger import EventLogger
from ..subsystems.planning.parsers.dstv import DSTVData

class PCR41_Controller:
    """
    PCR41 Machine Controller with Safety Interlocks and Physics-Based Processing.

    Orchestrates Robot, Feeder, and Tool subsystems with:
    - SafetyPLC event-based handshaking
    - ProcessEnergyCalculator for material-aware cutting speeds
    - Face-to-face transition penalties
    - Sliding window indexing with bisection logic
    """

    def __init__(self, env: simpy.Environment, logger: EventLogger):
        """
        Initialize the PCR41 controller and all subsystems.

        Args:
            env: SimPy environment for discrete event simulation
            logger: Event logger for tracking machine operations
        """
        self.env = env
        self.logger = logger

        # Instantiate Hardware
        self.feeder = LinearActuator(env, logger, name="PushRodFeeder")
        self.robot = RobotArm(env, logger)  # Loads fanuc.json automatically
        self.tool = FiberLaser()

        # Instantiate Logic
        self.indexer = Indexer(window_width=WINDOW_WIDTH, overlap=CLAMP_OVERLAP)
        self.plc = SafetyPLC(env, logger)

        # State tracking
        self.current_face = "v"  # Track last processed face for transition penalties

    def run_production(self, beam_dstv: DSTVData):
        """
        Main production loop with SafetyPLC integration and physics-based speeds.

        Args:
            beam_dstv: Parsed DSTV data containing beam geometry and features

        Yields:
            SimPy events for discrete event simulation
        """
        # 1. Plan the beam using sliding window algorithm
        cycles = self.indexer.plan_beam(beam_dstv)

        with self.logger.log_event("Production", "PCR41", f"Beam {beam_dstv.filename}"):
            # 2. Execute cycles
            for cycle in cycles:
                if cycle.type == "INDEX":
                    yield from self._execute_index(cycle, beam_dstv)

                elif cycle.type == "PROCESS":
                    yield from self._execute_process(cycle, beam_dstv)

                elif cycle.type == "SEVER":
                    yield from self._execute_sever(cycle, beam_dstv)

    def _execute_index(self, cycle: MachineCycle, beam_dstv: DSTVData):
        """
        Execute feeder indexing with PLC handshake.

        Args:
            cycle: INDEX cycle with target position
            beam_dstv: Beam data for mass calculation

        Yields:
            SimPy events for feeder motion
        """
        # Request permission from PLC
        yield from self.plc.request_feeder_move()

        # Calculate beam mass for physics (placeholder until BeamEntity implemented)
        beam_mass_kg = 50.0  # TODO: Get from beam_dstv.get_mass()

        # Execute motion
        with self.logger.log_event("Index", "Feeder", f"To {cycle.target_position:.0f}mm"):
            yield from self.feeder.move_to_position(cycle.target_position, beam_mass_kg)

        # Release PLC
        self.plc.release_feeder_move()

    def _execute_process(self, cycle: MachineCycle, beam_dstv: DSTVData):
        """
        Execute feature processing with dynamic speeds and face transitions.

        Args:
            cycle: PROCESS cycle with features to process
            beam_dstv: Beam data for material and geometry

        Yields:
            SimPy events for robot motion and processing
        """
        if not cycle.features:
            return

        # Request permission from PLC
        yield from self.plc.request_robot_entry()

        # Group features by face to minimize transitions
        features_by_face = {}
        for feat in cycle.features:
            features_by_face.setdefault(feat.face, []).append(feat)

        # Process each face
        for face, features in features_by_face.items():
            # Calculate transition penalty
            transition_time = TRANSITION_COSTS[self.current_face][face]

            if transition_time > 0:
                with self.logger.log_event(
                    "Transition", "Robot",
                    f"{self.current_face}->{face} ({transition_time:.1f}s)"
                ):
                    yield self.env.timeout(transition_time)

            self.current_face = face

            # Process each feature
            for feat in features:
                # Calculate cutting speed using physics-based energy calculator
                # Use material and thickness from DSTV data
                material_name = beam_dstv.material_grade or DEFAULT_MATERIAL

                # Estimate thickness based on face (simplified until BeamEntity implemented)
                # For structural beams: web ~= profile_height/40, flange ~= profile_height/20
                if face == "v" or face == "h":  # Web faces
                    thickness_mm = 10.0  # Conservative web thickness
                else:  # Flange faces (o, u)
                    thickness_mm = 15.0  # Conservative flange thickness

                cutting_speed = self.tool.energy_calc.calculate_cutting_speed(
                    material_name=material_name,
                    thickness_mm=thickness_mm,
                    tool_power_kw=self.tool.power_kw,
                    kerf_width_mm=self.tool.kerf_width_mm
                )

                # Execute robot motion (simplified - actual motion is more complex)
                # Move to feature location
                yield from self.robot.move_rapid(feat.x_pos, feat.y_pos, 100.0)

                # Cut the feature
                cut_time = feat.path_length / cutting_speed if cutting_speed > 0 else 0
                with self.logger.log_event(
                    "Cut", "Robot",
                    f"{feat.feature_type} {face} {thickness_mm:.0f}mm @ {cutting_speed:.1f}mm/s"
                ):
                    yield self.env.timeout(cut_time)

        # Return to safe position
        yield from self.robot.move_rapid(0.0, 0.0, ROBOT_SAFE_Z)

        # Release PLC
        self.plc.release_robot_entry()

    def _execute_sever(self, cycle: MachineCycle, beam_dstv: DSTVData):
        """
        Execute sever operation (vertical chop to bisect spanning feature).

        Args:
            cycle: SEVER cycle with chop length
            beam_dstv: Beam data for material

        Yields:
            SimPy events for robot sever motion
        """
        # Sever is a robot operation, requires PLC permission
        yield from self.plc.request_robot_entry()

        # Calculate sever speed using physics (severing through web)
        material_name = beam_dstv.material_grade or DEFAULT_MATERIAL
        web_thickness_mm = 10.0  # Conservative web thickness

        cutting_speed = self.tool.energy_calc.calculate_cutting_speed(
            material_name=material_name,
            thickness_mm=web_thickness_mm,
            tool_power_kw=self.tool.power_kw,
            kerf_width_mm=self.tool.kerf_width_mm
        )

        # Execute vertical cut
        sever_time = cycle.sever_length / cutting_speed if cutting_speed > 0 else 0
        with self.logger.log_event(
            "Sever", "Robot",
            f"{cycle.sever_length:.0f}mm @ {cutting_speed:.1f}mm/s"
        ):
            yield self.env.timeout(sever_time)

        # Return to safe position
        yield from self.robot.move_rapid(0.0, 0.0, ROBOT_SAFE_Z)

        # Release PLC
        self.plc.release_robot_entry()