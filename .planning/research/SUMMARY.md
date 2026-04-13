# Project Research Summary

**Project:** Eden Cell Optimizer — PCR42 Heavy Steel Robot Placement
**Domain:** Industrial robot cell spatial search / static base placement via IK-reachability analysis
**Researched:** 2026-04-12
**Confidence:** HIGH

---

## Executive Summary

The Eden Cell Optimizer is a deterministic two-phase engineering analysis tool, not a learning system. Phase 0 is a pure Python pipeline that filters the AISC structural steel database to PCR42-compatible shapes, categorizes them into face-count groups, computes per-category Maximum Material Envelopes (MME), and produces matplotlib overlays for human review. Phase 1 is a Genesis physics simulation that uses those envelopes to prove or disprove static floor mounting of a FANUC M-20iD/12L by evaluating IK reachability, collision clearance, and J5 singularity avoidance across both work zones for every candidate base position. The two phases are decoupled by a single `phase0_results.json` file — Phase 1 does not import Phase 0 code. This architecture is correct and should not change.

The recommended technology stack requires adding only one new package to the Eden venv: `optuna>=3.6.0`. Everything else — Genesis 0.3.4, PyTorch, numpy (<2.0), scipy, matplotlib, pandas, pyyaml — is already installed. The spatial search should use Optuna's TPE sampler, not scikit-optimize (unmaintained since 2021, Python 3.12 compatibility unverified) and not BoTorch/Ax (GP overhead unjustified for a 3D search with ~1–5ms evaluation cost). Genesis's built-in IK is sufficient; no external IK library (ikpy, TracIK, KDL) is needed or wanted. The FANUC URDF comes from the `ros-industrial/fanuc` GitHub repo, cloned as a submodule into `eden/assets/fanuc/`.

The dominant risks are all Genesis API integration issues rather than algorithmic questions. Three of the five critical pitfalls can silently produce wrong results: `requires_jac_and_IK` defaulting to False causes a runtime crash after a costly `scene.build()`; Genesis IK never raises on convergence failure (must check `return_error=True` residuals manually); and URDF scale compounding can silently load the robot at millimeter scale. A fourth critical pitfall — the cost of `scene.build()` per candidate — means the architecture must build the scene once and use `robot.set_pos()` between candidates, or use Genesis's `n_envs` batch idiom. These four issues must be smoke-tested before the search loop is written.

---

## Key Findings

### Recommended Stack

The existing Eden venv already contains the entire stack. Only Optuna needs to be added (`pip install optuna>=3.6.0`; add to `eden/requirements.txt`). Genesis 0.3.4 is pinned and confirmed operational at 596 steps/sec on GPU. The `numpy<2.0` pin must not be changed. The FANUC URDF is not yet on-disk and must be acquired by cloning `ros-industrial/fanuc` as a git submodule.

**Core technologies:**

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| `genesis-world` | 0.3.4 (pinned) | Physics engine, IK solver, collision detection | Confirmed operational in Eden Docker; built-in IK validated in Phase 2 experiments |
| `optuna` | >=3.6.0 | Bayesian optimization (TPE) for [X,Y,Z] search | Minimal setup; TPE ideal for 3D continuous spaces; pure Python; no GP training overhead |
| `numpy` | <2.0 (pinned) | Jacobian finite-difference, MME math | Already present; Genesis may be incompatible with numpy 2.x — do not upgrade |
| `scipy` | any | Quaternion/Euler conversions for Genesis [w,x,y,z] convention | Already present; `Rotation.from_euler()` + explicit [x,y,z,w] → [w,x,y,z] conversion required |
| `ros-industrial/fanuc` URDF | git submodule | FANUC M-20iD/12L kinematics and mesh geometry | Official maintained URDF; expected joint names `joint_1`–`joint_6`, flange `tool0` (verify at clone time) |
| `matplotlib` | 3.10.8 | Phase 0 MME overlays + Phase 1 result heatmaps | Already installed and proven in this codebase |

**Resolved conflict — optimizer library:** Architecture agent recommended `scikit-optimize`; Stack agent confirmed it is unmaintained (last PyPI release 0.9.0, September 2021, Python 3.12 compatibility unverified). **Optuna>=3.6.0 is the authoritative recommendation.**

**Unresolved — Genesis `get_jacobian()` availability:** Architecture agent references `robot.get_jacobian(link)` at `rigid_entity.py:862`. Stack agent notes this is not documented in the bundled genesis-doc. Must be empirically verified in Phase 1 smoke test. Fallback: finite-difference Jacobian via Genesis IK perturbation (implementation pattern in STACK.md).

---

### Expected Features

**Must have (table stakes) — without these the tool cannot answer "where does the robot base go?":**

