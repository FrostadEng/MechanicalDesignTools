# Feature Research

**Domain:** Robot workcell placement / reachability optimization tool (industrial robotics commissioning)
**Researched:** 2026-04-16
**Confidence:** MEDIUM — training data through Aug 2025; web search unavailable. Competitor analysis from direct tool familiarity (RoboDK, RobotStudio, KUKA.Sim) plus academic literature on reachability analysis. EDEN spec is the ground truth for this project.

---

## Ecosystem Context

Robot placement optimization tools fall into three categories:

**Commercial GUI simulators** (RoboDK, ABB RobotStudio, KUKA.Sim, Fanuc ROBOGUIDE): Full 3D simulation environments aimed at programmers and integrators. Reachability analysis is a secondary feature — primarily collision/path simulation with manual placement trials. Reachability "clouds" in RoboDK and RobotStudio show which Cartesian points are reachable for a given placement, but placement search is manual (user drags robot, reruns reach test).

**Academic/research toolkits** (Python + ikpy/opw_kinematics, MATLAB Robotics Toolbox, roboticstoolbox-python by Peter Corke): Provide IK + forward kinematics primitives, sometimes reachability workspace visualization. Placement optimization is left to the researcher; no automated grid search. Manipulability analysis (Yoshikawa measure, condition number) often included.

**Custom industrial scripts**: Most industrial integrators write one-off Python/MATLAB scripts for specific cell layout questions. These are typically one-time analyses, not reusable tools. They focus on pass/fail per pose, rarely produce formal gap reports or error budgets.

EDEN occupies a distinct position: an exhaustive brute-force optimizer for a specific robot + application domain (structural beam plasma coping) with formal engineering rigor (error budget, deflection model, modal check). No off-the-shelf tool does this combination.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features any credible placement/reachability tool must have. Missing these means the tool is a toy or research script, not an engineering deliverable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| IK solution per target pose | Every reach tool does this — it's the core primitive | HIGH | OPW C++ pybind11 required; ~4 μs/query. Pure Python non-viable at this scale |
| Joint limit enforcement | Without this, "reachable" is meaningless — solutions outside joint limits are invalid | LOW | Filter 8 OPW solutions against M-20iD/20 joint limits table |
| Reachability percentage score | Primary output of any placement analysis — "X% of poses reachable" | LOW | Aggregate pass/fail ratio across test set; trivial once IK is running |
| Best configuration identification | The tool must output a recommendation, not just raw data | LOW | Rank by reachability_pct, break ties by hardware_cost |
| Collision checking (boundary) | Any path that crashes the robot into walls/conveyors is invalid | MEDIUM | python-fcl wall planes, conveyor surface, ground plane |
| Wrist load compliance check | Industrial standard — tool designers must verify against manufacturer diagram | MEDIUM | Check wrist load diagram (Fig 3.5c) with 1.25× safety factor on all tool designs |
| Tool design space enumeration | Any analysis that fixes the tool is incomplete for greenfield design | MEDIUM | Sweep torch_angle × boom_length × puck_drop at 6 mm steps |
| Per-beam pass/fail breakdown | "90% reachable" is useless without knowing which 10% fail | LOW | reachability_heatmap.json keyed by beam section designation |
| Gap report (unreachable beams/faces) | Commissioning engineers need to know scope of unreachable work before buying hardware | LOW | gap_report.json with failure reason (reach vs. geometry vs. collision) |
| JSON/structured output files | Human-readable results that can be shared, archived, re-analyzed | LOW | best_config.json, top_10_configs.json — downstream use requires structured data |
| Dual-unit logging (Imperial + SI) | Structural steel in the US is Imperial; robotics/IK is SI. Mixed teams need both | LOW | Log mm alongside inches throughout; non-negotiable for US fabrication context |
| Run metadata / reproducibility record | Results are engineering claims — must document what grid, what catalog, what version | LOW | run_metadata.json: timing, filter rejection rates, grid dimensions, software versions |

### Differentiators (Competitive Advantage)

