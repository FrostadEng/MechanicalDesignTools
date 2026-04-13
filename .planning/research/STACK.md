# Technology Stack: Genesis Robot Placement Optimizer

**Project:** Eden Cell Optimizer — FANUC M-20iD/12L Spatial Search Milestone
**Researched:** 2026-04-12
**Overall Confidence:** HIGH (primary sources are the bundled genesis-doc source tree and live Eden API notes from Phase 2)

---

## Recommended Stack

### Core Simulation Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `genesis-world` | 0.3.4 (pinned in Eden API notes) | Physics engine, robot loading, IK solver, collision checking | Already operational in Docker venv; built-in IK confirmed working via Phase 2 validation (596 steps/sec @ CUDA); `gs.morphs.URDF(fixed=True)` is the confirmed loading path |
| PyTorch | >=2.1.0 (CUDA 12.1) | Genesis GPU backend runtime | Already installed; Genesis runs on Taichi/PyTorch; cannot be removed |
| Python | 3.12 (running venv) | Runtime | Installed venv is 3.12; Genesis requires >=3.10,<3.14 — compatible |

**Critical Genesis IK details (HIGH confidence — from bundled genesis-doc):**

- `robot.inverse_kinematics(link, pos, quat)` — single end-effector, returns joint position array
- `robot.inverse_kinematics_multilink(links, poss, quats, rot_mask, pos_mask)` — multi-link variant; `rot_mask` selects which rotation axes to constrain — useful for plasma torch approach (normal to face, free about tool axis)
- IK is purely kinematic (no physics step needed); call `robot.set_dofs_position(q)` + `scene.visualizer.update()` for fast batch checking without simulating
- Joint names queried at runtime: `robot.get_joint(name).dof_idx_local` — never hardcode indices
- `fixed=True` required in `gs.morphs.URDF()` for floor-mounted arm (confirmed in Phase 2 notes)
- Quaternion convention in Genesis: `[w, x, y, z]`
- Euler convention in Genesis: extrinsic x-y-z in degrees at the user level

**No external IK solver is needed.** Genesis's built-in IK is sufficient for the single-chain 6-DOF FANUC arm. Do not add ikpy, TracIK, or KDL unless Genesis IK proves pathological (see What to Avoid).

---

### Robot Model

| Technology | Source | Purpose | Why |
|------------|--------|---------|-----|
| `ros-industrial/fanuc` | GitHub submodule at `eden/assets/fanuc/` | URDF for FANUC M-20iD/12L | Official ros-industrial maintained URDF; joint names known from that package; `m20id` subfolder contains `m20id.urdf` and mesh STLs |

**FANUC M-20iD/12L URDF loading pattern (MEDIUM confidence — ros-industrial structure is stable but URDF is not yet on-disk in this repo; must be cloned):**

```python
robot = scene.add_entity(
    gs.morphs.URDF(
        file='eden/assets/fanuc/fanuc_m20id12l_support/urdf/m20id12l.urdf',
        fixed=True,
        pos=(X, Y, Z),   # base mount position in meters
        euler=(0, 0, 0), # flat mount, pitch/roll = 0
    )
)
```

Expected joint names in `ros-industrial/fanuc` m20id package: `joint_1` through `joint_6` (ros-industrial convention; verify at clone time with `robot.get_joint(name)` enumeration). End-effector link name will be `tool0` (ros-industrial standard flange link name).

**Acquisition:** Clone as git submodule into `eden/assets/fanuc/`:
```
git submodule add https://github.com/ros-industrial/fanuc.git eden/assets/fanuc
```
The relevant package path inside that repo is `fanuc_m20id12l_support/`.

---

### Spatial Search: Bayesian Optimization

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `optuna` | >=3.6.0 | Bayesian optimizer for [X, Y, Z] base placement search | Simplest API for this use case; Tree-structured Parzen Estimator (TPE) sampler is sample-efficient for 3D continuous search; no GPU dependency; works headlessly; integrates cleanly with Python loops; does not require defining a prior model |

**Preferred Optuna usage pattern:**

