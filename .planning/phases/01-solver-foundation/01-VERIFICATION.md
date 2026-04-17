---
phase: 01-solver-foundation
verified: 2026-04-16T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
gaps:
human_verification:
  - test: "Open Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.pdf, navigate to Fig 3.2a (Operating Space diagram), and compare the diagram dimensions against config.py values: OPW_A1=150mm, OPW_A2=-615mm, OPW_C1=500mm, OPW_C2=640mm, OPW_C3=200mm, OPW_C4=65mm"
    expected: "Dimensions from the PDF Fig 3.2a match (within ~10mm) the config.py values, confirming the numerically-found OPW parameters are physically correct for the M-20iD/20 geometry"
    why_human: "The OPW parameters were found by numerical search (not read directly from the datasheet). The automated FK->IK round-trips and max-reach tests pass, but they only confirm internal self-consistency — they cannot confirm the parameters match the real robot's physical dimensions. The Plan 02 Task 3 checkpoint explicitly requires human visual verification against Fig 3.2a before Phase 2 begins. Parameters in config.py are still marked [VERIFY-FIG3.2A]."
---

# Phase 1: Solver Foundation Verification Report

**Phase Goal:** Developer can run validated FK->IK round-trips on the M-20iD/20 at >=4 µs/query inside a reproducible environment
**Verified:** 2026-04-16T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | OPW solver achieves >=4 µs/query on the i5-13600K host | VERIFIED | `inverse_rt()` benchmarks at 3.40 µs/call — measured live in venv_optimizer. test_ik_performance passes (asserts <=4.0 µs). |
| 2 | 500+ FK->IK round-trips pass with position error <0.01 mm and orientation error <0.01 deg | VERIFIED | test_fk_ik_roundtrip_500 passes: 500/500 round-trips under tolerance (RANDOM_SEED=42, all within 0.01mm / 0.01 deg). |
| 3 | Joint limit enforcement verified for all 6 axes and all 8 OPW solution candidates | VERIFIED | test_joint_limits_all_axes, test_j3_wide_limit_retained (240 deg retained), test_j3_beyond_limit_rejected (280 deg rejected), test_all_8_solutions_present all pass. |
| 4 | All physical constants live in a single config.py with no magic numbers elsewhere | VERIFIED | config.py is 153 lines, defines all OPW params, joint limits, workzone geometry, TCP budget, riser sections (5), riser heights (8), tool constants. wrapper.py contains `import config` and zero hardcoded numerics. test_no_magic_numbers_in_config passes. |
| 5 | All physical quantities printed by the optimizer appear in both Imperial and SI units | VERIFIED | logging_utils.py exports log_dual(), mm_to_in(), in_to_mm(), kg_to_lb(), lb_to_kg(), rad_to_deg(), deg_to_rad(). test_log_dual_format and test_all_exports pass (23/23 config+logging tests pass). |

**Score:** 5/5 truths verified

