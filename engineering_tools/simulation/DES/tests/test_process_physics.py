"""
Unit tests for ProcessEnergyCalculator.

Tests verify:
- Realistic cutting speeds for known materials
- Material fallback behavior
- Thickness effects on speed
- Edge case handling (zero thickness, invalid inputs)
"""

import pytest
from ..core.machines.subsystems.eoa_tools.fiber_laser import ProcessEnergyCalculator


def test_a36_realistic_speed():
    """Verify A36 steel calculation returns realistic speed."""
    calc = ProcessEnergyCalculator(efficiency=0.35)

    speed = calc.calculate_cutting_speed(
        material_name="ASTM A36",
        thickness_mm=12.0,
        tool_power_kw=4.0,
        kerf_width_mm=1.5
    )

    # Expect 5-15 mm/s for 12mm A36 with 4kW laser
    # (Based on physics: 4kW × 0.35 eff × 0.7 abs / (7.9 J/mm³ × 18 mm²) ≈ 7 mm/s)
    assert 5.0 <= speed <= 15.0, f"Speed {speed} mm/s is outside realistic range"
    assert speed > 0, "Speed must be positive"


def test_a992_realistic_speed():
    """Verify A992 steel calculation returns realistic speed."""
    calc = ProcessEnergyCalculator(efficiency=0.35)

    speed = calc.calculate_cutting_speed(
        material_name="ASTM A992",
        thickness_mm=12.0,
        tool_power_kw=4.0,
        kerf_width_mm=1.5
    )

    # A992 should have similar speed to A36 (similar thermodynamics)
    assert 5.0 <= speed <= 15.0, f"Speed {speed} mm/s is outside realistic range"


def test_material_not_found_fallback():
    """Unknown material should fallback to A36 and return valid speed."""
    calc = ProcessEnergyCalculator()

    speed = calc.calculate_cutting_speed(
        material_name="FAKE_STEEL_XYZ",
        thickness_mm=10.0,
        tool_power_kw=4.0,
        kerf_width_mm=1.5
    )

    # Should return valid speed (not NaN or error)
    assert speed > 0, "Fallback speed must be positive"
    import math
    assert not math.isnan(speed), "Speed should not be NaN"


def test_thicker_material_slower_speed():
    """Thicker material should require slower cutting."""
    calc = ProcessEnergyCalculator()

    speed_thin = calc.calculate_cutting_speed("ASTM A36", 6.0, 4.0, 1.5)
    speed_thick = calc.calculate_cutting_speed("ASTM A36", 25.0, 4.0, 1.5)

    assert speed_thin > speed_thick, "Thinner material should cut faster"
    assert speed_thick > 0, "Thick material speed must still be positive"


def test_higher_power_faster_speed():
    """Higher laser power should enable faster cutting."""
    calc = ProcessEnergyCalculator()

    speed_low_power = calc.calculate_cutting_speed("ASTM A36", 12.0, 2.0, 1.5)
    speed_high_power = calc.calculate_cutting_speed("ASTM A36", 12.0, 6.0, 1.5)

    assert speed_high_power > speed_low_power, "Higher power should cut faster"


def test_zero_thickness_error():
    """Zero thickness should raise ValueError."""
    calc = ProcessEnergyCalculator()

    with pytest.raises(ValueError, match="Thickness must be positive"):
        calc.calculate_cutting_speed("ASTM A36", 0.0, 4.0, 1.5)


def test_negative_thickness_error():
    """Negative thickness should raise ValueError."""
    calc = ProcessEnergyCalculator()

    with pytest.raises(ValueError, match="Thickness must be positive"):
        calc.calculate_cutting_speed("ASTM A36", -5.0, 4.0, 1.5)


def test_zero_kerf_error():
    """Zero kerf width should raise ValueError."""
    calc = ProcessEnergyCalculator()

    with pytest.raises(ValueError, match="Kerf width must be positive"):
        calc.calculate_cutting_speed("ASTM A36", 12.0, 4.0, 0.0)


def test_zero_power_error():
    """Zero tool power should raise ValueError."""
    calc = ProcessEnergyCalculator()

    with pytest.raises(ValueError, match="Tool power must be positive"):
        calc.calculate_cutting_speed("ASTM A36", 12.0, 0.0, 1.5)


def test_efficiency_bounds():
    """Efficiency must be between 0 and 1."""
    # Valid efficiency
    calc = ProcessEnergyCalculator(efficiency=0.5)
    assert calc.efficiency == 0.5

    # Invalid efficiency
    with pytest.raises(ValueError, match="Efficiency must be between 0 and 1"):
        ProcessEnergyCalculator(efficiency=1.5)

    with pytest.raises(ValueError, match="Efficiency must be between 0 and 1"):
        ProcessEnergyCalculator(efficiency=-0.1)


def test_surface_condition_affects_speed():
    """Different surface conditions should affect cutting speed."""
    calc = ProcessEnergyCalculator()

    # Mill scale has lower absorption than primed surface
    speed_mill_scale = calc.calculate_cutting_speed(
        "ASTM A36", 12.0, 4.0, 1.5, surface_condition="mill_scale"
    )

    # Blast cleaned has lower absorption
    speed_blast_cleaned = calc.calculate_cutting_speed(
        "ASTM A36", 12.0, 4.0, 1.5, surface_condition="blast_cleaned"
    )

    # Mill scale typically absorbs more than blast cleaned for fiber laser
    assert speed_mill_scale > speed_blast_cleaned, \
        "Mill scale should absorb better than blast cleaned"


def test_melting_time_calculation():
    """Test melting time calculation for pierce operations."""
    calc = ProcessEnergyCalculator(efficiency=0.35)

    time = calc.calculate_melting_time(
        material_name="ASTM A36",
        mass_kg=0.01,  # 10 grams
        tool_power_kw=4.0
    )

    # Should be a reasonable time (few seconds for 10g of steel)
    # Physics: 10g needs ~11kJ, 4kW laser gives ~1.4kW effective, so ~8 seconds
    assert 0.1 < time < 20.0, f"Melting time {time}s seems unrealistic"


def test_melting_time_zero_mass_error():
    """Zero mass should raise ValueError."""
    calc = ProcessEnergyCalculator()

    with pytest.raises(ValueError, match="Mass must be positive"):
        calc.calculate_melting_time("ASTM A36", 0.0, 4.0)


def test_melting_time_zero_power_error():
    """Zero power should raise ValueError."""
    calc = ProcessEnergyCalculator()

    with pytest.raises(ValueError, match="Tool power must be positive"):
        calc.calculate_melting_time("ASTM A36", 0.01, 0.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
