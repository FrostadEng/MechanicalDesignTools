# Roadmap: EDEN Cell Optimizer

## Overview

Build a bounded brute-force grid search optimizer that exhaustively determines the optimal Fanuc M-20iD/20 robot base placement and EOAT geometry for a structural beam coping cell. The work proceeds in five phases: establish the IK solver foundation (hard blocking gate), pre-compute all artifact tables in parallel, build and smoke-test the search pipeline, execute the 23-hour two-phase search run, then generate the full reporting and visualization package. Every phase delivers a verifiable capability before the next begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Solver Foundation** - OPW IK solver built, validated, and environment configured — hard blocking gate (completed 2026-04-17)
- [ ] **Phase 2: Pre-computation Artifacts** - Tool table, riser model, collision environment, and target database all generated and frozen
- [ ] **Phase 3: Search Pipeline** - Multiprocessing search workers built and verified with 100-cell smoke test
- [ ] **Phase 4: Full Search Execution** - Phase A (~18 hr) and Phase B (~5 hr) runs complete with Parquet results on disk
- [ ] **Phase 5: Reporting and Visualization** - Full scoring, report files, and URDF scene renders delivered

## Phase Details

### Phase 1: Solver Foundation
**Goal**: Developer can run validated FK->IK round-trips on the M-20iD/20 at >=4 us/query inside a reproducible environment
**Depends on**: Nothing (first phase)
**Requirements**: SOLV-01, SOLV-02, SOLV-03, SOLV-04, SOLV-05, ENV-01, ENV-02, ENV-03, LOG-01
**Success Criteria** (what must be TRUE):
  1. The OPW C++ pybind11 extension builds cleanly and achieves >=4 us/query on the i5-13600K host
  2. 500+ FK->IK round-trip tests pass with position error <0.01 mm and orientation error <0.01 deg
  3. Joint limit enforcement is verified for all six axes and all 8 OPW solution candidates
  4. All physical constants (geometry, budget sub-allocations, section properties) live in a single `config.py` with no magic numbers elsewhere
  5. All physical quantities printed by the optimizer appear in both Imperial and SI units
**Plans:** 2/2 plans complete

Plans:
- [x] 01-01-PLAN.md -- Environment setup, config.py, logging_utils.py (ENV-01, ENV-02, LOG-01)
- [x] 01-02-PLAN.md -- OPW solver wrapper, validation suite, multiprocessing spawn (SOLV-01-05, ENV-03)

### Phase 2: Pre-computation Artifacts
**Goal**: All pre-computed lookup tables and databases are generated, validated, and frozen on disk — ready to feed the search pipeline
**Depends on**: Phase 1
**Requirements**: TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05, TOOL-06, RISER-01, RISER-02, RISER-03, RISER-04, RISER-05, COLL-01, COLL-02, COLL-03, COLL-04, TARG-01, TARG-02, TARG-03, TARG-04, TARG-05
**Success Criteria** (what must be TRUE):
  1. `valid_tools.json` exists with ~1044 entries (wrist-load and boom-deflection filtered) and ~150-200 cluster representatives selected by TCP/CG/angle proximity
  2. `riser_validity_table.json` exists covering all (section, height) pairs with computed d_TCP, f1, and k_anchor sensitivity margin — pairs exceeding 0.55 mm deflection or below 15 Hz marked failed
  3. An FCL collision scene is initializable with static boundary walls, conveyor surface, ground plane, and any live AISC beam mesh verified watertight before insertion
  4. `target_database/` exists with per-shape pose files (straight-cut sweeps at 25 mm spacing and cope trajectories) and `beam_difficulty_ranking.json` sorted hardest-first — all files read-only frozen
**Plans**: TBD

### Phase 3: Search Pipeline
**Goal**: The multiprocessing search pipeline is built, instrumented, and proven correct on a 100-cell smoke test — ready for a long run without silent failure
**Depends on**: Phase 2
**Requirements**: SRCH-01, SRCH-03, SRCH-04, SRCH-07, SRCH-08, LOG-02
**Success Criteria** (what must be TRUE):
  1. A 100-cell Phase A smoke test completes and produces correct per-cell results matching manual verification
  2. Reach-fail and geometry-fail early termination paths are demonstrably distinct (a reach-fail exits remaining beams; a geometry-fail continues)
  3. Per-worker Parquet shards are written with atomic rename so a mid-run worker crash leaves all completed work intact
  4. A regression test confirms riser height is propagated into the base transform: same X/Y/yaw placement at H=0 vs H=914 mm produces different IK results
  5. Workers spawn with `spawn` start method and pass only plain Python dicts through the task queue — no pybind11 GIL corruption under load
**Plans**: TBD

### Phase 4: Full Search Execution
**Goal**: Phase A and Phase B grid searches complete successfully, producing Parquet results that fully cover the search space
**Depends on**: Phase 3
**Requirements**: SRCH-02, SRCH-05, SRCH-06
**Success Criteria** (what must be TRUE):
  1. Phase A completes (~180 representative tools x 29,280 placement configs) with results written to Parquet shards — no worker crashes lost
  2. Top-750 unique placements are selected from Phase A by reachability_pct descending then hardware_cost ascending
  3. Phase B completes (~1044 valid tools x top-750 placements) with cope feasibility check applied when reachability >= 95% — results written to Parquet
**Plans**: TBD

### Phase 5: Reporting and Visualization
**Goal**: Developer can inspect a complete set of result files — JSON reports, heatmaps, gap analysis, error budget, and URDF scene renders — for the optimal and top-10 configurations
**Depends on**: Phase 4
**Requirements**: SCOR-01, SCOR-02, SCOR-03, SCOR-04, SCOR-05, VIZ-01
**Success Criteria** (what must be TRUE):
  1. `best_config.json`, `top_10_configs.json`, and `passing_configs.json` exist and contain scored configurations with reachability_pct, manipulability_mean, hardware_cost, and tcp_error_estimate
  2. `reachability_heatmap.json`, `cope_report.json`, and `gap_report.json` exist and categorize every beam/face/pose failure by reach, geometry, or collision cause
  3. `error_budget_report.json` exists showing modeled contributors (riser column, baseplate, tool boom) alongside flagged unmodeled terms for each top-10 config
  4. `run_metadata.json` exists capturing wall-clock timing, grid dimensions, and per-filter rejection rates for the completed run
  5. URDF scene renders of the top-10 configs are generated showing robot, riser, tool, and workzone geometry
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Solver Foundation | 2/2 | Complete   | 2026-04-17 |
| 2. Pre-computation Artifacts | 0/TBD | Not started | - |
| 3. Search Pipeline | 0/TBD | Not started | - |
| 4. Full Search Execution | 0/TBD | Not started | - |
| 5. Reporting and Visualization | 0/TBD | Not started | - |
