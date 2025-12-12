import numpy as np
from mech_core.units import ureg, Q_
from mech_core.components.aisc_members import SectionProperties
from mech_core.standards.materials.structural import StructuralMaterial

def calculate_strong_axis_bending(
    section: SectionProperties, 
    material: StructuralMaterial, 
    unbraced_length: Q_, 
    cb: float = 1.0
):
    if section.type not in ['W', 'M', 'S', 'HP', 'C', 'MC']:
        raise NotImplementedError(f"Shape type {section.type} not supported.")

    E = material.elastic_modulus
    Fy = material.yield_strength
    Sx = section.Sx
    Zx = section.Zx
    Lb = unbraced_length


    # Yielding
    Mp = Fy * Zx
    
    # LTB Constants
    ry = section.ry
    
    # LTB Limit Lp
    # We use .to('dimensionless').magnitude to be 100% safe
    term_E_Fy = np.sqrt((E / Fy).to("dimensionless").magnitude)
    Lp = 1.76 * ry * term_E_Fy
    
    # LTB Limit Lr
    rts = section.rts
    ho = section.ho
    J = section.J
    
    if rts is None or ho is None or J is None:
         print(f"[WARNING] Missing torsional props for {section.name}. Skipping LTB.")
         Lr = 999 * ureg.meter 
    else:
        c = 1.0 
        
        # --- ROBUST UNIT STRIPPING ---
        # 1. Stress Ratio
        # force 'dimensionless' then grab magnitude. 
        # This fixes the AttributeError because .magnitude returns a standard float.
        ratio_stress = (0.7 * Fy / E).to("dimensionless").magnitude
        
        # 2. Geometric Ratio
        ratio_geom = ((J * c) / (Sx * ho)).to("dimensionless").magnitude
        
        term2_inner = ratio_geom
        term3_inner = 6.76 * (ratio_stress**2)
        
        big_root = np.sqrt(term2_inner + np.sqrt(term2_inner**2 + term3_inner))
        
        # Lr = 1.95 * rts * (E / 0.7Fy) * big_root
        Lr = 1.95 * rts * (1 / ratio_stress) * big_root

    # Determine Mn
    status = ""
    Mn = 0 * ureg.newton * ureg.meter
    
    if Lb <= Lp:
        Mn = Mp
        status = "Zone 1 (Plastic Yielding)"
        
    elif Lb > Lp and Lb <= Lr:
        term_geometric = (Lb - Lp) / (Lr - Lp)
        Mn_calc = cb * (Mp - (Mp - 0.7 * Fy * Sx) * term_geometric)
        Mn = min(Mn_calc, Mp)
        status = "Zone 2 (Inelastic LTB)"
        
    else:
        # ZONE 3 (Elastic LTB)
        # Force dimensionless for safety
        L_rts = (Lb / rts).to("dimensionless").magnitude
        ratio_geom = ((J * c) / (Sx * ho)).to("dimensionless").magnitude

        term_A = (cb * np.pi**2 * E.to("MPa").magnitude) / (L_rts**2) # Use magnitude for calculation
        term_B = np.sqrt(1 + 0.078 * ratio_geom * L_rts**2)
        
        Fcr = (term_A * term_B) * ureg.MPa # Re-apply units
        Mn = Fcr * Sx
        Mn = min(Mn, Mp)
        status = "Zone 3 (Elastic LTB - Slender)"

    phi_b = 0.90
    Mu_capacity = phi_b * Mn
    
    return {
        "Mn": Mn.to(ureg.kN * ureg.meter),
        "Mu_capacity": Mu_capacity.to(ureg.kN * ureg.meter),
        "Lp": Lp.to(ureg.meter),
        "Lr": Lr.to(ureg.meter),
        "Lb": Lb.to(ureg.meter),
        "status": status,
        "Mp": Mp.to(ureg.kN * ureg.meter)
    }