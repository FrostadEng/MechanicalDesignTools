# Roadmap: Eden Cell Optimizer — PCR42 Heavy Steel Robot Placement

## Milestone 1 — PCR42 Static Placement Proof

## Overview

Starting from the raw AISC structural steel database, this milestone proves that a floor-mounted FANUC M-20iD/12L can statically reach all required cutting faces across both PCR42 work zones — eliminating the need for a 1-axis positioner. The pipeline runs in two phases: a pure-Python 2D MME sanity check (no Genesis), followed by a Genesis 3D simulation with IK-reachability search over the pre-filtered candidate space. A mandatory engineering review gate separates the two halves — Phase 2 output must be signed off before Phase 3 begins.

## Phases

- [ ] **Phase 1: AISC Filter and Shape Classification** - Load AISC DB, apply PCR42 constraints, classify shapes and handle Pint units
- [ ] **Phase 2: Maximum Material Envelope Generation** - Compute per-category MME bounding boxes, render matplotlib overlays, export phase0_results.json
- [ ] **Phase 3: FANUC URDF Acquisition and Validation** - Clone ros-industrial/fanuc, patch URIs, validate URDF loads in Genesis at correct scale
- [ ] **Phase 4: Genesis Scene Builder** - Build Genesis scene with block proxy collision bodies, validate robot repositioning
- [ ] **Phase 5: TCP Path Generator and Reach Pre-Filter** - Generate ordered TCP waypoints per face/zone, analytically pre-filter candidate space
- [ ] **Phase 6: Evaluator** - Per-candidate IK + joint limits + collision + J5 singularity + manipulability evaluation
- [ ] **Phase 7: Search Loop (Optuna TPE)** - Optuna TPE-driven candidate proposal loop over pre-filtered search space
- [ ] **Phase 8: Results Logger and Integration** - CSV/JSON output sorted by manipulability, end-to-end integration run

---

> **ENGINEERING REVIEW GATE (between Phase 2 and Phase 3)**
> Phase 3 does NOT begin until the user has inspected all PNG overlays in
> `eden/experiments/Beam_Coping_Machine/phase0_2d_mme/` and confirms:
> - Shape counts per category look correct
> - MME bounding boxes are visually reasonable
> - phase0_results.json schema matches downstream expectations
>
> Sign-off is required. Run `/gsd-plan-phase 3` only after explicit approval.

---

## Phase Details

### Phase 1: AISC Filter and Shape Classification
**Goal**: The AISC database is filtered to PCR42-compatible shapes, fully classified, and all dimensional values are safe for downstream geometric computation
**Depends on**: Nothing (first phase)
**Requirements**: AISC-01, AISC-02, AISC-03, AISC-04, AISC-05
**Success Criteria** (what must be TRUE):
  1. Pipeline loads aisc_shapes.json via the SectionProperties API without import errors in the Eden venv context (sys.path bridge in place)
  2. Filtering produces a deterministic list of shapes passing both constraints: weight <= 300 lbs/ft AND max cross-sectional dimension <= 1100mm
  3. Every valid shape has exactly one category assignment: 3-face, 4-face, L-angle-A, or L-angle-B
  4. Unequal-leg L-angles appear twice in the output — once per orientation — with distinct MME entries
  5. No raw Pint quantity objects reach any geometric computation; all dimensions are plain Python floats in consistent units
**Plans**: 6 plans

Plans:
- [ ] 01-01: Establish Eden venv sys.path bridge to engineering_tools/mech_core and confirm SectionProperties API loads
- [ ] 01-02: Implement PCR42 weight filter (<=300 lbs/ft) with Pint-safe magnitude extraction
- [ ] 01-03: Implement PCR42 dimension filter (max cross-sectional dimension <=1100mm) with Pint-safe extraction
- [ ] 01-04: Implement shape category classifier for 3-face, 4-face, and L-angle types
- [ ] 01-05: Implement L-angle dual-orientation splitter (L-angle-A long leg near datum, L-angle-B short leg near datum)
- [ ] 01-06: Write unit tests for filter, classifier, and unit-strip pipeline; assert no Pint quantities leak downstream

