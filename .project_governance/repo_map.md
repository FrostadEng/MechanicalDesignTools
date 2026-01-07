# Project Directory Structure

**Generated:** 2025-12-19
**Project:** MechanicalDesignTools
**Purpose:** Machine-readable directory and file reference

---

## Directory Tree

```
MechanicalDesignTools/
├── .claude/                               # Claude Code configuration
│   ├── settings.local.json
│   └── skills/
│       ├── catographer/
│       │   └── SKILL.md
│       └── governance/
│           └── SKILL.md
├── .project_governance/                   # Agent collaboration structure
│   ├── README.md                         # Governance documentation
│   ├── knowledge_graph/                  # Shared architectural knowledge
│   │   ├── architecture_decisions.md    # ADR records
│   │   ├── available_tools.md           # Tool documentation
│   │   └── style_guide.md               # Coding standards
│   ├── reports/                          # Implementation reports (Claude writes)
│   │   ├── implementation_report_2025-12-17.md
│   │   └── report_2025-12-19_PCR41_Simulation.md
│   ├── repo_map.md                       # This file - repository map
│   └── specs/                            # Specifications (Antigravity writes)
│       ├── active_spec.md
│       └── archive/
├── dev_tools/                             # Development utilities
│   ├── docker-compose.yaml
│   ├── ingest_aisc.py
│   └── postgres_data/                    # PostgreSQL database files
├── engineering_tools/                     # Main engineering package
│   ├── .gitignore
│   ├── requirements.txt
│   ├── mech_core/                        # Core engineering calculations
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── analysis/                     # Analysis modules
│   │   │   ├── __init__.py
│   │   │   ├── fea.py                   # Finite element analysis
│   │   │   ├── heat_transfer/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── conduction.py
│   │   │   │   └── phase_change.py
│   │   │   └── kinematics/
│   │   │       ├── __init__.py
│   │   │       ├── kinematics.py
│   │   │       └── README.md
│   │   ├── codes/                        # Industry code implementations
│   │   │   ├── __init__.py
│   │   │   └── structural/
│   │   │       ├── __init__.py
│   │   │       └── csa_s16/             # Canadian steel design code
│   │   │           ├── __init__.py
│   │   │           ├── connections.py
│   │   │           └── members.py
│   │   ├── components/                   # Structural components
│   │   │   ├── __init__.py
│   │   │   ├── fastener.py
│   │   │   ├── connections/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── axial/               # Axial connections
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base_plate.py
│   │   │   │   │   ├── gusset.py
│   │   │   │   │   └── splice.py
│   │   │   │   ├── common/              # Common connection utilities
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── bolt_checks.py
│   │   │   │   │   ├── failure_modes.py
│   │   │   │   │   └── weld_checks.py
│   │   │   │   ├── moment/              # Moment connections
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── end_plate_stiff.py
│   │   │   │   │   └── flange_plate.py
│   │   │   │   └── shear/               # Shear connections
│   │   │   │       ├── __init__.py
│   │   │   │       ├── double_angle.py
│   │   │   │       ├── end_plate.py
│   │   │   │       └── fin_plate.py
│   │   │   └── members/                  # Structural members
│   │   │       ├── __init__.py
│   │   │       ├── aisc.py              # AISC sections
│   │   │       └── AISC_MEMBERS_EXAMPLES.md
│   │   ├── standards/                    # Engineering standards
│   │   │   ├── __init__.py
│   │   │   ├── units.py
│   │   │   ├── fasteners/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── geometry.py
│   │   │   │   └── materials.py
│   │   │   ├── materials/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── concrete.py
│   │   │   │   ├── inventory.py
│   │   │   │   ├── steel.py
│   │   │   │   └── data/
│   │   │   │       ├── aisc_shapes.json
│   │   │   │       └── standard_thicknesses.json
│   │   │   └── reporting/
│   │   │       └── generator.py
│   │   └── tests/                        # Core module tests
│   ├── projects/                          # Project implementations
│   │   ├── mezzanine_design/
│   │   │   ├── __init__.py
│   │   │   ├── design_mezzanine.py
│   │   │   ├── beam_diagrams.png
│   │   │   └── Mezzanine_Calc_Package.md
│   │   └── PCR41_test/
│   │       ├── __init__.py
│   │       ├── simulation.py
│   │       ├── test_feeder_logic.py
│   │       └── sample_beam.nc1
│   ├── simulation/                        # Discrete event simulation
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── entities/
│   │   │   │   └── beam.py
│   │   │   ├── logging/
│   │   │   │   ├── __init__.py
│   │   │   │   └── logger.py
│   │   │   ├── machines/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── PCR41/               # PCR41 machine simulation
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── controller.py
│   │   │   │   │   ├── indexer.py
│   │   │   │   │   └── pcr41.py
│   │   │   │   ├── PCR42/               # PCR42 machine (placeholder)
│   │   │   │   └── subsystems/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── conveyors/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── conveyor.py
│   │   │   │       │   ├── cross_transfer.py
│   │   │   │       │   └── push_rod_feeder.py
│   │   │   │       ├── eoa_tools/       # End-of-arm tools
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── base.py
│   │   │   │       │   ├── fiber_laser.py
│   │   │   │       │   ├── plasma.py
│   │   │   │       │   └── configs/
│   │   │   │       │       ├── hypertherm_xpr300.json
│   │   │   │       │       └── ipg_yyl_4kw.json
│   │   │   │       ├── planning/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   └── parsers/
│   │   │   │       │       ├── __init__.py
│   │   │   │       │       └── dstv.py  # DSTV file parser
│   │   │   │       ├── robots/
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── robot_arm.py
│   │   │   │       │   └── configs/
│   │   │   │       │       ├── fanuc.json
│   │   │   │       │       └── kuka.json
│   │   │   │       └── tooling/
│   │   │   │           ├── __init__.py
│   │   │   │           └── clamp.py
│   │   │   └── visualization/
│   │   │       ├── __init__.py
│   │   │       └── gannt.py
│   │   └── tests/
│   │       └── __init__.py
│   └── tests/                             # Top-level tests
│       ├── test_fea_wrapper.py
│       ├── verify_aisc_benchmark.py
│       └── verify_example_f1_2a.py
├── .gitignore
├── LICENSE
└── README.md
```

