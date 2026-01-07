"""
mech_core/analysis/kinematics/kinematics.py

Core kinematic analysis functions for mechanical systems.
Provides basic kinematic calculations for position, velocity, acceleration,
and trajectory analysis in 1D, 2D, and 3D space.

Common use cases:
- Robot arm motion planning
- CNC machine tool path verification
- Conveyor and transport system analysis
- Mechanism simulation and design
"""

import numpy as np
from ...standards.units import ureg, Q_
from typing import Union, Tuple, List, Optional


# ==========================================
# Position, Velocity, Acceleration (1D)
# ==========================================

def linear_velocity(displacement: Q_, time: Q_) -> Q_:
    """
    Calculate average linear velocity.
    v = Δx / Δt

    Args:
        displacement: Distance traveled
        time: Time elapsed

    Returns:
        Velocity (m/s or compatible units)

    Example:
        >>> v = linear_velocity(10*ureg.meter, 2*ureg.second)
        >>> print(v)
        5.000 meter / second
    """
    return displacement / time


def linear_acceleration(velocity_change: Q_, time: Q_) -> Q_:
    """
    Calculate average linear acceleration.
    a = Δv / Δt

    Args:
        velocity_change: Change in velocity
        time: Time elapsed

    Returns:
        Acceleration (m/s^2 or compatible units)
    """
    return velocity_change / time


def position_from_constant_acceleration(
    initial_position: Q_,
    initial_velocity: Q_,
    acceleration: Q_,
    time: Q_
) -> Q_:
    """
    Calculate position under constant acceleration.
    x = x₀ + v₀*t + (1/2)*a*t²

    Args:
        initial_position: Starting position
        initial_velocity: Starting velocity
        acceleration: Constant acceleration
        time: Time elapsed

    Returns:
        Final position
    """
    return initial_position + initial_velocity * time + 0.5 * acceleration * time**2


def velocity_from_constant_acceleration(
    initial_velocity: Q_,
    acceleration: Q_,
    time: Q_
) -> Q_:
    """
    Calculate velocity under constant acceleration.
    v = v₀ + a*t

    Args:
        initial_velocity: Starting velocity
        acceleration: Constant acceleration
        time: Time elapsed

    Returns:
        Final velocity
    """
    return initial_velocity + acceleration * time


def time_to_position(
    target_position: Q_,
    initial_position: Q_,
    initial_velocity: Q_,
    acceleration: Q_
) -> Q_:
    """
    Calculate time to reach a target position under constant acceleration.
    Solves: x = x₀ + v₀*t + (1/2)*a*t²

    Args:
        target_position: Desired position
        initial_position: Starting position
        initial_velocity: Starting velocity
        acceleration: Constant acceleration

    Returns:
        Time to reach target (returns smallest positive root)

    Raises:
        ValueError: If no real solution exists
    """
    # Convert to: (1/2)*a*t² + v₀*t + (x₀ - x) = 0
    a_coeff = 0.5 * acceleration.magnitude
    b_coeff = initial_velocity.magnitude
    c_coeff = (initial_position - target_position).magnitude

    discriminant = b_coeff**2 - 4 * a_coeff * c_coeff

    if discriminant < 0:
        raise ValueError("No real solution: target position unreachable")

    t1 = (-b_coeff + np.sqrt(discriminant)) / (2 * a_coeff)
    t2 = (-b_coeff - np.sqrt(discriminant)) / (2 * a_coeff)

    # Return smallest positive time
    times = [t for t in [t1, t2] if t > 0]
    if not times:
        raise ValueError("No positive time solution")

    return min(times) * ureg.second


# ==========================================
# Rotational Kinematics
# ==========================================

def angular_velocity(angle_change: Q_, time: Q_) -> Q_:
    """
    Calculate average angular velocity.
    ω = Δθ / Δt

    Args:
        angle_change: Change in angle (radians or degrees)
        time: Time elapsed

    Returns:
        Angular velocity (rad/s or compatible)
    """
    return angle_change / time


def angular_acceleration(omega_change: Q_, time: Q_) -> Q_:
    """
    Calculate average angular acceleration.
    α = Δω / Δt

    Args:
        omega_change: Change in angular velocity
        time: Time elapsed

    Returns:
        Angular acceleration (rad/s^2 or compatible)
    """
    return omega_change / time


