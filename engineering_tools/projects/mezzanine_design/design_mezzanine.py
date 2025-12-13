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
from mech_core.standards.reporting.generator import ReportGenerator

def design_mezzanine():
    # 1. INIT REPORT
    rep = ReportGenerator("Mezzanine Structural Design", "Your Name")
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
    M_max = (w_beam * (4 * ureg.m)**2) / 8
    
    candidates = get_shapes_by_type("C", sort_by="W")
    best_beam = None
    
    print("Optimizing Beam...")
    for name in candidates:
        sec = get_section(name)
        res = calculate_bending_capacity(sec, steel_beams, unbraced_length=4*ureg.m)
        if res['Mu_capacity'] >= M_max:
            best_beam = name
            # ADD TO REPORT
            rep.add_section("Beam Selection")
            rep.add_text(f"Selected **{name}** for perimeter beams.")
            rep.add_calculation_result(f"Beam Check: {name}", res, res['status'])
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
            # ADD TO REPORT
            rep.add_section("Column Selection")
            rep.add_text(f"Selected **{name}** for main columns.")
            rep.add_calculation_result(f"Column Check: {name}", res, "PASS")
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