```python
import optuna

def objective(trial):
    x = trial.suggest_float('x', X_MIN, X_MAX)
    y = trial.suggest_float('y', Y_MIN, Y_MAX)
    z = trial.suggest_float('z', Z_MIN, Z_MAX)
    # run IK + collision check
    return -manipulability_score  # minimize negative score

study = optuna.create_study(sampler=optuna.samplers.TPESampler())
study.optimize(objective, n_trials=200)
```

**Why Optuna over alternatives:**

| Library | Verdict | Reason |
|---------|---------|--------|
| `optuna` | RECOMMENDED | Minimal setup, TPE sampler well-suited to 3–10 parameter spaces, zero external model fitting overhead, excellent Python integration |
| `scikit-optimize` (`skopt`) | AVOID | Maintenance stalled (last release 2021); not actively maintained for Python 3.12; `BayesSearchCV` API is sklearn-centric; poor fit for this use case |
| `botorch` + `ax-platform` | AVOID for this task | Gaussian Process BO is powerful but heavyweight; requires `torch` model fitting per iteration; adds significant complexity for a 3D search over at most ~500 pre-filtered candidates; overkill |
| `scipy.optimize` (differential evolution, Nelder-Mead) | FALLBACK | Deterministic, no uncertainty modeling; acceptable if Optuna proves awkward with discrete failure modes (IK fail = -inf) |

**Note:** The reach-bubble pre-filter will reduce the feasible search volume dramatically (see Architecture). Optuna's TPE over a tight pre-filtered bounding box is sufficient — you do not need the full GP machinery of BoTorch.

---

### Manipulability Index

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `numpy` | <2.0 (pinned in eden requirements.txt) | Jacobian computation and manipulability index | Already available; manipulability = sqrt(det(J * J^T)); requires 6×6 Jacobian extraction from Genesis |

**Implementation approach:**

Genesis does not expose a Jacobian API directly at this time (MEDIUM confidence — not documented in bundled genesis-doc). The correct approach is:

1. Query joint positions after IK solve: `q = robot.get_dofs_position(dofs_idx)`
2. Compute the geometric Jacobian analytically using the FANUC DH parameters or by finite-difference perturbation on the Genesis IK solver
3. Yoshikawa manipulability: `w = sqrt(det(J @ J.T))` where J is the 6×n Jacobian

**Finite-difference Jacobian via Genesis IK (practical approach):**
```python
def compute_jacobian_fd(robot, ee_link, q_current, dofs_idx, delta=1e-5):
    J = np.zeros((6, len(dofs_idx)))
    p0 = get_ee_pose(robot, ee_link)  # current pose
    for i, dof in enumerate(dofs_idx):
        q_perturb = q_current.copy()
        q_perturb[i] += delta
        robot.set_dofs_position(q_perturb, dofs_idx)
        p_perturb = get_ee_pose(robot, ee_link)
        J[:3, i] = (p_perturb[:3] - p0[:3]) / delta      # position
        J[3:, i] = (p_perturb[3:] - p0[3:]) / delta      # orientation
        robot.set_dofs_position(q_current, dofs_idx)      # restore
    return J
```

Do not pull in `roboticstoolbox-python` or `pinocchio` for manipulability alone — the dependency overhead is not justified.

---

### FANUC M-20iD/12L Reach Envelope Pre-filter

| Approach | Implementation | Why |
|----------|---------------|-----|
| Analytic sphere-annulus check | Pure numpy, no library | Robot has max reach ~1868mm (M-20iD/12L datasheet); min reach determined by shoulder singularity zone (~300mm from base axis); base is floor-mounted with fixed Z |

**Pre-filter logic (analytical):**

The M-20iD/12L has:
- Maximum reach: 1868mm (wrist center to base)
- Typical minimum usable reach (to avoid shoulder singularity): ~300mm from J1 axis

For a candidate base position `(X_base, Y_base, Z_base)`, reject if any required TCP point `(X_tcp, Y_tcp, Z_tcp)` satisfies:

```python
d = np.sqrt((X_tcp - X_base)**2 + (Y_tcp - Y_base)**2 + (Z_tcp - Z_base)**2)
if d > 1868 or d < 300:
    reject  # outside physical reach bubble
```

