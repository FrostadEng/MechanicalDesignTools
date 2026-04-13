# Domain Pitfalls: Genesis Robot Placement Optimization

**Domain:** Genesis physics simulation + ROS-Industrial URDF + IK reachability + spatial search
**Researched:** 2026-04-12
**Confidence:** HIGH for Genesis-specific findings (verified from installed source at `.venv/lib/python3.12/site-packages/genesis/`); MEDIUM for ros-industrial URDF patterns (verified from Franka URDF in repo as reference); HIGH for classical robotics pitfalls (well-established theory)

---

## Critical Pitfalls

Mistakes that force rewrites or invalidate entire runs.

---

### Pitfall C1: `requires_jac_and_IK` is False by Default — Silent Failure at Runtime

**What goes wrong:** Genesis's `URDF` morph has `requires_jac_and_IK: bool = False` by default (verified in `genesis/options/morphs.py` line 86). If you load the FANUC URDF without explicitly setting this flag, `robot.inverse_kinematics(...)` raises `"Inverse kinematics and jacobian are disabled for this entity"` — but only after `scene.build()` has already run (which is the expensive JIT compilation step). The error does not surface at load time.

**Why it happens:** Genesis separates the Jacobian/IK memory allocation from the URDF parsing step. The flag gates whether Taichi fields for `_IK_mat`, `_IK_jacobian`, etc. are allocated during `_init_jac_and_IK()`. Missing the flag means those fields are never created.

**Consequences:** Phase 1 search loop crashes on first IK call after a potentially multi-second build step. If running in a batch search loop across candidate positions, every loop iteration will fail immediately.

**Prevention:**
```python
robot = scene.add_entity(
    gs.morphs.URDF(
        file="assets/fanuc/fanuc_m20id12l_support/urdf/m20id12l.urdf",
        requires_jac_and_IK=True,   # REQUIRED — not the default
        fixed=True,                  # floor-mounted robot
    )
)
```

**Detection:** Run a single-scene smoke test before the search loop. Call `robot.inverse_kinematics(...)` on one known-reachable point immediately after `scene.build()`. If it crashes here, you have a flag problem.

**Phase:** Phase 1 setup. Must be confirmed before any search loop code is written.

---

### Pitfall C2: Genesis URDF Scale Compounding — Robot Loads at Millimeter Scale

**What goes wrong:** ros-industrial FANUC URDFs specify geometry in meters (URDF standard). Genesis's URDF parser reads the `<mesh filename="..." scale="..."/>` attribute from the URDF and multiplies it by `morph.scale` (verified in `genesis/utils/urdf.py` lines 113–115):

```python
scale = float(morph.scale)
if geom.geometry.geometry.scale is not None:
    scale *= geom.geometry.geometry.scale
```

If the URDF mesh `<scale>` tag is set to `"0.001 0.001 0.001"` (a common ros-industrial convention for STL meshes authored in millimeters) **and** you pass `morph.scale=0.001` thinking you're converting to meters, the result is `0.001 * 0.001 = 0.000001` — a robot 1000x too small. Conversely, if the URDF meshes are in meters and you set `morph.scale=1000.0` to "fix" a visual that looked too small, you compound in the wrong direction.

**Why it happens:** ros-industrial repos are inconsistent. Some use STL meshes in millimeters with `<scale>0.001 0.001 0.001</scale>`. Others ship meshes already in meters with no scale tag. The Franka URDF in this repo uses no scale tag and `.obj` files (already in meters). The FANUC M-20iD URDF must be inspected before assuming.

**Consequences:** Robot geometry is the wrong size. Collision detection produces nonsense. IK solutions exist but produce TCP positions in the wrong metric space. Joint origins (which are also scaled by `morph.scale` via `l_info["pos"] *= morph.scale`) are off by orders of magnitude.

**Prevention:**
1. After loading, check `robot.links[0].pos` against known FANUC base dimensions (base is roughly 300mm x 300mm footprint). If the base link position values are in the 0.001–0.01 range instead of 0.3, scale is wrong.
2. Explicitly grep the FANUC URDF for `<mesh ... scale=` tags before writing the loader code.
3. Use `morph.scale=1.0` as the default unless you have confirmed reason to deviate.