Features that no commercial GUI simulator provides and that distinguish EDEN as a rigorous engineering tool rather than an analysis script.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Two-phase hierarchical search (Phase A + Phase B) | Exhaustive coverage of 30.6M cell space in 23 hours instead of 13 days — makes the problem tractable without heuristics | HIGH | Core algorithmic contribution; Phase A with ~180 rep tools finds good placements; Phase B tests all 1044 tools at top 500 |
| Robot yaw as explicit search variable | RoboDK/RobotStudio require manual yaw trials; EDEN searches {0°,90°,180°,270°} automatically, finding J-limit advantage cases that manual analysis misses | LOW | 4 discrete values; incremental cost ~4× but often decisive for borderline placements |
| Riser cross-section as search variable | No simulator treats structural riser stiffness as an optimization variable; EDEN's 5-section sweep finds cases where a stiffer/lighter section shifts the optimum more than grid refinement | MEDIUM | Deflection model pre-computation gates (section, height) pairs before IK is run |
| RSS TCP error budget with named sub-allocations | Commercial tools report reachability with no accuracy model. EDEN quantifies how each hardware element (riser deflection, baseplate rotation, tool boom, thermal) contributes to the 1.0 mm TCP budget | MEDIUM | error_budget_report.json per top config; this is what an engineer needs to justify the design to a quality team |
| Baseplate rotation in deflection model | V2 omitted this; it's typically 2–10× column deflection. Including anchor bolt stretch + grout compression makes the deflection model trustworthy, not optimistic | MEDIUM | Closed-form superposition model using k_anchor, k_grout, k_plate — no FEA required |
| Modal frequency gate (f₁ ≥ 15 Hz) | Static deflection analysis misses vibration-related accuracy failure. Cope dynamics excite 5–12 Hz; checking f₁ rejects risers that look stiff but will resonate | LOW | Single-DOF lumped model; add as pre-computation gate alongside deflection |
| Active beam-to-tool collision check | RoboDK can check tool-environment collision, but requires manual scene setup per beam. EDEN automatically loads each AISC beam mesh into FCL and checks cope trajectory tool paths against it | HIGH | NEW in V3; required because cope trajectories pass under top flanges. python-fcl scene rebuild per beam evaluation |
| Hardest-first beam ordering with reach/geometry split | Naive evaluation tests beams in arbitrary order; EDEN sorts by difficulty and separates reach-failures (large beam, quit) from geometry-failures (unusual angle, continue) — saves ~70% evaluation time without sacrificing coverage | MEDIUM | beam_difficulty_ranking.json with two sorted lists; refined early-termination logic |
| TCP clustering with CG-inclusive 5 mm bins | 10 mm clustering that ignores CG causes Phase A false-passes (~5–15%). CG-inclusive clustering ensures representative tools actually represent the wrist load behavior of their cluster | MEDIUM | 6D feature vector: (TCP_xyz, CG_xy, torch_angle); k-means or binning |
| Full AISC catalog coverage as test set | Commercial tools test a handful of user-selected poses. EDEN tests all AISC W/C/S/L/HSS/Pipe/Rect shapes ≤300 lb/ft, giving a coverage claim backed by the entire catalog | HIGH | aisc.py integration; beam difficulty ranking; pose spacing 25 mm on each face |
| Buildable-resolution search grid | 6 mm grid searches to false precision — field anchor bolt tolerance is ±3–5 mm. 25 mm Y steps and discrete stock heights produce results that can actually be built | LOW | Correct framing of what "optimum" means in practice; prevents recommending a placement that can't be located in the field |
| Hardware validation plan as optimizer output | Optimizer outputs are hypotheses. Packaging a laser tracker + modal + strain gauge validation protocol alongside the top-10 configs is unusual and valuable for commissioning teams | LOW | Section 12 in V3 spec; top_10_configs.json + structured validation checklist |
| Cope feasibility check (trajectory continuity) | Reachability of straight-cut poses does not guarantee a cope trajectory can be executed continuously (no joint jumps). EDEN checks trajectory continuity as a Phase B secondary gate | MEDIUM | Only triggered when reachability ≥ 95%; tests square/radius/block cope patterns on representative beams |
| URDF scene visualization of top-N configs | Human-readable spatial output so engineers can visually confirm the recommended placement makes sense before buying steel | MEDIUM | trimesh or pyvista render; shows robot + riser + beam in cell layout |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Machine learning / genetic algorithm optimization | "Faster than brute force" — integrators who've seen convergence issues with exhaustive search want smarter search | Results are not guaranteed to be near-global-optimum; an ML optimizer might confidently return a local minimum. For a one-time capital hardware decision (riser, base plate, tool geometry), false confidence is worse than longer runtime | Hierarchical two-phase grid search reduces 13-day flat search to 23 hours without sacrificing exhaustiveness. This is the right tradeoff. |
| Continuous/fine-grained grid (6 mm Y steps) | More resolution = more precision (intuition) | Field anchor tolerance is ±3–5 mm, so 6 mm results are false precision and cannot be built. Continuous grid also multiplies evaluation count 10× without producing buildable results | 25 mm Y steps matching field anchor bolt tolerance; discrete stock riser heights |
| Interactive GUI / drag-and-drop placement | Users familiar with RoboDK/RobotStudio expect GUI interaction | A GUI adds a development tier (UI framework, event loop, rendering) that has no value for an exhaustive batch optimizer. The optimizer runs for 23 hours unattended; interaction during search is meaningless | Rich JSON outputs + URDF scene renders provide all the "see what happened" value without real-time interaction complexity |
| Real-time robot communication (OPC-UA, Fanuc PCDK) | "Connect to the real robot for validation" | Offline optimizer has no business talking to a live robot. Coupling introduces dependency on robot availability, network, and safety protocols. Hardware validation belongs to Section 12 protocol, not the optimizer | top_10_configs.json feeds a separate hardware validation checklist; real robot work is manual and intentional |
| ROS/ROS2 integration | Research background expectation; ROS has standard robot description formats | ROS adds catkin/colcon build complexity, message serialization overhead, and daemon dependencies. OPW C++ via pybind11 gives the same IK speed without any of this overhead | Standalone Python + C++ pybind11 as specified; URDF files read directly via urdfpy/trimesh, no ROS required |
| GPU-accelerated IK (CUDA) | Large grid → "use GPU for speedup" | The IK bottleneck is per-query latency (~4 μs C++ OPW), not throughput. GPU parallelism helps when you have thousands of independent queries per batch with minimal setup cost; this workload has hierarchical filtering that makes per-query GPU dispatch wasteful. CPU multiprocessing on 14 threads is the right model | Python multiprocessing.Pool(14) with C++ OPW kernel as specified |
| Manipulability as primary scoring metric | Academic robotics tradition — Yoshikawa manipulability index used as primary placement criterion | Manipulability measures how far from a singularity a configuration is, not whether it can actually reach and hold a cut pose. High mean manipulability across unreachable poses is meaningless. For plasma coping, cut quality depends on TCP accuracy, not manipulability margin | Use manipulability as a secondary tiebreaker (manipulability_mean in scoring). Primary metric is reachability_pct |
| Per-pose trajectory optimization (time-optimal, velocity) | Path planning completeness | Trajectory optimization requires a motion planner, velocity/acceleration models, and per-path solve times orders of magnitude higher than IK queries. This is path planning, not placement optimization | Scope boundary: EDEN determines optimal placement so that a trajectory planner can later succeed. Cope feasibility check verifies trajectory continuity (no joint jumps) without optimizing it |
| Thermal compensation / real-time TCP correction | "Close the loop on thermal drift" | Closed-loop TCP correction requires sensors (laser profiling, seam tracking) on the real cell. Modeling this in the optimizer adds unvalidated complexity to an already long error budget chain | Thermal drift is allocated 0.30 mm in the RSS budget and flagged as "measure on hardware." This is the correct conservative engineering approach |