- AISC shape filter (<=300 lbs/ft, <=1100mm max dimension) + 3-face / 4-face / L-angle categorization
- Per-category MME bounding box computation (composite worst-case cross-section)
- 2D matplotlib overlay with MME bounds — Phase 0 review gate, blocks Phase 1 until signed off
- Reach-envelope pre-filter (analytic annular cylinder against WZ corners, not centroid — eliminates ~75% of candidates)
- 6-DOF IK check per candidate TCP pose with explicit convergence tolerance (return_error=True, 2mm / 0.57 deg)
- Collision check against environmental block proxies (conveyor, pinch unit, beam)
- J5 singularity rejection (±5 degree dead-band around J5=0)
- Dual work-zone evaluation: WZ1 (+1.5ft to +4.0ft) and WZ2 (-1.5ft to -3.0ft) independently assessed
- Valid position log sorted by Yoshikawa manipulability index w = sqrt(det(J @ J.T))
- Floor/riser mount constraint enforcement: Z_base in [0, 1000mm], pitch=0, roll=0 (hard search space bounds)

**Should have (differentiators):**

- Bayesian optimization (Optuna TPE) for next-point proposal within pre-filtered region
- Block proxy → STEP mesh swap API contract (CollisionBody factory with .from_box() / .from_step())
- Dual-zone pass/fail decomposition with transition annotation
- Manipulability-ranked output (mean w across all valid waypoints per candidate, sorted descending)

**Defer to post-Phase 1:**

- STEP collision mesh import (user will supply CAD; block proxies sufficient for finding valid placement regions)
- Real-time Genesis viewer (disable in search loop; keep show_viewer=True for debug only)
- TCP geometry / plasma torch STEP model (user supplies TCP offset as config parameter at Phase 1 start)
- BoTorch/Ax Gaussian process optimizer (TPE is sufficient; GP adds 50-200ms per iteration overhead)
- General-purpose multi-robot support (single FANUC M-20iD/12L only for this milestone)

---

### Architecture Approach

The pipeline is strictly two-phase with a file-based contract at the boundary (`phase0_results.json`). Phase 0 runs in either venv — bridge `engineering_tools/` via `sys.path`; do not install `mech_core` into Eden venv as it pulls PySide6. Phase 1 runs entirely in `Robot_Simulations/eden/.venv`. All Genesis calls are isolated to `scene_builder.py` and `evaluator.py`; all pure-geometry code (`tcp_path_generator.py`, `reach_prefilter.py`) has no Genesis dependency and can be unit-tested independently. The scene is built once; the robot base is repositioned via `robot.set_pos()` + `scene.reset()` between candidates — never `scene.rebuild()`.

**Major components:**

| Component | File | Genesis dep? | Responsibility |
|-----------|------|-------------|----------------|
| Phase 0 pipeline | `phase0_2d_mme/phase0_2d_mme.py` | No | AISC filter → categorize → MME → PNG + JSON |
| Scene builder | `phase1_3d_sim/scene_builder.py` | Yes | Build Genesis scene once; factory for mesh-swap |
| TCP path generator | `phase1_3d_sim/tcp_path_generator.py` | No | Ordered (pos, quat) waypoints per face/zone |
| Reach pre-filter | `phase1_3d_sim/reach_prefilter.py` | No | Analytic annular cylinder filter against WZ corners |
| Evaluator | `phase1_3d_sim/evaluator.py` | Yes | IK → collision → Jacobian → singularity per waypoint |
| Search loop | `phase1_3d_sim/search_loop.py` | No (calls evaluator) | Optuna TPE candidate proposal |
| Results logger | `phase1_3d_sim/results_logger.py` | No | CSV + JSON output, sorted by manipulability score |

**Phase 0 → Phase 1 data contract (4 categories, L-angle split into 2 orientations for unequal legs):**

```
phase0_results.json keys: 3face, 4face, Langle_long_near_datum, Langle_short_near_datum
Each entry: { mme_width_mm, mme_depth_mm, shape_count, shapes[] }
```

Phase 1 runs 4 independent search passes — one per shape category.

---

### Critical Pitfalls (ordered by severity)

1. **`requires_jac_and_IK` defaults to False — silent crash after scene.build()**
   Verified from Genesis source `options/morphs.py` line 86. Architecture agent's claim of True default is wrong; Pitfalls agent direct source inspection is authoritative. Always set `requires_jac_and_IK=True` explicitly. Add smoke test: call `robot.inverse_kinematics()` on one known-reachable point immediately after `scene.build()` before writing any search loop code.

