import simpy
from ....logging.logger import EventLogger
from ..tooling.clamp import Clamp
from .conveyor import ConveyorSpecs
from ......mech_core.standards.units import ureg
from ......mech_core.analysis.kinematics import velocity_profile_trapezoidal


class LinearActuator:
    def __init__(self, env: simpy.Environment, logger: EventLogger, specs: ConveyorSpecs, name: str = "PushRod"):
        self.env = env
        self.logger = logger
        self.specs = specs
        self.name = name
        
        # State
        self.current_position = 0.0
        
        # Sub-components
        # We assume the Clamp is attached to this feeder
        self.clamp = Clamp(env, logger, clamp_time=1.5, name=f"{name}_Gripper")
        
        # Resources
        # This ensures we don't try to move to two places at once
        self.axis_resource = simpy.Resource(env, capacity=1)

    def move_to_position(self, target_position_mm: float, beam_mass_kg: float):
        """
        Moves the linear axis to an absolute position using trapezoidal kinematics.
        """
        with self.axis_resource.request() as req:
            yield req
            
            # Safety Check: Can't push a heavy beam if we aren't holding it!
            # (In reality, you might move the gripper empty (unclamped) OR move beam (clamped).
            #  For this v1, we assume we are moving the beam.)
            self.clamp.check_clamped(require_clamped=True)

            dist = abs(target_position_mm - self.current_position)
            
            if dist < 1.0: # Tolerance check
                return

            # PHYSICS CHECK: Dynamic Load Rating
            if beam_mass_kg > self.specs.max_load_kg:
                # Log a warning event but proceed (or raise error)
                with self.logger.log_event("WARNING", self.name, f"Overload: {beam_mass_kg}kg > {self.specs.max_load_kg}kg"):
                    pass
            
            # 1. KINEMATICS CALCULATION (Using your new mech_core API)
            # We generate the profile to find the total time.
            times, _, _ = velocity_profile_trapezoidal(
                total_distance=dist * ureg.mm,
                max_velocity=self.specs.max_speed_mm_sec * ureg.mm/ureg.s,
                acceleration=self.specs.accel_mm_sec2 * ureg.mm/ureg.s**2
            )
            
            # Get last timestamp (total duration)
            duration_sec = times[-1].to(ureg.second).magnitude
            
            # 2. SIMULATION
            with self.logger.log_event("Index", self.name, f"To {target_position_mm}mm"):
                yield self.env.timeout(duration_sec)
            
            # 3. STATE UPDATE
            self.current_position = target_position_mm