---
status: partial
phase: 01-solver-foundation
source: [01-VERIFICATION.md]
started: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. OPW Parameter Visual Verification Against Fanuc Manual Fig 3.2a

The OPW parameters (a1=150mm, a2=-615mm, c1=500mm, c2=640mm, c3=200mm, c4=65mm) were found by numerical search and produce the correct 1831.6mm max reach with 500/500 passing round-trips. However, computational self-consistency cannot confirm these parameters map to the correct physical joints. A swapped a1/c1 would still round-trip correctly but model the wrong robot geometry.

**Steps:**
1. Open: `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.pdf`, Fig 3.2a
2. Compare each parameter against the diagram dimensions:
   - a1 = 150 mm
   - a2 = -615 mm
   - c1 = 500 mm
   - c2 = 640 mm
   - c3 = 200 mm
   - c4 = 65 mm
3. Run `cd Robot_Simulations/optimizer && venv_optimizer/bin/python -m pytest tests/ -v` — confirm all 39 tests pass
4. If parameters correct: update this file `result: passed`
5. If corrections needed: update `config.py` constants marked `[VERIFY-FIG3.2A]`, re-run tests, update this file

expected: OPW parameters (a1, a2, c1–c4) match the physical robot dimensions in Fig 3.2a of the Fanuc M-20iD/20 Mechanical Unit Operators Manual
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
