import numpy as np
from mech_core.units import ureg, Q_
from mech_core.components.aisc_members import SectionProperties
from mech_core.standards.materials import StructuralMaterial

def calculate_bending_capacity(
    section: SectionProperties, 
    material: StructuralMaterial, 
    unbraced_length: Q_, 
    axis: str = "strong", 
    cb: float = 1.0
):
    """
    Calculates Flexural Strength (Mn) with "Textbook Level" Symbolic Documentation.
    """
    steps = [] 
    
    if section.type not in ['W', 'M', 'S', 'HP', 'C', 'MC']:
        raise NotImplementedError(f"Shape type {section.type} not supported.")

    # 1. SETUP VARIABLES
    E_val = material.elastic_modulus.to(ureg.MPa).magnitude
    Fy_val = material.yield_strength.to(ureg.MPa).magnitude
    Lb_val = unbraced_length.to(ureg.m).magnitude
    
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
    
    # Lp
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

    # Lr Components
    c = 1.0
    term_geom = (J_val * c) / (Sx_val * ho_val)
    term_stress = (0.7 * Fy_val) / E_val
    
    # Pre-calculate the inner terms for the display string so they aren't massive
    # But show the logic
    
    # Final Lr Calculation
    inner_root_val = np.sqrt(term_geom**2 + 6.76 * term_stress**2)
    outer_root_val = np.sqrt(term_geom + inner_root_val)
    Lr_val = (1.95 * rts_val * (1/term_stress) * outer_root_val) / 1000 # m
    
    # Formulate the Monster String for Substitution
    # We will insert the calculated terms Xgeom and Xstress into the formula string
    # to keep it readable but explicit.
    
    steps.append({
        "desc": "3b. Elastic Limit Length (Lr)",
        "ref": "AISC Eq. F2-6",
        "symbol": r"L_r = 1.95 r_{ts} \frac{E}{0.7 F_y} \sqrt{ \frac{J c}{S_x h_o} + \sqrt{ (\frac{J c}{S_x h_o})^2 + 6.76 (\frac{0.7 F_y}{E})^2 } }",
        # We explicitly show the numbers entering the square root
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
        
        # Breakdown the Mr term (0.7 Fy Sx)
        Mr_val = 0.7 * Fy_val * Sx_val * 1e-6
        
        # Calculate fraction for math
        numerator = Lb_val - Lp_val
        denominator = Lr_val - Lp_val
        fraction = numerator / denominator
        
        Mn_calc = cb * (Mp_val - (Mp_val - Mr_val) * fraction)
        Mn_val = min(Mn_calc, Mp_val)
        
        steps.append({
            "desc": "5. Nominal Strength (Inelastic LTB)",
            "ref": "AISC Eq. F2-2",
            "symbol": r"M_n = C_b \left[ M_p - (M_p - 0.7 F_y S_x) \left( \frac{L_b - L_p}{L_r - L_p} \right) \right] \le M_p",
            # THE BIG REVEAL: Full expansion
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
        
        # Fcr Calculation
        # We also expand 0.078 term for completeness
        Fcr_val = ((cb * np.pi**2 * E_val) / (slenderness**2)) * np.sqrt(1 + 0.078 * term_geom * slenderness**2)
        
        steps.append({
            "desc": "5b. Critical Buckling Stress (Fcr)",
            "ref": "AISC Eq. F2-4",
            "symbol": r"F_{cr} = \frac{C_b \pi^2 E}{\lambda^2} \sqrt{1 + 0.078 \frac{J c}{S_x h_o} \lambda^2}",
            # Full expansion
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