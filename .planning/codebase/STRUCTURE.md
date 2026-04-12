# Codebase Structure
_Generated: 2026-04-12_

## Summary

MechanicalDesignTools is a Python monorepo with two independent sub-projects under one root: `engineering_tools/` (structural engineering library + FEA + DES simulation + PySide6 GUI) and `Robot_Simulations/` (GPU-accelerated robot RL training via Genesis). The tree below covers all source files, excluding `__pycache__/`, `.pyc` bytecode, and generated binary assets.

---

## Top-Level Layout

```
MechanicalDesignTools/
├── engineering_tools/          # Primary sub-project: mech library, GUI, DES
│   ├── mech_core/              # Shared physics/materials kernel (no Qt dependency)
│   ├── simulation/             # GUI app (Structural) + DES engine (DES)
│   ├── projects/               # Runnable design scripts consuming mech_core
│   ├── requirements.txt        # Python deps for engineering_tools venv
│   └── .gitignore
├── Robot_Simulations/          # Secondary sub-project: robot RL / Genesis
│   └── eden/                   # GPU training environment (own venv, own git)
├── .planning/                  # AI-assistant planning artifacts (not shipped)
│   └── codebase/               # Generated codebase intelligence docs
├── .claude/                    # Claude Code agent/command configs
├── .serena/                    # Serena MCP server workspace data
└── .dev_tools/                 # Local dev tooling (postgres_data, etc.)
```

---

## `engineering_tools/mech_core/` — Physics Kernel

Shared, Qt-free computation library. All other components import from here.

```
mech_core/
├── __init__.py
├── README.md
├── analysis/
│   ├── __init__.py
│   ├── fea.py                              # FrameAnalysis — PyNiteFEA wrapper
│   ├── statics/
│   │   ├── __init__.py
│   │   └── section_properties.py          # Custom section property derivation
│   ├── kinematics/
│   │   ├── __init__.py
│   │   ├── kinematics.py                  # Trapezoidal velocity profiles, 3D distance
│   │   └── README.md
│   ├── heat_transfer/
│   │   ├── __init__.py
│   │   ├── conduction.py                  # Steady-state and transient conduction
│   │   └── phase_change.py                # Melting/solidification models
│   ├── fluid_dynamics/
│   │   ├── __init__.py
│   │   └── gas_jets.py                    # Assist gas nozzle/jet models
│   └── manufacturing/
│       ├── __init__.py
│       └── thermal_removal.py             # Laser/plasma material removal rate
├── components/
│   ├── __init__.py
│   ├── fastener.py                        # Standard bolt creation dataclass
│   ├── members/
│   │   ├── __init__.py
│   │   ├── aisc.py                        # SectionProperties + AISC DB loader
│   │   └── AISC_MEMBERS_EXAMPLES.md
│   └── connections/
│       ├── __init__.py
│       ├── common/
│       │   ├── __init__.py
│       │   ├── bolt_checks.py             # Generic bolt capacity checks
│       │   ├── weld_checks.py             # Generic weld capacity checks
│       │   └── failure_modes.py           # Shared failure mode enumerations
│       ├── shear/
│       │   ├── __init__.py
│       │   ├── fin_plate.py               # Fin plate shear connection
│       │   ├── end_plate.py               # Shear end plate connection
│       │   └── double_angle.py            # Double angle shear connection
│       ├── moment/
│       │   ├── __init__.py
│       │   ├── end_plate_stiff.py         # Stiffened moment end plate
│       │   └── flange_plate.py            # Flange plate moment connection
│       └── axial/
│           ├── __init__.py
│           ├── base_plate.py              # Column base plate design
│           ├── gusset.py                  # Gusset plate axial connection
│           └── splice.py                  # Member splice connection
└── standards/
    ├── __init__.py
    ├── units.py                           # Singleton pint.UnitRegistry (ureg / Q_)
    ├── materials/
    │   ├── __init__.py
    │   ├── steel.py                       # StructuralMaterial + SurfacePhysics dataclasses
    │   ├── concrete.py                    # Concrete grade definitions
    │   ├── inventory.py                   # Material lookup by name
    │   └── data/
    │       ├── aisc_shapes.json           # AISC v16.0 full shape database
    │       └── standard_thicknesses.json  # Standard plate thickness stock
    ├── fasteners/
    │   ├── __init__.py
    │   ├── geometry.py                    # Bolt hole and edge distance tables
    │   └── materials.py                   # Bolt material grade properties
    ├── structural/
    │   ├── __init__.py
    │   └── csa_s16/
    │       ├── __init__.py
    │       ├── members.py                 # CSA S16 compression/flexure checks + calc_trace
    │       └── connections.py             # CSA S16 connection resistance checks
    └── reporting/
        └── generator.py                   # ReportGenerator — Markdown engineering reports
```

---

