import sys
import os

# Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, repo_root)

from mech_core.units import ureg
from mech_core.components.aisc_members import get_section
from mech_core.standards.materials import get_material
from mech_core.analysis.beams import calculate_bending_capacity

def test_aisc_benchmark():
    print("=== AISC 15th Ed. Benchmark Test ===")
    print("Reference: Table 3-10 (W-Shapes Selection by Zx)")
    
    # 1. SETUP (Imperial Inputs)
    # W18x50 is a standard beam
    section = get_section("W18X50") 
    
    # ASTM A992 is the standard US Steel (50 ksi)
    # Ensure this exists in your structural.py, otherwise we make a temp one
    try:
        material = get_material("ASTM A992")
    except ValueError:
        print("Note: ASTM A992 not found, using generic 50ksi equivalent.")
        # Create a proxy object if needed
        class MatProxy:
            yield_strength = 50 * ureg.ksi
            elastic_modulus = 29000 * ureg.ksi
        material = MatProxy()

    # Test Case: 10 ft Unbraced Length
    Lb = 10.0 * ureg.ft
    Cb = 1.0 # Standard table assumption

    # 2. RUN CALCULATION (The Metric Engine)
    print(f"\nTesting: {section.name}")
    print(f"Material: Fy={material.yield_strength.to(ureg.ksi):.1f}")
    print(f"Length:   {Lb}")
    
    res = calculate_bending_capacity(section, material, Lb, cb=Cb)
    
    # 3. VERIFY OUTPUT
    # Convert our Metric result (kNm) back to Imperial (kip-ft) for comparison
    phi_Mn_calc = res['Mu_capacity'].to(ureg.kip * ureg.ft)
    
    # AISC Table 3-10 Value for W18x50 @ 10ft
    TRUTH_VALUE = 306.0 * ureg.kip * ureg.ft
    
    # Calculate Error
    error = abs(phi_Mn_calc - TRUTH_VALUE)
    percent_error = (error / TRUTH_VALUE) * 100
    
    print("\n--- RESULTS ---")
    print(f"AISC Table Value: {TRUTH_VALUE:.1f}")
    print(f"Our Python Calc:  {phi_Mn_calc:.1f}")
    print(f"Difference:       {percent_error.magnitude:.2f}%")
    
    # Check Zone Logic
    print(f"Zone Identified:  {res['ltb_zone']}")
    
    # Validation Logic (Allow < 2% difference due to unit rounding/constants)
    if percent_error < 2.0:
        print("\n[SUCCESS] Engine matches AISC Standards.")
    else:
        print("\n[FAILURE] Deviation too high. Check inputs or constants.")
        # Debug: Print the trace to see where it went wrong
        # for step in res['calc_trace']:
        #     print(step['desc'], step.get('result', ''))

if __name__ == "__main__":
    test_aisc_benchmark()