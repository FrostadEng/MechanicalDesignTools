import simpy
from dataclasses import dataclass

@dataclass
class ConveyorSpecs:
    length_mm: float
    max_speed_mm_sec: float
    accel_mm_sec2: float
    max_load_kg: float

class RollerConveyor:
    def __init__(self, env: simpy.Environment, specs: ConveyorSpecs, name: str):
        self.env = env
        self.specs = specs
        self.name = name
        self.resource = simpy.Resource(env, capacity=1) # Only one beam at a time

    def transfer_time(self, distance_mm: float, beam_mass_kg: float) -> float:
        """
        Calculates time based on trapezoidal velocity profile.
        If beam is too heavy, we derate acceleration (physics!).
        """
        if beam_mass_kg > self.specs.max_load_kg:
            raise ValueError(f"Beam {beam_mass_kg}kg exceeds {self.name} rating!")

        # Dynamic Physics Check:
        # If beam is heavy, effective accel might drop due to motor torque limits
        effective_accel = self.specs.accel_mm_sec2
        if beam_mass_kg > (self.specs.max_load_kg * 0.5):
             # Simple derating curve
            effective_accel *= (self.specs.max_load_kg / beam_mass_kg) * 0.5

        # Kinematics: Time to reach max speed
        t_accel = self.specs.max_speed_mm_sec / effective_accel
        d_accel = 0.5 * effective_accel * (t_accel ** 2)

        if distance_mm < (2 * d_accel):
            # Triangle profile (never reach full speed)
            return 2 * (distance_mm / effective_accel)**0.5
        else:
            # Trapezoid profile
            d_cruise = distance_mm - (2 * d_accel)
            t_cruise = d_cruise / self.specs.max_speed_mm_sec
            return (2 * t_accel) + t_cruise