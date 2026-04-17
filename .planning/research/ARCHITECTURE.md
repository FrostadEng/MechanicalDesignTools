# Architecture Patterns

**Domain:** Python-based robot reachability/placement optimizer, CPU-bound grid search with C++ extensions
**Project:** EDEN Cell Optimizer — Fanuc M-20iD/20 beam coping cell
**Researched:** 2026-04-16
**Confidence:** HIGH (derived directly from V3 spec + established Python/C++ patterns)

---

## Recommended Architecture

The system splits cleanly into two execution phases that must not be conflated:

**Pre-computation phase** (Steps 0-4): Produces frozen artifacts on disk. Runs once. Output is read-only during search. Each step depends on the previous.

**Search phase** (Steps 5-6): Consumes pre-computed artifacts. Parallel workers are stateless per-cell evaluators. Output is Parquet written per-worker then merged.

**Reporting phase** (Step 7): Reads Parquet, writes human-readable outputs. Single-process, no concurrency needed.

```
[Pre-computation] ──────────────────────────────────────────────────────
  OPW Solver (C++/pybind11)
       │
       ▼
  Tool Table Generator ──→ valid_tools.json
       │
       ▼
  Riser Pre-computer   ──→ riser_validity_table.json
       │
       ▼
  Collision Env Builder ──→ (in-memory scene defs, wall/conveyor planes)
       │
       ▼
  Target DB Generator  ──→ target_database/ (frozen Parquet/JSON)

[Search phase] ──────────────────────────────────────────────────────────
  Phase A Coordinator
       │ spawns 14 workers
       ├──→ Worker (cell evaluator) ──→ phase_a_worker_N.parquet
       ├──→ Worker (cell evaluator) ──→ phase_a_worker_N.parquet
       └──→ ...
       │ merge + rank
       ▼
  Top-500 Placement Selector ──→ top_500_placements.json

  Phase B Coordinator
       │ spawns 14 workers
       ├──→ Worker (cell evaluator) ──→ phase_b_worker_N.parquet
       └──→ ...
       │ merge + rank
       ▼
  Best Config Selector ──→ best_config.json, top_10_configs.json

[Reporting phase] ───────────────────────────────────────────────────────
  Report Generator
       │
       ├──→ reachability_heatmap.json
       ├──→ cope_report.json
       ├──→ gap_report.json
       ├──→ error_budget_report.json
       └──→ visualization/ (URDF scene renders)
```

---

## Component Boundaries

### Component 1: OPW Kinematic Solver (`solver/`)

**Responsibility:** Wraps the C++ OPW library via pybind11. Provides FK, IK, and joint-limit filtering. Validates round-trips.

**Communicates with:** Tool Table Generator (at startup), all search workers (at worker init, not per-call).

**Boundary rule:** This component has no business logic. It is a pure kinematic primitive. It knows nothing about beams, tools, placements, or scoring.

**Critical implementation note — pybind11 and multiprocessing:**

Python's `multiprocessing` module uses `fork` by default on Linux. `fork` copies the parent process memory including any already-imported C extension modules. This is generally safe for read-only C++ state, but the pybind11 module should be imported at the top of the worker module (not inside the worker function), so the import happens once in the forked child after it initializes. The preferred pattern is:

```python
# worker_module.py  ← imported by each spawned process
import opw_kinematics  # imported at module level, not inside the worker function

def evaluate_cell(cell_args):
    # opw_kinematics is already imported; no re-import cost
    solutions = opw_kinematics.inverse(pose, params)
    ...
```

Do NOT pickle/unpickle pybind11 objects across process boundaries. Pass plain Python data (dicts, numpy arrays) as cell arguments. The OPW parameter struct should be constructed once per worker from a plain dict, not shared as a C++ object via the queue.

**Confidence:** HIGH — this is the standard pattern for pybind11 + multiprocessing on Linux fork.

---

### Component 2: Tool Table Generator (`precompute/tool_table.py`)

**Responsibility:** Sweeps (torch_angle × boom_length × puck_drop), applies wrist load diagram, moment/inertia gates, boom deflection gate. Clusters survivors. Writes `valid_tools.json`.

