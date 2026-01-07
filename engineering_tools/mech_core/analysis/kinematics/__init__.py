"""
mech_core/analysis/kinematics

Kinematic analysis API for mechanical systems.

This module provides functions for:
- Linear motion (position, velocity, acceleration)
- Rotational motion (angular velocity, tangential velocity)
- Projectile motion and trajectories
- Path planning and velocity profiles
- Mechanism kinematics (linkages, slider-cranks)

Example Usage:
    >>> from mech_core.analysis.kinematics import *
    >>> from mech_core.standards.units import ureg
    >>>
    >>> # Linear motion
    >>> v = linear_velocity(100*ureg.meter, 5*ureg.second)
    >>> print(v)  # 20.0 m/s
    >>>
    >>> # Rotational motion
    >>> omega = rpm_to_rad_per_sec(1800*ureg.rpm)
    >>> v_tangential = tangential_velocity(omega, 0.5*ureg.meter)
    >>>
    >>> # Trapezoidal velocity profile for CNC
    >>> time, pos, vel = velocity_profile_trapezoidal(
    ...     total_distance=1.0*ureg.meter,
    ...     max_velocity=0.5*ureg.m/ureg.s,
    ...     acceleration=2.0*ureg.m/ureg.s**2
    ... )
    >>>
    >>> # Robot arm kinematics
    >>> x, y = forward_kinematics_2r(
    ...     theta1=45*ureg.degree,
    ...     theta2=30*ureg.degree,
    ...     L1=1.0*ureg.meter,
    ...     L2=0.8*ureg.meter
    ... )
"""

from .kinematics import (
    # Linear motion
    linear_velocity,
    linear_acceleration,
    position_from_constant_acceleration,
    velocity_from_constant_acceleration,
    time_to_position,

    # Rotational motion
    angular_velocity,
    angular_acceleration,
    tangential_velocity,
    centripetal_acceleration,
    rpm_to_rad_per_sec,

    # Vector kinematics
    velocity_vector_2d,
    velocity_magnitude,
    trajectory_time_of_flight,
    trajectory_range,
    trajectory_max_height,

    # Path analysis
    interpolate_linear_path,
    calculate_path_length,
    velocity_profile_trapezoidal,

    # Mechanisms
    forward_kinematics_2r,
    slider_crank_position,
    slider_crank_velocity,

    # Utilities
    distance_2d,
    distance_3d,
    unit_vector,
)

__all__ = [
    # Linear motion
    'linear_velocity',
    'linear_acceleration',
    'position_from_constant_acceleration',
    'velocity_from_constant_acceleration',
    'time_to_position',

    # Rotational motion
    'angular_velocity',
    'angular_acceleration',
    'tangential_velocity',
    'centripetal_acceleration',
    'rpm_to_rad_per_sec',

    # Vector kinematics
    'velocity_vector_2d',
    'velocity_magnitude',
    'trajectory_time_of_flight',
    'trajectory_range',
    'trajectory_max_height',

    # Path analysis
    'interpolate_linear_path',
    'calculate_path_length',
    'velocity_profile_trapezoidal',

    # Mechanisms
    'forward_kinematics_2r',
    'slider_crank_position',
    'slider_crank_velocity',

    # Utilities
    'distance_2d',
    'distance_3d',
    'unit_vector',
]
