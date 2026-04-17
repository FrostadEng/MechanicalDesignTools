# EDEN Cell Optimizer

## What This Is

A Python-based hierarchical exhaustive grid search optimizer that determines the optimal Fanuc M-20iD/20 robot base placement (X position, Y position, yaw orientation, riser height, riser cross-section) and EOAT geometry for a structural beam coping cell. Given the full AISC structural steel catalog and a 1-meter workzone, it finds the best (tool design, placement) combination maximizing reachability and cope feasibility subject to a 1.0 mm RSS TCP error budget, using bounded brute-force search at buildable resolution with no machine learning or heuristics.

## Core Value

Determine — exhaustively and without heuristics — the specific riser height, riser section, base X/Y/yaw, and tool geometry that achieves maximum AISC catalog reachability within the workzone, quantifying exactly what the gap is and which beams or faces fail.

## Requirements

### Validated

- ✓ OPW IK solver configured for Fanuc M-20iD/20 with validated FK→IK round-trips (3.4 µs/query via Rust/PyO3 py-opw-kinematics) — v1.0
- ✓ Single `config.py` with all physical constants (OPW params, joint limits, workzone, risers, TCP budget) — no magic numbers elsewhere — v1.0
- ✓ `spawn` multiprocessing start method verified without PyO3 GIL corruption — v1.0
- ✓ Dual-unit logging (Imperial + SI) infrastructure established via `logging_utils.py` — v1.0

### Active

- [ ] Phase 1 tool design table: sweep all (torch_angle × boom_length × puck_drop) combos, reject by wrist load diagram (1.25× safety) + boom deflection ≤0.20 mm, cluster by (TCP_xyz, CG_xy, torch_angle) at 5 mm, output valid_tools.json (~1044 entries, ~180 cluster representatives)
- [ ] Riser deflection + modal pre-computation: closed-form superposition model (column bending + baseplate rotation), reject (section, height) pairs where δ_TCP > 0.55 mm or f₁ < 15 Hz
- [ ] Collision environment: boundary wall planes (X=±515 mm), conveyor surface (Z=838 mm), ground plane, active beam mesh per evaluation (NEW in V3)
- [ ] Target database: straight-cut sweep poses (25 mm spacing) and cope trajectories for all AISC catalog beams ≤300 lb/ft fitting 56″ conveyor, sorted hardest-first by reach and geometry difficulty
- [ ] Phase A grid search: ~180 representative tools × full placement grid (~1.19M cells) → top 500 placements, scoring by reachability_pct + hardware_cost
- [ ] Phase B grid search: all ~1044 valid tools × top 500 placements (~522k evaluations) with cope feasibility check → optimal (tool, placement) pair
- [ ] TCP error budget RSS tracking: model riser column + baseplate rotation + tool boom contributions; flag unmodeled terms (robot accuracy, thermal, beam positioning, cable reaction)
- [ ] Results reporting: best_config.json, top_10_configs.json, reachability heatmap, cope report, gap report, error_budget_report.json, URDF scene visualization of top-10 configs
- [ ] 14-thread parallelization on i5-13600K with estimated ~23 hour wall time
- [ ] Dual-unit logging (Imperial + SI) throughout

### Out of Scope

- Machine learning, genetic algorithms, or any sampling-based optimization — pure brute force only
- ROS1/ROS2/catkin dependencies — standalone Python + C++ pybind11 only
- Secondary workzone or cantilevered riser configurations — single zone, straight riser only
- GPU compute — workload is purely CPU-bound
- Real-time robot control or communication — offline planning tool only
- Continuous riser height grid — discrete stock lengths only (12″/18″/24″/30″/36″/42″/48″ + floor mount)
- Online robot calibration or closed-loop TCP correction — offline optimization only

## Context

**Robot:** Fanuc ARC Mate 120iD/20 (M-20iD/20), 1831 mm reach, 25 kg payload, standard OPW kinematic structure (parallel base + spherical wrist). Repeatability ±0.02 mm; absolute accuracy ±0.5–1.5 mm (uncalibrated offline).

**Physical Setup:** 3 m workzone (X = ±1500 mm) centered at origin. Conveyor surface at Z = 838 mm (33″). Conveyor width 56″ (1422 mm). Global datum: end of conveyor roller at (0,0,0).

**Search Space (V3 — all new relative to V2):**
- X position: {-100, 0, +100} mm (3 values; V2 fixed X=0)
- Y position: +1612–+1778 mm (opposite side) or -450 to -1778 mm (datum side), 25 mm steps = 61 values
- Robot yaw: {0°, 90°, 180°, 270°} (4 values; V2 did not search yaw)
- Riser section: 5 candidates (10×10×⅜ HSS, 8×8×½ HSS, 12×12×⅜ HSS, 8″ sch 80 pipe, 10×10 grout-filled; V2 fixed 10×10×⅜)
- Riser height: 8 discrete stock lengths (0/305/457/610/762/914/1067/1219 mm; V2 used continuous 6 mm grid)
- Placement grid before tool: 3 × 61 × 4 × 5 × 8 = 29,280 configurations

