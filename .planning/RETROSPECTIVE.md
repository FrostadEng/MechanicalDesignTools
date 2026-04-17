# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — Solver Foundation

**Shipped:** 2026-04-17  
**Phases:** 1 | **Plans:** 2

### What Was Built

- `venv_optimizer` with py-opw-kinematics 1.0.0, scipy, numpy, pyarrow, python-fcl; reproducible environment for all subsequent phases
- `config.py` — single source of truth for all M-20iD/20 physical constants (OPW params, joint limits, 5 riser sections, 8 riser heights, TCP budget sub-allocations, workzone geometry)
- `opw_solver/wrapper.py` — OPW IK/FK wrapper achieving 3.4 µs/call on i5-13600K; `inverse_rt`/`forward_rt` fast path for grid search hot loop
- 39-test validation suite: 500 FK→IK round-trips, joint limit filtering (all 8 solutions), singularity behavior documentation, spawn multiprocessing safety
- `logging_utils.py` — dual-unit (Imperial + SI) logging infrastructure for all optimizer output

### What Worked

- **TDD red-green cycle**: Writing all 39 tests before any implementation code eliminated ambiguity and made every task's completion criteria concrete
- **Numerical parameter search**: Finding OPW params by optimizing for known max reach (1831mm) + round-trip consistency was faster and more reliable than manually reading DH tables from the PDF
- **Single config.py constraint**: Enforcing no magic numbers anywhere produced a clean codebase from day one; `test_no_magic_numbers_in_config` catches regressions automatically
- **py-opw-kinematics over pybind11**: Using an existing PyPI package (Rust/PyO3) instead of building a C++ extension eliminated an entire build toolchain problem with identical performance

### What Was Inefficient

- **False human verification gate**: The SOLV-03 checkpoint was scoped against Fig 3.2a (workspace envelope diagram) which cannot validate individual link parameters. Wasted planning overhead on a gate that should never have been written — the automated FK→IK tests were already the correct and sufficient verification
- **SUMMARY.md missing `requirements_completed` frontmatter**: The 3-source requirements cross-reference fell back to 2 sources; future plans should include this field from the start

### Patterns Established

- `inverse_rt` / `forward_rt` as the canonical hot-path API (returns numpy array, no object allocation) — all Phase 2+ grid search workers should use these exclusively
- `spawn` start method enforced at process pool construction, never inherited — prevents PyO3/pybind11 GIL corruption under any future extension additions
- Riser sections and heights as config-level constants (not computed) — Phase 2 riser model reads directly from `config.RISER_SECTIONS` and `config.RISER_HEIGHTS_MM`

### Key Lessons

1. **Workspace envelope diagrams cannot verify kinematic parameters.** Fig 3.2a shows reachable volume, not link dimensions. A parameter swap (e.g., A1 ↔ C1) still produces correct round-trips and correct max reach — only a URDF or DH table comparison catches it. Don't use envelope diagrams as kinematic ground truth.
2. **Numerical parameter finding + consistency tests = sufficient for OPW validation.** 500 round-trips at <0.01mm + max reach matching spec + workspace boundary tests fully verify the parameter set. No human visual inspection required.
3. **`SEARCH_Y_MM` must go in `config.py` before Phase 2.** Currently deferred; if Phase 2 defines it outside config.py it violates ENV-02. Pre-emptively add `SEARCH_Y_RANGE_MM` and `SEARCH_Y_STEP_MM` to config.py at Phase 2 plan start.

### Cost Observations

- Model mix: predominantly Sonnet 4.6
- Notable: Numerical OPW parameter search (wrong initial params gave 1577mm reach, corrected to 1831.6mm) discovered and resolved entirely within automated test loop — zero human debugging time

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 1 | 2 | First milestone — baseline established |

### Cumulative Quality

| Milestone | Tests | Pass Rate | LOC |
|-----------|-------|-----------|-----|
| v1.0 | 39 | 100% | 1,227 Python |

### Top Lessons (Verified Across Milestones)

1. Workspace envelope diagrams ≠ kinematic parameter ground truth — use URDF or automated consistency tests
