import sys
import os

# Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, repo_root)

from mech_core.standards.units import ureg
from mech_core.components.members.aisc import get_section
from mech_core.standards.materials import get_material
from mech_core.codes.structural.csa_s16.members import check_compressive_resistance

def run_design():
    print("=== Mezzanine Column Design ===\n")

    # 1. DEFINE LOADS
    # 2000 kg per leg (Approx 19.6 kN)
    # Apply a Safety Factor for Dead+Live loads? 
    # In LRFD/LSD, we factor the load: 1.2D + 1.5L. 
    # Let's assume the 2000kg is the *Factored* load for this example.
    load_per_leg = 20 * ureg.kN 
    column_height = 3.0 * ureg.meter
    
    # 2. DEFINE MATERIAL
    # Standard Steel
    steel = get_material("ASTM A36")

    # 3. ITERATIVE SELECTION
    # Let's try a few candidates from our shiny new database
    candidates = ["HSS3X3X1/4", "HSS4X4X1/4", "W4X13", "W8X31"]
    
    print(f"Design Load: {load_per_leg}")
    print(f"Height:      {column_height}")
    print("-" * 60)
    print(f"{'Shape':<15} | {'KL/r':<10} | {'Capacity (kN)':<15} | {'Status'}")
    print("-" * 60)

    for shape_name in candidates:
        try:
            # Get properties
            section = get_section(shape_name)
            
            # Calculate Strength
            # K=1.0 (Pinned-Pinned assumption for simple bolted columns)
            # If you weld the base to concrete and the top to a rigid moment frame, K could be 0.5.
            # But for a "Table", K=2.0 (Cantilever) if unbraced, or K=1.0 if cross-braced.
            # Let's assume cross-braced (K=1.0).
            
            result = check_compressive_resistance(section, steel, column_height, ["pinned", "pinned"])
            
            capacity = result['Pu_capacity']
            slenderness = result['slenderness']
            
            # Check Status
            status = "PASS" if capacity > load_per_leg else "FAIL"
            
            print(f"{shape_name:<15} | {slenderness.magnitude:<10.2f} | {capacity.magnitude:<15.2f} | {status}")
            
        except ValueError as e:
            print(f"{shape_name:<15} | ERROR: {e}")

    print("-" * 60)
    print("\nDetailed Report for W4X13:")
    # Detailed look at one
    s = get_section("W4X13")
    res = check_compressive_resistance(s, steel, column_height)
    print(f"Mode: {res['failure_mode']}")
    print(f"Critical Stress Fcr: {res['Fcr']}")
    print(f"Governing Axis: {res['governing_axis']}")

if __name__ == "__main__":
    run_design()