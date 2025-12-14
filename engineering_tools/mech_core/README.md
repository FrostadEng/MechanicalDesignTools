# mech_core Library

A mechanical engineering calculation library with clear separation between **analysis** (mathematical solvers) and **standards** (lookup tables and reference data).

## Structure

```
mech_core/
├── __init__.py
│
├── analysis/              # THE SOLVERS (Pure Physics - Code Agnostic)
│   ├── __init__.py
│   └── fea.py            # FEA wrapper (PyNite integration)
│
├── codes/                 # CODE-SPECIFIC VALIDATORS
│   └── structural/
│       └── csa_s16/
│           ├── members.py      # Beam & column design (CSA S16-19)
│           └── connections.py  # Connection validation (bolt shear, bearing, block shear)
│
├── components/           # THE OBJECTS (Physical Engineering Components)
│   ├── __init__.py
│   ├── fastener.py       # Fastener objects
│   ├── members/
│   │   ├── __init__.py
│   │   └── aisc.py       # AISC steel sections (database & queries)
│   └── connections/
│       ├── axial/
│       │   └── base_plate.py  # Base plate component
│       └── shear/
│           └── fin_plate.py   # Fin plate shear connection
│
└── standards/            # THE DATA (Lookup Tables & Standards)
    ├── __init__.py
    ├── units.py          # Pint unit registry for dimensional analysis
    │
    ├── fasteners/        # Fastener specifications
    │   ├── __init__.py
    │   ├── geometry.py   # Thread & head dimensions
    │   └── materials.py  # Bolt material properties
    │
    ├── materials/        # Material properties (modular architecture)
    │   ├── __init__.py           # Unified materials API
    │   ├── steel.py              # Structural steel physics (ASTM/CSA)
    │   ├── concrete.py           # Concrete material properties
    │   ├── inventory.py          # Stock thickness manager (singleton)
    │   └── data/
    │       ├── aisc_shapes.json         # AISC steel shapes database v16.0
    │       └── standard_thicknesses.json # Plate/sheet stock sizes
    │
    └── reporting/        # Report generation
        ├── __init__.py
        └── generator.py  # Markdown calculation package generator
```

## Philosophy

### analysis/ - Pure Physics Solvers
Contains code-agnostic mathematical solvers:
- FEA integration (PyNite wrapper)
- General mechanics equations
- Physics-based calculations independent of design codes

### codes/ - Code-Specific Validators
Design code validators (CSA S16, future AISC, Eurocode):
- Interprets design codes and standards
- Applies safety factors and resistance factors
- Returns pass/fail with utilization ratios
- Generates symbolic calculation traces

### components/ - Physical Objects
Engineering components with geometry only:
- Store dimensions and properties
- Calculate geometric values (areas, distances)
- Delegate validation to code layers
- No "pass/fail" logic - that's the code's job

### standards/ - The Data
Reference data from handbooks and specifications:
- Thread dimensions (ISO metric)
- Bolt strength grades
- Material properties (ASTM, CSA)
- Stock thickness inventory
- Lookup tables and constants
- No calculations, just data

## Usage Examples

### Example 1: Creating a Standard Bolt

```python
from mech_core.components.fastener import create_standard_bolt
from mech_core.standards.units import ureg

# Create a standard metric bolt
bolt = create_standard_bolt("M12", "8.8")

print(f"Thread pitch: {bolt.thread.pitch}")
print(f"Stress area: {bolt.thread.stress_area}")
print(f"Proof load: {bolt.proof_load.to(ureg.kN)}")
print(f"Shear capacity: {bolt.shear_capacity.to(ureg.kN)}")
```

### Example 2: Structural Steel Design with Reporting

