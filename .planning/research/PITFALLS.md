# Pitfalls Research

**Domain:** CPU-bound Python robot reachability optimizer with C++ extensions (OPW kinematics, python-fcl, multiprocessing, hierarchical grid search)
**Researched:** 2026-04-16
**Confidence:** HIGH (domain-specific; based on V3 spec analysis + established failure modes for OPW, pybind11, python-fcl, multiprocessing)

---

## Critical Pitfalls

### Pitfall 1: OPW Parameter Sign Convention Mismatch (Silent Wrong Answers)

**What goes wrong:**
The OPW solver returns solutions that pass FK→IK round-trips but are systematically offset in Cartesian space by 5–200 mm. The Fanuc M-20iD manual uses DH parameters measured from different reference frames than the opw_kinematics library expects (opw_kinematics uses a specific ortho-parallel convention from the Brandstotter paper). Parameters extracted directly from URDF joint origins without applying the correct sign and frame conventions produce a solver that appears to work — round-trips close — but the physical TCP is wrong because the base FK frame is inconsistent with the OPW frame assumed at IK evaluation time.

**Why it happens:**
The `a1`, `a2`, `c1`–`c4` parameters must be measured in the OPW-paper convention, not the URDF joint origin convention. The URDF places joint frames at the parent link origin; OPW places the measurement at the child joint center. For the M-20iD/20, the J2 horizontal offset `a1` is commonly mis-extracted as the J1-to-J2 horizontal offset rather than the base-to-J2-center horizontal distance. A 75 mm error here propagates to >75 mm reach error at full extension.

**How to avoid:**
1. Extract OPW parameters from Fig 3.2a (operating space diagram) in manual B-84074EN/03 by measuring the diagram coordinates directly, not from URDF joint origins.
2. After parameter extraction, run the FK→IK round-trip suite (Section 11C of spec) with 500+ random configs spanning the full joint range, not just near home.
3. Add a known-pose test: move robot to a physical teaching point (or use manual Fig 3.2a boundary points like full extension at J2=J3=0) and verify FK output matches the expected Cartesian coordinate within 1 mm.
4. Cross-check: verify that `c2 + c3 + c4 = 1831 mm` (max reach) ± link geometry corrections.

**Warning signs:**
- Round-trips pass at tight tolerance (< 0.1 mm) but reachability is implausibly low (< 50%) for a robot clearly able to reach the conveyor.
- Phase A results show maximum reachability clustering at exactly 3 of the 4 yaw orientations — suggests the base frame transform is wrong for one quadrant.
- IK returns solutions for poses that are geometrically impossible (TCP behind the robot base).

**Phase to address:**
Step 0 (OPW solver validation, before any grid search). This is a blocking correctness issue.

---

### Pitfall 2: OPW Returns 8 Solutions — Wrong Solution Filtered as "No IK"

**What goes wrong:**
The OPW solver returns up to 8 analytical solutions per pose. The joint-limit filtering step rejects solutions outside M-20iD/20 limits. When the filtering is done as a simple `all([lower <= q <= upper for q, lower, upper in zip(sol, lowers, uppers)])` check, off-by-one handling of the ±180° wrap-around on J1 (±170°) and the asymmetric J2/J3 limits causes valid solutions near limits to be incorrectly rejected. The pose is then marked "unreachable" even though a valid solution exists.

**Why it happens:**
The OPW library returns joint angles in radians. Limit checks done in degrees without consistent conversion, or with closed vs. open interval ambiguity at the boundary value (e.g., `q <= upper` vs. `q < upper`), cause edge-case rejections. The M-20iD/20 J3 has an asymmetric range (−190° to +268.4°), which is wider than the symmetric ±180°; if the filter naively clips to ±π, valid J3 solutions in the 180°–268° range are dropped.

**How to avoid:**
1. Store all joint limits in radians at init time. Never convert inside the hot path.
2. Use `lower - eps <= q <= upper + eps` with a small epsilon (0.001 rad) to avoid floating-point boundary rejections.
3. Write an explicit test: for a pose at full extension with J3 = +240° (within limits), verify that the solver returns and keeps at least one solution.
4. Log the filter rejection reason per solution per pose during validation — if "out of limits" accounts for > 40% of rejections during spot checks, the filter has a bug.

