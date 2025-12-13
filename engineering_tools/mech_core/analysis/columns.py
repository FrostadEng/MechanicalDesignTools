import numpy as np
from mech_core.units import ureg, Q_
from mech_core.components.aisc_members import SectionProperties
from mech_core.standards.materials import StructuralMaterial

def calculate_compressive_strength(
    section: SectionProperties,
    material: StructuralMaterial,
    length: Q_,
    upper_lower_boundary_conditions: list[str] = ["pinned", "pinned"]
):
    """
    Calculates the AISC 360-16 Nominal Compressive Strength (Pn).

    Args:
        section: The beam/column object (e.g., W8x31)
        material: The material object (e.g., A992 Steel)
        length: Unbraced length of the column
        upper_lower_boundary_conditions: Boundary conditions as [end1, end2] where each end is one of:
                                         "fixed", "pinned", "rolled", or "free"
                                         Default: ["pinned", "pinned"]

    Returns:
        dict containing Pn, mode of failure, and intermediate calcs.
    """

    # Map boundary conditions to K-factors
    def get_k_factor(boundary_conditions: list[str]) -> float:
        """
        Maps boundary conditions to effective length factor (K).

        Args:
            boundary_conditions: [end1, end2] boundary conditions

        Returns:
            K-factor based on AISC recommendations

        Raises:
            ValueError: If boundary conditions are invalid
        """
        # Normalize inputs to lowercase
        bc = [condition.lower() for condition in boundary_conditions]

        # Sort to create canonical ordering (since fixed-pinned = pinned-fixed)
        bc_sorted = tuple(sorted(bc))

        # K-factor mapping table
        k_factor_map = {
            ("fixed", "fixed"): 0.65,
            ("fixed", "pinned"): 0.8,
            ("fixed", "rolled"): 1.2,
            ("fixed", "free"): 2.1,
            ("pinned", "pinned"): 1.0,
        }

        if bc_sorted in k_factor_map:
            return k_factor_map[bc_sorted]
        else:
            valid_conditions = ["fixed", "pinned", "rolled", "free"]
            raise ValueError(
                f"Invalid boundary conditions: {boundary_conditions}. "
                f"Each end must be one of {valid_conditions}. "
                f"Valid combinations are: Fixed-Fixed (K=0.65), Fixed-Pinned (K=0.8), "
                f"Fixed-Rolled (K=1.2), Fixed-Free (K=2.1), Pinned-Pinned (K=1.0)"
            )

    # Get the K-factor from boundary conditions
    k_factor = get_k_factor(upper_lower_boundary_conditions)

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
        "governing_axis": "Y-Y" if section.ry < section.rx else "X-X",
        "k_factor": k_factor,
        "boundary_conditions": upper_lower_boundary_conditions
    }


def generate_markdown(
    section: SectionProperties,
    material: StructuralMaterial,
    length: Q_,
    upper_lower_boundary_conditions: list[str] = ["pinned", "pinned"]
):
    """
    Generates a formatted markdown report for column compressive strength analysis.

    Args:
        section: The column section object
        material: The material object
        length: Unbraced length of the column
        upper_lower_boundary_conditions: Boundary conditions as [end1, end2]

    Returns:
        Formatted markdown string
    """
    result = calculate_compressive_strength(section, material, length, upper_lower_boundary_conditions)

    lines = []
    lines.append(f"# Column Compressive Strength Analysis")
    lines.append(f"**Section:** {section.name} | **Material:** {material.name}")
    lines.append(f"**Unbraced Length:** {length.to(ureg.meter):.3f}")
    lines.append(f"**Boundary Conditions:** {result['boundary_conditions'][0].title()}-{result['boundary_conditions'][1].title()} (K = {result['k_factor']})")
    lines.append("---")

    lines.append(f"### Slenderness Analysis")
    lines.append(f"- **Governing Axis:** {result['governing_axis']}")
    lines.append(f"- **Slenderness Ratio (KL/r):** {result['slenderness']:.2f}")
    lines.append(f"- **Limit Slenderness:** {result['limit_slenderness']:.2f}")

    # Add warning if slenderness exceeds 200
    if result['slenderness'] > 200:
        lines.append(f"- **⚠️ WARNING:** Slenderness exceeds AISC recommendation of 200")

    lines.append("")
    lines.append(f"### Capacity Results")
    lines.append(f"- **Failure Mode:** {result['failure_mode']}")
    lines.append(f"- **Critical Stress (Fcr):** {result['Fcr']:.3f}")
    lines.append(f"- **Nominal Strength (Pn):** {result['Pn']:.3f}")
    lines.append(f"- **Design Capacity (φPn):** {result['Pu_capacity']:.3f}")

    lines.append("")
    lines.append("### CONCLUSION")
    lines.append(f"> **Design Axial Capacity:** {result['Pu_capacity']:.3f}")

    return "\n".join(lines)