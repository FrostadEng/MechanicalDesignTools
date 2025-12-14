"""
CSA S16 Member Design - Beams and Columns

This module contains CSA S16-specific validation logic for structural members.
Functions return detailed calculation traces showing step-by-step derivations.
"""
import numpy as np
from mech_core.standards.units import ureg, Q_
from mech_core.components.members.aisc import SectionProperties
from mech_core.standards.materials import StructuralMaterial


def get_k_factor(boundary_conditions: list[str]) -> float:
    """
    Determines effective length factor K based on theoretical boundaries.
    """
    # Normalize inputs
    conds = sorted([b.lower().strip() for b in boundary_conditions])

    # Mapping (Theoretical K values per AISC Table C-A-7.1)
    mapping = {
        "fixed-fixed": 0.65,
        "fixed-pinned": 0.80,
        "fixed-rolled": 1.20,
        "pinned-pinned": 1.00,
        "fixed-free": 2.10, # Cantilever
        "pinned-rolled": 2.00 # Unstable unless braced, treated as guided cantilever
    }

    key = f"{conds[0]}-{conds[1]}"
    if key in mapping:
        return mapping[key]

    # Default fallback
    print(f"[WARNING] Unknown boundary conditions '{key}'. Assuming K=1.0")
    return 1.0


