import numpy as np
from mech_core.units import ureg, Q_
from mech_core.standards.sections import SectionProperties
from mech_core.standards.materials.structural import StructuralMaterial

def calculate_compressive_strength(
    section: SectionProperties, 
    material: StructuralMaterial, 
    length: Q_, 
    k_factor: float = 1.0
):
    """
    Calculates the AISC 360-16 Nominal Compressive Strength (Pn).
    
    Args:
        section: The beam/column object (e.g., W8x31)
        material: The material object (e.g., A992 Steel)
        length: Unbraced length of the column
        k_factor: Effective length factor (1.0 for pinned-pinned, 0.5 fixed-fixed, 2.0 cantilever)
    
    Returns:
        dict containing Pn, mode of failure, and intermediate calcs.
    """
    
    # 1. Determine governing Radius of Gyration (r)
    # Columns buckle about their weakest axis (usually y-y for W-shapes)
    rx = section.rx
    ry = section.ry
    r_min = rx if rx.magnitude < ry.magnitude else ry
    
    # 2. Calculate Slenderness Ratio (KL/r)
    # L and r must be in same units. Pint handles this, but result is dimensionless.
    L_effective = k_factor * length
    slenderness = (L_effective / r_min).to(ureg.dimensionless).magnitude
    
    # AISC Limit: KL/r preferably < 200
    if slenderness > 200:
        print(f"[WARNING] Slenderness KL/r = {slenderness:.2f} > 200. Exceeds AISC recommendation.")

    # 3. Material Properties
    E = material.elastic_modulus
    Fy = material.yield_strength
    
    # 4. Calculate Elastic Buckling Stress (Fe) - Euler Stress
    # Fe = (pi^2 * E) / (KL/r)^2
    Fe = (np.pi**2 * E) / (slenderness**2)
    
    # 5. Determine Critical Stress (Fcr) based on Slenderness Limit
    # AISC Limit between Inelastic and Elastic buckling:
    # Limit = 4.71 * sqrt(E/Fy)
    limit_slenderness = 4.71 * np.sqrt(E / Fy)
    
    failure_mode = ""
    
    if slenderness <= limit_slenderness:
        # --- INELASTIC BUCKLING (Short/Intermediate Columns) ---
        # Fcr = [0.658 ^ (Fy / Fe)] * Fy
        # Note: The exponent is (Fy/Fe)
        exponent = (Fy / Fe).to(ureg.dimensionless).magnitude
        Fcr = (0.658 ** exponent) * Fy
        failure_mode = "Inelastic Buckling (Yielding dominates)"
    else:
        # --- ELASTIC BUCKLING (Long/Slender Columns) ---
        # Fcr = 0.877 * Fe
        Fcr = 0.877 * Fe
        failure_mode = "Elastic Buckling (Euler instability)"
        
    # 6. Nominal Compressive Strength (Pn)
    # Pn = Fcr * Ag
    Pn = Fcr * section.A
    
    # 7. Design Strength (LRFD vs ASD)
    # We will output LRFD (Phi = 0.90) by default as it's standard in Canada (LSD) and US (LRFD)
    phi_c = 0.90
    Pu_capacity = phi_c * Pn

    return {
        "Pn": Pn.to(ureg.kN),
        "Pu_capacity": Pu_capacity.to(ureg.kN), # Factored Capacity
        "Fcr": Fcr.to(ureg.MPa),
        "slenderness": slenderness,
        "limit_slenderness": limit_slenderness,
        "failure_mode": failure_mode,
        "governing_axis": "Y-Y" if section.ry < section.rx else "X-X"
    }