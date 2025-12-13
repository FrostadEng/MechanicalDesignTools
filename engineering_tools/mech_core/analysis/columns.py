import numpy as np
from mech_core.units import ureg, Q_
from mech_core.components.aisc_members import SectionProperties
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

def calculate_compressive_strength(
    section: SectionProperties, 
    material: StructuralMaterial, 
    length: Q_, 
    upper_lower_boundary_conditions: list[str] = ["pinned", "pinned"]
):
    """
    Calculates Axial Compressive Strength (Pn) with Detailed Symbolic Documentation.
    Implements AISC 360-16 Chapter E.
    """
    steps = []
    
    # 1. SETUP VARIABLES (Floats for math)
    # We use base metric units (MPa, mm, N) for the internal calculation engine
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
    # We check both axes to find the governing one.
    
    KL_x = k_val * L_val / rx_val
    KL_y = k_val * L_val / ry_val
    
    governing_axis = "X-X" if KL_x > KL_y else "Y-Y"
    KL_r_val = max(KL_x, KL_y)
    r_gov = rx_val if governing_axis == "X-X" else ry_val
    
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
    # Fe = pi^2 * E / (KL/r)^2
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
    # Determine boundary between Inelastic and Elastic
    # Limit = 4.71 * sqrt(E/Fy)
    
    # Safe float math
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
        # --- INELASTIC BUCKLING ---
        failure_mode = "Inelastic Buckling"
        
        # Fcr = 0.658^(Fy/Fe) * Fy
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
            "sub": f"F_{{cr}} = \\left[ 0.658^{{\\frac{{{Fy_val:.0f}}}{{{Fe_val:.1f}}}}} \\right] ({Fy_val:.0f}) = (0.658^{{{exponent:.2f}}})({Fy_val:.0f})",
            "result": f"{Fcr_val:.2f} \\text{{ MPa}}",
            "conclusion": "Therefore, this is the maximum stress the column can sustain."
        })
        
    else:
        # --- ELASTIC BUCKLING ---
        failure_mode = "Elastic Buckling"
        
        # Fcr = 0.877 * Fe
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
            "conclusion": "Capacity is reduced to 87.7% of the theoretical Euler stress to account for initial crookedness."
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
        "slenderness": KL_r_val,
        "limit_slenderness": limit_slenderness,
        "failure_mode": failure_mode,
        "governing_axis": governing_axis,
        "k_factor": k_val,
        "boundary_conditions": upper_lower_boundary_conditions,
        "calc_trace": steps # The Payload
    }