# Phase 1: Solver Foundation - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Build and validate the C++ OPW analytical IK extension for the Fanuc M-20iD/20; configure a reproducible optimizer environment with all physical constants consolidated in `config.py`. This phase delivers the hard blocking gate — nothing in Phase 2 or beyond can be built until this phase's success criteria pass.

**What this phase delivers:**
- Working OPW pybind11 C++ extension at ≥4 µs/query
- Validated FK→IK round-trips (500+ samples, <0.01 mm / <0.01°)
- Operating space confirmed against Fig 3.2a
- All joint limits and OPW solution filtering verified
- `config.py` with all M-20iD/20 physical constants, workzone geometry, and TCP budget sub-allocations
- Dual-unit logging infrastructure (Imperial + SI)

**What this phase does NOT include:**
- Tool table computation (Phase 2)
- Riser deflection model (Phase 2)
- Collision scene or target database (Phase 2)
- Grid search workers (Phase 3)

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- **D-01:** Optimizer module lives at `Robot_Simulations/optimizer/` — a new standalone module alongside `eden/`, committed to the Robot_Simulations sub-repo (per `planning.sub_repos: ["Robot_Simulations"]` in config.json)
- **D-02:** Environment: new `Robot_Simulations/optimizer/venv_optimizer/` (separate from genesis venv to avoid numpy 1.26.4 pin conflict)
- **D-03:** Build artifacts (pybind11 `.so`) live inside the optimizer module at `Robot_Simulations/optimizer/opw_kinematics/` with a `CMakeLists.txt` and `setup.py` for local editable install

### OPW Parameter Source
- **D-04:** Primary source for M-20iD/20 kinematic parameters is Fanuc manual B-84074EN/03 Fig 3.2a (operating space diagram) + Brandstotter paper conventions for a1/a2/b/c1–c4. Manual dimensions are authoritative.
- **D-05:** Check `ros-industrial/fanuc` (branch: noetic-devel) and `ros-industrial/fanuc_experimental` for any M-20iD/20 or M-20iD/25 URDF as a secondary verification cross-check only. If URDF exists, extract OPW parameters from it using Brandstotter sign conventions (not raw URDF joint-origin values, which use a different convention).
- **D-06:** Do NOT guess OPW parameters. If manual dimensions and URDF disagree, the validation suite (FK→IK round-trips + operating space envelope) is the arbiter — the set that passes validation is used.

### pybind11 Binding Approach
- **D-07:** Use `opw_kinematics` C++ header-only library (github.com/Jmeyer1292/opw_kinematics). Implement a custom pybind11 binding (~100-line `.cpp` + CMakeLists.txt). There is no PyPI package — this is the only viable path at <4 µs/query.
- **D-08:** Check for any existing Python binding forks before writing from scratch (search GitHub for `opw_kinematics python` or `opw-python`). Use one if it exists and passes validation; write custom binding if not.
- **D-09:** The pybind11 module must expose: `solve(params, T) -> List[JointConfig]` returning up to 8 IK solutions; `forward(params, joints) -> SE3Transform`. Both as pure Python-callable functions with no C++ objects crossing the boundary.

### Validation Suite (Hard Gate)
- **D-10:** The validation suite from spec Section 11C is non-negotiable and must fully pass before Phase 2 begins:
  1. 500+ FK→IK round-trips on random joint configs within M-20iD/20 limits — position error <0.01 mm, orientation error <0.01°
  2. Operating space envelope verification — reachable workspace matches Fig 3.2a bounds
  3. All 6 joint limits verified (J3 asymmetric ±268.4° upper limit is a known off-by-one risk)
  4. All 8 OPW solution candidates correctly filtered by joint limits
  5. Wrist-aligned singularity (J5 ≈ 0) and full-extension (max reach) behavior documented
  6. Riser-height regression: T_world_base computed for H=0 vs H=914mm must produce verifiably different IK results for the same target pose
- **D-11:** Validation tests must be runnable as `pytest` tests (not just scripts), committed alongside the binding code. Phase 2 cannot start if any test fails.

### config.py Organization
- **D-12:** Single `config.py` at `Robot_Simulations/optimizer/config.py` — module-level constants only (no dataclasses, no Pydantic). Simple, directly readable, zero import overhead.
- **D-13:** Constants grouped by section matching V3 spec structure:
  - `# === ROBOT: M-20iD/20 (Section 2) ===` — joint limits, reach, payload, OPW params
  - `# === TCP ERROR BUDGET (Section 3) ===` — all RSS sub-allocations
  - `# === WORKZONE GEOMETRY (Section 1) ===` — origin, conveyor, wall positions
  - `# === RISER SECTIONS (Section 4) ===` — all 5 candidate section properties
  - `# === RISER HEIGHTS (Section 4) ===` — 8 discrete stock lengths
  - `# === TOOL GEOMETRY (Section 5) ===` — boom constants, puck mass/CG, cable density
  - `# === SEARCH GRID (Section 10) ===` — X/Y/yaw grid values
- **D-14:** All values in SI (meters, kg, radians) as base units. Imperial equivalents added as inline comments where the spec provides them (e.g., `CONVEYOR_Z = 0.838  # 33"`).

### Dual-Unit Logging
- **D-15:** Implement a `log_dual(label, si_value, si_unit, imperial_value, imperial_unit)` utility function in a `logging_utils.py` module at Phase 1. All subsequent phases use this function — no ad-hoc print statements.

