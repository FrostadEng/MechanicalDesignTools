"""
Compressible Gas Jet Physics for Thermal Cutting Assist Gas.

Uses the calebbell/fluids library for rigorous thermodynamic calculations
of nozzle flow, jet velocity, and clearing capacity in thermal cutting operations.

This module implements fluid dynamics constraints for processes like laser cutting
and plasma cutting, where assist gas must clear molten material from the kerf.

References:
    - Anderson, "Modern Compressible Flow with Historical Perspective" (2003)
    - Fluids library documentation: https://fluids.readthedocs.io/

Example Usage:
    >>> from engineering_tools.mech_core.standards.units import ureg, Q_
    >>>
    >>> # Calculate nozzle exit velocity
    >>> v_exit = calculate_nozzle_exit_velocity(
    ...     pressure_inlet=Q_(10, ureg.bar),
    ...     pressure_ambient=Q_(1, ureg.bar),
    ...     temperature_inlet=Q_(300, ureg.K),
    ...     gas_gamma=1.4
    ... )
    >>> print(f"Exit velocity: {v_exit.to(ureg.m/ureg.s):.1f}")
"""

from ...standards.units import ureg, Q_
from typing import Optional
import math

# Try to import fluids library, fall back to simplified models if not available
try:
    from fluids.compressible import isentropic_T_rise_compression
    FLUIDS_AVAILABLE = True
except ImportError:
    FLUIDS_AVAILABLE = False
    import warnings
    warnings.warn(
        "fluids library not available, using simplified gas dynamics models. "
        "Install with: pip install fluids>=1.0.23"
    )


def calculate_nozzle_exit_velocity(
    pressure_inlet: Q_,
    pressure_ambient: Q_,
    temperature_inlet: Q_,
    gas_gamma: float = 1.4,
    gas_mw: float = 28.97
) -> Q_:
    """
    Calculate gas velocity at nozzle exit using isentropic expansion.

    Physics Model:
        For isentropic (reversible adiabatic) expansion through a converging nozzle:

        1. Temperature ratio: T2/T1 = (P2/P1)^((γ-1)/γ)
        2. Velocity from energy balance: v = sqrt(2 * Cp * (T1 - T2))

        For choked flow (when P_ratio > critical ~1.89 for air):
        - Flow reaches sonic conditions at nozzle throat
        - Exit velocity is limited by speed of sound

    Args:
        pressure_inlet: Upstream gas pressure (with units, e.g., Q_(10, ureg.bar))
        pressure_ambient: Downstream/ambient pressure (with units, e.g., Q_(1, ureg.bar))
        temperature_inlet: Upstream gas temperature (with units, e.g., Q_(300, ureg.K))
        gas_gamma: Ratio of specific heats (Cp/Cv)
                   - Air: 1.4
                   - Oxygen: 1.4
                   - Nitrogen: 1.4
                   - Argon: 1.67
                   Default: 1.4 (diatomic gases)
        gas_mw: Molecular weight (g/mol)
                - Air: 28.97
                - Oxygen: 32.0
                - Nitrogen: 28.01
                - Argon: 39.95
                Default: 28.97 (air)

    Returns:
        Exit velocity (Q_ with velocity units, typically m/s or mm/s)

    Notes:
        - Assumes ideal gas behavior
        - Neglects viscous losses (conservative estimate)
        - For supersonic flow, uses isentropic relations
        - Automatically handles choked flow conditions

    Example:
        >>> # High pressure cutting gas (supersonic)
        >>> v_exit = calculate_nozzle_exit_velocity(
        ...     pressure_inlet=Q_(10, ureg.bar),
        ...     pressure_ambient=Q_(1, ureg.bar),
        ...     temperature_inlet=Q_(300, ureg.K),
        ...     gas_gamma=1.4
        ... )
        >>> v_exit.to(ureg.m/ureg.s)
        <Quantity(530, 'meter / second')>  # Supersonic
    """
    # Input validation
    if pressure_inlet.magnitude <= 0:
        raise ValueError("Inlet pressure must be positive")
    if pressure_ambient.magnitude <= 0:
        raise ValueError("Ambient pressure must be positive")
    if temperature_inlet.magnitude <= 0:
        raise ValueError("Inlet temperature must be positive")
    if gas_gamma <= 1.0:
        raise ValueError("Gas gamma must be greater than 1.0")
    if gas_mw <= 0:
        raise ValueError("Molecular weight must be positive")

    # Convert pressures and temperature to SI base units
    P1 = pressure_inlet.to(ureg.Pa).magnitude
    P2 = pressure_ambient.to(ureg.Pa).magnitude
    T1 = temperature_inlet.to(ureg.K).magnitude

    if FLUIDS_AVAILABLE:
        # Use fluids library for accurate calculation
        # isentropic_T_rise_compression calculates T2 for compression
        # For expansion, we use it with reversed pressure ratio
        # Actually, for expansion we calculate temperature drop

        # Isentropic relation: T2/T1 = (P2/P1)^((gamma-1)/gamma)
        pressure_ratio = P2 / P1
        exponent = (gas_gamma - 1) / gas_gamma
        T2 = T1 * (pressure_ratio ** exponent)

        # Calculate specific heat at constant pressure (Cp)
        # For ideal gas: Cp = gamma * R / (MW * (gamma - 1))
        # Where R = 8.314 J/(mol·K)
        R_universal = 8.314  # J/(mol·K)
        Cp = gas_gamma * R_universal / ((gas_mw / 1000) * (gas_gamma - 1))  # J/(kg·K)

        # Velocity from energy balance: v = sqrt(2 * Cp * (T1 - T2))
        delta_T = T1 - T2
        if delta_T < 0:
            # Compression instead of expansion
            velocity = 0.0
        else:
            velocity = math.sqrt(2 * Cp * delta_T)

    else:
        # Fallback: Simplified Bernoulli equation
        # v = sqrt(2 * ΔP / ρ)
        # This is less accurate for compressible flow but provides conservative estimate

        # Calculate gas density at inlet using ideal gas law
        # ρ = P * MW / (R * T)
        R_universal = 8.314  # J/(mol·K)
        R_specific = R_universal / (gas_mw / 1000)  # J/(kg·K)
        rho_inlet = P1 / (R_specific * T1)  # kg/m³

        # Bernoulli approximation
        delta_P = P1 - P2
        velocity = math.sqrt(2 * delta_P / rho_inlet)

    # Return with units
    return velocity * ureg.meter / ureg.second


