import sys
import os

# SETUP PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, repo_root)

from mech_core.units import ureg
from mech_core.components.aisc_members import get_shapes_by_type, get_section
from mech_core.standards.materials import get_material, get_concrete
from mech_core.analysis.columns import calculate_compressive_strength
from mech_core.analysis.beams import calculate_bending_capacity
from mech_core.analysis.base_plate import BasePlateDesign
from mech_core.analysis.fea import FrameAnalysis
from mech_core.standards.reporting.generator import ReportGenerator

def design_mezzanine():
    # 1. INIT REPORT
    rep = ReportGenerator("Mezzanine Structural Design", "Carter Frostad")
    rep.add_header()
    rep.add_text("Design based on CSA S16 (LSD). Loads extracted from NBCC 2020.")

    # 2. SETUP
    steel_beams = get_material("ASTM A36")
    steel_cols  = get_material("CSA G40.21 350W")
    concrete    = get_concrete(25)
    
    area = (4 * ureg.m) * (4 * ureg.m)
    live_load = (500 * ureg.kg / ureg.m**2) * 9.81 * ureg.m/ureg.s**2 * area
    P_factored = 1.5 * live_load
    
    rep.add_section("Design Loads")
    rep.add_text(f"**Total Factored Load:** {P_factored.to(ureg.kN):.2f~}")

    # 3. BEAM DESIGN
    w_beam = (P_factored / 2) / (4 * ureg.m)

    candidates = get_shapes_by_type("C", sort_by="W")
    best_beam = None
    best_frame = None

    print("Optimizing Beam...")
    for name in candidates:
        sec = get_section(name)

        # Create FEA model
        frame = FrameAnalysis()
        frame.add_node("N1", 0, 0, 0)
        frame.add_node("N2", 4*ureg.m, 0, 0)
        frame.add_beam("B1", "N1", "N2", sec, steel_beams)

        # Apply pinned-pinned supports (fix translations)
        frame.add_support("N1", "pinned")
        frame.add_support("N2", "pinned")

        # Apply distributed load (negative Fy direction)
        frame.add_member_dist_load("B1", "Fy", -w_beam, -w_beam)

        # Solve
        frame.solve()

        # Get max moment
        forces = frame.get_beam_forces("B1")
        Mu_fea = max(abs(forces['max_moment_z'].magnitude), abs(forces['min_moment_z'].magnitude)) * ureg.kN * ureg.meter

        # Check capacity
        res = calculate_bending_capacity(sec, steel_beams, unbraced_length=4*ureg.m)
        if res['Mu_capacity'] >= Mu_fea:
            best_beam = name

            # --- GENERATE DIAGRAMS ---
            diag_filename = os.path.join(current_dir, "beam_diagrams.png")
            frame.generate_diagrams("B1", diag_filename, direction="strong_axis")

            # --- REPORTING ---
            rep.add_section("Beam Selection (FEA Verified)")
            rep.add_text(f"Selected **{name}** based on FEA results.")

            # 1. Show the Diagram
            rep.add_image("Shear and Moment Diagrams", "beam_diagrams.png")

            # 2. Show the Wolfram Proof (The Symbolic Math)
            if 'calc_trace' in res:
                rep.add_symbolic_derivation(f"Design Check: {name}", res['calc_trace'])

            # 3. Show the Summary Table (Fixing the Red X)
            # We explicitly say status="PASS" because we checked it in the 'if' statement above
            rep.add_calculation_result(f"Beam Summary: {name}", res, status="PASS")
            break
            
    # 4. COLUMN DESIGN
    P_col = P_factored / 4
    col_h = 3 * ureg.m
    col_candidates = get_shapes_by_type("W", sort_by="W")
    best_col = None
    
    print("Optimizing Column...")
    for name in col_candidates:
        sec = get_section(name)
        res = calculate_compressive_strength(sec, steel_cols, col_h, ["pinned", "pinned"])
        if res['Pu_capacity'] >= P_col:
            best_col = name

            # --- REPORTING ---
            rep.add_section("Column Selection")
            rep.add_text(f"Selected **{name}** for main columns.")

            # 1. Show the Wolfram Proof (The Symbolic Math)
            if 'calc_trace' in res:
                rep.add_symbolic_derivation(f"Column Design Check: {name}", res['calc_trace'])

            # 2. Show the Summary Table
            rep.add_calculation_result(f"Column Check: {name}", res, status="PASS")

            print(f"-> Selected Column: {name} (Capacity: {res['Pu_capacity']:.2f})")
            break
            
    # 5. BASE PLATE DESIGN
    if best_col:
        print("Designing Base Plate...")
        col_sec = get_section(best_col)
        bp = BasePlateDesign(
            column=col_sec, 
            load_Pu=P_col, 
            steel_grade=steel_beams, 
            concrete=concrete
        )
        # ADD TO REPORT (The module knows how to format itself)
        rep.add_section("Base Plate Design")
        rep.add_module(bp)

    # 6. SAVE
    output_path = os.path.join(current_dir, "Mezzanine_Calc_Package.md")
    rep.save(output_path)

if __name__ == "__main__":
    design_mezzanine()