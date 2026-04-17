# Phase 1: Solver Foundation - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 7 new files to be created
**Analogs found:** 5 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `Robot_Simulations/optimizer/config.py` | config | transform (constants → import) | `engineering_tools/simulation/DES/core/machines/PCR41/config.py` | role-match |
| `Robot_Simulations/optimizer/logging_utils.py` | utility | transform | `engineering_tools/simulation/DES/core/logging/logger.py` | partial-match |
| `Robot_Simulations/optimizer/opw_solver/__init__.py` | utility | request-response | `engineering_tools/mech_core/standards/units.py` | partial-match |
| `Robot_Simulations/optimizer/opw_solver/wrapper.py` | service | request-response | `engineering_tools/simulation/DES/core/machines/subsystems/robots/robot_arm.py` | role-match |
| `Robot_Simulations/optimizer/tests/conftest.py` | test | — | none | no-analog |
| `Robot_Simulations/optimizer/tests/test_opw_validation.py` | test | batch | `engineering_tools/simulation/DES/tests/test_gas_jets.py` | role-match |
| `Robot_Simulations/optimizer/tests/test_config.py` | test | — | `engineering_tools/simulation/DES/tests/test_safety_plc.py` | role-match |

---

## Pattern Assignments

### `Robot_Simulations/optimizer/config.py` (config, constants)

**Analog:** `engineering_tools/simulation/DES/core/machines/PCR41/config.py`

**Imports pattern** (lines 1-8 of analog):
```python
# No imports needed in config.py except math for unit conversions.
# The PCR41 config.py uses zero imports — pure constant assignments only.
# Follow the same pattern: import math, nothing else.
import math
```

**Core pattern** (lines 1-71 of analog — section-header grouping with inline docs):
```python
# ==========================================
# Window Geometry (mm)
# ==========================================

#: Processing window width - features larger than this must be bisected
WINDOW_WIDTH = 200.0

#: Safety buffer at window boundaries for clamp positioning
CLAMP_OVERLAP = 50.0
```

**Adaptation for optimizer config.py:**
- Replace `# ====` section separators from PCR41 config with `# === SECTION NAME (Spec Section N) ===` per D-13.
- PCR41 config uses `#:` docstring-style comments for each constant. Optimizer config uses inline trailing `# comment` for Imperial equivalents (per D-14) and source citations (per D-06).
- PCR41 config has no `import` statements. Optimizer config needs `import math` for `math.radians()` in joint limit constants.
- All values SI (meters, kg, radians). Imperial inline as `# 33"` or `# 36 in`.

**Key distinction — no dataclasses or Pydantic** (per D-12): The PCR41 config uses plain module-level constants (matching requirement). Do NOT adopt class-based or dict-based constant patterns from other files in the codebase.

---

### `Robot_Simulations/optimizer/logging_utils.py` (utility, transform)

**Analog:** `engineering_tools/simulation/DES/core/logging/logger.py`

**Imports pattern** (lines 1-7 of analog):
```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
import simpy
```

**Adaptation for logging_utils.py:**
The EventLogger is a heavyweight SimPy-integrated class. `logging_utils.py` must be a lightweight module with standalone functions — no SimPy, no class, no context manager overhead.

```python
# logging_utils.py — correct import pattern for optimizer (not EventLogger pattern)
import logging

_logger = logging.getLogger("optimizer")
```

**Core function pattern** — extract from RESEARCH.md Pattern 4 (D-15 mandated interface):
```python
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
```

**Convenience converter pattern** — follow the same module-level function pattern used throughout `mech_core/analysis/kinematics/kinematics.py` (lines 24-56 of that file):
```python
# Short verb-noun functions, no class wrapping:
def mm_to_in(mm: float) -> float:   return mm / 25.4
def in_to_mm(in_: float) -> float:  return in_ * 25.4
def kg_to_lb(kg: float) -> float:   return kg * 2.20462
def rad_to_deg(rad: float) -> float:
    import math
    return math.degrees(rad)
```

**What NOT to copy from EventLogger:** The `@contextmanager`, `_event_stack`, SimPy `.env.now` integration, and `@dataclass Event` — none of these belong in logging_utils.py. The optimizer uses Python's standard `logging` module, not SimPy events.

---

### `Robot_Simulations/optimizer/opw_solver/__init__.py` (utility, re-export)

**Analog:** `engineering_tools/mech_core/standards/units.py`

**Pattern** (full file — 11 lines):
```python
# mech_core/units.py
import pint

# The Single Source of Truth
ureg = pint.UnitRegistry()
ureg.default_format = ".3f"
Q_ = ureg.Quantity
```