def tangential_velocity(angular_velocity: Q_, radius: Q_) -> Q_:
    """
    Calculate tangential velocity for circular motion.
    v = ω * r

    Args:
        angular_velocity: Angular velocity (rad/s)
        radius: Distance from rotation axis

    Returns:
        Tangential velocity (m/s)

    Example:
        >>> omega = 60 * ureg.rpm
        >>> v = tangential_velocity(omega.to(ureg.rad/ureg.s), 0.5*ureg.m)
    """
    return angular_velocity * radius


def centripetal_acceleration(velocity: Q_, radius: Q_) -> Q_:
    """
    Calculate centripetal acceleration for circular motion.
    a_c = v² / r

    Args:
        velocity: Tangential velocity
        radius: Radius of circular path

    Returns:
        Centripetal acceleration (m/s^2)
    """
    return velocity**2 / radius


def rpm_to_rad_per_sec(rpm: Q_) -> Q_:
    """
    Convert RPM to radians per second.

    Args:
        rpm: Revolutions per minute

    Returns:
        Angular velocity in rad/s
    """
    return rpm.to(ureg.rad / ureg.second)


# ==========================================
# 2D/3D Vector Kinematics
# ==========================================

def velocity_vector_2d(
    displacement_x: Q_,
    displacement_y: Q_,
    time: Q_
) -> Tuple[Q_, Q_]:
    """
    Calculate 2D velocity components.

    Args:
        displacement_x: X displacement
        displacement_y: Y displacement
        time: Time elapsed

    Returns:
        (vx, vy) velocity components
    """
    vx = displacement_x / time
    vy = displacement_y / time
    return vx, vy


def velocity_magnitude(vx: Q_, vy: Q_, vz: Q_ = None) -> Q_:
    """
    Calculate velocity magnitude from components.
    |v| = sqrt(vx² + vy² + vz²)

    Args:
        vx: X component
        vy: Y component
        vz: Z component (optional, for 3D)

    Returns:
        Velocity magnitude
    """
    if vz is None:
        return np.sqrt(vx**2 + vy**2)
    return np.sqrt(vx**2 + vy**2 + vz**2)


def trajectory_time_of_flight(
    initial_velocity_y: Q_,
    initial_height: Q_,
    gravity: Q_ = 9.81 * ureg.m / ureg.s**2
) -> Q_:
    """
    Calculate time of flight for projectile motion.
    Solves: y = y₀ + v₀*t - (1/2)*g*t²

    Args:
        initial_velocity_y: Initial vertical velocity
        initial_height: Starting height
        gravity: Gravitational acceleration (default 9.81 m/s²)

    Returns:
        Time until object hits ground (y=0)
    """
    # 0 = y₀ + v₀*t - (1/2)*g*t²
    # Rearrange: (1/2)*g*t² - v₀*t - y₀ = 0
    a = 0.5 * gravity.magnitude
    b = -initial_velocity_y.magnitude
    c = -initial_height.magnitude

    discriminant = b**2 - 4 * a * c
    if discriminant < 0:
        raise ValueError("No real solution for time of flight")

    t1 = (-b + np.sqrt(discriminant)) / (2 * a)
    t2 = (-b - np.sqrt(discriminant)) / (2 * a)

    # Return positive time
    return max(t1, t2) * ureg.second


def trajectory_range(
    initial_velocity: Q_,
    launch_angle: Q_,
    initial_height: Q_ = 0 * ureg.meter,
    gravity: Q_ = 9.81 * ureg.m / ureg.s**2
) -> Q_:
    """
    Calculate horizontal range for projectile motion.

    Args:
        initial_velocity: Initial velocity magnitude
        launch_angle: Launch angle from horizontal
        initial_height: Starting height (default 0)
        gravity: Gravitational acceleration (default 9.81 m/s²)

    Returns:
        Horizontal distance traveled
    """
    # Velocity components
    angle_rad = launch_angle.to(ureg.radian).magnitude
    vx = initial_velocity * np.cos(angle_rad)
    vy = initial_velocity * np.sin(angle_rad)

    # Time of flight
    t_flight = trajectory_time_of_flight(vy, initial_height, gravity)

    # Range = vx * t
    return vx * t_flight


def trajectory_max_height(
    initial_velocity_y: Q_,
    initial_height: Q_ = 0 * ureg.meter,
    gravity: Q_ = 9.81 * ureg.m / ureg.s**2
) -> Q_:
    """
    Calculate maximum height for projectile motion.
    v² = v₀² - 2*g*h  (at max height, v=0)

    Args:
        initial_velocity_y: Initial vertical velocity
        initial_height: Starting height (default 0)
        gravity: Gravitational acceleration (default 9.81 m/s²)

    Returns:
        Maximum height reached
    """
    # h_max = v₀² / (2*g) + h₀
    height_gain = initial_velocity_y**2 / (2 * gravity)
    return initial_height + height_gain


