from dataclasses import dataclass

@dataclass
class ConveyorSpecs:
    """
    Physical specifications for roller conveyor systems.

    Defines operational limits for different roller conveyor models/configurations.
    Used by LinearActuator and other conveyor-based motion systems.

    Attributes:
        length_mm: Maximum travel distance (mm)
        max_speed_mm_sec: Maximum linear velocity (mm/s)
        accel_mm_sec2: Maximum acceleration/deceleration rate (mm/s²)
        max_load_kg: Maximum payload capacity (kg)
    """
    length_mm: float
    max_speed_mm_sec: float
    accel_mm_sec2: float
    max_load_kg: float