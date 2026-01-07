"""
Unit tests for mech_core.analysis.manufacturing.thermal_removal module.

Tests verify:
- Physics accuracy against known ProcessEnergyCalculator results
- Relationship constraints (thicker → slower, higher power → faster)
- Input validation and error handling
- Unit conversion correctness
"""

import pytest
import math
from engineering_tools.mech_core.analysis.manufacturing.thermal_removal import (
    calculate_melting_speed,
    calculate_pierce_time,
    calculate_specific_removal_rate
)
from engineering_tools.mech_core.standards.materials.steel import get_material
from engineering_tools.mech_core.standards.units import ureg, Q_


class TestCalculateMeltingSpeed:
    """Test suite for calculate_melting_speed function."""

    def test_a36_baseline_realistic_speed(self):
        """
        Verify A36 steel cutting speed matches ProcessEnergyCalculator results.

        Reference: test_process_physics.py line 28
        Expected range: 5-15 mm/s for 12mm A36 at 4kW with 35% efficiency
        """
        material = get_material("ASTM A36")

        speed = calculate_melting_speed(
            material=material,
            thickness=Q_(12.0, ureg.mm),
            tool_power=Q_(4.0, ureg.kW),
            kerf_width=Q_(1.5, ureg.mm),
            efficiency=0.35,
            absorptivity=0.70  # Mill scale
        )

        speed_mm_s = speed.to(ureg.mm / ureg.second).magnitude

        assert 5.0 <= speed_mm_s <= 15.0, \
            f"Speed {speed_mm_s:.2f} mm/s outside realistic range [5, 15] mm/s"
        assert speed_mm_s > 0, "Speed must be positive"

    def test_thickness_relationship_inverse(self):
        """Thicker material should cut slower (inverse relationship)."""
        material = get_material("ASTM A36")

        speed_thin = calculate_melting_speed(
            material, Q_(6.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )
        speed_thick = calculate_melting_speed(
            material, Q_(25.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )

        assert speed_thin > speed_thick, \
            "Thinner material should cut faster than thicker material"

        # Speed should be approximately inversely proportional to thickness
        ratio = speed_thin.magnitude / speed_thick.magnitude
        expected_ratio = 25.0 / 6.0  # ≈ 4.17
        assert pytest.approx(ratio, rel=0.1) == expected_ratio

    def test_power_relationship_linear(self):
        """Higher power should enable faster cutting (linear relationship)."""
        material = get_material("ASTM A36")

        speed_low = calculate_melting_speed(
            material, Q_(12.0, ureg.mm), Q_(2.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )
        speed_high = calculate_melting_speed(
            material, Q_(12.0, ureg.mm), Q_(6.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )

        # Should be approximately 3x faster (linear with power)
        ratio = speed_high.magnitude / speed_low.magnitude
        assert pytest.approx(ratio, rel=0.05) == 3.0, \
            f"Speed should scale linearly with power, got ratio {ratio:.2f}"

    def test_efficiency_effect(self):
        """Higher efficiency should enable faster cutting."""
        material = get_material("ASTM A36")

        speed_low_eff = calculate_melting_speed(
            material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )
        speed_high_eff = calculate_melting_speed(
            material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.70, 0.70  # 2x efficiency
        )

        ratio = speed_high_eff.magnitude / speed_low_eff.magnitude
        assert pytest.approx(ratio, rel=0.05) == 2.0, \
            "Speed should scale linearly with efficiency"

    def test_absorptivity_effect(self):
        """Higher absorptivity should enable faster cutting."""
        material = get_material("ASTM A36")

        # Blast cleaned (low absorption)
        speed_low_abs = calculate_melting_speed(
            material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.45
        )
        # Mill scale (high absorption)
        speed_high_abs = calculate_melting_speed(
            material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )

        assert speed_high_abs > speed_low_abs, \
            "Higher surface absorptivity should enable faster cutting"

        ratio = speed_high_abs.magnitude / speed_low_abs.magnitude
        expected_ratio = 0.70 / 0.45
        assert pytest.approx(ratio, rel=0.05) == expected_ratio

    def test_a992_steel_similar_to_a36(self):
        """A992 and A36 should have similar cutting speeds (similar properties)."""
        a36 = get_material("ASTM A36")
        a992 = get_material("ASTM A992")

        speed_a36 = calculate_melting_speed(
            a36, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )
        speed_a992 = calculate_melting_speed(
            a992, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
            Q_(1.5, ureg.mm), 0.35, 0.70
        )

        # Should be within 20% of each other (similar thermal properties)
        ratio = speed_a992.magnitude / speed_a36.magnitude
        assert 0.8 <= ratio <= 1.2, \
            f"A992 and A36 speeds should be similar, got ratio {ratio:.2f}"

    def test_zero_thickness_raises_error(self):
        """Zero thickness should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Thickness must be positive"):
            calculate_melting_speed(
                material, Q_(0.0, ureg.mm), Q_(4.0, ureg.kW),
                Q_(1.5, ureg.mm), 0.35, 0.70
            )

    def test_negative_thickness_raises_error(self):
        """Negative thickness should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Thickness must be positive"):
            calculate_melting_speed(
                material, Q_(-5.0, ureg.mm), Q_(4.0, ureg.kW),
                Q_(1.5, ureg.mm), 0.35, 0.70
            )

    def test_zero_power_raises_error(self):
        """Zero power should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Tool power must be positive"):
            calculate_melting_speed(
                material, Q_(12.0, ureg.mm), Q_(0.0, ureg.kW),
                Q_(1.5, ureg.mm), 0.35, 0.70
            )

    def test_zero_kerf_raises_error(self):
        """Zero kerf width should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Kerf width must be positive"):
            calculate_melting_speed(
                material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
                Q_(0.0, ureg.mm), 0.35, 0.70
            )

    def test_efficiency_above_one_raises_error(self):
        """Efficiency > 1 should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Efficiency must be between 0 and 1"):
            calculate_melting_speed(
                material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
                Q_(1.5, ureg.mm), 1.5, 0.70  # Invalid efficiency
            )

    def test_efficiency_negative_raises_error(self):
        """Negative efficiency should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Efficiency must be between 0 and 1"):
            calculate_melting_speed(
                material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
                Q_(1.5, ureg.mm), -0.5, 0.70
            )

    def test_absorptivity_above_one_raises_error(self):
        """Absorptivity > 1 should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Absorptivity must be between 0 and 1"):
            calculate_melting_speed(
                material, Q_(12.0, ureg.mm), Q_(4.0, ureg.kW),
                Q_(1.5, ureg.mm), 0.35, 1.2  # Invalid absorptivity
            )


class TestCalculatePierceTime:
    """Test suite for calculate_pierce_time function."""

    def test_pierce_time_baseline_realistic(self):
        """
        Verify pierce time calculation returns realistic values.

        Reference: test_process_physics.py line 162
        Expected range: 0.1-20 seconds for 10g @ 4kW
        """
        material = get_material("ASTM A36")

        time = calculate_pierce_time(
            material=material,
            mass=Q_(0.01, ureg.kg),  # 10 grams
            tool_power=Q_(4.0, ureg.kW),
            efficiency=0.35,
            absorptivity=0.70
        )

        time_s = time.to(ureg.second).magnitude

        assert 0.1 < time_s < 20.0, \
            f"Pierce time {time_s:.2f}s outside realistic range [0.1, 20] seconds"
        assert time_s > 0, "Pierce time must be positive"

    def test_pierce_time_mass_relationship(self):
        """Double mass should approximately double pierce time (linear relationship)."""
        material = get_material("ASTM A36")

        time_1g = calculate_pierce_time(
            material, Q_(0.001, ureg.kg), Q_(4.0, ureg.kW), 0.35, 0.70
        )
        time_2g = calculate_pierce_time(
            material, Q_(0.002, ureg.kg), Q_(4.0, ureg.kW), 0.35, 0.70
        )

        ratio = time_2g.magnitude / time_1g.magnitude
        assert pytest.approx(ratio, rel=0.01) == 2.0, \
            f"Pierce time should scale linearly with mass, got ratio {ratio:.3f}"

    def test_pierce_time_power_relationship(self):
        """Higher power should reduce pierce time (inverse relationship)."""
        material = get_material("ASTM A36")

        time_low_power = calculate_pierce_time(
            material, Q_(0.01, ureg.kg), Q_(2.0, ureg.kW), 0.35, 0.70
        )
        time_high_power = calculate_pierce_time(
            material, Q_(0.01, ureg.kg), Q_(6.0, ureg.kW), 0.35, 0.70
        )

        # Should be 3x faster (inverse relationship)
        ratio = time_low_power.magnitude / time_high_power.magnitude
        assert pytest.approx(ratio, rel=0.05) == 3.0, \
            "Pierce time should be inversely proportional to power"

    def test_zero_mass_raises_error(self):
        """Zero mass should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Mass must be positive"):
            calculate_pierce_time(
                material, Q_(0.0, ureg.kg), Q_(4.0, ureg.kW), 0.35, 0.70
            )

    def test_negative_mass_raises_error(self):
        """Negative mass should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Mass must be positive"):
            calculate_pierce_time(
                material, Q_(-0.01, ureg.kg), Q_(4.0, ureg.kW), 0.35, 0.70
            )

    def test_zero_power_raises_error(self):
        """Zero power should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Tool power must be positive"):
            calculate_pierce_time(
                material, Q_(0.01, ureg.kg), Q_(0.0, ureg.kW), 0.35, 0.70
            )


class TestCalculateSpecificRemovalRate:
    """Test suite for calculate_specific_removal_rate function."""

    def test_removal_rate_positive(self):
        """Removal rate should always be positive for valid inputs."""
        material = get_material("ASTM A36")

        rate = calculate_specific_removal_rate(
            material, Q_(4.0, ureg.kW), 0.35, 0.70
        )

        assert rate.magnitude > 0, "Removal rate must be positive"

    def test_removal_rate_power_relationship(self):
        """Removal rate should scale linearly with power."""
        material = get_material("ASTM A36")

        rate_low = calculate_specific_removal_rate(
            material, Q_(2.0, ureg.kW), 0.35, 0.70
        )
        rate_high = calculate_specific_removal_rate(
            material, Q_(6.0, ureg.kW), 0.35, 0.70
        )

        ratio = rate_high.magnitude / rate_low.magnitude
        assert pytest.approx(ratio, rel=0.05) == 3.0, \
            "Removal rate should scale linearly with power"

    def test_zero_power_raises_error(self):
        """Zero power should raise ValueError."""
        material = get_material("ASTM A36")

        with pytest.raises(ValueError, match="Tool power must be positive"):
            calculate_specific_removal_rate(
                material, Q_(0.0, ureg.kW), 0.35, 0.70
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
