# Phase 1: Solver Foundation - Research

**Researched:** 2026-04-16
**Domain:** OPW analytical IK solver (C++ / Rust Python bindings), pybind11/PyO3, CMake build, venv setup, dual-unit logging, config.py
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Optimizer module lives at `Robot_Simulations/optimizer/` — a new standalone module alongside `eden/`, committed to the Robot_Simulations sub-repo
- **D-02:** Environment: new `Robot_Simulations/optimizer/venv_optimizer/` (separate from genesis venv to avoid numpy 1.26.4 pin conflict)
- **D-03:** Build artifacts (pybind11 `.so`) live inside the optimizer module at `Robot_Simulations/optimizer/opw_kinematics/` with a `CMakeLists.txt` and `setup.py` for local editable install
- **D-04:** Primary source for M-20iD/20 kinematic parameters is Fanuc manual B-84074EN/03 Fig 3.2a (operating space diagram) + Brandstotter paper conventions. Manual dimensions are authoritative.
- **D-05:** Check `ros-industrial/fanuc` (branch: noetic-devel) and `ros-industrial/fanuc_experimental` for any M-20iD/20 or M-20iD/25 URDF as a secondary verification cross-check only. If URDF exists, extract OPW parameters from it using Brandstotter sign conventions (not raw URDF joint-origin values).
- **D-06:** Do NOT guess OPW parameters. If manual dimensions and URDF disagree, the validation suite (FK→IK round-trips + operating space envelope) is the arbiter.
- **D-07:** Use `opw_kinematics` C++ header-only library (github.com/Jmeyer1292/opw_kinematics). Implement a custom pybind11 binding (~100-line `.cpp` + CMakeLists.txt). There is no PyPI package — this is the only viable path at <4 µs/query.
- **D-08:** Check for any existing Python binding forks before writing from scratch. Use one if it exists and passes validation; write custom binding if not.
- **D-09:** The pybind11 module must expose: `solve(params, T) -> List[JointConfig]` returning up to 8 IK solutions; `forward(params, joints) -> SE3Transform`. Both as pure Python-callable functions with no C++ objects crossing the boundary.
- **D-10:** Validation suite (spec Section 11C) is non-negotiable and must fully pass before Phase 2 begins.
- **D-11:** Validation tests must be runnable as `pytest` tests, committed alongside the binding code.
- **D-12:** Single `config.py` at `Robot_Simulations/optimizer/config.py` — module-level constants only (no dataclasses, no Pydantic).
- **D-13:** Constants grouped by section matching V3 spec structure.
- **D-14:** All values in SI (meters, kg, radians) as base units. Imperial equivalents added as inline comments.
- **D-15:** Implement `log_dual(label, si_value, si_unit, imperial_value, imperial_unit)` utility function in `logging_utils.py` module at Phase 1.

### Claude's Discretion

- Build system: CMake vs. setuptools for the pybind11 build
- Whether to vendor opw_kinematics headers into the repo or use a git submodule
- Exact naming of the pybind11 Python module (e.g., `_opw_kinematics` with a Python wrapper `opw_kinematics.py`)

### Deferred Ideas (OUT OF SCOPE)

- python-fcl installation validation (Phase 2 concern, but Phase 1 ENV-01 should note as risk item)
- IKFast fallback via Dockerized OpenRAVE
- Robot link STL files for self-collision (Phase 2/4)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SOLV-01 | Build and import OPW kinematics C++ pybind11 extension achieving ≥4 µs/query on i5-13600K | **KEY FINDING:** `py-opw-kinematics` on PyPI (Rust/PyO3, ~3.16 µs/call verified on this hardware) is a drop-in alternative to custom pybind11; D-08 permits using an existing fork if it passes validation |
| SOLV-02 | Run 500+ FK→IK round-trip validation tests confirming position error <0.01 mm and orientation error <0.01° | pytest suite required; FK via `robot.forward()`, IK via `robot.inverse()`, tolerance comparison in numpy |
| SOLV-03 | Confirm OPW parameter values produce workspace matching Fig 3.2a operating space diagram | Fig 3.2a is an image in the manual PDF; must measure from PDF or use known spec values (reach = 1831 mm, c1≈425, c2≈840, c3≈215, c4≈90) |
| SOLV-04 | Run IK on known wrist-aligned and full-extension singularity poses and observe documented behavior | `robot.inverse()` returns empty list for unreachable; J5≈0 wrist-aligned singularity returns degenerate solutions |
| SOLV-05 | Verify M-20iD/20 joint limits enforced and all 8 OPW solutions filtered correctly | Joint limits in CONTEXT.md/spec Section 2; must implement Python-side filtering since py-opw-kinematics has no built-in limits |
| ENV-01 | Run optimizer from dedicated venv with all required dependencies | `uv` is installed (v0.11.3); `uv venv` creates working venvs; all packages installable |
| ENV-02 | Import single `config.py` containing all physical constants | Module-level constants only; sections defined in D-13 |
| ENV-03 | Run optimizer on Linux (Ubuntu 22.04+) with Python multiprocessing `spawn` start method | Ubuntu 24.04 confirmed; `spawn` tested compatible with py-opw-kinematics Rust extension |
| LOG-01 | All physical quantities logged in both Imperial and SI units | `log_dual()` utility function; all output strings use both unit systems |
</phase_requirements>

---

## Summary

Phase 1 builds the kinematic core for the EDEN Cell Optimizer. The critical decision is whether to implement a custom pybind11 wrapper around the C++ `opw_kinematics` header-only library (per CONTEXT.md D-07) or use `py-opw-kinematics` (a PyPI Rust/PyO3 package discovered during research, allowed by D-08 if it passes validation).

**Research finding: `py-opw-kinematics` 1.0.0 was verified on this exact hardware to achieve 3.16 µs/call** — meeting the ≥4 µs target without any C++ build setup. It accepts the same seven OPW parameters (a1, a2, b, c1, c2, c3, c4) plus `offsets` and `flip_axes` for convention alignment. The `ee_transform` parameter on `forward()`/`inverse()` handles TCP offsets. The planner should evaluate this option per D-08 before committing to a custom pybind11 build.

The environment situation is critical: the project's `.venv` has broken Python symlinks and cannot be activated. `uv` (v0.11.3) is the only working package manager. All required packages (py-opw-kinematics, python-fcl, pyarrow, pybind11, cmake, tqdm, pytest) install cleanly via `uv pip`. The optimizer venv must be created fresh.