---

## Feature Dependencies

```
[OPW IK Solver (C++ pybind11)]
    └──required by──> [Reachability % per pose]
                          └──required by──> [Phase A placement scoring]
                                                └──required by──> [Phase B full tool sweep]
                                                                      └──required by──> [best_config.json]
                                                                      └──required by──> [top_10_configs.json]
                                                                      └──required by──> [gap_report.json]

[Tool Design Table (Phase 1)]
    └──required by──> [TCP/CG clustering]
                          └──required by──> [Phase A representative tool set]
    └──required by──> [Wrist load compliance check]
    └──required by──> [Tool boom deflection gate]

[Riser Deflection + Modal Pre-computation]
    └──required by──> [Phase A + B filter cascade (step 1)]
    └──provides data to──> [error_budget_report.json]

[Beam Catalog (aisc.py)]
    └──required by──> [Target pose database]
                          └──required by──> [Full beam evaluation]
                                                └──required by──> [reachability_heatmap.json]
                                                └──required by──> [gap_report.json]

[Collision Environment (python-fcl)]
    └──required by──> [Boundary wall check]
    └──required by──> [Active beam-to-tool collision check]
                          └──enhances──> [gap_report.json failure reasons]

[Phase B results]
    └──required by──> [Cope feasibility check]
    └──required by──> [error_budget_report.json (per-config)]
    └──required by──> [URDF scene visualization]

[top_10_configs.json]
    └──feeds──> [Hardware validation plan (Section 12)]
```

