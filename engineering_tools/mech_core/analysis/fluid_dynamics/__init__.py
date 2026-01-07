"""
Fluid Dynamics Physics.

Provides calculations for compressible gas flow, nozzle dynamics, and
fluid-related constraints in manufacturing processes.

Modules:
    gas_jets: Compressible flow calculations for assist gas in thermal cutting

Example Usage:
    >>> from engineering_tools.mech_core.analysis.fluid_dynamics import (
    ...     calculate_nozzle_exit_velocity,
    ...     calculate_clearing_speed_limit
    ... )
    >>> from engineering_tools.mech_core.standards.units import ureg, Q_
    >>>
    >>> v_gas = calculate_nozzle_exit_velocity(
    ...     Q_(10, ureg.bar), Q_(1, ureg.bar), Q_(300, ureg.K), 1.4
    ... )
"""

from .gas_jets import (
    calculate_nozzle_exit_velocity,
    calculate_clearing_speed_limit,
    calculate_gas_density_at_nozzle
)

__all__ = [
    'calculate_nozzle_exit_velocity',
    'calculate_clearing_speed_limit',
    'calculate_gas_density_at_nozzle'
]