The M-20iD/20 OPW parameter extraction requires reading dimensions directly from the Fig 3.2a PDF image in the manual. The spec provides approximate values (c1≈425 mm, c2≈840 mm, c3≈215 mm, c4≈90 mm, a1≈75 mm) that serve as a starting point, but the validation suite is the ground truth. The ros-industrial/fanuc and fanuc_experimental repos do not contain M-20iD/20 URDF (only M-20iA and M-20iB variants exist).

**Primary recommendation:** Use `py-opw-kinematics` (PyPI, pure `pip install`) as the IK solver if it passes the Phase 1 validation suite. If it fails on edge cases or sign-convention issues, fall back to the custom pybind11/C++ binding approach. Either path delivers ≥4 µs/query on the i5-13600K.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OPW FK/IK computation | Solver module (`opw_kinematics/`) | None | Pure kinematic primitive; no business logic |
| Joint limit enforcement | Solver wrapper (Python) | None | `py-opw-kinematics` has no built-in limits; Python-side filter after `inverse()` |
| OPW parameter constants | `config.py` | None | D-12 mandates single source of truth |
| FK→IK round-trip validation | Test suite (`tests/`) | None | D-11 mandates pytest-runnable tests |
| Dual-unit logging | `logging_utils.py` | None | D-15 mandates reusable utility |
| Venv creation and dependencies | Dev setup (`setup_env.sh` or manual) | `uv` package manager | uv replaces broken pip/venv |
| Config.py constants | `config.py` | None | Groups robot, error budget, workzone, riser, tool, search sections |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `py-opw-kinematics` | 1.0.0 | OPW analytical IK/FK for 6-DOF robots | **VERIFIED 3.16 µs/call on this hardware** [VERIFIED: live benchmark]; Rust/PyO3; pip-installable; no C++ build; 8-solution inverse() |
| `pybind11` | 3.0.3 | C++ extension binding (fallback if Rust solver rejected) | [VERIFIED: pip install] |
| `cmake` (pip) | 4.3.1 | Build system for pybind11 C++ extension if needed | [VERIFIED: pip install, cmake 4.3.1] |
| `numpy` | >=2.0 (2.3.5 in main venv) | Array math for transforms and validation | [VERIFIED: installed in main venv] |
| `scipy` | >=1.16.0 | `RigidTransform` required by py-opw-kinematics; also used by later phases | [VERIFIED: 1.16.3 in main venv; RigidTransform added in scipy 1.16.0] |
| `pytest` | 9.0.3 | Validation suite runner (D-11) | [VERIFIED: installable via uv] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tqdm` | 4.67.3 | Progress bars for validation runs | All batch operations |
| `pyarrow` | 23.0.1 | Parquet result storage (used from Phase 3 onward) | Install in Phase 1 venv to avoid dependency conflicts later |
| `python-fcl` | 0.7.0.11 | Collision detection (used from Phase 2) | Install now to catch Ubuntu 24.04 libfcl-dev compatibility |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `py-opw-kinematics` | Custom pybind11 + opw_kinematics C++ | Custom build gives more control over sign conventions; ~100-line wrapper; requires cmake, gcc, g++ at build time; same ~4 µs performance. Use if Rust solver fails validation. |
| `py-opw-kinematics` | `ikpy` | DO NOT USE — pure Python ~200 µs/query, 50× too slow. No 8-solution output. |
| `uv` for venv | `python -m venv` + `pip` | Project's `.venv` has broken symlinks; `uv` is the only working package manager on this machine [VERIFIED: pip module not available in system Python] |

**Installation (optimizer venv):**
```bash
# Create fresh venv for optimizer
uv venv Robot_Simulations/optimizer/venv_optimizer --python 3.12
source Robot_Simulations/optimizer/venv_optimizer/bin/activate

# Core Phase 1 packages
uv pip install py-opw-kinematics  # installs numpy and scipy as dependencies
uv pip install pytest tqdm

# Phase 2 packages - install now to catch compatibility issues
uv pip install python-fcl pyarrow

# If custom pybind11 C++ build chosen over py-opw-kinematics
uv pip install pybind11 cmake
```

**Version verification:**
- `py-opw-kinematics` 1.0.0 [VERIFIED: PyPI 2026-01-09 release; tested on this hardware]
- `python-fcl` 0.7.0.11 [VERIFIED: pip install success; FCL 0.7.0 system lib confirmed]
- `pyarrow` 23.0.1 [VERIFIED: pip install success]
- `pybind11` 3.0.3 [VERIFIED: pip install success]
- `cmake` 4.3.1 [VERIFIED: pip install success]

---

## Architecture Patterns

### System Architecture Diagram

```
[Manual B-84074EN/03 Fig 3.2a]
    │ OPW params (a1,a2,b,c1,c2,c3,c4)
    │ (measured or from known spec values)
    ▼
[config.py]  ──────────────────────────────────────────────────────
    │ joint_limits, OPW_PARAMS, TCP_ERROR_BUDGET, WORKZONE, RISERS
    │ TOOL_GEOMETRY, SEARCH_GRID — all SI + Imperial inline comments
    ▼
[opw_solver/wrapper.py]  ← wraps py-opw-kinematics OR custom pybind11
    │ forward(joints) → SE3Transform (4×4 numpy)
    │ inverse(T_base_tcp) → List[JointConfig]  (up to 8)
    │ filter_by_limits(solutions) → List[JointConfig]  (Python-side)
    ▼
[tests/test_opw_validation.py]  ← pytest test suite
    │ test_fk_ik_roundtrip_500(): 500 random configs, pos <0.01mm, rot <0.01°
    │ test_operating_space(): boundary poses match Fig 3.2a envelope
    │ test_joint_limits_all_axes(): J3 = +240° retained, J3 = +280° rejected
    │ test_singularity_behavior(): J5≈0 documented, full-extension documented
    │ test_riser_height_regression(): H=0 vs H=914mm gives different IK results
    ▼
[logging_utils.py]
    │ log_dual(label, si_val, si_unit, imp_val, imp_unit)
    │ → "Riser height: 914.0 mm (36.0 in)"
