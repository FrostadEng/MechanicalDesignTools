# mech_core Library

A mechanical engineering calculation library with clear separation between **analysis** (mathematical solvers) and **standards** (lookup tables and reference data).

## Structure

```
mech_core/
├── __init__.py
├── units.py               # Pint unit registry for dimensional analysis
│
├── analysis/              # THE SOLVERS (Math & Calculations)
│   ├── __init__.py
│   ├── beams.py          # Beam bending & lateral-torsional buckling (AISC 360-16)
│   ├── columns.py        # Column compression & buckling (AISC 360-16)
│   ├── bolted_joint.py   # Bolted joint analysis (VDI 2230)
│   ├── rigid_body.py     # Robot payload calculations
│   ├── safety.py         # Laser safety (MPE/NOHD)
│   └── fluids.py         # Assist gas calculations
│
├── components/           # THE OBJECTS (Engineering Components)
│   ├── __init__.py
│   ├── fastener.py       # Fastener objects
│   └── aisc_members.py   # AISC steel sections (database, properties, queries)
│
└── standards/            # THE DATA (Lookup Tables & Standards)
    ├── __init__.py
    │
    ├── fasteners/        # Fastener specifications
    │   ├── __init__.py
    │   └── iso_metric.py # ISO metric bolts/threads
    │
    └── materials/        # Material properties
        ├── __init__.py
        ├── aisc_shapes.json  # AISC steel shapes database v16.0
        ├── structural.py     # Structural steel (ASTM A36, A992, A500)
        └── common_steels.py  # General steels
```

## Philosophy

### analysis/ - The Solvers
Contains the mathematical logic and computational methods:
- Calculate forces, stresses, safety factors
- Solve equations
- Run simulations
- The "scribbles on paper" that you'd do by hand

### standards/ - The Data
Contains reference data from handbooks and specifications:
- Thread dimensions (ISO 68-1)
- Bolt strength grades (ISO 898-1)
- Material properties (ASTM, AISI)
- Lookup tables and constants
- No calculations, just data

## Usage Examples

### Example 1: Using Standards Data Only

```python
from mech_core.standards.fasteners import iso_metric
from mech_core.standards.materials import common_steels

# Get thread dimensions
thread = iso_metric.get_thread_info("M12")
print(f"M12 pitch: {thread['pitch']} mm")

# Get bolt strength
proof_load = iso_metric.get_proof_load("M12", "8.8")
print(f"Proof load: {proof_load / 1000:.1f} kN")

# Get material properties
steel = common_steels.get_material("A36")
print(f"Yield strength: {steel.yield_strength} MPa")
```

### Example 2: Combining Standards + Analysis

```python
from mech_core.standards.fasteners import iso_metric
from mech_core.standards.materials import common_steels
from mech_core.analysis.bolted_joint import (
    BoltedJoint,
    BoltedJointGeometry,
    BoltedJointMaterials
)

# Get DATA from standards
stress_area = iso_metric.get_stress_area("M12")
steel = common_steels.get_material("A36")
bolt_props = iso_metric.ISO_PROPERTY_CLASSES["8.8"]

# Define geometry
geometry = BoltedJointGeometry(
    bolt_diameter=12.0,
    thread_pitch=1.75,
    grip_length=40.0,
    head_diameter=18.0,
    through_hole_diameter=13.0
)

# Define materials (using standards data)
materials = BoltedJointMaterials(
    bolt_modulus=200,
    member_modulus=steel.elastic_modulus,
    bolt_yield=bolt_props['proof_stress']
)

# Run ANALYSIS (the solver)
joint = BoltedJoint(geometry, materials, stress_area)
results = joint.analyze_external_load(
    preload=30000,      # N
    external_load=10000  # N
)

print(f"Safety factor: {results['yield_safety']:.2f}")
```

### Example 3: Structural Steel Design

```python
from mech_core.units import ureg
from mech_core.components.aisc_members import get_section, get_shapes_by_type
from mech_core.standards.materials.structural import get_material
from mech_core.analysis.columns import calculate_compressive_strength

# Get DATA from standards
steel = get_material("ASTM A36")  # Fy = 250 MPa, E = 200 GPa
w_shapes = get_shapes_by_type("W", sort_by="W")  # All W-shapes, sorted by weight

# Design parameters
column_height = 3.0 * ureg.meter
required_capacity = 100 * ureg.kN
k_factor = 1.0  # Pinned-pinned

# Find lightest adequate column (the solver)
for shape_name in w_shapes:
    section = get_section(shape_name)
    result = calculate_compressive_strength(section, steel, column_height, k_factor)

    if result['Pu_capacity'] >= required_capacity:
        print(f"Selected: {shape_name}")
        print(f"Capacity: {result['Pu_capacity']:.2f}")
        print(f"Slenderness: {result['slenderness']:.1f}")
        print(f"Mode: {result['failure_mode']}")
        break
```

