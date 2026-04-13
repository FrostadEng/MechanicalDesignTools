# Feature Landscape: Robot Cell Placement Optimizer

**Domain:** Robot reachability analysis / static base placement optimization for industrial work cells
**Project:** Eden Cell Optimizer — PCR42 Heavy Steel Robot Placement
**Researched:** 2026-04-12
**Confidence:** HIGH (project spec is precise and unambiguous; domain is well-understood from robotics literature)

---

## Table Stakes

Features the tool must have to produce a usable engineering answer. Missing any of these = tool cannot answer "where does the robot base go?"

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AISC shape filter + categorization | Without knowing which shapes the cell can process, there is no defined TCP path set to validate against | Low | Filter by weight (≤300 lbs/ft) and width/depth (≤1100mm); categorize into 3-face, 4-face, L-angle (two orientations) |
| Per-category bounding box (MME) computation | The composite "No-Go" zone is the collision envelope the robot must never enter; without it every candidate position is undefined | Low | Max X × Max Y across all shapes in each category; applied to conveyor datum |
| 2D matplotlib overlay with MME bounds | Engineering review step — proves the shape categorization is correct before 3D setup; catches dimension/category errors cheaply | Low | Export PNG per category; draw conveyor line (Y=0), datum roller (X=0), all cross-sections, MME box overlay |
| Reach-envelope pre-filter | Eliminates all [X,Y,Z] candidates geometrically outside the robot's max reach sphere before any Genesis call; without this the search loop calls Genesis for positions that are trivially unreachable | Medium | FANUC M-20iD/12L: 1831mm max reach; filter to annular cylinder (R_min..R_max) relative to each target zone centroid; Z bounded 0–1000mm |
| 6-DOF IK check per candidate pose | Core acceptance criterion — if IK cannot be resolved the robot physically cannot achieve the TCP pose | High | Must use robot's joint limits from URDF; Genesis IK solver or analytical fallback; check all required TCP poses, not just a single point |
| Collision check against environmental proxies | Accepting a pose that causes arm-to-pinch-unit or arm-to-conveyor collision is a hard failure | High | Block proxies sufficient for Phase 1; API must allow drop-in swap to STEP meshes later without restructuring |
| J5 singularity rejection | Passing through a J5 (wrist) singularity in the FANUC architecture causes uncontrolled joint velocity spikes — a hard safety rejection criterion | Medium | Detect when J5 angle approaches 0°; configurable dead-band threshold; reject path not just the pose |
| Work-zone-aware TCP path generation | The robot must cover both WZ1 (+1.5ft to +4.0ft) and WZ2 (-1.5ft to -3.0ft) face sweeps; failing WZ2 for a given base position is a valid partial failure, not a full failure | Medium | Path defined normal to each face of beam; dense point grid across face area in each zone; WZ1 and WZ2 evaluated independently with transition handled by robot repositioning |
| Valid position log sorted by manipulability index | The output of the tool — a ranked list engineers can directly read off to make a placement decision | Low | Log [X, Y, Z], manipulability score w = sqrt(det(J * J^T)), zone pass/fail per valid position; export to CSV or JSON |
| Floor-mount and riser-mount constraint enforcement | Z_base bounded 0–1000mm; pitch/roll strictly 0; any candidate violating this is structurally non-buildable | Low | Hard constraint on search space definition, not a check inside Genesis |

---

## Differentiators

What makes this tool better than a human engineer eyeballing a layout drawing. These are what justify building the tool at all.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Reach-bubble pre-filter dramatically shrinks Genesis call count | A naive grid search over a 2m × 2m × 1m space at 50mm resolution = ~16,000 candidates; after annular pre-filter, typically 200–800 survive; this is a 20–80x speedup with no loss of correctness | Medium | Compute analytically from robot DH parameters before any simulation setup |
| Bayesian optimization (BO) for next-point proposal | Rather than exhaustive grid search of the pre-filtered region, BO uses previous IK/collision results as a Gaussian process prior to propose the most informative next candidate; converges to valid region in far fewer evaluations than grid or random search | High | Use scipy or scikit-optimize (both available in venv or trivially pip-installable); acquisition function = Expected Improvement; falls back to grid if BO overhead exceeds savings for small search spaces |
| Per-shape category coverage rather than single shape | Validating against the composite MME (worst-case shape) means the placement proof covers all compatible shapes, not just the specific beam on the shop floor today — the result is a cell specification, not a one-time answer | Medium | Already baked into the Phase 0 → Phase 1 data flow |
| Dual-zone pass/fail decomposition with transition annotation | Most tools check a single workspace; this tool distinguishes WZ1 pass, WZ2 pass, WZ1+WZ2 pass, and flags whether the WZ1-to-WZ2 transition path is collision-free — a robot integrator cannot determine this from a spec sheet | Medium | Log zone results separately; annotate positions where transition collision was the only failure |
| Manipulability-ranked output | Any valid position is buildable; a high-manipulability position is durable — it means the robot has good kinematic conditioning throughout the sweep, so small deviations in workpiece position don't cause IK failures in production | Low | Compute w = sqrt(det(J * J^T)) at each valid pose and aggregate (e.g., minimum across all TCP path points); sort descending |
| Human-reviewable 2D sanity check before 3D | Phase 0 produces artifacts an engineer can read without robotics expertise; this creates a review gate that catches shape classification errors before GPU simulation time is spent | Low | PNGs with clear labels, datum lines, and dimension annotations |
| Block proxy → STEP mesh swap API contract | Designing the collision mesh interface so real CAD can slot in later without code restructuring is a differentiator over a quick-and-dirty script — it preserves the investment as the cell design matures | Low | Define a `CollisionBody` abstraction with `.from_box()` and `.from_step()` constructors used everywhere Genesis entities are built |