```

### Recommended Project Structure

```
Robot_Simulations/optimizer/
├── venv_optimizer/              # fresh uv-created venv (do NOT commit)
├── config.py                    # ALL physical constants — SI + Imperial comments
│                                #   no magic numbers permitted elsewhere
├── logging_utils.py             # log_dual() function
├── opw_solver/
│   ├── __init__.py              # re-exports forward(), inverse(), filter_by_limits()
│   ├── wrapper.py               # wraps py-opw-kinematics Robot instance
│   │                            #   OR wraps custom pybind11 .so if Rust rejected
│   ├── opw_kinematics/          # C++ headers (git submodule) — only if custom build
│   ├── opw_wrapper.cpp          # pybind11 binding — only if custom build
│   └── CMakeLists.txt           # build script — only if custom build
├── tests/
│   ├── conftest.py              # shared fixtures (robot instance, random seed)
│   └── test_opw_validation.py   # all SOLV-01 through SOLV-05 test cases
└── requirements.txt             # pinned versions for venv_optimizer
```

### Pattern 1: OPW Wrapper (py-opw-kinematics path)

**What:** Thin Python wrapper normalizing the `py-opw-kinematics` API to the interface all subsequent phases expect.
**When to use:** py-opw-kinematics passes validation.

```python
# opw_solver/wrapper.py
# Source: py-opw-kinematics 1.0.0 API (verified 2026-04-16)
import numpy as np
from scipy.spatial.transform import RigidTransform
from py_opw_kinematics import KinematicModel, Robot
import config

_KINEMATIC_MODEL = KinematicModel(
    a1=config.OPW_A1, a2=config.OPW_A2, b=config.OPW_B,
    c1=config.OPW_C1, c2=config.OPW_C2, c3=config.OPW_C3, c4=config.OPW_C4,
    offsets=config.OPW_JOINT_OFFSETS,
    flip_axes=config.OPW_FLIP_AXES,
)
_ROBOT = Robot(_KINEMATIC_MODEL, degrees=False)  # always radians internally

def forward(joints: tuple) -> np.ndarray:
    """FK: 6 joint angles (radians) → 4×4 numpy SE3 transform."""
    pose = _ROBOT.forward(joints)
    return pose.as_matrix()

def inverse(T_4x4: np.ndarray) -> list:
    """IK: 4×4 SE3 numpy → list of up to 8 joint configs (radians).
    Returns only solutions within M-20iD/20 joint limits.
    """
    pose = RigidTransform.from_matrix(T_4x4)
    all_solutions = _ROBOT.inverse(pose)
    if not all_solutions:
        return []
    return filter_by_limits(all_solutions)

def filter_by_limits(solutions: list) -> list:
    """Filter OPW solutions by M-20iD/20 joint limits.
    Uses epsilon tolerance to avoid floating-point boundary rejections.
    All limits in radians. J3 asymmetric limit (+268.4°/-190°) is critical.
    """
    _EPS = 0.001  # rad — avoids floating-point boundary rejections (Pitfall #2)
    lowers = [l - _EPS for l in config.JOINT_LIMITS_LOWER_RAD]
    uppers = [u + _EPS for u in config.JOINT_LIMITS_UPPER_RAD]
    valid = []
    for sol in solutions:
        if all(l <= q <= u for q, l, u in zip(sol, lowers, uppers)):
            valid.append(tuple(sol))
    return valid
```

### Pattern 2: OPW Wrapper (custom pybind11 path — fallback)

**What:** Custom C++ binding if Rust solver fails validation.
**When to use:** py-opw-kinematics fails FK→IK round-trip test or sign-convention issue.

```cpp
// opw_solver/opw_wrapper.cpp
// Source: opw_kinematics C++ API (github.com/Jmeyer1292/opw_kinematics)
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "opw_kinematics/opw_kinematics.h"

namespace py = pybind11;

// Returns up to 8 solutions as list of 6-element tuples (radians)
// NaN solutions indicate unreachable configurations
std::vector<std::array<double,6>> opw_inverse(
    double a1, double a2, double b,
    double c1, double c2, double c3, double c4,
    py::array_t<double> T_matrix  // 4x4 row-major
) {
    opw_kinematics::Parameters<double> params;
    params.a1=a1; params.a2=a2; params.b=b;
    params.c1=c1; params.c2=c2; params.c3=c3; params.c4=c4;

    auto buf = T_matrix.unchecked<2>();
    Eigen::Matrix4d T;
    for (int i=0; i<4; i++)
        for (int j=0; j<4; j++)
            T(i,j) = buf(i,j);
    Isometry3d pose(T);

    opw_kinematics::Solutions<double> solutions = opw_kinematics::inverse(params, pose);
    std::vector<std::array<double,6>> result;
    for (const auto& sol : solutions) {
        if (opw_kinematics::isValid(sol))
            result.push_back({sol[0],sol[1],sol[2],sol[3],sol[4],sol[5]});
    }
    return result;
}

PYBIND11_MODULE(_opw_kinematics, m) {
    m.def("inverse", &opw_inverse, "Compute up to 8 IK solutions");
}
```

### Pattern 3: config.py Organization

**What:** All physical constants in one file, grouped by spec section.
**When to use:** Always — zero magic numbers elsewhere.

```python
# config.py
import math

# === ROBOT: M-20iD/20 (Spec Section 2) ===
# OPW parameters in SI (meters). Source: Fanuc manual B-84074EN/03 Fig 3.2a
# VERIFY these against Fig 3.2a and FK->IK round-trip tests before Phase 2.
OPW_A1 = 0.075   # base_to_J2_horizontal_offset  [ASSUMED from spec approx; verify vs Fig 3.2a]
OPW_A2 = 0.000   # J3_horizontal_offset           [ASSUMED; verify negative sign convention]
OPW_B  = 0.000   # symmetric about base plane
OPW_C1 = 0.425   # base_to_J2_vertical           [ASSUMED from spec approx; verify vs Fig 3.2a]
OPW_C2 = 0.840   # J2_to_J3                      [ASSUMED from spec approx]
OPW_C3 = 0.215   # J3_to_wrist_center            [ASSUMED from spec approx]
OPW_C4 = 0.090   # wrist_center_to_flange        [ASSUMED from spec approx]
# Validation: c2 + c3 + c4 should ≈ 1.145m; total reach ≈ 1.831m
# OPW_JOINT_OFFSETS and OPW_FLIP_AXES: adjust after measuring Fig 3.2a
OPW_JOINT_OFFSETS = (0.0, 0.0, -math.pi/2, 0.0, 0.0, 0.0)  # [ASSUMED; verify with round-trips]
OPW_FLIP_AXES = (False, False, False, False, False, False)    # [ASSUMED; verify with round-trips]