**Communicates with:** OPW Solver (indirectly — needs TCP transform per tool). Nothing else.

**Inputs:** Torch puck STEP geometry constants (hardcoded or loaded from config), robot wrist load diagram boundaries (from datasheet, hardcoded or loaded).

**Outputs:** `valid_tools.json` — read by search workers, never written after this step completes.

**Boundary rule:** This component does not know about placements, beams, or the search grid. It only knows about the tool attached to the robot flange.

---

### Component 3: Riser Pre-computer (`precompute/riser_table.py`)

**Responsibility:** Closed-form superposition (column bending + baseplate rotation), modal frequency check. Builds lookup table of valid (section, height) pairs.

**Communicates with:** Nothing at runtime. Pure numerical computation. Reads section properties (hardcoded or from a materials config).

**Inputs:** 5 riser section properties, 8 discrete heights, robot mass, conservative anchor bolt stiffness.

**Outputs:** `riser_validity_table.json` — a simple dict mapping (section_id, height_mm) → bool. Used by search workers as a lookup, not recomputed per cell.

**Boundary rule:** This component has no dependency on IK, collision, or beams. It runs in seconds and is structurally independent of all search logic.

---

### Component 4: Collision Environment (`collision/scene.py`)

**Responsibility:** Manages python-fcl BVH collision objects. Provides two categories of objects:

1. **Static objects** (built once, reused for entire run): wall planes (X = ±515 mm), conveyor plane (Z = 838 mm), ground plane (Z = 0). These are FCL `Plane` or `Box` primitives loaded once at startup.

2. **Per-beam dynamic objects** (created per beam evaluation): beam mesh extruded from AISC cross-section, placed at datum roller position on conveyor surface. Added to scene before evaluating that beam's poses, removed (or replaced) for the next beam.

**Critical architecture decision — scene ownership per worker:**

Each multiprocessing worker must own its own FCL collision scene. python-fcl uses C++ objects internally and is not safe to share across process boundaries. The pattern is:

```python
# In worker initializer (called once per worker at pool startup)
def worker_init(static_scene_config):
    global _scene
    _scene = CollisionScene()
    _scene.build_static_objects(static_scene_config)

# In cell evaluator (called per cell)
def evaluate_cell(cell_args):
    beam_mesh = build_beam_mesh(cell_args.beam_id)
    _scene.set_active_beam(beam_mesh)   # replaces previous beam
    result = _scene.check(tool_mesh, robot_links)
    _scene.clear_active_beam()
```

The `static_scene_config` passed to the initializer must be a plain serializable dict (plane normals, offsets, dimensions) — not an FCL object.

**Communicates with:** Search Workers (owns scene), AISC beam database (reads cross-section geometry).

**Boundary rule:** Collision scene management is isolated from IK and scoring. The cell evaluator queries the scene with a tool+robot pose; the scene returns a boolean (collision / no-collision). No scoring logic lives here.

---

### Component 5: Target Database Generator (`precompute/target_db.py`)

**Responsibility:** Generates all beam pose sequences (straight-cut sweeps, cope trajectories). Applies clearance rules. Ranks beams by difficulty. Freezes everything to disk.

**Communicates with:** AISC beam database (queries cross-sections), Collision Environment (uses static scene to cull target points that immediately violate walls), nothing else.

**Outputs:** `target_database/` directory tree — JSON files per beam shape. Read-only during all search phases.

**Boundary rule:** Target generation is completely independent of robot placement. A target pose is a 6-DOF end-effector goal in world frame, independent of where the robot sits. The search engine applies the placement transform and queries IK.

---

### Component 6: Search Workers (`search/worker.py`)

**Responsibility:** Stateless cell evaluators. Each worker evaluates one (tool_id, base_x, base_y, base_yaw, riser_section, riser_height) cell and returns a scored result row.

**What a worker holds in memory (loaded once at init, never modified):**
- `valid_tools.json` contents as a list of dicts
- `riser_validity_table.json` as a lookup dict
- `target_database/` contents for all beams (loaded fully into RAM — ~hundreds of MB at most)
- Own FCL collision scene (static objects only)
- Imported pybind11 OPW module

