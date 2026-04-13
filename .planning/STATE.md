# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-12)

**Core value:** Prove static robot mounting achieves 100% reachability for PCR42 structural steel processing, eliminating 1-axis positioners.
**Current focus:** Phase 1 — AISC Filter and Shape Classification

## Current Position

Phase: 1 of 8 (AISC Filter and Shape Classification)
Plan: 0 of 6 in current phase
Status: Ready to plan
Last activity: 2026-04-12 — Roadmap and state initialized for Milestone 1

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-Phase 1]: sys.path bridge to engineering_tools/mech_core — do not pip install mech_core into Eden venv (pulls PySide6)
- [Pre-Phase 3]: optuna>=3.6.0 chosen over scikit-optimize (unmaintained since 2021) for TPE search
- [Pre-Phase 3]: requires_jac_and_IK defaults to False in Genesis 0.3.4 morphs.py:86 — always set explicitly to True

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: TCP offset (x,y,z relative to J6 faceplate) must be supplied by user before Phase 3 runs — no safe default
- [Phase 3]: FANUC M-20iD/12L reach radius has three conflicting values (1813mm, 1831mm, 1868mm) — confirm from official spec sheet before baking into reach_prefilter.py
- [Phase 3]: robot.set_pos() on fixed=True URDF after scene.build() is unverified — if broken, search loop switches to n_envs batch architecture
- [Phase 3]: robot.get_jacobian() availability in Genesis 0.3.4 unconfirmed — FD Jacobian fallback is available

## Session Continuity

Last session: 2026-04-12
Stopped at: Roadmap created, state initialized. Phase 1 ready to plan.
Resume file: None