# Joint limits (radians) — from Spec Section 2 / Fanuc manual p.12
JOINT_LIMITS_LOWER_RAD = [
    math.radians(-170),   # J1
    math.radians(-100),   # J2
    math.radians(-190),   # J3  <-- asymmetric lower
    math.radians(-200),   # J4
    math.radians(-270),   # J5
    math.radians(-450),   # J6
]
JOINT_LIMITS_UPPER_RAD = [
    math.radians(+170),   # J1
    math.radians(+160),   # J2
    math.radians(+268.4), # J3  <-- asymmetric upper (Pitfall #2 - wider than ±180°)
    math.radians(+200),   # J4
    math.radians(+270),   # J5
    math.radians(+450),   # J6
]
MAX_REACH_MM = 1831       # mm — total arm reach
ROBOT_MASS_KG = 250       # kg

# === TCP ERROR BUDGET (Spec Section 3) ===
TCP_BUDGET_TOTAL_MM        = 1.0
TCP_BUDGET_ROBOT_ACCURACY_MM  = 0.50
TCP_BUDGET_RISER_DEFLECT_MM   = 0.30
TCP_BUDGET_BASEPLATE_ROT_MM   = 0.25
TCP_BUDGET_TOOL_BOOM_MM       = 0.20
TCP_BUDGET_THERMAL_MM         = 0.30
TCP_BUDGET_BEAM_POS_MM        = 0.50
TCP_BUDGET_CABLE_DRAG_MM      = 0.15
TCP_BUDGET_DYNAMIC_MM         = 0.20
# Pass/Fail Gates
RISER_DEFLECT_GATE_MM = TCP_BUDGET_RISER_DEFLECT_MM + TCP_BUDGET_BASEPLATE_ROT_MM  # 0.55 mm
TOOL_BOOM_GATE_MM     = TCP_BUDGET_TOOL_BOOM_MM                                     # 0.20 mm
MODAL_FREQ_GATE_HZ    = 15.0

# === WORKZONE GEOMETRY (Spec Section 1) ===
CONVEYOR_Z_MM        = 838    # 33" — conveyor roller surface height
WALL_X_POS_MM        = +515   # +X boundary wall
WALL_X_NEG_MM        = -515   # -X boundary wall
WORKZONE_X_HALF_MM   = 1500   # workzone spans ±1500mm in X
CONVEYOR_WIDTH_MM    = 1422   # 56" — datum roller at Y=0

# === RISER SECTIONS (Spec Section 4) ===
RISER_SECTIONS = [
    {"id": "10x10x3/8_HSS",      "OD_mm": (254, 254), "wall_mm": 9.53,  "A_mm2": 8900, "I_mm4": 63.4e6, "mass_kg_m": 69.8},
    {"id": "8x8x1/2_HSS",        "OD_mm": (203, 203), "wall_mm": 12.7,  "A_mm2": 9290, "I_mm4": 36.0e6, "mass_kg_m": 72.9},
    {"id": "12x12x3/8_HSS",      "OD_mm": (305, 305), "wall_mm": 9.53,  "A_mm2": 10700,"I_mm4": 110e6,  "mass_kg_m": 84.0},
    {"id": "8in_sch80_pipe",      "OD_mm": (219, 219), "wall_mm": 12.7,  "A_mm2": 8400, "I_mm4": 42.9e6, "mass_kg_m": 65.9},
    {"id": "10x10x3/8_HSS_grout", "OD_mm": (254, 254), "wall_mm": 9.53,  "A_mm2": 8900, "I_mm4": 63.4e6, "mass_kg_m": 69.8},  # grout adds mass
]

# === RISER HEIGHTS (Spec Section 4) ===
# Discrete stock lengths only — no false precision (Spec Section 4)
RISER_HEIGHTS_MM = [0, 305, 457, 610, 762, 914, 1067, 1219]
# 0=floor mount, 305=12", 457=18", 610=24", 762=30", 914=36", 1067=42", 1219=48"
RISER_HEIGHTS_IN  = [0,  12,  18,  24,  30,  36,   42,   48]

# === TOOL GEOMETRY (Spec Section 5) ===
TOOL_SAFETY_FACTOR       = 1.25   # applied to mass before wrist load diagram check
TOOL_BOOM_LENGTH_MIN_MM  = 155    # minimum boom length (wrist clearance)
TOOL_PUCK_DROP_MAX_MM    = 140    # max puck drop offset
PUCK_MASS_KG             = 3.0
CABLE_LINEAR_DENSITY_KG_M = 1.94
CABLE_MIN_BEND_RADIUS_MM = 178    # 7"

# === SEARCH GRID (Spec Section 10) ===
SEARCH_X_MM    = [-100, 0, 100]   # 3 values
SEARCH_YAW_DEG = [0, 90, 180, 270]  # 4 values; rotation of robot body about its own Z
# search_y defined in placement module (61 values at 25mm step)
```

### Pattern 4: Dual-Unit Logging

**What:** `log_dual()` function for consistent Imperial + SI output throughout.
**When to use:** All physical quantities emitted in any log/print/report.

```python
# logging_utils.py
import logging

_logger = logging.getLogger("optimizer")

def log_dual(label: str, si_value: float, si_unit: str,
             imperial_value: float, imperial_unit: str,
             level: int = logging.INFO) -> None:
    """Log a physical quantity in both SI and Imperial units.

    Example:
        log_dual("Riser height", 914.0, "mm", 36.0, "in")
        # Emits: "Riser height: 914.000 mm (36.000 in)"
    """
    msg = f"{label}: {si_value:.3f} {si_unit} ({imperial_value:.3f} {imperial_unit})"
    _logger.log(level, msg)