## `engineering_tools/simulation/Structural/` — 3D Structural Lab GUI

PySide6 + PyVista interactive structural frame modeler. MVC with document-controller mediator pattern.

```
simulation/Structural/
├── __init__.py
├── __main__.py             # Entry point: python -m simulation.Structural
├── main_window.py          # MainWindow — sole inter-panel signal router
├── document.py             # StructuralDocument (model) + DocumentController (mutations/solve)
├── undo_stack.py           # UndoStack — snapshot-based undo/redo (max depth 60)
├── viewport_3d.py          # Viewport3D — PyVista 3D render pane; emits placement signals
├── model_tree.py           # ModelTreePanel — Qt tree view of nodes/members/loads
├── property_panel.py       # PropertyPanel — field editor for selected element
├── toolbar.py              # ModelingToolbar — mode buttons (Node, Member, Support, Load)
├── placement_tools.py      # Precise node/member placement + grid-snapping helpers
├── results.py              # ResultsCache — holds post-solve FEA output
├── project_io.py           # save_project / load_project — JSON persistence
└── pdf_export.py           # PDF export (optional; requires wkhtmltopdf binary)
```

**Signal routing summary:**
- `Viewport3D` emits: `node_placement_requested`, `member_placement_requested`, `selection_changed`
- `MainWindow._connect()` wires all signals to `DocumentController` methods
- `DocumentController` emits: `model_changed`, `solve_complete`
- Panels subscribe to `model_changed` / `solve_complete`; they are unaware of each other

---

## `engineering_tools/simulation/DES/` — Discrete Event Simulation Engine

SimPy-based DES for CNC manufacturing machines (PCR41 structural steel cutter). Hierarchical subsystem composition pattern.

```
simulation/DES/
├── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_composite_constraint.py
│   ├── test_gas_jets.py
│   ├── test_process_physics.py
│   ├── test_safety_plc.py
│   ├── test_thermal_removal.py
│   └── test_window_indexer.py
└── core/
    ├── __init__.py
    ├── entities/
    │   └── beam.py                        # BeamEntity — workpiece flowing through simulation
    ├── logging/
    │   ├── __init__.py
    │   └── logger.py                      # EventLogger — timestamped simulation event stream
    ├── visualization/
    │   ├── __init__.py
    │   └── gannt.py                       # Gantt chart output from EventLogger data
    └── machines/
        ├── __init__.py
        ├── PCR41/
        │   ├── __init__.py
        │   ├── pcr41.py                   # PCR41 top-level assembly / integration
        │   ├── controller.py              # PCR41_Controller — SimPy orchestrator process
        │   ├── indexer.py                 # Indexer — sliding-window beam indexing logic
        │   └── config.py                  # PCR41 machine configuration constants
        └── subsystems/
            ├── __init__.py
            ├── conveyors/
            │   ├── __init__.py
            │   ├── conveyor.py            # LinearActuator — conveyor belt model
            │   ├── push_rod_feeder.py     # Push-rod infeed feeder
            │   └── cross_transfer.py      # Cross-transfer unit
            ├── robots/
            │   ├── __init__.py
            │   ├── robot_arm.py           # RobotArm — 6-axis kinematics (loads configs/fanuc.json)
            │   └── configs/
            │       ├── fanuc.json         # Fanuc robot kinematic/speed parameters
            │       └── kuka.json          # KUKA robot kinematic/speed parameters
            ├── eoa_tools/
            │   ├── __init__.py
            │   ├── base.py                # EOATool base class
            │   ├── fiber_laser.py         # FiberLaser — physics-informed cut duration
            │   ├── plasma.py              # Plasma cutter — physics-informed cut duration
            │   └── configs/
            │       ├── ipg_yyl_4kw.json   # IPG 4kW fiber laser parameters
            │       └── hypertherm_xpr300.json  # Hypertherm XPR300 plasma parameters
            ├── tooling/
            │   ├── __init__.py
            │   └── clamp.py               # Workpiece clamping subsystem
            ├── logic/
            │   ├── __init__.py
            │   └── safety_plc.py          # SafetyPLC — event-based safety interlocks
            └── planning/
                ├── __init__.py
                └── parsers/
                    ├── __init__.py
                    └── dstv.py            # DSTVData — DSTV/NC1 CNC file parser
```

---

## `engineering_tools/projects/` — Project-Specific Design Scripts

Runnable scripts that consume `mech_core` directly. Each subdirectory is a standalone design project.

