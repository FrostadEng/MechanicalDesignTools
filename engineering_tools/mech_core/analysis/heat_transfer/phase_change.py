"""
Phase Change Thermodynamics.
Calculates energy requirements for melting/solidification.
"""
from ...standards.units import ureg, Q_
from ...standards.materials.steel import StructuralMaterial

def calculate_melting_energy(
    material: StructuralMaterial,
    mass: Q_,
    t_ambient: Q_ = None
) -> Q_:
    """
    Calculates the total energy required to raise a mass from ambient
    temperature to a fully liquid state (Sensible Heat + Latent Heat).

    Q_total = m * [ Cp * (Tm - T_amb) + Lf ]
    """
    # Set default ambient temperature
    if t_ambient is None:
        t_ambient = Q_(20, ureg.degC)

    # 1. Sensible Heat (Energy to reach melting point)
    # delta_T is a Temperature Difference (Kelvin), so subtraction is safe here
    delta_T = material.melting_point - t_ambient
    q_sensible = mass * material.specific_heat * delta_T
    
    # 2. Latent Heat (Energy to turn solid to liquid at constant Temp)
    q_latent = mass * material.latent_heat_fusion
    
    return q_sensible + q_latent

def specific_melting_energy_volumetric(
    material: StructuralMaterial,
    t_ambient: Q_ = None
) -> Q_:
    """
    Returns the energy required to melt 1 cubic meter of this material.
    Useful for cutting calculations (Kerf Volume).

    Returns: Joules / meter^3
    """
    # Set default ambient temperature
    if t_ambient is None:
        t_ambient = Q_(20, ureg.degC)

    # Get energy per kg
    energy_per_kg = (
        material.specific_heat * (material.melting_point - t_ambient) +
        material.latent_heat_fusion
    )
    
    # Convert to Energy per Volume using Density
    return energy_per_kg * material.density