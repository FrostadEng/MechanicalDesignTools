"""
Manufacturing Process Physics.

Provides physics-based calculations for thermal material removal processes
including laser cutting, plasma cutting, and other manufacturing operations.

Modules:
    thermal_removal: Energy balance calculations for melting-based processes

Example Usage:
    >>> from engineering_tools.mech_core.analysis.manufacturing import calculate_melting_speed
    >>> from engineering_tools.mech_core.standards.materials.steel import get_material
    >>> from engineering_tools.mech_core.standards.units import ureg, Q_
    >>>
    >>> material = get_material("ASTM A36")
    >>> speed = calculate_melting_speed(
    ...     material, Q_(12, ureg.mm), Q_(4, ureg.kW),
    ...     Q_(1.5, ureg.mm), 0.35, 0.70
    ... )
"""

from .thermal_removal import (
    calculate_melting_speed,
    calculate_pierce_time,
    calculate_specific_removal_rate
)

__all__ = [
    'calculate_melting_speed',
    'calculate_pierce_time',
    'calculate_specific_removal_rate'
]
