# Mechanical Design Tools

A Python-based engineering toolset for structural steel design calculations following AISC 360-16 standards with full unit handling using Pint.

## Features

- **Structural Analysis**
  - Column design (AISC 360-16 compression with boundary condition mapping)
  - Beam design (strong and weak axis bending, lateral-torsional buckling)
  - Base plate design (bearing pressure, anchor bolt layout per CSA S16)
  - LRFD (Load and Resistance Factor Design) methodology

- **AISC Steel Database**
  - Complete AISC shapes database (W, C, L, HSS, etc.)
  - Query and filter functions for section selection
  - Metric and imperial units support

- **Material Management**
  - Structural steel properties (ASTM A36, A992, CSA G40.21)
  - Concrete materials (configurable fc')
  - Stock thickness availability system
  - Standard plate and sheet thickness lookups

- **Professional Reporting**
  - Markdown report generation for calculation packages
  - Modular report components
  - Export calculations to professional documentation

- **Unit-Aware Calculations**
  - Full integration with Pint for dimensional analysis
  - Automatic unit conversions
  - Prevents unit-related errors

## Project Structure

```
MechanicalDesignTools/
├── engineering_tools/
│   ├── mech_core/                 # Core engineering modules
│   │   ├── analysis/              # Structural analysis modules
│   │   │   ├── beams.py          # Beam bending (strong/weak axis, LTB)
│   │   │   ├── columns.py        # Column compression with boundary conditions
│   │   │   └── base_plate.py     # Base plate design & anchor bolts
│   │   ├── components/           # Engineering components & objects
│   │   │   ├── fastener.py       # Fastener objects
│   │   │   └── aisc_members.py   # AISC steel sections (database & queries)
│   │   ├── standards/            # Standards & material databases
│   │   │   ├── materials/
│   │   │   │   ├── data/
│   │   │   │   │   ├── aisc_shapes.json         # AISC shapes database
│   │   │   │   │   └── standard_thicknesses.json # Stock plate/sheet sizes
│   │   │   │   ├── steel.py          # Structural steel properties
│   │   │   │   ├── concrete.py       # Concrete materials
│   │   │   │   ├── inventory.py      # Stock thickness manager
│   │   │   │   └── __init__.py       # Unified materials API
│   │   │   ├── reporting/
│   │   │   │   └── generator.py      # Markdown report generator
│   │   │   └── fasteners/        # Fastener standards
│   │   └── units.py              # Pint unit registry
│   └── projects/                 # Design project examples
│       └── mezzanine_design/
│           ├── design_mezzanine.py          # Full structural design
│           └── Mezzanine_Calc_Package.md    # Generated calculation report
└── README.md
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/MechanicalDesignTools.git
cd MechanicalDesignTools
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r engineering_tools/requirements.txt
```

## Quick Start

### Example: Designing a Mezzanine Structure

```python
from mech_core.units import ureg
from mech_core.components.aisc_members import get_section, get_shapes_by_type
from mech_core.standards.materials import get_material, get_concrete
from mech_core.analysis.columns import calculate_compressive_strength
from mech_core.analysis.beams import calculate_bending_capacity
from mech_core.analysis.base_plate import BasePlateDesign
from mech_core.standards.reporting.generator import ReportGenerator

# Initialize report
report = ReportGenerator("Mezzanine Structural Design", "Engineering Co.")
report.add_header()

# Define loads
live_load = (500 * ureg.kg / ureg.meter**2) * 9.81 * ureg.meter/ureg.second**2
area = 4.0 * ureg.meter * 4.0 * ureg.meter
factored_load = live_load * area * 1.5

# Select materials
steel = get_material("ASTM A36")
concrete = get_concrete(25)  # 25 MPa concrete

# Find adequate beam - iterate through C-channels
beam_candidates = get_shapes_by_type("C", sort_by="W")
for beam_name in beam_candidates:
    section = get_section(beam_name)
    result = calculate_bending_capacity(section, steel, unbraced_length=4.0*ureg.meter)
    if result['Mu_capacity'] >= required_moment:
        print(f"Selected beam: {beam_name}")
        report.add_calculation_result(f"Beam: {beam_name}", result, "PASS")
        break

# Find adequate column - iterate through W-shapes
col_candidates = get_shapes_by_type("W", sort_by="W")
for col_name in col_candidates:
    section = get_section(col_name)
    result = calculate_compressive_strength(
        section, steel, 3.0*ureg.meter,
        ["pinned", "pinned"]  # Boundary conditions
    )
    if result['Pu_capacity'] >= required_load:
        print(f"Selected column: {col_name}")
        report.add_calculation_result(f"Column: {col_name}", result, "PASS")
        break

# Design base plate
base_plate = BasePlateDesign(
    column=section,
    load_Pu=factored_load/4,
    steel_grade=steel,
    concrete=concrete
)
report.add_module(base_plate)

# Save report
report.save("Structural_Calc_Package.md")
```

Run the example:
```bash
cd engineering_tools
python projects/mezzanine_design/design_mezzanine.py
```

## Core Modules

### `mech_core.analysis.columns`
Column design per AISC 360-16 Chapter E (Compression Members)
- Boundary condition mapping (`["pinned", "pinned"]`, `["fixed", "free"]`, etc.)
- Slenderness ratio calculation (KL/r)
- Elastic vs inelastic buckling modes
- LRFD capacity (φPn)
- Markdown report generation

### `mech_core.analysis.beams`
Beam design per AISC 360-16 Chapter F (Flexural Members)
- Strong axis (X-X) and weak axis (Y-Y) bending
- Yielding limit state (Mp = Fy * Z)
- Lateral-torsional buckling (LTB) for strong axis
- LRFD moment capacity (φMn)
- Markdown report generation

### `mech_core.analysis.base_plate`
Base plate design per CSA S16
- Bearing pressure on concrete
- Required plate thickness calculation
- Standard thickness selection from inventory
- Anchor bolt layout (4-bolt pattern)
- Edge distance and spacing checks
- Integrated reporting

### `mech_core.standards.materials`
Material property management with separation of concerns:
- `get_material()` - Structural steel (ASTM A36, A992, CSA G40.21)
- `get_concrete()` - Concrete materials with configurable fc'
- `stock` - Singleton manager for standard plate/sheet thicknesses
- Metric and imperial thickness lookups

### `mech_core.standards.reporting`
Professional calculation package generation:
- `ReportGenerator` - Markdown report builder
- Modular calculation sections
- Automatic formatting for results
- Export to .md files for documentation

### `mech_core.components.aisc_members`
AISC steel section database and query utilities:
- `get_section()` - Retrieve section by name
- `get_shapes_by_type()` - Get all shapes of a type
- `get_shapes_in_range()` - Filter by property ranges
- `get_lightest_shape()` - Find most economical section
- `SectionProperties` - Section property class with automatic unit scaling

## Standards & References

- **AISC 360-16**: Specification for Structural Steel Buildings
- **CSA S16**: Design of Steel Structures (Canadian Standard)
- **CSA A23.3**: Design of Concrete Structures
- **AISC Database v16.0**: Steel section properties (metric)
- **LRFD/LSD Method**: Load and Resistance Factor Design

## Requirements

- Python 3.8+
- numpy >= 1.24.0
- scipy >= 1.10.0
- pandas >= 2.0.0
- matplotlib >= 3.7.0
- pint >= 0.21.0

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is provided as-is for educational and professional use.

## Recent Additions

- ✅ Base plate design with anchor bolt layout
- ✅ Markdown report generation system
- ✅ Material inventory management (stock thicknesses)
- ✅ Boundary condition string mapping for columns
- ✅ Weak axis bending support for beams
- ✅ Modular materials architecture (steel/concrete/inventory)

## Future Development

- [ ] Shear design for beams
- [ ] Welded and bolted connection design
- [ ] Seismic design provisions (CSA S16 seismic)
- [ ] Wind load calculations (NBCC 2020)
- [ ] Web interface for calculations
- [ ] PDF report generation from markdown
- [ ] Moment connection design
- [ ] Composite beam design

## Author

Built with structural engineering best practices and AISC standards compliance.