# Milestones

## v1.0 Solver Foundation (Shipped: 2026-04-17)

**Phases completed:** 2 phases, 2 plans, 5 tasks

**Key accomplishments:**

- Isolated `venv_optimizer` with py-opw-kinematics 1.0.0; `config.py` with all M-20iD/20 physical constants; `logging_utils.py` dual-unit output; 23 TDD tests passing
- OPW solver wrapper with corrected M-20iD/20 parameters (1831.6mm reach); `inverse_rt` fast path at 3.4 µs/call; 500 FK→IK round-trips all passing; spawn multiprocessing verified; 39/39 tests green

---
