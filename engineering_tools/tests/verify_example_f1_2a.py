import sys
import os

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, repo_root)

from mech_core.units import ureg
from mech_core.components.aisc_members import get_section
from mech_core.standards.materials import get_material
from mech_core.analysis.beams import calculate_bending_capacity

def verify_example_f1_2a():
    print("=== Verifying AISC Example F.1-2A ===")
    print("Goal: Check W18x50 at Lb = 11.7 ft (Third point of 35ft span)")
    print("Target (AISC Chart Reading): ~302 kip-ft")
    
    # 1. SETUP
    section = get_section("W18X50")
    
    # Material: ASTM A992 (50 ksi)
    # We create a proxy if not in your DB, or fetch it
    try:
        steel = get_material("ASTM A992")
    except:
        print("Using generic 50ksi steel...")
        class MatProxy:
            yield_strength = 50 * ureg.ksi
            elastic_modulus = 29000 * ureg.ksi
        steel = MatProxy()

    # 2. INPUTS FROM EXAMPLE
    # "Unbraced Length = 35/3 = 11.7 ft"
    # "Conservatively neglect Cb (Cb=1.0)"
    Lb = 11.7 * ureg.ft
    Cb = 1.0 

    # 3. RUN CALCULATION
    res = calculate_bending_capacity(section, steel, Lb, cb=Cb)
    
    # 4. COMPARE
    phi_Mn = res['Mu_capacity'].to(ureg.kip * ureg.ft)
    
    print(f"\n--- RESULTS ---")
    print(f"Beam:             {section.name}")
    print(f"Unbraced Length:  {Lb}")
    print(f"Zone:             {res['ltb_zone']}")
    print("-" * 30)
    print(f"AISC Manual Approx:  302.0 kip-ft")
    print(f"Python Calculated:   {phi_Mn:.1f}")
    
    # Check deviation
    diff = abs(phi_Mn.magnitude - 302.0)
    percent = (diff / 302.0) * 100
    
    print(f"Difference:          {percent:.2f}%")
    
    if percent < 2.0:
        print("\n[SUCCESS] Calculated value matches AISC Example within 2%.")
        print("Your tool is more accurate than reading the chart by eye!")
    else:
        print("\n[CHECK] Deviation > 2%. Check if Cb or Material props differ.")

if __name__ == "__main__":
    verify_example_f1_2a()