### Claude's Discretion
- Build system: CMake vs. setuptools for the pybind11 build — planner decides based on what integrates cleanly with the optimizer venv
- Whether to vendor opw_kinematics headers into the repo or use a git submodule
- Exact naming of the pybind11 Python module (e.g., `_opw_kinematics` with a Python wrapper `opw_kinematics.py`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (Authoritative)
- `Robot_Simulations/Optimizing_Robot_Placement.md` — V3 master specification. Section 2 (robot specs), Section 3 (TCP error budget), Section 11 (IK solver setup + validation, CRITICAL), Section 14 Step 0 (implementation sequence for this phase)

### Robot Manual
- `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.md` — OCR'd manual. Fig 3.2a (operating space diagram for OPW parameter extraction), Fig 3.5c (wrist load diagram), p.12 (joint limits table), p.17–21 (motion limits)

### Existing Codebase Assets
- `engineering_tools/mech_core/components/members/aisc.py` — confirmed AISC loader (2299 shapes). Phase 1 ENV setup must ensure optimizer venv can import this.
- `engineering_tools/mech_core/standards/units.py` — Pint ureg singleton. Optimizer uses its own dual-unit logging (not Pint), but this is the reference for how units are handled in the broader codebase.
- `engineering_tools/simulation/DES/core/machines/subsystems/robots/robot_arm.py` — existing simplified RobotArm class. Reference for how existing code models Fanuc robots; NOT the OPW solver (too slow).
- `engineering_tools/simulation/DES/core/machines/subsystems/robots/configs/fanuc.json` — existing Fanuc config. Reference for what parameters are already captured; cross-check link lengths for sanity.
- `engineering_tools/projects/PCR42 EOA Tool Design/eoat_sweep.py` — existing EOAT parameter sweep. Read before Phase 2 TOOL table work — may have reusable geometry logic.

### Research Outputs
- `.planning/research/STACK.md` — Stack decisions: OPW binding, pybind11 pattern, python-fcl install notes, pyarrow, multiprocessing spawn
- `.planning/research/ARCHITECTURE.md` — Component boundaries, worker pattern, config.py as load-bearing artifact
- `.planning/research/PITFALLS.md` — CRITICAL for Phase 1: OPW parameter sign conventions (Pitfall #1), joint limit boundary off-by-one J3 (Pitfall #2), pybind11 fork corruption (Pitfall #3)

### External References (Step 0)
- `https://github.com/Jmeyer1292/opw_kinematics` — OPW C++ header-only library
- `https://github.com/ros-industrial/fanuc` (branch: noetic-devel) — check for M-20iD/20 or M-20iD/25 URDF
- `https://github.com/ros-industrial/fanuc_experimental` — check for M-20iD/20 support

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `aisc.py` + `aisc_shapes.json`: AISC catalog is already available — ENV-01 setup must ensure the optimizer venv can reach it (symlink or PYTHONPATH inclusion)
- `fanuc.json`: Contains Fanuc link-length / speed parameters for DES use — cross-reference link lengths (c1, c2, c3, c4 candidates) as a sanity check against manual extraction, but do not use as primary source
- `eoat_sweep.py`: Contains existing EOAT geometry sweep logic — read before Phase 2 to avoid duplicating boom/puck geometry math

### Established Patterns
- **Config files**: The DES subsystem uses JSON configs per machine (`fanuc.json`, `kuka.json`). The optimizer uses a Python module (`config.py`) instead — this is deliberate (constants need to be importable by workers without JSON parsing overhead)
- **No build system**: The repo has no Makefile or pyproject.toml. The pybind11 build will need its own `CMakeLists.txt` + `setup.py` within the optimizer module — this is new infrastructure for the project
- **Separate venvs**: `Robot_Simulations/eden` already uses a separate venv. `optimizer/venv_optimizer` follows the same pattern

### Integration Points
- `Robot_Simulations/optimizer/` is a new top-level module — no existing integration points to wire up in Phase 1
- aisc.py import path: `engineering_tools.mech_core.components.members.aisc` — optimizer must add `engineering_tools/` to PYTHONPATH or use a relative sys.path insert in the entry points

</code_context>

<specifics>
## Specific Ideas

- V3 spec Section 11B explicitly states: "Do NOT guess parameters. Validate with FK→IK round-trips (Section 11C)." — This is the guiding principle for Phase 1 parameter extraction work.
- V3 spec Section 11C gives the exact validation criteria: ≥1 IK solution FKs back to same pose, <0.01 mm position, <0.01° orientation. These are the acceptance test pass criteria.
- PITFALLS.md Pitfall #1: OPW sign conventions — the Brandstotter paper uses a specific sign convention for a2 (negative in some notations). Must check the opw_kinematics C++ library documentation for its expected sign convention before transcribing manual values.
- PITFALLS.md Pitfall #2: J3 joint limit is asymmetric (+268.4° upper, -190° lower) — this is easy to get backwards. Verify from spec Section 2 table, not from DES robot_arm.py (which may use different limits).
- ARCHITECTURE.md: "config.py is architecturally load-bearing" — magic numbers elsewhere make hardware validation error tracing impossible.

</specifics>

<deferred>
## Deferred Ideas

- python-fcl installation validation: Research flagged this as a Phase 1 install risk (Ubuntu 24.04 libfcl-dev version mismatch). This is a Phase 2 concern — collision environment isn't needed until Phase 2. However, the Phase 1 ENV-01 setup should note this as a known risk item to investigate.
- IKFast fallback via Dockerized OpenRAVE: Deferred — only invoke if OPW parameter extraction proves impossible from both manual and URDF sources.
- Robot link STL files for self-collision: Not needed for Phase 1. Needed in Phase 2/4 for COLL-04. Note for planner.

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-solver-foundation*
*Context gathered: 2026-04-16*