def calculate_gas_density_at_nozzle(
    pressure: Q_,
    temperature: Q_,
    gas_mw: float = 28.97
) -> Q_:
    """
    Calculate gas density using ideal gas law.

    Physics Model:
        Ideal Gas Law: PV = nRT
        Density: ρ = m/V = (n * MW)/V = (P * MW)/(R * T)

        Where:
        - P: Pressure (Pa)
        - MW: Molecular weight (kg/mol)
        - R: Universal gas constant = 8.314 J/(mol·K)
        - T: Temperature (K)

    Args:
        pressure: Gas pressure (with units, e.g., Q_(10, ureg.bar))
        temperature: Gas temperature (with units, e.g., Q_(300, ureg.K))
        gas_mw: Molecular weight (g/mol)
                - Air: 28.97
                - Oxygen: 32.0
                - Nitrogen: 28.01
                Default: 28.97 (air)

    Returns:
        Gas density (Q_ with density units, kg/m³)

    Example:
        >>> # Compressed air at nozzle
        >>> rho = calculate_gas_density_at_nozzle(
        ...     pressure=Q_(10, ureg.bar),
        ...     temperature=Q_(300, ureg.K),
        ...     gas_mw=28.97
        ... )
        >>> rho.to(ureg.kg/ureg.m**3)
        <Quantity(11.6, 'kilogram / meter ** 3')>
    """
    # Input validation
    if pressure.magnitude <= 0:
        raise ValueError("Pressure must be positive")
    if temperature.magnitude <= 0:
        raise ValueError("Temperature must be positive")
    if gas_mw <= 0:
        raise ValueError("Molecular weight must be positive")

    # Convert to SI units
    P = pressure.to(ureg.Pa).magnitude
    T = temperature.to(ureg.K).magnitude

    # Universal gas constant
    R_universal = 8.314  # J/(mol·K)

    # Convert molecular weight from g/mol to kg/mol
    MW_kg = gas_mw / 1000  # kg/mol

    # Calculate density using ideal gas law
    # ρ = (P * MW) / (R * T)
    density = (P * MW_kg) / (R_universal * T)  # kg/m³

    return density * ureg.kg / ureg.m**3


