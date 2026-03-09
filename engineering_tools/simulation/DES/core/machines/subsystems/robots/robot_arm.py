import simpy
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

# Shared Imports
from ....logging.logger import EventLogger
from ......mech_core.standards.units import ureg
from ......mech_core.analysis.kinematics import velocity_profile_trapezoidal, distance_3d

# Type Checking Imports to prevent circular dependency errors at runtime
if TYPE_CHECKING:
    from ..eoa_tools.base import ManufacturingTool
    from ..planning.parsers.dstv import DSTVFeature
    from ....entities.beam import BeamEntity

@dataclass
class RobotState:
    x: float
    y: float
    z: float

class RobotArm:
    def __init__(self, env: simpy.Environment, logger: EventLogger, config_file: str = "fanuc.json"):
        self.env = env
        self.logger = logger
        
        # 1. Load Configuration
        # resolved path: .../robots/configs/fanuc.json
        config_path = Path(__file__).parent / "configs" / config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Robot config not found: {config_path}")
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # 2. Parse Kinematics Limits
        self.model_name = self.config['model']
        self.max_payload = self.config['max_payload_kg']
        
        # Base Kinematics (Unloaded)
        kin = self.config['kinematics']
        self.base_rapid_v = kin['linear_speed_rapid_mm_s']
        self.base_accel = kin['linear_accel_mm_s2']
        self.derating_factor = kin['accel_derating_factor']
        
        # Current Physics State (starts unloaded)
        self.current_accel = self.base_accel
        
        # Position State (Starts at "Home" high above the conveyor)
        self.pos = RobotState(x=0.0, y=500.0, z=500.0)
        
        # SimPy Resource (The Robot can only do one thing at a time)
        self.resource = simpy.Resource(env, capacity=1)

    def mount_tool(self, tool: 'ManufacturingTool'):
        """
        Called by the Tool when it starts an operation.
        Updates the robot's physics based on the tool's mass.
        """
        if tool.mass_kg > self.max_payload:
            # In simulation, we warn but allow. In reality, this trips an alarm.
            self.logger.log_event("WARNING", self.model_name, f"Tool Overload: {tool.mass_kg}kg > {self.max_payload}kg")
            
        # Calculate Physics Derating
        # Formula: New_Accel = Base_Accel * (1 - (Load_Ratio * Derating_Factor))
        load_ratio = min(tool.mass_kg / self.max_payload, 1.0)
        penalty = load_ratio * self.derating_factor
        
        self.current_accel = self.base_accel * (1.0 - penalty)
        
        # Optional: Log the physics update if you want deep debugging
        # self.logger.log_event("Physics Update", self.model_name, f"Accel derated to {self.current_accel:.0f} mm/s²")

    def execute_features(self, features: List['DSTVFeature'], tool: 'ManufacturingTool', beam_entity: 'BeamEntity'):
        """
        Main entry point for the Controller.
        The Controller says: "Here is a list of holes, and here is the tool to use."
        The Robot says: "Okay, I will let the Tool drive."
        """
        with self.resource.request() as req:
            yield req
            
            # Mount the tool (Physically update mass properties)
            self.mount_tool(tool)
            
            # Simple sorting optimization (Minimize air travel)
            sorted_features = sorted(features, key=lambda f: (f.x_pos, f.y_pos))
            
            for feat in sorted_features:
                # INVERSION OF CONTROL:
                # The Robot hands itself over to the Tool.
                # The Tool calculates speeds, sequences (IHS, Pierce), and commands moves.
                yield from tool.process_feature(self.env, self, feat, beam_entity)

    # ==========================================
    # MOTION PRIMITIVES (The API used by Tools)
    # ==========================================

    def move_rapid(self, target_x: float, target_y: float, target_z: float):
        """
        High-speed move using Trapezoidal Kinematics and Dynamic Acceleration.
        Used for air-moves between cuts.
        """
        # 1. Calculate Distance
        p1 = [self.pos.x * ureg.mm, self.pos.y * ureg.mm, self.pos.z * ureg.mm]
        p2 = [target_x * ureg.mm, target_y * ureg.mm, target_z * ureg.mm]
        
        dist_obj = distance_3d(p1, p2)
        dist_mm = dist_obj.to(ureg.mm).magnitude
        
        # Tolerance check
        if dist_mm < 1.0:
            return

        # 2. Calculate Profile (Using payload-derated acceleration)
        times, _, _ = velocity_profile_trapezoidal(
            total_distance=dist_obj,
            max_velocity=self.base_rapid_v * ureg.mm/ureg.s,
            acceleration=self.current_accel * ureg.mm/ureg.s**2
        )
        duration = times[-1].to(ureg.second).magnitude
        
        # 3. Log and Wait
        with self.logger.log_event("Rapid", self.model_name, f"Dist: {dist_mm:.0f}mm"):
            yield self.env.timeout(duration)
            
        # 4. Update State
        self.pos = RobotState(target_x, target_y, target_z)

    def move_linear(self, target_x: float, target_y: float, target_z: float, speed_mm_s: float):
        """
        Controlled velocity move (Straight Line).
        Used for IHS approach, probing, or precise positioning.
        """
        # Euclidean distance
        dx = target_x - self.pos.x
        dy = target_y - self.pos.y
        dz = target_z - self.pos.z
        dist_mm = (dx**2 + dy**2 + dz**2)**0.5
        
        if dist_mm < 0.1: return

        duration = dist_mm / speed_mm_s
        
        # No specific log event here because usually the Tool wraps this in "IHS" or "Pierce" log
        yield self.env.timeout(duration)
        
        self.pos = RobotState(target_x, target_y, target_z)

    def move_path(self, distance_mm: float, speed_mm_s: float):
        """
        Process move along a contour.
        Does not update X/Y/Z state because the path shape is complex (circles/slots).
        We just simulate the time it takes to trace the path.
        """
        duration = distance_mm / speed_mm_s
        yield self.env.timeout(duration)