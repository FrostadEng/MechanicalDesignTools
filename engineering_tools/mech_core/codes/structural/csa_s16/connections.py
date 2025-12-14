"""
CSA S16 Connection Design

Validation logic for bolted and welded connections per CSA S16-19.
Returns detailed 'Wolfram-style' calculation traces.
"""
import numpy as np
from mech_core.standards.units import ureg, Q_
from mech_core.standards.materials import StructuralMaterial

# Helper: Standard Bolt Strengths (CSA/ASTM)
# Ideally, this comes from the fastener component, but the code layer needs a fallback reference
_BOLT_STRENGTHS = {
    "A325": 825,   # MPa (approx 120 ksi)
    "F3125": 825,  # Modern A325
    "A490": 1035,  # MPa (approx 150 ksi)
    "Grade 8.8": 800, # Metric class
    "Grade 10.9": 1000
}

def check_bolt_shear(
    n_bolts: int,
    bolt_diameter: Q_,
    bolt_grade: str,
    factored_shear: Q_
) -> dict:
    """
    Check bolt shear capacity per CSA S16 Clause 13.11.2.
     Assumes threads are excluded from shear plane (conservative/standard for shear tabs).
    """
    steps = []
    
    # 1. Setup Variables (Metric Base)
    db_val = bolt_diameter.to(ureg.mm).magnitude
    Vf_val = factored_shear.to(ureg.kN).magnitude
    
    # Resolve Bolt Strength
    Fu_bolt = 825.0 # Default A325
    clean_grade = bolt_grade.replace("ASTM", "").strip()
    
    # Simple lookup logic
    found_strength = False
    for key, val in _BOLT_STRENGTHS.items():
        if key in clean_grade or clean_grade in key:
            Fu_bolt = val
            found_strength = True
            break
            
    if not found_strength:
        # Fallback logic if user passes specific string
        pass 

    steps.append({
        "desc": "1. Bolt Parameters",
        "variables": [
            f"d_b = {db_val:.1f} \\text{{ mm}}",
            f"Grade: {bolt_grade}",
            f"F_{{ub}} = {Fu_bolt:.0f} \\text{{ MPa}}",
            f"n = {n_bolts}",
            f"V_f = {Vf_val:.2f} \\text{{ kN}}"
        ],
        "conclusion": "Parameters established for shear check."
    })

    # 2. Calculate Area
    Ab = (np.pi * db_val**2) / 4
    
    steps.append({
        "desc": "2. Bolt Area",
        "symbol": r"A_b = \frac{\pi d_b^2}{4}",
        "sub": f"A_b = \\frac{{\\pi ({db_val:.1f})^2}}{{4}}",
        "result": f"{Ab:.1f} \\text{{ mm}}^2"
    })

    # 3. Shear Resistance
    # CSA S16 13.11.2 (c): Threads excluded -> 0.60 factor
    # phi_b = 0.80
    phi_b = 0.80
    m_planes = 1.0 # Single shear tab
    
    Vr_one = 0.60 * phi_b * Ab * Fu_bolt * m_planes * 1e-3 # kN
    Vr_total = Vr_one * n_bolts
    
    steps.append({
        "desc": "3. Factored Shear Resistance (Per Bolt)",
        "ref": "CSA S16 Cl. 13.11.2",
        "symbol": r"V_r = 0.60 \phi_b A_b F_{ub} m",
        "sub": f"V_r = 0.60(0.80)({Ab:.0f})({Fu_bolt:.0f})(1)(10^{{-3}})",
        "result": f"{Vr_one:.2f} \\text{{ kN/bolt}}",
        "conclusion": "Capacity per bolt in single shear."
    })
    
    steps.append({
        "desc": "4. Total Shear Resistance",
        "symbol": r"V_{r,total} = n \cdot V_r",
        "sub": f"V_{{r,total}} = {n_bolts} \\cdot {Vr_one:.2f}",
        "result": f"\\mathbf{{{Vr_total:.2f} \\text{{ kN}}}}"
    })

    # 4. Utilization
    util = Vf_val / Vr_total
    status = "PASS" if util <= 1.0 else "FAIL"
    
    steps.append({
        "desc": "5. Check Utilization",
        "symbol": r"\frac{V_f}{V_r} \le 1.0",
        "sub": f"{Vf_val:.2f} / {Vr_total:.2f} = {util:.3f}",
        "result": status,
        "conclusion": f"The bolts {status.lower()} in shear."
    })

    return {
        "Vr": Vr_one * ureg.kN,
        "total_resistance": Vr_total * ureg.kN,
        "utilization": util,
        "status": status,
        "calc_trace": steps
    }