---

## Anti-Features

Things that would bloat scope without adding value to the stated question ("where should the robot base go?").

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Trajectory smoothness / motion quality optimization | The acceptance criterion is IK-reachable + collision-free; smooth motion is a post-placement concern for the robot programmer, not the cell designer | Accept any collision-free IK solution; do not add jerk or velocity-continuity checks |
| RL / reward-function training | Training a policy requires 10k–100k episodes and produces a non-interpretable result; the question being answered is deterministic and narrow | Deterministic IK + collision + singularity checks produce an auditable, explainable answer |
| Real-time simulation visualization / interactive viewer | Genesis viewer adds GPU overhead and is not needed for a batch search loop; it complicates headless Docker execution | Disable viewer in search loop; keep show_viewer=True only in debug/validation runs |
| Multi-robot configuration analysis | One FANUC M-20iD/12L is the design constraint; multi-robot is a different cell architecture question | Hard-code single robot; do not parameterize for N robots |
| Path planning (avoiding obstacles en-route) | The tool checks whether every required TCP pose is reachable without collision; it does not need to find a continuous motion path connecting them | Check each TCP pose independently; transition path is only checked at a coarse level to confirm it's not the sole failure mode |
| Full production scheduling / cycle time | That is the PCR41/PCR42 DES scope; this tool answers geometry, not throughput | Output is placement geometry only; no takt time, throughput, or OEE metrics |
| STEP mesh import in Phase 1 | User will provide CAD files later; block proxies are sufficient to find valid placement regions | Design the abstraction for easy swap; execute Phase 1 with proxies |
| TCP geometry / plasma torch STEP model | User supplies TCP offset (x,y,z) at Phase 1 start; tool applies it as a rigid offset from J6 faceplate | Accept TCP offset as a config parameter; do not build torch mesh import |
| Web UI / visualization dashboard | This is a scriptable engineering analysis tool, not a product; PNGs and CSV/JSON outputs are sufficient for engineering review | matplotlib PNGs for Phase 0; JSON/CSV for Phase 1 results |
| General-purpose robot support (arbitrary URDF) | Designing for arbitrary robots adds abstraction overhead; FANUC M-20iD/12L is fixed for this milestone | Hard-code DH parameters and joint limits for M-20iD/12L; document where to replace for a future robot swap |

---

## Feature Dependencies

```
Phase 0 (must complete before Phase 1):
  AISC shape filter
      → per-category bounding box (MME)
          → 2D matplotlib overlay  [Phase 0 deliverable, review gate]
          → Work-zone TCP path generation (uses MME as collision envelope)

Phase 1 (depends on Phase 0 sign-off):
  Robot reach-envelope pre-filter
      → Bayesian optimization / grid search (operates on pre-filtered space)
          → Genesis IK check (per candidate)
              → Collision check (per candidate)
                  → J5 singularity rejection (per candidate)
                      → Manipulability score (only for passing candidates)
                          → Sorted valid position log  [Phase 1 deliverable]
```

Reach pre-filter MUST precede Genesis to avoid trivial wasted evaluations.
Work-zone path generation MUST precede the search loop (paths are fixed; base position varies).
Phase 0 sign-off MUST precede Phase 1 execution (MME dimensions drive TCP path extent).

---

## MVP Recommendation

Prioritize in this order:

1. **AISC filter + categorization + MME bounding box** — defines the problem space
2. **2D matplotlib overlay** — Phase 0 review gate; blocks Phase 1 until signed off
3. **Reach-envelope pre-filter** — highest-leverage single feature; makes Phase 1 tractable
4. **Genesis IK + collision + J5 check** — core correctness
5. **Manipulability-sorted log** — turns a pass/fail result into an actionable ranked output

Defer:
- **Bayesian optimization**: Start with a grid search over the pre-filtered region. If runtime is acceptable (< ~30 min for a full search), BO adds complexity without urgency. Add BO as an upgrade if grid search is slow.
- **Block → STEP swap abstraction**: Design the interface clean from day one, but do not implement `.from_step()` until user delivers CAD files.

---

## Sources

- Project specification: `/mnt/intelligence/GitHub_Projects/MechanicalDesignTools/Robot_Simulations/Optimizing_Robot_Placement.md`
- Project governance: `/mnt/intelligence/GitHub_Projects/MechanicalDesignTools/.planning/PROJECT.md`
- Existing kinematic utilities: `engineering_tools/mech_core/analysis/kinematics/kinematics.py` (confirms no 6-DOF IK or manipulability exists yet; must be built)
- FANUC M-20iD/12L spec (training data, HIGH confidence): 6-axis vertical articulated; max reach 1831mm; 12kg payload; standard wrist (J4/J5/J6); J5 singularity at 0° is a known FANUC constraint
- Genesis physics engine (training data, MEDIUM confidence): batch IK solver available via `robot.set_dofs_position` + forward kinematics; collision detection via `scene.step()` + contact query; headless operation confirmed by existing Docker setup
- Manipulability index: Yoshikawa, T. (1985) "Manipulability of robotic mechanisms" — sqrt(det(J * J^T)) is standard, well-established in robotics literature (HIGH confidence)
- Bayesian optimization for robot placement: standard in robotics optimization literature; scikit-optimize and scipy both available in the eden venv (MEDIUM confidence — venv contents not fully audited)