**EOAT Design Space:** 5 torch angles (0°/30°/45°/60°/90°) × ~58 boom lengths (155 mm to deflection limit, 6 mm steps) × ~24 puck drop positions = ~6,960 raw candidates. After wrist load rejection (~85%): ~1,044 valid tools. TCP/CG clustering at 5 mm: ~150–200 cluster representatives.

**TCP Error Budget (V3 RSS):** 1.0 mm RSS total — robot accuracy (0.50), riser column (0.30), baseplate rotation (0.25), tool boom (0.20), thermal (0.30), beam positioning (0.50), cable drag (0.15), dynamic path vibration (0.20). Pass gates: riser δ ≤ 0.55 mm, tool boom δ ≤ 0.20 mm, f₁ ≥ 15 Hz.

**IK:** OPW kinematics via C++ pybind11 wrapper (~4 μs per query). Pure Python OPW is non-viable (~40 μs). URDF source: ros-industrial/fanuc — verify M-20iD/20 vs M-20iD/25 distinction (same kinematics, different wrist motors).

**Beam Catalog:** Full AISC catalog ≤300 lb/ft fitting 56″ conveyor. Shapes: W/C/S (3-face), L-angle (inverted V, 2 slopes), HSS/Pipe/Rect tube (4-face). Cope trajectory types: square, radius, block.

**Compute:** Intel i5-13600K (14 threads). Phase A ~18 hours, Phase B ~5 hours. Total ~23 hours (vs. V2's 33 hours).

**Robot manual:** `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.md` (OCR'd). Key sections: specs p.12, operating space Fig 3.2a p.15, wrist load diagram Fig 3.5c p.25.

## Constraints

- **Performance**: C++ OPW via pybind11 mandatory — pure Python is 10× too slow for the grid size
- **Accuracy**: TCP error budget ≤ 1.0 mm RSS total; riser + baseplate deflection ≤ 0.55 mm; tool boom deflection ≤ 0.20 mm; modal frequency f₁ ≥ 15 Hz
- **Safety factor**: 1.25× applied to all tool masses before wrist load diagram check
- **Hardware**: Single machine, i5-13600K, 14 threads, Linux (Ubuntu 22.04+)
- **No ML**: Results must be exhaustive brute-force over pruned search space
- **Build accuracy**: Y positions at 25 mm steps (field anchor bolt tolerance); riser heights at discrete stock lengths — no false precision

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two-phase hierarchical search | Flat grid = 30.6M cells (13 days). Phase A with 180 rep tools finds good placements; Phase B tests all 1044 tools at top 500. Still 100% brute force over full space | — Pending |
| Rust/PyO3 py-opw-kinematics instead of C++ pybind11 | Same performance goal (~4 µs); py-opw-kinematics 1.0.0 on PyPI is simpler than building pybind11 C++ extension. D-08 supersedes D-09 in Plan 02. | ✓ 3.4 µs/call achieved — v1.0 |
| TCP clustering tightened to 5 mm CG-inclusive | V2 10 mm clustering with CG mismatch caused ~5–15% Phase A false-passes. Now clusters on (TCP_xyz, CG_xy, torch_angle) | — Pending |
| Robot yaw as search variable | J1 range changes with orientation; 4 discrete values cheap to test, potentially large impact on J-limit behavior | — Pending |
| Riser cross-section as search variable | Stiffness/mass varies by section; testing 5 candidates likely shifts optimum more than any grid refinement | — Pending |
| Buildable resolution (25 mm Y, discrete stock heights) | Field anchor tolerance ±3–5 mm. Shop floor can't build to 6 mm precision. V2 resolution was false precision | — Pending |
| RSS error budget (1.0 mm target) | Hypertherm plasma ISO 9013 Range 3–4 is ±0.4–1.0 mm. AISC hole tolerance ±1 mm. V2's 0.2 mm kerf comparison was wrong frame | — Pending |
| Baseplate rotation in deflection model | Typically 2–10× column deflection alone. V2 ignored this; now modeled via anchor bolt stretch + grout compression | — Pending |
| Modal frequency check f₁ ≥ 15 Hz | Cope dynamics excite 5–12 Hz. Static deflection alone misses vibration-related accuracy failure | — Pending |
| Active beam collision check | Cope trajectories pass under flanges; tool must not hit beam. V2 only checked wall planes — missed real failure mode | — Pending |
| Refined early termination (reach vs. geometry) | V2 early-terminated on any fail. V3 separates reach-fail (large beam, quit) from geometry-fail (weird angle, continue). Prevents dropping 99% coverage configs | — Pending |
| Robot X as search variable | V2 assumed X=0 by symmetry; now verified empirically with 3 values at minimal cost | — Pending |
| Hardware validation plan (top-10 configs) | Optimizer outputs are hypotheses. Laser tracker + modal test + test cuts required before committing to final design | — Pending |
| "Guaranteed global optimum" claim removed | Honest framing: bounded grid-resolution search over pruned tool space. Discretization + clustering → not truly global | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-17 after v1.0 milestone — Solver Foundation shipped (1,227 LOC Python, 39/39 tests green, 3.4 µs/call IK)*
