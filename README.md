# Mechanical Design Tools

A comprehensive Python-based engineering platform with two main components:
1. **mech_core**: Structural steel design calculations following AISC 360-16 standards with full unit handling
2. **simulation**: Discrete-event simulation framework for manufacturing operations leveraging mech_core physics

## Features

### mech_core: Structural Design & Analysis

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
  - Physics calculations (specific melting energy for thermal cutting)
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

### simulation: Manufacturing Process Simulation

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
  - Support for holes, cuts, and markings

- **Manufacturing Tools**
  - Fiber laser simulation (4kW IPG with fly-cutting)
  - Plasma torch simulation (Hypertherm XPR300)
  - Configurable end-of-arm tooling system
  - Tool-specific operation sequences (IHS, pierce, cut)

- **Visualization & Analysis**
  - Gantt chart generation for resource utilization
  - Throughput metrics (seconds per beam, utilization %)
  - Steady-state filtering for accurate performance analysis
  - Event hierarchy visualization

## Project Structure

```
MechanicalDesignTools/
├── engineering_tools/
│   ├── mech_core/                 # Structural design & analysis
│   │   ├── analysis/              # Pure physics solvers
│   │   │   ├── fea.py            # FEA wrapper (PyNite integration)
│   │   │   ├── heat_transfer/    # Thermal cutting physics
│   │   │   └── kinematics/       # Motion profile calculations
│   │   ├── codes/                 # Code-specific validators
│   │   │   └── structural/
│   │   │       └── csa_s16/
│   │   │           ├── members.py      # Beam & column design (CSA S16-19)
│   │   │           └── connections.py  # Connection validation
│   │   ├── components/           # Physical objects (geometry only)
│   │   │   ├── fastener.py       # Fastener objects
│   │   │   ├── members/
│   │   │   │   └── aisc.py       # AISC steel sections (database & queries)
│   │   │   └── connections/
│   │   │       ├── axial/
│   │   │       │   └── base_plate.py  # Base plate component
│   │   │       └── shear/
│   │   │           └── fin_plate.py   # Fin plate shear connection
│   │   └── standards/            # Standards & reference data
│   │       ├── units.py          # Pint unit registry
│   │       ├── materials/
│   │       │   ├── data/
│   │       │   │   ├── aisc_shapes.json         # AISC shapes database
│   │       │   │   └── standard_thicknesses.json # Stock plate/sheet sizes
│   │       │   ├── steel.py          # Structural steel properties
│   │       │   ├── concrete.py       # Concrete materials
│   │       │   ├── inventory.py      # Stock thickness manager
│   │       │   └── __init__.py       # Unified materials API
│   │       ├── reporting/
│   │       │   └── generator.py      # Markdown report generator with LaTeX
│   │       └── fasteners/        # Fastener standards
│   │
│   ├── simulation/               # Manufacturing simulation framework
│   │   ├── core/                 # Core infrastructure & physics
│   │   │   ├── machines/         # Concrete machine implementations
│   │   │   │   ├── PCR41/        # Plasma/Fiber laser cutting platform
│   │   │   │   │   ├── controller.py  # Main orchestration logic
│   │   │   │   │   └── indexer.py     # Feature grouping & planning
│   │   │   │   └── subsystems/   # Reusable mechanical components
│   │   │   │       ├── robots/        # Robot arms (Fanuc, KUKA)
│   │   │   │       ├── conveyors/     # Motion systems (indexers, transfer)
│   │   │   │       ├── eoa_tools/     # End-of-arm tools (laser, plasma)
│   │   │   │       ├── tooling/       # Workholding (clamps, fixtures)
│   │   │   │       └── planning/      # NC code parsing (DSTV)
│   │   │   ├── entities/         # Work objects (beams, parts)
│   │   │   ├── logging/          # Event tracking for Gantt charts
│   │   │   └── visualization/    # Charts and reports
│   │   └── tests/              # tests for the simulation module functionality
│   │       
│   │
│   └── projects/                 # Design project examples
│       ├── mezzanine_design/
│       │   ├── design_mezzanine.py          # Full structural design with FEA
│       │   ├── Mezzanine_Calc_Package.md    # Generated calculation report
│       │   └── beam_diagrams.png            # Auto-generated FEA diagrams
│       └── test_fea_wrapper.py              # FEA integration tests
│       └── PCR41_test/       # Reference implementation & test cases
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
from mech_core.standards.units import ureg
from mech_core.components.members.aisc import get_section, get_shapes_by_type
from mech_core.standards.materials import get_material, get_concrete
from mech_core.analysis.fea import FrameAnalysis
from mech_core.codes.structural.csa_s16.members import check_compressive_resistance, check_flexural_resistance
from mech_core.components.connections.axial.base_plate import BasePlateDesign
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
    result = check_flexural_resistance(section, steel, unbraced_length=4.0*ureg.meter)
    if result['Mr'] >= M_fea:
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

### Example: Simulating a Manufacturing Process

```python
import simpy
from mech_core.standards.units import ureg
from simulation.core.machines.PCR41.controller import PCR41Controller
from simulation.core.machines.subsystems.robots.robot_arm import RobotArm
from simulation.core.machines.subsystems.conveyors.cross_transfer import CrossTransfer
from simulation.core.machines.subsystems.conveyors.linear_actuator import LinearActuator, ConveyorSpecs
from simulation.core.machines.subsystems.eoa_tools.fiber_laser import FiberLaser
from simulation.core.machines.PCR41.indexer import Indexer
from simulation.core.entities.beam import BeamEntity
from simulation.core.machines.subsystems.planning.parsers.dstv import DSTVParser
from simulation.core.logging.logger import EventLogger
from simulation.core.visualization.gantt import GanttChart

