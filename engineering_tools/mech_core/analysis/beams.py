import numpy as np
from mech_core.units import ureg, Q_
from mech_core.components.aisc_members import SectionProperties
from mech_core.standards.materials import StructuralMaterial

def calculate_bending_capacity(
    section: SectionProperties, 
    material: StructuralMaterial, 
    unbraced_length: Q_, 
    axis: str = "strong",  # NEW PARAMETER
    cb: float = 1.0
):
    """
    Calculates Flexural Strength (Mn) for W/C shapes.
    Handles 'strong' (X-X) or 'weak' (Y-Y) axis bending.
    """
    if section.type not in ['W', 'M', 'S', 'HP', 'C', 'MC']:
        raise NotImplementedError(f"Shape type {section.type} not supported.")
    
    # Normalize axis input
    axis = axis.lower().strip()
    if axis not in ["strong", "x", "weak", "y"]:
        raise ValueError("Axis must be 'strong'/'x' or 'weak'/'y'")

    E = material.elastic_modulus
    Fy = material.yield_strength
    
    # --- WEAK AXIS BENDING (Y-Y) ---
    # Logic: Beams bent about their weak axis do NOT suffer Lateral Torsional Buckling.
    # They fail by Plastic Yielding (Zy) or Flange Local Buckling.
    # For this MVP, we assume compact flanges and check Plastic Limit.
    if axis in ["weak", "y"]:
        Zy = section.Zy
        Sy = section.Sy
        
        # Nominal Strength is just Plastic Moment
        # Limit: 1.6 * Fy * Sy (To prevent excessive deformation per AISC F6)
        Mn_plastic = Fy * Zy
        Mn_limit = 1.6 * Fy * Sy
        
        Mn = min(Mn_plastic, Mn_limit)
        
        phi_b = 0.90
        return {
            "Mn": Mn.to(ureg.kN * ureg.meter),
            "Mu_capacity": (phi_b * Mn).to(ureg.kN * ureg.meter),
            "status": "Weak Axis Yielding",
            "axis": "Weak (Y-Y)"
        }

    # --- STRONG AXIS BENDING (X-X) ---
    # This is the existing LTB logic
    Sx = section.Sx
    Zx = section.Zx
    Mp = Fy * Zx
    
    # LTB Constants
    ry = section.ry
    
    term_E_Fy = np.sqrt((E / Fy).to("dimensionless").magnitude)
    Lp = 1.76 * ry * term_E_Fy
    
    # LTB Limit Lr
    rts = section.rts
    ho = section.ho
    J = section.J
    
    if rts is None or ho is None or J is None:
         # Fallback
         Lr = 999 * ureg.meter 
    else:
        c = 1.0 
        ratio_stress = (0.7 * Fy / E).to("dimensionless").magnitude
        ratio_geom = ((J * c) / (Sx * ho)).to("dimensionless").magnitude
        
        term2_inner = ratio_geom
        term3_inner = 6.76 * (ratio_stress**2)
        big_root = np.sqrt(term2_inner + np.sqrt(term2_inner**2 + term3_inner))
        
        Lr = 1.95 * rts * (1 / ratio_stress) * big_root

    # Determine Mn
    status = ""
    Mn = 0 * ureg.newton * ureg.meter
    Lb = unbraced_length
    
    if Lb <= Lp:
        Mn = Mp
        status = "Zone 1 (Plastic Yielding)"
    elif Lb > Lp and Lb <= Lr:
        term_geometric = (Lb - Lp) / (Lr - Lp)
        Mn_calc = cb * (Mp - (Mp - 0.7 * Fy * Sx) * term_geometric)
        Mn = min(Mn_calc, Mp)
        status = "Zone 2 (Inelastic LTB)"
    else:
        L_rts = (Lb / rts).to("dimensionless").magnitude
        ratio_geom = ((J * c) / (Sx * ho)).to("dimensionless").magnitude
        term_A = (cb * np.pi**2 * E.to("MPa").magnitude) / (L_rts**2)
        term_B = np.sqrt(1 + 0.078 * ratio_geom * L_rts**2)
        Fcr = (term_A * term_B) * ureg.MPa
        Mn = Fcr * Sx
        Mn = min(Mn, Mp)
        status = "Zone 3 (Elastic LTB)"

    phi_b = 0.90
    return {
        "Mn": Mn.to(ureg.kN * ureg.meter),
        "Mu_capacity": (phi_b * Mn).to(ureg.kN * ureg.meter),
        "Lp": Lp.to(ureg.meter),
        "Lr": Lr.to(ureg.meter),
        "status": status,
        "axis": "Strong (X-X)"
    }


def generate_markdown(
    section: SectionProperties,
    material: StructuralMaterial,
    unbraced_length: Q_,
    axis: str = "strong",
    cb: float = 1.0
):
    """
    Generates a formatted markdown report for beam bending capacity analysis.

    Args:
        section: The beam section object
        material: The material object
        unbraced_length: Unbraced length of the beam
        axis: "strong" (X-X) or "weak" (Y-Y) axis
        cb: Moment gradient factor

    Returns:
        Formatted markdown string
    """
    result = calculate_bending_capacity(section, material, unbraced_length, axis, cb)

    lines = []
    lines.append(f"# Beam Bending Capacity Analysis")
    lines.append(f"**Section:** {section.name} | **Material:** {material.name}")
    lines.append(f"**Unbraced Length:** {unbraced_length.to(ureg.meter):.3f} | **Cb:** {cb}")
    lines.append(f"**Axis:** {result['axis']}")
    lines.append("---")

    lines.append(f"### Results")
    lines.append(f"- **Failure Mode:** {result['status']}")
    lines.append(f"- **Nominal Moment (Mn):** {result['Mn']:.3f}")
    lines.append(f"- **Design Capacity (φMn):** {result['Mu_capacity']:.3f}")

    # Add LTB limits for strong axis bending
    if axis.lower() in ["strong", "x"]:
        lines.append(f"- **Lp (Plastic Limit):** {result['Lp']:.3f}")
        lines.append(f"- **Lr (Inelastic Limit):** {result['Lr']:.3f}")

    lines.append("")
    lines.append("### CONCLUSION")
    lines.append(f"> **Design Moment Capacity:** {result['Mu_capacity']:.3f}")

    return "\n".join(lines)