def check_bearing(
    bolt_diameter: Q_,
    plate_thickness: Q_,
    end_distance: Q_, # Not used in simplified check, but good for future expansion
    material: StructuralMaterial,
    factored_force: Q_,
    member_name: str = "Member"
) -> dict:
    """
    Check bearing capacity per CSA S16 Clause 13.12.
    Uses the standard "regular" bolt hole assumption.

    Args:
        member_name: Optional name to identify the member being checked (e.g., "Fin Plate", "Beam Web")
    """
    steps = []

    # 1. Setup
    db_val = bolt_diameter.to(ureg.mm).magnitude
    tp_val = plate_thickness.to(ureg.mm).magnitude
    Fu_plate = material.ultimate_strength.to(ureg.MPa).magnitude
    Vf_val = factored_force.to(ureg.kN).magnitude

    steps.append({
        "desc": f"1. Bearing Parameters ({member_name})",
        "variables": [
            f"t = {tp_val:.1f} \\text{{ mm}}",
            f"d_b = {db_val:.1f} \\text{{ mm}}",
            f"F_u = {Fu_plate:.0f} \\text{{ MPa}}",
            f"V_f = {Vf_val:.2f} \\text{{ kN}}"
        ],
        "conclusion": f"Material properties for the {member_name}."
    })

    # 2. Bearing Resistance
    # CSA S16 13.12.1.2: Br = 3 * phi_br * t * d * Fu
    # This applies when deformation at service loads is not a design consideration (standard)
    phi_br = 0.80
    
    Br_val = 3 * phi_br * tp_val * db_val * Fu_plate * 1e-3 # kN
    
    steps.append({
        "desc": "2. Factored Bearing Resistance",
        "ref": "CSA S16 Cl. 13.12.1.2",
        "symbol": r"B_r = 3 \phi_{br} t d F_u",
        "sub": f"B_r = 3(0.80)({tp_val:.1f})({db_val:.1f})({Fu_plate:.0f}) 10^{{-3}}",
        "result": f"\\mathbf{{{Br_val:.2f} \\text{{ kN}}}}",
        "conclusion": "Maximum load before bolt tears through material (Bearing limit)."
    })

    # 3. Check
    util = Vf_val / Br_val
    status = "PASS" if util <= 1.0 else "FAIL"
    
    steps.append({
        "desc": "3. Check Utilization",
        "symbol": r"\frac{V_f}{B_r} \le 1.0",
        "sub": f"{Vf_val:.2f} / {Br_val:.2f} = {util:.3f}",
        "result": status
    })

    return {
        "Br": Br_val * ureg.kN,
        "total_resistance": Br_val * ureg.kN,
        "utilization": util,
        "status": status,
        "calc_trace": steps
    }


def check_block_shear(
    Agv: Q_,          # Gross Shear Area
    Anv: Q_,          # Net Shear Area
    Ant: Q_,          # Net Tension Area
    material: StructuralMaterial,
    factored_force: Q_, # Generic name (can be Shear or Tension)
    Ubs: float = 1.0
):
    """
    Checks Block Shear Rupture per CSA S16 13.11.
    """
    # 1. Setup
    Fy = material.yield_strength.to(ureg.MPa).magnitude
    Fu = material.ultimate_strength.to(ureg.MPa).magnitude
    
    Agv_val = Agv.to(ureg.mm**2).magnitude
    Anv_val = Anv.to(ureg.mm**2).magnitude
    Ant_val = Ant.to(ureg.mm**2).magnitude
    Force_val = factored_force.to(ureg.kN).magnitude
    
    steps = []
    steps.append({
        "desc": "Block Shear Geometry",
        "variables": [
            f"A_{{gv}} = {Agv_val:.0f} \\text{{ mm}}^2",
            f"A_{{nv}} = {Anv_val:.0f} \\text{{ mm}}^2",
            f"A_{{nt}} = {Ant_val:.0f} \\text{{ mm}}^2",
            f"U_{{bs}} = {Ubs}"
        ],
        "conclusion": "Areas calculated based on bolt layout."
    })

    # 2. Calculate Resistance (Simplified common approach for S16/AISC J4.3)
    # Note: CSA S16-19 and AISC use slightly different formulations for the yield term.
    # We will use the AISC J4.3 standard formulation (Rupture + Yield check) 
    # which is generally accepted as robust.
    # Rn = 0.6 Fu Anv + Ubs Fu Ant <= 0.6 Fy Agv + Ubs Fu Ant
    
    # Term 1: Shear Rupture + Tension Rupture
    Rn_1 = 0.6 * Fu * Anv_val + Ubs * Fu * Ant_val
    
    # Term 2: Shear Yield + Tension Rupture
    Rn_2 = 0.6 * Fy * Agv_val + Ubs * Fu * Ant_val
    
    # Governing is minimum
    Rn = min(Rn_1, Rn_2)
    
    # Phi factor for rupture
    phi_u = 0.75 
    Vr = phi_u * Rn * 1e-3 # kN
    
    status = "PASS" if Vr >= Force_val else "FAIL"
    
    steps.append({
        "desc": "Block Shear Capacity",
        "ref": "CSA S16 13.11 / AISC J4.3",
        "symbol": r"T_r = \phi_u [ \min(0.6 F_u A_{nv}, 0.6 F_y A_{gv}) + U_{bs} F_u A_{nt} ]",
        "sub": f"T_r = {phi_u} [ \\min({0.6*Fu*Anv_val:.0f}, {0.6*Fy*Agv_val:.0f}) + {Ubs*Fu*Ant_val:.0f} ] 10^{{-3}}",
        "result": f"{Vr:.2f} \\text{{ kN}}",
        "conclusion": f"Resistance ({Vr:.1f} kN) vs Load ({Force_val:.1f} kN) -> {status}"
    })
    
    return {
        "capacity": Vr * ureg.kN,
        "utilization": Force_val / Vr if Vr > 0 else 999.0,
        "status": status,
        "calc_trace": steps
    }