def check_compressive_resistance(
    section: SectionProperties,
    material: StructuralMaterial,
    length: Q_,
    upper_lower_boundary_conditions: list[str] = ["pinned", "pinned"]
):
    """
    Checks Axial Compressive Resistance per CSA S16 with Detailed Symbolic Documentation.
    """
    steps = []

    # 1. SETUP VARIABLES (Floats for math)
    L_val = length.to(ureg.mm).magnitude
    E_val = material.elastic_modulus.to(ureg.MPa).magnitude
    Fy_val = material.yield_strength.to(ureg.MPa).magnitude
    Ag_val = section.A.to(ureg.mm**2).magnitude
    rx_val = section.rx.to(ureg.mm).magnitude
    ry_val = section.ry.to(ureg.mm).magnitude

    k_val = get_k_factor(upper_lower_boundary_conditions)

    steps.append({
        "desc": "1. Design Variables",
        "variables": [
            f"F_y = {Fy_val:.0f} \\text{{ MPa}}",
            f"E = {E_val:.0f} \\text{{ MPa}}",
            f"L = {L_val:.0f} \\text{{ mm}}",
            f"A_g = {Ag_val:.0f} \\text{{ mm}}^2",
            f"r_x = {rx_val:.1f} \\text{{ mm}}",
            f"r_y = {ry_val:.1f} \\text{{ mm}}",
            f"K = {k_val:.2f} \\text{{ ({'-'.join(upper_lower_boundary_conditions)})}}"
        ],
        "conclusion": "Inputs collected from AISC Database and boundary conditions."
    })

    # 2. SLENDERNESS RATIO (KL/r)
    KL_x = k_val * L_val / rx_val
    KL_y = k_val * L_val / ry_val

    governing_axis = "X-X" if KL_x > KL_y else "Y-Y"
    KL_r_val = max(KL_x, KL_y)

    steps.append({
        "desc": "2. Slenderness Ratio (KL/r)",
        "symbol": r"\frac{KL}{r} = \max \left( \frac{KL}{r_x}, \frac{KL}{r_y} \right)",
        "sub": rf"\max \left( \frac{{{k_val} \cdot {L_val:.0f}}}{{{rx_val:.1f}}}, \frac{{{k_val} \cdot {L_val:.0f}}}{{{ry_val:.1f}}} \right) = \max({KL_x:.1f}, {KL_y:.1f})",
        "result": rf"{KL_r_val:.2f} \text{{ (Axis {governing_axis})}}",
        "conclusion": "The column will buckle about this axis first."
    })

    if KL_r_val > 200:
        steps.append({
            "desc": "WARNING: Slenderness Limit",
            "symbol": r"\frac{KL}{r} > 200",
            "result": r"\text{Exceeds AISC User Note recommendation}",
            "conclusion": "The column is extremely slender and efficiency is low."
        })

    # 3. ELASTIC BUCKLING STRESS (Fe)
    Fe_val = (np.pi**2 * E_val) / (KL_r_val**2)

    steps.append({
        "desc": "3. Elastic Buckling Stress (Fe)",
        "ref": "AISC Eq. E3-4",
        "symbol": r"F_e = \frac{\pi^2 E}{(KL/r)^2}",
        "sub": f"F_e = \\frac{{\\pi^2 ({E_val:.0f})}}{{({KL_r_val:.1f})^2}}",
        "result": f"{Fe_val:.2f} \\text{{ MPa}}",
        "conclusion": "This is the theoretical Euler buckling stress."
    })

    # 4. CRITICAL STRESS (Fcr)
    limit_slenderness = 4.71 * np.sqrt(E_val / Fy_val)
    Fcr_val = 0.0
    failure_mode = ""

    steps.append({
        "desc": "4. Buckling Regime Classification",
        "symbol": r"\frac{KL}{r} \text{ vs } 4.71\sqrt{\frac{E}{F_y}}",
        "sub": f"{KL_r_val:.1f} \\text{{ vs }} 4.71\\sqrt{{{E_val:.0f}/{Fy_val:.0f}}} = {limit_slenderness:.1f}",
        "result": "Check Limit",
        "conclusion": "Comparing actual slenderness to the material yield limit."
    })

    if KL_r_val <= limit_slenderness:
        failure_mode = "Inelastic Buckling"
        exponent = Fy_val / Fe_val
        Fcr_val = (0.658 ** exponent) * Fy_val

        steps.append({
            "desc": "Classification: Inelastic Buckling",
            "symbol": r"\frac{KL}{r} \le 4.71\sqrt{\frac{E}{F_y}}",
            "result": r"\text{Regime: Inelastic (Short/Intermediate Column)}",
            "conclusion": "The column will yield and crush before it fully buckles elastically."
        })

        steps.append({
            "desc": "5. Critical Stress Calculation",
            "ref": "AISC Eq. E3-2",
            "symbol": r"F_{cr} = \left[ 0.658^{\frac{F_y}{F_e}} \right] F_y",
            "sub": f"F_{{cr}} = \\left[ 0.658^{{\\frac{{{Fy_val:.0f}}}{{{Fe_val:.1f}}}}} \\right] ({Fy_val:.0f})",
            "result": f"{Fcr_val:.2f} \\text{{ MPa}}",
            "conclusion": "Therefore, this is the maximum stress the column can sustain."
        })

    else:
        failure_mode = "Elastic Buckling"
        Fcr_val = 0.877 * Fe_val

        steps.append({
            "desc": "Classification: Elastic Buckling",
            "symbol": r"\frac{KL}{r} > 4.71\sqrt{\frac{E}{F_y}}",
            "result": r"\text{Regime: Elastic (Slender Column)}",
            "conclusion": "The column behaves like a classic Euler column."
        })

        steps.append({
            "desc": "5. Critical Stress Calculation",
            "ref": "AISC Eq. E3-3",
            "symbol": r"F_{cr} = 0.877 F_e",
            "sub": f"F_{{cr}} = 0.877 ({Fe_val:.2f})",
            "result": f"{Fcr_val:.2f} \\text{{ MPa}}",
            "conclusion": "Capacity is reduced to 87.7% of the theoretical Euler stress."
        })

    # 5. NOMINAL STRENGTH
    Pn_val = Fcr_val * Ag_val * 1e-3 # N -> kN

    steps.append({
        "desc": "6. Nominal Compressive Strength",
        "ref": "AISC Eq. E3-1",
        "symbol": r"P_n = F_{cr} A_g",
        "sub": f"P_n = ({Fcr_val:.2f} \\text{{ MPa}})({Ag_val:.0f} \\text{{ mm}}^2)(10^{{-3}})",
        "result": f"{Pn_val:.2f} \\text{{ kN}}",
        "conclusion": "Therefore, this is the unfactored capacity."
    })

    # 6. LRFD CHECK
    phi_c = 0.9
    Pu_cap = phi_c * Pn_val

    steps.append({
        "desc": "7. Design Compressive Strength (LRFD)",
        "symbol": r"\phi_c P_n = 0.9 P_n",
        "sub": f"0.9 ({Pn_val:.2f})",
        "result": f"\\mathbf{{{Pu_cap:.2f} \\text{{ kN}}}}",
        "conclusion": "Therefore, this is the factored axial capacity."
    })

    return {
        "Pn": Pn_val * ureg.kN,
        "Pu_capacity": Pu_cap * ureg.kN,
        "Fcr": Fcr_val * ureg.MPa,
        "slenderness": KL_r_val * ureg.dimensionless,
        "limit_slenderness": limit_slenderness,
        "failure_mode": failure_mode,
        "governing_axis": governing_axis,
        "k_factor": k_val,
        "boundary_conditions": upper_lower_boundary_conditions,
        "calc_trace": steps
    }


