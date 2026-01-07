"""
Unit tests for mech_core.analysis.fluid_dynamics.gas_jets module.

Tests verify:
- Compressible flow physics (subsonic vs supersonic)
- Ideal gas law calculations
- Clearing speed heuristic model
- Input validation and error handling
"""

import pytest
import math
from engineering_tools.mech_core.analysis.fluid_dynamics.gas_jets import (
    calculate_nozzle_exit_velocity,
    calculate_clearing_speed_limit,
    calculate_gas_density_at_nozzle
)
from engineering_tools.mech_core.standards.units import ureg, Q_


class TestCalculateNozzleExitVelocity:
    """Test suite for calculate_nozzle_exit_velocity function."""

    def test_subsonic_flow_low_pressure_ratio(self):
        """
        Low pressure ratio should give subsonic flow.

        Physics: Speed of sound in air at 300K ≈ 347 m/s
        With pressure ratio of 2:1, should be subsonic
        """
        v = calculate_nozzle_exit_velocity(
            pressure_inlet=Q_(2.0, ureg.bar),
            pressure_ambient=Q_(1.0, ureg.bar),
            temperature_inlet=Q_(300, ureg.K),
            gas_gamma=1.4
        )

        v_m_s = v.to(ureg.m / ureg.s).magnitude

        # Speed of sound at 300K: c = sqrt(gamma * R * T) ≈ 347 m/s
        speed_of_sound = 347  # m/s

        assert v_m_s < speed_of_sound, \
            f"Low pressure ratio should give subsonic flow, got {v_m_s:.1f} m/s"
        assert v_m_s > 0, "Velocity must be positive"

    def test_supersonic_flow_high_pressure_ratio(self):
        """
        High pressure ratio should give supersonic flow.

        For pressure ratios > critical (~1.89 for air), flow can be supersonic
        """
        v = calculate_nozzle_exit_velocity(
            pressure_inlet=Q_(10.0, ureg.bar),
            pressure_ambient=Q_(1.0, ureg.bar),
            temperature_inlet=Q_(300, ureg.K),
            gas_gamma=1.4
        )

        v_m_s = v.to(ureg.m / ureg.s).magnitude

        speed_of_sound = 347  # m/s

        assert v_m_s > speed_of_sound, \
            f"High pressure ratio should give supersonic flow, got {v_m_s:.1f} m/s"
        # But not unreasonably high (< Mach 3)
        assert v_m_s < 3 * speed_of_sound, \
            f"Velocity {v_m_s:.1f} m/s seems too high (> Mach 3)"

    def test_pressure_relationship_monotonic(self):
        """Higher pressure ratio should give higher velocity (monotonic)."""
        v_low = calculate_nozzle_exit_velocity(
            Q_(5.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K), 1.4
        )
        v_high = calculate_nozzle_exit_velocity(
            Q_(15.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K), 1.4
        )

        assert v_high > v_low, \
            "Higher inlet pressure should give higher exit velocity"

    def test_temperature_effect(self):
        """Higher inlet temperature should give higher exit velocity."""
        v_cold = calculate_nozzle_exit_velocity(
            Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(250, ureg.K), 1.4
        )
        v_hot = calculate_nozzle_exit_velocity(
            Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(400, ureg.K), 1.4
        )

        assert v_hot > v_cold, \
            "Higher inlet temperature should give higher exit velocity"

    def test_oxygen_vs_air(self):
        """
        Oxygen and air should give similar velocities (same gamma=1.4).

        MW difference (32 vs 28.97) should cause small difference
        """
        v_air = calculate_nozzle_exit_velocity(
            Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K),
            gas_gamma=1.4, gas_mw=28.97
        )
        v_oxygen = calculate_nozzle_exit_velocity(
            Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K),
            gas_gamma=1.4, gas_mw=32.0
        )

        # Should be within 10% of each other
        ratio = v_oxygen.magnitude / v_air.magnitude
        assert 0.9 <= ratio <= 1.1, \
            f"Oxygen and air velocities should be similar, got ratio {ratio:.3f}"

    def test_argon_higher_gamma(self):
        """
        Argon (gamma=1.67) should behave differently from air (gamma=1.4).
        """
        v_air = calculate_nozzle_exit_velocity(
            Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K),
            gas_gamma=1.4, gas_mw=28.97
        )
        v_argon = calculate_nozzle_exit_velocity(
            Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K),
            gas_gamma=1.67, gas_mw=39.95
        )

        # Argon should be different (monoatomic vs diatomic)
        assert v_argon != v_air, "Argon and air should have different velocities"

    def test_zero_inlet_pressure_raises_error(self):
        """Zero inlet pressure should raise ValueError."""
        with pytest.raises(ValueError, match="Inlet pressure must be positive"):
            calculate_nozzle_exit_velocity(
                Q_(0.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K), 1.4
            )

    def test_zero_temperature_raises_error(self):
        """Zero temperature should raise ValueError."""
        with pytest.raises(ValueError, match="Inlet temperature must be positive"):
            calculate_nozzle_exit_velocity(
                Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(0, ureg.K), 1.4
            )

    def test_invalid_gamma_raises_error(self):
        """Gamma <= 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="Gas gamma must be greater than 1.0"):
            calculate_nozzle_exit_velocity(
                Q_(10.0, ureg.bar), Q_(1.0, ureg.bar), Q_(300, ureg.K), 0.8
            )


class TestCalculateGasDensityAtNozzle:
    """Test suite for calculate_gas_density_at_nozzle function."""

    def test_density_ideal_gas_law(self):
        """
        Gas density should follow ideal gas law.

        At 10 bar, 300K: ρ ≈ 11.6 kg/m³ (approximately 10x atmospheric)
        """
        rho = calculate_gas_density_at_nozzle(
            pressure=Q_(10.0, ureg.bar),
            temperature=Q_(300, ureg.K),
            gas_mw=28.97  # Air
        )

        rho_kg_m3 = rho.to(ureg.kg / ureg.m**3).magnitude

        # At 1 bar, 300K, air is ~1.16 kg/m³
        # At 10 bar, should be ~11.6 kg/m³
        assert 10.0 < rho_kg_m3 < 13.0, \
            f"Density {rho_kg_m3:.2f} kg/m³ outside expected range [10, 13]"

    def test_density_pressure_relationship(self):
        """Density should be proportional to pressure (isothermal)."""
        rho_1bar = calculate_gas_density_at_nozzle(
            Q_(1.0, ureg.bar), Q_(300, ureg.K), 28.97
        )
        rho_10bar = calculate_gas_density_at_nozzle(
            Q_(10.0, ureg.bar), Q_(300, ureg.K), 28.97
        )

        # Should be 10x denser
        ratio = rho_10bar.magnitude / rho_1bar.magnitude
        assert pytest.approx(ratio, rel=0.01) == 10.0, \
            f"Density should scale linearly with pressure, got ratio {ratio:.3f}"

    def test_density_temperature_relationship(self):
        """Density should be inversely proportional to temperature (isobaric)."""
        rho_cold = calculate_gas_density_at_nozzle(
            Q_(10.0, ureg.bar), Q_(250, ureg.K), 28.97
        )
        rho_hot = calculate_gas_density_at_nozzle(
            Q_(10.0, ureg.bar), Q_(500, ureg.K), 28.97
        )

        # Should be 2x less dense (500K / 250K = 2)
        ratio = rho_cold.magnitude / rho_hot.magnitude
        assert pytest.approx(ratio, rel=0.01) == 2.0, \
            f"Density should be inversely proportional to temperature, got ratio {ratio:.3f}"

    def test_density_molecular_weight_effect(self):
        """Heavier gas should have higher density."""
        rho_nitrogen = calculate_gas_density_at_nozzle(
            Q_(10.0, ureg.bar), Q_(300, ureg.K), 28.01  # N2
        )
        rho_argon = calculate_gas_density_at_nozzle(
            Q_(10.0, ureg.bar), Q_(300, ureg.K), 39.95  # Ar
        )

        assert rho_argon > rho_nitrogen, \
            "Heavier gas (argon) should have higher density than lighter gas (nitrogen)"

        ratio = rho_argon.magnitude / rho_nitrogen.magnitude
        expected_ratio = 39.95 / 28.01
        assert pytest.approx(ratio, rel=0.01) == expected_ratio

    def test_zero_pressure_raises_error(self):
        """Zero pressure should raise ValueError."""
        with pytest.raises(ValueError, match="Pressure must be positive"):
            calculate_gas_density_at_nozzle(
                Q_(0.0, ureg.bar), Q_(300, ureg.K), 28.97
            )

    def test_zero_temperature_raises_error(self):
        """Zero temperature should raise ValueError."""
        with pytest.raises(ValueError, match="Temperature must be positive"):
            calculate_gas_density_at_nozzle(
                Q_(10.0, ureg.bar), Q_(0, ureg.K), 28.97
            )


class TestCalculateClearingSpeedLimit:
    """Test suite for calculate_clearing_speed_limit function."""

    def test_clearing_speed_realistic_range(self):
        """
        Clearing speed should be in realistic range for cutting operations.

        Typical supersonic gas jet should enable speeds in 1-1000 mm/s range
        """
        v_gas = Q_(500, ureg.m / ureg.s)  # Typical supersonic jet
        gas_rho = Q_(12.0, ureg.kg / ureg.m**3)  # 10 bar compressed air

        v_clear = calculate_clearing_speed_limit(
            nozzle_velocity=v_gas,
            nozzle_diameter=Q_(2.0, ureg.mm),
            kerf_width=Q_(1.5, ureg.mm),
            material_density=Q_(7850, ureg.kg / ureg.m**3),  # Steel
            gas_density=gas_rho,
            efficiency_factor=0.1
        )

        v_clear_mm_s = v_clear.to(ureg.mm / ureg.s).magnitude

        assert v_clear_mm_s > 0, "Clearing speed must be positive"
        assert 1.0 < v_clear_mm_s < 10000.0, \
            f"Clearing speed {v_clear_mm_s:.1f} mm/s outside realistic range"

    def test_clearing_speed_gas_velocity_relationship(self):
        """Higher gas velocity should allow faster clearing."""
        base_params = {
            'nozzle_diameter': Q_(2.0, ureg.mm),
            'kerf_width': Q_(1.5, ureg.mm),
            'material_density': Q_(7850, ureg.kg / ureg.m**3),
            'gas_density': Q_(12.0, ureg.kg / ureg.m**3),
            'efficiency_factor': 0.1
        }

        v_clear_low = calculate_clearing_speed_limit(
            nozzle_velocity=Q_(300, ureg.m / ureg.s), **base_params
        )
        v_clear_high = calculate_clearing_speed_limit(
            nozzle_velocity=Q_(600, ureg.m / ureg.s), **base_params
        )

        assert v_clear_high > v_clear_low, \
            "Higher gas velocity should enable faster clearing"

        # Should scale with v² (momentum flux)
        ratio = v_clear_high.magnitude / v_clear_low.magnitude
        expected_ratio = (600 / 300) ** 2  # = 4
        assert pytest.approx(ratio, rel=0.1) == expected_ratio

    def test_clearing_speed_nozzle_diameter_effect(self):
        """Larger nozzle should allow faster clearing (more gas flow)."""
        base_params = {
            'nozzle_velocity': Q_(500, ureg.m / ureg.s),
            'kerf_width': Q_(1.5, ureg.mm),
            'material_density': Q_(7850, ureg.kg / ureg.m**3),
            'gas_density': Q_(12.0, ureg.kg / ureg.m**3),
            'efficiency_factor': 0.1
        }

        v_clear_small = calculate_clearing_speed_limit(
            nozzle_diameter=Q_(1.0, ureg.mm), **base_params
        )
        v_clear_large = calculate_clearing_speed_limit(
            nozzle_diameter=Q_(3.0, ureg.mm), **base_params
        )

        assert v_clear_large > v_clear_small, \
            "Larger nozzle should enable faster clearing"

    def test_clearing_speed_material_density_effect(self):
        """
        Denser material should reduce clearing speed limit.

        Heavier material is harder to eject with same gas momentum
        """
        base_params = {
            'nozzle_velocity': Q_(500, ureg.m / ureg.s),
            'nozzle_diameter': Q_(2.0, ureg.mm),
            'kerf_width': Q_(1.5, ureg.mm),
            'gas_density': Q_(12.0, ureg.kg / ureg.m**3),
            'efficiency_factor': 0.1
        }

        v_clear_aluminum = calculate_clearing_speed_limit(
            material_density=Q_(2700, ureg.kg / ureg.m**3), **base_params
        )
        v_clear_steel = calculate_clearing_speed_limit(
            material_density=Q_(7850, ureg.kg / ureg.m**3), **base_params
        )

        assert v_clear_aluminum > v_clear_steel, \
            "Lighter material (aluminum) should have higher clearing speed than heavier (steel)"

    def test_clearing_speed_efficiency_factor_effect(self):
        """Higher efficiency factor should increase clearing speed."""
        base_params = {
            'nozzle_velocity': Q_(500, ureg.m / ureg.s),
            'nozzle_diameter': Q_(2.0, ureg.mm),
            'kerf_width': Q_(1.5, ureg.mm),
            'material_density': Q_(7850, ureg.kg / ureg.m**3),
            'gas_density': Q_(12.0, ureg.kg / ureg.m**3)
        }

        v_clear_conservative = calculate_clearing_speed_limit(
            efficiency_factor=0.1, **base_params
        )
        v_clear_optimistic = calculate_clearing_speed_limit(
            efficiency_factor=0.5, **base_params
        )

        ratio = v_clear_optimistic.magnitude / v_clear_conservative.magnitude
        assert pytest.approx(ratio, rel=0.05) == 5.0, \
            "Clearing speed should scale linearly with efficiency factor"

    def test_zero_nozzle_velocity_raises_error(self):
        """Zero nozzle velocity should raise ValueError."""
        with pytest.raises(ValueError, match="Nozzle velocity must be positive"):
            calculate_clearing_speed_limit(
                Q_(0, ureg.m / ureg.s), Q_(2, ureg.mm), Q_(1.5, ureg.mm),
                Q_(7850, ureg.kg / ureg.m**3), Q_(12, ureg.kg / ureg.m**3), 0.1
            )

    def test_zero_nozzle_diameter_raises_error(self):
        """Zero nozzle diameter should raise ValueError."""
        with pytest.raises(ValueError, match="Nozzle diameter must be positive"):
            calculate_clearing_speed_limit(
                Q_(500, ureg.m / ureg.s), Q_(0, ureg.mm), Q_(1.5, ureg.mm),
                Q_(7850, ureg.kg / ureg.m**3), Q_(12, ureg.kg / ureg.m**3), 0.1
            )

    def test_invalid_efficiency_factor_raises_error(self):
        """Efficiency factor outside [0, 1] should raise ValueError."""
        with pytest.raises(ValueError, match="Efficiency factor must be between 0 and 1"):
            calculate_clearing_speed_limit(
                Q_(500, ureg.m / ureg.s), Q_(2, ureg.mm), Q_(1.5, ureg.mm),
                Q_(7850, ureg.kg / ureg.m**3), Q_(12, ureg.kg / ureg.m**3), 1.5
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
