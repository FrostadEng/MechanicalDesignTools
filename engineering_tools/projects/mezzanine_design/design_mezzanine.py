import sys
import os

# SETUP PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, repo_root)

from mech_core.units import ureg
from mech_core.components.aisc_members import get_section, get_shapes_by_type
from mech_core.standards.materials.structural import get_material
from mech_core.analysis.columns import calculate_compressive_strength
from mech_core.analysis.beams import calculate_strong_axis_bending

def design_mezzanine():
    print("=== MEZZANINE STRUCTURAL CALCULATION ===\n")
    
    # --- 1. LOADS ---
    width = 4.0 * ureg.meter
    length = 4.0 * ureg.meter
    area = width * length
    
    live_load_pressure = (500 * ureg.kg / ureg.meter**2) * 9.81 * ureg.meter/ureg.second**2
    total_load = live_load_pressure * area
    
    # LRFD Factors (National Building Code of Canada / ASCE 7)
    # 1.25 Dead + 1.5 Live (Standard Canada) or 1.2D + 1.6L (USA)
    # Let's assume the 500kg/m2 is the Live Load and Dead Load is negligible for this MVP.
    factored_load = total_load * 1.5 
    
    print(f"Total Factored Load: {factored_load.to(ureg.kN):.2f}")
    
    # --- 2. BEAM DESIGN (C-Channels) ---
    # Assumption: 2 Beams support the floor. Each takes half the load.
    # Uniform Distributed Load w (kN/m)
    w_dist = (factored_load / 2) / length
    
    # Max Moment (Simply Supported): M = wL^2 / 8
    M_max = (w_dist * length**2) / 8
    print(f"Beam Moment (Mu):    {M_max.to(ureg.kN * ureg.meter):.2f}")
    
    # Select Material
    steel = get_material("ASTM A36")
    
    # Beam Iteration - Get all C-channel shapes
    beam_candidates = get_shapes_by_type("C", sort_by="W")

    print("\n--- BEAM SELECTION (Unbraced L = 4m) ---")
    print(f"{'Shape':<10} | {'Mu Cap (kN-m)':<15} | {'Status':<30}")

    selected_beam = None

    for b_name in beam_candidates:
        sec = get_section(b_name)
        # Calculate Strength (Lb = 4.0m, unbraced)
        res = calculate_strong_axis_bending(sec, steel, unbraced_length=length)

        capacity = res['Mu_capacity']
        status = "PASS" if capacity >= M_max else "FAIL"

        # Only print if PASS or if first passing beam found
        if status == "PASS":
            print(f"{b_name:<10} | {capacity.magnitude:<15.2f} | {status} ({res['status']})")
            if selected_beam is None:
                selected_beam = b_name
                print(f"  --> Selected: {selected_beam}")
                break  # Stop after finding first adequate beam

    # --- 3. COLUMN DESIGN (W-Shapes) ---
    # Load per column = Total Load / 4
    P_col = factored_load / 4
    col_height = 3.0 * ureg.meter
    
    print(f"\n--- COLUMN SELECTION (Pu = {P_col.to(ureg.kN):.2f}) ---")

    # Column Iteration - Get all W-shape sections
    col_candidates = get_shapes_by_type("W", sort_by="W")

    selected_column = None

    for c_name in col_candidates:
        sec = get_section(c_name)
        # K=1.0 (Pinned-Pinned)
        res = calculate_compressive_strength(sec, steel, col_height, k_factor=1.0)

        capacity = res['Pu_capacity']
        status = "PASS" if capacity >= P_col else "FAIL"

        # Only print passing columns
        if status == "PASS":
            # Warning for slenderness
            note = ""
            if res['slenderness'] > 200:
                note = "(Slender!)"

            print(f"{c_name:<10} | {capacity.magnitude:<15.2f} | {status} {note}")

            if selected_column is None and res['slenderness'] <= 200:
                selected_column = c_name
                print(f"  --> Selected: {selected_column}")
                break  # Stop after finding first adequate column

    # --- SUMMARY ---
    print("\n" + "="*50)
    print("DESIGN SUMMARY")
    print("="*50)
    if selected_beam:
        print(f"Beams (C-Channel):  {selected_beam}")
    if selected_column:
        print(f"Columns (W-Shape):  {selected_column}")
    print(f"Material:           ASTM A36 Steel")
    print("="*50)

if __name__ == "__main__":
    design_mezzanine()