### Phase 2: Maximum Material Envelope Generation
**Goal**: Per-category MME bounding boxes are computed and rendered as human-reviewable PNG overlays; phase0_results.json is written as the downstream data contract
**Depends on**: Phase 1
**Requirements**: MME-01, MME-02, MME-03, MME-04, MME-05
**Success Criteria** (what must be TRUE):
  1. Each shape category produces a composite bounding box (max-width x max-depth) computed from all valid shapes in that category
  2. Each PNG overlay shows all valid cross-section profiles superimposed at correct relative scale with Y=0 conveyor line, X=0 datum roller line, and the MME bounding box
  3. One PNG per category is written to eden/experiments/Beam_Coping_Machine/phase0_2d_mme/ without file-write errors
  4. phase0_results.json is written with schema {category: {mme_width_mm, mme_depth_mm, shape_count, shapes[]}} and is valid JSON
  5. phase0_results.json is machine-readable by Phase 5 without schema changes
**Plans**: 5 plans

Plans:
- [ ] 02-01: Implement per-category MME bounding box computation (max width x max depth across all shapes in category)
- [ ] 02-02: Implement matplotlib overlay renderer — superimposed cross-section profiles with conveyor line, datum line, MME box
- [ ] 02-03: Implement PNG export to phase0_2d_mme/ output directory with one file per category
- [ ] 02-04: Implement phase0_results.json serializer with full schema validation
- [ ] 02-05: Wire Phase 1 + Phase 2 into a single runnable phase0_2d_mme.py entry point; confirm all outputs generated in one invocation

---

> **STOP — ENGINEERING REVIEW GATE**
> Inspect all PNGs and phase0_results.json before proceeding to Phase 3.
> See gate description above under Phases.

---

### Phase 3: FANUC URDF Acquisition and Validation
**Goal**: The FANUC M-20iD/12L URDF is on-disk with patched mesh URIs, loads in Genesis at correct scale (tool0 Z ~0.911m), and passes IK smoke test
**Depends on**: Phase 2 (after engineering review gate sign-off)
**Requirements**: ENV-01, ENV-02, ENV-03, ENV-04, ENV-05

> **RESEARCH FLAG**: This phase requires `/gsd-research-phase` before planning begins.
> Open questions:
> - `robot.get_jacobian()` availability in Genesis 0.3.4 (rigid_entity.py:862 — not in public docs)
> - `robot.set_pos()` behavior on `fixed=True` URDF after `scene.build()` — if broken, entire search loop switches to n_envs batch architecture
> - ros-industrial/fanuc joint names after cloning (expected joint_1 through joint_6, tool0 — must verify)
> - FANUC M-20iD/12L official reach radius (three conflicting values: 1813mm, 1831mm, 1868mm — confirm from spec sheet)

**Success Criteria** (what must be TRUE):
  1. ros-industrial/fanuc is cloned as a git submodule under eden/assets/fanuc/ and all URDF package:// URIs resolve to relative filesystem paths
  2. Genesis loads the URDF after scene.build() with requires_jac_and_IK=True set explicitly — no runtime crash
  3. At home position, robot.get_link("tool0").pos Z-component reads between 0.901m and 0.921m (0.911m nominal ±10mm); test fails and blocks if outside this range
  4. IK smoke test passes: robot.inverse_kinematics(link, known_reachable_pos, quat, return_error=True) returns translational residual < 0.002m
  5. robot.set_pos() repositioning behavior is documented empirically: either confirmed working or n_envs fallback architecture is specified in a decision record
**Plans**: 7 plans

