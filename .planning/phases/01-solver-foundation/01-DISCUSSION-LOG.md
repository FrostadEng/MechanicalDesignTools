# Phase 1: Solver Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 01-solver-foundation
**Mode:** --auto (all choices auto-selected with recommended defaults)
**Areas discussed:** Project Structure, OPW Parameter Source, pybind11 Binding Approach, Validation Suite, config.py Organization, Dual-Unit Logging

---

## Project Structure

| Option | Description | Selected |
|--------|-------------|----------|
| `Robot_Simulations/optimizer/` | New standalone module alongside eden/, committed to Robot_Simulations sub-repo | ✓ |
| `engineering_tools/simulation/optimizer/` | Add to existing engineering_tools tree | |
| `Robot_Simulations/eden/optimizer/` | Nested inside eden, shares genesis venv | |

**Auto-selected:** `Robot_Simulations/optimizer/` (recommended default)
**Notes:** Matches sub_repos config, keeps optimizer isolated from genesis GPU stack, avoids numpy pin conflict.

---

## OPW Parameter Source

| Option | Description | Selected |
|--------|-------------|----------|
| Fanuc manual Fig 3.2a + Brandstotter conventions | Manual dimensions as authoritative source; URDF as secondary cross-check | ✓ |
| URDF-first extraction | Parse ros-industrial/fanuc URDF joint origins, convert to OPW params | |
| Both in parallel | Extract from both, compare, flag discrepancies | |

**Auto-selected:** Fanuc manual Fig 3.2a + Brandstotter conventions (recommended default)
**Notes:** URDF sign convention mismatch is Pitfall #1 from research. Manual is authoritative; URDF is verification only.

---

## pybind11 Binding Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Custom binding of opw_kinematics header-only | ~100-line .cpp + CMakeLists.txt wrapping Jmeyer1292/opw_kinematics | ✓ |
| Find existing Python binding fork | Search GitHub for opw-python or similar before writing | |
| IKFast via Docker | Last resort if OPW parameters unresolvable | |

**Auto-selected:** Custom binding (after checking for existing forks first) (recommended default)
**Notes:** No PyPI package exists. Stack research confirmed this is the only viable path for <4 µs/query.

---

## Validation Suite

| Option | Description | Selected |
|--------|-------------|----------|
| Full spec Section 11C suite | 500+ round-trips + envelope + joint limits + singularities + riser regression | ✓ |
| Minimal round-trips only | 100 round-trips, skip envelope and riser regression | |
| Skip and test via Phase A smoke test | Defer validation until search pipeline is built | |

**Auto-selected:** Full spec Section 11C suite (recommended default)
**Notes:** This is the hard blocking gate. Skipping any component risks silent wrong answers propagating through all downstream phases.

---

## config.py Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level constants | Simple assignments, grouped by spec section, zero import overhead | ✓ |
| Dataclasses per section | Typed, IDE-friendly, slightly more overhead | |
| JSON config file | Runtime-loadable, but adds parsing overhead in hot worker path | |

**Auto-selected:** Module-level constants (recommended default)
**Notes:** Workers import config.py at startup. Module-level constants have zero parse overhead and are directly readable by humans debugging hardware validation errors.

---

## Dual-Unit Logging

| Option | Description | Selected |
|--------|-------------|----------|
| `log_dual()` utility function in logging_utils.py | Implemented in Phase 1, used by all subsequent phases | ✓ |
| Ad-hoc f-string logging per module | Each module formats its own dual-unit strings | |
| Pint-based unit tracking | Use existing ureg from engineering_tools | |

**Auto-selected:** `log_dual()` utility (recommended default)
**Notes:** Establishes consistent dual-unit output pattern from Phase 1. Subsequent phases inherit without re-implementing.

---

## Claude's Discretion

- Build system choice (CMake vs. setuptools for pybind11) — planner decides
- Whether to vendor opw_kinematics headers vs. git submodule
- Exact pybind11 Python module naming convention

## Deferred Ideas

- python-fcl install validation spike: noted as Phase 2 risk, not Phase 1 scope
- IKFast Docker fallback: deferred unless OPW parameter extraction fails
- Robot link STL files for self-collision: needed in Phase 2/4, not Phase 1