---

## Directory Descriptions

### Root Level
- `.claude/`: Claude Code configuration and skills
- `.claude/skills/catographer/`: Cartography skill for maintaining repository map
- `.claude/skills/governance/`: Governance protocols for reading specs and filing reports
- `.project_governance/`: Agent collaboration structure
- `.project_governance/knowledge_graph/`: Shared architectural knowledge
- `.project_governance/reports/`: Implementation reports (Claude writes)
- `.project_governance/specs/`: Specifications (Antigravity writes)
- `.project_governance/specs/archive/`: Archived specifications
- `dev_tools/`: Development utilities
- `dev_tools/postgres_data/`: PostgreSQL database files
- `engineering_tools/`: Main engineering package

### Engineering Tools - Core
- `engineering_tools/mech_core/`: Core engineering calculations
- `engineering_tools/mech_core/analysis/`: Analysis modules
- `engineering_tools/mech_core/analysis/heat_transfer/`: Heat transfer analysis (conduction, phase change)
- `engineering_tools/mech_core/analysis/kinematics/`: Kinematic analysis
- `engineering_tools/mech_core/codes/`: Industry code implementations
- `engineering_tools/mech_core/codes/structural/`: Structural design codes
- `engineering_tools/mech_core/codes/structural/csa_s16/`: Canadian steel design code
- `engineering_tools/mech_core/components/`: Structural components
- `engineering_tools/mech_core/components/connections/`: Connection design modules
- `engineering_tools/mech_core/components/connections/axial/`: Axial connections
- `engineering_tools/mech_core/components/connections/common/`: Common connection utilities
- `engineering_tools/mech_core/components/connections/moment/`: Moment connections
- `engineering_tools/mech_core/components/connections/shear/`: Shear connections
- `engineering_tools/mech_core/components/members/`: Structural members
- `engineering_tools/mech_core/standards/`: Engineering standards
- `engineering_tools/mech_core/standards/fasteners/`: Fastener specifications
- `engineering_tools/mech_core/standards/materials/`: Material properties
- `engineering_tools/mech_core/standards/materials/data/`: Material database files
- `engineering_tools/mech_core/standards/reporting/`: Report generation
- `engineering_tools/mech_core/tests/`: Core module tests

### Engineering Tools - Projects
- `engineering_tools/projects/`: Project implementations
- `engineering_tools/projects/mezzanine_design/`: Mezzanine design calculations
- `engineering_tools/projects/PCR41_test/`: PCR41 machine testing

### Engineering Tools - Simulation
- `engineering_tools/simulation/`: Discrete event simulation
- `engineering_tools/simulation/core/`: Core simulation components
- `engineering_tools/simulation/core/entities/`: Simulation entities (beams, etc.)
- `engineering_tools/simulation/core/logging/`: Simulation logger
- `engineering_tools/simulation/core/machines/`: Machine models
- `engineering_tools/simulation/core/machines/PCR41/`: PCR41 machine simulation
- `engineering_tools/simulation/core/machines/PCR42/`: PCR42 machine (placeholder)
- `engineering_tools/simulation/core/machines/subsystems/`: Reusable subsystems
- `engineering_tools/simulation/core/machines/subsystems/conveyors/`: Conveyor subsystems
- `engineering_tools/simulation/core/machines/subsystems/eoa_tools/`: End-of-arm tools
- `engineering_tools/simulation/core/machines/subsystems/eoa_tools/configs/`: EOA tool configurations
- `engineering_tools/simulation/core/machines/subsystems/planning/`: Planning subsystems
- `engineering_tools/simulation/core/machines/subsystems/planning/parsers/`: File parsers (DSTV, etc.)
- `engineering_tools/simulation/core/machines/subsystems/robots/`: Robot arm subsystems
- `engineering_tools/simulation/core/machines/subsystems/robots/configs/`: Robot configurations
- `engineering_tools/simulation/core/machines/subsystems/tooling/`: Tooling subsystems
- `engineering_tools/simulation/core/visualization/`: Result visualization
- `engineering_tools/simulation/tests/`: Simulation tests