**What a worker receives per cell (passed as plain serializable data):**
- (tool_id, base_x, base_y, base_yaw, riser_section, riser_height) — integers and floats only

**What a worker returns per cell:**
- A dict of scalar values (reachability_pct, manipulability_mean, hardware_cost, tcp_error_estimate, pass/fail flags). No C++ objects.

**Filter cascade (in order, cheapest first):**
1. Riser validity lookup (dict lookup, ~0 cost) — ~30% rejection
2. Geometric reach envelope (scalar distance, ~1 μs) — ~60% of remaining
3. 8-point IK spot check (~0.03 ms total) — ~20% of remaining
4. Full beam evaluation, reach-hardest-first, early termination (~0.35 s avg) — final scoring

**Early termination split (V3 refinement):** Workers track failure reason per beam. A "reach fail" (IK globally infeasible at this placement for this beam) triggers early exit. A "geometry fail" (IK works elsewhere but collision/joint-limit on specific faces) does not trigger early exit — continue to next beam.

---

### Component 7: Search Coordinators (`search/phase_a.py`, `search/phase_b.py`)

**Responsibility:** Builds the cell list, distributes to workers, collects results, writes per-worker Parquet files, merges to final Parquet, selects top-N outputs.

**Parquet strategy — write-per-worker then merge:**

This is the correct pattern for this workload. The alternative (queue-based single writer) introduces a serialization bottleneck that wastes CPU time on the i5-13600K. The recommended structure:

```python
# Each worker writes its own Parquet shard when it completes a batch
# (e.g., every 1000 cells, or at process exit)
def worker_write_shard(results_batch, worker_id, phase, shard_idx):
    path = f"results/{phase}_worker_{worker_id}_shard_{shard_idx}.parquet"
    table = pa.Table.from_pylist(results_batch)
    pq.write_table(table, path)

# Coordinator merges after all workers finish
def merge_phase_results(phase):
    shards = glob(f"results/{phase}_worker_*.parquet")
    tables = [pq.read_table(s) for s in shards]
    merged = pa.concat_tables(tables)
    pq.write_table(merged, f"results/{phase}_results.parquet")
```

Each worker writes to a unique path (worker_id + shard_idx) — no file locking needed. The merge step at coordinator level is fast (column concatenation) and runs once after the pool completes.

**Why not a queue-based single writer:** At ~0.35 s/cell and 14 workers, the writer would receive ~40 result dicts/second. This is trivially handleable, but the queue add/get round-trip adds latency per cell that compounds to hours over 190k cells. Write-per-worker eliminates this entirely.

**Communicates with:** Workers (via multiprocessing.Pool.imap_unordered), disk (Parquet shards).

---

### Component 8: Report Generator (`reporting/`)

**Responsibility:** Reads `phase_b_results.parquet`, generates all human outputs. Single-process. No concurrency.

**Outputs:** `best_config.json`, `top_10_configs.json`, `reachability_heatmap.json`, `cope_report.json`, `gap_report.json`, `error_budget_report.json`, URDF scene renders.

**Communicates with:** Parquet results (read), target database (read for gap analysis), URDF files (read for visualization).

**Boundary rule:** Reporting is purely transformational. It reads frozen data and writes formatted outputs. No recomputation.

---

## Data Flow

```
[Disk] valid_tools.json ──────────────────────────────────┐
[Disk] riser_validity_table.json ─────────────────────────┤
[Disk] target_database/ ──────────────────────────────────┤
                                                           │ (read at worker init)
                                                     ┌─────▼──────┐
                  [Coordinator: cell list] ──────────→│   Worker   │──→ result dict
                                                     └─────┬──────┘
                                                           │ (batched write)
                                                     [per-worker .parquet shard]
                                                           │
                                                     [merge step]
                                                           │
                                                   [phase_X_results.parquet]
                                                           │
                                                   [Report Generator]
                                                           │
                                              [JSON/heatmap/visualization outputs]
```

**Direction of data flow is strictly downward.** No component writes back to a higher-level artifact. Pre-computation outputs are write-once, read-many.

---

## Suggested Build Order