**Adaptation for opw_solver/__init__.py:**
The `units.py` singleton pattern (import once, re-export) is the closest analog for `__init__.py` that re-exports the wrapper's public API. Apply the same "single source of truth" philosophy:

```python
# opw_solver/__init__.py
# Re-exports the public API. All other code imports from here, not from wrapper.py directly.
from .wrapper import forward, inverse, filter_by_limits

__all__ = ["forward", "inverse", "filter_by_limits"]
```

**Key distinction:** The `units.py` singleton creates a module-level object (`ureg`) that is shared globally. `opw_solver/__init__.py` should similarly create the Robot instance once at module import time (inside `wrapper.py`), so all callers share a single pre-initialized kinematic model.

---

### `Robot_Simulations/optimizer/opw_solver/wrapper.py` (service, request-response)

**Analog:** `engineering_tools/simulation/DES/core/machines/subsystems/robots/robot_arm.py`

**Imports pattern** (lines 1-13 of analog):
```python
import simpy
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from ....logging.logger import EventLogger
from ......mech_core.standards.units import ureg
from ......mech_core.analysis.kinematics import velocity_profile_trapezoidal, distance_3d

if TYPE_CHECKING:
    from ..eoa_tools.base import ManufacturingTool
```

**Adaptation for wrapper.py** — strip SimPy, keep the configuration-from-config pattern:
```python
# opw_solver/wrapper.py
import numpy as np
from scipy.spatial.transform import RigidTransform
from py_opw_kinematics import KinematicModel, Robot
import config  # top-level config.py — all OPW params live there
```

**Core singleton-init pattern** (lines 25-55 of robot_arm.py — `__init__` loading config):
The RobotArm loads `fanuc.json` at construction and stores it on `self`. The wrapper.py equivalent initializes the kinematic model once at module level (not per-call), mirroring how `units.py` creates `ureg` once:

```python
# Module-level singleton — initialized once on import, shared by all callers
_KINEMATIC_MODEL = KinematicModel(
    a1=config.OPW_A1, a2=config.OPW_A2, b=config.OPW_B,
    c1=config.OPW_C1, c2=config.OPW_C2, c3=config.OPW_C3, c4=config.OPW_C4,
    offsets=config.OPW_JOINT_OFFSETS,
    flip_axes=config.OPW_FLIP_AXES,
)
_ROBOT = Robot(_KINEMATIC_MODEL, degrees=False)  # always radians internally
```

**Error/boundary pattern** (lines 57-73 of robot_arm.py — `mount_tool` with warning but no exception):
```python
if tool.mass_kg > self.max_payload:
    self.logger.log_event("WARNING", self.model_name, f"Tool Overload: ...")
```

**Adaptation:** `wrapper.py` uses the same "warn but continue" approach for wrist-aligned singularity — `inverse()` returning an empty list is not an exception, it is a documented condition. Return `[]` and let the caller decide.

**Joint limit filter pattern** — closest analog is the config-driven limit check in `robot_arm.py` lines 67-70:
```python
load_ratio = min(tool.mass_kg / self.max_payload, 1.0)
penalty = load_ratio * self.derating_factor
```

The optimizer filter applies the same "compare against config-sourced limits" pattern but for joint angles:
```python
def filter_by_limits(solutions: list) -> list:
    _EPS = 0.001  # rad — avoids floating-point boundary rejections (Pitfall #2)
    lowers = [l - _EPS for l in config.JOINT_LIMITS_LOWER_RAD]
    uppers = [u + _EPS for u in config.JOINT_LIMITS_UPPER_RAD]
    valid = []
    for sol in solutions:
        if all(l <= q <= u for q, l, u in zip(sol, lowers, uppers)):
            valid.append(tuple(sol))
    return valid
```

---

### `Robot_Simulations/optimizer/tests/test_opw_validation.py` (test, batch)

**Analog:** `engineering_tools/simulation/DES/tests/test_gas_jets.py`

**Imports pattern** (lines 1-18 of analog):
```python
"""
Unit tests for mech_core.analysis.fluid_dynamics.gas_jets module.

Tests verify:
- Compressible flow physics (subsonic vs supersonic)
- Ideal gas law calculations
- Clearing speed heuristic model
- Input validation and error handling
"""

import pytest
import math
from engineering_tools.mech_core.analysis.fluid_dynamics.gas_jets import (
    calculate_nozzle_exit_velocity,
    calculate_clearing_speed_limit,
    calculate_gas_density_at_nozzle
)
from engineering_tools.mech_core.standards.units import ureg, Q_
```

