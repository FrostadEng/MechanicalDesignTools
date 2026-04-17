# Technology Stack: EDEN Cell Optimizer V3

**Project:** EDEN Cell Optimizer — Beam Coping Cell Kinematic Optimizer (V3)
**Researched:** 2026-04-16
**Overall Confidence:** HIGH for core stack; MEDIUM for python-fcl install path; LOW for OPW binding version pins

---

## Summary

This is a CPU-bound, brute-force Python optimizer. No simulation engine, no ML, no ROS. The stack is
intentionally narrow: a C++ analytical IK kernel wrapped in pybind11, a collision library, a pre-existing
AISC catalog, standard scientific Python, and columnar result storage. Every component exists to serve the
~23 hour grid search on a 14-thread i5-13600K.

---

## Recommended Stack

### IK Solver (Critical Path)

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `opw_kinematics` (C++ header-only) | HEAD / latest tag | Analytical OPW IK, 8 solutions, ~4 µs/query | MEDIUM — library is actively used in ROS-I ecosystem but has no PyPI package; must build from source |
| `pybind11` | >=2.12.0 | C++/Python binding for OPW wrapper | HIGH — latest stable is 2.13.x as of 2025; installable via `pip install pybind11` |
| `cmake` | >=3.18 | Build system for C++ extension | HIGH — system cmake or `pip install cmake` |

**OPW library source:** `https://github.com/Jmeyer1292/opw_kinematics`

This is a C++ header-only library. There is no official Python package. The project must implement its own
pybind11 binding. The binding is a ~100-line `.cpp` file that:

1. Accepts 7 OPW parameters (a1, a2, b, c1, c2, c3, c4) and a 4×4 homogeneous transform as input.
2. Calls `opw_kinematics::inverse()` from the header.
3. Returns a list of up to 8 joint-angle arrays (some may be NaN for unreachable).
4. Filters by joint limits (M-20iD/20 limits from spec Section 2).

**Build pattern:**

```
eden_optimizer/
  ik/
    opw_wrapper.cpp        # pybind11 module definition
    CMakeLists.txt         # builds opw_wrapper.so
    opw_kinematics/        # git submodule or header copy
```

```cmake
# CMakeLists.txt (minimal)
cmake_minimum_required(VERSION 3.18)
project(opw_wrapper)
find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
add_subdirectory(opw_kinematics)
pybind11_add_module(opw_wrapper opw_wrapper.cpp)
target_include_directories(opw_wrapper PRIVATE opw_kinematics/include)
```

**Why not alternatives:**

| Alternative | Verdict | Reason |
|-------------|---------|--------|
| Pure Python OPW re-implementation | DO NOT USE | ~40 µs/query vs 4 µs. On 1.19M Phase A cells × ~4 IK checks per filter = ~5× speed penalty. Exceeds the 23-hour budget by days. Spec explicitly forbids this. |
| ikpy | DO NOT USE | Pure Python, numeric Jacobian. ~100-200 µs/query. 50× too slow. No analytical 8-solution output. |
| tracikpy | DO NOT USE | C++ TRAC-IK binding exists but is designed for ROS build environments (catkin/colcon). Standalone build requires significant effort. Uses KDL internally for numerical refinement — not pure analytical. Overhead higher than OPW. |
| IKFast (OpenRAVE) | LAST RESORT ONLY | Spec Section 11D acknowledges this as fallback if OPW parameters prove unreliable. Requires Dockerized OpenRAVE (OpenRAVE is abandonware). Use only if OPW FK→IK round-trip validation fails and cannot be resolved. |
| KDL kinematics | DO NOT USE | ROS-centric (OROCOS KDL). Iterative numeric solver — not analytical. No guarantee of all 8 solutions. |

**Validation requirement before any grid search:** 100+ random joint configs within M-20iD/20 limits, FK to
pose, IK on pose, verify ≥1 solution FKs back within 0.01 mm / 0.01°. This is not optional — bad OPW
parameters silently produce wrong results that pass all other checks.

---

### Collision Detection

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `python-fcl` | 0.7.x (latest on PyPI) | BVH mesh collision, plane primitives, convex hulls | MEDIUM — library is maintained by BerkeleyAutomation; install sometimes requires system liboctomap; verify on Ubuntu 24.04 |

**Source:** `https://github.com/BerkeleyAutomation/python-fcl`

