# EDEN Cell Optimizer

## What This Is

A Python-based exhaustive grid search optimizer that determines the globally optimal Fanuc M-20iD/35 robot base placement (Y position + riser height) and end-of-arm tool (EOAT) geometry for a beam coping cell. Given the full AISC structural steel catalog and a 1-meter workzone, it provably finds the single best (tool design, placement) combination that maximizes reachability and cope feasibility across all beam shapes at 6mm buildable resolution.

## Core Value

Prove — exhaustively and without heuristics — that a specific riser height, base Y position, and tool geometry achieves 100% reachability across the entire AISC catalog within the given workzone, or quantify exactly what the gap is.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] OPW IK solver configured for Fanuc M-20iD/35 with validated FK→IK round-trips
- [ ] Phase 1 tool design table: sweep all (torch_angle × boom_length × puck_drop) combos, reject by wrist load diagram + deflection constraint, output valid_tools.json
- [ ] Collision environment: two boundary wall planes (X=±515mm), conveyor surface (Z=838mm), AISC beam extrusion meshes
- [ ] Target database: straight-cut sweep poses (25mm spacing) and cope trajectories for all AISC catalog beams, sorted hardest-first
- [ ] Phase A grid search: 100 representative tools × full placement grid → top 500 placements
- [ ] Phase B grid search: all valid tools × top 500 placements → globally optimal (tool, placement) pair
- [ ] Results reporting: best_config.json, reachability heatmap, cope report, gap report, visualization of top-N configs
- [ ] 14-thread parallelization on i5-13600K with estimated ~33 hour wall time
- [ ] Dual-unit logging (Imperial + SI) throughout

### Out of Scope

- Machine learning, genetic algorithms, or any sampling-based optimization — pure brute force only
- ROS1/ROS2/catkin dependencies — standalone Python + C++ pybind11 only
- Secondary workzone or cantilevered riser configurations — single zone, straight riser only
- GPU compute — workload is purely CPU-bound
- Real-time robot control or communication — offline planning tool only

## Context

**Robot:** Fanuc ARC Mate 120iD/35 (M-20iD/35), 1831mm reach, 35kg payload, standard OPW kinematic structure (parallel base + spherical wrist).

**Physical Setup:** 1m workzone centered at origin. Conveyor rollers at Z=838mm (33"). Robot X position fixed at 0. Y placement in two valid ranges: +1612mm to +1778mm (opposite side) or -190mm to -1778mm (datum side). Riser is straight 10"×10"×3/8" HSS.

**EOAT Design Space:** 5 torch angles (0°/30°/45°/60°/90°) × ~58 boom lengths (155mm to max, 6mm steps) × ~25 puck drop positions = ~7,250 raw candidates. After wrist load rejection (~85% rejection rate): ~1,088 valid tools. After TCP clustering: ~100-200 representative groups.

**IK:** OPW kinematics via C++ pybind11 wrapper (~4μs per query). Pure Python OPW is non-viable (~40μs, doubles runtime to 52+ days). URDF source: ros-industrial/fanuc — verify M-20iD/35 vs M-20iA distinction.

**Beam Catalog:** Full AISC catalog ≤300 lb/ft fitting 56" conveyor width, queried from aisc.py. Shapes: W/C/S (3-face), L-angle (inverted V, 2 slopes), HSS/Pipe/Rect tube (4-face). Cope trajectory types: square, radius, block.

**Compute:** Intel i5-13600K, 14 threads. Phase A ~17 hours, Phase B ~16 hours. Total ~33 hours.

**Robot manual:** `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.md` (OCR'd).

## Constraints

- **Performance**: C++ OPW via pybind11 mandatory — pure Python is 10× too slow for the grid size
- **Accuracy**: Grid resolution 6mm (1/8" buildable). TCP deflection ≤1/16" (1.5875mm) at max riser height
- **Safety factor**: 1.25× applied to all tool masses before wrist load diagram check
- **Hardware**: Single machine, i5-13600K, 14 threads, Linux
- **No ML**: Results must be provably globally optimal (exhaustive), not probabilistically good
- **Build accuracy**: All output coordinates must be achievable with a tape measure (6mm / 1/8" resolution)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two-phase hierarchical search | Flat grid = 766M cells (31 days). Hierarchical = 33 hours. Phase A finds placements with 100 representative tools; Phase B tests all tools at top 500 placements. Still 100% brute force | — Pending |
| C++ OPW via pybind11 | Pure Python OPW ~40μs/query; C++ ~4μs. On 766M-cell grid this is 33 hours vs 52 days | — Pending |
| TCP clustering (10mm bins) | Tools with TCP within 10mm behave nearly identically at same placement. Reduces Phase A from ~1800 to ~100 representative tools | — Pending |
| Hardest-beam-first evaluation | Early termination: failing W36 skips remaining 290 beams. Reduces avg evaluation time ~70% | — Pending |
| Fixed X=0 robot position | Symmetry — no advantage to offsetting along beam travel direction | — Pending |
| 5 discrete torch angles (special triangles) | 0°/30°/45°/60°/90° are easy to cut, verify, and build. Continuous angles would add ~10× design space with negligible benefit | — Pending |
| Representative collision blocks | Full pinch unit/conveyor mesh not needed. Two boundary wall planes + conveyor surface capture hard constraints | — Pending |
| M-20iD/35 replaces M-20iA | New product design. Higher payload (35kg vs 20kg), same reach class, integrated cable routing | — Pending |

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
*Last updated: 2026-04-15 after initialization*
