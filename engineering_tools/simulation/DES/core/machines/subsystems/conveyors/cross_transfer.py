import simpy
from dataclasses import dataclass
from ....logging.logger import EventLogger
from ......mech_core.standards.units import ureg

@dataclass
class CrossTransferSpecs:
    lift_capacity_per_unit_kg: float = 2000.0
    lift_time_sec: float = 2.0
    lower_time_sec: float = 2.0
    traverse_speed_mm_sec: float = 300.0
    traverse_dist_mm: float = 2500.0 # Distance from buffer to conveyor center

class CrossTransfer:
    def __init__(self, env: simpy.Environment, logger: EventLogger, specs: CrossTransferSpecs, num_units: int = 2):
        self.env = env
        self.logger = logger
        self.specs = specs
        self.num_units = num_units # Master + Slaves
        
        # Calculate Total System Capacity
        self.total_capacity_kg = specs.lift_capacity_per_unit_kg * num_units
        
        # Resource (Only one beam transfer at a time)
        self.resource = simpy.Resource(env, capacity=1)

    def load_beam(self, beam_mass_kg: float):
        """
        Executes the Load Cycle: Lift -> In -> Drop -> Out
        """
        with self.resource.request() as req:
            yield req
            
            # 1. Capacity Check (The Slave Logic)
            if beam_mass_kg > self.total_capacity_kg:
                # Log critical warning but proceed (or crash simulation)
                with self.logger.log_event("CRITICAL", "CrossTransfer", f"Overload! Beam {beam_mass_kg}kg > Capacity {self.total_capacity_kg}kg"):
                    # We add a penalty delay to simulate the hydraulics stalling/struggling
                    yield self.env.timeout(5.0)
            
            # 2. The Cycle
            with self.logger.log_event("Load Cycle", "CrossTransfer", f"Units: {self.num_units}") as cycle_id:
                
                # Lift
                with self.logger.log_event("Lift", "CrossTransfer", parent_id=cycle_id):
                    yield self.env.timeout(self.specs.lift_time_sec)

                # Traverse In (Trapezoidal simplified to constant speed for short travel)
                traverse_time = self.specs.traverse_dist_mm / self.specs.traverse_speed_mm_sec
                with self.logger.log_event("Traverse In", "CrossTransfer", parent_id=cycle_id):
                    yield self.env.timeout(traverse_time)

                # Lower (Place on Rollers)
                with self.logger.log_event("Lower", "CrossTransfer", parent_id=cycle_id):
                    yield self.env.timeout(self.specs.lower_time_sec)

                # Return Home (Empty)
                with self.logger.log_event("Retract", "CrossTransfer", parent_id=cycle_id):
                    yield self.env.timeout(traverse_time)