`python-fcl` wraps the Flexible Collision Library (FCL), which supports:
- Plane primitives (workzone wall planes, conveyor surface, ground)
- Box / cylinder / convex hull primitives (beam cross-sections)
- BVH meshes (robot link STLs from URDF, tool geometry)
- Continuous collision detection (not needed here — discrete is sufficient)
- `CollisionObject`, `CollisionManager`, `collide()`, `distance()` API

**Install on Ubuntu 22.04/24.04:**

```bash
sudo apt-get install liboctomap-dev libfcl-dev
pip install python-fcl
```

If `libfcl-dev` is not in apt at the required version, build FCL from source first. python-fcl pins to
FCL 0.6.x. On Ubuntu 24.04, `libfcl-dev` ships FCL 0.7 — may require the git HEAD of python-fcl
rather than the PyPI release. Verify version compatibility before Phase 3.

**Usage pattern for beam collision:**

```python
import fcl

# Static environment (created once per optimizer run)
wall_pos  = fcl.CollisionObject(fcl.Box(0.001, 3.0, 3.0), fcl.Transform(t=[0.515, 0, 1.5]))
conveyor  = fcl.CollisionObject(fcl.Box(3.0, 3.0, 0.001), fcl.Transform(t=[0, 0, 0.838]))

# Active beam (recreated per beam type, ~200 beams total)
beam_verts, beam_faces = build_beam_mesh(aisc_section)  # from aisc.py
beam_mesh  = fcl.BVHModel(); beam_mesh.beginModel(...); beam_mesh.addSubModel(beam_verts, beam_faces); beam_mesh.endModel()
beam_obj   = fcl.CollisionObject(beam_mesh, fcl.Transform(t=[0, 0, 0.838]))

# Per-IK-solution check (~10 µs per check at BVH depth)
request    = fcl.CollisionRequest()
result     = fcl.CollisionResult()
collide    = fcl.collide(tool_obj, beam_obj, request, result)
```

**Why not alternatives:**

| Alternative | Verdict | Reason |
|-------------|---------|--------|
| trimesh ray casting | DO NOT USE for collision | Not a proper collision library. Ray-cast approach fails for concave meshes and doesn't give separation distance. trimesh is for geometry processing and visualization only. |
| pybullet collision | DO NOT USE | Requires physics server; overhead per check is much higher; designed for simulation not batch offline queries. |
| Open3D collision | AVOID | No persistent BVH scene management API. Would require rebuilding BVH every call. |

---

### Beam Catalog

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `aisc.py` (in-repo) | N/A — already in repo at `engineering_tools/mech_core/components/members/aisc.py` | AISC steel catalog lookup (2299 shapes in `aisc_shapes.json`) | HIGH — verified on-disk with 2299 entries, W/C/S/L/HSS types, full section properties |

The local `aisc.py` module and `aisc_shapes.json` are already present in this monorepo. The optimizer
imports them directly via `sys.path` addition or package install.

**Key methods available (from reading source):**
- `SectionProperties` — attribute access for any shape property (Ix, d, bf, tw, tf, A, etc.) with
  automatic Pint unit scaling per AISC Database v16.0
- `_SHAPE_DB` — dict keyed by imperial name (e.g., `"W44X408"`)
- Supports W, C, S, L, HSS, Pipe shapes

**Geometry extraction for collision mesh:** `aisc.py` provides 2D cross-section dimensions (d, bf, tw,
tf, etc.). The optimizer must extrude these into 3D meshes using trimesh. This is a ~50-line function per
shape family (W-shape = 3-piece I-profile extrusion; HSS = hollow rectangle extrusion; etc.).

---

### Scientific Computation

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `numpy` | >=1.26.4, <2.0 (pin for venv compat) OR >=2.0 for standalone | Array math, homogeneous transforms, vectorized geometry | HIGH — 1.26.4 confirmed installed in project venv; 2.x is safe for new venv |
| `scipy` | >=1.11.0 (1.16.2 in venv) | Closed-form deflection equations, k-means clustering for tool design table | HIGH — confirmed in venv |

**numpy pinning note:** The existing Eden venv pins `numpy<2.0` for Genesis compatibility. The V3 optimizer
is a standalone project with its own venv. Use `numpy>=2.0` there — it is faster for small-array
operations (the 4×4 transform math dominating each IK call) and includes improvements to `np.linalg`.

**scipy usage:**
- `scipy.spatial.KMeans` or `scipy.cluster.vq` for 6D tool clustering (Phase 1 Step 5E)
- `scipy.linalg` for stiffness matrix operations in deflection model
- No scipy optimization routines needed — the grid search is pure enumeration