This pre-filter runs in microseconds per candidate vs. milliseconds per Genesis IK call. Use it to cull the 3D grid before entering the Bayesian optimizer loop.

---

### Visualization

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `matplotlib` | 3.10.8 (installed in main venv) | 2D bounding box overlays (Phase 0), result heatmaps | Already installed and proven for FEA diagrams in this codebase |

**Phase 0 overlays:** `matplotlib.patches.Rectangle` for MME bounding boxes; `matplotlib.patches.Polygon` for cross-section profiles overlaid on the conveyor datum line. Export to PNG via `fig.savefig(path, dpi=150)`.

**Phase 1 result visualization:** Scatter plot of valid base positions color-coded by manipulability index. Matplotlib is sufficient; no 3D visualization library is needed for the output artifact.

---

### Supporting Libraries (Already in eden requirements.txt)

| Library | Version | Purpose |
|---------|---------|---------|
| `numpy` | <2.0 | Array ops, Jacobian, MME bounding box math |
| `scipy` | any | Rotation utilities (`scipy.spatial.transform.Rotation`); useful for quaternion/euler conversions to match Genesis `[w,x,y,z]` convention |
| `pandas` | any | Logging valid poses to CSV for downstream review |
| `pyyaml` | any | Configuration for search bounds, work zone offsets, TCP offset |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| IK solver | Genesis built-in (`robot.inverse_kinematics`) | ikpy | ikpy is a pure Python forward/inverse kinematics library with no Genesis integration; adds a second kinematic model that may drift from Genesis collision geometry; unnecessary complexity |
| IK solver | Genesis built-in | TracIK (Python bindings) | TracIK requires ROS2 environment + C++ bindings; overkill for a single-chain arm; Genesis IK confirmed working in Phase 2 |
| IK solver | Genesis built-in | KDL (PyKDL) | Same ROS2 dependency issue; not compatible with eden Docker without ROS2 environment activated |
| Bayesian opt | Optuna (TPE) | BoTorch + Ax | GP overhead unjustified for 3D continuous + small budget; requires fitting a GP model each iteration; adds PyTorch training loop complexity on top of existing simulation loop |
| Bayesian opt | Optuna (TPE) | scikit-optimize | Unmaintained since 2021; Python 3.12 compatibility unverified; API is sklearn-centric |
| Jacobian/manipulability | Pure numpy (FD or analytic DH) | roboticstoolbox-python | Heavy dependency; brings its own kinematics model separate from Genesis; version conflicts likely |
| Jacobian/manipulability | Pure numpy | pinocchio | C++ library with Python bindings; complex install; no Docker image support without separate build; not justified for one manipulability metric |
| Reach pre-filter | Analytic sphere check | Voxel grid discretization | Adds quantization error; slower to build than an analytic check; no benefit for a continuous-output optimizer |

---

## Installation

All dependencies except `optuna` are already in `eden/requirements.txt`. Add:

```bash
# Inside Robot_Simulations/eden/.venv
pip install optuna>=3.6.0
```

Optuna is pure Python, no CUDA requirement, ~30MB. Add to `eden/requirements.txt`:

```
optuna>=3.6.0
```

No other new packages are required for this milestone.

---

## Dependency Constraints

- `numpy<2.0` is pinned in `eden/requirements.txt` — do not upgrade. Genesis may use NumPy internals incompatible with 2.x.
- `setuptools==67.8.0` and `packaging==23.1` are pinned for authoring image compatibility — do not change.
- `torch>=2.1.0` is a Genesis hard dependency — present.
- `stable-baselines3[extra]` is in requirements but unused for this milestone — do not remove (it anchors the Gymnasium version Genesis depends on).

---

## What NOT to Use