**Detection:** After `scene.build()`, call `robot.get_link("flange").pos` with all joints at zero (home position) and compare against FANUC published kinematic data: reach is 911mm, which means the flange at full extension should read approximately 0.911 in world Z. If you read 0.000911 or 911.0, scale is wrong.

**Phase:** Phase 1 URDF loading. Catch this before writing any path generation code.

---

### Pitfall C3: Genesis IK Has No Built-in Convergence Status Return — Silent Reachability Failures

**What goes wrong:** `robot.inverse_kinematics(link, pos, quat)` returns `qpos` always — it does not raise an exception when IK fails to converge. The solver runs `max_samples=50` restarts of `max_solver_iters=20` iterations each (defaults verified in `rigid_entity.py` lines 1073–1074) and returns the best solution found, even if that solution has large residual error. The `return_error=True` flag must be explicitly passed to get the error vector.

**Why it happens:** Genesis's IK is designed for batched RL training where per-sample failure is expected and penalized via reward, not via exceptions. For deterministic reachability checking, you must interpret the error yourself.

**Consequences:** The search loop logs a candidate position as "valid" when the robot is actually 50mm short of the target — the IK solver returned the closest it could get, not a failure signal. The placement is accepted, but in the real cell the robot cannot reach.

**Prevention:**
```python
qpos, error = robot.inverse_kinematics(
    link=tcp_link,
    pos=target_pos,
    quat=target_quat,
    return_error=True,
)
err_pos = np.linalg.norm(error[:3])    # translational residual, meters
err_rot = np.linalg.norm(error[3:])    # rotational residual, radians

REACH_TOL_M   = 0.002   # 2mm — tighter than Genesis default 0.5mm to be conservative
REACH_TOL_RAD = 0.01    # ~0.57 degrees

if err_pos > REACH_TOL_M or err_rot > REACH_TOL_RAD:
    result = "UNREACHABLE"
else:
    result = "REACHABLE"
```

**Detection:** Test against a point you know is 10mm outside the reach envelope. Confirm the error vector magnitude is large. If `inverse_kinematics` returns silently with small error on an unreachable point, your tolerance is set wrong.

**Phase:** Phase 1. Must be in the search loop from the first iteration.

---

### Pitfall C4: IK Converges but Joint Limits Are Violated — Accepted Pose is Mechanically Invalid

**What goes wrong:** `respect_joint_limit=True` is the default, but joint limits in the URDF may not match the real FANUC M-20iD/12L controller limits. The URDF joint limits are what Genesis enforces. If the URDF was generated with soft limits from a ROS safety controller (`<safety_controller>` tag — visible in the Franka URDF as `k_position`, `k_velocity`) rather than the hard mechanical limits, Genesis reads the `<safety_controller>` fields and uses them as `dofs_kp`/`dofs_kv` (verified in `genesis/utils/urdf.py` lines 277–281), not as limit overrides. The hard `<limit lower=... upper=...>` values are still used for the constraint, but the stiffness of limit enforcement may be too soft.

**Why it happens:** URDF joint limits are advisory in MuJoCo-derived physics. Genesis's IK uses damped least-squares which can produce solutions that technically violate limits by a small margin if the damping term is large relative to the limit gradient.

**Consequences:** A path point accepted by IK may require J3 at 168° when the real robot controller allows 162°. The path runs in simulation but trips a joint overtravel fault on physical hardware.

**Prevention:**
1. After getting `qpos` from IK, independently clamp-check each joint against FANUC published limits. Build a lookup from the official FANUC M-20iD/12L spec sheet (J1: ±340°, J2: -90°/+145°, J3: -180°/+264° range, J4: ±380°, J5: ±125°, J6: ±720°) and verify `qpos` components are within these values.
2. Use tighter `pos_tol` and `rot_tol` than defaults if running a high-density path sweep.