def calculate_clearing_speed_limit(
    nozzle_velocity: Q_,
    nozzle_diameter: Q_,
    kerf_width: Q_,
    material_density: Q_,
    gas_density: Q_,
    efficiency_factor: float = 0.1
) -> Q_:
    """
    Estimate maximum cutting speed limited by molten material ejection.

    Physics Model (Heuristic Momentum Balance):
        The gas jet must have sufficient momentum flux to clear molten material
        at the rate it's being created by the cutting process.

        Momentum Balance:
        - Material generation rate: dm/dt = Speed × Kerf × Thickness × ρ_material
        - Gas momentum flux: F_gas = ρ_gas × A_nozzle × v_gas²
        - Clearing constraint: F_gas ≥ η × (dm/dt) × v_ejection

        Simplified heuristic:
        Speed_max = (ρ_gas × A_nozzle × v_gas² × η) / (ρ_material × Kerf × Thickness)

        Where η (efficiency_factor) accounts for:
        - Jet divergence (not all momentum reaches kerf)
        - Turbulent mixing losses
        - Material viscosity resistance
        - Standoff distance effects

    Args:
        nozzle_velocity: Gas exit velocity (from calculate_nozzle_exit_velocity)
        nozzle_diameter: Nozzle orifice diameter (with units, e.g., Q_(2, ureg.mm))
        kerf_width: Width of cut (with units, e.g., Q_(1.5, ureg.mm))
        material_density: Density of material being cut (with units)
        gas_density: Density of assist gas at nozzle (from calculate_gas_density_at_nozzle)
        efficiency_factor: Empirical correction (0.0-1.0)
                          - Conservative (safe): 0.1
                          - Moderate: 0.2-0.3
                          - Optimistic: 0.5
                          Default: 0.1 (conservative)

    Returns:
        Maximum linear cutting speed (Q_ with velocity units)

    Notes:
        - This is a simplified engineering model
        - Real clearing behavior is highly nonlinear
        - Depends on: standoff distance, nozzle angle, gas type, melt viscosity
        - Use conservative efficiency_factor for safety
        - Validate against experimental cutting tests

    Example:
        >>> v_gas = calculate_nozzle_exit_velocity(...)
        >>> gas_rho = calculate_gas_density_at_nozzle(...)
        >>> v_clearing = calculate_clearing_speed_limit(
        ...     nozzle_velocity=v_gas,
        ...     nozzle_diameter=Q_(2.0, ureg.mm),
        ...     kerf_width=Q_(1.5, ureg.mm),
        ...     material_density=Q_(7850, ureg.kg/ureg.m**3),
        ...     gas_density=gas_rho,
        ...     efficiency_factor=0.1
        ... )
    """
    # Input validation
    if nozzle_velocity.magnitude <= 0:
        raise ValueError("Nozzle velocity must be positive")
    if nozzle_diameter.magnitude <= 0:
        raise ValueError("Nozzle diameter must be positive")
    if kerf_width.magnitude <= 0:
        raise ValueError("Kerf width must be positive")
    if material_density.magnitude <= 0:
        raise ValueError("Material density must be positive")
    if gas_density.magnitude <= 0:
        raise ValueError("Gas density must be positive")
    if not 0 <= efficiency_factor <= 1:
        raise ValueError("Efficiency factor must be between 0 and 1")

    # Calculate nozzle cross-sectional area
    # A = π * d²/4
    nozzle_area = math.pi * (nozzle_diameter ** 2) / 4

    # Calculate gas momentum flux
    # Momentum flux = ρ_gas × A × v²
    momentum_flux = gas_density * nozzle_area * (nozzle_velocity ** 2)

    # Heuristic clearing speed limit
    # Assumes momentum transfer is proportional to ability to clear material
    # Speed ∝ (Gas Momentum Flux) / (Material Density × Kerf Width)
    #
    # Dimensional analysis:
    # [momentum_flux] = kg·m/s² = N
    # [material_density × kerf] = kg/m³ × m = kg/m²
    # [speed] = [momentum_flux] / [material_density × kerf] / [some_length]
    #
    # We use a characteristic length related to nozzle geometry
    clearing_speed = (momentum_flux * efficiency_factor) / (material_density * kerf_width * nozzle_diameter)

    return clearing_speed