Note: ROADMAP SC #1 refers to "C++ pybind11 extension" — the actual implementation uses py-opw-kinematics (Rust/PyO3 PyPI package). This is an intentional design decision documented in Plan 02 (D-08 supersedes D-09). The performance and functional intent of SC #1 is fully satisfied: a compiled native extension is importable and achieves the target speed. This constitutes an acceptable implementation deviation, not a goal failure.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Robot_Simulations/optimizer/requirements.txt` | Pinned dependency list for venv_optimizer | VERIFIED | 7 lines; contains `py-opw-kinematics==1.0.0`, `scipy>=1.16.0` |
| `Robot_Simulations/optimizer/config.py` | All physical constants for the optimizer | VERIFIED | 153 lines; contains OPW_A1, OPW_C2, joint limits, RISER_SECTIONS (5 entries), RISER_HEIGHTS_MM (8 entries), TCP budget, workzone geometry |
| `Robot_Simulations/optimizer/logging_utils.py` | Dual-unit logging utility | VERIFIED | 73 lines; exports log_dual, mm_to_in, in_to_mm, kg_to_lb, lb_to_kg, rad_to_deg, deg_to_rad |
| `Robot_Simulations/optimizer/pytest.ini` | Test discovery configuration | VERIFIED | Contains `testpaths = tests`, `python_files = test_*.py`, `addopts = -v --tb=short` |
| `Robot_Simulations/optimizer/tests/test_config.py` | Tests for config.py completeness | VERIFIED | 12 tests covering OPW params, joint limits, TCP budget, riser sections, workzone geometry — all pass |
| `Robot_Simulations/optimizer/tests/test_logging_utils.py` | Tests for log_dual and unit converters | VERIFIED | 11 tests — all pass |
| `Robot_Simulations/optimizer/opw_solver/wrapper.py` | OPW IK/FK wrapper with joint limit filtering | VERIFIED | 156 lines; exports forward, forward_rt, inverse, inverse_rt, filter_by_limits; all wired to config.py and py_opw_kinematics |
| `Robot_Simulations/optimizer/opw_solver/__init__.py` | Public API re-exports | VERIFIED | Contains `from .wrapper import forward, forward_rt, inverse, inverse_rt, filter_by_limits` |
| `Robot_Simulations/optimizer/tests/test_opw_validation.py` | Full Phase 1 validation suite (SOLV-01 through SOLV-05) | VERIFIED | 14 tests covering all SOLV-01..SOLV-05 and riser height regression — all pass |
| `Robot_Simulations/optimizer/tests/test_multiprocessing.py` | spawn start method verification (ENV-03) | VERIFIED | 2 tests: test_spawn_pool (20 IK tasks across Pool(2)) and test_spawn_start_method_enforced — both pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `opw_solver/wrapper.py` | `config.py` | `import config` | WIRED | wrapper.py line 31: `import config`; uses OPW_A1..C4, OPW_JOINT_OFFSETS, OPW_FLIP_AXES, JOINT_LIMITS_LOWER_RAD, JOINT_LIMITS_UPPER_RAD |
| `opw_solver/wrapper.py` | `py_opw_kinematics` | `from py_opw_kinematics import KinematicModel, Robot` | WIRED | Lines 30, 35-47: KinematicModel and Robot instantiated at module level as singletons |
| `opw_solver/__init__.py` | `opw_solver/wrapper.py` | `from .wrapper import ...` | WIRED | Line 18: `from .wrapper import forward, forward_rt, inverse, inverse_rt, filter_by_limits` |
| `tests/test_opw_validation.py` | `opw_solver.wrapper` | `from opw_solver.wrapper import forward, inverse, filter_by_limits` | WIRED | Line 26 in test file; all 14 tests use the imported functions |
| `tests/test_multiprocessing.py` | `opw_solver.wrapper` | import inside worker function | WIRED | Worker function imports `from opw_solver.wrapper import forward, inverse` in subprocess |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces a computational library (IK/FK solver) and configuration module, not UI components or data-rendering artifacts. All data flows are through function calls, not rendered state. The round-trip tests (test_fk_ik_roundtrip_500) serve as the behavioral data-flow verification.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| venv_optimizer Python can import key packages | `venv_optimizer/bin/python -c "from py_opw_kinematics import KinematicModel, Robot; import numpy; import scipy; import pytest; print('ALL IMPORTS OK')"` | ALL IMPORTS OK | PASS |
| Fast-path IK at <=4 µs/call | Live benchmark via test_ik_performance | 3.40 µs/call | PASS |
| 500 FK->IK round-trips | test_fk_ik_roundtrip_500 | 500/500 pass | PASS |
| J3=240 deg retained, J3=280 deg rejected | test_j3_wide_limit_retained, test_j3_beyond_limit_rejected | Both pass | PASS |
| spawn multiprocessing pool with IK | test_spawn_pool | 20/20 tasks complete with >=1 non-zero result | PASS |
| All 39 tests pass | `venv_optimizer/bin/python -m pytest tests/ -v` | 39 passed in 0.86s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SOLV-01 | 01-02 | OPW extension importable, >=4 µs/query | SATISFIED | test_import + test_ik_performance pass (3.40 µs/call) |
| SOLV-02 | 01-02 | 500+ FK->IK round-trips <0.01mm / <0.01 deg | SATISFIED | test_fk_ik_roundtrip_500 passes: 500/500 |
| SOLV-03 | 01-02 | OPW params produce workspace matching Fig 3.2a operating space | PARTIALLY SATISFIED | Automated: max reach 1831.6mm matches spec; test_operating_space_boundary, test_home_position_fk, test_operating_space_within_workzone pass. Human verification pending: params marked [VERIFY-FIG3.2A] in config.py awaiting visual Fig 3.2a cross-check |
| SOLV-04 | 01-02 | Singularity behavior documented (not silent failure) | SATISFIED | test_singularity_wrist_aligned, test_singularity_full_extension, test_unreachable_pose all pass with documented behavior assertions |
| SOLV-05 | 01-02 | Joint limits enforced for all 6 axes, all 8 solutions filtered | SATISFIED | test_joint_limits_all_axes, test_j3_wide_limit_retained, test_j3_beyond_limit_rejected, test_all_8_solutions_present, test_riser_height_regression all pass |
| ENV-01 | 01-01 | venv_optimizer with all required deps importable | SATISFIED | venv_optimizer/bin/python exists; py-opw-kinematics, numpy, scipy, pytest, tqdm, pyarrow, python-fcl all install verified |
| ENV-02 | 01-01 | Single config.py with all physical constants, no magic numbers elsewhere | SATISFIED | config.py 153 lines; test_no_magic_numbers_in_config passes; wrapper.py imports config, no hardcoded values |
| ENV-03 | 01-02 | spawn start method multiprocessing works without PyO3 GIL corruption | SATISFIED | test_spawn_pool and test_spawn_start_method_enforced pass; 20 IK tasks dispatched to Pool(2) with spawn context |
| LOG-01 | 01-01 | All physical quantities logged in both Imperial and SI units | SATISFIED | logging_utils.log_dual() implemented; 11 unit tests pass; available to all subsequent optimizer modules via import |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `config.py` | 22-28 | `[VERIFY-FIG3.2A]` comments on OPW_A1, OPW_A2, OPW_C1..C4 | Info | Intentional design marker, not a stub. Parameters are numerically validated by FK->IK tests. Human visual check is the remaining gate. |