The dependency graph is mostly linear with one parallel opportunity (Tool Table and Riser Table are independent of each other):

```
Step 0: OPW Solver (C++/pybind11)
        └── BLOCKS: everything (IK used in tool table, target gen, and all search)

Step 1a: Tool Table Generator (depends on Step 0 for TCP transform validation)
Step 1b: Riser Pre-computer (independent of Step 0 — pure beam mechanics)
         (Steps 1a and 1b can be built in parallel)

Step 2: Collision Environment (depends on AISC beam database availability)
        (can be built in parallel with Steps 1a/1b)

Step 3: Target DB Generator (depends on Steps 0, 2)
        └── Needs collision scene to cull invalid poses
        └── Needs OPW to verify IK feasibility of pose types (optional but recommended)

Step 4: Search Worker (depends on Steps 0, 1a, 1b, 2, 3)
        └── Pulls in all pre-computation outputs
        └── This is the highest-value component — everything else feeds it

Step 5: Search Coordinators (depends on Step 4)
        └── Phase A coordinator: builds cell list over rep tools × full placement grid
        └── Phase B coordinator: builds cell list over all tools × top-500 placements

Step 6: Report Generator (depends on Step 5 outputs)
        └── Reads frozen Parquet; no search logic
```

**Implication for roadmap phases:** The natural phase boundaries are:

- **Phase 0 (solver):** Build and validate the C++ OPW solver with pybind11 wrapper. This is the hardest infrastructure piece and blocks everything. Validate FK→IK round-trips before moving on — a bad kinematic model invalidates all downstream results.
- **Phase 1 (pre-computation):** Build tool table, riser table, collision environment, target database sequentially (or in parallel for tool/riser). Each produces a frozen artifact that is unit-testable in isolation.
- **Phase 2 (search infrastructure):** Build the worker + coordinator skeleton with a minimal test grid before running the real 23-hour search. Verify Parquet writes/reads, filter cascade, and multiprocessing process lifecycle.
- **Phase 3 (full search runs):** Run Phase A and Phase B. These are execution phases, not build phases — infrastructure must be complete and validated first.
- **Phase 4 (reporting):** Generate all outputs from Phase B Parquet.

---

## Patterns to Follow

### Pattern 1: Worker Initializer for Shared Read-Only State

Load large read-only data (tool table, target database) once per worker at pool startup using `multiprocessing.Pool(initializer=..., initargs=...)`. Store in a module-level global. Never pass large data through the task queue.

```python
_tools = None
_targets = None
_scene = None

def worker_init(tools_path, targets_path, static_scene_config):
    global _tools, _targets, _scene
    import opw_kinematics  # pybind11 module — import here in worker context
    _tools = load_json(tools_path)
    _targets = load_target_database(targets_path)
    _scene = CollisionScene()
    _scene.build_static_objects(static_scene_config)

def evaluate_cell(cell):
    tool = _tools[cell['tool_id']]
    ...
```

**Why:** On Linux fork, the parent's memory is copy-on-write. If the worker only reads, the OS shares the physical pages across all 14 workers. Loading 200 MB of target data once in the parent (before the pool spawns) and letting fork copy-on-write is more memory-efficient than loading per-worker. However, loading in each worker initializer is safer and avoids fork-safety concerns with some C extensions — prefer per-worker load unless RAM is constrained.

### Pattern 2: Filter Cascade with Structured Early Returns

Implement each filter as a function returning `(passed: bool, reason: str)`. Compose in order from cheapest to most expensive. Log rejection reason per cell for diagnostics.

```python
def evaluate_cell(cell) -> dict:
    if not riser_validity[cell.section][cell.height]:
        return {'passed': False, 'reason': 'riser_deflection', 'score': None}

    if not geometric_reach_check(cell):
        return {'passed': False, 'reason': 'reach_envelope', 'score': None}

    if not spot_check_ik(cell):
        return {'passed': False, 'reason': 'spot_ik', 'score': None}

    return full_beam_evaluation(cell)  # expensive path
```

This structure makes filter rejection rates trivially measurable: count `reason` values in the result Parquet.

### Pattern 3: Beam Evaluation with Separated Failure Modes

