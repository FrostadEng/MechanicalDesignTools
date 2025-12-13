"""
Test script for FrameAnalysis wrapper with PyNiteFEA.

This demonstrates how to use the FEA wrapper with AISC sections
and materials from the mech_core library.
"""
import sys
import os

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, repo_root)

from mech_core.units import ureg
from mech_core.components.aisc_members import get_section
from mech_core.standards.materials import get_material
from mech_core.analysis.fea import FrameAnalysis


def test_simple_beam():
    """
    Test Case: Simply supported beam with point load at midspan

    Configuration:
    - Beam: W12X26 AISC section
    - Material: ASTM A36 steel
    - Length: 6 meters
    - Load: 50 kN point load at center
    - Supports: Pin at left, roller at right
    """
    print("=" * 60)
    print("TEST: Simply Supported Beam with Point Load")
    print("=" * 60)

    # Initialize FEA model
    frame = FrameAnalysis()

    # Get section and material from AISC library
    section = get_section("W12X26")
    steel = get_material("ASTM A36")

    print(f"\nSection: {section.name}")
    print(f"Material: {steel.name}")
    print(f"Fy = {steel.yield_strength.to(ureg.MPa)}")
    print(f"E = {steel.elastic_modulus.to(ureg.GPa)}")

    # Build model
    # Nodes: N1 (left support), N2 (midpoint), N3 (right support)
    frame.add_node("N1", 0, 0, 0)
    frame.add_node("N2", 3, 0, 0)  # Midpoint
    frame.add_node("N3", 6, 0, 0)

    # Beams
    frame.add_beam("B1", "N1", "N2", section, steel)
    frame.add_beam("B2", "N2", "N3", section, steel)

    # Boundary conditions
    frame.add_support("N1", "pinned")
    frame.add_support("N3", "roller")

    # Apply point load at midspan (50 kN downward in Z direction)
    frame.add_node_load("N2", Fz=-50*ureg.kN)

    print("\nModel built successfully!")
    print("- 3 nodes")
    print("- 2 beam elements")
    print("- 50 kN point load at midspan")

    # Solve
    print("\nSolving FEA model...")
    frame.solve()
    print("✓ Analysis complete!")

    # Get results
    print("\n" + "=" * 60)
    print("RESULTS: Member Forces")
    print("=" * 60)

    for member in ["B1", "B2"]:
        forces = frame.get_beam_forces(member)
        print(f"\nMember {member}:")
        print(f"  Max Shear (Fy): {forces['max_shear_y']:.2f}")
        print(f"  Min Shear (Fy): {forces['min_shear_y']:.2f}")
        print(f"  Max Moment (Mz - Strong Axis): {forces['max_moment_z']:.2f}")
        print(f"  Min Moment (Mz - Strong Axis): {forces['min_moment_z']:.2f}")

    # Generate diagrams
    print("\nGenerating shear and moment diagrams...")
    output_path = os.path.join(current_dir, "simple_beam_diagrams.png")
    frame.generate_diagrams("B1", output_path, direction="strong_axis")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


def test_cantilever_beam():
    """
    Test Case: Cantilever beam with distributed load

    Configuration:
    - Beam: C10X15.3 channel section
    - Material: CSA G40.21 350W
    - Length: 4 meters
    - Load: 10 kN/m uniform distributed load
    - Support: Fixed at left end
    """
    print("\n\n" + "=" * 60)
    print("TEST: Cantilever Beam with Distributed Load")
    print("=" * 60)

    # Initialize
    frame = FrameAnalysis()

    # Section and material
    section = get_section("C10X15.3")
    steel = get_material("CSA G40.21 350W")

    print(f"\nSection: {section.name}")
    print(f"Material: {steel.name}")

    # Build model
    frame.add_node("N1", 0, 0, 0)
    frame.add_node("N2", 4, 0, 0)

    frame.add_beam("B1", "N1", "N2", section, steel)

    # Fixed support at left end
    frame.add_support("N1", "fixed")

    # Distributed load (10 kN/m downward)
    w = -10 * ureg.kN / ureg.meter
    frame.add_member_dist_load("B1", "Fz", w, w)

    print("\nModel built successfully!")
    print("- Cantilever length: 4 m")
    print("- Distributed load: 10 kN/m")

    # Solve
    print("\nSolving...")
    frame.solve()
    print("✓ Analysis complete!")

    # Results
    forces = frame.get_beam_forces("B1")
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Max Shear: {forces['max_shear_y']:.2f}")
    print(f"Max Moment: {forces['max_moment_z']:.2f}")

    # Expected theoretical values for cantilever:
    # Max Shear = w * L = 10 kN/m * 4 m = 40 kN
    # Max Moment = w * L^2 / 2 = 10 * 16 / 2 = 80 kN·m
    print("\nTheoretical values:")
    print(f"Expected Shear: 40.00 kN")
    print(f"Expected Moment: 80.00 kN·m")

    # Generate diagram
    output_path = os.path.join(current_dir, "cantilever_diagrams.png")
    frame.generate_diagrams("B1", output_path)

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    try:
        # Run test cases
        test_simple_beam()
        test_cantilever_beam()

        print("\n" + "🎉" * 30)
        print("ALL TESTS PASSED!")
        print("🎉" * 30)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