---

### Parallelization

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `multiprocessing.Pool` | stdlib (Python 3.12) | 14-thread parallel grid evaluation | HIGH — stdlib, no install needed |

**Critical implementation constraint — pickling C++ extensions:**

pybind11 extension modules are NOT picklable by default. `multiprocessing.Pool` uses pickle to send work
to worker processes. The correct pattern is:

```python
# Pattern: initialize OPW solver in each worker via initializer, not as a closure
import multiprocessing as mp

def worker_init(opw_params, joint_limits, target_db_path):
    global g_ik_solver, g_targets, g_collision_env
    g_ik_solver = build_opw_solver(opw_params)       # C++ object, created in-process
    g_targets   = load_targets(target_db_path)        # read-only JSON, loaded per worker
    g_collision_env = build_static_collision_env()    # FCL scene, created in-process

def evaluate_cell(args):
    tool_id, base_x, base_y, base_yaw, riser_section, riser_height = args
    # uses g_ik_solver, g_targets, g_collision_env from module globals
    ...

with mp.Pool(14, initializer=worker_init, initargs=(opw_params, joint_limits, TARGET_DB)) as pool:
    results = pool.map(evaluate_cell, grid_cells)
```

This avoids pickling the OPW solver or FCL CollisionObjects. Worker startup cost is ~2-5 seconds per
worker (loading target database), which is amortized over millions of cells.

**Worker startup memory:** Each worker loads `target_database/` (~200 beams × ~100 poses/face × 4 faces
= ~80k pose objects) and the tool table (~1044 entries). At ~200 bytes/pose, that is ~16 MB per worker ×
14 workers = ~220 MB. Well within 32 GB RAM budget.

**Why not threading (`threading.Pool`):** Python GIL prevents true parallel CPU execution of Python code.
The GIL is released during C extension calls (OPW IK), but the surrounding Python loop logic (collision
bookkeeping, scoring, parquet accumulation) would still be single-threaded. Use `multiprocessing`, not
`threading`.

**Why not `concurrent.futures.ProcessPoolExecutor`:** Functionally equivalent to `multiprocessing.Pool`
with slightly cleaner API. Either works. `multiprocessing.Pool` has `initializer`/`initargs` which is
the key feature needed here.

---

### Result Storage

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `pyarrow` | >=16.0.0 (latest stable is 19.x as of 2025) | Write Phase A/B results as Parquet files; columnar read/filter for post-processing | HIGH — parquet is the standard for this use case |

**pyarrow is not currently in the project venv.** Add to the optimizer's `requirements.txt`:

```
pyarrow>=16.0.0
```

**Write pattern for Phase A results:**

```python
import pyarrow as pa
import pyarrow.parquet as pq

schema = pa.schema([
    pa.field('tool_cluster_id', pa.int32()),
    pa.field('base_x', pa.float32()),
    pa.field('base_y', pa.float32()),
    pa.field('base_yaw', pa.float32()),
    pa.field('riser_section', pa.utf8()),
    pa.field('riser_height_mm', pa.int16()),
    pa.field('reachability_pct', pa.float32()),
    pa.field('manipulability_mean', pa.float32()),
    pa.field('hardware_cost', pa.float32()),
    pa.field('tcp_error_estimate_mm', pa.float32()),
])

# Batch writes — collect N cells then flush, don't write row-by-row
writer = pq.ParquetWriter('phase_a_results.parquet', schema,
                          compression='zstd',  # zstd: best ratio/speed tradeoff
                          compression_level=3)

# In main process, collect results from pool.imap_unordered(), buffer into batches
batch_size = 10_000
buffer = []
for result in pool.imap_unordered(evaluate_cell, grid_cells):
    buffer.append(result)
    if len(buffer) >= batch_size:
        writer.write_batch(pa.RecordBatch.from_pylist(buffer, schema=schema))
        buffer.clear()
if buffer:
    writer.write_batch(pa.RecordBatch.from_pylist(buffer, schema=schema))
writer.close()
```

**Compression:** Use `zstd` at level 3. Phase A has ~1.19M rows × ~10 float32 columns = ~48 MB
uncompressed. With zstd it compresses to ~3-5 MB. Phase B is ~522k rows, smaller. Avoid `snappy` (lower
ratio) and `gzip` (slower write, no read benefit here).