The V3 early-termination refinement is architecturally important. The beam evaluator must track two counters per config:

- `reach_fail_count`: IK infeasible globally (placement too far/close for this beam's scale)
- `geometry_fail_count`: IK feasible elsewhere but collision/joint-limit on specific trajectory

Terminate early only when `reach_fail_count` triggers the threshold (e.g., 3 largest beams all fail on reach). Continue through geometry fails. Implement this as a named state machine, not inline boolean logic, so it is testable.

### Pattern 4: Per-Worker Parquet Shards

Each worker writes to `results/{phase}_worker_{pid}.parquet` using `pyarrow.parquet.write_table`. Workers never write to the same file. The coordinator's merge step runs serially after `pool.join()`. This eliminates all concurrency concerns for I/O.

Define a fixed schema for the result row (as a `pyarrow.schema`) before the run. Workers validate each result dict against this schema before writing. This catches data type mismatches early rather than at merge time.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Sharing C++ Objects Across Process Boundaries

**What:** Placing pybind11 objects (OPW solver instance, FCL scene, numpy arrays backed by C++ memory) in a `multiprocessing.Manager()` dict or passing them through a `Queue`.

**Why bad:** pybind11 objects are not pickle-safe by default. This causes either silent data corruption or hard crashes. On Linux, fork copies the memory space correctly, but serialization through a queue does not.

**Instead:** Import pybind11 modules per-worker. Construct C++ objects (OPW params, FCL scene) per-worker in the initializer. Pass only plain Python data (dicts, lists, numpy arrays of primitives) through the cell queue.

### Anti-Pattern 2: Reloading Target Database Per Cell

**What:** Opening and parsing beam JSON files inside `evaluate_cell()`.

**Why bad:** With ~190k full-evaluation cells × however many beams per cell, filesystem I/O dominates. A single W-shape JSON file parsed 190k times costs gigabytes of redundant I/O.

**Instead:** Load all target database files once in `worker_init()`. Keep the full beam → poses mapping in a module-level dict for the worker's lifetime.

### Anti-Pattern 3: Mixing Pre-computation and Search Logic

**What:** Computing riser deflection or tool clustering inside the search worker's cell evaluator.

**Why bad:** These computations are cell-independent. Recomputing them per cell wastes time and makes the worker harder to test. A deflection check that takes 1 ms per cell adds ~3 minutes to Phase A.

**Instead:** All pre-computation outputs are frozen artifacts. Workers only do lookups (O(1) dict access) against pre-computed tables.

### Anti-Pattern 4: Single-File Parquet Writer With Queue

**What:** A dedicated writer process that receives result dicts from a queue and writes them to a single `phase_a_results.parquet`.

**Why bad:** pyarrow's `ParquetWriter` can append rows, but the writer process becomes a throughput bottleneck. At ~40 results/second across 14 workers, the queue overhead is measurable at scale. More importantly, a writer crash loses all buffered results.

**Instead:** Per-worker shards + merge. Each shard is immediately durable on disk. A worker crash loses at most one shard's worth of cells, which can be rerun.

### Anti-Pattern 5: Flat Module Structure

**What:** All Python files in one directory or one large script.

**Why bad:** The pre-computation phase and search phase have completely different execution lifecycles, test strategies, and dependencies. Mixing them makes it impossible to run the tool table generator without importing the search coordinator.

**Instead:** See module structure below.

---

## Module / File Structure

```
eden_optimizer/
├── solver/
│   ├── build/                   # C++ build artifacts (CMake)
│   │   └── opw_kinematics.so    # compiled pybind11 extension
│   ├── opw_kinematics.cpp       # C++ OPW implementation + pybind11 bindings
│   ├── CMakeLists.txt
│   ├── opw_params.py            # M-20iD/20 OPW parameter constants + loader
│   └── validate.py              # FK→IK validation suite (run standalone)
│
├── precompute/
│   ├── tool_table.py            # sweeps tool space, writes valid_tools.json
│   ├── riser_table.py           # deflection + modal model, writes riser_validity_table.json
│   ├── target_db.py             # generates target_database/ tree
│   └── run_all.py               # orchestrates Steps 0-4 in sequence
│
├── collision/
│   ├── scene.py                 # CollisionScene class (FCL wrapper)
│   ├── beam_mesh.py             # builds FCL BVH from AISC cross-section
│   └── static_objects.py       # wall planes, conveyor, ground
│
├── search/
│   ├── worker.py                # worker_init() + evaluate_cell() — the core evaluator
│   ├── filters.py               # filter cascade functions (riser, envelope, spot IK)
│   ├── beam_eval.py             # full beam evaluation loop with reach/geometry split
│   ├── phase_a.py               # Phase A coordinator: builds grid, runs pool, merges
│   └── phase_b.py               # Phase B coordinator: builds grid, runs pool, merges
│
├── reporting/
│   ├── select_top.py            # reads Parquet, selects top-500 / top-10 configs
│   ├── heatmap.py               # reachability heatmap generation
│   ├── gap_report.py            # gap analysis: which beams/faces/poses fail, why
│   ├── error_budget.py          # RSS error budget report per config
│   └── visualize.py             # URDF scene renders of top-10 configs
│
├── data/
│   ├── valid_tools.json         # output of precompute/tool_table.py
│   ├── riser_validity_table.json
│   └── target_database/         # tree of beam JSON files
│
├── results/
│   ├── phase_a_worker_*.parquet  # per-worker shards
│   ├── phase_a_results.parquet   # merged Phase A output
│   ├── phase_b_worker_*.parquet
│   ├── phase_b_results.parquet   # merged Phase B output
│   ├── best_config.json
│   ├── top_10_configs.json
│   └── ...
│
├── config.py                    # all physical constants: wall positions, conveyor height,
│                                #   robot mass, joint limits, anchor bolt stiffness, etc.
│                                #   No magic numbers in module code.
└── run.py                       # top-level CLI: run_precompute, run_phase_a, run_phase_b,
                                 #   run_reports, or run_all
```

**config.py is load-bearing.** All physical constants (wall positions, conveyor height, robot specs, anchor bolt stiffness estimates, error budget allocations) must live here, never hardcoded in module bodies. This is the single source of truth for physical parameters and makes the system auditable against the V3 spec by comparing config.py to spec sections 2-8.

---

## Scalability Considerations

| Concern | Current (i5-13600K, 14 threads) | If more cores available | Notes |
|---------|--------------------------------|------------------------|-------|
| Phase A wall time (~18 hrs) | ~18 hrs at 14 threads | Linear speedup to ~32 cores | After ~32 cores, RAM bandwidth for target DB becomes limit |
| Phase B wall time (~5 hrs) | ~5 hrs at 14 threads | Linear speedup | 522k cells is embarrassingly parallel |
| Target DB RAM footprint | ~hundreds MB (estimate) | Same | All beams in AISC ≤300 lb/ft, 25 mm pose spacing — bounded |
| Parquet merge time | Seconds (columnar concat) | Seconds | Merge is not on the critical path |
| Riser table recompute | Seconds | Seconds | 5 sections × 8 heights = 40 pairs |
| Tool table recompute | Minutes | Minutes | ~6960 raw candidates, vectorizable with NumPy |

The architecture is embarrassingly parallel at the cell level. No shared mutable state between workers. Scaling to more cores requires only changing the `Pool(N)` argument. The target database RAM load is the practical memory limit.

---

## Sources

- EDEN Cell Optimizer V3 Specification (`Robot_Simulations/Optimizing_Robot_Placement.md`)
- EDEN Cell Optimizer PROJECT.md (`/.planning/PROJECT.md`)
- Established Python multiprocessing patterns for CPU-bound C extension workloads (HIGH confidence — standard CPython behavior on Linux)
- pybind11 documentation: fork safety, GIL, module import patterns (HIGH confidence — well-documented CPython/pybind11 behavior)
- pyarrow Parquet documentation: per-file write model, schema enforcement, concat_tables (HIGH confidence — standard pyarrow patterns)
- python-fcl architecture: C++ object ownership, no cross-process sharing (HIGH confidence — standard pattern for Python-wrapped C++ libraries)
