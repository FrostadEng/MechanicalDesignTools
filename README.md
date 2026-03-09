# Mechanical Design Tools

A comprehensive Python-based engineering platform with three main components:
1. **mech_core**: Structural steel design calculations following AISC/CSA standards with full unit handling
2. **simulation/Structural**: Interactive 3D structural frame modeling and FEA GUI
3. **simulation/DES**: Discrete-event simulation framework for manufacturing operations

## Features

### mech_core: Structural Design & Analysis

- **Structural Analysis**
  - Column design (CSA S16-19 compression with boundary condition mapping)
  - Beam design (strong and weak axis bending, lateral-torsional buckling)
  - Base plate design (bearing pressure, anchor bolt layout per CSA S16)
  - FEA Integration (PyNite wrapper for 3D frame analysis)
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
  - Structural steel properties (ASTM A36, A992, CSA G40.21 350W/350A)
  - Concrete materials (configurable fc')
  - Physics calculations (specific melting energy for thermal cutting)
  - Stock thickness availability system

- **Standards — Unified**
  - CSA S16-19 member design (compression, flexure, torsion)
  - CSA S16-19 connection design (bolts, bearing, block shear)
  - All code validators live under `mech_core.standards.structural`

- **Professional Reporting**
  - Markdown report generation for calculation packages
  - Symbolic mathematical derivations (step-by-step LaTeX equations)
  - Image embedding (diagrams, charts)

- **Unit-Aware Calculations**
  - Full integration with Pint for dimensional analysis
  - Automatic unit conversions throughout

### simulation/Structural: Interactive 3D Frame Modeler

- **3D Modeling Environment**
  - Node placement by clicking in a PyVista 3D viewport
  - Member creation by selecting node pairs
  - Support assignment (fixed, pinned, roller, custom DOFs)
  - Node and member distributed loads with load case management
  - Snap-to-grid with configurable resolution

- **Live Visualization**
  - Dark-themed PyVista viewport embedded in PySide6
  - Nodes (spheres), members (tubes), support glyphs, load arrows
  - Toggle labels, deformed shape overlay with adjustable scale
  - Internal force diagram surfaces (Vy, Vz, Mz, My, Axial, Torsion)
  - Screenshot export

- **FEA Integration**
  - Solve button → builds and runs FrameAnalysis from the live model
  - Post-solve results panel: shear/moment envelope per member
  - Diagram export (PNG) via the property panel

- **Model Management**
  - Model tree panel (nodes, members, supports, loads)
  - Context-sensitive property panel (forms per entity type)
  - Snapshot-based undo/redo (50-level history)
  - Section picker across all AISC shape types (W, C, HSS, L, …)
  - Material picker (ASTM A36, A992, CSA G40.21 350W/350A)

### simulation/DES: Manufacturing Process Simulation

- **Discrete-Event Simulation Framework**
  - Physics-based manufacturing operations modeling
  - Event-driven architecture for complex machine interactions
  - Hierarchical event logging for process analysis
  - Resource utilization tracking and optimization

- **Machine Modeling**
  - Complete PCR41 laser/plasma cutting platform simulation
  - Configurable robot arms (Fanuc M-710iC/50, KUKA models)
  - Material handling systems (cross-transfer units)
  - Linear indexing systems with physics-based motion profiles

- **Physics-Aware Processing**
  - Cutting speed calculations from mech_core material properties
  - Dynamic robot payload derating based on tool mass
  - Trapezoidal velocity profiles for realistic motion
  - Energy density-based thermal cutting simulation

- **NC Code Integration**
  - DSTV (.nc1) parser for European CNC standard
  - Feature extraction and intelligent grouping
  - Optimized processing sequence generation

- **Visualization & Analysis**
  - Gantt chart generation for resource utilization
  - Throughput metrics (seconds per beam, utilization %)
  - Steady-state filtering for accurate performance analysis

## Project Structure

```
MechanicalDesignTools/
├── engineering_tools/
│   ├── mech_core/                     # Structural design & analysis
│   │   ├── analysis/                  # Pure physics solvers
│   │   │   ├── fea.py                # FEA wrapper (PyNite integration)
│   │   │   ├── heat_transfer/        # Thermal cutting physics
│   │   │   └── kinematics/           # Motion profile calculations
│   │   ├── components/               # Physical objects (geometry only)
│   │   │   ├── members/
│   │   │   │   └── aisc.py           # AISC steel sections (database & queries)
│   │   │   └── connections/
│   │   │       ├── axial/
│   │   │       │   └── base_plate.py # Base plate component
│   │   │       └── shear/
│   │   │           └── fin_plate.py  # Fin plate shear connection
│   │   └── standards/                # Standards, materials & reference data
│   │       ├── units.py              # Pint unit registry
│   │       ├── materials/
│   │       │   ├── data/
│   │       │   │   ├── aisc_shapes.json           # AISC shapes database
│   │       │   │   └── standard_thicknesses.json  # Stock plate/sheet sizes
│   │       │   ├── steel.py          # Structural steel properties
│   │       │   ├── concrete.py       # Concrete materials
│   │       │   ├── inventory.py      # Stock thickness manager
│   │       │   └── __init__.py       # Unified materials API
│   │       ├── structural/           # Code-specific validators (unified)
│   │       │   └── csa_s16/
│   │       │       ├── members.py    # Beam & column design (CSA S16-19)
│   │       │       └── connections.py # Connection validation
│   │       ├── reporting/
│   │       │   └── generator.py      # Markdown report generator with LaTeX
│   │       └── fasteners/            # Fastener standards
│   │
│   ├── simulation/                    # Simulation environments
│   │   ├── Structural/               # Interactive 3D frame modeler (GUI)
│   │   │   ├── __main__.py           # Entry point: python -m simulation.Structural
│   │   │   ├── main_window.py        # MainWindow — layout & signal wiring
│   │   │   ├── document.py           # StructuralDocument + DocumentController
│   │   │   ├── undo_stack.py         # Snapshot-based undo/redo
│   │   │   ├── results.py            # Post-solve ResultsCache
│   │   │   ├── viewport_3d.py        # PyVista 3D viewport + picking
│   │   │   ├── toolbar.py            # Mode toolbar (Node/Member/Support/Load/Solve)
│   │   │   ├── model_tree.py         # Entity tree panel
│   │   │   └── property_panel.py     # Context-sensitive property editor
│   │   └── DES/                      # Discrete-event simulation framework
│   │       └── core/
│   │           ├── machines/         # Concrete machine implementations
│   │           │   ├── PCR41/        # Plasma/Fiber laser cutting platform
│   │           │   └── subsystems/   # Reusable mechanical components
│   │           ├── entities/         # Work objects (beams, parts)
│   │           ├── logging/          # Event tracking for Gantt charts
│   │           └── visualization/    # Charts and reports
│   │
│   ├── projects/                     # Design project examples
│   │   ├── mezzanine_design/
│   │   │   ├── design_mezzanine.py   # Full structural design with FEA
│   │   │   └── Mezzanine_Calc_Package.md
│   │   └── portal_design/
│   │       └── design_portal.py      # Portal frame design
│   │
│   ├── tests/                        # Verification tests
│   └── requirements.txt
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

### Launch the Interactive Structural Modeler

```bash
cd engineering_tools
python -m simulation.Structural
```

The GUI opens with a dark-themed 3D viewport. Use the toolbar to:
- **Add Node** [N] — click in the viewport to place nodes (snapped to grid)
- **Add Member** [M] — click two existing nodes to connect them
- **Add Support** [S] — click a node, then choose fixed/pinned/roller in the property panel
- **Add Load** [L] — click a node or member to open the load form
- **Solve** [F5] — runs the FEA, overlays deformed shape and diagram options

### Example: Structural Design with FEA (script)

```python
from mech_core.standards.units import ureg
from mech_core.components.members.aisc import get_section, get_shapes_by_type
from mech_core.standards.materials import get_material, get_concrete
from mech_core.analysis.fea import FrameAnalysis
from mech_core.standards.structural.csa_s16.members import (
    check_compressive_resistance, check_flexural_resistance
)
from mech_core.components.connections.axial.base_plate import BasePlateDesign
from mech_core.standards.reporting.generator import ReportGenerator

# Initialize report
report = ReportGenerator("Mezzanine Structural Design", "Engineering Co.")
report.add_header()

# Define loads
live_load = (500 * ureg.kg / ureg.meter**2) * 9.81 * ureg.meter/ureg.second**2
area = 4.0 * ureg.meter * 4.0 * ureg.meter
factored_load = live_load * area * 1.5
w_beam = (factored_load / 2) / (4 * ureg.m)

# Select materials
steel    = get_material("ASTM A36")
concrete = get_concrete(25)  # 25 MPa

# Find adequate beam with FEA verification
for beam_name in get_shapes_by_type("C", sort_by="W"):
    section = get_section(beam_name)

    frame = FrameAnalysis()
    frame.add_node("N1", 0, 0, 0)
    frame.add_node("N2", 4*ureg.m, 0, 0)
    frame.add_beam("B1", "N1", "N2", section, steel)
    frame.add_support("N1", "pinned")
    frame.add_support("N2", "pinned")
    frame.add_member_dist_load("B1", "Fy", -w_beam, -w_beam)
    frame.solve()

    forces = frame.get_beam_forces("B1")
    M_fea  = max(abs(forces['max_moment_z'].magnitude),
                 abs(forces['min_moment_z'].magnitude)) * ureg.kN * ureg.meter

    result = check_flexural_resistance(section, steel, unbraced_length=4.0*ureg.meter)
    if result['Mr'] >= M_fea:
        frame.generate_diagrams("B1", "beam_diagrams.png")
        report.add_section("Beam Selection (FEA Verified)")
        report.add_image("Shear and Moment Diagrams", "beam_diagrams.png")
        if 'calc_trace' in result:
            report.add_symbolic_derivation(f"Design Check: {beam_name}", result['calc_trace'])
        report.add_calculation_result(f"Beam: {beam_name}", result, "PASS")
        break

report.save("Structural_Calc_Package.md")
```

```bash
cd engineering_tools
python projects/mezzanine_design/design_mezzanine.py
```

### Example: Manufacturing Process Simulation

```python
import simpy
from mech_core.standards.units import ureg
from simulation.DES.core.machines.PCR41.controller import PCR41Controller
from simulation.DES.core.logging.logger import EventLogger
from simulation.DES.core.visualization.gantt import GanttChart

env    = simpy.Environment()
logger = EventLogger()

# ... configure hardware, parse NC code, run simulation ...

env.run()

chart = GanttChart(logger)
chart.plot(resources=["Robot", "CrossTransfer"], output_file="gantt.png")
metrics = chart.calculate_metrics(resources=["Robot"], steady_state_start_cycle=2)
print(f"Robot Utilization: {metrics['Robot']['utilization_pct']:.1f}%")
```

## Core Modules

### `mech_core.analysis.fea`
PyNite FEA wrapper for 3D frame analysis:
- Node and member definition with unit-aware inputs
- Support conditions (fixed, pinned, roller)
- Point and distributed load application
- Force extraction (shear, moment, axial)
- Diagram generation (shear/moment plots with matplotlib)

### `mech_core.standards.structural.csa_s16.members`
Member design per CSA S16-19:
- `check_compressive_resistance()` — Column design, slenderness, LRFD capacity
- `check_flexural_resistance()` — Strong/weak axis bending, LTB, LRFD moment capacity
- `check_torsional_resistance()` — Torsional resistance
- Symbolic derivation traces (`calc_trace` with step-by-step LaTeX)

### `mech_core.standards.structural.csa_s16.connections`
Connection design validators per CSA S16-19:
- `check_bolt_shear()`, `check_bearing()`, `check_block_shear()`
- All functions return `calc_trace` for documentation

### `mech_core.standards.materials`
Material property management:
- `get_material()` — Structural steel (ASTM A36, A992, CSA G40.21 350W/350A)
- `get_concrete()` — Concrete with configurable fc'
- `stock` — Standard plate/sheet thickness manager

### `mech_core.components.members.aisc`
AISC steel section database:
- `get_section()`, `get_shapes_by_type()`, `get_shapes_in_range()`, `get_lightest_shape()`
- `SectionProperties` — automatic unit scaling per AISC Database v16.0

### `mech_core.components.connections`
- `axial.base_plate` — Bearing pressure, plate thickness, anchor bolt layout
- `shear.fin_plate` — Bolt shear, bearing, block shear with combined reporting

### `mech_core.standards.reporting`
Professional calculation package generation:
- `ReportGenerator` — Markdown builder with symbolic LaTeX derivations and image embedding

### `simulation.Structural` (GUI)
Interactive 3D structural frame modeler:
- `DocumentController` — model state, undo stack, FEA solve orchestration
- `Viewport3D` — PyVista QtInteractor with click/drag detection and screen-space picking
- `ModelTreePanel` — live entity browser with context-menu delete
- `PropertyPanel` — context-sensitive forms (node coords, section/material picker, load inputs, results table)

## Integration Between mech_core and simulation

| Simulation Need | mech_core Provider | Usage |
|---|---|---|
| **Section Geometry** | `mech_core.components.members.aisc` | Web/flange thickness for cutting |
| **Material Properties** | `mech_core.standards.materials.steel` | Specific melting energy, density |
| **Cutting Speed** | `mech_core.analysis.heat_transfer` | Energy density → tool feed rate |
| **Motion Planning** | `mech_core.analysis.kinematics` | Trapezoidal velocity profiles |
| **Unit Handling** | `mech_core.standards.units` | Dimensional analysis throughout |
| **FEA Solve** | `mech_core.analysis.fea` | Frame analysis from GUI model |

## Standards & References

- **AISC 360-16**: Specification for Structural Steel Buildings
- **CSA S16-19**: Design of Steel Structures (Canadian Standard)
- **CSA A23.3**: Design of Concrete Structures
- **AISC Database v16.0**: Steel section properties (metric)
- **LRFD / LSD Method**: Load and Resistance Factor Design

## Requirements

- Python 3.8+
- numpy >= 1.24.0
- scipy >= 1.10.0
- pandas >= 2.0.0
- matplotlib >= 3.7.0
- pint >= 0.21.0
- PyNiteFEA >= 0.3.0
- simpy >= 4.1.1
- PySide6 >= 6.6.0 *(GUI)*
- pyvista >= 0.43.0 *(GUI)*
- pyvistaqt >= 0.11.0 *(GUI)*

## Recent Additions

### mech_core
- ✅ **Standards unified** — `codes/structural` merged into `standards/structural`
- ✅ **FEA Integration** (PyNite wrapper with AISC section mapping)
- ✅ **Symbolic derivation traces** (step-by-step LaTeX equations in reports)
- ✅ **Diagram generation** (shear/moment plots from FEA)
- ✅ Base plate design with anchor bolt layout
- ✅ Fin plate shear connection design
- ✅ Modular materials architecture (steel/concrete/inventory)
- ✅ Heat transfer analysis (specific melting energy)
- ✅ Kinematics module (trapezoidal velocity profiles)

### simulation/Structural (GUI)
- ✅ **Interactive 3D frame modeler** (PySide6 + PyVista)
- ✅ **Node/member/support/load creation** via toolbar modes + viewport click
- ✅ **FEA solve integration** with deformed shape and diagram overlays
- ✅ **Snapshot undo/redo** (50-level history)
- ✅ **AISC section picker** with shape-type filter
- ✅ **Post-solve results panel** with diagram export

### simulation/DES
- ✅ Discrete-event simulation framework (SimPy-based)
- ✅ PCR41 machine model (complete laser/plasma cutting platform)
- ✅ Physics-based robot simulation (dynamic payload derating)
- ✅ Fiber laser & plasma torch tools (energy density cutting)
- ✅ DSTV NC code parser (European CNC standard)
- ✅ Event logging system (hierarchical event tracking)
- ✅ Gantt chart visualization (resource utilization)

## Future Development

### mech_core
- [ ] Shear design for beams
- [ ] Seismic design provisions (CSA S16 seismic annex)
- [ ] Wind load calculations (NBCC 2020)
- [ ] PDF report generation from markdown
- [ ] Moment connection design
- [ ] Composite beam design

### simulation/Structural
- [ ] Load combination definitions (NBCC / ASCE 7)
- [ ] Member utilization ratios displayed on viewport
- [ ] Save / load model to JSON
- [ ] CSA S16 code-check results overlaid on members

### simulation/DES
- [ ] PCR42 machine model (secondary cutting platform)
- [ ] Additional robot models (ABB, Universal Robots)
- [ ] Waterjet cutting tool simulation
- [ ] Multi-beam batch processing optimization
- [ ] Real-time simulation dashboard

## Author

Built with structural engineering best practices, AISC/CSA standards compliance, and physics-based manufacturing simulation principles.
