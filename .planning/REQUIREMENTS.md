# Requirements: Eden Cell Optimizer — PCR42 Heavy Steel Robot Placement

**Defined:** 2026-04-13
**Core Value:** Prove static robot mounting achieves 100% reachability for PCR42 structural steel processing, eliminating 1-axis positioners.

---

## v1 Requirements

### Phase 0 — AISC Filter and Shape Classification

- [ ] **AISC-01**: Pipeline loads and queries `aisc_shapes.json` via `aisc.py` SectionProperties API
- [ ] **AISC-02**: Filters all AISC shapes to PCR42 constraints: weight ≤ 300 lbs/ft and max cross-sectional dimension ≤ 1100mm
- [ ] **AISC-03**: Classifies valid shapes into categories: 3-face (W, S, M, HP, C, MC), 4-face (HSS rect/sq/pipe), L-angle-A (long leg near datum), L-angle-B (short leg near datum)
- [ ] **AISC-04**: L-angle shapes with unequal legs are tested in both orientations and produce two separate MME entries
- [ ] **AISC-05**: All AISC dimensional values converted from Pint `ureg.mm` quantities to raw floats before any geometric computation

### Phase 0 — Maximum Material Envelope (MME)

- [ ] **MME-01**: Computes composite worst-case bounding box (max width × max depth) per shape category
- [ ] **MME-02**: Generates scaled 2D matplotlib overlay per category showing all valid cross-section profiles superimposed
- [ ] **MME-03**: Each overlay includes: Y=0 conveyor line, X=0 datum roller line, all valid cross-sections, and the composite MME bounding box
- [ ] **MME-04**: Exports one PNG per category to `eden/experiments/Beam_Coping_Machine/phase0_2d_mme/`
- [ ] **MME-05**: Exports `phase0_results.json` to `phase0_2d_mme/` with schema: `{category: {mme_width_mm, mme_depth_mm, shape_count, shapes[]}}`

### Phase 1 — Genesis Environment and FANUC URDF

- [ ] **ENV-01**: `ros-industrial/fanuc` repository cloned as git submodule into `eden/assets/fanuc/`
- [ ] **ENV-02**: URDF `package://` URI references patched to relative filesystem paths so Genesis can resolve STL meshes without a ROS2 environment
- [ ] **ENV-03**: FANUC M-20iD/12L URDF loads in Genesis with `requires_jac_and_IK=True` set explicitly; smoke test confirms no runtime crash after `scene.build()`
- [ ] **ENV-04**: Robot scale validated: at home position, `robot.get_link("tool0").pos` Z-component reads approximately 0.911m (±10mm); fail if <0.5m or >1.5m
- [ ] **ENV-05**: Genesis IK smoke test: call `robot.inverse_kinematics(link, known_reachable_pos, quat, return_error=True)` and confirm translational residual < 0.002m

### Phase 1 — Scene Builder

- [ ] **SCENE-01**: `scene_builder.py` builds a Genesis scene with conveyor (block proxy), pinch unit (block proxy), and FANUC robot; `show_viewer=False` in search mode
- [ ] **SCENE-02**: Scene is built once; robot repositioned between candidates via `robot.set_pos([X, Y, Z])` + `scene.reset()` — never rebuilt per candidate
- [ ] **SCENE-03**: `set_pos()` behavior on `fixed=True` URDF validated empirically; if it does not work, fallback to `n_envs` batch evaluation and architecture is documented
- [ ] **SCENE-04**: CollisionBody factory implements `.from_box(dims, pose)` and `.from_step(path, pose)` so block proxies can be swapped for real STEP meshes without touching evaluator code
- [ ] **SCENE-05**: Conveyor geometry models the inter-roller gap (region where bottom-face cutting TCP paths must reach through)

### Phase 1 — TCP Path Generator and Reach Pre-Filter

- [ ] **PATH-01**: `tcp_path_generator.py` generates ordered `(pos, quat)` waypoints per face for a given shape category and beam placement, with 50mm spacing along each face
- [ ] **PATH-02**: TCP normals are perpendicular to each face; tool orientation is free about the face-normal axis (addressed via Genesis `rot_mask` parameter)
- [ ] **PATH-03**: Paths are generated separately for WZ1 (+1.5ft to +4.0ft) and WZ2 (-1.5ft to -3.0ft); foot values converted via `FT = 0.3048` defined once at module level
- [ ] **PATH-04**: `reach_prefilter.py` eliminates base positions analytically: a candidate `[X, Y, Z_base]` is rejected if any WZ corner point falls outside the robot's reachability annulus (inner radius: min_reach, outer radius: FANUC M-20iD/12L max reach confirmed from spec sheet)
- [ ] **PATH-05**: Pre-filter operates on worst-case WZ corners (not centroid) including max beam depth from MME

