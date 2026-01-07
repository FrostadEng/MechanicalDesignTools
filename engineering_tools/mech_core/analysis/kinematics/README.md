# Kinematics API

Core kinematic analysis functions for mechanical systems. Provides calculations for position, velocity, acceleration, and trajectory analysis in 1D, 2D, and 3D space.

## Installation

```python
from mech_core.analysis.kinematics import *
from mech_core.standards.units import ureg
```

The module is set up with a clean API through [`__init__.py`](__init__.py) that exports all functions.

## Core Features

### Linear Motion
Calculate position, velocity, and acceleration for linear systems:
- `linear_velocity(displacement, time)` - v = Δx / Δt
- `linear_acceleration(velocity_change, time)` - a = Δv / Δt
- `position_from_constant_acceleration(x₀, v₀, a, t)` - x = x₀ + v₀t + ½at²
- `time_to_position(target, x₀, v₀, a)` - Solve for time to reach target

### Rotational Motion
Handle angular kinematics and circular motion:
- `angular_velocity(angle_change, time)` - ω = Δθ / Δt
- `tangential_velocity(angular_velocity, radius)` - v = ωr
- `centripetal_acceleration(velocity, radius)` - aᶜ = v²/r
- `rpm_to_rad_per_sec(rpm)` - Unit conversion helper

### Trajectory Analysis
Projectile motion and ballistics:
- `trajectory_time_of_flight(v₀y, h₀, g)` - Time until landing
- `trajectory_range(v₀, angle, h₀, g)` - Horizontal distance
- `trajectory_max_height(v₀y, h₀, g)` - Peak height

### Path Planning
Motion profile generation for automation:
- `velocity_profile_trapezoidal(distance, v_max, accel)` - Returns (time, position, velocity) arrays
- `interpolate_linear_path(start, end, num_points)` - Linear interpolation
- `calculate_path_length(positions)` - Total path distance

### Mechanism Kinematics
Linkage and mechanism analysis:
- `forward_kinematics_2r(θ₁, θ₂, L₁, L₂)` - 2-link planar robot arm position
- `slider_crank_position(θ, r, l)` - Piston position from crank angle
- `slider_crank_velocity(θ, ω, r, l)` - Slider velocity

## Usage Examples

### Linear Motion
```python
# Calculate velocity
v = linear_velocity(100 * ureg.meter, 5 * ureg.second)
# Result: 20.0 m/s

# Find time to reach position
t = time_to_position(
    target_position=100 * ureg.meter,
    initial_position=0 * ureg.meter,
    initial_velocity=10 * ureg.m/ureg.s,
    acceleration=2 * ureg.m/ureg.s**2
)
```

### Rotational Motion
```python
# Convert motor speed and find tangential velocity
omega = rpm_to_rad_per_sec(1800 * ureg.rpm)
v_tangential = tangential_velocity(omega, 0.5 * ureg.meter)

# Calculate centripetal acceleration
a_c = centripetal_acceleration(v_tangential, 0.5 * ureg.meter)
```

### Velocity Profile for CNC
```python
# Generate trapezoidal motion profile
time, position, velocity = velocity_profile_trapezoidal(
    total_distance=1.0 * ureg.meter,
    max_velocity=0.5 * ureg.m/ureg.s,
    acceleration=2.0 * ureg.m/ureg.s**2,
    num_points=100
)
# Returns numpy arrays with units attached
```

### Robot Arm Forward Kinematics
```python
# Calculate end effector position
x, y = forward_kinematics_2r(
    theta1=45 * ureg.degree,
    theta2=30 * ureg.degree,
    L1=1.0 * ureg.meter,
    L2=0.8 * ureg.meter
)
```

### Slider-Crank Mechanism
```python
# Find piston position in engine
x_piston = slider_crank_position(
    crank_angle=90 * ureg.degree,
    crank_length=0.05 * ureg.meter,   # 50mm crank
    rod_length=0.15 * ureg.meter      # 150mm connecting rod
)

# Calculate piston velocity
v_piston = slider_crank_velocity(
    crank_angle=90 * ureg.degree,
    crank_angular_velocity=3000 * ureg.rpm,
    crank_length=0.05 * ureg.meter,
    rod_length=0.15 * ureg.meter
)
```

## Common Applications

- **Robot arm motion planning** - Forward kinematics and path interpolation
- **CNC machine tool paths** - Velocity profiles and trajectory verification
- **Conveyor systems** - Linear motion analysis
- **Engine design** - Slider-crank kinematics
- **Projectile systems** - Trajectory calculations
- **Rotating machinery** - Angular velocity and centripetal forces

## Units

All functions use Pint units (`ureg`) from `mech_core.standards.units`. The API automatically handles unit conversions and dimensional analysis.

## API Reference

See [`kinematics.py`](kinematics.py:1) for complete function documentation with detailed parameter descriptions and examples.