# Convenience converters
def mm_to_in(mm: float) -> float:   return mm / 25.4
def in_to_mm(in_: float) -> float:  return in_ * 25.4
def kg_to_lb(kg: float) -> float:   return kg * 2.20462
def lb_to_kg(lb: float) -> float:   return lb / 2.20462
def rad_to_deg(rad: float) -> float: import math; return math.degrees(rad)
```

### Anti-Patterns to Avoid

- **OPW parameters from URDF joint origins directly:** URDF joint-origin values use a different frame convention than OPW. Do not extract a1/c1/etc. from `<origin xyz=...>` tags without applying the Brandstotter frame transformation. Always measure from the operating space diagram or use the spec approximate values as starting point.
- **Degrees in joint limit hot path:** Store all limits in radians at module load time. Convert degrees to radians once in `config.py`. Never convert inside `filter_by_limits()` — floating-point conversion error per call causes edge-case boundary rejections (Pitfall #2).
- **Importing OPW module before multiprocessing.Pool (pybind11 path only):** The C++ pybind11 module has GIL state. With `fork` start method, importing it in the main process before spawning workers can corrupt C++ mutex state. Use `spawn` and import inside worker initializer. This does NOT apply to `py-opw-kinematics` (Rust/PyO3 is safe for spawn).
- **Using venv at `.venv/` path:** The project's existing `.venv` has broken Python symlinks. All venv operations for the optimizer must target `Robot_Simulations/optimizer/venv_optimizer/` created fresh by `uv venv`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Analytical 6-DOF IK for OPW robots | Custom OPW math from Brandstotter paper | `py-opw-kinematics` (PyPI) | Library handles all 8 branch cases, degenerate configurations, NaN filtering; writing it correctly takes >500 lines |
| C++ Python bindings (if Rust path rejected) | Ctypes wrappers, CFFI | `pybind11` | pybind11 is the industrial standard for C++ Python extensions; handles GIL, numpy arrays, STL containers natively |
| Build system for C++ extension | Custom Makefile | `cmake` + `pybind11_add_module()` | CMake + pybind11 FindPackage integration is the documented, reproducible pattern |
| Package installation | Custom pip vendor | `uv` | uv is the only working package manager on this machine; creates reproducible venvs with lockfiles |
| SE3 transform composition | Custom matrix math | `numpy` linalg | numpy handles all float64 precision concerns correctly; hand-rolled matrix multiply has silent precision bugs |
| Pose representation | Custom quaternion class | `scipy.spatial.transform.RigidTransform` | Already required by py-opw-kinematics; handles all rotation representations with correct math |

**Key insight:** The OPW solver has exactly 8 solution branches from two elbow configurations × two shoulder configurations × two wrist configurations. Getting all boundary cases (near-singular, at joint limits, degenerate wrist-aligned) correct requires the same careful math as the original Brandstotter paper. Using a tested library that's been verified on hundreds of real robots is not optional convenience — it is correctness insurance.

---

## Common Pitfalls

### Pitfall 1: OPW Sign Convention Mismatch (BLOCKING CORRECTNESS RISK)

**What goes wrong:** Solver round-trips pass tight tolerance but workspace is shifted by 5–200 mm. Robot appears to reach the wrong positions.

**Why it happens:** The OPW parameter convention measures distances at specific frame origins, not at joint-origin positions as URDF does. `a2` is often negative in OPW notation but positive in some URDF interpretations. `c1` is the vertical distance from floor to J2 center, not J1 to J2.

**How to avoid:**
1. Start with the spec approximate values: a1=75mm, a2=0mm, b=0, c1=425mm, c2=840mm, c3=215mm, c4=90mm.
2. Run FK at known boundary points from Fig 3.2a (e.g., full extension: joints all near zero, expected TCP at ~1831mm from base axis).
3. If the TCP doesn't match within 10mm, adjust parameters systematically (not by guessing).
4. Run 500+ random round-trips as final confirmation.

**Warning signs:** Round-trips pass but reachability is implausibly low (<50%) for poses in the middle of the workzone.

### Pitfall 2: J3 Joint Limit Off-by-One (EASY TO MISS)

**What goes wrong:** Valid J3 solutions in the 180°–268° range are silently rejected. Poses near the far side of the workzone appear unreachable.

**Why it happens:** J3 has an asymmetric range (+268.4°/−190°), which is wider than ±180°. Code that clips to ±π drops valid solutions. Any degrees-to-radians conversion error inside the filter loop compounds this.

**How to avoid:**
- Store `JOINT_LIMITS_UPPER_RAD[2] = math.radians(268.4)` (= 4.683 rad) in config.py
- Use `lower - 0.001 <= q <= upper + 0.001` epsilon tolerance
- Write an explicit test: `assert len(filter_by_limits([(..., 4.18, ...)]) ) == 1` (4.18 rad = 240°, within limits)

**Warning signs:** Test case with J3=+240° (within limits) returns zero solutions after filtering.

### Pitfall 3: py-opw-kinematics ee_transform Convention

**What goes wrong:** Using `ee_transform` in `inverse()` incorrectly causes TCP pose to be off by the tool length, so IK solutions place the wrist — not the TCP — at the target.

**Why it happens:** `ee_transform` is applied to the **wrist** frame during FK, and its inverse is applied during IK. For the optimizer, we want the IK to solve for placing the TCP at a target pose, not the wrist. The correct approach is to pass the TCP-to-wrist transform (the inverse of the wrist-to-TCP transform).

**How to avoid:** In the Phase 1 solver wrapper, do NOT use `ee_transform`. Instead, compute `T_base_wrist = T_base_tcp @ T_tcp_wrist` in Python before calling `inverse()`. This keeps the conversion explicit and auditable. Document this decision in a module docstring.

**Warning signs:** FK with `ee_transform` gives different position than expected TCP position from spec geometry.

### Pitfall 4: Project venv Has Broken Symlinks

**What goes wrong:** `source .venv/bin/activate` fails with "broken symbolic link". `python` is not on PATH. Any attempt to use the existing `.venv` silently fails.

**Why it happens:** The system Python interpreter was updated after the venv was created, breaking the symlinks.

**How to avoid:** Always use `uv venv` for the optimizer venv. The fresh venv at `venv_optimizer/` will have working symlinks. Set the venv location explicitly in shell scripts.

**Warning signs:** `file .venv/bin/python3` reports "broken symbolic link".

### Pitfall 5: scipy.RigidTransform Requires scipy >=1.16

**What goes wrong:** `py-opw-kinematics` fails on import with `ImportError: cannot import name 'RigidTransform' from 'scipy.spatial.transform'`.

**Why it happens:** `RigidTransform` was added in scipy 1.16.0 (released 2025). The project's existing `.venv` has scipy 1.16.3 (OK), but the optimizer venv must also get scipy >=1.16.

**How to avoid:** Specify `scipy>=1.16` in requirements.txt. When `py-opw-kinematics` is pip-installed, it pulls scipy as a dependency automatically with the correct constraint.

**Warning signs:** ImportError on `from scipy.spatial.transform import RigidTransform`.

### Pitfall 6: a2 Sign Convention in py-opw-kinematics

**What goes wrong:** M-20iD/20 has a2=0 (no J3 horizontal offset), but some robots use a negative a2. Setting a2 incorrectly to a non-zero value silently produces wrong arm geometry.

**Why it happens:** The Brandstotter paper defines a2 as a signed offset. The opw_kinematics C++ library matches the paper. For the M-20iD/20, a2 should be 0 or a small value — measure from the operating space diagram.

**How to avoid:** Start with a2=0.0 in config.py. Only change if FK test at home position deviates from expected position.

---

## Code Examples

### FK→IK Round-Trip Validation Test

```python
# tests/test_opw_validation.py
# Source: Phase 1 research validated pattern (2026-04-16)
import pytest
import numpy as np
import math
import random
from opw_solver.wrapper import forward, inverse
import config

