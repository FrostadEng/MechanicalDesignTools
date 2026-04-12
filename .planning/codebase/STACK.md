# Technology Stack
_Generated: 2026-04-12_

## Summary

MechanicalDesignTools is a pure Python engineering platform split into two sub-projects: `engineering_tools` (structural design + FEA + discrete-event simulation + a PySide6/PyVista GUI), and `Robot_Simulations/eden` (GPU-accelerated robot RL training built on the Genesis physics simulator). Both sub-projects run Python 3.12 and manage dependencies through separate virtual environments. There are no JavaScript/TypeScript application layers; the only Node.js usage is tooling for MCP servers invoked by the AI assistant configuration.

## Languages

**Primary:**
- Python 3.12 — all application code across both sub-projects

**No secondary languages** — shell scripts exist only inside `Robot_Simulations/eden/docker/` for Docker build automation.

## Runtime

**Environment:**
- Python 3.12 (confirmed by `.venv/lib/python3.12/` path and system `python3 --version`)
- README states Python 3.8+ minimum for `engineering_tools`

**Package Managers:**
- `pip` with `venv` — main project venv at `.venv/`
- `pip` with `venv` — Robot_Simulations/eden venv at `Robot_Simulations/eden/.venv/`
- No lockfile detected (no `poetry.lock`, `Pipfile.lock`, or `pip-compile` output files)
- Node.js / `npx` used only to launch MCP server processes (see `.mcp.json`)

## Frameworks

**GUI (engineering_tools):**
- PySide6 6.10.2 (installed) / >=6.6.0 (required) — Qt6 bindings for the interactive 3D frame modeler
- PyVista 0.47.1 (installed) / >=0.43.0 (required) — 3D VTK-based visualization embedded in the GUI
- PyVistaQt 0.11.3 (installed) / >=0.11.0 (required) — Qt integration bridge for PyVista
- VTK 9.6.0 (installed) — underlying rendering engine used by PyVista
- QtPy 2.4.3 — Qt abstraction layer

**Finite Element Analysis:**
- PyNiteFEA 1.6.2 (installed) / >=0.3.0 (required) — 3D frame FEA solver; wrapped by `engineering_tools/mech_core/analysis/fea.py`

**Discrete-Event Simulation:**
- SimPy 4.1.1 — process-based discrete-event simulation framework; used by `engineering_tools/simulation/DES/`

**Robot / RL Training (Robot_Simulations/eden):**
- Genesis (`genesis-world`) — GPU-accelerated physics simulator with CUDA/Vulkan/Metal backends; entry point in `Robot_Simulations/eden/experiments/hello_genesis.py`
- Stable-Baselines3 (`stable-baselines3[extra]`) — reinforcement learning algorithms
- Gymnasium — standard RL environment interface
- PyTorch >=2.1.0 with CUDA 12.1 — deep learning framework, CUDA GPU execution
- TensorBoard — training metrics visualization

**Testing:**
- pytest 9.0.2 (installed) / >=7.3.0 (in requirements comments) — used for both sub-projects
- pytest-cov >=4.0.0 (required for eden, not installed in main venv)

## Key Dependencies

**Scientific Computing:**
- NumPy 2.3.5 (installed) / >=1.24.0 (required) — array operations throughout
- SciPy 1.16.3 (installed) / >=1.10.0 (required) — numerical solvers
- pandas 2.3.3 (installed) / >=2.0.0 (required) — data handling and analysis

**Engineering-Specific:**
- Pint 0.25.2 (installed) / >=0.21.0 (required) — dimensional unit analysis; central to all calculations via `mech_core/standards/units.py`
- fluids 1.3.0 (installed) / >=1.0.23 (required) — fluid dynamics calculations, used in `mech_core/analysis/fluid_dynamics/gas_jets.py`
- matplotlib 3.10.8 (installed) / >=3.7.0 (required) — plot generation for FEA diagrams (shear/moment, Gantt charts)

**MCP / AI Tooling (not application code):**
- `mcp` 1.24.0 — Model Context Protocol SDK, used by Claude AI assistant integration
- `mcp_server_git` — MCP Git server
- `uvicorn` 0.38.0, `starlette` 0.50.0, `httpx` 0.28.1 — HTTP infrastructure for MCP server transport
- `python-dotenv` — environment variable loading

**PDF Export (optional, external binary required):**
- `pdfkit` (not in requirements, optional install) — wraps `wkhtmltopdf` for PDF report export from `simulation/Structural/pdf_export.py`; `wkhtmltopdf` binary must be installed separately

## Configuration

**Environment:**
- No `.env` file detected in the project root
- Database connection string embedded in `.mcp.json` (PostgreSQL, dev only)
- No `pyproject.toml` or `setup.cfg` found; no formal package build configuration

**Build:**
- No build system (no `pyproject.toml`, `setup.py`, or Makefile)
- Runs as a local source tree; `cd engineering_tools && python -m simulation.Structural`
- Docker used only for the Robot_Simulations/eden GPU training environment

## Docker (Robot_Simulations/eden)

**Images defined in `Robot_Simulations/eden/docker/`:**
- `Dockerfile.training` — FROM `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime`; installs Genesis, SB3, Gymnasium, NumPy, SciPy, pandas, matplotlib, PyYAML, TensorBoard, pytest
- `Dockerfile.authoring` — separate authoring workspace image
- `Dockerfile.genesis`, `Dockerfile.genesis-official`, `Dockerfile.genesis-cpu`, `Dockerfile.amdgpu` — GPU/CPU variants
- `docker-compose.yaml` — `authoring-ws` service with NVIDIA GPU passthrough, X11 display forwarding, host networking for GUI

**GPU Requirements (eden training):**
- NVIDIA GPU with CUDA 12.1 + cuDNN 8
- `NVIDIA_DRIVER_CAPABILITIES=all` environment variable required

## Dev Tooling

**Listed in `Robot_Simulations/eden/requirements.txt` (not enforced in main venv):**
- black >=23.0.0 — code formatter
- pylint >=2.17.0 — linter
- mypy >=1.0.0 — static type checker

**Commented out in `engineering_tools/requirements.txt` (not installed):**
- pytest >=7.3.0
- black >=23.0.0
- flake8 >=6.0.0

**No `pyproject.toml`, `.flake8`, `mypy.ini`, or `.prettierrc` config files found.** Dev tooling is specified in requirements but has no committed configuration files enforcing it.

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
