# Architecture: Robot Placement Optimization Pipeline

**Domain:** Industrial robot cell — static base placement via IK/collision/singularity reachability analysis
**Researched:** 2026-04-12
**Overall confidence:** HIGH — derived from direct inspection of Genesis 0.3.4 source, existing Eden codebase, and project specification

---

## System Overview

The Eden Cell Optimizer is a two-phase deterministic pipeline. Phase 0 is a pure Python analysis that produces beam shape envelopes; Phase 1 is a Genesis simulation that uses those envelopes to prove or disprove static robot mounting viability. The two phases are coupled by a single file-based data contract, not by import or shared runtime.

---

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Phase 0 — 2D MME Sanity Check                                                │
│ engineering_tools venv (or Eden venv via sys.path bridge)                    │
│                                                                              │
│  ┌─────────────────────┐     ┌───────────────────────┐                       │
│  │   aisc_loader       │────▶│  shape_filter         │                       │
│  │   (aisc.py +        │     │  ≤300 lbs/ft           │                       │
│  │   aisc_shapes.json) │     │  ≤1100mm w/d           │                       │
│  └─────────────────────┘     └──────────┬────────────┘                       │
│                                         │                                    │
│                              ┌──────────▼────────────┐                       │
│                              │  shape_categorizer    │                       │
│                              │  3-face / 4-face / L  │                       │
│                              └──────────┬────────────┘                       │
│                                         │                                    │
│                              ┌──────────▼────────────┐                       │
│                              │  mme_calculator       │                       │
│                              │  composite bounding   │                       │
│                              │  box per category     │                       │
│                              └──────────┬────────────┘                       │
│                                         │                                    │
│                              ┌──────────▼────────────┐                       │
│                              │  matplotlib renderer  │                       │
│                              │  scaled 2D overlays   │                       │
│                              └──────────┬────────────┘                       │
│                                         │                                    │
└─────────────────────────────────────────┼────────────────────────────────────┘
                                          │
                          ┌───────────────▼──────────────┐
                          │  DATA CONTRACT (file-based)   │
                          │  phase0_results.json          │
                          │  {                            │
                          │    "3face": {                 │
                          │      "max_width_mm": ...,     │
                          │      "max_depth_mm": ...,     │
                          │      "shapes": [...]          │
                          │    },                         │
                          │    "4face": { ... },          │
                          │    "Langle": { ... }          │
                          │  }                            │
                          └───────────────┬──────────────┘
                                          │
