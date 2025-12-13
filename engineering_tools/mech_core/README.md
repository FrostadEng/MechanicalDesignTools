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
│   ├── beams.py          # Beam bending & LTB (AISC 360-16) - strong/weak axis
│   ├── columns.py        # Column compression & buckling (AISC 360-16) - with BC mapping
│   ├── base_plate.py     # Base plate design (CSA S16) - bearing & anchor bolts
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
    ├── materials/        # Material properties (modular architecture)
    │   ├── __init__.py           # Unified materials API
    │   ├── steel.py              # Structural steel physics (ASTM/CSA)
    │   ├── concrete.py           # Concrete material properties
    │   ├── inventory.py          # Stock thickness manager (singleton)
    │   ├── common_steels.py      # General steels
    │   └── data/
    │       ├── aisc_shapes.json         # AISC steel shapes database v16.0
    │       └── standard_thicknesses.json # Plate/sheet stock sizes
    │
    └── reporting/        # Report generation
        ├── __init__.py
        └── generator.py  # Markdown calculation package generator
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

### Example 3: Structural Steel Design with Reporting

```python
from mech_core.units import ureg
from mech_core.components.aisc_members import get_section, get_shapes_by_type
from mech_core.standards.materials import get_material, get_concrete, stock
from mech_core.analysis.columns import calculate_compressive_strength
from mech_core.analysis.base_plate import BasePlateDesign
from mech_core.standards.reporting.generator import ReportGenerator

# Initialize report
report = ReportGenerator("Column Design", "Engineer Name")
report.add_header()

# Get DATA from standards
steel = get_material("ASTM A36")  # Fy = 250 MPa, E = 200 GPa
concrete = get_concrete(25)  # 25 MPa concrete
w_shapes = get_shapes_by_type("W", sort_by="W")  # All W-shapes, sorted by weight

# Design parameters
column_height = 3.0 * ureg.meter
required_capacity = 100 * ureg.kN

# Find lightest adequate column (the solver)
for shape_name in w_shapes:
    section = get_section(shape_name)
    result = calculate_compressive_strength(
        section, steel, column_height,
        ["pinned", "pinned"]  # Boundary conditions
    )

    if result['Pu_capacity'] >= required_capacity:
        print(f"Selected: {shape_name}")
        report.add_calculation_result(f"Column: {shape_name}", result, "PASS")

        # Design base plate
        base_plate = BasePlateDesign(
            column=section,
            load_Pu=required_capacity,
            steel_grade=steel,
            concrete=concrete
        )
        report.add_module(base_plate)
        break

# Save professional calculation package
report.save("Column_Design.md")
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
- `calculate_bending_capacity()` - Flexural design per AISC 360-16 Chapter F
- Strong axis (X-X) and weak axis (Y-Y) bending
- Yielding limit state (Mp = Fy * Z)
- Lateral-torsional buckling (LTB) zones 1, 2, 3 for strong axis
- LRFD moment capacity (φMn)
- `generate_markdown()` - Report generation

### analysis/columns.py
- `calculate_compressive_strength()` - Compression design per AISC 360-16 Chapter E
- Boundary condition mapping (string-based: `["pinned", "pinned"]`, `["fixed", "free"]`)
- Slenderness ratio (KL/r)
- Elastic vs inelastic buckling modes
- LRFD capacity (φPn)
- `generate_markdown()` - Report generation

### analysis/base_plate.py
- `BasePlateDesign` - Base plate design per CSA S16
- Bearing pressure on concrete (CSA A23.3)
- Required thickness calculation
- Standard thickness selection from inventory
- 4-bolt anchor pattern layout
- Edge distance and spacing checks
- `generate_markdown()` - Integrated reporting

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

### standards/materials/ (Modular Architecture)
**Unified API through `__init__.py`:**
- `get_material()` - Structural steel (ASTM A36, A992, CSA G40.21 350W/300W)
- `get_concrete()` - Concrete materials with configurable fc'
- `stock` - Singleton for standard thickness lookups

**Internal modules:**
- `steel.py` - `StructuralMaterial` dataclass with Pint units
- `concrete.py` - `ConcreteMaterial` dataclass
- `inventory.py` - `MaterialStockManager` singleton for plate/sheet thicknesses
- `common_steels.py` - General purpose steels

**Data files:**
- `data/aisc_shapes.json` - AISC section database
- `data/standard_thicknesses.json` - Stock plate/sheet sizes (metric/imperial)

### standards/reporting/generator.py
- `ReportGenerator` - Professional markdown calculation packages
- `add_header()`, `add_section()`, `add_text()` - Report building
- `add_calculation_result()` - Formatted calculation results
- `add_module()` - Integrate analysis modules with reporting
- `save()` - Export to .md files

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