**Post-processing:** `pyarrow.parquet.read_table()` with `columns=` parameter to read only needed
columns, and `filters=` for predicate pushdown (e.g., `reachability_pct > 0.90`). No need for pandas
or dask for datasets this size.

---

### Visualization

| Technology | Version | Purpose | Verdict |
|------------|---------|---------|---------|
| `trimesh` | 4.9.0 (confirmed in venv) | Mesh loading, cross-section extrusion, geometry processing | RECOMMENDED for geometry work |
| `pyvista` | 0.46.3 (confirmed in venv) | URDF scene assembly and interactive visualization of top-10 configs | RECOMMENDED for visualization |
| `vtk` | 9.5.2 (confirmed in venv, pyvista backend) | Low-level rendering backend for pyvista | Not called directly |

**Division of responsibility:**

`trimesh` is the geometry engine. Use it to:
- Extrude AISC 2D profiles into 3D meshes for FCL input and visualization
- Load robot link STL files from the URDF package
- Compute mesh boolean operations (not needed in core path, but useful for validation scenes)
- Export meshes to OBJ/STL for external inspection

`pyvista` is the visualization engine. Use it to:
- Assemble URDF scenes showing top-10 robot placements with beam and workzone geometry
- Render reachability heatmaps as colored point clouds on beam surfaces
- Generate screenshots for `visualization/` output directory

**Why trimesh over Open3D for geometry:** trimesh is already installed in the venv, has a cleaner API
for 2D profile extrusion (`trimesh.creation.extrude_polygon()`), and integrates better with pyvista's
mesh import (`pyvista.wrap(trimesh_mesh)`).

**Why pyvista over matplotlib 3D:** pyvista renders full 3D scenes with lighting, material colors, and
camera control. matplotlib's 3D axes are limited to scatter/line/surface plots — not suitable for robot
URDF scene rendering. pyvista's `Plotter.add_mesh()` + `add_lines()` is exactly the right API for
assembling a robot scene from link meshes.

**Off-screen rendering:** The compute node may not have a display. pyvista supports off-screen rendering:

```python
import pyvista as pv
pl = pv.Plotter(off_screen=True)
pl.add_mesh(robot_mesh, color='lightgray')
pl.add_mesh(beam_mesh, color='steelblue')
pl.screenshot('visualization/config_01.png')
```

Requires `vtk` with EGL or OSMesa support. On Ubuntu 22.04+: `sudo apt-get install libgl1-mesa-glx libgles2-mesa-dev`.

---

### Logging and Output

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| `logging` (stdlib) | Python 3.12 | Structured per-cell and per-filter statistics; dual-unit output | HIGH |
| `json` (stdlib) | Python 3.12 | `valid_tools.json`, `best_config.json`, `top_10_configs.json` output | HIGH |
| `tqdm` | >=4.60 | Progress bars for grid search phases | HIGH — confirmed in venv (4.67.1) |

**Dual-unit logging pattern:** All computed values stored internally in SI (meters, kg, N, Pa). Log
statements emit both units:

```python
logger.info(f"Riser deflection: {delta_m*1000:.3f} mm ({delta_m*39.37:.4f} in)")
```

---

## Environment Setup

**Standalone venv for optimizer (separate from Eden/Genesis venv):**