┌─────────────────────────────────────────┼────────────────────────────────────┐
│ Phase 1 — 3D Genesis Simulation         │                                    │
│ Robot_Simulations/eden/.venv            │                                    │
│                                         ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  scene_builder.py                                                       │ │
│  │  Builds and holds the Genesis scene. Designed for mesh swap.            │ │
│  │                                                                         │ │
│  │  conveyor  ─── gs.morphs.Box proxies (rollers / gaps)                  │ │
│  │  pinch_unit ── gs.morphs.Box proxy                                      │ │
│  │  beam_proxy ── gs.morphs.Box at shape MME dimensions                   │ │
│  │  robot ──────── gs.morphs.URDF(file=..., fixed=True,                   │ │
│  │                                requires_jac_and_IK=True)               │ │
│  │                                                                         │ │
│  │  swap hook: replace Box morphs with gs.morphs.Mesh(file=".step")       │ │
│  └────────────────────────────┬────────────────────────────────────────────┘ │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────────┐ │
│  │  tcp_path_generator.py                                                  │ │
│  │  Builds ordered lists of (pos, quat) TCP waypoints for a given shape   │ │
│  │  and work zone.                                                         │ │
│  │                                                                         │ │
│  │  3-face shapes (W, S, M, HP, C, MC):                                   │ │
│  │    top_face_path()    — grid of points on top flange, normal = +Z       │ │
│  │    left_face_path()   — grid of points on left web face, normal = -Y    │ │
│  │    right_face_path()  — grid of points on right web face, normal = +Y   │ │
│  │                                                                         │ │
│  │  4-face shapes (HSS rect / sq / pipe):                                  │ │
│  │    top, left, right + bottom_face_path()                                │ │
│  │    bottom path: TCP approaches through inter-roller gap (Y offset)      │ │
│  │                                                                         │ │
│  │  L-angle: two orientations × 2 faces each                               │ │
│  │                                                                         │ │
│  │  Path density: ~25mm grid spacing is sufficient for reachability;      │ │
│  │  not path planning — just presence/absence of IK solution at each pt   │ │
│  └────────────────────────────┬────────────────────────────────────────────┘ │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────────┐ │
│  │  reach_prefilter.py                                                     │ │
│  │  Trims the 3D search volume before any Genesis evaluation.              │ │
│  │                                                                         │ │
│  │  FANUC M-20iD/12L reach radius: 1813mm (from spec sheet)               │ │
│  │  Robot base search volume: X ∈ [-2500, 2500], Y ∈ [-2500, 2500],      │ │
│  │                            Z ∈ [0, 1000] mm                             │ │
│  │                                                                         │ │
│  │  For each candidate (X, Y, Z):                                          │ │
│  │    Farthest TCP target = max(dist(base_xy, farthest WZ corner))         │ │
│  │    Nearest TCP target  = min(dist(base_xy, nearest WZ corner))          │ │
│  │    Accept if: nearest < reach AND farthest < reach                      │ │
│  │    (Both zones must be coverable by reach bubble before entering sim)   │ │
│  │                                                                         │ │
│  │  Reduction expected: ~70-80% of naive grid eliminated                   │ │
│  └────────────────────────────┬────────────────────────────────────────────┘ │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────────┐ │
│  │  search_loop.py                                                         │ │
│  │  Orchestrates the evaluation of candidate base positions.               │ │
│  │                                                                         │ │
│  │  Input: pre-filtered candidate grid (from reach_prefilter)              │ │
│  │  Algorithm: Bayesian Optimization (scikit-optimize or scipy minimize)   │ │
│  │  see Search Loop Architecture section below                             │ │
│  │                                                                         │ │
│  │  For each proposed [X, Y, Z]:                                           │ │
│  │    1. Reposition robot base in Genesis scene (set_pos on robot entity) │ │
│  │    2. Run evaluator.evaluate(candidate) → (pass/fail, score)           │ │
│  │    3. If pass: append to results_log with score                         │ │
│  │    4. Feed result back to BO acquisition function                       │ │
│  └────────────────────────────┬────────────────────────────────────────────┘ │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────────┐ │
│  │  evaluator.py                                                           │ │
│  │  Core per-candidate evaluation. All Genesis API calls live here.        │ │
│  │                                                                         │ │
│  │  For each TCP waypoint in WZ1 path (then WZ2 path):                    │ │
│  │    qpos, err = robot.inverse_kinematics(                                │ │
│  │        link=ee_link,                                                    │ │
│  │        pos=waypoint_pos,                                                │ │
│  │        quat=waypoint_quat,                                              │ │
│  │        return_error=True                                                │ │
│  │    )                                                                    │ │
│  │    if err[:3] > pos_tol → IK_FAIL                                       │ │
│  │    robot.set_qpos(qpos)                                                 │ │
│  │    scene.step()    ← runs collision detection                           │ │
│  │    contacts = robot.get_contacts(with_entity=pinch_unit)               │ │
│  │    if contacts > 0 → COLLISION_FAIL                                     │ │
│  │    J = robot.get_jacobian(link=ee_link)   ← shape (6, n_dofs)          │ │
│  │    w = sqrt(det(J @ J.T))                  ← Yoshikawa manipulability   │ │
│  │    if w < singularity_threshold → SINGULARITY_WARN (not hard fail)     │ │
│  │                                                                         │ │
│  │  score = mean(w across all valid waypoints) — higher is better         │ │
│  └────────────────────────────┬────────────────────────────────────────────┘ │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────────┐ │
│  │  results_logger.py                                                      │ │
│  │  Appends to a CSV/JSON log every time a valid pose is found.            │ │
│  │  Columns: X, Y, Z, score, wz1_pass_rate, wz2_pass_rate, timestamp      │ │
│  │  Final output sorted by score (descending).                             │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
aisc_shapes.json
      │
      ▼
[Phase 0] filter → categorize → MME compute → PNG exports
                                     │
                           phase0_results.json
                                     │
                                     ▼
[Phase 1] scene_builder builds Genesis scene (once, not per candidate)
                                     │
                           tcp_path_generator produces waypoint lists
                           (once per shape category, reused across candidates)
                                     │
                           reach_prefilter eliminates ~75% of candidates
                                     │
                           search_loop feeds [X,Y,Z] candidates to evaluator
                                     │
                           evaluator runs IK → collision → Jacobian per waypoint
                                     │
                           results_logger appends each passing candidate
                                     │
                           Final sorted results table (CSV + JSON)