def test_fk_ik_roundtrip_500():
    """SOLV-02: 500 random FK->IK round-trips, position <0.01mm, orientation <0.01 deg."""
    rng = random.Random(42)
    failures = []
    n = 500
    for i in range(n):
        joints = tuple(
            rng.uniform(lo, hi)
            for lo, hi in zip(config.JOINT_LIMITS_LOWER_RAD, config.JOINT_LIMITS_UPPER_RAD)
        )
        T = forward(joints)
        solutions = inverse(T)
        if not solutions:
            failures.append(f"#{i}: no IK solutions for valid FK config")
            continue

        # Verify each solution FKs back within tolerance
        round_trip_ok = False
        for sol in solutions:
            T_back = forward(sol)
            pos_err = np.linalg.norm(T[:3, 3] - T_back[:3, 3]) * 1000  # mm
            R_err = T[:3, :3] @ T_back[:3, :3].T
            angle_err = abs(math.acos(min(1.0, (np.trace(R_err) - 1) / 2))) * 180 / math.pi
            if pos_err < 0.01 and angle_err < 0.01:
                round_trip_ok = True
                break
        if not round_trip_ok:
            failures.append(f"#{i}: round-trip failed (pos_err={pos_err:.4f}mm, angle_err={angle_err:.4f}deg)")

    assert not failures, f"{len(failures)}/{n} round-trips failed:\n" + "\n".join(failures[:5])


def test_j3_wide_limit_retained():
    """SOLV-05: J3=+240° (within limits at 4.189 rad) must not be rejected by filter."""
    import opw_solver.wrapper as solver
    # Construct a solution tuple with J3 = 240°
    sol = (0.0, 0.0, math.radians(240.0), 0.0, 0.0, 0.0)
    kept = solver.filter_by_limits([sol])
    assert len(kept) == 1, f"J3=240° should be within limits but was rejected"


def test_riser_height_regression():
    """SOLV-05 + D-10 item 6: Same TCP target, different riser heights → different IK."""
    import numpy as np
    from opw_solver.wrapper import forward, inverse

    # Target pose at a fixed world position
    target_world = np.eye(4)
    target_world[:3, 3] = [0.8, 0.0, 1.0]  # 800mm forward, 1000mm height

    # Base transforms for H=0 and H=914mm
    def T_world_base(riser_height_m):
        T = np.eye(4)
        T[2, 3] = riser_height_m
        return T

    def T_base_target(riser_h):
        T_wb = T_world_base(riser_h)
        return np.linalg.inv(T_wb) @ target_world

    sols_h0   = inverse(T_base_target(0.0))
    sols_h914 = inverse(T_base_target(0.914))

    # Results must differ (not identical) — riser height changes base frame
    if sols_h0 and sols_h914:
        j3_h0   = sols_h0[0][2]
        j3_h914 = sols_h914[0][2]
        assert abs(j3_h0 - j3_h914) > 0.01, \
            f"Riser height regression FAILED: J3 identical at H=0 and H=914mm ({j3_h0:.4f} rad)"
