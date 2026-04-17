<!-- GSD:project-start source:PROJECT.md -->
## Project

**EDEN Cell Optimizer**

A Python-based hierarchical exhaustive grid search optimizer that determines the optimal Fanuc M-20iD/20 robot base placement (X position, Y position, yaw orientation, riser height, riser cross-section) and EOAT geometry for a structural beam coping cell. Given the full AISC structural steel catalog and a 1-meter workzone, it finds the best (tool design, placement) combination maximizing reachability and cope feasibility subject to a 1.0 mm RSS TCP error budget, using bounded brute-force search at buildable resolution with no machine learning or heuristics.

**Core Value:** Determine — exhaustively and without heuristics — the specific riser height, riser section, base X/Y/yaw, and tool geometry that achieves maximum AISC catalog reachability within the workzone, quantifying exactly what the gap is and which beams or faces fail.

### Constraints

- **Performance**: C++ OPW via pybind11 mandatory — pure Python is 10× too slow for the grid size
- **Accuracy**: TCP error budget ≤ 1.0 mm RSS total; riser + baseplate deflection ≤ 0.55 mm; tool boom deflection ≤ 0.20 mm; modal frequency f₁ ≥ 15 Hz
- **Safety factor**: 1.25× applied to all tool masses before wrist load diagram check
- **Hardware**: Single machine, i5-13600K, 14 threads, Linux (Ubuntu 22.04+)
- **No ML**: Results must be exhaustive brute-force over pruned search space
- **Build accuracy**: Y positions at 25 mm steps (field anchor bolt tolerance); riser heights at discrete stock lengths — no false precision
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Summary
## Languages
- Python 3.12 — all application code across both sub-projects
## Runtime
- Python 3.12 (confirmed by `.venv/lib/python3.12/` path and system `python3 --version`)
- README states Python 3.8+ minimum for `engineering_tools`
- `pip` with `venv` — main project venv at `.venv/`
- `pip` with `venv` — Robot_Simulations/eden venv at `Robot_Simulations/eden/.venv/`
- No lockfile detected (no `poetry.lock`, `Pipfile.lock`, or `pip-compile` output files)
- Node.js / `npx` used only to launch MCP server processes (see `.mcp.json`)
## Frameworks
- PySide6 6.10.2 (installed) / >=6.6.0 (required) — Qt6 bindings for the interactive 3D frame modeler
- PyVista 0.47.1 (installed) / >=0.43.0 (required) — 3D VTK-based visualization embedded in the GUI
- PyVistaQt 0.11.3 (installed) / >=0.11.0 (required) — Qt integration bridge for PyVista
- VTK 9.6.0 (installed) — underlying rendering engine used by PyVista
- QtPy 2.4.3 — Qt abstraction layer
- PyNiteFEA 1.6.2 (installed) / >=0.3.0 (required) — 3D frame FEA solver; wrapped by `engineering_tools/mech_core/analysis/fea.py`
- SimPy 4.1.1 — process-based discrete-event simulation framework; used by `engineering_tools/simulation/DES/`
- Genesis (`genesis-world`) — GPU-accelerated physics simulator with CUDA/Vulkan/Metal backends; entry point in `Robot_Simulations/eden/experiments/hello_genesis.py`
- Stable-Baselines3 (`stable-baselines3[extra]`) — reinforcement learning algorithms
- Gymnasium — standard RL environment interface
- PyTorch >=2.1.0 with CUDA 12.1 — deep learning framework, CUDA GPU execution
- TensorBoard — training metrics visualization
- pytest 9.0.2 (installed) / >=7.3.0 (in requirements comments) — used for both sub-projects
- pytest-cov >=4.0.0 (required for eden, not installed in main venv)
## Key Dependencies
- NumPy 2.3.5 (installed) / >=1.24.0 (required) — array operations throughout
- SciPy 1.16.3 (installed) / >=1.10.0 (required) — numerical solvers
- pandas 2.3.3 (installed) / >=2.0.0 (required) — data handling and analysis
- Pint 0.25.2 (installed) / >=0.21.0 (required) — dimensional unit analysis; central to all calculations via `mech_core/standards/units.py`
- fluids 1.3.0 (installed) / >=1.0.23 (required) — fluid dynamics calculations, used in `mech_core/analysis/fluid_dynamics/gas_jets.py`
- matplotlib 3.10.8 (installed) / >=3.7.0 (required) — plot generation for FEA diagrams (shear/moment, Gantt charts)
- `mcp` 1.24.0 — Model Context Protocol SDK, used by Claude AI assistant integration
- `mcp_server_git` — MCP Git server
- `uvicorn` 0.38.0, `starlette` 0.50.0, `httpx` 0.28.1 — HTTP infrastructure for MCP server transport
- `python-dotenv` — environment variable loading
- `pdfkit` (not in requirements, optional install) — wraps `wkhtmltopdf` for PDF report export from `simulation/Structural/pdf_export.py`; `wkhtmltopdf` binary must be installed separately
## Configuration
- No `.env` file detected in the project root
- Database connection string embedded in `.mcp.json` (PostgreSQL, dev only)
- No `pyproject.toml` or `setup.cfg` found; no formal package build configuration
- No build system (no `pyproject.toml`, `setup.py`, or Makefile)
- Runs as a local source tree; `cd engineering_tools && python -m simulation.Structural`
- Docker used only for the Robot_Simulations/eden GPU training environment
## Docker (Robot_Simulations/eden)
- `Dockerfile.training` — FROM `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime`; installs Genesis, SB3, Gymnasium, NumPy, SciPy, pandas, matplotlib, PyYAML, TensorBoard, pytest
- `Dockerfile.authoring` — separate authoring workspace image
- `Dockerfile.genesis`, `Dockerfile.genesis-official`, `Dockerfile.genesis-cpu`, `Dockerfile.amdgpu` — GPU/CPU variants
- `docker-compose.yaml` — `authoring-ws` service with NVIDIA GPU passthrough, X11 display forwarding, host networking for GUI
- NVIDIA GPU with CUDA 12.1 + cuDNN 8
- `NVIDIA_DRIVER_CAPABILITIES=all` environment variable required
## Dev Tooling
- black >=23.0.0 — code formatter
- pylint >=2.17.0 — linter
- mypy >=1.0.0 — static type checker
- pytest >=7.3.0
- black >=23.0.0
- flake8 >=6.0.0
## CAD / Data Formats
- AISC shapes database: `engineering_tools/mech_core/standards/materials/data/aisc_shapes.json`
- Stock thicknesses: `engineering_tools/mech_core/standards/materials/data/standard_thicknesses.json`
- DSTV/NC1 CNC files: parsed by `engineering_tools/simulation/DES/core/machines/subsystems/planning/parsers/dstv.py`; sample at `engineering_tools/projects/PCR41_test/sample_beam.nc1`
- STEP/STP files: `Robot_Simulations/eden/cad_source/` — robot cell CAD for Genesis scenes
## Gaps / Unknowns
- No lockfile exists; exact transitive dependency versions not pinned, creating reproducibility risk.
- `pdfkit` and `wkhtmltopdf` are optional and not in `requirements.txt`; PDF export is conditionally available.
- Python minimum version is stated as 3.8+ in README but actual venvs use 3.12; compatibility with older versions is untested.
- `Robot_Simulations/eden` has its own separate git history (`Robot_Simulations/.git`) — it may be a git submodule or a separately managed repo embedded here.
- No CI/CD pipeline configuration (no `.github/workflows/`, no `Jenkinsfile`, no `.gitlab-ci.yml`) was found.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Summary
## Style Configuration
## Naming Conventions
- `snake_case` throughout: `gas_jets.py`, `thermal_removal.py`, `push_rod_feeder.py`
- Module files match the primary class or domain they contain
- Test files prefix with `test_`: `test_gas_jets.py`, `test_safety_plc.py`
- Verification scripts use `verify_` prefix: `verify_aisc_benchmark.py`, `verify_example_f1_2a.py`
- `PascalCase`: `FrameAnalysis`, `SectionProperties`, `StructuralMaterial`, `EventLogger`, `SafetyPLC`, `CrossTransfer`
- Enums use `PascalCase` name with `UPPER_SNAKE` members: `RobotState.HOME`, `FeederState.MOVING`
- `dataclass` is used for pure data containers: `SurfacePhysics`, `StructuralMaterial`, `Event`
- `snake_case` for all functions: `calculate_nozzle_exit_velocity`, `check_flexural_resistance`, `get_section`
- Calculation functions use verb-noun pattern: `calculate_*`, `check_*`, `get_*`
- Private/internal helpers prefixed with `_`: `_get_or_add_material`, `_section_counter`
- Local loop vars and temporaries: `snake_case` — `mat_name`, `Lb_val`, `phi_Mn`
- Physics variables (intermediate calculation values) often use short-form matching engineering notation: `Fy_val`, `KL_r_val`, `Fcr_val`, `Mn_val`
- Constants use `UPPER_SNAKE_CASE`: `DB_PATH`, `CURRENT_DIR`, `FLUIDS_AVAILABLE`
- Pint quantity parameters typed as `Q_`: `thickness: Q_`, `tool_power: Q_`
- Optional parameters use `Optional[Q_] = None` pattern
## Type Annotations
## Documentation Conventions
## Error Handling Patterns
## Logging and Observability
## Code Organization Patterns
## Import Organization
## Gaps / Unknowns
- No formatter config (black, ruff, autopep8) enforced — style is maintained manually.
- No linter config present; flake8/pylint not active.
- Warning pattern is inconsistent (`print("[WARNING]...")` vs `warnings.warn(...)`).
- `projects/` directory files (`design_mezzanine.py`, `design_portal.py`, `eoat_sweep.py`) were not fully reviewed — may have lower convention adherence.
- GUI code in `simulation/Structural/` was not deeply analyzed for convention adherence.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Summary
## High-Level Pattern
```
```
## Component Responsibilities
### `mech_core` — Physics Kernel
- **`mech_core.analysis`** — Numerical analysis engines
- **`mech_core.components`** — Physical component models
- **`mech_core.standards`** — Code-of-practice logic and reference data
### `simulation/Structural` — 3D Structural Lab GUI
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
### `simulation/DES` — Discrete Event Simulation Engine
```
```
- `core/logging/logger.py`: `EventLogger` — timestamped event stream.
- `core/entities/beam.py`: `BeamEntity` — workpiece entity that flows through the simulation.
- `core/visualization/gannt.py`: Gantt chart output.
- `core/machines/subsystems/planning/parsers/dstv.py`: Parses DSTV NC files (structural steel marking format).
### `projects/` — Project-specific scripts
- `mezzanine_design/design_mezzanine.py`: Full CSA S16 mezzanine structural design with FEA, connection checks, and report generation.
- `portal_design/design_portal.py`: Portal frame design.
- `PCR41_test/simulation.py`: Integration test script for PCR41 DES.
- `PCR42 EOA Tool Design/eoat_sweep.py`: End-of-arm tool design sweep.
### `Robot_Simulations/` — Robot placement tooling
## Data Flow
### Structural GUI solve flow
### DES simulation flow
## State Management
## Key Design Patterns
- **Singleton unit registry** (`mech_core/standards/units.py`): All dimensional values use `pint` quantities via a single shared `ureg`. This enforces unit consistency across the entire repo.
- **Snapshot undo** (`UndoStack`): Avoids Command pattern complexity; serialises to dict before every mutation (max depth 60).
- **Signal/slot mediator** (`MainWindow._connect()`): GUI panels are fully decoupled; `MainWindow` is the only place that knows about all panels.
- **Coordinate axis swap in solve**: GUI uses Z-up; PyNite uses Y-up. The swap (y↔z) is performed explicitly in `DocumentController.run_solve()` and in load direction mapping.
- **Subsystem composition over inheritance** in DES: `PCR41_Controller` composes hardware subsystem objects rather than subclassing them.
- **Config-file-driven robot kinematics**: `RobotArm` loads `configs/fanuc.json` at construction, decoupling kinematics parameters from code.
- **Symbolic calculation traces**: CSA S16 checks (`csa_s16/members.py`) return `steps` lists with intermediate values, enabling engineering report traceability.
## Entry Points
| Entry Point | How to Invoke | Purpose |
|-------------|---------------|---------|
| `engineering_tools/simulation/Structural/__main__.py` | `python -m simulation.Structural` (from `engineering_tools/`) | Launch 3D Structural Lab GUI |
| `engineering_tools/projects/mezzanine_design/design_mezzanine.py` | `python design_mezzanine.py` | Run mezzanine design script |
| `engineering_tools/projects/portal_design/design_portal.py` | `python design_portal.py` | Run portal frame design |
| `engineering_tools/projects/PCR41_test/simulation.py` | `python simulation.py` | Run PCR41 DES integration test |
| `pytest` (from `engineering_tools/`) | `pytest` | Run all tests |
## Gaps / Unknowns
- `Robot_Simulations/` workspace is early-stage; its `eden` environment and Docker setup are not integrated with the `engineering_tools` tree.
- `simulation/DES/core/entities/beam.py` role in the current DES vs. the older `PCR41_Assembly` (in `projects/PCR41_test/`) is ambiguous — two PCR41 implementations exist at different levels of maturity.
- No HTTP API or database layer is present; this is a purely local desktop/scripting tool.
- PDF export in the Structural GUI (`pdf_export.py`) depends on an optional library (`check_available()` guards it); the exact dependency is not determined from inspection.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| cartographer | Tools to maintain the repository map. Use ONLY when the project structure has changed significantly. | `.claude/skills/catographer/SKILL.md` |
| governance | Protocols for reading Architect specifications and filing implementation reports. | `.claude/skills/governance/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
