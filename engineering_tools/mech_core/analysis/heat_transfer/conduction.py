from ...standards.units import ureg, Q_
from ...standards.materials.steel import StructuralMaterial

def calculate_heat_flux_1d(
    material: StructuralMaterial, 
    delta_temp: Q_, 
    thickness: Q_
) -> Q_:
    """
    Fourier's Law for steady-state 1D conduction.
    q_flux = k * (dT / dx)
    
    Returns: Power per Unit Area (Watt / meter^2)
    """
    # k is in W/(m*K)
    k = material.thermal_conductivity
    
    # Calculate gradient (dT/dx)
    # delta_temp can be degC or Kelvin difference, Pint handles it
    gradient = delta_temp / thickness
    
    return k * gradient

def calculate_thermal_diffusivity(material: StructuralMaterial) -> Q_:
    """
    Calculates Alpha (α).
    α = k / (rho * Cp)
    
    This represents how fast heat diffuses through the material.
    High Diffusivity = Heat spreads fast (Aluminum).
    Low Diffusivity = Heat stays local (Stainless Steel).
    
    Crucial for transient thermal analysis (e.g., HAZ size).
    Returns: meter^2 / second
    """
    k = material.thermal_conductivity
    rho = material.density
    cp = material.specific_heat
    
    return k / (rho * cp)