2. **`scene.build()` costs 10–30 seconds — never rebuild per candidate**
   Genesis JIT-compiles Taichi kernels at build time. Build once at a neutral position; use `robot.set_pos([X, Y, Z])` + `scene.reset()` between candidates. If `set_pos` on a `fixed=True` URDF does not work after build, fall back to Genesis `n_envs` batch idiom. This architecture decision must be validated in Phase 1 Step 2 before the search loop is designed.

3. **Genesis IK never raises on convergence failure — silently accepts unreachable poses**
   `robot.inverse_kinematics()` always returns `qpos`. Always use `return_error=True` and check translational residual < 0.002m and rotational residual < 0.01 rad. Failure to do this logs "valid" candidates where the robot is 50mm short of the target.

4. **URDF scale compounding produces wrong-size robot**
   Genesis multiplies `morph.scale` by the URDF mesh `<scale>` tag value. ros-industrial repos are inconsistent on mm vs meters. Use `morph.scale=1.0` and verify: at home position, `robot.get_link("tool0").pos` Z-component should be ~0.911m. If it reads 0.000911 or 911.0, scale is wrong.

5. **AISC Pint quantities — raw `.magnitude` is in mm, not meters**
   `section.d > 1100` raises `DimensionalityError`. Always use `.to(target_unit).magnitude`. When building Genesis geometry: `section.d.to(ureg.meter).magnitude`. Raw `.magnitude` yields millimeters → 1000x scale error in Genesis scene.

**Additional moderate pitfalls (must handle in implementation):**

- Post-IK joint limit audit: `np.clip(qpos, lower_limits, upper_limits)` check; URDF limits may not match real FANUC controller hard limits
- Manipulability NaN near singularity: use `eigvalsh(J @ J.T)` with `np.maximum(eigenvalues, 0.0)` instead of `det`
- Quaternion convention: Genesis [w,x,y,z]; scipy returns [x,y,z,w] — add explicit conversion wrapper
- Foot-to-meter: define `FT = 0.3048` once at module level; never inline-convert in path generation
- Reach pre-filter against worst-case WZ corner, not centroid: worst case is WZ2 far edge + max beam depth
- L-angle dual orientation: two separate MME entries required in Phase 0 for unequal leg shapes

---

## Implications for Roadmap

Research implies a three-phase roadmap with a mandatory engineering review gate between Phase 0 and Phase 1.

### Phase 0 — 2D MME Sanity Check

**Rationale:** No Genesis dependency; fast to build; catches shape classification errors before GPU simulation time is spent. MME dimensions are required inputs for Phase 1 TCP path generation — Phase 1 cannot be specified until Phase 0 is complete and reviewed.
**Delivers:** `phase0_results.json` + per-category PNG overlays. Engineering sign-off gate.
**Addresses:** AISC filter, shape categorization, MME computation, 2D overlay (all table-stakes features)
**Avoids:** Pitfall C5 (Pint units), Pitfall m4 (L-angle dual orientation)
**Research flag:** Standard patterns — no phase research needed.

### Phase 1 — Scene Setup and Infrastructure Validation

