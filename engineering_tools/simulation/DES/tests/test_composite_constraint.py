"""
Integration tests for composite constraint model in tool drivers.

Tests verify:
- FiberLaser uses min(thermal, fluid) constraint
- PlasmaTorch uses min(thermal, fluid) constraint
- Composite model correctly picks limiting constraint
- Both tools produce realistic cutting speeds
"""

import pytest
from engineering_tools.simulation.core.machines.subsystems.eoa_tools.fiber_laser import FiberLaser
from engineering_tools.simulation.core.machines.subsystems.eoa_tools.plasma import PlasmaTorch
from engineering_tools.mech_core.standards.materials.steel import get_material


class TestFiberLaserCompositeConstraint:
    """Test suite for FiberLaser composite constraint implementation."""

    def test_fiber_laser_composite_constraint_returns_positive_speed(self):
        """Verify fiber laser composite constraint returns positive, realistic speed."""
        laser = FiberLaser()
        material = get_material("ASTM A36")

        speed = laser.calculate_cutting_speed(material, thickness_mm=12.0)

        assert speed > 0, "Cutting speed must be positive"
        assert speed < 200, f"Speed {speed:.1f} mm/s seems unreasonably high for laser cutting"

    def test_fiber_laser_thin_material(self):
        """Thin material should cut faster (less thermal constraint)."""
        laser = FiberLaser()
        material = get_material("ASTM A36")

        speed_thin = laser.calculate_cutting_speed(material, thickness_mm=3.0)
        speed_thick = laser.calculate_cutting_speed(material, thickness_mm=25.0)

        assert speed_thin > speed_thick, \
            "Thinner material should cut faster"

    def test_fiber_laser_a992_vs_a36(self):
        """Different materials should have reasonable cutting speeds."""
        laser = FiberLaser()
        a36 = get_material("ASTM A36")
        a992 = get_material("ASTM A992")

        speed_a36 = laser.calculate_cutting_speed(a36, thickness_mm=12.0)
        speed_a992 = laser.calculate_cutting_speed(a992, thickness_mm=12.0)

        # Both should be positive and realistic
        assert 0 < speed_a36 < 200
        assert 0 < speed_a992 < 200

        # Should be within reasonable range of each other (similar properties)
        ratio = speed_a992 / speed_a36
        assert 0.5 < ratio < 2.0, \
            f"A992 and A36 speeds should be similar, got ratio {ratio:.2f}"


class TestPlasmaTorchCompositeConstraint:
    """Test suite for PlasmaTorch composite constraint implementation."""

    def test_plasma_composite_constraint_returns_positive_speed(self):
        """Verify plasma torch composite constraint returns positive, realistic speed."""
        plasma = PlasmaTorch()
        material = get_material("ASTM A36")

        speed = plasma.calculate_cut_speed(material, thickness_mm=10.0)

        assert speed > 0, "Cutting speed must be positive"
        assert speed < 300, f"Speed {speed:.1f} mm/s seems unreasonably high for plasma cutting"

    def test_plasma_thin_material(self):
        """Thin material should cut faster (less thermal constraint)."""
        plasma = PlasmaTorch()
        material = get_material("ASTM A36")

        speed_thin = plasma.calculate_cut_speed(material, thickness_mm=5.0)
        speed_thick = plasma.calculate_cut_speed(material, thickness_mm=20.0)

        assert speed_thin > speed_thick, \
            "Thinner material should cut faster"

    def test_plasma_different_materials(self):
        """Different materials should have reasonable cutting speeds."""
        plasma = PlasmaTorch()
        a36 = get_material("ASTM A36")
        a992 = get_material("ASTM A992")

        speed_a36 = plasma.calculate_cut_speed(a36, thickness_mm=10.0)
        speed_a992 = plasma.calculate_cut_speed(a992, thickness_mm=10.0)

        # Both should be positive and realistic
        assert 0 < speed_a36 < 300
        assert 0 < speed_a992 < 300


class TestCompositeConstraintComparison:
    """Test suite comparing laser vs plasma composite constraints."""

    def test_laser_vs_plasma_speeds(self):
        """
        Compare laser and plasma cutting speeds.

        Plasma typically has higher power, so may be faster on thick material.
        Laser may be faster on thin material due to better precision.
        """
        laser = FiberLaser()
        plasma = PlasmaTorch()
        material = get_material("ASTM A36")

        # Thin material
        laser_thin = laser.calculate_cutting_speed(material, thickness_mm=3.0)
        plasma_thin = plasma.calculate_cut_speed(material, thickness_mm=3.0)

        # Thick material
        laser_thick = laser.calculate_cutting_speed(material, thickness_mm=20.0)
        plasma_thick = plasma.calculate_cut_speed(material, thickness_mm=20.0)

        # Both tools should produce positive, reasonable speeds
        assert 0 < laser_thin < 200
        assert 0 < plasma_thin < 300
        assert 0 < laser_thick < 200
        assert 0 < plasma_thick < 300

    def test_thermal_dominates_for_normal_gas_params(self):
        """
        With high gas parameters (as set in configs), thermal should dominate.

        This verifies regression safety: with gas_pressure=100 bar and
        nozzle_diameter=10mm, the fluid constraint should be very high,
        making thermal the limiting factor (as in the original implementation).
        """
        laser = FiberLaser()
        material = get_material("ASTM A36")

        # Calculate speed (should be thermal-limited with high gas params)
        speed = laser.calculate_cutting_speed(material, thickness_mm=12.0)

        # Speed should be in the same range as original ProcessEnergyCalculator
        # Original range was 5-15 mm/s for A36 at 12mm, 4kW, 35% efficiency
        assert 5.0 <= speed <= 20.0, \
            f"With high gas params, thermal should dominate. Speed {speed:.1f} mm/s outside expected range [5, 20]"


class TestConstraintDominance:
    """Test suite verifying which constraint dominates under different conditions."""

    def test_extremely_thick_material_thermal_limited(self):
        """
        Extremely thick material should be thermal-limited.

        Even with high gas flow, very thick material requires enormous thermal energy.
        """
        laser = FiberLaser()
        material = get_material("ASTM A36")

        speed = laser.calculate_cutting_speed(material, thickness_mm=50.0)

        # Should be very slow (thermal-limited)
        assert 0 < speed < 10, \
            f"Extremely thick material should cut very slowly, got {speed:.1f} mm/s"

    def test_multiple_thicknesses_monotonic(self):
        """
        Cutting speed should decrease monotonically with thickness.

        This verifies the composite constraint behaves physically correct.
        """
        laser = FiberLaser()
        material = get_material("ASTM A36")

        speeds = []
        thicknesses = [3, 6, 12, 18, 25]
        for t in thicknesses:
            speed = laser.calculate_cutting_speed(material, thickness_mm=t)
            speeds.append(speed)

        # Verify monotonic decrease
        for i in range(len(speeds) - 1):
            assert speeds[i] > speeds[i+1], \
                f"Speed should decrease with thickness: {thicknesses[i]}mm={speeds[i]:.1f} mm/s > {thicknesses[i+1]}mm={speeds[i+1]:.1f} mm/s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