Plans:
- [ ] 03-01: Clone ros-industrial/fanuc as git submodule into eden/assets/fanuc/; enumerate URDF file paths and joint names
- [ ] 03-02: Write URDF package:// URI patcher script; validate all mesh STL paths resolve to on-disk files after patching
- [ ] 03-03: Write minimal Genesis URDF load script with requires_jac_and_IK=True; confirm scene.build() completes without crash
- [ ] 03-04: Validate robot scale — assert tool0 Z is in [0.901, 0.921] m at home position; document scale=1.0 vs corrective scale value
- [ ] 03-05: IK smoke test — call inverse_kinematics with return_error=True on a known-reachable pose; assert translational residual < 0.002m
- [ ] 03-06: Empirically test robot.set_pos() on fixed=True URDF after build; document result; if broken, write n_envs fallback architecture design decision
- [ ] 03-07: Verify robot.get_jacobian() availability in Genesis 0.3.4; if absent, implement and test finite-difference Jacobian fallback

### Phase 4: Genesis Scene Builder
**Goal**: A complete Genesis scene exists with conveyor (inter-roller gap modeled), pinch unit, and FANUC robot; robot.set_pos() + scene.reset() repositioning is validated; CollisionBody factory supports proxy-to-STEP swap
**Depends on**: Phase 3
**Requirements**: SCENE-01, SCENE-02, SCENE-03, SCENE-04, SCENE-05
**Success Criteria** (what must be TRUE):
  1. scene_builder.py builds a Genesis scene containing conveyor block proxy, pinch unit block proxy, and FANUC robot in a single build() call with show_viewer=False
  2. Robot can be repositioned between candidates via robot.set_pos([X,Y,Z]) + scene.reset() without calling scene.build() again; verified with at least 3 sequential positions
  3. Conveyor geometry models the inter-roller gap region where bottom-face TCP paths must reach through
  4. CollisionBody.from_box(dims, pose) and CollisionBody.from_step(path, pose) both work; evaluator code does not need to change when switching between proxy and STEP mesh
  5. If set_pos() is non-functional, n_envs batch fallback is implemented and search loop architecture is documented accordingly
**Plans**: 6 plans

Plans:
- [ ] 04-01: Implement conveyor block proxy with inter-roller gap modeled as geometry cutout or separate collision entities
- [ ] 04-02: Implement pinch unit block proxy with correct bounding box dimensions
- [ ] 04-03: Implement CollisionBody factory with from_box() and from_step() constructors; ensure evaluator API surface is identical for both
- [ ] 04-04: Assemble scene_builder.py combining conveyor, pinch unit, and FANUC robot into one build() call
- [ ] 04-05: Validate robot.set_pos() + scene.reset() repositioning loop — test 3 sequential candidate positions, confirm kinematics are consistent after each reset
- [ ] 04-06: Write scene integration smoke test; confirm scene.step() runs without error and robot contacts can be queried

### Phase 5: TCP Path Generator and Reach Pre-Filter
**Goal**: Pure Python modules generate ordered TCP waypoints per face/zone and analytically eliminate infeasible base positions; both are fully unit-testable without Genesis
**Depends on**: Phase 2 (reads phase0_results.json), Phase 3 (FANUC reach spec confirmed)
**Requirements**: PATH-01, PATH-02, PATH-03, PATH-04, PATH-05
**Success Criteria** (what must be TRUE):
  1. tcp_path_generator.py produces ordered (pos, quat) waypoints at 50mm spacing for each face of a given shape category, with TCP normals perpendicular to each face
  2. WZ1 (+1.5ft to +4.0ft) and WZ2 (-1.5ft to -3.0ft) paths are generated separately; FT = 0.3048 is defined once at module level and used exclusively for all foot-to-meter conversion
  3. reach_prefilter.py rejects candidates where any WZ corner point falls outside the robot reachability annulus; operates on worst-case WZ corners including max MME beam depth from phase0_results.json
  4. Both modules import and run correctly with zero Genesis imports; pytest suite passes in the main engineering_tools venv
  5. Pre-filter eliminates a measurable fraction of the raw candidate grid in a benchmark test (confirming it is doing useful work)
