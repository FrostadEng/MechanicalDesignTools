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

def design_portal_frame():
    """
    Design a portal frame (2 columns + 1 beam) with fixed connections.
    
    Loading at mid-span of beam:
    - P_v: Vertical force (downward)
    - P_h: Horizontal force 
    - M_t: Torsional moment (twisting the beam about its longitudinal axis)
    - M_z: Moment perpendicular to ground (twisting through beam into columns)
    
    Self-weight of members is automatically included.
    """
    
    # =========================================================================
    # 1. CONFIGURATION - MODIFY THESE VALUES
    # =========================================================================
    
    # Frame Geometry
    BEAM_SPAN = 3 * ureg.m          # Horizontal span between columns
    COLUMN_HEIGHT = 2 * ureg.m       # Height of columns
    
    # Applied Loads at Mid-Span (Factored)
    P_vertical = 27.44 * ureg.kN        # Vertical load (positive = downward)
    P_horizontal = 25.48 * ureg.kN      # Horizontal load (positive = +Z direction, into the page)
    M_torsion = 38.22 * ureg.kN * ureg.m # Torsion on beam (twisting about beam axis)
    M_perpendicular = 16.66 * ureg.kN * ureg.m  # Moment perpendicular to ground (about Z)

    # Robot Operational Loads
    Robot_Weight = 8.34 * ureg.kN #Dead Load of robot, not including payload, resulting static deflection is not an issue for this application because the TCP has be calibrated after deflection occured
    Payload_Weight = 0.6 * ureg.kN #Payload weight, resulting static deflection is not an issue for this application because the TCP has be calibrated after deflection occured
    Robot_Reach = 2.04 * ureg.m #Reach of robot
    Tolerance = 0.000025 * ureg.m #Tolerance for robot TCP calibration, deflection cannot make the TCP miss the target

    # Material Selection
    steel_beams = get_material("ASTM A36")
    steel_cols = get_material("ASTM A36")
    concrete = get_concrete(25)  # For base plate design
    
    # Section Types to Consider
    BEAM_SHAPE_TYPE = "W"    # W shapes for beams
    COLUMN_SHAPE_TYPE = "W"  # W shapes for columns
    
    # =========================================================================
    # 2. INITIALIZE REPORT
    # =========================================================================
    
    rep = ReportGenerator("Portal Frame Structural Design", "Carter Frostad")
    rep.add_header()
    rep.add_text("Design based on CSA S16 (LSD). Portal frame with fixed beam-column connections.")
    
    rep.add_section("Frame Configuration")
    rep.add_text(f"**Beam Span:** {BEAM_SPAN.to(ureg.m):.2f~}")
    rep.add_text(f"**Column Height:** {COLUMN_HEIGHT.to(ureg.m):.2f~}")
    
    rep.add_section("Applied Loads (at Mid-Span)")
    rep.add_text(f"**Vertical Force (P_v):** {P_vertical.to(ureg.kN):.2f~}")
    rep.add_text(f"**Horizontal Force (P_h):** {P_horizontal.to(ureg.kN):.2f~}")
    rep.add_text(f"**Torsional Moment (M_t):** {M_torsion.to(ureg.kN * ureg.m):.2f~}")
    rep.add_text(f"**Perpendicular Moment (M_z):** {M_perpendicular.to(ureg.kN * ureg.m):.2f~}")
    
    # =========================================================================
    # 3. GET CANDIDATE SECTIONS (sorted by weight - lightest first)
    # =========================================================================
    
    beam_candidates = get_shapes_by_type(BEAM_SHAPE_TYPE, sort_by="W")
    col_candidates = get_shapes_by_type(COLUMN_SHAPE_TYPE, sort_by="W")
    
    # =========================================================================
    # 4. OPTIMIZATION LOOP - Find lightest passing combination
    # =========================================================================
    
    best_solution = None
    best_total_weight = float('inf') * ureg.kg
    
    print("=" * 60)
    print("PORTAL FRAME OPTIMIZATION")
    print("=" * 60)
    print(f"Testing {len(beam_candidates)} beam sections x {len(col_candidates)} column sections")
    print("-" * 60)
    
    g = 9.81 * ureg.m / ureg.s**2  # Gravitational acceleration
    
    iteration = 0
    for beam_name in beam_candidates:
        beam_sec = get_section(beam_name)
        
        # Section weight property (already has units kg/m from AISC database)
        beam_weight_per_m = beam_sec.W * ureg.kg / ureg.m
        beam_total_weight = beam_weight_per_m * BEAM_SPAN
        
        # Beam self-weight as distributed load
        w_beam_self = beam_weight_per_m * g
        
        for col_name in col_candidates:
            iteration += 1
            col_sec = get_section(col_name)
            col_weight_per_m = col_sec.W * ureg.kg / ureg.m
            col_total_weight = col_weight_per_m * COLUMN_HEIGHT * 2  # Two columns
            
            # Column self-weight as point load at top
            P_col_self = col_weight_per_m * COLUMN_HEIGHT * g
            
            # Total frame weight
            total_weight = beam_total_weight + col_total_weight
            
            # Skip if already heavier than best solution
            if total_weight >= best_total_weight:
                continue
            
            # -----------------------------------------------------------------
            # BUILD FEA MODEL
            # -----------------------------------------------------------------
            
            frame = FrameAnalysis()
            
            # Nodes:
            # N1 = Base of left column (0, 0, 0)
            # N2 = Top of left column / left end of beam (0, H, 0)
            # N3 = Mid-span of beam (L/2, H, 0)
            # N4 = Top of right column / right end of beam (L, H, 0)
            # N5 = Base of right column (L, 0, 0)
            
            H = COLUMN_HEIGHT.to(ureg.m).magnitude
            L = BEAM_SPAN.to(ureg.m).magnitude
            
            frame.add_node("N1", 0, 0, 0)
            frame.add_node("N2", 0, H, 0)
            frame.add_node("N3", L/2, H, 0)  # Mid-span node for point loads
            frame.add_node("N4", L, H, 0)
            frame.add_node("N5", L, 0, 0)
            
            # Members:
            # Left Column: N1 -> N2 (vertical, along Y-axis)
            # Beam Left Half: N2 -> N3 (horizontal, along X-axis)
            # Beam Right Half: N3 -> N4 (horizontal, along X-axis)
            # Right Column: N4 -> N5 (vertical, along -Y direction)
            
            frame.add_beam("COL_L", "N1", "N2", col_sec, steel_cols)
            frame.add_beam("BEAM_L", "N2", "N3", beam_sec, steel_beams)
            frame.add_beam("BEAM_R", "N3", "N4", beam_sec, steel_beams)
            frame.add_beam("COL_R", "N4", "N5", col_sec, steel_cols)
            
            # Supports: Fixed at base
            frame.add_support("N1", "fixed")
            frame.add_support("N5", "fixed")
            
            # -----------------------------------------------------------------
            # APPLY LOADS (using keyword arguments per fea.py API)
            # -----------------------------------------------------------------
            
            # 1. Self-weight of beam (distributed load, -Y direction)
            frame.add_member_dist_load("BEAM_L", "Fy", -w_beam_self, -w_beam_self)
            frame.add_member_dist_load("BEAM_R", "Fy", -w_beam_self, -w_beam_self)
            
            # 2. Self-weight of columns (point load at beam-column joints)
            #    Column weight acts downward at the top of each column
            frame.add_node_load("N2", Fy=-P_col_self)
            frame.add_node_load("N4", Fy=-P_col_self)
            
            # 3. Applied vertical load at mid-span (downward = -Y)
            frame.add_node_load("N3", Fy=-P_vertical)
            
            # 4. Applied horizontal load at mid-span (+X direction)
            frame.add_node_load("N3", Fx=P_horizontal)
            
            # 5. Torsional moment on beam (Mx - about beam's longitudinal axis)
            #    For horizontal beam along X, torsion is about X-axis
            frame.add_node_load("N3", Mx=M_torsion)
            
            # 6. Moment perpendicular to ground (Mz - about vertical axis)
            #    This creates torsion that flows through the frame
            frame.add_node_load("N3", Mz=M_perpendicular)
            
            # -----------------------------------------------------------------
            # SOLVE
            # -----------------------------------------------------------------
            
            try:
                frame.solve()
            except Exception as e:
                print(f"  [{iteration}] {beam_name} + {col_name}: FEA FAILED - {e}")
                continue
            
            # -----------------------------------------------------------------
            # CHECK BEAM CAPACITY
            # -----------------------------------------------------------------
            
            # Get forces from both beam segments
            forces_L = frame.get_beam_forces("BEAM_L")
            forces_R = frame.get_beam_forces("BEAM_R")
            
            # Maximum moment in beam (about strong axis = Mz in PyNite convention)
            Mu_beam = max(
                abs(forces_L['max_moment_z'].magnitude),
                abs(forces_L['min_moment_z'].magnitude),
                abs(forces_R['max_moment_z'].magnitude),
                abs(forces_R['min_moment_z'].magnitude)
            ) * ureg.kN * ureg.m
            
            # Maximum shear in beam
            Vu_beam = max(
                abs(forces_L['max_shear_y'].magnitude),
                abs(forces_L['min_shear_y'].magnitude),
                abs(forces_R['max_shear_y'].magnitude),
                abs(forces_R['min_shear_y'].magnitude)
            ) * ureg.kN
            
            # Check beam flexural capacity
            # Unbraced length = half span (conservative - assumes mid-span is braced)
            beam_check = check_flexural_resistance(
                beam_sec, 
                steel_beams, 
                unbraced_length=BEAM_SPAN/2
            )
            
            if beam_check['Mu_capacity'] < Mu_beam:
                continue  # Beam fails, try next combination
            
            # -----------------------------------------------------------------
            # CHECK COLUMN CAPACITY
            # -----------------------------------------------------------------
            
            # Get forces from columns
            forces_col_L = frame.get_beam_forces("COL_L")
            forces_col_R = frame.get_beam_forces("COL_R")
            
            # Get axial forces (using helper function)
            axial_col_L = get_member_axial_forces(frame, "COL_L")
            axial_col_R = get_member_axial_forces(frame, "COL_R")
            
            # Maximum axial force in columns (compression is typically negative)
            Pu_col = max(
                abs(axial_col_L['max_axial'].magnitude),
                abs(axial_col_L['min_axial'].magnitude),
                abs(axial_col_R['max_axial'].magnitude),
                abs(axial_col_R['min_axial'].magnitude)
            ) * ureg.kN
            
            # Maximum moment in columns (strong axis = Mz)
            Mu_col = max(
                abs(forces_col_L['max_moment_z'].magnitude),
                abs(forces_col_L['min_moment_z'].magnitude),
                abs(forces_col_R['max_moment_z'].magnitude),
                abs(forces_col_R['min_moment_z'].magnitude)
            ) * ureg.kN * ureg.m
            
            # Check column compressive capacity (fixed-fixed)
            col_comp_check = check_compressive_resistance(
                col_sec, 
                steel_cols, 
                COLUMN_HEIGHT, 
                ["fixed", "fixed"]
            )
            
            # Check column flexural capacity
            col_flex_check = check_flexural_resistance(
                col_sec, 
                steel_cols, 
                unbraced_length=COLUMN_HEIGHT
            )
            
            # Combined check (simplified interaction - P/Pc + M/Mc <= 1.0)
            # CSA S16 Clause 13.8 uses more complex interaction, this is conservative
            utilization = (Pu_col / col_comp_check['Pu_capacity'] + 
                          Mu_col / col_flex_check['Mu_capacity'])
            
            if utilization > 1.0:
                continue  # Column fails interaction check
            
            # -----------------------------------------------------------------
            # SUCCESS! This combination passes
            # -----------------------------------------------------------------
            
            print(f"  [{iteration}] {beam_name} + {col_name}: PASS")
            print(f"       Weight: {total_weight.to(ureg.kg):.1f~}")
            print(f"       Beam M: {Mu_beam:.2f~} / {beam_check['Mu_capacity']:.2f~}")
            print(f"       Col Util: {utilization.magnitude:.2%}")
            
            # Update best solution
            if total_weight < best_total_weight:
                best_total_weight = total_weight
                best_solution = {
                    'beam_name': beam_name,
                    'col_name': col_name,
                    'beam_sec': beam_sec,
                    'col_sec': col_sec,
                    'frame': frame,
                    'beam_check': beam_check,
                    'col_comp_check': col_comp_check,
                    'col_flex_check': col_flex_check,
                    'Mu_beam': Mu_beam,
                    'Vu_beam': Vu_beam,
                    'Pu_col': Pu_col,
                    'Mu_col': Mu_col,
                    'utilization': utilization,
                    'total_weight': total_weight,
                    'forces_beam_L': forces_L,
                    'forces_beam_R': forces_R,
                    'forces_col_L': forces_col_L,
                    'forces_col_R': forces_col_R,
                    'axial_col_L': axial_col_L,
                    'axial_col_R': axial_col_R
                }
    
    # =========================================================================
    # 5. REPORT RESULTS
    # =========================================================================
    
    if best_solution is None:
        print("\n" + "=" * 60)
        print("NO VALID SOLUTION FOUND")
        print("=" * 60)
        rep.add_section("Design Failed")
        rep.add_text("No combination of available sections satisfies the design requirements.")
        output_path = os.path.join(current_dir, "Portal_Frame_Design.md")
        rep.save(output_path)
        return None
    
    print("\n" + "=" * 60)
    print("OPTIMAL SOLUTION FOUND")
    print("=" * 60)
    print(f"Beam:   {best_solution['beam_name']}")
    print(f"Column: {best_solution['col_name']}")
    print(f"Total Weight: {best_solution['total_weight'].to(ureg.kg):.1f~}")
    
    # -----------------------------------------------------------------
    # GENERATE DIAGRAMS
    # -----------------------------------------------------------------
    
    frame = best_solution['frame']
    
    # Beam diagrams (use left half for illustration)
    beam_diag_file = os.path.join(current_dir, "beam_diagrams.png")
    frame.generate_diagrams("BEAM_L", beam_diag_file, direction="strong_axis")
    
    # Column diagrams
    col_diag_file = os.path.join(current_dir, "column_diagrams.png")
    frame.generate_diagrams("COL_L", col_diag_file, direction="strong_axis")
    
    # -----------------------------------------------------------------
    # POPULATE REPORT
    # -----------------------------------------------------------------
    
    rep.add_section("Selected Members")
    rep.add_text(f"**Beam:** {best_solution['beam_name']}")
    rep.add_text(f"**Columns:** {best_solution['col_name']}")
    rep.add_text(f"**Total Frame Weight:** {best_solution['total_weight'].to(ureg.kg):.1f~}")
    
    # Beam Design
    rep.add_section("Beam Design Verification")
    rep.add_text(f"**Maximum Factored Moment:** {best_solution['Mu_beam']:.2f~}")
    rep.add_text(f"**Maximum Factored Shear:** {best_solution['Vu_beam']:.2f~}")
    
    if 'calc_trace' in best_solution['beam_check']:
        rep.add_symbolic_derivation(
            f"Beam Flexural Check: {best_solution['beam_name']}", 
            best_solution['beam_check']['calc_trace']
        )
    
    rep.add_calculation_result(
        f"Beam Summary: {best_solution['beam_name']}", 
        best_solution['beam_check'], 
        status="PASS"
    )
    rep.add_image("Beam Shear and Moment Diagrams", "beam_diagrams.png")
    
    # Column Design
    rep.add_section("Column Design Verification")
    rep.add_text(f"**Maximum Factored Axial:** {best_solution['Pu_col']:.2f~}")
    rep.add_text(f"**Maximum Factored Moment:** {best_solution['Mu_col']:.2f~}")
    rep.add_text(f"**Combined Utilization:** {best_solution['utilization'].magnitude:.1%}")
    
    if 'calc_trace' in best_solution['col_comp_check']:
        rep.add_symbolic_derivation(
            f"Column Compression Check: {best_solution['col_name']}", 
            best_solution['col_comp_check']['calc_trace']
        )
    
    if 'calc_trace' in best_solution['col_flex_check']:
        rep.add_symbolic_derivation(
            f"Column Flexure Check: {best_solution['col_name']}", 
            best_solution['col_flex_check']['calc_trace']
        )
    
    rep.add_calculation_result(
        f"Column Compression: {best_solution['col_name']}", 
        best_solution['col_comp_check'], 
        status="PASS"
    )
    rep.add_calculation_result(
        f"Column Flexure: {best_solution['col_name']}", 
        best_solution['col_flex_check'], 
        status="PASS"
    )
    rep.add_image("Column Force Diagrams", "column_diagrams.png")
    
    # -----------------------------------------------------------------
    # BASE PLATE DESIGN
    # -----------------------------------------------------------------
    
    rep.add_section("Base Plate Design")
    rep.add_text("Design for column base connection to concrete foundation.")
    
    bp = BasePlateDesign(
        column=best_solution['col_sec'],
        load_Pu=best_solution['Pu_col'],
        steel_grade=steel_beams,
        concrete=concrete
    )
    rep.add_module(bp)
    
    # -----------------------------------------------------------------
    # SAVE REPORT
    # -----------------------------------------------------------------
    
    output_path = os.path.join(current_dir, "Portal_Frame_Design.md")
    rep.save(output_path)
    print(f"\nReport saved to: {output_path}")
    
    return best_solution


if __name__ == "__main__":
    design_portal_frame()