### Phase 2 — Evaluator

- [ ] **EVAL-01**: `evaluator.py` accepts a candidate base position `[X, Y, Z]` and a set of TCP waypoints; returns pass/fail with failure reason
- [ ] **EVAL-02**: IK check per waypoint uses `return_error=True`; rejects if translational residual ≥ 0.002m or rotational residual ≥ 0.01 rad
- [ ] **EVAL-03**: Post-IK joint position audit: `qpos` clipped against URDF joint limits; position that requires joints outside limits is rejected
- [ ] **EVAL-04**: Collision check runs `scene.step()` at the resolved `qpos` and calls `robot.get_contacts(with_entity=...)` for conveyor, pinch unit, and beam; contact = reject
- [ ] **EVAL-05**: J5 singularity rejection: if J5 joint angle is within ±5 degrees of 0 at any waypoint in the path, the candidate is rejected
- [ ] **EVAL-06**: Manipulability index computed for each passing waypoint: `w = sqrt(det(J @ J.T))` using `robot.get_jacobian(link)` if available, else finite-difference fallback; uses `eigvalsh` to avoid NaN near singularity
- [ ] **EVAL-07**: WZ1 and WZ2 evaluated independently; candidate passes only if both zones pass; failure reason distinguishes WZ1-only-fail vs WZ2-only-fail vs both

### Phase 2 — Search Loop and Results

- [ ] **SEARCH-01**: Search space bounded by: X in configurable range (default ±2m), Y in configurable range (default ±2m), Z in [0, 1.0m]; pitch=0, roll=0 (hard constraints)
- [ ] **SEARCH-02**: Reach pre-filter applied before any Genesis evaluation; logged with count of candidates eliminated
- [ ] **SEARCH-03**: Initial search uses Optuna TPE sampler (`optuna>=3.6.0`) to propose `[X, Y, Z]` candidates; objective = maximize mean manipulability across all passing waypoints
- [ ] **SEARCH-04**: If Optuna search finds no valid candidates, falls back to a coarse 100mm grid scan over the pre-filtered region with a warning logged
- [ ] **SEARCH-05**: `results_logger.py` writes `results.csv` and `results.json` to `phase1_3d_sim/output/` sorted descending by mean manipulability; includes per-candidate: position, mean_w, WZ1_pass, WZ2_pass, failure_reason
- [ ] **SEARCH-06**: Search is parameterized: TCP offset `[x, y, z]` relative to J6 faceplate is a required CLI/config argument; tool aborts with a clear error if not provided
- [ ] **SEARCH-07**: Runtime logged per evaluation; final run summary reports: candidates evaluated, candidates passed, best position, best manipulability score, total runtime

---

## v2 Requirements

### STEP Mesh Integration

- **STEP-01**: Real STEP collision meshes for pinch_unit and conveyor loaded from user-supplied CAD files
- **STEP-02**: Block proxy dimensions auto-sized from STEP mesh bounding box for continuity across proxy/real runs

### Visualization

- **VIZ-01**: Post-run heatmap of manipulability scores projected onto X-Y floor plane (matplotlib)
- **VIZ-02**: Optional Genesis viewer scene showing robot at best-candidate position with all TCP waypoints rendered

### Advanced Search

- **ADV-01**: Two-stage search: Optuna TPE coarse scan followed by dense 10mm grid within best-found ±100mm window
- **ADV-02**: Multi-shape-category search in one run with combined manipulability score (worst-case across categories)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| RL / reward function training | Old Eden automotive use case; this project is deterministic IK search only |
| Trajectory smoothness / motion planning | Answers placement question only; path quality is a post-placement concern |
| Cycle time / throughput analysis | Handled by PCR41/PCR42 DES; out of scope for placement tool |
| Multi-robot configurations | Single FANUC M-20iD/12L only for this milestone |
| Genesis viewer in search loop | show_viewer=False in all search runs; viewer causes timeout in headless Docker |
| BoTorch/Ax Gaussian process optimizer | GP training overhead (50-200ms/iter) unjustified when IK evaluation is 1-5ms; Optuna TPE sufficient |
| mech_core install into eden venv | Pulls PySide6 and other heavy GUI deps; use sys.path bridge or file contract instead |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AISC-01 through AISC-05 | Phase 1 | Pending |
| MME-01 through MME-05 | Phase 2 | Pending |
| ENV-01 through ENV-05 | Phase 3 | Pending |
| SCENE-01 through SCENE-05 | Phase 4 | Pending |
| PATH-01 through PATH-05 | Phase 5 | Pending |
| EVAL-01 through EVAL-07 | Phase 6 | Pending |
| SEARCH-01 through SEARCH-07 | Phases 7–8 | Pending |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after initial definition*