### Dependency Notes

- **OPW IK solver is the single most critical dependency**: Everything downstream of pose evaluation requires it. Must be validated (FK→IK round-trips) before any grid search runs.
- **Tool Design Table must precede Phase A**: Representatives are drawn from the clustered tool table. Phase A is meaningless without a valid representative set.
- **Riser model must precede both phases**: The deflection/modal gate is the first filter in the cascade; incorrect model = wrong placements passed through.
- **Active beam collision requires per-beam FCL scene rebuild**: This is an implementation complexity risk — FCL scene management inside the tight inner loop of beam evaluation is non-trivial.
- **Cope feasibility check depends on Phase B completing**: It is a secondary Phase B check, not a standalone feature. Cannot be developed in isolation.

---

## MVP Definition

### Launch With (v1)

Minimum output set that constitutes a valid engineering deliverable — the "optimizer ran and produced a defensible recommendation."

- [ ] OPW IK solver validated — FK→IK round-trips, joint limits enforced, operating space matches Fig 3.2a
- [ ] Tool Design Table (Phase 1) — valid_tools.json with ~1044 entries, clustered to ~180 representatives
- [ ] Riser deflection + modal pre-computation — riser_validity_table.json pruning invalid (section, height) pairs
- [ ] Target pose database (frozen) — straight-cut poses at 25 mm spacing, all AISC ≤300 lb/ft, difficulty-ranked
- [ ] Phase A grid search — top 500 placements with reachability_pct scores
- [ ] Phase B full tool sweep — best_config.json + top_10_configs.json
- [ ] Boundary collision checking — walls, conveyor, ground (python-fcl)
- [ ] Per-beam reachability heatmap — reachability_heatmap.json
- [ ] Gap report — gap_report.json with failure reason categories
- [ ] Error budget report — error_budget_report.json (modeled contributors per top config)
- [ ] Dual-unit logging throughout
- [ ] Run metadata — reproducibility record

### Add After Validation (v1.x)

Add once core optimizer produces valid, trusted results.

- [ ] Active beam-to-tool collision check — currently only boundary walls; add beam mesh per evaluation when FCL scene management is stable
- [ ] URDF scene visualization of top-10 — trimesh/pyvista renders; useful for communication but not needed to validate the numbers
- [ ] Cope feasibility check (trajectory continuity) — secondary Phase B gate; only needed once ≥95% reachability configs are confirmed to exist
- [ ] Hardware validation protocol documentation — top_10_configs.json + structured checklist; needed before committing to steel purchase

### Future Consideration (v2+)

Defer until v1 results are validated on hardware.

- [ ] Robot calibration integration — post-hardware laser tracker data fed back to update kinematic model and re-run Phase B
- [ ] Dynamic path simulation — trajectory planner integration, acceleration limit checks, cable whip modeling
- [ ] Multi-zone optimization — extend grid to include zone-switching placements if secondary workzone is added
- [ ] Closed-loop TCP correction modeling — update error budget when seam tracking or laser profiling is added to cell

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| OPW IK solver (C++ pybind11, validated) | HIGH | HIGH | P1 |
| Tool Design Table + Phase 1 evaluation | HIGH | MEDIUM | P1 |
| Riser deflection + modal pre-computation | HIGH | MEDIUM | P1 |
| Target pose database (AISC catalog) | HIGH | MEDIUM | P1 |
| Phase A hierarchical search | HIGH | HIGH | P1 |
| Phase B full tool sweep | HIGH | MEDIUM | P1 |
| best_config.json + top_10_configs.json | HIGH | LOW | P1 |
| Boundary collision (walls, conveyor, ground) | HIGH | MEDIUM | P1 |
| reachability_heatmap.json | HIGH | LOW | P1 |
| gap_report.json with failure reasons | HIGH | LOW | P1 |
| error_budget_report.json | HIGH | LOW | P1 |
| Dual-unit logging | MEDIUM | LOW | P1 |
| run_metadata.json | MEDIUM | LOW | P1 |
| Active beam-to-tool collision (FCL per beam) | HIGH | HIGH | P2 |
| URDF scene visualization (top-10) | MEDIUM | MEDIUM | P2 |
| Cope feasibility check | MEDIUM | MEDIUM | P2 |
| Hardware validation protocol | MEDIUM | LOW | P2 |
| Robot calibration feedback loop | LOW | HIGH | P3 |
| Dynamic path simulation | LOW | HIGH | P3 |
| Multi-zone optimization | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1 to constitute a valid engineering deliverable
- P2: Add after v1 results are trusted; needed for full commissioning package
- P3: Future work; only if hardware results reveal need