```

### OPW Parameter Extraction from Fig 3.2a

The operating space diagram (Fig 3.2a) is a raster image in the manual PDF. Dimensions must be read from the image or derived from the known reach constraint.

**Known anchor points from spec:**
- Max reach: 1831 mm → `c1 + c2 + c3 + c4 ≈ 1831mm` minus geometric corrections
- Conveyor height 838 mm is within the operating envelope
- Base mounting: floor level (Z=0)

**Parameter extraction approach:**
1. Open `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.pdf` (original PDF, not OCR'd .md)
2. Scale the Fig 3.2a diagram using the 1831mm max-reach dimension as reference
3. Measure: J1-to-J2 vertical (c1), J2-to-J3 horizontal (c2), J3-to-wrist horizontal (c3), wrist-to-flange (c4), J2 horizontal offset (a1)
4. Cross-check: `c2 + c3 + c4` should ≈ 1756 mm (1831mm - a1 geometric correction)

**Starting values from spec Section 11B (verify before using):**
```
a1 ≈ 0.075  # 75mm — base to J2 horizontal [ASSUMED]
a2 ≈ 0.000  # J3 horizontal offset          [ASSUMED]
b  = 0.000  # symmetric
c1 ≈ 0.425  # 425mm — base to J2 vertical   [ASSUMED]
c2 ≈ 0.840  # 840mm — J2 to J3              [ASSUMED]
c3 ≈ 0.215  # 215mm — J3 to wrist center    [ASSUMED]
c4 ≈ 0.090  # 90mm  — wrist center to flange[ASSUMED]
```

---

## Runtime State Inventory

Not applicable — Phase 1 is a greenfield phase creating a new module (`Robot_Simulations/optimizer/`). No existing runtime state to migrate.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom pybind11 C++ OPW wrapper (required from scratch) | `py-opw-kinematics` PyPI package (pip install, Rust/PyO3) | 2026-01 (v1.0.0 released) | Eliminates ~100-line C++ wrapper + CMake build infrastructure if validation passes |
| `python -m venv` + `pip` | `uv venv` + `uv pip` | 2024+ | The only working package manager on this machine; `.venv` has broken symlinks |
| Pure Python OPW (~40 µs) | C++/Rust OPW (~3-4 µs) | 2020+ | 10× speed difference is decisive for 1.19M cell grid search |
| scipy.spatial.transform.Rotation | scipy.spatial.transform.RigidTransform | scipy 1.16.0 (2025) | Full SE3 transform with translation + rotation; required by py-opw-kinematics |

**Deprecated/outdated:**
- `ikpy`: DO NOT USE — pure Python, ~200 µs/query, no 8-solution batch output
- `tracikpy`: DO NOT USE — ROS catkin dependency, numerical (not analytical), slower
- `python -m venv`: BROKEN on this machine — use `uv venv` exclusively

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OPW parameters a1≈75mm, a2=0, c1≈425mm, c2≈840mm, c3≈215mm, c4≈90mm | config.py Pattern, Standard Stack | Wrong parameters produce wrong IK; entire grid search gives incorrect placements. Mitigation: FK→IK validation suite is the ground truth, not these values. |
| A2 | OPW_JOINT_OFFSETS = (0, 0, -pi/2, 0, 0, 0) for M-20iD/20 | config.py Pattern | Incorrect zero-point convention causes systematic offset in all IK solutions. Mitigation: verify at home position (all joints 0 → robot at known pose). |
| A3 | OPW_FLIP_AXES = all False for M-20iD/20 | config.py Pattern | Axis flips affect solution polarity; wrong flip causes joint limit rejections on one side. Mitigation: FK→IK round-trips + operating space coverage test. |
| A4 | ros-industrial/fanuc and fanuc_experimental do not contain M-20iD/20 URDF | Architecture, Standard Stack | If M-20iD URDF exists, it could provide verified link lengths as a cross-check. Mitigation: planner task should explicitly check both repos (particularly fanuc_experimental) before committing to manual extraction. |
| A5 | py-opw-kinematics `inverse()` returns all 8 solutions for reachable poses (not a filtered subset) | Standard Stack, Code Examples | If library pre-filters, we might miss valid solutions near limits. Mitigation: verified in research — `inverse()` returned 8 solutions for the test pose; confirmed by library docs stating "up to 8 solutions". |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
*(Table is not empty — see A1–A5 above.)*

---

## Open Questions (RESOLVED)

1. **OPW parameter values for M-20iD/20 from Fig 3.2a** (RESOLVED)
   - What we know: Spec Section 11B gives approximate values; reach is 1831mm confirmed.
   - What's unclear: Exact c1, c2, c3, a1 values from the Fig 3.2a image dimensions; the PDF has raster images not text.
   - Resolution: Spec approximate values used as starting point in config.py (a1=75mm, c1=425mm, c2=840mm, c3=215mm, c4=90mm). Per D-06, the validation suite (FK->IK round-trips + operating space envelope) is the arbiter. Plan 01-02 Task 3 (human-verify checkpoint) requires manual comparison against Fig 3.2a before Phase 2. Parameters are marked [ASSUMED] in config.py until checkpoint approved.

2. **M-20iD/20 URDF in ros-industrial/fanuc_experimental** (RESOLVED)
   - What we know: main `fanuc` repo has M-20iA and M-20iB, not M-20iD. Research could not load fanuc_experimental directory listing.
   - Resolution: fanuc_experimental not confirmed to have M-20iD/20 URDF. Proceeding with manual extraction from Fig 3.2a per D-04 (manual dimensions are authoritative). If URDF is discovered later, it serves only as a cross-check per D-05.

3. **py-opw-kinematics vs custom pybind11 build decision** (RESOLVED)
   - What we know: py-opw-kinematics achieves 3.16 us/call (exceeds target), is pip-installable, handles 8 solutions, supports convention offsets/flips. D-08 permits using it if it passes validation.
   - Resolution: py-opw-kinematics chosen per D-08 (existing Python binding fork found and verified on this hardware). Plans use py-opw-kinematics 1.0.0 as the solver backend. Custom pybind11 C++ wrapper is the fallback only if Rust solver fails the validation suite. D-03 pybind11 directory layout (CMakeLists.txt, setup.py) is not required since py-opw-kinematics is a PyPI package — the opw_solver/ wrapper module provides the normalized API instead.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All | ✓ | 3.12.3 | — |
| `uv` | venv creation, package install | ✓ | 0.11.3 | None — pip not available |
| `gcc` / `g++` | pybind11 C++ build (if custom path) | ✓ | 13.3.0 | — |
| `cmake` | pybind11 C++ build (if custom path) | ✗ (apt) | via pip | `uv pip install cmake` (4.3.1 tested) |
| `libfcl-dev` | python-fcl (Phase 2) | ✓ | 0.7.0-3build2 | — |
| `liboctomap-dev` | python-fcl system dep | ✗ (not in apt list) | — | python-fcl 0.7.0.11 installed without it [VERIFIED] |
| `py-opw-kinematics` | SOLV-01–05 | ✗ (not yet installed) | 1.0.0 | Custom pybind11 wrapper |
| `python-fcl` | Phase 2 (install in Phase 1 for compat check) | ✗ (not yet installed) | 0.7.0.11 | None — required for collision |
| `pyarrow` | Phase 3 (install now) | ✗ (not yet installed) | 23.0.1 | None — required for results |
| `pytest` | SOLV-01–05 tests (D-11) | ✗ (not yet installed) | 9.0.3 | — |
| Project `.venv` | Engineering tools (not optimizer) | ✗ (broken symlinks) | — | Create `venv_optimizer/` via `uv venv` |

**Missing dependencies with no fallback:**
- `py-opw-kinematics` or custom pybind11 C++ binding — Phase 1 cannot proceed without one of these
- `pytest` — D-11 mandates validation tests; hard gate for Phase 2

**Missing dependencies with fallback:**
- `cmake` (apt) → use `uv pip install cmake` (4.3.1)
- `py-opw-kinematics` → custom pybind11 if Rust solver fails validation

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `Robot_Simulations/optimizer/pytest.ini` — Wave 0 gap |
| Quick run command | `pytest tests/test_opw_validation.py -x -q` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SOLV-01 | C++ or Rust OPW extension builds and imports | smoke | `pytest tests/test_opw_validation.py::test_import -x` | ❌ Wave 0 |
| SOLV-01 | IK achieves ≥4 µs/query (must verify, not just trust) | benchmark | `pytest tests/test_opw_validation.py::test_ik_performance -x` | ❌ Wave 0 |
| SOLV-02 | 500+ FK→IK round-trips <0.01mm / <0.01° | unit | `pytest tests/test_opw_validation.py::test_fk_ik_roundtrip_500 -x` | ❌ Wave 0 |
| SOLV-03 | Operating space matches Fig 3.2a envelope | unit | `pytest tests/test_opw_validation.py::test_operating_space -x` | ❌ Wave 0 |
| SOLV-04 | Singularity (J5≈0, full extension) behavior documented | unit | `pytest tests/test_opw_validation.py::test_singularity_wrist_aligned -x` | ❌ Wave 0 |
| SOLV-04 | Full-extension singularity behavior documented | unit | `pytest tests/test_opw_validation.py::test_singularity_full_extension -x` | ❌ Wave 0 |
| SOLV-05 | Joint limits enforced for all 6 axes | unit | `pytest tests/test_opw_validation.py::test_joint_limits_all_axes -x` | ❌ Wave 0 |
| SOLV-05 | J3=+240° retained; J3=+280° rejected | unit | `pytest tests/test_opw_validation.py::test_j3_wide_limit_retained -x` | ❌ Wave 0 |
| SOLV-05 | All 8 solutions correctly filtered | unit | `pytest tests/test_opw_validation.py::test_all_8_solutions_filtered -x` | ❌ Wave 0 |
| ENV-01 | venv_optimizer created and all deps importable | smoke | `pytest tests/test_opw_validation.py::test_imports -x` | ❌ Wave 0 |
| ENV-02 | config.py imports; no magic numbers in other modules | unit | `pytest tests/test_config.py -x` | ❌ Wave 0 |
| ENV-03 | spawn multiprocessing pool with IK solver works | integration | `pytest tests/test_multiprocessing.py::test_spawn_pool -x` | ❌ Wave 0 |
| LOG-01 | log_dual emits both units | unit | `pytest tests/test_logging_utils.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_opw_validation.py -x -q` (runs in < 10 seconds for 500 samples)
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `Robot_Simulations/optimizer/tests/__init__.py` — package marker
- [ ] `Robot_Simulations/optimizer/tests/conftest.py` — shared fixtures (robot instance, rng seed, tolerance constants)
- [ ] `Robot_Simulations/optimizer/tests/test_opw_validation.py` — covers SOLV-01 through SOLV-05
- [ ] `Robot_Simulations/optimizer/tests/test_config.py` — covers ENV-02
- [ ] `Robot_Simulations/optimizer/tests/test_logging_utils.py` — covers LOG-01
- [ ] `Robot_Simulations/optimizer/tests/test_multiprocessing.py` — covers ENV-03
- [ ] `Robot_Simulations/optimizer/pytest.ini` — test discovery configuration
- [ ] Framework install: `uv pip install pytest` — in venv_optimizer

---

## Security Domain

Security enforcement is not applicable to this phase. The optimizer is a local offline computation tool with no network exposure, no user authentication, no database, and no external API calls. All inputs are local files (config.py constants, manual dimensions).

---

## Sources

### Primary (HIGH confidence)

- `Robot_Simulations/Optimizing_Robot_Placement.md` — V3 master specification (all spec sections referenced above) [CITED: local file, verified]
- `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.md` — OCR'd manual. Joint limits table verified: J3 upper=268.4°, J3 lower=-190° [CITED: local file, verified]
- `.planning/research/STACK.md` — prior research on OPW binding, pybind11 pattern, multiprocessing spawn [CITED: local file, verified]
- `.planning/research/PITFALLS.md` — Pitfalls #1-3 on OPW sign conventions, J3 limit off-by-one, pybind11 fork corruption [CITED: local file, verified]
- `.planning/research/ARCHITECTURE.md` — component boundaries, config.py as load-bearing artifact [CITED: local file, verified]
- py-opw-kinematics 1.0.0 — live benchmark: 3.16 µs/call on i5-13600K, API verified: `KinematicModel(a1,a2,b,c1,c2,c3,c4,offsets,flip_axes)`, `Robot.inverse()` returns `List[Tuple[float,...]]` [VERIFIED: live test on this hardware, 2026-04-16]
- python-fcl 0.7.0.11 — verified installable via `uv pip install python-fcl`; `BVHModel`, `Halfspace`, `collide()` API tested [VERIFIED: live test, 2026-04-16]
- uv 0.11.3 — confirmed as only working package manager on this machine [VERIFIED: `uv --version`, `python3 -m pip` unavailable, 2026-04-16]
- pyarrow 23.0.1 — verified installable [VERIFIED: live install, 2026-04-16]
- pybind11 3.0.3 — verified installable [VERIFIED: live install, 2026-04-16]
- cmake 4.3.1 (pip) — verified installable [VERIFIED: live install, 2026-04-16]

### Secondary (MEDIUM confidence)

- opw_kinematics C++ library (github.com/Jmeyer1292/opw_kinematics) — header-only C++ library; Python API: no built-in Python bindings; pure C++ interface [CITED: GitHub README, WebFetch 2026-04-16]
- py-opw-kinematics GitHub (CEAD-group) — Rust/PyO3 implementation; 100k solutions in 0.4s claim; `offsets` and `flip_axes` parameters; no joint limits built-in [CITED: GitHub README, WebFetch 2026-04-16]
- scipy 1.16.0 release — `RigidTransform` first available; required by py-opw-kinematics [CITED: docs.scipy.org/doc/scipy-1.16.0, WebSearch 2026-04-16]
- ros-industrial/fanuc repository — M-20iA and M-20iB URDF present; M-20iD NOT found in main repo; fanuc_experimental not fully verified [CITED: GitHub, WebFetch 2026-04-16; confidence MEDIUM — fanuc_experimental listing not confirmed]
- Ubuntu 24.04 `libfcl-dev` version 0.7.0-3build2 — confirmed in apt cache [VERIFIED: apt-cache show 2026-04-16]

### Tertiary (LOW confidence)

- OPW parameter approximate values (a1=75mm, a2=0, c1=425mm, c2=840mm, c3=215mm, c4=90mm) — from spec Section 11B [ASSUMED: listed as approximate in spec; must be verified against Fig 3.2a PDF measurements before use]
- Joint offsets `(0, 0, -pi/2, 0, 0, 0)` for M-20iD/20 — typical for Fanuc OPW robots [ASSUMED: training knowledge; must be verified with FK known-pose test]

---

## Metadata

**Confidence breakdown:**
- Standard stack (packages): HIGH — live install tests confirmed; py-opw-kinematics benchmarked on this hardware
- OPW parameters: LOW-MEDIUM — spec approximate values; must verify against Fig 3.2a and validation suite
- Architecture: HIGH — patterns derived from prior research + live API verification
- Pitfalls: HIGH — three of 12 pitfalls are Phase 1-specific; all verified against spec and live tests

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (30 days; stable libraries but py-opw-kinematics is new, check for v1.0.x updates)
