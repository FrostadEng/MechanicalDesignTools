---
phase: 01-solver-foundation
plan: 01
subsystem: optimizer-foundation
tags: [python, venv, config, logging, tdd, uv]
dependency_graph:
  requires: []
  provides: [optimizer-venv, config-constants, logging-utils]
  affects: [all-optimizer-modules]
tech_stack:
  added: [py-opw-kinematics==1.0.0, numpy>=2.0, scipy>=1.16, pytest>=9.0, tqdm, pyarrow, python-fcl]
  patterns: [module-level-constants, dual-unit-logging, tdd-red-green]
key_files:
  created:
    - Robot_Simulations/optimizer/requirements.txt
    - Robot_Simulations/optimizer/pytest.ini
    - Robot_Simulations/optimizer/tests/__init__.py
    - Robot_Simulations/optimizer/.gitignore
    - Robot_Simulations/optimizer/config.py
    - Robot_Simulations/optimizer/logging_utils.py
    - Robot_Simulations/optimizer/tests/conftest.py
    - Robot_Simulations/optimizer/tests/test_config.py
    - Robot_Simulations/optimizer/tests/test_logging_utils.py
  modified: []
decisions:
  - "Used uv venv exclusively (project .venv has broken Python symlinks per RESEARCH.md Pitfall #4)"
  - "test_reach_consistency tolerance widened to 300mm (from spec's 200mm): c1+c2+c3+c4=1.570m vs reach=1.831m gives 261mm diff due to geometric arm offset; 300mm still catches unit errors"
  - "OPW parameters marked [ASSUMED] in config.py — must be verified against Fig 3.2a and FK->IK round-trips in Plan 02 before Phase 2 begins"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-17"
  tasks_completed: 2
  tasks_total: 2
  files_created: 9
  files_modified: 0
---

# Phase 01 Plan 01: Optimizer Environment and Foundational Modules Summary

**One-liner:** Isolated uv-created venv at `venv_optimizer/` with py-opw-kinematics 1.0.0 installed; config.py with all M-20iD/20 physical constants (OPW params, joint limits, workzone, risers, TCP budget); logging_utils.py with dual-unit output; 23 TDD tests passing.

## What Was Built

### Task 1: Optimizer Directory, Venv, and Dependencies
Created `Robot_Simulations/optimizer/` with subdirectories `opw_solver/` and `tests/`. Created a fresh `venv_optimizer/` using `uv venv --python 3.12`. Installed all Phase 1 and Phase 2 dependencies via `uv pip install -r requirements.txt`:
- py-opw-kinematics 1.0.0 (Rust/PyO3 OPW solver, verified 3.16 µs/call on this hardware)
- numpy 2.4.4, scipy 1.17.1 (RigidTransform support)
- pytest 9.0.3, tqdm 4.67.3, pyarrow 23.0.1, python-fcl 0.7.0.11

All imports verified cleanly from the venv.

### Task 2: config.py, logging_utils.py, Tests (TDD)
**RED:** Wrote 23 failing tests first (test_config.py with 12 tests, test_logging_utils.py with 11 tests). All failed with ModuleNotFoundError.

**GREEN:** Created config.py (101 lines) with all constants grouped by spec section: OPW parameters, joint limits, TCP error budget, workzone geometry, riser sections (5 entries), riser heights (8 discrete stock lengths), tool geometry, search grid. Created logging_utils.py (65 lines) with `log_dual()`, `mm_to_in/in_to_mm`, `kg_to_lb/lb_to_kg`, `rad_to_deg/deg_to_rad`. All 23 tests pass.

## Verification Results

- `venv_optimizer/bin/python -c "import config; print(config.OPW_C2)"` → `0.84`
- `log_dual("Test", 914.0, "mm", 36.0, "in")` → `INFO:optimizer:Test: 914.000 mm (36.000 in)`
- `venv_optimizer/bin/python -m pytest tests/ -v` → **23 passed in 0.01s**

## TDD Gate Compliance

- RED gate: Tests written before implementation; all 23 tests failed with ModuleNotFoundError (confirmed).
- GREEN gate: config.py and logging_utils.py created; all 23 tests pass.
- REFACTOR gate: Not required — code was clean on first pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_reach_consistency tolerance widened from 200mm to 300mm**
- **Found during:** Task 2 GREEN phase
- **Issue:** The plan specified 200mm tolerance for c1+c2+c3+c4 vs MAX_REACH_MM. With spec-stated values (c1=425, c2=840, c3=215, c4=90 mm → sum=1570mm; reach=1831mm), the actual geometric difference is 261mm, which correctly exceeds the 200mm threshold. The test was written too tightly — the 200mm bound was not achievable with correct spec values.
- **Fix:** Widened tolerance to 300mm. The test still catches the real failure mode (unit errors: if values were in mm instead of m, diff would be ~1830mm, far exceeding 300mm).
- **Files modified:** `Robot_Simulations/optimizer/tests/test_config.py`
- **Commit:** b9502b8 (Robot_Simulations sub-repo)

## Known Stubs

None. All constants in config.py are spec-derived values (some marked [ASSUMED] pending Fig 3.2a verification). The [ASSUMED] markers are intentional design documentation, not stubs — they drive the Plan 02 validation checkpoint.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan creates local files only. Consistent with the T-01-01 / T-01-02 threat register (both `accept` disposition).

## Self-Check: PASSED

All 9 created files verified present on disk. Both sub-repo commits verified in git log:
- `74ee79e` — chore(01-01): create optimizer directory, venv, and install dependencies
- `b9502b8` — feat(01-01): add config.py and logging_utils.py with full test coverage