### Tests
- `engineering_tools/tests/`: Top-level tests

---

## Architecture Overview

### Three-Layer Architecture

1. **Core Layer** (`mech_core/`)
   - Fundamental engineering calculations
   - Standards and material databases
   - Analysis modules (FEA, thermal, kinematics)
   - Component design (connections, members, fasteners)
   - Industry code implementations (CSA S16)

2. **Projects Layer** (`projects/`)
   - Project-specific implementations
   - Design calculations for specific structures
   - Example: Mezzanine design, PCR41 testing

3. **Simulation Layer** (`simulation/`)
   - Discrete event simulation engine
   - Machine models (PCR41, PCR42)
   - Subsystems (conveyors, robots, tools)
   - Visualization and logging

### Key Module Groups

#### Analysis Modules
- `mech_core/analysis/fea.py` - FEA integration
- `mech_core/analysis/heat_transfer/` - Thermal analysis
- `mech_core/analysis/kinematics/` - Motion analysis

#### Connection Design
- `mech_core/components/connections/axial/` - Axial connections
- `mech_core/components/connections/moment/` - Moment connections
- `mech_core/components/connections/shear/` - Shear connections
- `mech_core/components/connections/common/` - Common utilities

#### Standards & Materials
- `mech_core/standards/materials/` - Material properties
- `mech_core/standards/fasteners/` - Fastener specifications
- `mech_core/codes/structural/` - Building code implementations

#### Simulation Components
- `simulation/core/machines/` - Machine models
- `simulation/core/machines/subsystems/` - Reusable subsystems
- `simulation/core/visualization/` - Result visualization

---

## Common Import Paths

```python
# Core analysis
from engineering_tools.mech_core.analysis.fea import FEAWrapper
from engineering_tools.mech_core.analysis.heat_transfer.conduction import HeatConduction
from engineering_tools.mech_core.analysis.kinematics.kinematics import KinematicSolver

# Materials and standards
from engineering_tools.mech_core.standards.materials.steel import SteelMaterial
from engineering_tools.mech_core.standards.materials.inventory import MaterialInventory
from engineering_tools.mech_core.standards.units import convert_units

# Connections
from engineering_tools.mech_core.components.connections.axial.base_plate import BasePlate
from engineering_tools.mech_core.components.connections.common.bolt_checks import check_bolt_capacity
from engineering_tools.mech_core.components.connections.shear.fin_plate import FinPlate

# Members
from engineering_tools.mech_core.components.members.aisc import AISCSection

# Code implementations
from engineering_tools.mech_core.codes.structural.csa_s16.members import check_member_capacity

# Simulation
from engineering_tools.simulation.core.machines.PCR41.pcr41 import PCR41Machine
from engineering_tools.simulation.core.machines.subsystems.conveyors.conveyor import Conveyor
from engineering_tools.simulation.core.machines.subsystems.robots.robot_arm import RobotArm
```

---

## Notes for Agents

### For Antigravity (Planning)
- Write specifications to: `.project_governance/specs/active_spec.md`
- Update architectural decisions: `.project_governance/knowledge_graph/architecture_decisions.md`
- Maintain style guide: `.project_governance/knowledge_graph/style_guide.md`
- Read implementation reports from: `.project_governance/reports/`

### For Claude (Implementation)
- Read specifications from: `.project_governance/specs/active_spec.md`
- Follow style guide: `.project_governance/knowledge_graph/style_guide.md`
- Follow architecture decisions: `.project_governance/knowledge_graph/architecture_decisions.md`
- Write implementation reports to: `.project_governance/reports/implementation_report_[date].md`

### Key Directories for Development
- **Core calculations**: `engineering_tools/mech_core/`
- **Project examples**: `engineering_tools/projects/`
- **Simulation work**: `engineering_tools/simulation/`
- **Tests**: `engineering_tools/tests/`, `engineering_tools/mech_core/tests/`
- **Utilities**: `dev_tools/`

---

## Last Updated

**Date:** 2025-12-19
**Generated by:** Claude (Cartographer skill)
**Purpose:** Provide machine-readable directory reference for AI agents and developers
