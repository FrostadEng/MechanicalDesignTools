# Eden Cell Optimizer — PCR42 Heavy Steel Robot Placement

## What This Is

A deterministic robot placement optimization pipeline built on top of the Eden Factory IDE. Starting from the AISC structural steel database, it establishes 2D Maximum Material Envelopes (MME) for every beam shape the PCR42 can process, then uses the Genesis physics engine to prove that a static floor-mounted FANUC M-20iD/12L can reach all required cutting faces across both work zones — enabling a standardized, modular work cell architecture.

**This is an engineering analysis tool, not a production scheduler.** It answers the question: where should the robot base go?

## Core Value

Prove that static robot mounting achieves 100% reachability for PCR42 structural steel processing, eliminating the need for costly 1-axis integrated positioners.

## Requirements

### Validated

- ✓ Genesis physics simulator operational — Docker + `.venv` with Genesis, PyTorch, CUDA running in `Robot_Simulations/eden/`
- ✓ AISC shape database loaded and queryable — `aisc_shapes.json` + `aisc.py` SectionProperties API exists in `engineering_tools/mech_core/`
- ✓ Robot kinematic utilities available — `mech_core.analysis.kinematics` (trapezoidal profiles, 3D distance)
- ✓ Fanuc robot model configuration exists — `configs/fanuc.json` used by DES `RobotArm`, baseline kinematics known
- ✓ Eden Docker infrastructure functional — GPU passthrough, compose, authoring and training containers built
- ✓ matplotlib available — used for FEA diagrams throughout `engineering_tools`; available in both venvs

### Active

**Phase 0 — 2D MME Sanity Check:**
- [ ] Filter AISC database to PCR42-compatible shapes (≤300 lbs/ft, ≤1100mm max width/depth)
- [ ] Categorize shapes: 3-face (W, S, M, HP, C, MC), 4-face (HSS rect/sq/pipe), L-angle (2 orientations for unequal legs)
- [ ] Compute composite bounding box (MME / No-Go zone) per category
- [ ] Render scaled 2D matplotlib overlays with all cross-sections + MME bounds, export PNGs
- [ ] Output to `Robot_Simulations/eden/experiments/Beam_Coping_Machine/phase0_2d_mme/`

**Phase 1 — 3D Genesis Simulation Spatial Search:**
- [ ] Load FANUC M-20iD/12L URDF from `ros-industrial/fanuc` into `eden/assets/fanuc/`
- [ ] Build Genesis scene: conveyor (with inter-roller gaps for bottom-face cuts), pinch_unit (block proxy), robot
- [ ] For each Phase-0-validated shape: place 40ft surrogate beam, derive required TCP face paths per N-face category
- [ ] Define work zones: WZ1 = +1.5ft to +4.0ft; WZ2 = -1.5ft to -3.0ft (third offset -1.5ft, dead zone = 3.0ft)
- [ ] Implement search loop: propose [X,Y,Z] base mount → IK check → collision check → singularity check → log
- [ ] Pre-filter candidate search space using FANUC M-20iD/12L reach envelope before Genesis evaluation
- [ ] Log valid poses sorted by kinematic manipulability index
- [ ] Consider Bayesian optimization for next-point proposal within pre-filtered region

### Out of Scope

- RL/reward-function training — this project uses deterministic IK reachability checks, not learned policies; RL is the prior Eden automotive use case
- Real STEP collision meshes — user will provide CAD files later; block proxies used for initial runs
- TCP geometry / plasma torch STEP model — user to supply tool offset (x,y,z relative to J6) at Phase 1 start; 50mm umbilical buffer baked into collision volume
- Full production scheduling / cycle time — that's the PCR41/PCR42 DES; this project answers placement only
- Multi-robot configurations — single FANUC M-20iD/12L only for this milestone
- Path planning quality (smooth trajectories) — IK reachability + collision-free is the acceptance criteria; motion smoothness is post-placement concern

## Context

**Machine:** PCR42 — structural steel coping/cutting line using plasma torch on a FANUC M-20iD/12L. The robot currently uses a 1-axis positioner integrated into the pinch unit, causing overhung load problems and gearbox lubrication starvation. This project proves the robot can be statically mounted instead.

**Predecessor:** Eden was originally built for automotive spot welding optimization. The Genesis Docker environment, robot model infrastructure, and hello_genesis.py experiments are the starting point. The pivot is from learning-based control (RL) to deterministic spatial search (IK + collision).

**Work Zones (from PCR42 geometry, user-provided):**
- Origin: center of pinch unit at datum, floor level
- WZ1 (main): +1.5ft to +4.0ft downstream of pinch
- WZ2 (secondary — tail features): -1.5ft to -3.0ft upstream of pinch
- Dead zone (between WZ1 near edge and WZ2 near edge): 3.0ft — these features are inaccessible, not a failure

**Key integration:** `aisc.py` and `aisc_shapes.json` live in `engineering_tools/`, but Phase 0 script runs in `Robot_Simulations/eden/` venv context. Import path bridging or a copy of the relevant data will be needed.

**Eden structure for this work:**
```
Robot_Simulations/eden/experiments/Beam_Coping_Machine/
├── phase0_2d_mme/    # Phase 0 scripts and PNG outputs
└── phase1_3d_sim/    # Phase 1 Genesis scripts
```

## Constraints

- **Tech Stack**: Python 3.x, Genesis (Embodied AI), ROS2 Jazzy, ros-industrial/fanuc URDF, numpy, matplotlib — no new heavy frameworks
- **Runtime**: All Genesis simulation must run inside the existing `Robot_Simulations/eden/.venv` (or Docker); Genesis is not available in the main `engineering_tools` venv
- **Robot base**: Floor or standard riser only (Z = 0 to 1000mm); pitch and roll strictly 0 (flat mount)
- **No Genesis modification**: Eden principle — never modify the Genesis engine itself
- **Collision meshes**: Block proxies acceptable for initial Phase 1; real STEP files to be swapped in later without code restructuring
- **User-supplied data at Phase 1 start**: TCP x,y,z offset relative to J6 faceplate (required before running search)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Static mounting over 1-axis positioner | Eliminates overhung loads, gearbox starvation, cost; this whole project proves it's viable | — Pending |
| Deterministic IK search over RL | Faster to validate, more interpretable, directly answers placement question without training time | — Pending |
| Bayesian optimization for search loop | Reach-bubble pre-filter dramatically reduces candidate space; BO is sample-efficient for remaining candidates | — Pending |
| Block proxies for collision meshes | Real STEP files not yet available; proxies allow Phase 1 to proceed; API designed for easy swap | — Pending |
| Phase 0 first, no Genesis yet | 2D sanity check is fast and catches dimension/category errors before expensive 3D setup | — Pending |

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
*Last updated: 2026-04-12 after initialization*