```

---

## Phase 0 → Phase 1 Integration Contract

Phase 0 writes a single JSON file. Phase 1 reads it at startup. There is no import dependency — this allows Phase 0 to run in either venv.

**Recommended schema for `phase0_results.json`:**

```json
{
  "generated": "2026-04-12T...",
  "constraints": {
    "max_weight_lbs_per_ft": 300,
    "max_dimension_mm": 1100
  },
  "categories": {
    "3face": {
      "mme_width_mm": 410.0,
      "mme_depth_mm": 530.0,
      "shape_count": 147,
      "shapes": ["W44X335", "W40X431", "..."]
    },
    "4face": {
      "mme_width_mm": 305.0,
      "mme_depth_mm": 305.0,
      "shape_count": 62,
      "shapes": ["HSS16X16X5/8", "..."]
    },
    "Langle_long_near_datum": {
      "mme_width_mm": 203.0,
      "mme_depth_mm": 152.0,
      "shape_count": 18,
      "shapes": ["L8X6X1", "..."]
    },
    "Langle_short_near_datum": {
      "mme_width_mm": 152.0,
      "mme_depth_mm": 203.0,
      "shape_count": 18,
      "shapes": ["L8X6X1", "..."]
    }
  }
}
```

Phase 1 iterates over `categories`, builds one beam proxy per category (at MME dimensions), and runs the full search loop for each. This means 4 search passes total for the standard set of categories.

**Import bridging for Phase 0:** The simplest approach is to add `engineering_tools/` to `sys.path` at the top of `phase0_2d_mme.py` when running inside the Eden venv, or copy `aisc_shapes.json` + `aisc.py` into a local `lib/` folder under the experiment. Do not install `mech_core` as a package into the Eden venv — it pulls in PySide6 and other GUI dependencies.

---

## Scene Builder Architecture — Mesh Swap Design

The scene builder must be structured so block proxies can be replaced with STEP meshes without changing evaluation code. The correct pattern is a factory function that accepts a `mesh_config` dict:

```python
# scene_builder.py

PROXY_MODE = "box"      # for Phase 1 initial runs
MESH_MODE  = "step"     # for later CAD-accurate runs

def build_scene(mesh_config: dict, robot_base_pos=(0, 0, 0)) -> dict:
    """
    Returns handles to all named entities so evaluator can reference them.
    mesh_config keys: conveyor, pinch_unit, beam_3face, beam_4face
    mesh_config values: either {"mode": "box", "size": [...]} 
                        or     {"mode": "step", "file": "path/to/mesh.step"}
    """
    scene = gs.Scene(...)

    conveyor = _add_entity(scene, mesh_config["conveyor"], ...)
    pinch_unit = _add_entity(scene, mesh_config["pinch_unit"], ...)
    beam = _add_entity(scene, mesh_config["beam"], ...)

    robot = scene.add_entity(
        gs.morphs.URDF(
            file=robot_urdf_path,
            pos=robot_base_pos,
            fixed=True,
            requires_jac_and_IK=True,   # default True for URDF — confirmed
        )
    )

    scene.build()

    return {
        "scene": scene,
        "robot": robot,
        "conveyor": conveyor,
        "pinch_unit": pinch_unit,
        "beam": beam,
        "ee_link": robot.get_link("J6"),
    }
