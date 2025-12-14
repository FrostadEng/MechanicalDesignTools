import sys
import os

# SETUP PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, repo_root)

from mech_core.standards.units import ureg
from mech_core.components.members.aisc import get_shapes_by_type, get_section
from mech_core.standards.materials import get_material, get_concrete
from mech_core.codes.structural.csa_s16.members import check_compressive_resistance, check_flexural_resistance
from mech_core.components.connections.axial.base_plate import BasePlateDesign
from mech_core.analysis.fea import FrameAnalysis
from mech_core.standards.reporting.generator import ReportGenerator

# --- NEW IMPORTS FOR CONNECTIONS ---
from mech_core.components.connections.shear.fin_plate import FinPlateConnection
from mech_core.components.fastener import create_standard_bolt

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
    design_shear_Vf = None # <--- NEW VARIABLE TO STORE SHEAR

    print("Optimizing Beam...")
    for name in candidates:
        sec = get_section(name)

        # Create FEA model (Same as before)
        frame = FrameAnalysis()
        frame.add_node("N1", 0, 0, 0)
        frame.add_node("N2", 4*ureg.m, 0, 0)
        frame.add_beam("B1", "N1", "N2", sec, steel_beams)
        frame.add_support("N1", "pinned")
        frame.add_support("N2", "pinned")
        frame.add_member_dist_load("B1", "Fy", -w_beam, -w_beam)
        frame.solve()

        # Get forces
        forces = frame.get_beam_forces("B1")
        Mu_fea = max(abs(forces['max_moment_z'].magnitude), abs(forces['min_moment_z'].magnitude)) * ureg.kN * ureg.meter
        
        # --- NEW: CAPTURE SHEAR ---
        # We need the max shear to design the connection
        Vf_fea = max(abs(forces['max_shear_y'].magnitude), abs(forces['min_shear_y'].magnitude)) * ureg.kN

        # Check capacity
        res = check_flexural_resistance(sec, steel_beams, unbraced_length=4*ureg.m)
        if res['Mu_capacity'] >= Mu_fea:
            best_beam = name
            design_shear_Vf = Vf_fea # <--- SAVE IT

            # --- GENERATE DIAGRAMS ---
            diag_filename = os.path.join(current_dir, "beam_diagrams.png")
            frame.generate_diagrams("B1", diag_filename, direction="strong_axis")

            # --- REPORTING ---
            rep.add_section("Beam Selection (FEA Verified)")
            rep.add_text(f"Selected **{name}** based on FEA results.")
            
            # Report the Shear Force for reference
            rep.add_text(f"**Max Factored Shear (Vf):** {design_shear_Vf:.2f~}")

            rep.add_image("Shear and Moment Diagrams", "beam_diagrams.png")

            if 'calc_trace' in res:
                rep.add_symbolic_derivation(f"Design Check: {name}", res['calc_trace'])

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
        res = check_compressive_resistance(sec, steel_cols, col_h, ["pinned", "pinned"])
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

    # 5. SHEAR CONNECTION DESIGN
    if best_beam and best_col and design_shear_Vf:
        print(f"\n... Designing Connection: {best_beam} -> {best_col} ...")
        
        beam_sec = get_section(best_beam)
        col_sec = get_section(best_col)
        
        # --- 1. DEFINE GEOMETRY (The Physical Object) ---
        
        # Bolt Specification (Dict, not Object, per new API)
        bolt_spec = {
            'diameter': 20 * ureg.mm,
            'grade': '8.8' # Metric structural grade
        }
        
        # Pattern Layout
        bolt_pattern = {
            'rows': 2,
            'spacing': 75 * ureg.mm,
            'edge_v': 35 * ureg.mm,
            'edge_h': 40 * ureg.mm
        }
        
        # Calculate Plate Dimensions based on bolts
        # Height = (Rows - 1) * Spacing + 2 * Vertical Edge
        p_height = (bolt_pattern['rows'] - 1) * bolt_pattern['spacing'] + 2 * bolt_pattern['edge_v']
        
        conn = FinPlateConnection(
            beam=beam_sec,
            column=col_sec,
            plate_thickness=10 * ureg.mm, # Initial guess
            plate_depth=p_height,
            plate_material=steel_beams,   # Reuse our A36 material object
            beam_material=steel_beams,    # The beam is A36
            bolt_pattern=bolt_pattern,
            bolt_spec=bolt_spec
        )
        
        # --- 2. RUN ANALYSIS (The Code Check) ---
        # We inject the load HERE, not in __init__
        conn_res = conn.analyze(factored_shear=design_shear_Vf, code='csa_s16')
        
        # 3. REPORTING
        rep.add_section("Beam-to-Column Connection")
        rep.add_text(f"Designing shear tab for **{best_beam}** connecting to **{best_col}**.")
        rep.add_text(f"**Design Shear Force (Vf):** {design_shear_Vf:.2f~}")
        
        # Bolt Shear Trace
        if 'bolt_shear' in conn_res and 'calc_trace' in conn_res['bolt_shear']:
             rep.add_symbolic_derivation("Check 1: Bolt Shear", conn_res['bolt_shear']['calc_trace'])

        # Bearing Trace
        if 'bearing' in conn_res and 'calc_trace' in conn_res['bearing']:
             rep.add_symbolic_derivation("Check 2: Bearing", conn_res['bearing']['calc_trace'])
             
        # Block Shear Trace (NEW)
        if 'block_shear' in conn_res and 'calc_trace' in conn_res['block_shear']:
             rep.add_symbolic_derivation("Check 3: Block Shear Rupture", conn_res['block_shear']['calc_trace'])
        
        status_icon = "✅" if conn_res.get('overall_status') == "PASS" else "❌"
        rep.add_text(f"> **Overall Connection Status:** {status_icon} {conn_res.get('overall_status')}")
        rep.add_text(f"> **Critical Mode:** {conn_res.get('critical_mode')}")


    # 6. BASE PLATE DESIGN
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