### Example 4: Laser Safety Calculation

```python
from mech_core.analysis.safety import LaserBeam, calculate_nohd

# Define laser (the data)
laser = LaserBeam(
    power=100,        # Watts
    wavelength=1064,  # nm (Nd:YAG)
    beam_diameter=5,  # mm
    divergence=1.0    # mrad
)

# Run calculation (the solver)
nohd = calculate_nohd(laser)
print(f"Nominal Ocular Hazard Distance: {nohd:.1f} m")
```

## Available Modules

### analysis/beams.py
- `calculate_strong_axis_bending()` - Flexural design per AISC 360-16 Chapter F
- Yielding limit state (Mp = Fy * Zx)
- Lateral-torsional buckling (LTB) zones 1, 2, 3
- LRFD moment capacity (φMn)

### analysis/columns.py
- `calculate_compressive_strength()` - Compression design per AISC 360-16 Chapter E
- Slenderness ratio (KL/r)
- Elastic vs inelastic buckling modes
- LRFD capacity (φPn)

### analysis/bolted_joint.py
- `BoltedJoint` - Joint stiffness analysis
- `BoltedJointGeometry` - Geometry definition
- `BoltedJointMaterials` - Material properties
- `calculate_bearing_stress()` - Bearing calculations
- `calculate_shear_stress()` - Shear calculations
- `eccentric_shear_load()` - Eccentric loading

### analysis/rigid_body.py
- `RigidBody` - Mass properties and moments
- `combine_rigid_bodies()` - Combine multiple bodies
- Robot payload analysis

### analysis/safety.py
- `LaserBeam` - Laser beam properties
- `calculate_mpe()` - Maximum Permissible Exposure
- `calculate_nohd()` - Nominal Ocular Hazard Distance

### analysis/fluids.py
- `reynolds_number()` - Reynolds number calculation
- `pressure_drop_pipe()` - Darcy-Weisbach pressure drop
- `nozzle_flow_rate()` - Compressible flow through nozzle

### standards/fasteners/iso_metric.py
- `ISO_METRIC_THREADS` - Thread dimensions (ISO 68-1)
- `ISO_PROPERTY_CLASSES` - Bolt grades (ISO 898-1)
- `get_stress_area()` - Thread stress area
- `get_proof_load()` - Bolt proof load
- `get_recommended_torque()` - Assembly torque

### components/aisc_members.py
- `SectionProperties` - AISC section property class with automatic unit scaling
- `get_section()` - Retrieve section by name (e.g., "W12X26", "C8X18.75")
- `get_shapes_by_type()` - Get all shapes of a type (W, C, L, HSS, etc.)
- `get_shapes_in_range()` - Filter shapes by property ranges
- `get_lightest_shape()` - Find most economical section meeting criteria
- `get_available_types()` - List all shape types in database
- `search_shapes()` - Search by name pattern

### standards/materials/structural.py
- `StructuralMaterial` - Material property class with Pint units
- `get_material()` - Lookup structural steel (ASTM A36, A992, A500)
- Yield strength, elastic modulus, density

### standards/materials/common_steels.py
- `STEELS` - Material property database
- `MaterialProperties` - Material data class
- `get_material()` - Lookup material by designation
- `SAFETY_FACTORS` - Recommended design factors

## Adding New Modules

### Adding New Standards Data

Create a new file in `standards/`:

```python
# standards/materials/aluminum_alloys.py

ALUMINUM_6061_T6 = {
    "density": 2700,  # kg/m^3
    "yield_strength": 276,  # MPa
    # ... more properties
}
```

### Adding New Analysis Functions

Create a new file in `analysis/`:

```python
# analysis/beam_bending.py

def calculate_deflection(load, length, modulus, moment_of_inertia):
    """Calculate beam deflection using equations."""
    # Mathematical solver logic here
    return deflection
```

## Running the Demo

```bash
cd engineering_tools
python demo_bolted_joint.py
```

This demonstrates the complete workflow:
1. Get thread data from ISO standards
2. Get material properties
3. Define joint geometry
4. Run bolted joint analysis
5. Calculate safety factors

## References

- ISO 68-1: Basic profile of metric threads
- ISO 898-1: Mechanical properties of fasteners
- VDI 2230: Systematic calculation of bolted joints
- ANSI Z136.1: Laser safety standards
- Shigley's Mechanical Engineering Design