**Detection:** After an IK solve, `np.clip(qpos, lower_limits, upper_limits)` and check `np.allclose(qpos, clipped_qpos, atol=1e-3)`. Any difference flags a limit violation.

**Phase:** Phase 1 search loop. Add to the rejection criteria checklist.

---

### Pitfall C5: AISC `SectionProperties` Returns Pint Quantities — Direct Numeric Comparison Crashes

**What goes wrong:** `aisc.py` returns `Pint`-wrapped quantities for every dimensional property (depth `d`, flange width `bf`, weight `W`, etc.). Code like `if section.d > 1100` raises `pint.errors.DimensionalityError` because `section.d` is `1100 mm` not `1100`. Similarly, arithmetic like `half_width = section.bf / 2` returns a Pint quantity — which works for Pint-aware code but fails when passed to numpy or Genesis (which expects raw floats in meters).

**Why it happens:** `aisc.py`'s `__getattr__` always attaches `ureg.mm` to length properties (lines 83–92). The Phase 0 script is in a different venv (`engineering_tools`) from Phase 1 (`eden/.venv`), but even within the same venv, any downstream consumer that doesn't import `pint` will fail when it receives a Pint quantity.

**Consequences:**
- Phase 0: Filter logic `section.W <= 300 * (ureg.lb / ureg.ft)` works if you use Pint units throughout, but `section.W <= 300` crashes because `W` is `kg/m`.
- Phase 1: If you pass `section.d.magnitude` (the raw float) to beam geometry construction, the value is in mm. Genesis expects meters. A beam constructed as 300 mm wide instead of 0.300 m will collide with a robot sized in meters — i.e., it will look 1000x too wide.

**Prevention:**
```python
# Phase 0 — correct unit comparison:
weight_lbs_per_ft = section.W.to(ureg.lb / ureg.ft).magnitude
if weight_lbs_per_ft > 300:
    continue

# Phase 1 — strip to meters for Genesis:
beam_depth_m  = section.d.to(ureg.meter).magnitude
beam_width_m  = section.bf.to(ureg.meter).magnitude
```

Never use `.magnitude` without `.to(target_unit)` first. Raw magnitude is in mm (the AISC metric DB stores lengths in mm per the AISC V16 readme).

**Detection:** Add an assertion at the top of Phase 0 and Phase 1 scripts:
```python
from engineering_tools.mech_core.components.members.aisc import get_section
s = get_section("W12X26")
assert abs(s.d.to(ureg.mm).magnitude - 310.0) < 5.0, "AISC unit scaling broken"
```

**Phase:** Phase 0 and Phase 1 boundary. Critical at the point where AISC dimensions feed Genesis geometry construction.

---

### Pitfall C6: Genesis `scene.build()` is Called Once — Scene Cannot be Rebuilt Between Candidate Positions

**What goes wrong:** The standard Genesis workflow is: add entities → `scene.build()` → run simulation. `scene.build()` triggers Taichi JIT compilation and allocates all GPU memory. There is no `scene.rebuild()` or dynamic entity repositioning API at scene level. Moving the robot base to a new candidate position requires either (a) using `robot.set_pos(new_base_pos)` + `robot.set_quat(...)` at the entity level after build, or (b) rebuilding the entire scene from scratch.

**Why it happens:** Genesis was designed for batched parallel environments (n_envs) where all variants are run simultaneously, not sequentially rebuilt. The sequential search loop pattern expected by this project is architecturally contrary to Genesis's primary use case.

**Consequences:** A naive implementation that calls `scene = gs.Scene(); scene.add_entity(robot); scene.build()` inside the search loop over candidate positions will JIT-compile for every candidate. At ~10–30 seconds per build on a modern GPU, a 1000-candidate search space takes 3–8 hours just in build overhead.

**Prevention:** Build the scene once with the robot at a neutral position. Use `robot.set_pos()` / joint state reset between candidates to reposition the base without rebuilding. Alternatively, use `n_envs` to evaluate a batch of candidate positions in parallel in a single build:

```python
scene = gs.Scene(n_envs=batch_size)
scene.add_entity(robot_urdf_morph, ...)
scene.build()
# Set different base positions per env using envs_idx
```

The `n_envs` approach is the correct Genesis idiom for this search pattern.

**Detection:** Time a single `scene.build()` call. If it takes > 5 seconds, multiply by your candidate count. If the product exceeds your time budget, you need the `n_envs` batch approach.

**Phase:** Phase 1 architecture design. Must be decided before the search loop is implemented.

---

## Moderate Pitfalls

Mistakes that waste significant time or produce incorrect results, but are recoverable.

---

### Pitfall M1: J5 Wrist Singularity — IK Converges but the Solution is Degenerate

**What goes wrong:** For a 6-DOF robot with a spherical wrist (FANUC M-20iD/12L has this), a wrist singularity occurs when J5 approaches 0° (axes of J4 and J6 become collinear). IK can still find a solution — the solver returns valid `qpos` with `err_pos` and `err_rot` below tolerance — but the Jacobian is rank-deficient at this configuration. Genesis's damped least-squares IK uses `damping=0.01` to regularize the near-singular Jacobian (line 1077 in `rigid_entity.py`), so it returns a solution rather than failing. The returned solution, however, may have J4 or J6 spinning to extreme values to compensate, making the path physically non-executable or requiring very high joint velocities.

**Why it happens:** Genesis IK does not detect or flag singularities. The damping prevents numerical blow-up but masks the singular condition from the caller.

**Consequences:** A path sweep that passes through a J5 singularity produces large, non-physical joint velocity spikes between adjacent path points. If this path is accepted, the robot cannot execute it at cutting speed without a motion fault.

**Prevention — Detection:** After computing `qpos` for a path point, check the J5 value:
```python
J5_IDX = 4  # 0-indexed, verify against FANUC URDF joint order
j5_angle_deg = np.degrees(qpos[J5_IDX])
J5_SINGULARITY_BAND_DEG = 5.0  # reject if J5 within ±5° of 0
if abs(j5_angle_deg) < J5_SINGULARITY_BAND_DEG:
    result = "SINGULARITY_J5"
```

Alternatively, compute the Jacobian condition number after getting `qpos`:
```python
J = robot.get_jacobian(tcp_link)  # shape (6, n_dofs)
J_np = J.cpu().numpy()
_, singular_values, _ = np.linalg.svd(J_np)
condition_number = singular_values[0] / singular_values[-1]
if condition_number > 50:   # empirical threshold; tune based on observed distribution
    result = "NEAR_SINGULAR"
```

The J5 angle check is simpler and more robust. Use it as primary rejection; reserve the Jacobian condition number for logging and threshold calibration.

**Phase:** Phase 1 search loop. One of the three explicit failure conditions from the spec.

---

### Pitfall M2: Wrist-Down vs Wrist-Up IK Configuration — Solver Returns Wrong Elbow

**What goes wrong:** Genesis IK uses random restarts (`max_samples=50`) with random `init_qpos` sampling. For a given TCP target, there are typically multiple IK solutions (wrist-up, wrist-down, elbow-left, elbow-right). The solver returns the best of 50 random starts, but "best" means smallest final error — not "most useful for this application." In a plasma cutting scenario where the torch must approach from above and the robot must stay clear of the beam, the wrist-up configuration is strongly preferred. The solver may return a wrist-down solution that passes IK error and joint limit checks but collides with the conveyor.

**Why it happens:** Genesis IK has no concept of preferred configuration. The `init_qpos` parameter allows seeding, but without a consistent seed the solver explores the full joint space randomly.

**Prevention:**
1. Provide `init_qpos` seeded from the robot's home posture (all-zeros or a known good configuration) to bias toward consistent elbow solutions.
2. After getting `qpos`, check J3 angle to discriminate wrist-up vs wrist-down — for the FANUC M-20iD, wrist-up configurations have J3 roughly in the range -45° to +90°; wrist-down inverts J2 and J3.
3. Run the collision check immediately after IK; a wrist-down collision with the conveyor is a rejection, not just a warning.

