"""
Thermal Material Removal Physics for Manufacturing Processes.

Calculates cutting speeds and pierce times based on energy balance
between tool power and material enthalpy requirements.

This module provides stateless functions for thermal process calculations,
extracted from tool-specific implementations to enable reuse across
laser, plasma, waterjet, and other thermal cutting technologies.

Example Usage:
    >>> from engineering_tools.mech_core.standards.materials.steel import get_material
    >>> from engineering_tools.mech_core.standards.units import ureg, Q_
    >>>
    >>> material = get_material("ASTM A36")
    >>> speed = calculate_melting_speed(
    ...     material=material,
    ...     thickness=Q_(12.0, ureg.mm),
    ...     tool_power=Q_(4.0, ureg.kW),
    ...     kerf_width=Q_(1.5, ureg.mm),
    ...     efficiency=0.35,
    ...     absorptivity=0.70
    ... )
    >>> print(f"Cutting speed: {speed.to(ureg.mm/ureg.s):.2f}")
"""

from ...standards.units import ureg, Q_
from ...standards.materials.steel import StructuralMaterial
from ..heat_transfer.phase_change import (
    specific_melting_energy_volumetric,
    calculate_melting_energy
)
from typing import Optional


def calculate_melting_speed(
    material: StructuralMaterial,
    thickness: Q_,
    tool_power: Q_,
    kerf_width: Q_,
    efficiency: float = 1.0,
    absorptivity: float = 1.0,
    t_ambient: Optional[Q_] = None
) -> Q_:
    """
    Calculate linear cutting speed from thermal energy balance.

    Physics Model:
        Speed = Effective_Power / (Energy_Density × Cross_Section_Area)

        Where:
        - Effective_Power = Power × Efficiency × Absorptivity
        - Energy_Density = specific_melting_energy_volumetric(material)
        - Area = Thickness × Kerf_Width

    The energy balance ensures that the power delivered to the material
    (after accounting for process efficiency and surface absorption) is
    sufficient to melt the material at the calculated speed.

    Args:
        material: StructuralMaterial with thermal properties (melting point,
                 specific heat, latent heat of fusion, density)
        thickness: Material thickness (with units, e.g., Q_(12, ureg.mm))
        tool_power: Tool power output (with units, e.g., Q_(4.0, ureg.kW))
        kerf_width: Width of cut (with units, e.g., Q_(1.5, ureg.mm))
        efficiency: Process efficiency (0.0-1.0), optical to thermal conversion
                   - Fiber laser: ~0.35 (35% optical to thermal)
                   - Plasma: ~0.55 (55% electrical to thermal)
                   Default: 1.0 (no loss)
        absorptivity: Surface absorption coefficient (0.0-1.0)
                     - Mill scale: ~0.70
                     - Blast cleaned: ~0.45
                     - Plasma (irrelevant): 1.0
                     Default: 1.0 (full absorption)
        t_ambient: Ambient temperature (defaults to 20°C if not specified)

    Returns:
        Linear cutting speed (Q_ with velocity units, e.g., mm/s)

    Raises:
        ValueError: If thickness, power, or kerf is zero/negative
        ValueError: If efficiency or absorptivity outside [0, 1]

    Example:
        >>> material = get_material("ASTM A36")
        >>> speed = calculate_melting_speed(
        ...     material=material,
        ...     thickness=Q_(12.0, ureg.mm),
        ...     tool_power=Q_(4.0, ureg.kW),
        ...     kerf_width=Q_(1.5, ureg.mm),
        ...     efficiency=0.35,
        ...     absorptivity=0.70
        ... )
        >>> speed.to(ureg.mm / ureg.second)
        <Quantity(7.2, 'millimeter / second')>
    """
    # Input validation
    if thickness.magnitude <= 0:
        raise ValueError("Thickness must be positive")
    if tool_power.magnitude <= 0:
        raise ValueError("Tool power must be positive")
    if kerf_width.magnitude <= 0:
        raise ValueError("Kerf width must be positive")
    if not 0 <= efficiency <= 1:
        raise ValueError("Efficiency must be between 0 and 1")
    if not 0 <= absorptivity <= 1:
        raise ValueError("Absorptivity must be between 0 and 1")

    # Get volumetric enthalpy (energy to melt per unit volume)
    # Returns J/m³ from phase_change module
    energy_density = specific_melting_energy_volumetric(material, t_ambient)

    # Calculate effective power accounting for process efficiency and surface absorption
    effective_power = tool_power * efficiency * absorptivity

    # Calculate cross-sectional area of kerf (material removal area)
    area = thickness * kerf_width

    # Calculate linear cutting speed using energy balance
    # Speed = Power / (Energy_Density × Area)
    # This gives the speed at which material can be continuously removed
    speed = effective_power / (energy_density * area)

    return speed