def check_flexural_resistance(
    section: SectionProperties,
    material: StructuralMaterial,
    unbraced_length: Q_,
    axis: str = "strong",
    cb: float = 1.0
):
    """
    Checks Flexural Resistance per CSA S16 with "Textbook Level" Symbolic Documentation.
    """
    steps = []

    if section.type not in ['W', 'M', 'S', 'HP', 'C', 'MC']:
        raise NotImplementedError(f"Shape type {section.type} not supported.")

    # 1. SETUP VARIABLES
    E_val = material.elastic_modulus.to(ureg.MPa).magnitude
    Fy_val = material.yield_strength.to(ureg.MPa).magnitude
    Lb_val = unbraced_length.to(ureg.m).magnitude

    # --- WEAK AXIS PATH (RESTORED) ---
    if axis.lower() in ["weak", "y"]:
        Zy_val = section.Zy.to(ureg.mm**3).magnitude
        Sy_val = section.Sy.to(ureg.mm**3).magnitude
        
        steps.append({
            "desc": "1. Design Variables (Weak Axis)",
            "variables": [
                f"F_y = {Fy_val:.0f} \\text{{ MPa}}",
                f"Z_y = {Zy_val/1e3:.1f} \\times 10^3 \\text{{ mm}}^3",
                f"S_y = {Sy_val/1e3:.1f} \\times 10^3 \\text{{ mm}}^3"
            ],
            "conclusion": "Checking bending about the minor axis."
        })
        
        Mn_plastic = (Fy_val * Zy_val) * 1e-6 # kNm
        Mn_limit = (1.6 * Fy_val * Sy_val) * 1e-6 # kNm
        Mn_val = min(Mn_plastic, Mn_limit)
        
        steps.append({
            "desc": "2. Nominal Flexural Strength",
            "ref": "AISC Eq. F6-1",
            "symbol": r"M_n = \min(F_y Z_y, 1.6 F_y S_y)",
            "sub": f"M_n = \\min({Mn_plastic:.2f}, {Mn_limit:.2f})",
            "result": f"{Mn_val:.2f} \\text{{ kNm}}",
            "conclusion": "Capacity governed by plastic yielding (no LTB for weak axis)."
        })
        
        return {
            "Mn": Mn_val * ureg.kNm,
            "Mu_capacity": (0.9 * Mn_val) * ureg.kNm,
            "ltb_zone": "Weak Axis",
            "calc_trace": steps
        }

    # --- STRONG AXIS PATH ---
    Sx_val = section.Sx.to(ureg.mm**3).magnitude
    Zx_val = section.Zx.to(ureg.mm**3).magnitude
    ry_val = section.ry.to(ureg.mm).magnitude
    rts_val = section.rts.to(ureg.mm).magnitude
    J_val = section.J.to(ureg.mm**4).magnitude
    ho_val = section.ho.to(ureg.mm).magnitude

    steps.append({
        "desc": "1. Design Variables",
        "variables": [
            f"F_y = {Fy_val:.0f} \\text{{ MPa}}",
            f"E = {E_val:.0f} \\text{{ MPa}}",
            f"Z_x = {Zx_val:.0f} \\text{{ mm}}^3",
            f"S_x = {Sx_val:.0f} \\text{{ mm}}^3",
            f"r_y = {ry_val:.1f} \\text{{ mm}}",
            f"r_{{ts}} = {rts_val:.1f} \\text{{ mm}}",
            f"J = {J_val:.2e} \\text{{ mm}}^4",
            f"h_o = {ho_val:.1f} \\text{{ mm}}",
            f"L_b = {Lb_val:.2f} \\text{{ m}}",
            f"C_b = {cb:.2f}"
        ],
        "conclusion": "Inputs collected from AISC Database and Material Standards."
    })

    # 2. PLASTIC MOMENT
    Mp_val = (Fy_val * Zx_val) * 1e-6

    steps.append({
        "desc": "2. Plastic Moment Capacity (Mp)",
        "ref": "AISC Eq. F2-1",
        "symbol": r"M_p = F_y \cdot Z_x",
        "sub": f"M_p = ({Fy_val:.0f} \\text{{ MPa}})({Zx_val:.0f} \\text{{ mm}}^3) (10^{{-6}})",
        "result": f"{Mp_val:.2f} \\text{{ kNm}}",
        "conclusion": "This is the theoretical maximum capacity of the section."
    })

    # 3. LIMITING LENGTHS
    ratio_E_Fy = E_val / Fy_val
    Lp_val = 1.76 * ry_val * np.sqrt(ratio_E_Fy) / 1000 # m

    steps.append({
        "desc": "3a. Compact Limit Length (Lp)",
        "ref": "AISC Eq. F2-5",
        "symbol": r"L_p = 1.76 r_y \sqrt{\frac{E}{F_y}}",
        "sub": f"L_p = 1.76 ({ry_val:.1f} \\text{{ mm}}) \\sqrt{{\\frac{{{E_val:.0f}}}{{ {Fy_val:.0f} }}}}",
        "result": f"{Lp_val:.2f} \\text{{ m}}",
        "conclusion": "If unbraced length is less than this, M_n = M_p."
    })

    c = 1.0
    term_geom = (J_val * c) / (Sx_val * ho_val)
    term_stress = (0.7 * Fy_val) / E_val

    inner_root_val = np.sqrt(term_geom**2 + 6.76 * term_stress**2)
    outer_root_val = np.sqrt(term_geom + inner_root_val)
    Lr_val = (1.95 * rts_val * (1/term_stress) * outer_root_val) / 1000 # m

    steps.append({
        "desc": "3b. Elastic Limit Length (Lr)",
        "ref": "AISC Eq. F2-6",
        "symbol": r"L_r = 1.95 r_{ts} \frac{E}{0.7 F_y} \sqrt{ \frac{J c}{S_x h_o} + \sqrt{ (\frac{J c}{S_x h_o})^2 + 6.76 (\frac{0.7 F_y}{E})^2 } }",
        "sub": f"L_r = 1.95 ({rts_val:.1f}) \\frac{{{E_val:.0f}}}{{0.7({Fy_val:.0f})}} \\sqrt{{ {term_geom:.4f} + \\sqrt{{ ({term_geom:.4f})^2 + 6.76 (\\frac{{0.7({Fy_val:.0f})}}{{{E_val:.0f}}})^2 }} }}",
        "result": f"{Lr_val:.2f} \\text{{ m}}",
        "conclusion": "If unbraced length exceeds this, the beam fails by elastic buckling."
    })

    # 4. CLASSIFICATION
    Mn_val = 0.0
    zone_desc = ""

    steps.append({
        "desc": "4. Slenderness Classification",
        "symbol": r"L_p \text{ vs } L_b \text{ vs } L_r",
        "sub": f"{Lp_val:.2f} \\text{{ m}} \\text{{ vs }} \\mathbf{{{Lb_val:.2f} \\text{{ m}}}} \\text{{ vs }} {Lr_val:.2f} \\text{{ m}}",
        "result": "Check Zone",
        "conclusion": "We compare the actual unbraced length to the calculated limits."
    })

    if Lb_val <= Lp_val:
        Mn_val = Mp_val
        zone_desc = "Compact Zone (Zone 1)"
        steps.append({
            "desc": "Conclusion: Zone 1",
            "symbol": r"L_b \le L_p",
            "sub": f"{Lb_val:.2f} \\le {Lp_val:.2f}",
            "result": r"\mathbf{M_n = M_p}",
            "conclusion": "Therefore, the beam is fully compact."
        })

    elif Lb_val > Lp_val and Lb_val <= Lr_val:
        zone_desc = "Inelastic LTB (Zone 2)"
        Mr_val = 0.7 * Fy_val * Sx_val * 1e-6
        numerator = Lb_val - Lp_val
        denominator = Lr_val - Lp_val
        fraction = numerator / denominator

        Mn_calc = cb * (Mp_val - (Mp_val - Mr_val) * fraction)
        Mn_val = min(Mn_calc, Mp_val)

        steps.append({
            "desc": "5. Nominal Strength (Inelastic LTB)",
            "ref": "AISC Eq. F2-2",
            "symbol": r"M_n = C_b \left[ M_p - (M_p - 0.7 F_y S_x) \left( \frac{L_b - L_p}{L_r - L_p} \right) \right] \le M_p",
            "sub": f"M_n = {cb} \\left[ {Mp_val:.1f} - ({Mp_val:.1f} - 0.7({Fy_val:.0f})({Sx_val:.0f})10^{{-6}}) \\left( \\frac{{{Lb_val:.2f} - {Lp_val:.2f}}}{{{Lr_val:.2f} - {Lp_val:.2f}}} \\right) \\right]",
            "result": f"{Mn_val:.2f} \\text{{ kNm}}",
            "conclusion": "Therefore, the capacity is reduced from the plastic moment based on the unbraced length."
        })

    else:
        zone_desc = "Elastic LTB (Zone 3)"
        slenderness = Lb_val * 1000 / rts_val

        steps.append({
            "desc": "5a. Slenderness Ratio",
            "symbol": r"\lambda = \frac{L_b}{r_{ts}}",
            "sub": f"\\lambda = \\frac{{{Lb_val:.2f} \\times 1000}}{{ {rts_val:.1f} }}",
            "result": f"{slenderness:.2f}",
            "conclusion": "Effective slenderness ratio."
        })

        Fcr_val = ((cb * np.pi**2 * E_val) / (slenderness**2)) * np.sqrt(1 + 0.078 * term_geom * slenderness**2)

        steps.append({
            "desc": "5b. Critical Buckling Stress (Fcr)",
            "ref": "AISC Eq. F2-4",
            "symbol": r"F_{cr} = \frac{C_b \pi^2 E}{\lambda^2} \sqrt{1 + 0.078 \frac{J c}{S_x h_o} \lambda^2}",
            "sub": f"F_{{cr}} = \\frac{{{cb} \\pi^2 ({E_val:.0f})}}{{({slenderness:.1f})^2}} \\sqrt{{1 + 0.078 ({term_geom:.4f}) ({slenderness:.1f})^2}}",
            "result": f"{Fcr_val:.2f} \\text{{ MPa}}",
            "conclusion": "Therefore, the beam fails by elastic buckling at this stress level."
        })

        Mn_calc = Fcr_val * Sx_val * 1e-6
        Mn_val = min(Mn_calc, Mp_val)

        steps.append({
            "desc": "5c. Nominal Strength",
            "symbol": r"M_n = F_{cr} S_x \le M_p",
            "sub": f"M_n = ({Fcr_val:.1f})({Sx_val:.0f})(10^{{-6}})",
            "result": f"{Mn_val:.2f} \\text{{ kNm}}",
            "conclusion": "Therefore, this is the maximum elastic moment."
        })

    # 6. LRFD CHECK
    phi = 0.9
    Mu_cap = phi * Mn_val

    steps.append({
        "desc": "6. Design Strength (LRFD)",
        "symbol": r"\phi_b M_n = 0.9 M_n",
        "sub": f"0.9 ({Mn_val:.2f})",
        "result": f"\\mathbf{{{Mu_cap:.2f} \\text{{ kNm}}}}",
        "conclusion": "Therefore, this is the factored moment resistance of the beam."
    })

    return {
        "Mn": Mn_val * ureg.kN * ureg.m,
        "Mu_capacity": Mu_cap * ureg.kN * ureg.m,
        "Lp": Lp_val * ureg.m,
        "Lr": Lr_val * ureg.m,
        "ltb_zone": zone_desc,
        "calc_trace": steps
    }