No empty implementations, TODO/FIXME stubs, return null/empty patterns, or hardcoded empty data found in any phase artifact.

### Human Verification Required

#### 1. OPW Parameter Visual Verification Against Fanuc Manual Fig 3.2a

**Test:** Open `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.pdf`, navigate to Fig 3.2a (Operating Space diagram), and compare each dimension against config.py:

- OPW_A1 = 0.150 m (150mm — base to J2 horizontal offset)
- OPW_A2 = -0.615 m (-615mm — J2 to J3 horizontal offset, negative in OPW convention)
- OPW_C1 = 0.500 m (500mm — base to J2 vertical)
- OPW_C2 = 0.640 m (640mm — J2 to J3 link)
- OPW_C3 = 0.200 m (200mm — J3 to wrist center)
- OPW_C4 = 0.065 m (65mm — wrist center to flange)

**Then run the full test suite to confirm current state:**
```bash
cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/ -v
```

**Expected:** Diagram dimensions match config.py values within ~10mm. All 39 tests pass.

**Why human:** The OPW parameters were found by numerical search to produce the correct max reach (1831.6mm) and pass 500 FK->IK round-trips. Computational self-consistency does not prove the parameters map to the correct physical joints. The Fig 3.2a diagram is the ground truth for which physical dimension each OPW parameter represents. If a1 and c1 are swapped, for example, the math still rounds trips correctly but the robot would be modeled incorrectly. This human checkpoint was explicitly scoped in Plan 02 Task 3 (blocking gate) and in the REQUIREMENTS SOLV-03 description.

**If corrections needed:** Update config.py with the correct values, re-run tests, confirm all 39 pass. The [VERIFY-FIG3.2A] markers will remain until this checkpoint is approved.

**Resume signal:** Type "approved" if parameters match Fig 3.2a and all tests pass. Type "adjust: [param=value, ...]" if corrections are needed.

### Gaps Summary

No automated gaps. All 5 ROADMAP success criteria pass automated verification. The phase goal (FK->IK round-trips at >=4 µs/query in a reproducible environment) is computationally achieved.

One human verification item remains: visual confirmation that the OPW parameters correspond to the correct physical dimensions in the Fanuc manual Fig 3.2a. This was a planned checkpoint in Plan 02 (Task 3, type: checkpoint:human-verify, gate: blocking) and is the reason status is `human_needed` rather than `passed`.

---

_Verified: 2026-04-16T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