```

**Critical constraint:** `scene.build()` is called once. Genesis JIT-compiles the scene at build time. The robot base position cannot be changed by rebuilding — it must be set via `robot.set_pos()` or by rebuilding the scene. Rebuilding per candidate is too expensive. Use `robot.set_pos()` to reposition between candidates, then call `scene.reset()` to flush contact state.

**STEP mesh swap:** When real meshes arrive, only `mesh_config` values change. The evaluator, search loop, and results logger are untouched. This is the sole purpose of the factory pattern.

---

## TCP Path Generation Architecture

TCP path generation is the translation of geometry (face + work zone bounds) into a list of `(pos_world, quat_world)` tuples the IK solver can consume.

**Design rule:** Path generation is pure Python / NumPy. No Genesis calls. Generate all paths before the search loop starts, since they are the same for every candidate base position.

```
WorkZone = namedtuple("WorkZone", ["start_m", "end_m"])  # meters, from datum
WZ1 = WorkZone(start_m=+0.457, end_m=+1.219)   # +1.5ft to +4.0ft
WZ2 = WorkZone(start_m=-0.457, end_m=-0.914)   # -1.5ft to -3.0ft
```

**Face normal convention (robot approaches from outside):**

| Face | Normal direction | TCP Z-axis (approach) |
|------|-----------------|----------------------|
| Top | +Z | -Z (approach from above) |
| Left web | -Y | +Y |
| Right web | +Y | -Y |
| Bottom | -Z | +Z (approach from below, through roller gap) |

**Grid density recommendation:** 50mm along the length axis (beam axis), 30mm across the face width. This gives ~300-600 points per face per work zone depending on shape. Each IK call takes ~5ms in Genesis; 2000 waypoints per candidate = ~10 seconds per candidate on GPU. The reach prefilter reduces candidates to ~200-500 from a naive 10,000-point grid, giving a total search budget of roughly 30-90 minutes.

**WZ2 path offset logic:** WZ2 evaluates the robot approaching from the opposite side of the pinch unit. The TCP paths for WZ2 are geometrically identical to WZ1 paths but Z-mirrored in the longitudinal (X) axis around the datum. The transition between WZ1 and WZ2 (the 3ft dead zone) is not evaluated — this is correct per specification, since the assumption is the robot moves to a home position and re-approaches WZ2 on a wider arc.

---

## Search Loop Architecture

**Recommendation: Bayesian Optimization over the reach-prefiltered region.**

The rationale and implementation specifics:

### Why not pure grid scan
A 25mm grid over X ∈ [-2500, 2500], Y ∈ [-2500, 2500], Z ∈ [0, 1000] produces ~800,000 candidates before prefilter. Even after ~75% prefilter reduction, ~200,000 remain. At 10 seconds per evaluation this is infeasible. Grid scan is only appropriate for the final fine-grained sweep around a known good region found by BO.

### Why not random sampling
Random sampling has no convergence guarantee. It is useful as a fallback if BO libraries are unavailable but should not be the primary strategy.

### Recommended: Two-stage approach

**Stage 1 — Bayesian Optimization over coarse grid (50mm step)**
Use `scipy.optimize.differential_evolution` or `scikit-optimize.gp_minimize` to propose next candidate based on acquisition function. Target: ~200 evaluations to find the best region.

```
from skopt import gp_minimize
from skopt.space import Real

space = [
    Real(x_min, x_max, name='X'),
    Real(y_min, y_max, name='Y'),
    Real(0.0, 1000.0, name='Z'),
]

result = gp_minimize(
    func=evaluator_objective,   # returns -score (minimize negative = maximize score)
    dimensions=space,
    n_calls=200,
    n_initial_points=20,        # random exploration before GP fits
    acq_func='EI',              # Expected Improvement
    noise=0.01,
)
```

`evaluator_objective` must return a scalar: return `-score` if reachable, return `+10.0` (high penalty) if any failure condition triggered.

**Stage 2 — Dense grid scan around BO optimum**
Once Stage 1 identifies the best [X, Y] neighborhood (±100mm window), run a 10mm-step grid scan over that window at all Z heights. This finds the true discrete optimum within the continuous BO approximation.

**`scikit-optimize` availability:** Must be installed in the Eden venv. Add `scikit-optimize>=0.9.0` to `Robot_Simulations/eden/requirements.txt`. If import fails, fall back to a pure random search with 500 samples as a degraded mode.

---

## Manipulability Index Computation

The Yoshikawa manipulability measure is the standard metric for 6-DOF robots. It quantifies how far the robot configuration is from a singularity.

**Definition:**
```
w(q) = sqrt( det( J(q) @ J(q).T ) )
```

Where `J(q)` is the 6×n spatial Jacobian at joint configuration q.

- `w = 0`: robot is exactly at a singularity (J is rank-deficient)
- `w > threshold`: robot has sufficient dexterity to move in all 6 DOF

**Genesis API for this:**
```python
# After robot.set_qpos(qpos) and scene.step():
J = robot.get_jacobian(link=ee_link)  # shape: (6, 6) for 6-DOF robot
import torch
w = torch.sqrt(torch.det(J @ J.T)).item()
```

**Important:** `get_jacobian` requires `morph.requires_jac_and_IK=True` at scene build time. For `gs.morphs.URDF`, this defaults to `True` — confirmed from Genesis 0.3.4 source (`options/morphs.py` line 897). No extra flag needed when loading via URDF.

**Singularity threshold:** For the FANUC M-20iD/12L, a practical threshold is `w < 0.001`. Configurations near J5 = 0 (wrist singularity) or near full arm extension (elbow singularity) will produce `w` near zero. Log these as warnings, not hard failures — the manipulability score captures them numerically in the ranking.

**Use in scoring:** The final score for a candidate pose is the mean of `w` across all valid (IK-passing, collision-free) waypoints. Poses with higher mean `w` are preferred because the robot retains more dexterity throughout the full sweep.

---

## Dual Work Zone (WZ1 + WZ2) Evaluation

Both work zones must pass for a candidate position to be valid. The recommended evaluation order and failure semantics:

```
evaluate_candidate(X, Y, Z):
    1. Reposition robot base
    2. Run WZ1 path evaluation
       - If any IK failure: return FAIL_WZ1_IK
       - If any collision: return FAIL_WZ1_COLLISION
       - Collect w values for all valid points
    3. Run WZ2 path evaluation (separate from WZ1 — no transition penalty)
       - If any IK failure: return FAIL_WZ2_IK
       - If any collision: return FAIL_WZ2_COLLISION
       - Collect w values
    4. score = mean(w_WZ1 + w_WZ2)
    5. return PASS, score