# ==========================================
# Path and Trajectory Analysis
# ==========================================

def interpolate_linear_path(
    start_pos: np.ndarray,
    end_pos: np.ndarray,
    num_points: int = 50
) -> np.ndarray:
    """
    Generate linear interpolation between two positions.

    Args:
        start_pos: Starting position [x, y] or [x, y, z]
        end_pos: Ending position [x, y] or [x, y, z]
        num_points: Number of interpolation points

    Returns:
        Array of shape (num_points, ndim) with interpolated positions

    Example:
        >>> path = interpolate_linear_path(
        ...     np.array([0, 0, 0]),
        ...     np.array([10, 5, 2]),
        ...     num_points=100
        ... )
    """
    t = np.linspace(0, 1, num_points)
    return np.outer(1 - t, start_pos) + np.outer(t, end_pos)


def calculate_path_length(positions: np.ndarray) -> float:
    """
    Calculate total path length from a sequence of positions.

    Args:
        positions: Array of shape (n, 2) or (n, 3) with positions

    Returns:
        Total path length (magnitude)

    Example:
        >>> positions = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        >>> length = calculate_path_length(positions)
        >>> print(length)  # Should be 3.0
    """
    if len(positions) < 2:
        return 0.0

    # Calculate distance between consecutive points
    deltas = np.diff(positions, axis=0)
    distances = np.linalg.norm(deltas, axis=1)
    return np.sum(distances)