**Plans**: 7 plans

Plans:
- [ ] 05-01: Define module-level constants (FT = 0.3048, FANUC reach annulus inner/outer radii from confirmed spec); document source
- [ ] 05-02: Implement WZ1 and WZ2 path segment boundary computation from FT constant
- [ ] 05-03: Implement per-face waypoint generator for 3-face shape category (top, left, right faces)
- [ ] 05-04: Implement per-face waypoint generator for 4-face and L-angle categories
- [ ] 05-05: Implement reach_prefilter.py with annular cylinder test against worst-case WZ corners + max MME beam depth
- [ ] 05-06: Write pytest suite for tcp_path_generator.py and reach_prefilter.py; confirm zero Genesis imports and all tests pass outside Eden venv
- [ ] 05-07: Run pre-filter benchmark on 100mm grid over ±2m x ±2m; confirm >50% candidate elimination rate

### Phase 6: Evaluator
**Goal**: evaluator.py accepts a candidate base position and TCP waypoints, runs IK + collision + joint limits + J5 singularity + manipulability checks, and returns a structured pass/fail result with per-zone decomposition
**Depends on**: Phase 3 (URDF), Phase 4 (scene builder), Phase 5 (TCP paths)
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07
**Success Criteria** (what must be TRUE):
  1. evaluator.py accepts (candidate_pos, tcp_waypoints) and returns a structured result containing pass/fail, failure_reason, WZ1_pass, WZ2_pass, and mean manipulability score
  2. IK check uses return_error=True; any waypoint with translational residual >= 0.002m or rotational residual >= 0.01 rad immediately fails the candidate with reason logged
  3. Post-IK joint limit audit clips qpos against URDF limits and rejects candidates that require out-of-limit joints
  4. Collision check runs scene.step() at resolved qpos and queries robot.get_contacts() for conveyor, pinch unit, and beam; any contact fails the candidate
  5. J5 singularity check rejects any candidate where J5 joint angle is within +-5 degrees of 0 at any waypoint
  6. Manipulability computed via robot.get_jacobian() if available, else finite-difference fallback; uses eigvalsh not det; never produces NaN
  7. WZ1 and WZ2 are evaluated independently; failure reason distinguishes WZ1-only-fail, WZ2-only-fail, and both-fail
**Plans**: 8 plans

Plans:
- [ ] 06-01: Implement IK check loop per waypoint with return_error=True and explicit residual thresholds (2mm / 0.01 rad)
- [ ] 06-02: Implement post-IK joint limit audit using URDF joint limit values; reject out-of-limit qpos
- [ ] 06-03: Implement collision check via scene.step() + robot.get_contacts() for all environmental entities
- [ ] 06-04: Implement J5 singularity rejection (+-5 degree dead-band at each waypoint)
- [ ] 06-05: Implement manipulability computation using robot.get_jacobian() with eigvalsh; include finite-difference fallback path
- [ ] 06-06: Implement WZ1/WZ2 independent evaluation with structured per-zone pass/fail output
- [ ] 06-07: Implement evaluator.py top-level interface: (candidate_pos, waypoints) -> EvalResult dataclass
- [ ] 06-08: Write evaluator integration test against known-good and known-bad candidate positions; assert correct pass/fail classification

### Phase 7: Search Loop (Optuna TPE)
**Goal**: An Optuna TPE-driven search loop proposes [X,Y,Z] candidates over the pre-filtered space, calls the evaluator, and falls back to coarse grid scan if no valid candidates are found
**Depends on**: Phase 5 (pre-filter), Phase 6 (evaluator)
**Requirements**: SEARCH-01, SEARCH-02, SEARCH-03, SEARCH-04
**Success Criteria** (what must be TRUE):
  1. Search space is bounded by configurable X/Y ranges (default +-2m) and Z in [0, 1.0m]; pitch and roll are hard-constrained to 0 and never sampled
  2. Reach pre-filter is applied before every Genesis evaluation; count of eliminated candidates is logged at run completion
  3. Optuna TPE sampler (optuna>=3.6.0 in requirements.txt) proposes [X,Y,Z] candidates; objective is maximize mean manipulability across passing waypoints
  4. If Optuna finds zero valid candidates, search falls back to a coarse 100mm grid scan over the pre-filtered region with a warning logged at WARNING level
  5. TCP offset [x,y,z] relative to J6 is a required argument; search_loop.py aborts immediately with a clear error message if not provided