**Detection:** Visualize 10 IK solutions for a single known target position by calling `inverse_kinematics` 10 times with different `init_qpos` seeds. If you see both wrist-up and wrist-down configurations, add the seeding strategy.

**Phase:** Phase 1 path generation and IK calling convention.

---

### Pitfall M3: Collision Mesh Convexification Produces False Collision Pockets

**What goes wrong:** Genesis's URDF loader applies `convexify=True` by default for robot links (verified in `genesis/options/morphs.py` — `decompose_robot_error_threshold=float("inf")` means no decomposition unless explicitly overridden, but `convexify` itself defaults to True for FileMorph entities). Each non-convex mesh is replaced by its convex hull. For the FANUC M-20iD arm, the J3 link has a C-shaped cross section in certain configurations. The convex hull of that C-shape fills in the interior concavity — creating phantom collision volume where the real robot has open space.

**Why it happens:** Convex hulls are conservative by design. `coacd` decomposition is available (`coacd_options`) but is not automatically triggered for robot links unless `decompose_robot_error_threshold` is reduced below the 15% default for general objects. The robot threshold is `float("inf")` (line 503), meaning robot links are **never** decomposed into multiple convex parts by default.

**Consequences:** Candidate positions are rejected due to false collision detections at configurations where the physical robot would actually be clear. The search space is artificially shrunk. Block proxy models (the Phase 1 plan) avoid this for the environment, but the robot geometry itself still has this issue.

**Prevention:**
- For Phase 1 with block proxies, this is low risk — the robot geometry error is smaller than the block proxy conservatism anyway.
- When real STEP geometry is swapped in (post-Phase 1), add:
  ```python
  gs.morphs.URDF(
      file=urdf_path,
      decompose_robot_error_threshold=0.05,  # decompose links with >5% volume error
  )
  ```
- Accept that some conservatism in collision checking is correct — a placement that the simulation barely passes is riskier than one with margin.

**Detection:** After loading, call `scene.visualize()` and inspect the J3 link collision volume. If it fills in a concave region that is open on the real robot, convexification has created phantom volume.

**Phase:** Phase 1, latent. Becomes critical only when real geometry replaces block proxies.

---

### Pitfall M4: Work Zone Coordinate Frame Drift — Beam Frame vs World Frame

**What goes wrong:** The PROJECT.md defines work zones in feet relative to the pinch unit center: WZ1 = +1.5ft to +4.0ft downstream, WZ2 = -1.5ft to -3.0ft upstream. "Downstream" means along the beam travel direction. If the beam is loaded along the Genesis world X-axis, downstream is +X. But if the scene is built with Y as the beam travel direction (a common robotics convention where X is forward from the robot base), then the work zone bounds are applied to the wrong axis and all path points are generated in the wrong plane.

**Why it happens:** Genesis uses a default coordinate convention where Z is up, but X and Y for "forward" are not specified — they depend on how you orient the scene. ROS uses X-forward, Y-left, Z-up. The FANUC URDF from ros-industrial may place the robot with its J1 axis along the URDF Z-axis, which Genesis then maps to world Z. The beam conveyor travel direction must be explicitly defined and documented in the scene setup code, not assumed.

**Consequences:** Path points are generated in the correct shape (normal to faces, covering the MME) but at the wrong location in world space. IK is evaluated against wrong targets. The search finds "valid" placements for the wrong geometry.

**Prevention:**
1. At scene setup, define a scene manifest constant:
   ```python
   BEAM_TRAVEL_AXIS = np.array([1, 0, 0])   # +X is downstream
   WZ1_MIN_M = 1.5 * 0.3048   # convert ft to meters at definition time
   WZ1_MAX_M = 4.0 * 0.3048
   WZ2_MIN_M = -1.5 * 0.3048
   WZ2_MAX_M = -3.0 * 0.3048  # note: more negative = further upstream
   ```