```python
from mech_core.standards.units import ureg
from mech_core.components.members.aisc import get_section, get_shapes_by_type
from mech_core.standards.materials import get_material, get_concrete, stock
from mech_core.codes.structural.csa_s16.members import check_compressive_resistance
from mech_core.components.connections.axial.base_plate import BasePlateDesign
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

# Find lightest adequate column (the validator)
for shape_name in w_shapes:
    section = get_section(shape_name)
    result = check_compressive_resistance(
        section, steel, column_height,
        ["pinned", "pinned"]  # Boundary conditions
    )

    if result['Cr'] >= required_capacity:
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

## Available Modules

### analysis/fea.py
- `FrameAnalysis` - PyNite FEA wrapper for 3D frame analysis
- `add_node()`, `add_beam()` - Build frame geometry
- `add_support()` - Define boundary conditions (pinned, fixed, roller)
- `add_member_dist_load()` - Apply distributed loads
- `solve()` - Run FEA solver
- `get_beam_forces()` - Extract shear, moment, axial forces
- `generate_diagrams()` - Create shear/moment diagrams

### codes/structural/csa_s16/members.py
- `check_compressive_resistance()` - Column design per CSA S16-19 Chapter E
  - Boundary condition mapping (`["pinned", "pinned"]`, `["fixed", "free"]`)
  - Slenderness ratio (KL/r)
  - Elastic vs inelastic buckling modes
  - Returns `Cr` (factored compressive resistance)
- `check_flexural_resistance()` - Beam design per CSA S16-19 Chapter F
  - Strong axis (X-X) and weak axis (Y-Y) bending
  - Yielding limit state (Mp = Fy * Z)
  - Lateral-torsional buckling (LTB) for strong axis
  - Returns `Mr` (factored moment resistance)
- All functions return `calc_trace` with symbolic LaTeX derivations

### codes/structural/csa_s16/connections.py
- `check_bolt_shear()` - Bolt shear resistance per CSA S16-19
- `check_bearing()` - Bearing resistance on plates/webs
- `check_block_shear()` - Block shear rupture (uses Agv for yield, Anv for rupture)
- Returns utilization ratios and calc_trace

### components/connections/axial/base_plate.py
- `BasePlateDesign` - Base plate design component
- Bearing pressure on concrete (CSA A23.3)
- Required thickness calculation
- Standard thickness selection from inventory
- 4-bolt anchor pattern layout
- Edge distance and spacing checks
- `generate_markdown()` - Integrated reporting

### components/connections/shear/fin_plate.py
- `FinPlateConnection` - Fin plate shear connection component
- Calculates geometric properties (net areas, edge distances)
- `analyze()` - Validates connection against design code
- Delegates to CSA S16 validators (bolt shear, bearing, block shear)
- Returns combined calc_trace and individual check results

### components/members/aisc.py
- `SectionProperties` - AISC section property class with automatic unit scaling
- `get_section()` - Retrieve section by name (e.g., "W12X26", "C8X18.75")
- `get_shapes_by_type()` - Get all shapes of a type (W, C, L, HSS, etc.)
- `get_shapes_in_range()` - Filter shapes by property ranges
- `get_lightest_shape()` - Find most economical section meeting criteria
- `get_available_types()` - List all shape types in database
- `search_shapes()` - Search by name pattern

### components/fastener.py
- `Bolt` - Bolt component (thread + head + material)
- `create_standard_bolt()` - Factory for standard metric bolts
- `proof_load`, `shear_capacity` - Calculated properties

### standards/fasteners/geometry.py & materials.py
- `get_metric_thread()` - Thread dimensions (ISO 68-1)
- `get_hex_head()` - Hex head dimensions
- `get_iso_property_class()` - Bolt material properties (ISO 898-1)

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

## Running the Examples

```bash
cd engineering_tools
python projects/mezzanine_design/design_mezzanine.py
```

This demonstrates the complete workflow:
1. Define design loads and materials
2. Select AISC sections from database
3. Run FEA analysis to get internal forces
4. Validate members using CSA S16 code checks
5. Design connections (fin plates, base plates)
6. Generate professional calculation package with symbolic derivations

## References

- **CSA S16-19**: Design of Steel Structures (Canadian Standard)
- **AISC 360-16**: Specification for Structural Steel Buildings
- **CSA A23.3**: Design of Concrete Structures
- **ISO 68-1**: Basic profile of metric threads
- **ISO 898-1**: Mechanical properties of fasteners
- **AISC Database v16.0**: Steel section properties (metric)
