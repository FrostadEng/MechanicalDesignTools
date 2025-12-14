import numpy as np
from mech_core.standards.units import ureg

def check_bolt_shear_group(num_bolts, bolt_object, num_shear_planes=1):
    """
    Standard CSA/AISC Check for Bolt Group Shear.
    Returns the Wolfram Trace Step.
    """
    # Extract Values
    Ab = bolt_object.thread.stress_area.to(ureg.mm**2).magnitude
    Fub = bolt_object.material.tensile_strength.to(ureg.MPa).magnitude
    
    # CSA S16 13.11.2 (phi = 0.80)
    phi = 0.80
    Vr_one = 0.6 * phi * Ab * Fub * num_shear_planes * 1e-3 # kN
    Vr_total = Vr_one * num_bolts
    
    return {
        "capacity": Vr_total * ureg.kN,
        "step": {
            "desc": "Bolt Group Shear Capacity",
            "ref": "CSA S16 13.11.2",
            "symbol": r"V_r = n \cdot 0.6 \phi_b A_b F_u m",
            "sub": f"V_r = {num_bolts} \cdot 0.6(0.8)({Ab:.0f})({Fub:.0f})(1)",
            "result": f"{Vr_total:.2f} \\text{{ kN}}"
        }
    }

def check_block_shear_rupture(Fu_elem, Anv, Ant, Ubs=1.0):
    """
    Calculates Block Shear Rupture (Common to C-Channels, Coping, Gussets).
    Anv: Net Area in Shear (Vertical line of bolts)
    Ant: Net Area in Tension (Horizontal bottom leg)
    """
    # Ensure raw floats
    if hasattr(Fu_elem, 'magnitude'): Fu_elem = Fu_elem.magnitude
    if hasattr(Anv, 'magnitude'): Anv = Anv.magnitude
    if hasattr(Ant, 'magnitude'): Ant = Ant.magnitude
    
    # AISC J4.3 / CSA S16 13.11
    # Rn = 0.6 Fu Anv + Ubs Fu Ant
    R_shear = 0.6 * Fu_elem * Anv
    R_tension = Ubs * Fu_elem * Ant
    
    Rn = (R_shear + R_tension) * 1e-3 # kN
    phi = 0.75
    Vr = phi * Rn
    
    return {
        "capacity": Vr * ureg.kN,
        "step": {
            "desc": "Block Shear Rupture",
            "ref": "AISC J4.3 / CSA 13.11",
            "symbol": r"V_r = \phi_u [ 0.6 F_u A_{nv} + U_{bs} F_u A_{nt} ]",
            "sub": f"V_r = {phi} [ 0.6({Fu_elem:.0f})({Anv:.0f}) + (1.0)({Fu_elem:.0f})({Ant:.0f}) ]",
            "result": f"{Vr:.2f} \\text{{ kN}}"
        }
    }