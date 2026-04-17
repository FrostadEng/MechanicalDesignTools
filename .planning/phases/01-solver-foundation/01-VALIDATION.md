---
phase: 1
slug: solver-foundation
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
audited: 2026-04-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `Robot_Simulations/optimizer/pytest.ini` |
| **Quick run command** | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/ -x -q` |
| **Full suite command** | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds (includes multiprocessing spawn test) |

---

## Sampling Rate

- **After every task commit:** Run `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | ENV-01 | — | N/A | infra | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -c "import py_opw_kinematics; import numpy; import scipy; print('OK')"` | N/A (runtime check) | green |
| 1-01-02 | 01 | 1 | ENV-02, LOG-01 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_config.py tests/test_logging_utils.py -v` | Wave 0 | green |
| 1-02-01 | 02 | 2 | SOLV-01 | — | N/A | benchmark | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_ik_performance -x` | Wave 0 | green |
| 1-02-02 | 02 | 2 | SOLV-02 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_fk_ik_roundtrip_500 -x` | Wave 0 | green |
| 1-02-03 | 02 | 2 | SOLV-03 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_operating_space_boundary -x` | Wave 0 | green |
| 1-02-04 | 02 | 2 | SOLV-03 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_operating_space_within_workzone -x` | Wave 0 | green |
| 1-02-05 | 02 | 2 | SOLV-04 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_singularity_wrist_aligned -x` | Wave 0 | green |
| 1-02-06 | 02 | 2 | SOLV-04 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_singularity_full_extension -x` | Wave 0 | green |
| 1-02-07 | 02 | 2 | SOLV-05 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_joint_limits_all_axes -x` | Wave 0 | green |
| 1-02-08 | 02 | 2 | SOLV-05 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_j3_wide_limit_retained -x` | Wave 0 | green |
| 1-02-09 | 02 | 2 | SOLV-05 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_all_8_solutions_present -x` | Wave 0 | green |
| 1-02-10 | 02 | 2 | SOLV-05 | — | N/A | unit | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_opw_validation.py::test_riser_height_regression -x` | Wave 0 | green |
| 1-02-11 | 02 | 2 | ENV-03 | — | N/A | integration | `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/test_multiprocessing.py -v` | Wave 0 | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `Robot_Simulations/optimizer/tests/__init__.py` — test package init
- [x] `Robot_Simulations/optimizer/tests/conftest.py` — shared fixtures (rng seed, tolerance constants)
- [x] `Robot_Simulations/optimizer/tests/test_config.py` — covers ENV-02
- [x] `Robot_Simulations/optimizer/tests/test_logging_utils.py` — covers LOG-01
- [x] `Robot_Simulations/optimizer/tests/test_opw_validation.py` — covers SOLV-01 through SOLV-05
- [x] `Robot_Simulations/optimizer/tests/test_multiprocessing.py` — covers ENV-03
- [x] `Robot_Simulations/optimizer/pytest.ini` — test discovery configuration
- [x] Framework install: `uv pip install pytest` — in venv_optimizer

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OPW parameters match Fig 3.2a from M-20iD/20 manual PDF | SOLV-03 | Requires visual inspection of raster image in PDF | Open PDF, locate Fig 3.2a, compare a1/a2/b/c1-c4 values to config.py |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-04-16 — 39/39 tests green, 0.84s runtime

---

## Validation Audit 2026-04-16

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests | 39 |
| Pass | 39 |
| Fail | 0 |

All 13 task requirements had tests already written and passing. Wave 0 files all exist. No gaps to fill.