def velocity_profile_trapezoidal(
    total_distance: Q_,
    max_velocity: Q_,
    acceleration: Q_,
    num_points: int = 100
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate trapezoidal velocity profile (constant acceleration motion).

    Common for CNC machines, robots, and conveyors.

    Profile:
    - Accelerate at constant rate to max velocity
    - Maintain max velocity (cruise)
    - Decelerate at constant rate to stop

    Args:
        total_distance: Total distance to travel
        max_velocity: Maximum velocity during cruise
        acceleration: Acceleration/deceleration rate (same magnitude)
        num_points: Number of points in profile

    Returns:
        (time_array, position_array, velocity_array)

    Example:
        >>> t, pos, vel = velocity_profile_trapezoidal(
        ...     1.0 * ureg.meter,
        ...     0.5 * ureg.m/ureg.s,
        ...     1.0 * ureg.m/ureg.s**2
        ... )
    """
    # Time to reach max velocity
    t_accel = (max_velocity / acceleration).to(ureg.second).magnitude

    # Distance during acceleration
    d_accel = (0.5 * acceleration * (t_accel * ureg.second)**2).to(total_distance.units).magnitude

    # Distance during deceleration (same as acceleration)
    d_decel = d_accel

    # Distance during cruise
    d_cruise = total_distance.magnitude - d_accel - d_decel

    if d_cruise < 0:
        # Can't reach max velocity - triangular profile
        # Calculate actual max velocity
        v_max_actual = np.sqrt(acceleration.magnitude * total_distance.magnitude)
        t_accel = v_max_actual / acceleration.magnitude
        t_cruise = 0
        t_decel = t_accel
        t_total = t_accel + t_decel
    else:
        # Normal trapezoidal profile
        v_max_actual = max_velocity.magnitude
        t_cruise = d_cruise / v_max_actual
        t_decel = t_accel
        t_total = t_accel + t_cruise + t_decel

    # Generate time array
    time = np.linspace(0, t_total, num_points)
    position = np.zeros(num_points)
    velocity = np.zeros(num_points)

    for i, t in enumerate(time):
        if t <= t_accel:
            # Acceleration phase
            velocity[i] = acceleration.magnitude * t
            position[i] = 0.5 * acceleration.magnitude * t**2
        elif t <= t_accel + t_cruise:
            # Cruise phase
            t_cruise_elapsed = t - t_accel
            velocity[i] = v_max_actual
            position[i] = (0.5 * acceleration.magnitude * t_accel**2 +
                          v_max_actual * t_cruise_elapsed)
        else:
            # Deceleration phase
            t_decel_elapsed = t - t_accel - t_cruise
            velocity[i] = v_max_actual - acceleration.magnitude * t_decel_elapsed
            position[i] = (0.5 * acceleration.magnitude * t_accel**2 +
                          v_max_actual * t_cruise +
                          v_max_actual * t_decel_elapsed -
                          0.5 * acceleration.magnitude * t_decel_elapsed**2)

    # Attach units to the arrays
    time_with_units = time * ureg.second
    position_with_units = position * total_distance.units
    velocity_with_units = velocity * max_velocity.units

    return time_with_units, position_with_units, velocity_with_units


# ==========================================
# Joint and Linkage Kinematics
# ==========================================

def forward_kinematics_2r(
    theta1: Q_,
    theta2: Q_,
    L1: Q_,
    L2: Q_
) -> Tuple[Q_, Q_]:
    """
    Forward kinematics for 2-link planar robot arm.

    Calculates end effector position from joint angles.

    Args:
        theta1: First joint angle (from horizontal)
        theta2: Second joint angle (relative to first link)
        L1: First link length
        L2: Second link length

    Returns:
        (x, y) end effector position

    Example:
        >>> x, y = forward_kinematics_2r(
        ...     45 * ureg.degree,
        ...     30 * ureg.degree,
        ...     1.0 * ureg.meter,
        ...     0.8 * ureg.meter
        ... )
    """
    theta1_rad = theta1.to(ureg.radian).magnitude
    theta2_rad = theta2.to(ureg.radian).magnitude

    # Position of first joint (elbow)
    x1 = L1 * np.cos(theta1_rad)
    y1 = L1 * np.sin(theta1_rad)

    # Position of end effector
    x2 = x1 + L2 * np.cos(theta1_rad + theta2_rad)
    y2 = y1 + L2 * np.sin(theta1_rad + theta2_rad)

    return x2, y2


def slider_crank_position(
    crank_angle: Q_,
    crank_length: Q_,
    rod_length: Q_
) -> Q_:
    """
    Calculate slider position in slider-crank mechanism.

    Common in piston engines, presses, and reciprocating mechanisms.

    Args:
        crank_angle: Crank angle from horizontal (0 = fully extended)
        crank_length: Length of crank (r)
        rod_length: Length of connecting rod (l)

    Returns:
        Slider position (x distance from crank center)

    Example:
        >>> x = slider_crank_position(
        ...     90 * ureg.degree,
        ...     0.05 * ureg.meter,  # 50mm crank
        ...     0.15 * ureg.meter   # 150mm rod
        ... )
    """
    theta = crank_angle.to(ureg.radian).magnitude
    r = crank_length.magnitude
    l = rod_length.magnitude

    # Slider position formula
    x = r * np.cos(theta) + np.sqrt(l**2 - (r * np.sin(theta))**2)

    return x * crank_length.units


def slider_crank_velocity(
    crank_angle: Q_,
    crank_angular_velocity: Q_,
    crank_length: Q_,
    rod_length: Q_
) -> Q_:
    """
    Calculate slider velocity in slider-crank mechanism.

    Args:
        crank_angle: Crank angle from horizontal
        crank_angular_velocity: Angular velocity of crank (ω)
        crank_length: Length of crank (r)
        rod_length: Length of connecting rod (l)

    Returns:
        Slider velocity (dx/dt)
    """
    theta = crank_angle.to(ureg.radian).magnitude
    omega = crank_angular_velocity.to(ureg.rad / ureg.second).magnitude
    r = crank_length.magnitude
    l = rod_length.magnitude

    # Velocity formula (derivative of position)
    sin_theta = np.sin(theta)
    cos_theta = np.cos(theta)

    v = -r * omega * (sin_theta + (r * sin_theta * cos_theta) /
                      np.sqrt(l**2 - (r * sin_theta)**2))

    return v * crank_length.units / ureg.second


# ==========================================
# Utility Functions
# ==========================================

def distance_2d(x1: Q_, y1: Q_, x2: Q_, y2: Q_) -> Q_:
    """Calculate Euclidean distance between two 2D points."""
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def distance_3d(x1: Q_, y1: Q_, z1: Q_, x2: Q_, y2: Q_, z2: Q_) -> Q_:
    """Calculate Euclidean distance between two 3D points."""
    return np.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)


def unit_vector(vector: np.ndarray) -> np.ndarray:
    """
    Calculate unit vector (normalized).

    Args:
        vector: Input vector (1D numpy array)

    Returns:
        Normalized unit vector
    """
    magnitude = np.linalg.norm(vector)
    if magnitude == 0:
        return vector
    return vector / magnitude
