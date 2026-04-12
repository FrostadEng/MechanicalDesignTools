# Architecture
_Generated: 2026-04-12_

## Summary
MechanicalDesignTools is a Python monorepo containing three major sub-systems: a shared engineering computation library (`mech_core`), a discrete-event simulation (DES) engine for CNC machine modeling, and a GUI-based 3D structural analysis application ("Frostad Structural Lab"). All three sub-systems depend on `mech_core` as the shared physics/materials kernel; the GUI and DES layers consume it but do not depend on each other.

## High-Level Pattern

**Layered library + desktop application** with a DES simulation arm running separately.

```
┌─────────────────────────────────────────────────────────┐
│  GUI Application          DES Simulation                 │
│  simulation/Structural/   simulation/DES/                │
│  (PySide6 + PyVista)      (SimPy + subsystem model)      │
│         │                          │                     │
│         └──────────┬───────────────┘                     │
│                    ▼                                     │
│           engineering_tools/mech_core/                   │
│   (physics kernel: FEA, materials, standards, units)    │
└─────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### `mech_core` — Physics Kernel
Location: `engineering_tools/mech_core/`

The shared, Qt-free computation library consumed by all other components. Divided into three sub-namespaces:

- **`mech_core.analysis`** — Numerical analysis engines
  - `fea.py`: `FrameAnalysis` wraps PyNiteFEA for 3D frame FEA. Handles AISC-to-PyNite axis mapping and unit conversion.
  - `statics/section_properties.py`: Derives section properties from dimensions (custom shapes).
  - `kinematics/kinematics.py`: Trapezoidal velocity profiles, 3D distance — used by DES robot simulation.
  - `analysis/heat_transfer/`: Conduction and phase-change models (used by laser/plasma DES tools).
  - `analysis/fluid_dynamics/gas_jets.py`: Gas jet models (assist gas for cutting processes).
  - `analysis/manufacturing/thermal_removal.py`: Material removal rate models for laser/plasma.

- **`mech_core.components`** — Physical component models
  - `members/aisc.py`: `SectionProperties` class, AISC steel section DB loader (reads `aisc_shapes.json`).
  - `components/connections/`: Shear, moment, and axial connection checks (fin plate, end plate, double angle, base plate, gusset, splice, flange plate).
  - `components/fastener.py`: Standard bolt creation.

- **`mech_core.standards`** — Code-of-practice logic and reference data
  - `standards/materials/steel.py`: `StructuralMaterial` and `SurfacePhysics` dataclasses; ASTM/CSA grades.
  - `standards/materials/concrete.py`: Concrete grade definitions.
  - `standards/materials/inventory.py`: Material lookup by name.
  - `standards/materials/data/aisc_shapes.json`: Full AISC v16.0 shape database (JSON).
  - `standards/structural/csa_s16/members.py`: CSA S16 compressive/flexural resistance checks with symbolic step traces.
  - `standards/structural/csa_s16/connections.py`: CSA S16 connection checks.
  - `standards/fasteners/`: Bolt geometry and material tables.
  - `standards/units.py`: Singleton `pint.UnitRegistry` (`ureg`) — the global unit system for the entire repo.
  - `standards/reporting/generator.py`: `ReportGenerator` builds Markdown engineering reports.

---

### `simulation/Structural` — 3D Structural Lab GUI
Location: `engineering_tools/simulation/Structural/`

A desktop application using PySide6 + PyVista for interactive structural frame modeling and FEA.

**Architecture pattern: MVC with document-controller mediator.**

| Layer | Class | File |
|-------|-------|------|
| Model (data) | `StructuralDocument` | `document.py` |
| Controller (mutations + solve) | `DocumentController` | `document.py` |
| Undo | `UndoStack` | `undo_stack.py` |
| View — 3D viewport | `Viewport3D` | `viewport_3d.py` |
| View — model tree | `ModelTreePanel` | `model_tree.py` |
| View — properties | `PropertyPanel` | `property_panel.py` |
| View — toolbar | `ModelingToolbar` | `toolbar.py` |
| Results cache | `ResultsCache` | `results.py` |
| Persistence | `save_project` / `load_project` | `project_io.py` |
| App entry point | `main()` | `__main__.py` |
| Window wiring | `MainWindow` | `main_window.py` |

`MainWindow` acts as the sole inter-panel signal router — individual panels are unaware of each other. All cross-panel signal connections are established in `MainWindow._connect()`.

---

### `simulation/DES` — Discrete Event Simulation Engine
Location: `engineering_tools/simulation/DES/`

SimPy-based DES for modeling CNC manufacturing machines (PCR41 cutter).

**Architecture pattern: Hierarchical subsystem composition.**

```
PCR41_Controller (orchestrator)
  ├── LinearActuator (feeder/conveyor)
  ├── RobotArm (6-axis robot, loads fanuc.json)
  ├── FiberLaser (end-of-arm tool)
  ├── Indexer (sliding-window beam indexing logic)
  └── SafetyPLC (event-based safety interlocks)