**Adaptation for test_opw_validation.py:**
```python
"""
Validation tests for opw_solver — Phase 1 hard gate.

Tests verify (per spec Section 11C / D-10):
- FK->IK round-trips: 500 samples, position <0.01 mm, orientation <0.01 deg
- Operating space envelope matches Fig 3.2a bounds
- Joint limits enforced for all 6 axes (J3 asymmetric: +268.4°/-190°)
- All 8 OPW solutions correctly filtered
- Singularity behavior (wrist-aligned J5≈0, full extension)
- Riser height regression (H=0 vs H=914mm → different IK)
"""

import pytest
import numpy as np
import math
import random
from opw_solver.wrapper import forward, inverse, filter_by_limits
import config
```

**Test function structure pattern** (lines 22-80 of analog — `TestCalculateNozzleExitVelocity` class):
```python
class TestCalculateNozzleExitVelocity:
    """Test suite for calculate_nozzle_exit_velocity function."""

    def test_subsonic_flow_low_pressure_ratio(self):
        """
        Low pressure ratio should give subsonic flow.
        Physics: Speed of sound in air at 300K ≈ 347 m/s
        """
        v = calculate_nozzle_exit_velocity(...)
        v_m_s = v.to(ureg.m / ureg.s).magnitude
        speed_of_sound = 347
        assert v_m_s < speed_of_sound, \
            f"Low pressure ratio should give subsonic flow, got {v_m_s:.1f} m/s"
        assert v_m_s > 0, "Velocity must be positive"
```

**Adaptation:** Use module-level test functions (not class-based) following the `test_safety_plc.py` analog (simpler style used in DES tests):
```python
def test_fk_ik_roundtrip_500():
    """SOLV-02: 500 random FK->IK round-trips, position <0.01mm, orientation <0.01 deg."""
    rng = random.Random(42)
    failures = []
    ...
    assert not failures, f"{len(failures)}/500 round-trips failed:\n" + "\n".join(failures[:5])
```

**Assert message pattern** (analog lines 43-44):
```python
assert v_m_s < speed_of_sound, \
    f"Low pressure ratio should give subsonic flow, got {v_m_s:.1f} m/s"
```

All assertions must include an f-string failure message with the actual observed value.

---

### `Robot_Simulations/optimizer/tests/test_config.py` (test, smoke)

**Analog:** `engineering_tools/simulation/DES/tests/test_safety_plc.py`

**Imports pattern** (lines 1-15 of analog):
```python
import pytest
import simpy
from ..core.logging.logger import EventLogger
from ..core.machines.subsystems.logic.safety_plc import SafetyPLC, RobotState, FeederState

def test_initial_state():
    """Verify PLC starts with both resources available."""
    env = simpy.Environment()
    ...
    assert plc.robot_state == RobotState.HOME
```

**Adaptation for test_config.py** — same flat function style, no fixtures needed:
```python
import pytest
import math
import config

def test_config_imports():
    """ENV-02: config.py must import without error."""
    assert hasattr(config, "OPW_A1")
    assert hasattr(config, "JOINT_LIMITS_LOWER_RAD")

def test_joint_limits_count():
    """Each joint limit list must have exactly 6 elements."""
    assert len(config.JOINT_LIMITS_LOWER_RAD) == 6
    assert len(config.JOINT_LIMITS_UPPER_RAD) == 6

def test_j3_upper_limit_asymmetric():
    """J3 upper limit must be +268.4° (4.683 rad), not capped at +180°."""
    j3_upper = config.JOINT_LIMITS_UPPER_RAD[2]
    assert abs(j3_upper - math.radians(268.4)) < 0.001, \
        f"J3 upper limit must be 268.4° but got {math.degrees(j3_upper):.1f}°"
```

---

### `Robot_Simulations/optimizer/tests/conftest.py` (test fixture, no analog)

No analog exists in the codebase — there are no `conftest.py` files anywhere in the project. Use the pytest standard pattern from RESEARCH.md:

```python
# tests/conftest.py
import pytest
import random
import config
from opw_solver.wrapper import forward, inverse, filter_by_limits

POSITION_TOL_MM = 0.01   # spec Section 11C
ANGLE_TOL_DEG   = 0.01   # spec Section 11C
RANDOM_SEED     = 42

@pytest.fixture(scope="session")
def rng():
    """Seeded RNG for reproducible random joint configs."""
    return random.Random(RANDOM_SEED)

@pytest.fixture(scope="session")
def joint_limits():
    """Paired (lower, upper) joint limit tuples in radians."""
    return list(zip(config.JOINT_LIMITS_LOWER_RAD, config.JOINT_LIMITS_UPPER_RAD))
```