def calculate_pierce_time(
    material: StructuralMaterial,
    mass: Q_,
    tool_power: Q_,
    efficiency: float = 1.0,
    absorptivity: float = 1.0,
    t_ambient: Optional[Q_] = None
) -> Q_:
    """
    Calculate time to melt a given mass of material (pierce operation).

    Physics Model:
        Time = Energy_Required / Effective_Power

        Where:
        - Energy_Required = calculate_melting_energy(material, mass)
                          = m × [Cp × (Tm - T_amb) + Lf]
        - Effective_Power = Power × Efficiency × Absorptivity

    This function is useful for pierce operations where the laser or plasma
    torch must create an initial hole before beginning a cut. The pierce
    involves melting through the full thickness at a single point.

    Args:
        material: StructuralMaterial with thermal properties
        mass: Mass to melt (with units, e.g., Q_(0.01, ureg.kg))
        tool_power: Tool power output (with units)
        efficiency: Process efficiency (0.0-1.0)
        absorptivity: Surface absorption coefficient (0.0-1.0)
        t_ambient: Ambient temperature (defaults to 20°C)

    Returns:
        Time to melt (Q_ with time units, e.g., seconds)

    Raises:
        ValueError: If mass or power is zero/negative
        ValueError: If efficiency or absorptivity outside [0, 1]

    Example:
        >>> material = get_material("ASTM A36")
        >>> pierce_time = calculate_pierce_time(
        ...     material=material,
        ...     mass=Q_(0.01, ureg.kg),  # 10 grams
        ...     tool_power=Q_(4.0, ureg.kW),
        ...     efficiency=0.35,
        ...     absorptivity=0.70
        ... )
        >>> pierce_time.to(ureg.second)
        <Quantity(8.2, 'second')>
    """
    # Input validation
    if mass.magnitude <= 0:
        raise ValueError("Mass must be positive")
    if tool_power.magnitude <= 0:
        raise ValueError("Tool power must be positive")
    if not 0 <= efficiency <= 1:
        raise ValueError("Efficiency must be between 0 and 1")
    if not 0 <= absorptivity <= 1:
        raise ValueError("Absorptivity must be between 0 and 1")

    # Calculate total energy required to melt this mass
    # Uses existing phase_change.calculate_melting_energy function
    # which computes: Q = m × [Cp × (Tm - T_amb) + Lf]
    energy_required = calculate_melting_energy(material, mass, t_ambient)

    # Calculate effective power delivered to material
    effective_power = tool_power * efficiency * absorptivity

    # Calculate time using energy / power
    time = energy_required / effective_power

    return time


def calculate_specific_removal_rate(
    material: StructuralMaterial,
    tool_power: Q_,
    efficiency: float = 1.0,
    absorptivity: float = 1.0,
    t_ambient: Optional[Q_] = None
) -> Q_:
    """
    Calculate volumetric material removal rate per unit power.

    Physics Model:
        Removal_Rate = Effective_Power / Energy_Density

    This metric is useful for comparing process efficiency across different
    materials and tool configurations. Higher removal rate = more efficient.

    Args:
        material: StructuralMaterial with thermal properties
        tool_power: Tool power output (with units)
        efficiency: Process efficiency (0.0-1.0)
        absorptivity: Surface absorption coefficient (0.0-1.0)
        t_ambient: Ambient temperature (defaults to 20°C)

    Returns:
        Volumetric removal rate (Q_ with volume/time units, e.g., mm³/s)

    Example:
        >>> material = get_material("ASTM A36")
        >>> rate = calculate_specific_removal_rate(
        ...     material=material,
        ...     tool_power=Q_(4.0, ureg.kW),
        ...     efficiency=0.35,
        ...     absorptivity=0.70
        ... )
        >>> rate.to(ureg.mm**3 / ureg.second)
        <Quantity(95.2, 'millimeter ** 3 / second')>
    """
    # Input validation
    if tool_power.magnitude <= 0:
        raise ValueError("Tool power must be positive")
    if not 0 <= efficiency <= 1:
        raise ValueError("Efficiency must be between 0 and 1")
    if not 0 <= absorptivity <= 1:
        raise ValueError("Absorptivity must be between 0 and 1")

    # Get volumetric enthalpy
    energy_density = specific_melting_energy_volumetric(material, t_ambient)

    # Calculate effective power
    effective_power = tool_power * efficiency * absorptivity

    # Calculate volumetric removal rate
    removal_rate = effective_power / energy_density

    return removal_rate