**Warning signs:**
- Phase A spot-check filter (8-point IK) rejects cells at known reachable positions (e.g., directly in front of robot at 900 mm distance at conveyor height).
- Reachability heatmap shows surprising "stripes" of failure in the middle of the robot's operating envelope.
- Round-trip validation passes but operating space diagram coverage < expected (~1831 mm radius).

**Phase to address:**
Step 0 (OPW solver validation). Verify limit filtering before any grid evaluation.

---

### Pitfall 3: pybind11 Extension Imported Before `multiprocessing.Pool` Fork — GIL State Corruption

**What goes wrong:**
On Linux with `fork`-based `multiprocessing`, importing the pybind11 OPW extension module in the main process before `Pool()` is created causes child workers to inherit a copy of the GIL state and the C++ global objects (static solver instance, any heap-allocated data structures). If the C++ extension holds a `std::mutex`, `std::atomic`, or any POSIX thread state (even implicitly via `pthread_atfork`), the forked child can deadlock or produce silently incorrect results when it invokes the extension.

**Why it happens:**
`fork()` copies the parent process including any locked mutexes mid-operation. pybind11 itself is safe for this in simple cases, but any C++ global state initialized at module import (common in OPW wrappers that pre-allocate solver objects) is inherited in potentially inconsistent state. On systems where the allocator has fork-unsafe state (glibc's `malloc` with thread arena locks), even object allocation in the child after fork can deadlock.

**How to avoid:**
1. Use `multiprocessing.Pool` with `mp.set_start_method('spawn', force=True)` instead of default `fork`. Spawn creates a fresh Python interpreter in each worker, eliminating inherited C++ state. Cost: ~0.3–0.5 s per worker startup (one-time at pool creation, not per task).
2. If spawn is unacceptable for startup overhead, import the pybind11 module **inside** the worker initializer function (`initializer=` argument to `Pool`), not at module level in the main process.
3. Never use `Pool` with `fork` and shared C++ objects that hold OS-level synchronization primitives.

**Warning signs:**
- Workers hang indefinitely on first call to the OPW solver with no output — deadlock on a forked mutex.
- Intermittent incorrect IK results that vary by worker index but not by input — inherited RNG or solver state divergence.
- `strace` on a stuck worker shows `futex(FUTEX_WAIT)` with no corresponding waker.

**Phase to address:**
Step 5 (Phase A grid search). Must be tested with `spawn` mode before any long run. Write a 100-cell smoke test that checks result reproducibility across 14 workers.

---

### Pitfall 4: python-fcl Coordinate Frame — Transform Applied in World Frame When Collision Object Moves

**What goes wrong:**
python-fcl `CollisionObject.setTransform(T)` sets the object's transform in the **world frame**. A common mistake is composing transforms relative to the previous object frame and calling `setTransform` with the relative transform. This produces incorrect collision geometry — the beam mesh appears at the wrong position/orientation in the collision scene, and the checker either produces false positives (collision reported when tool is clear) or false negatives (no collision reported when tool actually intersects beam).

**Why it happens:**
The FCL C++ API operates on world-frame transforms, but the conceptual model of "move this object relative to where it was" is natural in robotics. When the active beam changes (new beam loaded per evaluation), the beam mesh is repositioned to `(datum_y=0, Z=838mm)` in world frame, but if the code applies a delta transform instead of the absolute world-frame transform, the beam drifts with each evaluation call. After 100 beam evaluations in a Phase A cell, the beam mesh is ~100 beam-widths from where it should be.

**How to avoid:**
1. Every call to `setTransform` must supply an absolute world-frame transform, not a relative one. Build `T_world_beam` fresh from scratch using the beam's global datum position — never accumulate transforms.
2. Assert beam mesh position after `setTransform`: `assert abs(beam_obj.getTranslation()[2] - 0.838) < 0.001` before any collision check.
3. Write a unit test: place a simple box mesh at a known world position, check collision with a sphere at that same position. Confirm collision is detected. Move sphere to a position 200 mm away and confirm no collision.

**Warning signs:**
- Phase A shows 0% beam-collision rejections across all cells, even for tools with very long booms — false negatives.
- Alternatively, 100% collision rejection regardless of robot placement — false positives.
- Running the same cell twice returns different collision results — transform state is mutated between calls.

**Phase to address:**
Step 3 (collision environment setup). Add collision correctness tests before Step 4 (target generation) depends on collision filtering.

---

### Pitfall 5: python-fcl Mesh Winding / Convex Decomposition Requirement Ignored

**What goes wrong:**
python-fcl's `BVHModel` for mesh collision requires the mesh to be **watertight** (all faces with consistent outward normals, no open edges, no T-intersections). AISC beam profiles extruded with `trimesh.extrude_polygon` or similar tools sometimes produce meshes with inverted face normals on end caps, or open edges where the extrusion doesn't properly close. FCL's BVH builder silently accepts the broken mesh, but the distance/collision query returns wrong results (object appears to have zero volume from inside, or reports distance=0 everywhere).

**Why it happens:**
The extrusion workflow creates vertices and faces programmatically. If the polygon points are wound clockwise in XY before extrusion and the extrusion library doesn't fix normals, the resulting mesh has inverted normals on lateral faces. FCL treats inside as outside, reporting no collision when the TCP is inside the beam flange.

**How to avoid:**
1. After constructing each beam mesh, call `mesh.is_watertight` and `mesh.is_winding_consistent` (trimesh attributes). Assert both are True. Fail loudly if not — fix the extrusion, don't proceed.
2. For non-convex beam profiles (W, C, S sections with re-entrant flanges), use convex decomposition (HACD/VHACD) via `trimesh.decomposition.convex_decomposition`. FCL handles non-convex shapes better through a convex hull set than a single non-convex BVH.
3. For simple wall planes, use FCL's `Box` primitive — not a mesh. Boxes are exact, require no winding checks, and are faster.

**Warning signs:**
- Collision check reports no collision even when two meshes visually overlap in the URDF scene render.
- `mesh.is_watertight` returns False for any beam section — stop and fix before grid search.
- Distance queries return 0.0 for all pairs regardless of position.

**Phase to address:**
Step 3 (collision environment setup). Validate every beam mesh before freezing the target database (Step 4).

---

### Pitfall 6: TCP Transform Chain — Riser Height Changes Base-to-World Transform, Not Detected

**What goes wrong:**
The robot base is placed at world position `(base_x, base_y, riser_height)` with yaw rotation `base_yaw` about Z. The TCP pose at the workpiece must be evaluated in the **world frame**. If the IK is called with the target pose in the world frame but the robot base transform is not correctly composed into the IK call, the riser height is effectively ignored. The optimizer then scores all riser heights identically (the IK sees the same world-frame target but uses a base transform frozen at `riser_height=0`), and the riser height dimension of the search space becomes meaningless.

**Why it happens:**
IK solvers take target poses in the robot base frame, not world frame. The conversion is: `T_base_target = T_world_base.inv() @ T_world_target`. If `T_world_base` is computed once at program startup and not recomputed per (riser_section, riser_height, base_x, base_y, base_yaw) combination, only the most recently computed base transform is used. In Python, this often appears as a global or module-level `T_base = compute_base_transform(default_config)` that is never updated inside the inner loop.

**How to avoid:**
1. The base transform must be a **parameter of the inner evaluation function**, computed fresh from `(base_x, base_y, riser_height, base_yaw)` on every cell. Never use a cached global.
2. Write a parametric test: fix all beam targets; vary only `riser_height` from 0 to 1219 mm; verify that reachability changes monotonically (shorter risers reach lower beam faces better, taller risers reach higher web faces better). If reachability is identical across all 8 riser heights, the bug is present.
3. Log `T_world_base` for the first 5 cells of a test run and inspect the translation Z value — it should vary with riser height.

**Warning signs:**
- Phase A results show identical reachability scores across all 8 riser heights for every (X, Y, yaw, section) combination.
- The parquet file has no variance in `reachability_pct` along the `riser_height` dimension.
- The "best" riser height is always 0 (floor mount) regardless of beam size — likely means the base transform has riser height stuck at 0.

**Phase to address:**
Step 5 (Phase A grid search). Must be caught by the parametric riser-height regression test before the 18-hour run starts.

---

### Pitfall 7: Hierarchical Search Phase A Cluster Representative Not Representative — Phase B Misses Valid Configs

**What goes wrong:**
Phase A uses one tool per cluster (the "median boom_length within cluster") to find good placements. If the cluster representative's TCP position is at the cluster boundary rather than the centroid, Phase A may score a placement as "unreachable" for a tool that the actual cluster centroid would reach. Those placements are dropped from the top-500 list. Phase B never sees them. The final optimizer result is missing valid (tool, placement) pairs.

**Why it happens:**
5 mm clustering on a 6D feature vector (TCP_x, TCP_y, TCP_z, CG_x, CG_y, torch_angle) produces clusters where the "median boom_length" member may not be the centroid in TCP space. For clusters near the edge of the valid tool space (e.g., maximum boom length before deflection rejection), the representative is systematically the shortest surviving tool in the cluster, which has a shorter reach than the cluster centroid. The cluster was designed to reduce compute; using a non-centroid representative introduces a bias toward conservatively short tools.

**How to avoid:**
1. Select the cluster representative as the tool **closest to the cluster centroid in the 6D feature vector** (Euclidean distance after normalizing units), not the median boom_length member. These are different when the cluster is elongated along the boom_length axis.
2. Before the 18-hour Phase A run, run a calibration: for 10 random placements, compare reachability scores using the centroid-closest representative vs. three other cluster members. If the spread is > 5 percentage points, tighten the cluster radius to 3 mm.
3. Phase A's top-500 cutoff should use a buffer: take the top-750, then in Phase B score all of them and keep the best 500 at the end. The extra 250 Phase B evaluations cost ~25 minutes and protect against cluster boundary errors.

**Warning signs:**
- Phase B best config shows a significantly different tool cluster than Phase A's top-1 predicted.
- Phase B gap report shows unreachable beams that Phase A had marked as reachable at the same placement.
- Multiple Phase B placements in the top-500 achieve lower scores than Phase A predicted — systematic over-prediction.

**Phase to address:**
Step 1 (tool design table + clustering) and Step 5 (Phase A). Fix clustering before Phase A runs; adjust top-N cutoff before Phase B runs.

---

### Pitfall 8: Early Termination on Geometry Failure Drops 99%-Coverage Configs (V2 Bug Reintroduced)

**What goes wrong:**
The V3 spec explicitly separates "reach-fail" (terminate) from "geometry-fail" (continue). If the early termination logic is implemented as a simple `fail_count > threshold` check without distinguishing failure type, a placement that fails W36×300 due to wrist singularity (geometry-fail) is terminated and never scored on the 200 lighter beams it can reach. It appears as 0% reachability in Phase A and is not promoted to Phase B. The actual optimal placement may be excluded.

**Why it happens:**
The "reach-hardest-first" ordering puts large beams first. An early termination condition on "any fail among the first N beams" is a natural-sounding optimization. The spec's distinction between reach-fail (IK fails for ALL poses on a beam, meaning the robot simply cannot reach that distance) and geometry-fail (IK succeeds at some poses, but collision or joint-singularity blocks specific faces) requires per-pose IK result classification, which is easy to skip under time pressure.

**How to avoid:**
1. Implement an explicit `FailureMode` enum: `REACH_FAIL` (zero IK solutions anywhere on the beam), `GEOM_FAIL` (some IK solutions exist but collision or joint limit blocks the specific trajectory). Only `REACH_FAIL` on the N largest beams triggers early termination.
2. Add an assertion: after Phase A completes, verify that no placement in the top-500 has a `reach_fail_count` = 0 paired with very low reachability. If so, the geometry-fail path is incorrectly triggering reach-fail termination.
3. Smoke test: construct a placement that is known to fail W36×300 due to singularity but clearly reaches W8×10. Run Phase A on it and confirm it gets a non-zero reachability score.

**Warning signs:**
- Phase A output has a bimodal reachability distribution: many cells at ~100% and many at exactly 0%, with almost nothing in between. Should be a smooth distribution if geometry-fails are handled correctly.
- The gap report for the best config shows only large beams failing — if it also shows small beams failing with "no IK", the termination is prematurely cutting off evaluation.
- Runtime is suspiciously fast (e.g., Phase A completes in 4 hours instead of 18) — most cells are being terminated early.

**Phase to address:**
Step 5 (Phase A). The early termination logic must be correct before the long run. Add the smoke test in Step 4 (after target generation).

---

### Pitfall 9: Python `multiprocessing.Pool` Worker Crash Silent — Result Queue Never Receives Entry, Pool Hangs

**What goes wrong:**
When a worker process raises an unhandled exception (segfault in the C++ extension, OOM kill, unexpected SIGKILL from the OS), the `Pool.map` or `Pool.imap_unordered` call hangs indefinitely waiting for a result that will never arrive. With 14 workers and a 23-hour run, a single worker crash at hour 17 causes the entire run to hang rather than completing with a partial result.

**Why it happens:**
Python's `multiprocessing.Pool` does not have a built-in timeout for individual tasks. `imap_unordered` with no `chunksize` blocks the main process on the result iterator. If the worker process exits without putting a result in the queue, the iterator never advances for that item and blocks forever.

**How to avoid:**
1. Use `Pool.imap_unordered` with an explicit per-task timeout via `concurrent.futures.ProcessPoolExecutor` (which has `as_completed` with timeout) rather than raw `multiprocessing.Pool`. Or implement a watchdog thread that monitors worker liveness via `Pool._pool` and restarts dead workers.
2. Checkpoint results to Parquet incrementally (every 1000 cells or every 30 minutes), not only at the end. Use `pyarrow.parquet.ParquetWriter` in append mode. A crashed run can be resumed from the last checkpoint.
3. Catch all exceptions in the worker function and return a sentinel `result = {'status': 'ERROR', 'cell_id': cell_id, 'error': str(e)}` rather than raising. The main process then logs the error and continues.
4. Use `maxtasksperchild=500` on `Pool` to recycle workers periodically, preventing memory growth from accumulating over thousands of tasks per worker.

**Warning signs:**
- Run progress stops updating after a period of steady output — a worker may have died.
- Memory usage on any single process grows monotonically (use `ps aux` or `htop` to monitor per-worker RSS).
- `dmesg | grep -i kill` shows OOM killer events.

**Phase to address:**
Step 5 (Phase A). Implement checkpointing and crash isolation before the 18-hour run. Test by artificially killing one worker mid-run and verifying the run recovers.

---

### Pitfall 10: Parquet Partial Write on Crash — Corrupted File Silently Loaded as Valid

**What goes wrong:**
If the Phase A run writes `phase_a_results.parquet` as a single file using `pyarrow.parquet.write_table()` and the process is killed mid-write, the resulting file has a partial footer. When Phase B tries to load it with `pd.read_parquet()`, pyarrow may raise an exception, or worse — silently read only the rows written before the incomplete footer, producing a phase_a_results set smaller than expected. Phase B then runs on an incomplete top-500 list, potentially missing the true optimal placement.

**Why it happens:**
Parquet files are written with a file-level footer that is appended last. If the write is interrupted, the footer is missing or truncated. `read_parquet` with default settings (`use_legacy_dataset=False`) will attempt footer reading and may raise a cryptic error like `ArrowInvalid: Parquet file size is 0 bytes`. But some versions of pyarrow fall back to partial reading without warning.

**How to avoid:**
1. Use `ParquetWriter` in append mode with explicit `write_row_group()` calls in batches of ~1000 rows. Each row group has its own metadata, so partial writes are recoverable to the last complete row group.
2. Write to a temp file (`phase_a_results.parquet.tmp`), then atomically rename to `phase_a_results.parquet` only after `writer.close()` succeeds. This prevents a partial file from ever having the production filename.
3. After every write, read back the file and verify `len(df) == expected_row_count`. Log a warning if the count is wrong.
4. Pre-flight disk space check: estimate total parquet size (1.19M rows × ~200 bytes/row ≈ 240 MB for Phase A; 522k rows × ~300 bytes/row ≈ 157 MB for Phase B) and verify available space is at least 5× this before starting.

**Warning signs:**
- `phase_a_results.parquet` exists but has a file size much smaller than expected (< 50 MB suggests truncation).
- `pyarrow.parquet.read_metadata(path)` raises an exception.
- Phase B's top-500 list contains fewer than 500 unique placements even though Phase A appeared to run to completion.

**Phase to address:**
Step 5 and Step 6. Implement incremental checkpointing and atomic rename pattern before any long run.

---

### Pitfall 11: Coordinate Frame — Robot Yaw Rotation Applied Before Translation or After (Order Matters)

**What goes wrong:**
When constructing `T_world_base` from `(base_x, base_y, riser_height, base_yaw)`, the order of rotation and translation in the homogeneous transform matters. "Rotate the robot by yaw, then place it at (base_x, base_y, riser_height) in world frame" produces a different transform than "place it first, then rotate about its own Z axis." The correct interpretation is: the robot is placed at world position (base_x, base_y, riser_height) with its base frame rotated by base_yaw about the world Z axis (the robot's Z axis at its mounted position). This is `T = Translate(base_x, base_y, riser_height) @ RotateZ(base_yaw)`.

**Why it happens:**
The common mistake is using `RotateZ(base_yaw) @ Translate(base_x, base_y, riser_height)`, which rotates the translation vector — placing the robot at a world position that rotates around the world origin by base_yaw. At base_yaw=0, both are identical. At base_yaw=90°, the robot is placed at world position (-base_y, base_x, riser_height) instead of (base_x, base_y, riser_height). With base_y = 1612 mm, this places the robot 1612 mm in the -X direction — outside the workzone — and reachability collapses to ~0% for yaw=90°, yaw=180°, yaw=270°.

**How to avoid:**
1. Test explicitly: for base_x=0, base_y=1612, yaw=90°, verify that the robot base world-frame position is still at Y=1612 (not at X=-1612). `assert abs(T[1,3] - 1.612) < 0.001`.
2. Document the convention in a module docstring and a constants file — "base_yaw is rotation of robot body about its own vertical axis; translation is always in world frame."
3. Run the 4-yaw smoke test: all 4 yaw values at the same (X, Y) placement should produce non-zero reachability for a beam directly in front of the original robot home position.

**Warning signs:**
- Phase A results show reachability ≈ 0% for yaw values other than 0° across all placements.
- The world-frame robot base position changes when base_yaw changes (log T_world_base[:3,3] for the 4 yaw values at fixed X,Y — it should be identical across all 4).

**Phase to address:**
Step 5 (Phase A). The transform construction must be verified in Step 0 as part of the IK validation suite.

---

### Pitfall 12: k_anchor Conservative Estimate Accepts (Section, Height) Pairs That Fail on Hardware

**What goes wrong:**
The baseplate rotation stiffness uses `k_anchor ≈ 1.5×10⁶ N·m/rad` (conservative estimate from spec). If the actual installed k_anchor is lower (e.g., under-torqued anchor bolts, soft grout, thin baseplate), the real δ_baseplate is larger than modeled. A (section, height) pair that just barely passes the 0.55 mm deflection gate in simulation may fail by 0.3 mm on hardware. Since deflection gate pruning happens before Phase A, these pairs are kept in the search and appear in the top-10 results. Hardware validation then rejects them.

**Why it happens:**
The k_anchor estimate is inherently uncertain without a physical mockup test. The spec correctly flags this as a known limitation but sets `k_conservative = 1.5×10⁶ N·m/rad` without any safety margin applied to the gate threshold. The error budget has a 0.25 mm allocation for baseplate rotation, but if k_anchor is 2× softer than assumed, the actual contribution is 0.50 mm — consuming the entire riser deflection budget from one source alone.

**How to avoid:**
1. Apply a 1.5× uncertainty factor to the deflection gate specifically for configurations where δ_baseplate > 0.15 mm: use an effective gate of `δ_baseplate × 1.5 ≤ 0.25 mm` for uncertain cases. This builds in a margin against k_anchor softness.
2. Flag any top-10 config with computed δ_baseplate > 0.18 mm in `error_budget_report.json` with a "HIGH UNCERTAINTY — mockup test required" note.
3. When building the deflection model, test sensitivity: `d(δ_baseplate)/d(k_anchor)` at the nominal value. Report this sensitivity in the error budget report so hardware team knows what to measure.

**Warning signs:**
- Top-10 configs all use riser heights ≥ 762 mm (tall risers have larger moments, higher δ_baseplate sensitivity to k_anchor).
- The error budget report shows δ_baseplate > 0.20 mm for multiple top-10 configs.
- Hardware laser tracker shows TCP error 0.4–0.8 mm larger than modeled for tall risers — the excess is likely baseplate contribution.

**Phase to address:**
Step 2 (riser deflection model). Build in the k_anchor uncertainty margin before computing validity tables.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use forked `multiprocessing.Pool` instead of `spawn` | Faster worker startup | Potential silent C++ GIL/mutex corruption from pybind11 state | Never — use `spawn` |
| Cache `T_world_base` as module-level global | One less function parameter | Riser height dimension of search space silently ignored | Never — always pass as parameter |
| Skip `mesh.is_watertight` assertion on beam meshes | Faster target generation | FCL returns wrong collision answers silently | Never — assert at generation time |
| Use flat parquet write instead of incremental `ParquetWriter` | Simpler code | Entire 18-hour run lost on crash | Never for runs > 1 hour |
| Use `median_boom_length` as cluster representative | Simpler selection logic | Cluster may be non-centrally represented, causing Phase A misses | Acceptable only if Phase B top-N buffer is ≥ 1.5× Phase A's top-N |
| Skip FK→IK round-trips beyond 100 samples | Faster validation setup | OPW parameter errors undetected; wrong results throughout grid | Never — run 500+ before any grid search |
| Apply joint limit check in degrees (with conversion per call) | Readable code | Floating-point conversion error accumulates; edge-case rejections | Never — store and check in radians always |
| Write phase_a_results.parquet in one batch at end | Simpler code | All results lost on crash after hour 17 | Never for Phase A; consider for Phase B (shorter) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OPW pybind11 wrapper | Import module at Python startup before Pool creation | Import inside worker initializer with `spawn` start method |
| python-fcl `CollisionObject.setTransform` | Pass relative transform (delta from previous position) | Always pass absolute world-frame transform; rebuild from scratch per beam |
| python-fcl `BVHModel` construction | Use non-watertight extruded polygon mesh | Assert `is_watertight` and `is_winding_consistent`; use convex decomposition for W/C/S sections |
| AISC `aisc.py` cross-section lookup | Assume all shapes return consistent units (mixed inch/mm in source) | Normalize all outputs to SI (meters) at the database boundary; assert unit consistency |
| pyarrow `write_table()` | Write full table at end of run | Use `ParquetWriter` with row groups + atomic rename on close |
| `multiprocessing.Pool(14)` on i5-13600K | Use all 14 threads including E-cores as equal workers | E-cores are slower; optionally pin workers to P-cores for predictable timing, or accept variance in per-task time |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Pure Python OPW fallback left in codebase | Phase A runtime 10× over estimate (180+ hours) | Assert at startup that C++ OPW extension is loaded; fail fast if pure Python path is taken | Immediately — the 4 μs vs. 40 μs difference is decisive for 1.19M cells |
| FCL collision check called on every IK pose (not just valid IK solutions) | Phase A filter stage 4 runs much slower than 0.35 s/cell | Only call FCL on poses where IK returned at least one valid joint config | When per-beam pose count > 50 (most W-sections) |
| Parquet file read into memory for each Phase B evaluation | Memory exhaustion with Phase A's 1.19M row result | Load phase_a_results once, extract top-500 placements once, hold in memory as list | When RAM < 32 GB |
| Target database loaded from disk per worker per cell | I/O bottleneck; 14 workers hammering disk simultaneously | Load target database once in worker initializer (`initializer=` kwarg), store in process-local variable | At > 4 workers if database is > 500 MB |
| TCP transform recomputed from scratch per IK call (matrix multiply chain) | Inner loop slower than expected | Pre-compute tool TCP transforms for all ~1044 tools once at startup; look up by tool_id | At Phase B scale (522k evaluations) |

---

## "Looks Done But Isn't" Checklist

- [ ] **OPW solver:** FK→IK round-trips pass, but operating space envelope not verified against Fig 3.2a. A solver can round-trip correctly on random poses within ±45° of home but fail at J3 extremes. Verify: generate poses at the known maximum reach boundary and confirm IK returns at least one solution.
- [ ] **Collision environment:** Wall planes and conveyor plane added to FCL scene. Active beam mesh per evaluation NOT added (the V3 requirement). Verify: confirm `scene.addObject(beam_mesh)` is called inside the per-beam evaluation loop, not just once at startup.
- [ ] **Error budget report:** `tcp_error_estimate` field in parquet contains only riser + tool contributions. Unmodeled terms (thermal, beam positioning, cable reaction) are NOT included. Report correctly flags them as "unmodeled." Verify: check that `error_budget_report.json` explicitly lists unmodeled terms with their spec-assigned allocations.
- [ ] **Riser validity table:** Computed from worst-case load (robot at full extension, max tool mass). If computed at robot home position, all tall risers pass — verify the table uses the worst-case gravity load condition.
- [ ] **Phase A top-500 placements:** Selected as unique (base_x, base_y, base_yaw, riser_section, riser_height) tuples. If accidentally selected as (tool_cluster, base_x, base_y, base_yaw, riser_section, riser_height), Phase B sees non-unique placements and duplicates work. Verify: assert `len(set(top_500_placements)) == 500` on the deduplicated tuple key.
- [ ] **Dual-unit logging:** Logs emit both Imperial and SI for all length/force/mass values. Verify by inspecting a sample log line — it should have both "mm" and "in" (or "kg" and "lb") annotations. Missing one unit system means field team cannot verify against their tooling.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| OPW parameter error discovered after Phase A completes | HIGH | Re-extract parameters from Fig 3.2a, re-run full validation suite, re-run Phase A (~18 hours) |
| Phase A parquet file corrupted on crash | MEDIUM if checkpointed, HIGH if not | If checkpointed: resume from last checkpoint row group. If not: re-run from scratch. |
| Cluster representative non-centrality causes Phase B to miss optimal | MEDIUM | Re-run Phase A with centroid-closest representatives + top-750 buffer; Phase B on full 750 set |
| python-fcl mesh winding error caught after Phase A | MEDIUM | Re-build beam meshes with winding correction, re-run target generation, re-run Phase A |
| Base transform bug (riser height not propagating) caught after Phase A | HIGH | Fix transform function, re-run Phase A entirely — results are invalid |
| Worker crash hang discovered mid-run | LOW if crash isolation in place | Kill hung pool, load checkpoint, restart from last saved row group |
| k_anchor too optimistic — top hardware configs fail validation | MEDIUM | Re-run deflection model with measured k_anchor from mockup, re-prune validity table, re-run Phase B on new valid set (cheaper than Phase A) |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| OPW parameter sign convention mismatch | Step 0 (solver validation) | 500 FK→IK round-trips + known-pose test + operating space envelope check |
| Joint limit off-by-one at boundary | Step 0 (solver validation) | Explicit J3=+240° solution retention test |
| pybind11 GIL fork corruption | Step 5 (Phase A setup) | 100-cell smoke test with `spawn` mode, 14 workers, result reproducibility check |
| FCL world-frame transform error | Step 3 (collision environment) | Beam-at-known-position collision unit test |
| FCL mesh winding / non-watertight | Step 3 / Step 4 (target generation) | `is_watertight` assertion on every beam mesh before freeze |
| TCP transform chain missing riser height | Step 0 + Step 5 | Parametric riser-height regression test before Phase A |
| Phase A cluster representative non-centroid | Step 1 (tool clustering) | Phase B top-N buffer ≥ 1.5×; centroid-closest selection algorithm |
| Early termination confusion reach vs. geometry | Step 5 (Phase A logic) | Smoke test: known geometry-fail beam doesn't zero out small-beam reachability |
| Pool worker crash hang | Step 5 (Phase A infrastructure) | Artificial worker kill test; verify checkpoint recovery |
| Parquet partial write corruption | Step 5 / Step 6 | Atomic rename pattern; row-count verification after each write |
| Robot yaw transform order error | Step 0 + Step 5 | 4-yaw world-position assertion test |
| k_anchor uncertainty accepting marginal configs | Step 2 (riser deflection) | 1.5× uncertainty margin on δ_baseplate gate; sensitivity analysis in report |

---

## Sources

- V3 spec Section 19 (Known Limitations) — starting context for V3-acknowledged limitations
- V3 spec Section 11 (IK Solver Setup) — OPW parameter extraction guidance and validation requirements
- V3 spec Section 6 (Riser Deflection Model) — baseplate k_anchor estimate and uncertainty flag
- V3 spec Section 10 (Two-Phase Hierarchical Grid Search) — Phase A/B design and clustering
- V3 spec Section 5E (Tool Clustering) — representative selection criteria
- Brandstotter, Angerer, Hofbaur: "An Analytical Solution of the Inverse Kinematics Problem of Industrial Serial Manipulators with an Ortho-parallel Basis and a Spherical Wrist" — OPW parameter convention definition
- opw_kinematics library (github.com/Jmeyer1292/opw_kinematics) — parameter sign conventions
- pybind11 docs: GIL section, multiprocessing fork safety
- python-fcl: BVHModel construction requirements, transform API
- pyarrow docs: ParquetWriter append mode, atomic write patterns
- Python multiprocessing docs: `spawn` vs. `fork` start methods, `maxtasksperchild`

---
*Pitfalls research for: CPU-bound Python robot reachability optimizer — EDEN Cell Optimizer (beam coping cell, Fanuc M-20iD/20)*
*Researched: 2026-04-16*