---

## Shared Patterns

### Module-Level Constants (Zero Magic Numbers)

**Source:** `engineering_tools/simulation/DES/core/machines/PCR41/config.py` (full file, 71 lines)
**Apply to:** `config.py`, and as the governing principle for ALL optimizer modules

```python
# Pattern: named constant, section header, inline doc comment
# === FEEDER LIMITS ===
MAX_FEEDER_SPEED_MM_S = 500.0    # max indexing speed
FEEDER_ACCEL_MM_S2 = 200.0       # feeder acceleration
```

No magic numbers anywhere outside `config.py`. Every numeric literal in `wrapper.py`, `logging_utils.py`, and test files must reference a `config.*` constant or be a test-local tolerance constant defined at the top of the test file.

---

### Config-Driven Initialization

**Source:** `engineering_tools/simulation/DES/core/machines/subsystems/robots/robot_arm.py` lines 25-55
**Apply to:** `opw_solver/wrapper.py`

```python
# robot_arm.py pattern: load config at __init__, store on self
config_path = Path(__file__).parent / "configs" / config_file
with open(config_path, 'r') as f:
    self.config = json.load(f)
self.model_name = self.config['model']
self.max_payload = self.config['max_payload_kg']
```

**Adaptation:** The optimizer uses a Python `config.py` module instead of JSON (per D-12). The module-level singleton in `wrapper.py` is initialized from `config.*` constants directly at import time — same intent, no JSON parsing overhead.

---

### Pytest Test Function Style

**Source:** `engineering_tools/simulation/DES/tests/test_safety_plc.py` lines 17-59
**Apply to:** All files in `Robot_Simulations/optimizer/tests/`

```python
def test_initial_state():
    """Verify PLC starts with both resources available."""
    env = simpy.Environment()
    logger = EventLogger(env)
    plc = SafetyPLC(env, logger)

    assert plc.robot_state == RobotState.HOME
    assert plc.feeder_is_idle.triggered
```

Rules extracted:
1. Module-level functions, not classes (unlike `test_gas_jets.py` which uses class grouping — prefer flat style for the optimizer test suite)
2. One behavior per function
3. Docstring states exactly what is verified
4. Assertions use f-string failure messages with actual value

---

### Import Organization

**Source:** `engineering_tools/mech_core/components/members/aisc.py` lines 1-14
**Apply to:** All new optimizer Python files

```python
"""
Module docstring — what this provides, not how.
"""

import json
import os
from typing import List, Optional
from mech_core.standards.units import ureg, Q_

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "../../standards/materials/data", "aisc_shapes.json")
```

Rules:
1. Module docstring first
2. Standard library imports
3. Third-party imports
4. Local/project imports
5. Module-level constants (UPPER_SNAKE) immediately after imports

---

### Naming Conventions (from CLAUDE.md)

**Apply to:** All new files

| Entity | Convention | Example |
|--------|-----------|---------|
| Module files | `snake_case` | `logging_utils.py`, `wrapper.py` |
| Functions | `snake_case`, verb-noun | `filter_by_limits()`, `log_dual()` |
| Constants | `UPPER_SNAKE_CASE` | `OPW_C1`, `JOINT_LIMITS_LOWER_RAD` |
| Private helpers | `_` prefix | `_KINEMATIC_MODEL`, `_ROBOT` |
| Physics variables | Short engineering notation | `c1`, `a1`, `j3_upper` |

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `Robot_Simulations/optimizer/tests/conftest.py` | test fixture | — | No conftest.py files exist anywhere in the project; standard pytest pattern from RESEARCH.md applies |
| `Robot_Simulations/optimizer/opw_solver/wrapper.py` (pybind11 fallback path) | service | request-response | No C++ extension build infrastructure exists in this project; CMakeLists.txt + opw_wrapper.cpp have no analog — use RESEARCH.md Pattern 2 for the cpp/CMake skeleton |

---

## Metadata

**Analog search scope:** `engineering_tools/` (full tree), `Robot_Simulations/eden/` (not relevant — RL training code)
**Files scanned:** 12 source files read in detail; 110+ files globbed for structure
**Pattern extraction date:** 2026-04-16

**Optimizer module location:** `Robot_Simulations/optimizer/` — directory does not yet exist. All 7 files are new.
