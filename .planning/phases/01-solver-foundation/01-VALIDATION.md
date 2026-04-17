---
phase: 1
slug: solver-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `engineering_tools/pytest.ini` or `pyproject.toml` (Wave 0 installs) |
| **Quick run command** | `cd engineering_tools && python -m pytest tests/test_solver/ -x -q` |
| **Full suite command** | `cd engineering_tools && python -m pytest tests/test_solver/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd engineering_tools && python -m pytest tests/test_solver/ -x -q`
- **After every plan wave:** Run `cd engineering_tools && python -m pytest tests/test_solver/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | ENV-01 | — | N/A | infra | `uv venv venv_optimizer && uv pip install py-opw-kinematics pytest` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | ENV-02 | — | N/A | infra | `python -c "import opw_kinematics; print('ok')"` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | SOLV-01 | — | N/A | benchmark | `python -m pytest tests/test_solver/test_benchmark.py -v` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | SOLV-02 | — | N/A | unit | `python -m pytest tests/test_solver/test_round_trip.py -v` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | SOLV-03 | — | N/A | unit | `python -m pytest tests/test_solver/test_joint_limits.py -v` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | SOLV-04 | — | N/A | unit | `python -m pytest tests/test_solver/test_config.py -v` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 1 | SOLV-05 | — | N/A | unit | `python -m pytest tests/test_solver/test_units.py -v` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 1 | LOG-01 | — | N/A | unit | `python -m pytest tests/test_solver/test_logging.py -v` | ❌ W0 | ⬜ pending |
| 1-01-09 | 01 | 1 | ENV-03 | — | N/A | infra | `cat venv_optimizer/pyvenv.cfg | grep version` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `engineering_tools/tests/test_solver/__init__.py` — test package init
- [ ] `engineering_tools/tests/test_solver/test_round_trip.py` — stubs for SOLV-02 (500+ FK→IK tests)
- [ ] `engineering_tools/tests/test_solver/test_benchmark.py` — stubs for SOLV-01 (≥4 µs/query)
- [ ] `engineering_tools/tests/test_solver/test_joint_limits.py` — stubs for SOLV-03 (joint limit enforcement)
- [ ] `engineering_tools/tests/test_solver/test_config.py` — stubs for SOLV-04 (no magic numbers)
- [ ] `engineering_tools/tests/test_solver/test_units.py` — stubs for SOLV-05 (Imperial+SI output)
- [ ] `engineering_tools/tests/test_solver/test_logging.py` — stubs for LOG-01
- [ ] `engineering_tools/tests/conftest.py` — shared fixtures (if needed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OPW parameters match Fig 3.2a from M-20iD/20 manual PDF | SOLV-01 | Requires visual inspection of raster image in PDF | Open PDF, locate Fig 3.2a, compare a1/a2/b/c1–c4 values to config.py |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
