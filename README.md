# Mechanical Design Tools

A Python-based engineering toolset for structural steel design calculations following AISC 360-16 standards with full unit handling using Pint.

## Features

- **Structural Analysis**
  - Column design (AISC 360-16 compression with boundary condition mapping)
  - Beam design (strong and weak axis bending, lateral-torsional buckling)
  - Base plate design (bearing pressure, anchor bolt layout per CSA S16)
  - **FEA Integration** (PyNite wrapper for frame analysis)
  - LRFD (Load and Resistance Factor Design) methodology

- **Finite Element Analysis**
  - PyNite integration for 3D frame analysis
  - Automatic AISC section property mapping
  - Support for distributed and point loads
  - Shear and moment diagram generation
  - Seamless integration with design verification workflows

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
  - **Symbolic mathematical derivations** (step-by-step LaTeX equations)
  - Image embedding (diagrams, charts)
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
│   │   │   ├── base_plate.py     # Base plate design & anchor bolts
│   │   │   └── fea.py            # FEA wrapper (PyNite integration)
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
│   │   │   │   └── generator.py      # Markdown report generator with LaTeX
│   │   │   └── fasteners/        # Fastener standards
│   │   └── units.py              # Pint unit registry
│   └── projects/                 # Design project examples
│       ├── mezzanine_design/
│       │   ├── design_mezzanine.py          # Full structural design with FEA
│       │   ├── Mezzanine_Calc_Package.md    # Generated calculation report
│       │   └── beam_diagrams.png            # Auto-generated FEA diagrams
│       └── test_fea_wrapper.py              # FEA integration tests
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

### Example: Designing a Mezzanine Structure with FEA

```python
from mech_core.units import ureg
from mech_core.components.aisc_members import get_section, get_shapes_by_type
from mech_core.standards.materials import get_material, get_concrete
from mech_core.analysis.fea import FrameAnalysis
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
w_beam = (factored_load / 2) / (4 * ureg.m)  # Distributed load on beam

# Select materials
steel = get_material("ASTM A36")
concrete = get_concrete(25)  # 25 MPa concrete

# Find adequate beam with FEA verification
beam_candidates = get_shapes_by_type("C", sort_by="W")
for beam_name in beam_candidates:
    section = get_section(beam_name)

    # Run FEA to get actual moment
    frame = FrameAnalysis()
    frame.add_node("N1", 0, 0, 0)
    frame.add_node("N2", 4*ureg.m, 0, 0)
    frame.add_beam("B1", "N1", "N2", section, steel)
    frame.add_support("N1", "pinned")
    frame.add_support("N2", "pinned")
    frame.add_member_dist_load("B1", "Fy", -w_beam, -w_beam)
    frame.solve()

    forces = frame.get_beam_forces("B1")
    M_fea = max(abs(forces['max_moment_z'].magnitude),
                abs(forces['min_moment_z'].magnitude)) * ureg.kN * ureg.meter

    # Check capacity with symbolic trace
    result = calculate_bending_capacity(section, steel, unbraced_length=4.0*ureg.meter)
    if result['Mu_capacity'] >= M_fea:
        print(f"Selected beam: {beam_name}")

        # Generate diagrams
        frame.generate_diagrams("B1", "beam_diagrams.png", direction="strong_axis")

        # Add to report with diagrams and symbolic derivation
        report.add_section("Beam Selection (FEA Verified)")
        report.add_image("Shear and Moment Diagrams", "beam_diagrams.png")
        if 'calc_trace' in result:
            report.add_symbolic_derivation(f"Design Check: {beam_name}", result['calc_trace'])
        report.add_calculation_result(f"Beam Summary: {beam_name}", result, "PASS")
        break

# Column design (similar process)
# ... column selection code ...

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

### `mech_core.analysis.fea`
**NEW:** PyNite FEA wrapper for frame analysis
- 3D frame modeling with automatic AISC section integration
- Node and member definition with unit-aware inputs
- Support conditions (fixed, pinned, roller)
- Point and distributed load application
- FEA solver integration
- Force extraction (shear, moment, axial)
- **Diagram generation** (shear/moment plots with matplotlib)
- Seamless Pint unit handling throughout

### `mech_core.analysis.columns`
Column design per AISC 360-16 Chapter E (Compression Members)
- Boundary condition mapping (`["pinned", "pinned"]`, `["fixed", "free"]`, etc.)
- Slenderness ratio calculation (KL/r)
- Elastic vs inelastic buckling modes
- LRFD capacity (φPn)
- Symbolic derivation traces (`calc_trace` with LaTeX equations)

### `mech_core.analysis.beams`
Beam design per AISC 360-16 Chapter F (Flexural Members)
- Strong axis (X-X) and weak axis (Y-Y) bending
- Yielding limit state (Mp = Fy * Z)
- Lateral-torsional buckling (LTB) for strong axis
- LRFD moment capacity (φMn)
- **Symbolic derivation traces** (`calc_trace` with step-by-step LaTeX)

### `mech_core.analysis.base_plate`
Base plate design per CSA S16
- Bearing pressure on concrete
- Required plate thickness calculation
- Standard thickness selection from inventory
- Anchor bolt layout (4-bolt pattern)
- Edge distance and spacing checks
- Integrated markdown reporting

### `mech_core.standards.materials`
Material property management with separation of concerns:
- `get_material()` - Structural steel (ASTM A36, A992, CSA G40.21)
- `get_concrete()` - Concrete materials with configurable fc'
- `stock` - Singleton manager for standard plate/sheet thicknesses
- Metric and imperial thickness lookups

### `mech_core.standards.reporting`
Professional calculation package generation:
- `ReportGenerator` - Markdown report builder
- **Symbolic derivation display** (`add_symbolic_derivation()` with LaTeX rendering)
- **Image embedding** (`add_image()` for diagrams and charts)
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
- PyNiteFEA >= 0.0.90 (for FEA integration)

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is provided as-is for educational and professional use.

## Recent Additions

- ✅ **FEA Integration** (PyNite wrapper with AISC section mapping)
- ✅ **Symbolic derivation traces** (step-by-step LaTeX equations in reports)
- ✅ **Diagram generation** (shear/moment plots from FEA)
- ✅ **Image embedding** in markdown reports
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