```

Supporting infrastructure:
- `core/logging/logger.py`: `EventLogger` — timestamped event stream.
- `core/entities/beam.py`: `BeamEntity` — workpiece entity that flows through the simulation.
- `core/visualization/gannt.py`: Gantt chart output.
- `core/machines/subsystems/planning/parsers/dstv.py`: Parses DSTV NC files (structural steel marking format).

---

### `projects/` — Project-specific scripts
Location: `engineering_tools/projects/`

Runnable design scripts that consume `mech_core` directly:
- `mezzanine_design/design_mezzanine.py`: Full CSA S16 mezzanine structural design with FEA, connection checks, and report generation.
- `portal_design/design_portal.py`: Portal frame design.
- `PCR41_test/simulation.py`: Integration test script for PCR41 DES.
- `PCR42 EOA Tool Design/eoat_sweep.py`: End-of-arm tool design sweep.

---

### `Robot_Simulations/` — Robot placement tooling
Location: `Robot_Simulations/`

Separate workspace for robot cell simulation, including Docker-based environment (`eden`), CAD source files, and implementation notes. Has its own Python virtual environment and `requirements.txt`. Contains early-stage simulation experiments distinct from the engineering_tools tree.

---

## Data Flow

### Structural GUI solve flow
1. User places nodes/members/supports/loads via `Viewport3D` or `PropertyPanel`.
2. `Viewport3D` emits signals (`node_placement_requested`, `member_placement_requested`, etc.).
3. `MainWindow` routes signals to `DocumentController` mutation methods.
4. Each mutation: push undo snapshot → mutate `StructuralDocument` → invalidate `ResultsCache` → emit `model_changed`.
5. `Viewport3D` and `ModelTreePanel` re-render on `model_changed`.
6. User clicks "Solve": `DocumentController.run_solve()` builds `FrameAnalysis` from `StructuralDocument`, calls `fea.solve()`, wraps output in `ResultsCache`, emits `solve_complete`.
7. `Viewport3D.show_results()` renders deformed shape and force diagrams from `ResultsCache`.

### DES simulation flow
1. `DSTVData` is parsed from a DSTV NC file.
2. `PCR41_Controller.run_production(beam_dstv)` is called with a `BeamEntity`.
3. Controller orchestrates: feeder transport → robot positioning → laser/plasma cutting (physics-informed durations via `mech_core` kinematics and heat transfer).
4. `SafetyPLC` issues handshake signals between subsystems.
5. `EventLogger` records timestamped events throughout.
6. `ResultsCache` / Gantt chart reports throughput.

---

## State Management

**Structural GUI:** All mutable state lives in `StructuralDocument` (a plain Python dataclass). `DocumentController` owns the single instance. Undo/redo is snapshot-based (`UndoStack` deep-copies `to_dict()` / restores via `from_dict()`). Solved results are held in `ResultsCache`; they are invalidated (set to `None`) on any document mutation.

**DES:** State is managed per-object within SimPy process coroutines. `RobotState` (position), `SafetyPLC` (interlock flags), and `Indexer` (window position) each carry their own state. No global state store.

---

## Key Design Patterns

- **Singleton unit registry** (`mech_core/standards/units.py`): All dimensional values use `pint` quantities via a single shared `ureg`. This enforces unit consistency across the entire repo.
- **Snapshot undo** (`UndoStack`): Avoids Command pattern complexity; serialises to dict before every mutation (max depth 60).
- **Signal/slot mediator** (`MainWindow._connect()`): GUI panels are fully decoupled; `MainWindow` is the only place that knows about all panels.
- **Coordinate axis swap in solve**: GUI uses Z-up; PyNite uses Y-up. The swap (y↔z) is performed explicitly in `DocumentController.run_solve()` and in load direction mapping.
- **Subsystem composition over inheritance** in DES: `PCR41_Controller` composes hardware subsystem objects rather than subclassing them.
- **Config-file-driven robot kinematics**: `RobotArm` loads `configs/fanuc.json` at construction, decoupling kinematics parameters from code.
- **Symbolic calculation traces**: CSA S16 checks (`csa_s16/members.py`) return `steps` lists with intermediate values, enabling engineering report traceability.

---

## Entry Points

| Entry Point | How to Invoke | Purpose |
|-------------|---------------|---------|
| `engineering_tools/simulation/Structural/__main__.py` | `python -m simulation.Structural` (from `engineering_tools/`) | Launch 3D Structural Lab GUI |
| `engineering_tools/projects/mezzanine_design/design_mezzanine.py` | `python design_mezzanine.py` | Run mezzanine design script |
| `engineering_tools/projects/portal_design/design_portal.py` | `python design_portal.py` | Run portal frame design |
| `engineering_tools/projects/PCR41_test/simulation.py` | `python simulation.py` | Run PCR41 DES integration test |
| `pytest` (from `engineering_tools/`) | `pytest` | Run all tests |

---

## Gaps / Unknowns
- `Robot_Simulations/` workspace is early-stage; its `eden` environment and Docker setup are not integrated with the `engineering_tools` tree.
- `simulation/DES/core/entities/beam.py` role in the current DES vs. the older `PCR41_Assembly` (in `projects/PCR41_test/`) is ambiguous — two PCR41 implementations exist at different levels of maturity.
- No HTTP API or database layer is present; this is a purely local desktop/scripting tool.
- PDF export in the Structural GUI (`pdf_export.py`) depends on an optional library (`check_available()` guards it); the exact dependency is not determined from inspection.