2. Generate all path points using `BEAM_TRAVEL_AXIS` as the sweep axis. Never hardcode `x=`, `y=`, or `z=` in path generation — use axis-parameterized expressions.
3. Visualize the first path sweep over an H-beam before running any search.

**Detection:** Generate path points for WZ1 minimum position (+1.5ft = +0.457m) and verify in the Genesis viewer that the TCP target is downstream of the pinch unit by the expected visual distance.

**Phase:** Phase 1 scene setup and path generation.

---

### Pitfall M5: Foot-to-Meter Conversion Inconsistency — Work Zone Bounds Mix Units

**What goes wrong:** The specification document uses feet throughout (1.5ft, 4.0ft, 3.0ft). Genesis works in meters. AISC properties after `.to(ureg.meter)` are in meters. If any part of the code constructs work zone bounds in feet and path offsets in meters without explicit conversion at each boundary, the bounds will be 3.28x wrong.

**Why it happens:** Mixed-unit projects accumulate conversion errors at every interface. The AISC database, the specification document, and the Genesis engine all use different unit systems.

**Prevention:** Define a single module-level constant block at the top of the Phase 1 script:
```python
# All internal calculations in SI (meters, radians)
FT = 0.3048   # 1 foot in meters

WZ1_NEAR_M  =  1.5 * FT
WZ1_FAR_M   =  4.0 * FT
WZ2_NEAR_M  = -1.5 * FT
WZ2_FAR_M   = -(3.0 * FT + 1.5 * FT)  # dead_zone + WZ2_NEAR, see PROJECT.md

ROBOT_BASE_Z_MIN_M = 0.0
ROBOT_BASE_Z_MAX_M = 1.0   # 1000mm riser max
```

Do not perform ft-to-m conversions inline in path generation loops.

**Phase:** Phase 1 setup. Manifests as a subtle spatial error, not a crash.

---

### Pitfall M6: Manipulability Index Numerical Instability Near Singularities

**What goes wrong:** Manipulability is typically computed as `w = sqrt(det(J @ J.T))` where `J` is the 6×n Jacobian. Near a singularity, `det(J @ J.T)` approaches zero. Computing `sqrt` of a small negative float (from floating-point rounding when det should be exactly 0) produces `nan`. A `nan` manipulability score silently poisons the sorting of valid candidates — `nan > any_float` is False in Python, so `nan`-scored positions sort to the bottom but may not be detected as failures.

**Why it happens:** Genesis returns the Jacobian as a torch tensor via `robot.get_jacobian(link)`. The tensor is on GPU. Moving it to CPU with `.cpu().numpy()` may introduce small floating-point errors in near-singular cases.

**Consequences:** Search log has some entries with `manipulability=nan`. These are placed incorrectly in the sorted output. If the best valid position happens to be near a low-manipulability region (not singular, just lower w), `nan` entries above it in the sort pollute the recommendation.

**Prevention:**
```python
def compute_manipulability(J_np):
    """Numerically stable manipulability. Returns 0.0 near singularity."""
    JJT = J_np @ J_np.T
    eigenvalues = np.linalg.eigvalsh(JJT)   # symmetric, more stable than det
    eigenvalues = np.maximum(eigenvalues, 0.0)  # clamp floating-point negatives
    return float(np.sqrt(np.prod(eigenvalues)))
```

Using `eigvalsh` on `J @ J.T` instead of `det` is numerically more stable and naturally handles near-singular cases by clamping small negative eigenvalues to zero.

**Detection:** After computing manipulability for all valid candidates, `assert not np.any(np.isnan(scores))`. Add this assertion to the search loop logging step.

**Phase:** Phase 1 ranking/output step.

---

### Pitfall M7: Search Loop Local Optima — Reach-Bubble Pre-filter Creates Blind Spots

**What goes wrong:** The PROJECT.md correctly notes that a reach-bubble pre-filter should eliminate candidate positions outside the FANUC M-20iD/12L's 911mm reach. However, the pre-filter is typically based on the distance from the robot base to the centroid of the work zone, not to the worst-case TCP target point. A position that passes the centroid-distance filter may fail reachability for corner TCP points — specifically the bottom-face targets at the maximum beam depth (deep W-shapes near 300mm depth) at the far edge of WZ2.

