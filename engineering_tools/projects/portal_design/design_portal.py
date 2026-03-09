
import sys
import os
import math

# SETUP PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, repo_root)

from mech_core.standards.units import ureg
from mech_core.components.members.aisc import get_shapes_by_type, get_section
from mech_core.standards.materials import get_material, get_concrete
from mech_core.standards.structural.csa_s16.members import check_compressive_resistance, check_flexural_resistance, check_torsional_resistance
from mech_core.components.connections.axial.base_plate import BasePlateDesign
from mech_core.analysis.fea import FrameAnalysis
from mech_core.standards.reporting.generator import ReportGenerator

# --- NEW IMPORTS FOR CONNECTIONS ---
from mech_core.components.connections.shear.fin_plate import FinPlateConnection
from mech_core.components.fastener import create_standard_bolt

def design_portal_frame():
    """
    Design a portal frame (2 columns + 1 beam) with fixed connections.
    Includes explicit checks for:
    1. Operating Accuracy (Stiffness/Twist) against Tolerance.
    2. E-Stop Survival (Strength) against AISC Yielding.
    """
    
    # =========================================================================
    # 1. CONFIGURATION - INPUTS
    # =========================================================================
    
    # Frame Geometry
    BEAM_SPAN = 3 * ureg.m          
    COLUMN_HEIGHT = 2 * ureg.m       
    
    # E-STOP LOADS (Worst Case Datasheet Values)
    # These are the raw maximum loads experienced during an E-Stop.
    E_STOP_LOADS = {
        'Fy': -27.44 * ureg.kN,       # Vertical (down)
        'Fx': 25.48 * ureg.kN,        # Horizontal (+Z into page / +X in FEA) - Updated to match prior script logic
        'Mx': 38.22 * ureg.kN * ureg.m, # Torsion
        'Mz': 16.66 * ureg.kN * ureg.m  # Bending Moment (Perpendicular)
    }

    # OPERATING PARAMETERS
    # Robot Physical Config
    Robot_Reach = 2.04 * ureg.m 
    Tolerance = 0.000025 * ureg.m # 1/1000 inch approx (microns)
    
    # FACTORS
    SAFETY_FACTOR = 1.5           # Multiplier for E-Stop loads (Strength Check)
    OPERATING_RATIO = 0.60        # Multiplier on E-Stop loads for Regular Operation (Stiffness Check)

    # Material Selection
    steel_beams = get_material("ASTM A36")
    steel_cols = get_material("ASTM A36")
    concrete = get_concrete(25)
    
    # Section Types to Consider (Lists)
    BEAM_SHAPE_TYPES = ["W", "HSS"]   
    COLUMN_SHAPE_TYPES = ["W", "HSS"]
    
    # =========================================================================
    # 2. INITIALIZE REPORT
    # =========================================================================
    
    rep = ReportGenerator("Portal Frame Structural Design", "Carter Frostad")
    rep.add_header()
    rep.add_text("Design based on CSA S16 (LSD). Evaluates both Operating Accuracy (Stiffness) and E-Stop Survival (Strength).")
    
    rep.add_section("Design Criteria")
    rep.add_text(f"**Safety Factor (Strength):** {SAFETY_FACTOR}")
    rep.add_text(f"**Operating Ratio (Stiffness):** {OPERATING_RATIO*100:.0f}% of E-Stop Loads")
    rep.add_text(f"**TCP Accuracy Tolerance:** {Tolerance.to(ureg.mm):.4f~}")
    
    # =========================================================================
    # 3. GET CANDIDATE SECTIONS
    # =========================================================================
    
    beam_candidates = []
    for stype in BEAM_SHAPE_TYPES:
        beam_candidates.extend(get_shapes_by_type(stype, sort_by="W"))
    # Re-sort combined list by weight
    beam_candidates.sort(key=lambda x: get_section(x).W.magnitude)
        
    col_candidates = []
    for stype in COLUMN_SHAPE_TYPES:
        col_candidates.extend(get_shapes_by_type(stype, sort_by="W"))
    col_candidates.sort(key=lambda x: get_section(x).W.magnitude)
    
    # =========================================================================
    # 4. OPTIMIZATION LOOP
    # =========================================================================
    
    best_solution = None
    best_total_weight = float('inf') * ureg.kg
    
    print("=" * 60)
    print("PORTAL FRAME OPTIMIZATION (Two-Phase)")
    print("=" * 60)
    print(f"Testing {len(beam_candidates)} beams x {len(col_candidates)} columns")
    print("-" * 60)
    
    g = 9.81 * ureg.m / ureg.s**2
    iteration = 0
    
    # Define Load Sets
    op_loads = {k: v * OPERATING_RATIO for k, v in E_STOP_LOADS.items()}
    str_loads = {k: v * SAFETY_FACTOR for k, v in E_STOP_LOADS.items()}
    
    for i, beam_name in enumerate(beam_candidates):
        if i % 5 == 0: # Print every 5th beam to reduce clutter slightly, or every one
            print(f"[{i+1}/{len(beam_candidates)}] Checking Beam: {beam_name}...")

        beam_sec = get_section(beam_name)
        
        # Check if shape has Torsion properties (HSS might be missing Cw)
        # We need J (Torsional Constant)
        prop_J = getattr(beam_sec, 'J', None)

        if prop_J is None:
            # Skip shapes that can't be analyzed for torsion accurately
            continue

        # Beam Weights
        # beam_sec.W is already a Quantity (kg/m). Use .to() to enforce/verify units explicitly.
        beam_weight_per_m = beam_sec.W.to(ureg.kg / ureg.m)
        beam_total_weight = beam_weight_per_m * BEAM_SPAN
        w_beam_self = beam_weight_per_m * g
        
        # -----------------------------------------------------------------
        # PHASE 1: STIFFNESS CHECK (Operating Accuracy)
        # -----------------------------------------------------------------
        
        # 1.a Twist Angle Calculation (Analytic)
        try:
            twist_res = check_torsional_resistance(
                beam_sec, 
                op_loads['Mx'], 
                BEAM_SPAN, 
                steel_beams
            )
        except Exception:
            # Skip if math error (e.g. invalid props)
            continue
            
        theta_rad = twist_res['theta_rad']
        
        # 1.b Deflection Calculation (FEA - simplified beam only or estimated?)
        # To get accurate linear deflection at the robot mount (Mid-span), we need to consider column flexibility.
        # But iterating columns inside Phase 1 is expensive if we do full FEA every time.
        # Strategy: Do full loop.
        
        for col_name in col_candidates:
            iteration += 1
            col_sec = get_section(col_name)
            
            # Weight Checks
            col_weight_per_m = col_sec.W.to(ureg.kg / ureg.m)
            col_total_weight = col_weight_per_m * COLUMN_HEIGHT * 2
            total_weight = beam_total_weight + col_total_weight
            
            if total_weight >= best_total_weight:
                continue

            # --- BUILD PRE-CHECK FEA (Operating Loads) ---
            # We need the deflection at the center node (N3)
            # This is relatively fast.
            
            frame_op = FrameAnalysis()
            H_val = COLUMN_HEIGHT.to(ureg.m).magnitude
            L_val = BEAM_SPAN.to(ureg.m).magnitude
            
            frame_op.add_node("N1", 0, 0, 0)
            frame_op.add_node("N2", 0, H_val, 0)
            frame_op.add_node("N3", L_val/2, H_val, 0)
            frame_op.add_node("N4", L_val, H_val, 0)
            frame_op.add_node("N5", L_val, 0, 0)
            
            frame_op.add_beam("COL_L", "N1", "N2", col_sec, steel_cols)
            frame_op.add_beam("BEAM_L", "N2", "N3", beam_sec, steel_beams) # Split beam
            frame_op.add_beam("BEAM_R", "N3", "N4", beam_sec, steel_beams)
            frame_op.add_beam("COL_R", "N4", "N5", col_sec, steel_cols)
            
            frame_op.add_support("N1", "fixed")
            frame_op.add_support("N5", "fixed")
            
            # Apply Operating Loads at N3
            frame_op.add_node_load("N3", 
                Fy=op_loads['Fy'], 
                Fx=op_loads['Fx'], # Assuming Fx is lateral 
                Mx=op_loads['Mx'], 
                Mz=op_loads['Mz']
            )
            
            # Self weight causes deflection too, strictly speaking. Include it.
            frame_op.add_member_dist_load("BEAM_L", "Fy", -w_beam_self, -w_beam_self)
            frame_op.add_member_dist_load("BEAM_R", "Fy", -w_beam_self, -w_beam_self)
            
            try:
                frame_op.solve()
            except Exception as e:
                # print(f"Solver failed for {beam_name}/{col_name}: {e}")
                continue
                
            # EXTRACT DISPLACEMENTS AT N3
            node_n3 = frame_op.model.nodes["N3"]
            
            # DEBUG: Check keys
            result_key = 'Case 1'
            if 'Case 1' not in node_n3.DY:
                if 'Combo 1' in node_n3.DY:
                    result_key = 'Combo 1'
                else:
                    # Fallback / Error
                    # print(f"DEBUG: No valid results. Keys: {node_n3.DY.keys()}")
                    continue
                
            # DispX = node_n3.DX, DispY = node_n3.DY
            delta_vertical = abs(node_n3.DY[result_key]) * ureg.m
            delta_horizontal = abs(node_n3.DX[result_key]) * ureg.m
            delta_linear = math.sqrt(delta_vertical.magnitude**2 + delta_horizontal.magnitude**2) * ureg.m
            
            # TCP Deviation due to Twist
            # Deviation = Theta * Reach
            delta_twist = (theta_rad * ureg.rad) * Robot_Reach
            
            # Total Deviation (Vector Sum of Tip Movement)
            # Assumption: Twist moves tip perpendicular to arm. Arm is assumed sticking out?
            # Worst case summation:
            total_deviation = math.sqrt(delta_linear.magnitude**2 + delta_twist.magnitude**2) * ureg.m
            
            # STIFFNESS CHECK
            if total_deviation > Tolerance:
                # Too flexible
                # Optimization: Since beam torsion is main driver of twist, and beam bending is main driver of vertical,
                # we are likely failing.
                continue
            
            # -----------------------------------------------------------------
            # PHASE 2: STRENGTH CHECK (E-Stop Survival)
            # -----------------------------------------------------------------
            
            # Re-run FEA with Factored Loads (Safety Factor)
            frame_str = FrameAnalysis()
            frame_str.add_node("N1", 0, 0, 0)
            frame_str.add_node("N2", 0, H_val, 0)
            frame_str.add_node("N3", L_val/2, H_val, 0)
            frame_str.add_node("N4", L_val, H_val, 0)
            frame_str.add_node("N5", L_val, 0, 0)
            
            frame_str.add_beam("COL_L", "N1", "N2", col_sec, steel_cols)
            frame_str.add_beam("BEAM_L", "N2", "N3", beam_sec, steel_beams) 
            frame_str.add_beam("BEAM_R", "N3", "N4", beam_sec, steel_beams)
            frame_str.add_beam("COL_R", "N4", "N5", col_sec, steel_cols)
            
            frame_str.add_support("N1", "fixed")
            frame_str.add_support("N5", "fixed")
            
            # Apply FACTORED Loads
            frame_str.add_node_load("N3", 
                Fy=str_loads['Fy'], 
                Fx=str_loads['Fx'], 
                Mx=str_loads['Mx'], 
                Mz=str_loads['Mz']
            )
            
            # Self weight (factored? usually Dead Load factor 1.25, but let's effectively use SF applied to everything for simplicity/conservative)
            w_self_factored = w_beam_self * SAFETY_FACTOR
            frame_str.add_member_dist_load("BEAM_L", "Fy", -w_self_factored, -w_self_factored)
            frame_str.add_member_dist_load("BEAM_R", "Fy", -w_self_factored, -w_self_factored)
            
            try:
                frame_str.solve()
            except:
                continue

            # 2.a Check Beam Strength
            beam_forces_L = frame_str.get_beam_forces("BEAM_L")
            beam_forces_R = frame_str.get_beam_forces("BEAM_R")
            
            Mu_beam = max(
                abs(beam_forces_L['max_moment_z'].magnitude), abs(beam_forces_R['max_moment_z'].magnitude)
            ) * ureg.kN * ureg.m
            
            beam_flex_res = check_flexural_resistance(beam_sec, steel_beams, BEAM_SPAN/2)
            
            if beam_flex_res['Mu_capacity'] < Mu_beam:
                continue
                
            # 2.b Check Torsion Strength (Warping Stress)
            # Helper provided stress values for Factored Torsion
            twist_str_res = check_torsional_resistance(beam_sec, str_loads['Mx'], BEAM_SPAN, steel_beams)
            sigma_w = twist_str_res['sigma_warping']
            
            # Check Combined Stress roughly: (Mu/Mn) + (Sigma_w / Fy) <= 1.0 (Conservative simplified check)
            # Actually, standard is Stress(Mu) + Stress(Twist) < Fy
            # Stress(Mu) = Mu / Sx
            Sx = beam_sec.Sx.to(ureg.m**3)
            sigma_b = (Mu_beam / Sx).to(ureg.Pa)
            
            Fy = steel_beams.yield_strength.to(ureg.Pa)
            
            if (sigma_b + sigma_w) > (0.9 * Fy): # 0.9 Phi factor
                continue 
                
            # 2.c Check Column Strength (Axial + Bending)
            col_forces = frame_str.get_beam_forces("COL_L") # Assume symmetry roughly
            Mu_col = max(abs(col_forces['max_moment_z'].magnitude), abs(col_forces['min_moment_z'].magnitude)) * ureg.kNm
            
            # Get axial (Manual sum? PyNite forces?)
            # Simplified: Reaction at support roughly P_factored / 2
            # Let's get actuals if possible. frame_str doesn't easy expose axial yet in 'get_beam_forces'
            # Estimate:
            Pu_col = (abs(str_loads['Fy']) + w_self_factored * BEAM_SPAN) / 2
            
            col_comp_res = check_compressive_resistance(col_sec, steel_cols, COLUMN_HEIGHT, ["fixed", "fixed"])
            col_flex_res = check_flexural_resistance(col_sec, steel_cols, COLUMN_HEIGHT)
            
            util_col = (Pu_col / col_comp_res['Pu_capacity']) + (Mu_col / col_flex_res['Mu_capacity'])
            
            if util_col > 1.0:
                continue
                
            # SUCCESS
            print(f"  > PASSED: {beam_name} + {col_name} (Wt: {total_weight.to(ureg.kg):.1f~})")
            
            if total_weight < best_total_weight:
                best_total_weight = total_weight
                best_solution = {
                    'beam': beam_name,
                    'col': col_name,
                    'weight': total_weight,
                    'dev_total': total_deviation,
                    'dev_twist': delta_twist,
                    'dev_lin': delta_linear,
                    'util_col': util_col,
                    'sigma_b': sigma_b,
                    'sigma_w': sigma_w,
                    'frame_str': frame_str
                }
                
    # =========================================================================
    # 5. REPORTING
    # =========================================================================
    
    if best_solution:
        print("\n" + "="*60)
        print("OPTIMAL SOLUTION FOUND")
        print("="*60)
        print(f"Beam:   {best_solution['beam']}")
        print(f"Column: {best_solution['col']}")
        print(f"Total Weight: {best_solution['weight']:.1f~}")
        print(f"Total Deviation: {best_solution['dev_total'].to(ureg.mm):.4f~} (Limit: {Tolerance.to(ureg.mm):.4f~})")
        print(f"  - Twist Comp: {best_solution['dev_twist'].to(ureg.mm):.4f~}")
        print(f"  - Linear Comp: {best_solution['dev_lin'].to(ureg.mm):.4f~}")
        
        rep.add_section("Selected Members")
        rep.add_text(f"**Beam:** {best_solution['beam']}")
        rep.add_text(f"**Columns:** {best_solution['col']}")
        rep.add_text(f"**Total Weight:** {best_solution['weight']:.2f~}")
        
        rep.add_section("Stiffness Verification (Operating)")
        rep.add_text(f"**Calculated Deviation:** {best_solution['dev_total'].to(ureg.mm):.4f~}")
        rep.add_text(f"**Tolerance Limit:** {Tolerance.to(ureg.mm):.4f~}")
        rep.add_text(f"  - Linear Deflection (FEA): {best_solution['dev_lin'].to(ureg.mm):.4f~}")
        rep.add_text(f"  - Twist Deviation (Roark): {best_solution['dev_twist'].to(ureg.mm):.4f~}")
        
        rep.add_section("Strength Verification (E-Stop)")
        rep.add_text(f"**Combined Beam Stress:** {(best_solution['sigma_b'] + best_solution['sigma_w']).to(ureg.MPa):.2f~}")
        rep.add_text(f"  - Bending Stress: {best_solution['sigma_b'].to(ureg.MPa):.2f~}")
        rep.add_text(f"  - Warping Stress: {best_solution['sigma_w'].to(ureg.MPa):.2f~}")
        rep.add_text(f"**Column Utilization:** {best_solution['util_col']:.1%}")

        # Diagrams
        diag_path = os.path.join(current_dir, "solution_diagrams.png")
        best_solution['frame_str'].generate_diagrams("BEAM_L", diag_path)
        rep.add_image("Beam Force Diagrams (E-Stop Case)", "solution_diagrams.png")
        
        out_path = os.path.join(current_dir, "Portal_Frame_Design.md")
        rep.save(out_path)
        print(f"Report saved to {out_path}")
    else:
        print("No valid solution found.")
        print("-" * 60)
        print("DIAGNOSTIC: Analyzing Heaviest Combination (Best Chance)")
        print("-" * 60)
        
        # Try the heaviest beam and heaviest column
        if beam_candidates and col_candidates:
            beam_name = beam_candidates[-1]
            col_name = col_candidates[-1]
            
            print(f"Testing: {beam_name} + {col_name}")
            beam_sec = get_section(beam_name)
            col_sec = get_section(col_name)
            
            # 1. Check Stiffness
            # (Copying logic briefly for diagnostic - ideally refactor to function, but inline is fine for this report)
            prop_J = getattr(beam_sec, 'J', None)
            if prop_J:
                try:
                    twist_res = check_torsional_resistance(beam_sec, op_loads['Mx'], BEAM_SPAN, steel_beams)
                    theta_rad = twist_res['theta_rad']
                    
                    frame_op = FrameAnalysis()
                    H_val = COLUMN_HEIGHT.to(ureg.m).magnitude
                    L_val = BEAM_SPAN.to(ureg.m).magnitude
                    frame_op.add_node("N1", 0, 0, 0)
                    frame_op.add_node("N2", 0, H_val, 0)
                    frame_op.add_node("N3", L_val/2, H_val, 0)
                    frame_op.add_node("N4", L_val, H_val, 0)
                    frame_op.add_node("N5", L_val, 0, 0)
                    frame_op.add_beam("COL_L", "N1", "N2", col_sec, steel_cols)
                    frame_op.add_beam("BEAM_L", "N2", "N3", beam_sec, steel_beams) 
                    frame_op.add_beam("BEAM_R", "N3", "N4", beam_sec, steel_beams)
                    frame_op.add_beam("COL_R", "N4", "N5", col_sec, steel_cols)
                    frame_op.add_support("N1", "fixed")
                    frame_op.add_support("N5", "fixed")
                    frame_op.add_node_load("N3", Fy=op_loads['Fy'], Fx=op_loads['Fx'], Mx=op_loads['Mx'], Mz=op_loads['Mz'])
                    frame_op.solve()
                    
                    node_n3 = frame_op.model.nodes["N3"]
                    
                    # DEBUG: Check keys
                    result_key = 'Case 1'
                    if 'Case 1' not in node_n3.DY:
                        if 'Combo 1' in node_n3.DY:
                            result_key = 'Combo 1'
                        else:
                            print(f"    -> ERROR: No valid result keys found: {node_n3.DY.keys()}")
                            return

                    delta_vertical = abs(node_n3.DY[result_key]) * ureg.m
                    delta_horizontal = abs(node_n3.DX[result_key]) * ureg.m
                    delta_linear = math.sqrt(delta_vertical.magnitude**2 + delta_horizontal.magnitude**2) * ureg.m
                    delta_twist = (theta_rad * ureg.rad) * Robot_Reach
                    total_deviation = math.sqrt(delta_linear.magnitude**2 + delta_twist.magnitude**2) * ureg.m
                    
                    print(f"  Stiffness Check:")
                    print(f"    Total Deviation: {total_deviation.to(ureg.mm):.4f~}")
                    print(f"      - Linear: {delta_linear.to(ureg.mm):.4f~}")
                    print(f"      - Twist:  {delta_twist.to(ureg.mm):.4f~}")
                    print(f"    Limit: {Tolerance.to(ureg.mm):.4f~}")
                    if total_deviation > Tolerance:
                        print("    -> FAILS STIFFNESS")
                    else:
                        print("    -> PASSES STIFFNESS")
                        
                except Exception as e:
                    print(f"  Stiffness Analysis Failed: {e}")
            else:
                print("  Skipped (No J property)")

if __name__ == "__main__":
    design_portal_frame()