# Initialize simulation environment
env = simpy.Environment()
logger = EventLogger()

# Configure hardware components
cross_transfer = CrossTransfer(env, logger, num_units=3, capacity_per_unit=2000*ureg.kg)
push_rod_specs = ConveyorSpecs(
    length=18000*ureg.mm,
    max_speed=800*ureg.mm/ureg.second,
    acceleration=150*ureg.mm/ureg.second**2
)
push_rod = LinearActuator(env, logger, specs=push_rod_specs)
robot = RobotArm(env, logger, config_file="fanuc_m710ic_50.json")
tool = FiberLaser(env, logger)
indexer = Indexer()

# Load NC code and create work entity
parser = DSTVParser("path/to/part.nc1")
dstv_data = parser.parse()
beam = BeamEntity.from_dstv(dstv_data)

# Generate optimized processing plan
processing_plan = indexer.generate_plan(dstv_data.features)

# Create machine controller
controller = PCR41Controller(
    env=env,
    logger=logger,
    cross_transfer=cross_transfer,
    push_rod=push_rod,
    robot=robot,
    tool=tool,
    indexer=indexer
)

# Run simulation
env.process(controller.process_beam(beam, processing_plan))
env.run()

# Analyze results
chart = GanttChart(logger)
chart.plot(
    resources=["Robot", "CrossTransfer", "PushRod"],
    output_file="throughput_analysis.png",
    steady_state_start_cycle=2  # Skip startup transient
)