**Why it happens:** The pre-filter is an approximation. The reachable workspace of a 6-DOF robot is not a sphere but an irregular torus with inner and outer radius. Pre-filtering by sphere-distance assumes the work zone fits entirely within the sphere, which is false for points at WZ2's far edge combined with maximum beam height.

**Consequences:** The search space is correctly thinned for the easy cases, but the hard constraints (WZ2 far edge + deep beam + bottom-face TCP) are under-sampled. Bayesian optimization may converge on a position that handles WZ1 perfectly but fails on the worst-case WZ2 point.

**Prevention:**
1. Pre-filter against the worst-case TCP point, not the centroid. The worst case is: WZ2 far edge (`WZ2_FAR_M`) + maximum beam depth below floor datum (for 4-face operations, the TCP must reach the bottom face through the conveyor roller gaps) + normal TCP orientation.
2. When using Bayesian optimization, include a hard constraint that all eight corner points of the combined work zone bounding box must be within the reach bubble before proposing the candidate to Genesis.
3. For the initial grid search (before Bayesian optimization takes over), use a coarser grid but ensure the WZ2 far-edge + max-depth corner is one of the evaluated target points in every IK batch.

**Phase:** Phase 1 search loop design. Affects the correctness of the reach-bubble pre-filter.

---

## Minor Pitfalls

Low severity but commonly encountered.

---

### Pitfall m1: ros-industrial FANUC URDF Package Path Resolution

**What goes wrong:** ros-industrial URDFs use `package://fanuc_m20id_support/meshes/...` paths. Genesis's URDF loader uses `urdfpy` (bundled in `genesis/ext/urdfpy/`) which resolves `package://` paths relative to the URDF file's directory if no ROS environment is present. If the URDF is cloned into `eden/assets/fanuc/` but the mesh files are in a subdirectory not at the expected relative path, mesh loading silently fails and the link renders as invisible (no geometry, no collision volume).

**Prevention:** After cloning, verify with `python -c "from genesis.ext import urdfpy; r = urdfpy.URDF.load('path/to/m20id12l.urdf'); print([l.name for l in r.links])"`. If links load but visuals are empty, the mesh paths are not resolving. Use absolute paths or symlink the mesh directories to match `package://` expectations.

**Phase:** Phase 1 setup.

---

### Pitfall m2: Genesis `fixed=True` Required for Floor-Mounted Robot

**What goes wrong:** If `fixed=True` is not set on the robot morph, Genesis treats the robot base as a free-floating body. During simulation, the robot will drift or fall through the floor. IK may still "work" because Genesis's IK is kinematic (does not check if the base moves), but the base position will not correspond to the tested candidate position after any simulation step.

**Prevention:** Always set `fixed=True` for the FANUC URDF morph. This is separate from `requires_jac_and_IK`.

**Phase:** Phase 1 scene setup.

---

### Pitfall m3: Genesis Quaternion Convention is W-X-Y-Z, Not X-Y-Z-W

**What goes wrong:** Genesis uses `(w, x, y, z)` quaternion convention (verified in `genesis/options/morphs.py` line 110: `self.quat = (1.0, 0.0, 0.0, 0.0)` for identity). scipy, ROS, and many IK utilities use `(x, y, z, w)`. If you compute a target orientation using scipy's `Rotation.from_euler(...)`, call `.as_quat()` (which returns x,y,z,w), and pass it directly to `robot.inverse_kinematics(quat=...)`, the orientation is silently wrong.

**Prevention:** Define a conversion wrapper at the top of Phase 1:
```python
def scipy_quat_to_genesis(q_xyzw):
    """Convert scipy (x,y,z,w) to Genesis (w,x,y,z)."""
    x, y, z, w = q_xyzw
    return np.array([w, x, y, z])
```

**Phase:** Phase 1 TCP orientation computation.

---