```bash
python3 -m venv .venv_optimizer
source .venv_optimizer/bin/activate

# Core scientific stack
pip install "numpy>=2.0" "scipy>=1.11" "pyarrow>=16.0" "tqdm>=4.60"

# Visualization
pip install "trimesh>=4.0" "pyvista>=0.44"

# pybind11 build tools
pip install "pybind11>=2.12" "cmake>=3.18"

# Collision detection
sudo apt-get install liboctomap-dev libfcl-dev
pip install python-fcl

# OPW kinematics (custom build — no PyPI package)
git submodule add https://github.com/Jmeyer1292/opw_kinematics.git ik/opw_kinematics
cd ik && mkdir build && cd build
cmake .. -DPYTHON_EXECUTABLE=$(which python3) -Dpybind11_DIR=$(python3 -m pybind11 --cmakedir)
make -j$(nproc)
# Copy opw_wrapper.so to project root or install in venv
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| IK solver | opw_kinematics C++ | ikpy | 50× too slow (pure Python, ~200 µs/query) |
| IK solver | opw_kinematics C++ | tracikpy | ROS/catkin build dependency; numeric TRAC-IK slower than analytical OPW; no 8-solution batch output |
| IK solver | opw_kinematics C++ | IKFast | OpenRAVE abandonware; Docker-only; last resort per spec |
| Collision | python-fcl | pybullet | Physics server overhead; designed for simulation, not batch offline queries |
| Collision | python-fcl | trimesh ray cast | Not a collision library; fails on concave meshes |
| Parallelization | multiprocessing.Pool | threading.Pool | GIL prevents parallel Python execution |
| Parallelization | multiprocessing.Pool | Dask/Ray | Unnecessary complexity for single-machine workload; no distributed compute needed |
| Storage | pyarrow/parquet | SQLite | Columnar parquet reads 10-100× faster for analytics queries (filter by score, sort by column) |
| Storage | pyarrow/parquet | HDF5 (h5py) | Less convenient for tabular result querying; parquet has better ecosystem (pandas/polars/duckdb) |
| Visualization | pyvista | matplotlib 3D | Not suitable for full URDF scene rendering with meshes |
| Visualization | pyvista | Open3D | More complex API for scene assembly; no advantage here |
| numpy version | >=2.0 (standalone venv) | pinned 1.26.4 | 1.26.4 pin is for Genesis compat; V3 optimizer is a separate project; 2.x is safe and faster for small arrays |

---

## What NOT to Use

| Library | Reason |
|---------|--------|
| `genesis-world` | V3 optimizer is not a simulation task. Genesis is a physics engine for RL; it has no role here. Importing it adds ~30-second startup and GPU dependency. |
| `torch` / PyTorch | No ML in V3. GPU compute explicitly out of scope per spec. Adding torch adds 2+ GB to the environment for zero benefit. |
| `optuna`, `pymoo`, `scipy.optimize` | Grid search is pure enumeration over a finite pre-pruned space. No optimizer needed. Using a sampler here would be non-exhaustive (violates spec requirement of bounded brute-force). |
| `urdfpy`, `yourdfpy` | URDF loading libraries designed for visualization/simulation. For this project, URDF is only needed to extract OPW kinematic parameters (DH offsets) — do this once manually, not at runtime. |
| `ROS1/ROS2/catkin` | Explicitly forbidden by spec. opw_kinematics C++ is header-only and builds standalone. |
| `pandas` | Fine for interactive analysis but adds overhead in tight loops. Use pyarrow directly for write path; load results into pandas only for post-processing analysis if desired. |

---

## Version Summary

| Package | Confirmed Version | Source |
|---------|-------------------|--------|
| Python | 3.12.3 | System (`/usr/bin/python3`) |
| numpy | 1.26.4 (venv) | `.dist-info` on disk |
| scipy | 1.16.2 (venv) | `.dist-info` on disk |
| trimesh | 4.9.0 (venv) | `.dist-info` on disk |
| pyvista | 0.46.3 (venv) | `.dist-info` on disk |
| vtk | 9.5.2 (venv) | `.dist-info` on disk |
| tqdm | 4.67.1 (venv) | `.dist-info` on disk |
| pyarrow | NOT INSTALLED | Must add to optimizer requirements |
| python-fcl | NOT INSTALLED | Must install (system + pip) |
| pybind11 | NOT INSTALLED standalone | Must install; torch bundled copy not usable |
| opw_kinematics | NOT INSTALLED | Must clone and build custom binding |
| cmake | NOT IN PATH | Must install (`pip install cmake` or `apt`) |

Versions for packages not yet installed are recommended minimums, not confirmed; verify at install time.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| OPW IK approach | HIGH | Spec mandates this; architecture is clear; ~4 µs is documented in spec and consistent with C++ analytical IK literature |
| pybind11 binding pattern | HIGH | Standard approach; torch's bundled pybind11 confirms 2.x API is available; custom wrapper is ~100 lines |
| python-fcl | MEDIUM | Library is real and maintained; Ubuntu 24.04 apt FCL version may mismatch; install path needs validation in Phase 1 |
| pyarrow/parquet | HIGH | Standard for columnar result storage; API is stable; compression recommendations are well-established |
| multiprocessing pattern | HIGH | Worker initializer pattern for C++ extensions is a known, documented approach |
| trimesh + pyvista | HIGH | Both confirmed installed in project venv with appropriate versions |
| aisc.py | HIGH | Verified on-disk, 2299 shapes, correct data structure |
| numpy version choice | HIGH | 2.x safe for standalone venv; 1.26.4 pin is a Genesis-only constraint |