```

**WZ2 physical model:** WZ2 is behind the pinch unit (negative X from datum). The beam extends through the pinch unit; the robot approaches from the same side. The pinch_unit entity is static. Collision checks between the robot arm and the pinch_unit entity are the critical check for WZ2. The beam proxy for WZ2 is at the same Y,Z as WZ1 (same beam cross-section), just at a different X range.

**WZ2 outer bound derivation (from spec):**
```
WZ1: +1.5ft to +4.0ft  →  +457mm to +1219mm
WZ2 near bound: -1.5ft →  -457mm (third offset)
Dead zone: 3.0ft       →  914mm
WZ2 far bound: -(1.5 + 3.0)ft = -4.5ft → -1372mm
```

---

## Suggested Build Order

### Step 1 — Phase 0 Script
**File:** `experiments/Beam_Coping_Machine/phase0_2d_mme/phase0_2d_mme.py`

Build and validate before touching Genesis:
1. Import `aisc.py` via `sys.path` bridge or local copy
2. Filter shapes to PCR42 constraints
3. Categorize into 3-face / 4-face / L-angle groups
4. Compute MME per category
5. Render `matplotlib` scaled overlays, export PNGs
6. Write `phase0_results.json`

Engineering review of PNGs and JSON before proceeding.

### Step 2 — Scene Builder (no search yet)
**File:** `experiments/Beam_Coping_Machine/phase1_3d_sim/scene_builder.py`

Build the scene factory and verify in viewer:
1. Conveyor box proxies with roller gap modeled
2. Pinch unit box proxy at correct datum position
3. FANUC URDF loaded with `fixed=True`, `requires_jac_and_IK=True`
4. Beam proxy at 3-face MME dimensions for visual check
5. Verify IK returns a solution for a known reachable TCP point
6. Verify `get_jacobian` returns a non-singular matrix at that point

### Step 3 — TCP Path Generator
**File:** `experiments/Beam_Coping_Machine/phase1_3d_sim/tcp_path_generator.py`

Pure NumPy, no Genesis dependency. Write and unit-test independently:
1. `generate_3face_paths(mme, wz1, wz2)` → `{wz: {face: [(pos, quat)]}}` 
2. `generate_4face_paths(mme, wz1, wz2)` → same structure
3. Visualize one path in matplotlib (top view) to confirm geometry

### Step 4 — Reach Prefilter
**File:** `experiments/Beam_Coping_Machine/phase1_3d_sim/reach_prefilter.py`

Pure NumPy, no Genesis dependency:
1. Load FANUC reach radius (1813mm from spec)
2. Generate coarse candidate grid
3. Filter by reach bubble against WZ1 and WZ2 corners
4. Print reduction statistics

### Step 5 — Evaluator
**File:** `experiments/Beam_Coping_Machine/phase1_3d_sim/evaluator.py`

First Genesis-heavy component:
1. Accepts a candidate position and paths as input
2. Runs IK, collision, Jacobian checks per waypoint
3. Returns structured result dict, not raw Genesis objects
4. Test on 3-5 manually chosen known-good and known-bad positions

### Step 6 — Search Loop + Results Logger
**Files:** `search_loop.py`, `results_logger.py`

Wire BO acquisition to evaluator:
1. Install `scikit-optimize` in Eden venv
2. Implement BO Stage 1 (coarse)
3. Implement dense grid Stage 2 around BO result
4. Log all candidates and results to `results/run_YYYYMMDD_HHMMSS.json`
5. Print final sorted table

---

## Key Genesis API Facts (confirmed from v0.3.4 source)

| API | Location | Notes |
|-----|----------|-------|
| `robot.inverse_kinematics(link, pos, quat, return_error=True)` | `rigid_entity.py:1063` | Returns `(qpos, error_pose)`. error_pose[:3] = pos error in meters. |
| `robot.get_jacobian(link)` | `rigid_entity.py:862` | Returns tensor shape `(6, n_dofs)`. Requires `requires_jac_and_IK=True`. |
| `robot.get_contacts(with_entity=...)` | `rigid_entity.py:2564` | Returns dict with `valid_mask`. Check `valid_mask.any()` for collision. |
| `gs.morphs.URDF(requires_jac_and_IK=True)` | `options/morphs.py:897` | Default is `True` — IK enabled automatically for URDF loads. |
| `gs.morphs.URDF(fixed=True)` | `options/morphs.py:814` | Required for fixed-base robots. |
| Manipulability | computed from Jacobian | `w = sqrt(det(J @ J.T))`. No native Genesis method — compute in PyTorch. |

---

## Component Boundaries

| Component | Responsibility | Has Genesis Dependency | Inputs | Outputs |
|-----------|---------------|----------------------|--------|---------|
| `phase0_2d_mme.py` | Shape filtering, MME compute, PNG export | No | `aisc_shapes.json` | PNGs, `phase0_results.json` |
| `scene_builder.py` | Genesis scene construction, entity handles | Yes | mesh_config dict | scene + entity handle dict |
| `tcp_path_generator.py` | Waypoint geometry computation | No | MME dims, WZ bounds | `{zone: {face: [(pos,quat)]}}` |
| `reach_prefilter.py` | Geometric pre-filtering of candidate grid | No | WZ corners, reach radius | filtered candidate list |
| `evaluator.py` | Per-candidate IK/collision/Jacobian evaluation | Yes | scene handles, candidate pos, paths | result dict `{pass, score, w_mean}` |
| `search_loop.py` | BO-driven candidate proposal | No (calls evaluator) | prefiltered candidates | candidate stream |
| `results_logger.py` | Log append + final sort | No | result dicts | CSV + JSON output |

---

## Pitfall: Scene Rebuild Cost

Genesis compiles Taichi kernels on `scene.build()`. A full rebuild takes 30-60 seconds on GPU. Do not rebuild the scene per candidate. Instead:

1. Build once with robot at a nominal position
2. Between candidates: `robot.set_pos([X, Y, Z])` then `scene.reset()` to flush physics state
3. Verify that `set_pos` on a `fixed=True` URDF correctly translates the base — test this in Step 2 before the search loop exists

If `set_pos` on a fixed-base entity does not work as expected in Genesis 0.3.4, the fallback is to keep a list of ~10 scene instances pre-built at positions covering the search space, and map each candidate to the nearest pre-built scene. This is a known complexity risk — confirm in Step 2.

---

## Sources

- Genesis 0.3.4 source code: `/mnt/intelligence/GitHub_Projects/MechanicalDesignTools/Robot_Simulations/eden/.venv/lib/python3.12/site-packages/genesis/`
  - `engine/entities/rigid_entity/rigid_entity.py` — IK, Jacobian, contact APIs (confirmed line numbers above)
  - `options/morphs.py` — URDF morph defaults including `requires_jac_and_IK=True`
- Project specification: `Robot_Simulations/Optimizing_Robot_Placement.md`
- Eden project document: `.planning/PROJECT.md`
- Eden folder structure: `Robot_Simulations/eden/docs/FOLDER_STRUCTURE.md`
- Existing Eden experiments: `experiments/phase2/scene_builder_demo.py`, `experiments/phase2/urdf_import_validation.py`
- Existing DES Fanuc config: `engineering_tools/simulation/DES/core/machines/subsystems/robots/configs/fanuc.json`
- Yoshikawa manipulability measure: T. Yoshikawa, "Manipulability of Robotic Mechanisms," The International Journal of Robotics Research, 1985 — standard formulation, not web-sourced