### Pitfall m4: L-Angle Orientation — Two Distinct MME Bounding Boxes Required

**What goes wrong:** The spec notes that L-angles "sit leg down on the conveyor like an inverted V" and that unequal legs require testing both orientations. Phase 0 must produce two distinct MME bounding boxes for unequal L-angles (L-long-leg-outboard vs L-short-leg-outboard), not one. If Phase 0 only computes one bounding box for all L-angles, the Phase 0 MME will be too conservative (using the maximum of both orientations everywhere) or too permissive (using the smaller orientation's bounds).

**Prevention:** In the Phase 0 filtering loop, detect L-shapes where `section.b != section.d` (unequal leg lengths). For these, compute the bounding box twice — once in each orientation — and produce two separate MME entries for the L category. Phase 1 then tests both orientations as separate beam types.

**Phase:** Phase 0 shape categorization.

---

## Phase-Specific Warning Matrix

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|----------------|------------|
| Phase 0 | AISC unit handling | Pint quantities in filter comparisons (C5) | Strip units using `.to().magnitude` pattern |
| Phase 0 | L-angle categorization | Single MME for both orientations (m4) | Two separate bounding boxes for unequal legs |
| Phase 1 setup | URDF loading | `requires_jac_and_IK=False` default (C1) | Explicit flag in morph, smoke test before search |
| Phase 1 setup | URDF scale | Scale compounding (C2) | Check flange position against known reach |
| Phase 1 setup | Robot base | Missing `fixed=True` (m2) | Always set in morph |
| Phase 1 setup | Coordinate frames | Beam axis not defined (M4) | Scene manifest constants, no hardcoded axes |
| Phase 1 path gen | TCP orientation | Wrong quaternion convention (m3) | Explicit conversion wrapper |
| Phase 1 path gen | Work zone bounds | Foot-meter mix (M5) | Single-location ft constant block |
| Phase 1 search loop | IK failure | No convergence status (C3) | `return_error=True`, explicit tolerance check |
| Phase 1 search loop | IK failure | Wrong elbow solution (M2) | Seed `init_qpos`, collision check catches it |
| Phase 1 search loop | IK failure | Joint limit violation (C4) | Post-IK limit audit |
| Phase 1 search loop | Singularity | J5 not detected (M1) | J5 angle band check + Jacobian condition number |
| Phase 1 search loop | Performance | Scene rebuilt per candidate (C6) | Build once, use `set_pos` or `n_envs` batch |
| Phase 1 search loop | Pre-filter | Centroid-only reach check misses WZ2 corners (M7) | Pre-filter against worst-case corner |
| Phase 1 ranking | Manipulability | `nan` from near-singular det (M6) | `eigvalsh` method, assert no nan in output |
| Post-Phase 1 | Collision geometry | Robot convex hull phantom volume (M3) | Set `decompose_robot_error_threshold` when real geometry arrives |
| Post-Phase 1 | Package paths | `package://` resolution without ROS (m1) | Test urdfpy.URDF.load independently |

---

## Sources

All Genesis findings verified from installed source code at:
`/mnt/intelligence/GitHub_Projects/MechanicalDesignTools/Robot_Simulations/eden/.venv/lib/python3.12/site-packages/genesis/`

Key files examined:
- `genesis/utils/urdf.py` — URDF parsing, scale handling, mimic joint encoding
- `genesis/options/morphs.py` — `requires_jac_and_IK` default, `convexify`/`decompose_robot_error_threshold` defaults
- `genesis/options/solvers.py` — `IK_max_targets` default (6)
- `genesis/engine/entities/rigid_entity/rigid_entity.py` — `inverse_kinematics()` signature, `return_error` behavior, default tolerances

AISC findings from:
- `engineering_tools/mech_core/components/members/aisc.py` — Pint wrapping in `__getattr__`

Project geometry from:
- `.planning/PROJECT.md`
- `Robot_Simulations/Optimizing_Robot_Placement.md`

Classical robotics pitfalls (singularity detection, manipulability, IK configuration selection) are established theory — confidence HIGH.