**Rationale:** The four critical Genesis integration pitfalls must be caught empirically before the search loop is written. Building the scene, loading the URDF, and smoke-testing IK / `set_pos` / Jacobian are all independent of the search algorithm. Writing hundreds of lines of search logic before validating these integrations risks discovering a blocking issue too late.
**Delivers:** Validated `scene_builder.py`, FANUC URDF at correct scale, IK smoke test passing, `robot.set_pos()` repositioning confirmed (or `n_envs` fallback design decision made), `tcp_path_generator.py` unit-tested, `reach_prefilter.py` unit-tested
**Addresses:** Floor-mount constraint, work-zone TCP path generation, reach pre-filter, block proxy → STEP mesh swap API (design-only)
**Avoids:** Pitfall C1 (IK flag), C2 (URDF scale), C6 (scene rebuild cost), m1 (package:// path), m2 (fixed=True), m3 (quaternion convention), M4 (coordinate frame), M5 (unit inconsistency)
**Research flag:** Needs phase research. Verify: `robot.get_jacobian()` availability in 0.3.4; `robot.set_pos()` behavior on fixed=True URDF after build; ros-industrial FANUC joint names after cloning.

### Phase 2 — Search Loop and Results

**Rationale:** Depends entirely on Phase 1 infrastructure. The evaluator, Optuna study, and results logger are pure wiring once the scene builder and evaluator primitives work correctly.
**Delivers:** `evaluator.py`, `search_loop.py` (Optuna TPE stage 1 + optional dense grid stage 2), `results_logger.py`. Final output: CSV/JSON ranked by manipulability per shape category.
**Addresses:** 6-DOF IK check, collision check, J5 singularity rejection, dual-zone pass/fail, manipulability-ranked log, Bayesian optimization
**Avoids:** Pitfall C3 (IK convergence), C4 (joint limit), M1 (J5 singularity), M6 (manipulability NaN), M7 (reach pre-filter centroid error)
**Research flag:** Standard patterns. Optuna TPE API is stable and well-documented.

### Phase Ordering Rationale

- Phase 0 before Phase 1: MME dimensions are inputs to TCP path generation; also provides cheap human review gate.
- Phase 1 infrastructure before Phase 2 search: Four critical Genesis pitfalls require empirical validation from the installed genesis-world 0.3.4 before the search loop architecture is committed.
- Optuna BO deferred within Phase 2: Start with coarse grid scan. If runtime is acceptable (< 30 min), BO adds complexity without urgency. Add TPE if grid scan is slow. Infrastructure does not change.

### Research Flags

**Needs phase research:**
- Phase 1: `robot.get_jacobian()` availability and `robot.set_pos()` on fixed=True behavior — central architecture question for candidate repositioning strategy (set_pos vs n_envs batch)
- Phase 1: ros-industrial/fanuc URDF joint names and mesh scale after cloning

**Standard patterns (skip research):**
- Phase 0: AISC API + matplotlib — fully understood
- Phase 2: Optuna TPE integration — stable, well-documented API

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Genesis 0.3.4 confirmed operational in this repo; Optuna Python 3.12 compatibility confirmed; scikit-optimize elimination confirmed from PyPI metadata; all other packages proven in-place |
| Features | HIGH | Project specification is precise and unambiguous; Yoshikawa manipulability is established theory |
| Architecture | HIGH | Derived from direct Genesis 0.3.4 source inspection; two-phase file contract is the only viable decoupling given two-venv split |
| Pitfalls | HIGH | Genesis findings verified from installed source; classical robotics pitfalls are established theory |

**Overall confidence: HIGH**

### Conflicts Resolved

| Conflict | Resolution |
|----------|-----------|
| scikit-optimize vs optuna | Optuna>=3.6.0 — scikit-optimize unmaintained since 2021 (Stack agent authoritative) |
| `requires_jac_and_IK` default True vs False | Default is False — always set explicitly to True (Pitfalls agent verified from genesis/options/morphs.py line 86) |
| `robot.get_jacobian()` availability | Unresolved — verify empirically in Phase 1; FD Jacobian is documented fallback |

### Gaps to Address Before Phase 1 Starts

1. **TCP offset (x, y, z relative to J6 faceplate)** — user must supply before Phase 1. No default is safe; wrong offset invalidates all IK results. This is a blocking input.
2. **FANUC M-20iD/12L reach radius** — three agents gave three values (1813mm, 1831mm, 1868mm). Must confirm from official FANUC spec sheet before baking into the reach pre-filter.
3. **`robot.set_pos()` on fixed=True URDF after scene.build()** — if this does not work, the entire search loop architecture must switch to `n_envs` batch evaluation. Highest-risk architectural assumption.
4. **ros-industrial/fanuc joint names and URDF mesh scale** — enumerate after cloning; expected `joint_1`–`joint_6` and `tool0` but not confirmed.
5. **`robot.get_jacobian()` in Genesis 0.3.4** — if absent, use FD Jacobian (STACK.md pattern). Known fallback available.

---

## Sources

### Primary (HIGH confidence — direct source inspection)

- Genesis 0.3.4 installed source: `Robot_Simulations/eden/.venv/lib/python3.12/site-packages/genesis/` — IK API, Jacobian API, URDF loading, `requires_jac_and_IK` default (morphs.py line 86), convexification defaults
- `engineering_tools/mech_core/components/members/aisc.py` — Pint wrapping in `__getattr__`
- `Robot_Simulations/eden/experiments/phase2/urdf_import_validation.py` — Genesis URDF loading with `fixed=True` confirmed (TEST PASSED)
- EDEN_API_NOTES.md Section 4.6 — Genesis IK API confirmed, Genesis 0.3.4 version confirmed

### Secondary (MEDIUM confidence)

- `ros-industrial/fanuc` GitHub naming conventions — expected URDF package path and joint names (must verify at clone time)
- FANUC M-20iD/12L product spec (training data) — reach radius 1813–1868mm range across sources; confirm from official spec sheet
- Optuna PyPI release notes — Python 3.12 compatibility confirmed for 3.x series

### Established Theory (HIGH confidence)

- Yoshikawa, T. (1985). "Manipulability of Robotic Mechanisms." *International Journal of Robotics Research* — manipulability index w = sqrt(det(J @ J.T))
- J5 wrist singularity behavior for spherical-wrist 6-DOF arms (standard robotics)

---
*Research completed: 2026-04-12*
*Ready for roadmap: yes*