---

## Competitor Feature Analysis

| Feature | RoboDK | RobotStudio (ABB) | Custom Python (opw/ikpy) | EDEN (this project) |
|---------|--------|-------------------|--------------------------|----------------------|
| IK solver | Built-in (numerical, ~1 ms) | Built-in (numerical) | Analytical (OPW/ikpy, ~4–40 μs) | OPW C++ pybind11 (~4 μs) |
| Placement search | Manual — user moves robot, reruns test | Manual | Custom loop if user writes it | Exhaustive 2-phase hierarchical grid |
| Reachability cloud/map | Yes — per-placement Cartesian density map | Yes — reach map over Cartesian grid | Possible with scripting | Per-beam pass/fail heatmap over AISC catalog |
| Collision detection | Yes — mesh-based, all objects | Yes | Via python-fcl if integrated | python-fcl (boundary walls + beam mesh per evaluation in v1.x) |
| EOAT design optimization | No — user sets fixed tool | No | No | Yes — full sweep of torch_angle × boom_length × puck_drop |
| Wrist load check | No | No (user must verify manually) | No | Yes — wrist load diagram check with 1.25× safety factor |
| Deflection / modal analysis | No | No | No | Yes — closed-form riser + baseplate + tool boom model; f₁ gate |
| Error budget (RSS) | No | No | No | Yes — named sub-allocations to 1.0 mm RSS target |
| Gap report (unreachable catalog items) | Not structured — visual only | Not structured | Only if user codes it | Structured JSON gap_report.json with failure reason codes |
| Cope trajectory feasibility | No | No | No | Yes — trajectory continuity check (Phase B secondary gate) |
| Hardware validation protocol | No | No | No | Yes — laser tracker + modal + strain gauge + test cut checklist |
| Runtime for full catalog sweep | Manual setup per run, hours to days depending on pose count | Similar | Depends entirely on user implementation | ~23 hours for full AISC catalog × full placement grid |
| Structural steel catalog integration | No — user imports geometry manually | No | No | Yes — aisc.py full catalog, difficulty-ranked |

The key differentiator gap: **No existing tool combines EOAT design optimization, structural riser engineering, TCP error budget, and full-catalog reachability scoring into a single automated run.** EDEN's value is the integration, not any single feature.

---

## Sources

- RoboDK feature set: training data through Aug 2025 (MEDIUM confidence; core features stable since 2022)
- ABB RobotStudio reach analysis features: training data through Aug 2025 (MEDIUM confidence)
- KUKA.Sim feature set: training data through Aug 2025 (LOW confidence; less familiar)
- OPW kinematics performance: https://github.com/Jmeyer1292/opw_kinematics — spec confirms ~4 μs C++ target
- python-fcl collision API: https://github.com/BerkeleyAutomation/python-fcl — spec confirms use
- AISC 360 / AWS D1.1 tolerance values: cited in V3 spec Section 3 and 17C
- Fanuc M-20iD/20 wrist load limits: V3 spec Section 2, citing manual B-84074EN/03
- Yoshikawa manipulability: Yoshikawa (1985) — standard academic reference, training data HIGH confidence
- V3 spec (primary ground truth): `Robot_Simulations/Optimizing_Robot_Placement.md`

---
*Feature research for: Robot workcell placement / reachability optimization — EDEN Cell Optimizer*
*Researched: 2026-04-16*
