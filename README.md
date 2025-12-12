# Mechanical Design Tools

A Python-based engineering toolset for structural steel design calculations following AISC 360-16 standards with full unit handling using Pint.

## Features

- **Structural Analysis**
  - Column design (AISC 360-16 compression)
  - Beam design (strong-axis bending, lateral-torsional buckling)
  - LRFD (Load and Resistance Factor Design) methodology

- **AISC Steel Database**
  - Complete AISC shapes database (W, C, L, HSS, etc.)
  - Query and filter functions for section selection
  - Metric and imperial units support

- **Material Properties**
  - Common structural steels (ASTM A36, A992, A500)
  - Extensible material database

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
│   │   │   ├── beams.py          # Beam bending calculations
│   │   │   └── columns.py        # Column compression calculations
│   │   ├── standards/            # Material & section databases
│   │   │   ├── data/
│   │   │   │   └── aisc_shapes.json  # AISC shapes database
│   │   │   ├── materials/
│   │   │   │   └── structural.py     # Structural steel properties
│   │   │   ├── sections.py           # Section property loader
│   │   │   ├── query.py              # Database query utilities
│   │   │   └── QUERY_EXAMPLES.md     # Query function examples
│   │   └── units.py              # Pint unit registry
│   └── projects/                 # Design project examples
│       └── mezzanine_design/
│           └── design_mezzanine.py   # Example: Mezzanine structural design
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
from mech_core.standards.sections import get_section
from mech_core.standards.materials.structural import get_material
from mech_core.standards.query import get_shapes_by_type
from mech_core.analysis.columns import calculate_compressive_strength
from mech_core.analysis.beams import calculate_strong_axis_bending

# Define loads
live_load = (500 * ureg.kg / ureg.meter**2) * 9.81 * ureg.meter/ureg.second**2
area = 4.0 * ureg.meter * 4.0 * ureg.meter
factored_load = live_load * area * 1.5

# Select material
steel = get_material("ASTM A36")

# Find adequate beam - iterate through C-channels
beam_candidates = get_shapes_by_type("C", sort_by="W")
for beam_name in beam_candidates:
    section = get_section(beam_name)
    result = calculate_strong_axis_bending(section, steel, unbraced_length=4.0*ureg.meter)
    if result['Mu_capacity'] >= required_moment:
        print(f"Selected beam: {beam_name}")
        break

# Find adequate column - iterate through W-shapes
col_candidates = get_shapes_by_type("W", sort_by="W")
for col_name in col_candidates:
    section = get_section(col_name)
    result = calculate_compressive_strength(section, steel, 3.0*ureg.meter, k_factor=1.0)
    if result['Pu_capacity'] >= required_load:
        print(f"Selected column: {col_name}")
        break
```

Run the example:
```bash
cd engineering_tools
python projects/mezzanine_design/design_mezzanine.py
```

## Core Modules

### `mech_core.analysis.columns`
Column design per AISC 360-16 Chapter E (Compression Members)
- Slenderness ratio calculation
- Elastic vs inelastic buckling
- LRFD capacity (φPn)

### `mech_core.analysis.beams`
Beam design per AISC 360-16 Chapter F (Flexural Members)
- Yielding limit state
- Lateral-torsional buckling (LTB)
- LRFD moment capacity (φMn)

### `mech_core.standards.query`
Database query utilities for AISC shapes:
- `get_shapes_by_type()` - Get all shapes of a type
- `get_shapes_in_range()` - Filter by property ranges
- `get_lightest_shape()` - Find most economical section
- See [QUERY_EXAMPLES.md](engineering_tools/mech_core/standards/QUERY_EXAMPLES.md) for details

## Standards & References

- **AISC 360-16**: Specification for Structural Steel Buildings
- **AISC Database v16.0**: Steel section properties (metric)
- **LRFD Method**: Load and Resistance Factor Design

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

## Future Development

- [ ] Shear design for beams
- [ ] Connection design
- [ ] Seismic design provisions
- [ ] Wind load calculations
- [ ] Web interface for calculations
- [ ] PDF report generation

## Author

Built with structural engineering best practices and AISC standards compliance.