**Plans**: 6 plans

Plans:
- [ ] 07-01: Add optuna>=3.6.0 to Robot_Simulations/eden/requirements.txt; verify import in Eden venv
- [ ] 07-02: Implement configurable search space definition with X/Y range, Z range [0, 1.0m], and hard pitch=0, roll=0 constraints
- [ ] 07-03: Implement TCP offset validation — abort with clear error if not provided via CLI or config
- [ ] 07-04: Implement Optuna TPE study with evaluator as objective function; maximize mean manipulability; skip pre-filtered candidates
- [ ] 07-05: Implement 100mm coarse grid scan fallback triggered when Optuna study finds zero passing candidates
- [ ] 07-06: Wire pre-filter into search loop; log eliminated candidate count; run end-to-end dry run with evaluator mock to confirm flow

### Phase 8: Results Logger and Integration
**Goal**: CSV and JSON outputs sorted by manipulability are written to phase1_3d_sim/output/; a full end-to-end run against the W-shapes category confirms the pipeline produces at least one valid position
**Depends on**: Phase 7
**Requirements**: SEARCH-05, SEARCH-06, SEARCH-07
**Success Criteria** (what must be TRUE):
  1. results.csv and results.json are written to phase1_3d_sim/output/ sorted descending by mean_w; each row contains position [X,Y,Z], mean_w, WZ1_pass, WZ2_pass, failure_reason, eval_time_ms
  2. Runtime summary is printed at run completion: candidates evaluated, candidates passed, best position, best manipulability score, total runtime
  3. End-to-end run for W-shapes category completes without crash and produces at least one candidate with both WZ1_pass and WZ2_pass = True, OR produces a documented engineering explanation for why no valid position exists
  4. search_loop.py aborts with a clear error (exit code != 0) if TCP offset argument is missing
  5. All output files are written atomically (no partial files on crash); results are deterministic for a fixed Optuna random seed
**Plans**: 5 plans

Plans:
- [ ] 08-01: Implement results_logger.py writing results.csv and results.json to phase1_3d_sim/output/ sorted by mean_w descending
- [ ] 08-02: Implement per-row schema: position [X,Y,Z], mean_w, WZ1_pass, WZ2_pass, failure_reason, eval_time_ms
- [ ] 08-03: Implement runtime summary reporter: candidates evaluated, candidates passed, best position, best w, total runtime
- [ ] 08-04: Implement atomic file write (write to .tmp then rename) to prevent partial output on crash
- [ ] 08-05: Run full end-to-end integration against W-shapes category; confirm pipeline runs to completion and produces valid output; document result

## Progress

**Execution Order:**
Phases execute in strict numeric order. Phase 3 requires engineering review gate sign-off after Phase 2.
Phases 5 and 6 can begin in parallel after Phase 4 completes (Phase 5 has no Genesis dependency).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. AISC Filter and Shape Classification | 0/6 | Not started | - |
| 2. Maximum Material Envelope Generation | 0/5 | Not started | - |
| 3. FANUC URDF Acquisition and Validation | 0/7 | Not started | - |
| 4. Genesis Scene Builder | 0/6 | Not started | - |
| 5. TCP Path Generator and Reach Pre-Filter | 0/7 | Not started | - |
| 6. Evaluator | 0/8 | Not started | - |
| 7. Search Loop (Optuna TPE) | 0/6 | Not started | - |
| 8. Results Logger and Integration | 0/5 | Not started | - |