# Get metrics
metrics = chart.calculate_metrics(
    resources=["Robot"],
    steady_state_start_cycle=2
)
print(f"Robot Utilization: {metrics['Robot']['utilization_pct']:.1f}%")
print(f"Seconds per Beam: {metrics['Robot']['seconds_per_beam']:.2f}s")
```

Run the example:
```bash
cd engineering_tools
python simulation/studies/PCR41_test/test_full_sequence.py
```

## Core Modules

### mech_core Modules

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

### `mech_core.codes.structural.csa_s16.members`
Member design per CSA S16-19 (based on AISC 360-16 principles)
- `check_compressive_resistance()` - Column design (Chapter E)
  - Boundary condition mapping (`["pinned", "pinned"]`, `["fixed", "free"]`, etc.)
  - Slenderness ratio calculation (KL/r)
  - Elastic vs inelastic buckling modes
  - LRFD capacity (φPn)
- `check_flexural_resistance()` - Beam design (Chapter F)
  - Strong axis (X-X) and weak axis (Y-Y) bending
  - Yielding limit state (Mp = Fy * Z)
  - Lateral-torsional buckling (LTB) for strong axis
  - LRFD moment capacity (φMn)
- **Symbolic derivation traces** (`calc_trace` with step-by-step LaTeX)

### `mech_core.codes.structural.csa_s16.connections`
Connection design validators per CSA S16-19
- `check_bolt_shear()` - Bolt shear resistance
- `check_bearing()` - Bearing resistance on plates/webs
- `check_block_shear()` - Block shear rupture (shear + tension)
- All functions return calc_trace for documentation

### `mech_core.components.connections.axial.base_plate`
Base plate design component per CSA S16
- Bearing pressure on concrete
- Required plate thickness calculation
- Standard thickness selection from inventory
- Anchor bolt layout (4-bolt pattern)
- Edge distance and spacing checks
- Integrated markdown reporting

### `mech_core.components.connections.shear.fin_plate`
Fin plate shear connection component
- Geometric property calculation (net areas, edge distances)
- Delegates validation to CSA S16 connection validators
- Combined reporting with bolt shear, bearing, and block shear checks
- Returns detailed calc_trace for each failure mode

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

### `mech_core.components.members.aisc`
AISC steel section database and query utilities:
- `get_section()` - Retrieve section by name
- `get_shapes_by_type()` - Get all shapes of a type
- `get_shapes_in_range()` - Filter by property ranges
- `get_lightest_shape()` - Find most economical section
- `SectionProperties` - Section property class with automatic unit scaling

### simulation Modules

#### `simulation.core.machines.PCR41.controller`
Main orchestration logic for the PCR41 cutting platform:
- Coordinates material handling, indexing, and processing subsystems
- Manages beam loading/unloading sequences
- Directs robot and tool operations for each indexed position
- Implements complete production cycle workflow

#### `simulation.core.machines.PCR41.indexer`
Feature grouping and motion optimization:
- `generate_plan()` - Groups features by X-position within tolerance
- Minimizes repositioning moves by clustering operations
- Optimizes processing sequence from DSTV data
- Returns indexed positions with associated feature lists

#### `simulation.core.machines.subsystems.robots.robot_arm`
Physics-aware robot arm simulation:
- Configuration-driven from JSON (Fanuc M-710iC/50, KUKA models)
- **Dynamic payload derating** - acceleration reduces with tool mass
- Trapezoidal velocity profiles for realistic motion (from mech_core kinematics)
- Motion types: rapid moves, linear interpolation, path following
- Inversion of control pattern: robot hands itself to tools for orchestration

#### `simulation.core.machines.subsystems.eoa_tools.fiber_laser`
4kW IPG fiber laser simulation:
- **Physics-based cutting speed** calculation from mech_core materials
- Queries beam thickness and material grade from BeamEntity
- Uses specific melting energy for energy density calculations
- Fly-cutting approach with rapid moves between features
- Mass: 12.5kg (minimal robot derating)

#### `simulation.core.machines.subsystems.eoa_tools.plasma_torch`
Hypertherm XPR300 plasma torch simulation:
- Complex operation sequence: IHS (In-Height Sensing) + Pierce + Cut
- Pierce delay: 0.7s, IHS time: 1.2s, retract distance: 75mm
- **Physics-based cutting** using same energy density approach as laser
- Mass: 32kg (significant robot payload derating)
- Realistic manufacturing cycle times

#### `simulation.core.machines.subsystems.conveyors.linear_actuator`
Push rod feeder with physics-based motion:
- Trapezoidal kinematics for smooth acceleration/deceleration
- Accounts for beam mass and acceleration derating
- Integrated clamping/unclamping logic
- Configurable specs: length (18m), speed (800mm/s), acceleration (150mm/s²)

#### `simulation.core.machines.subsystems.conveyors.cross_transfer`
Multi-unit hydraulic transfer system:
- 1-3 unit configuration with capacity checking (2000kg per unit)
- Operations: Lift, Lower, Traverse with realistic timing
- Load capacity validation against beam mass
- Hierarchical event logging for process visibility

#### `simulation.core.machines.subsystems.planning.parsers.dstv`
DSTV (.nc1) NC code parser:
- Parses European/German CNC standard format
- Extracts: profile code, material grade, features (holes/cuts/marks)
- Face designation mapping (v=web, o=top flange, u=bottom flange)
- Returns `DSTVData` with aggregated metrics and feature lists

#### `simulation.core.entities.beam`
Physics-aware work entity:
- `from_dstv()` - Hydrates from DSTV data
- Loads AISC section geometry from mech_core database
- Maps material grades to mech_core material properties
- `get_thickness_at_feature()` - Returns web/flange thickness for cutting physics
- Provides mass calculation for material handling validation

#### `simulation.core.logging.logger`
Hierarchical event tracking system:
- Captures simulation events with start/end times
- Supports nested event tracking (parent-child relationships)
- Cycle tracking for throughput analysis
- Query methods: by resource, cycle range, hierarchy level
- Context-manager pattern for automatic event closure

#### `simulation.core.visualization.gantt`
Manufacturing throughput analysis and visualization:
- Generates resource utilization Gantt charts (matplotlib)
- Y-axis: resources (Robot, CrossTransfer, PushRod, etc.)
- X-axis: simulation time with color-coded production cycles
- Calculates metrics: utilization %, seconds per beam, total throughput
- Steady-state filtering to exclude startup/shutdown transients

## Integration Between mech_core and simulation

The simulation framework leverages mech_core for all physics calculations:

| Simulation Need | mech_core Provider | Usage |
|---|---|---|
| **Section Geometry** | `mech_core.components.members.aisc` | Web/flange thickness for cutting |
| **Material Properties** | `mech_core.standards.materials.steel` | Specific melting energy, density |
| **Cutting Speed** | `mech_core.analysis.heat_transfer` | Energy density → tool feed rate |
| **Motion Planning** | `mech_core.analysis.kinematics` | Trapezoidal velocity profiles |
| **Unit Handling** | `mech_core.standards.units` | Dimensional analysis throughout |

**Key Design Pattern:** No simulation parameters are hard-coded. All physics derives from mech_core databases and standard materials, ensuring consistency and accuracy across structural design and manufacturing simulation.

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
- PyNiteFEA >= 0.0.90 (for mech_core FEA integration)
- simpy >= 4.0.0 (for simulation discrete-event framework)

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is provided as-is for educational and professional use.

## Recent Additions

### mech_core
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
- ✅ **Heat transfer analysis** (specific melting energy for thermal cutting)
- ✅ **Kinematics module** (trapezoidal velocity profiles)

### simulation
- ✅ **Discrete-event simulation framework** (SimPy-based)
- ✅ **PCR41 machine model** (complete laser/plasma cutting platform)
- ✅ **Physics-based robot simulation** (dynamic payload derating)
- ✅ **Fiber laser & plasma torch tools** (energy density cutting calculations)
- ✅ **DSTV NC code parser** (European CNC standard)
- ✅ **Event logging system** (hierarchical event tracking)
- ✅ **Gantt chart visualization** (resource utilization analysis)
- ✅ **Material handling subsystems** (cross-transfer, linear actuators)
- ✅ **Integration with mech_core** (geometry, materials, physics)

## Future Development

### mech_core
- [ ] Shear design for beams
- [ ] Welded and bolted connection design
- [ ] Seismic design provisions (CSA S16 seismic)
- [ ] Wind load calculations (NBCC 2020)
- [ ] Web interface for calculations
- [ ] PDF report generation from markdown
- [ ] Moment connection design
- [ ] Composite beam design

### simulation
- [ ] PCR42 machine model (secondary cutting platform)
- [ ] Additional robot models (ABB, Universal Robots)
- [ ] Waterjet cutting tool simulation
- [ ] Multi-beam batch processing optimization
- [ ] 3D visualization of machine operations
- [ ] Real-time simulation dashboard
- [ ] Integration with production scheduling systems
- [ ] Tool path optimization algorithms

## Author

Built with structural engineering best practices, AISC standards compliance, and physics-based manufacturing simulation principles.