```
projects/
├── mezzanine_design/
│   ├── __init__.py
│   ├── design_mezzanine.py        # Full CSA S16 mezzanine: FEA + connections + report
│   ├── Mezzanine_Calc_Package.md  # Generated engineering calculation package
│   └── beam_diagrams.png          # Generated shear/moment diagram output
├── portal_design/
│   └── design_portal.py           # Portal frame structural design
├── PCR41_test/
│   ├── __init__.py
│   ├── simulation.py              # PCR41 DES integration test script
│   ├── test_feeder_logic.py       # Feeder logic unit tests
│   └── sample_beam.nc1            # Sample DSTV NC1 file for testing
└── PCR42 EOA Tool Design/
    ├── instructions.md
    └── eoat_sweep.py              # End-of-arm tool design parameter sweep
```

---

## `Robot_Simulations/` — Robot Cell Simulation (Separate Sub-Project)

Early-stage GPU-accelerated robot RL training workspace. Has its own git history (`Robot_Simulations/.git`), Python venv, and Docker environment. Not integrated with the `engineering_tools` tree.

```
Robot_Simulations/
└── eden/
    ├── requirements.txt           # Genesis, SB3, Gymnasium, PyTorch, pytest, black, mypy
    ├── docker/
    │   ├── Dockerfile.training    # FROM pytorch:2.1.0-cuda12.1; installs Genesis + RL stack
    │   ├── Dockerfile.authoring   # Authoring workspace image
    │   ├── Dockerfile.genesis*    # GPU/CPU/AMD variant images
    │   └── docker-compose.yaml    # authoring-ws service with NVIDIA GPU passthrough + X11
    ├── cad_source/                # STEP/STP robot cell CAD files for Genesis scenes
    └── experiments/
        └── hello_genesis.py       # Genesis entry-point / smoke test
```

---

## `.planning/codebase/` — AI-Generated Codebase Intelligence

```
.planning/codebase/
├── ARCHITECTURE.md     # Component responsibilities, data flows, state management, design patterns
├── CONVENTIONS.md      # Naming, typing, docstring, error handling, import conventions
├── INTEGRATIONS.md     # External library integrations and boundary contracts
├── STACK.md            # Technology stack, runtimes, frameworks, key dependencies
└── STRUCTURE.md        # This file — full directory tree with file-level annotations
```

---

## Key File Index (Quick Reference)

| File | Role |
|------|------|
| `engineering_tools/mech_core/standards/units.py` | Singleton `ureg` / `Q_` — global unit system |
| `engineering_tools/mech_core/analysis/fea.py` | `FrameAnalysis` — PyNiteFEA wrapper |
| `engineering_tools/mech_core/components/members/aisc.py` | `SectionProperties`, AISC shape DB loader |
| `engineering_tools/mech_core/standards/structural/csa_s16/members.py` | CSA S16 member checks + `calc_trace` |
| `engineering_tools/mech_core/standards/reporting/generator.py` | `ReportGenerator` — Markdown reports |
| `engineering_tools/mech_core/standards/materials/data/aisc_shapes.json` | AISC v16.0 shape database (JSON) |
| `engineering_tools/simulation/Structural/__main__.py` | GUI entry point |
| `engineering_tools/simulation/Structural/document.py` | `StructuralDocument` + `DocumentController` |
| `engineering_tools/simulation/Structural/main_window.py` | `MainWindow` — signal router |
| `engineering_tools/simulation/Structural/viewport_3d.py` | `Viewport3D` — PyVista 3D pane |
| `engineering_tools/simulation/Structural/placement_tools.py` | Grid-snapping + precision placement tools |
| `engineering_tools/simulation/DES/core/machines/PCR41/controller.py` | `PCR41_Controller` — SimPy orchestrator |
| `engineering_tools/simulation/DES/core/machines/subsystems/robots/robot_arm.py` | `RobotArm` — 6-axis kinematics |
| `engineering_tools/simulation/DES/core/machines/subsystems/logic/safety_plc.py` | `SafetyPLC` — safety interlocks |
| `engineering_tools/simulation/DES/core/machines/subsystems/planning/parsers/dstv.py` | `DSTVData` — NC1 file parser |
| `engineering_tools/simulation/DES/core/logging/logger.py` | `EventLogger` — simulation event stream |
| `engineering_tools/projects/mezzanine_design/design_mezzanine.py` | Full mezzanine design script |
| `engineering_tools/requirements.txt` | Python dependencies for main venv |

---

## Gaps / Unknowns

- `Robot_Simulations/` has its own `Robot_Simulations/.git` — it may be a git submodule or embedded repo; its relationship to the outer repo is not formalized.
- Two PCR41 implementations exist at different maturity levels: `simulation/DES/core/machines/PCR41/` (current modular) and `projects/PCR41_test/` (older test harness). The older one references `PCR41_Assembly` which may be stale.
- `simulation/Structural/pdf_export.py` depends on optional `pdfkit`/`wkhtmltopdf`; not listed in `requirements.txt`.
- No `__init__.py` was confirmed for `projects/portal_design/` — it may not be importable as a package.
- `simulation/DES/core/visualization/gannt.py` filename has a typo (should be `gantt.py`).