| Library | Why Not |
|---------|---------|
| `ikpy` | Maintains its own kinematic model independent of Genesis scene geometry; IK solution may be feasible in ikpy but collide in Genesis; two IK systems for one robot is a reliability hazard |
| `tracik-python` | Requires compiled C++ TracIK library; adds ROS2 build dependency; install is fragile; Genesis built-in IK is equivalent for this arm |
| `scikit-optimize` | Unmaintained (2021); Python 3.12 untested; `gp_minimize` is slower than Optuna TPE for low-dimensional spaces |
| `botorch` / `ax-platform` | GP training per iteration adds 50–200ms overhead; correct for expensive black-box problems but the Genesis IK check is only 1–5ms; TPE is more appropriate |
| `roboticstoolbox-python` | Large dependency; brings its own URDF parser, DHRobot, and IK stack that will duplicate Genesis; version conflicts with numpy<2.0 likely |
| `pinocchio` | C++ pinned bindings; requires separate apt install (`ros-$ROS_DISTRO-pinocchio`) or Conda; not worth it for one manipulability metric |
| `openrave` | Deprecated; Python 2 era; do not use |
| Any ROS2 Python library (rclpy, geometry_msgs) | ROS2 Jazzy is mentioned as stack context but the search loop itself runs in the eden Docker venv which is not a ROS2 environment; URDF is loaded directly by Genesis, not through ROS |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Genesis IK API (`robot.inverse_kinematics`, `inverse_kinematics_multilink`) | HIGH | Confirmed in bundled `genesis-doc` source and Eden Phase 2 API notes (EDEN_API_NOTES.md Section 4.6) |
| Genesis URDF loading (`gs.morphs.URDF(fixed=True)`) | HIGH | Confirmed in Phase 2 `urdf_import_validation.py` (TEST PASSED) and genesis-doc |
| Genesis version in this project (0.3.4) | HIGH | Stated in EDEN_API_NOTES.md header |
| Genesis quaternion convention `[w,x,y,z]` | HIGH | Stated in `misc_guidelines.md` from genesis-doc |
| ros-industrial/fanuc URDF package name (`fanuc_m20id12l_support`) | MEDIUM | Based on ros-industrial naming conventions; must be verified at clone time; joint names (`joint_1` through `joint_6`, `tool0`) are ros-industrial standard but must be confirmed by running `robot.get_joint(name)` enumeration |
| FANUC M-20iD/12L max reach (1868mm) | MEDIUM | From datasheet knowledge (training data); must be confirmed against official FANUC spec sheet before baking into pre-filter |
| Optuna TPE suitability | MEDIUM | Well-documented community pattern for low-dimensional Bayesian search; version compatibility with Python 3.12 confirmed from Optuna release notes (3.x series targets 3.8–3.12) |
| Genesis Jacobian API absence | MEDIUM | Not documented in bundled genesis-doc; no `get_jacobian` or similar method found in API reference or user guides; FD approach is a safe workaround but should be re-checked against genesis-world 0.3.4 release notes |
| scikit-optimize being unmaintained | HIGH | Last PyPI release was 0.9.0 in September 2021; confirmed by PyPI metadata |

---

## Open Questions / Phase-Specific Research Flags

1. **ros-industrial/fanuc joint names** — Must verify exact joint name strings and end-effector link name from the cloned URDF before writing the search loop. Run `robot.get_joint(name)` enumeration after loading.

2. **Genesis IK failure mode** — When IK is unreachable, does `robot.inverse_kinematics()` raise an exception or return a sentinel value (e.g., zeros, NaN)? This determines the collision-check guard logic. Needs empirical test at Phase 1 start.

3. **Genesis collision query API** — The current Phase 2 notes do not document a direct post-step collision query (e.g., `robot.is_in_collision()`). The pattern from the docs uses `scene.step()` + `rigid.get_contact_pairs()`. Verify how to efficiently check robot-vs-environment collision after IK without running a full physics step (which would be slower). Consider `enable_collision=False` for IK-only queries then a separate collision check pass.

4. **FANUC M-20iD/12L arm mass / inertia for PD gain tuning** — Control gains from Phase 2 notes are tuned for Franka Panda. FANUC gains must be tuned separately; this is blocking for any path execution test. For IK-only reachability checks (no `control_dofs_position`), gains are irrelevant — only `set_dofs_position` is needed.

5. **URDF mesh paths** — `ros-industrial/fanuc` URDF references STL meshes via `package://` ROS URI convention. Genesis URDF loader may or may not resolve `package://` URIs. If not, the URDF file must be patched to use relative paths before loading. This is a known friction point when loading ROS URDFs outside of a ROS environment.
