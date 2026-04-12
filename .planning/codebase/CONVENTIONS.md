# Coding Conventions
_Generated: 2026-04-12_

## Summary
The codebase is pure Python (3.12) with no enforced formatter or linter config present (black and flake8 are listed in `requirements.txt` but commented out). Code quality is generally high in the `mech_core` and `simulation/DES` subsystems, where consistent patterns emerge organically. The `projects/` directory and legacy test files are less disciplined.

---

## Style Configuration

No `.flake8`, `.pylintrc`, `pyproject.toml`, or `setup.cfg` detected. The `requirements.txt` at `engineering_tools/requirements.txt` lists `black` and `flake8` as commented-out dev dependencies, meaning formatting is **not enforced at commit time**. No CI pipeline was found, so style consistency is entirely manual.

---

## Naming Conventions

**Files:**
- `snake_case` throughout: `gas_jets.py`, `thermal_removal.py`, `push_rod_feeder.py`
- Module files match the primary class or domain they contain
- Test files prefix with `test_`: `test_gas_jets.py`, `test_safety_plc.py`
- Verification scripts use `verify_` prefix: `verify_aisc_benchmark.py`, `verify_example_f1_2a.py`

**Classes:**
- `PascalCase`: `FrameAnalysis`, `SectionProperties`, `StructuralMaterial`, `EventLogger`, `SafetyPLC`, `CrossTransfer`
- Enums use `PascalCase` name with `UPPER_SNAKE` members: `RobotState.HOME`, `FeederState.MOVING`
- `dataclass` is used for pure data containers: `SurfacePhysics`, `StructuralMaterial`, `Event`

**Functions:**
- `snake_case` for all functions: `calculate_nozzle_exit_velocity`, `check_flexural_resistance`, `get_section`
- Calculation functions use verb-noun pattern: `calculate_*`, `check_*`, `get_*`
- Private/internal helpers prefixed with `_`: `_get_or_add_material`, `_section_counter`

**Variables:**
- Local loop vars and temporaries: `snake_case` — `mat_name`, `Lb_val`, `phi_Mn`
- Physics variables (intermediate calculation values) often use short-form matching engineering notation: `Fy_val`, `KL_r_val`, `Fcr_val`, `Mn_val`
- Constants use `UPPER_SNAKE_CASE`: `DB_PATH`, `CURRENT_DIR`, `FLUIDS_AVAILABLE`

**Parameters:**
- Pint quantity parameters typed as `Q_`: `thickness: Q_`, `tool_power: Q_`
- Optional parameters use `Optional[Q_] = None` pattern

---

## Type Annotations

Partial adoption. Core library modules use type hints for function signatures:

```python
def calculate_melting_speed(
    material: StructuralMaterial,
    thickness: Q_,
    tool_power: Q_,
    kerf_width: Q_,
    efficiency: float = 1.0,
    absorptivity: float = 1.0,
    t_ambient: Optional[Q_] = None
) -> Q_:
```

`dataclass` is used for data containers in `steel.py`, `fastener.py`, `concrete.py`, `logger.py`, `document.py`, `results.py`. The frozen dataclass pattern is used for immutable material definitions:

```python
@dataclass(frozen=True)
class StructuralMaterial:
    name: str
    yield_strength: Q_
    ...
```

Return types are sometimes omitted for longer functions. `typing.List`, `typing.Dict`, `typing.Optional`, `typing.Tuple` imported from `typing` (pre-Python 3.10 style, not using built-in generics).

---

## Documentation Conventions

**Module-level docstrings:** Present on almost all source files in `mech_core/` and `simulation/DES/`. Pattern:

```python
"""
Module path and one-line summary.

Longer description of purpose and domain.

References:
    - Standard/book citation
"""
```

**Class docstrings:** Present on most classes; usually describe purpose and include a `Usage:` or `Example:` block with runnable `>>>` doctest-style code:

```python
class FrameAnalysis:
    """
    Wrapper for PyNiteFEA that integrates with mech_core AISC components.
    ...
    Example:
        >>> frame = FrameAnalysis()
        >>> section = get_section("W12X26")
    """
```

**Function docstrings:** Consistent use of Google-style docstrings with `Args:`, `Returns:` sections. Physics functions often include `Physics Model:` describing the equation being implemented:

```python
def calculate_melting_speed(...) -> Q_:
    """
    Calculate linear cutting speed from thermal energy balance.

    Physics Model:
        Speed = Effective_Power / (Energy_Density × Cross_Section_Area)

    Args:
        material: StructuralMaterial object
        ...
    Returns:
        Cutting speed as Pint quantity
    """
```

**Inline comments:** Used extensively for section markers (`# 1. SETUP VARIABLES`, `# CRITICAL AXIS MAPPING`) and inline engineering notation. LaTeX-style symbols embedded in strings for the `calc_trace` report system (`r"F_{cr} = ..."`).

---

## Error Handling Patterns

**Explicit `ValueError` with descriptive messages** is the dominant pattern for input validation in physics calculation functions:

```python
if pressure_inlet.magnitude <= 0:
    raise ValueError("Inlet pressure must be positive")
if efficiency < 0 or efficiency > 1:
    raise ValueError("Efficiency must be between 0 and 1")
```

**`raise NotImplementedError`** used for unimplemented code paths (e.g., unsupported section shapes in `members.py`):
```python
if section.type not in ['W', 'M', 'S', 'HP', 'C', 'MC']:
    raise NotImplementedError(f"Shape type {section.type} not supported.")
```

**`raise RuntimeError`** in simulation state machines for illegal state transitions (e.g., `SafetyPLC` in `safety_plc.py`).

**`raise ValueError` with named match strings** — validation errors are written so their message matches pytest `pytest.raises(ValueError, match="...")` patterns, indicating test-driven design:
```python
raise ValueError("Inlet pressure must be positive")
# matched in tests as: pytest.raises(ValueError, match="Inlet pressure must be positive")
```

**Warnings via `print`** (not `warnings.warn`) are used in non-critical fallback paths:
```python
print(f"[WARNING] Unknown boundary conditions '{key}'. Assuming K=1.0")
print(f"[WARNING] {self.steel.name} not in plate database...")
```
This is inconsistent: `gas_jets.py` correctly uses `warnings.warn()` for the missing `fluids` library import fallback, while other modules use `print("[WARNING]...")`.

---

## Logging and Observability

**Simulation layer:** A custom `EventLogger` class (`engineering_tools/simulation/DES/core/logging/logger.py`) provides structured simulation event tracking for Gantt chart visualization. It does not use Python's `logging` module — it is domain-specific:

```python
with logger.log_event("Robot: MIG Weld", "Robot", cycle_num=5):
    yield env.timeout(welding_time)
```

**mech_core layer:** No structured logging. Output is via `print()` statements only. Warnings are mixed between `print("[WARNING]...")` and `warnings.warn(...)` (inconsistent).

**Calculation trace system:** Engineering calculation functions in `mech_core/standards/structural/csa_s16/members.py` return a `calc_trace` list of dicts containing symbolic LaTeX expressions, numeric substitutions, and conclusions. This is used by `ReportGenerator` to produce engineering report outputs:
```python
return {
    "Pn": ...,
    "calc_trace": steps  # List of step dicts with 'desc', 'symbol', 'sub', 'result'
}
```

---

## Code Organization Patterns

**Section dividers** are used in longer files to demarcate logical regions:
```python
# ============================================================================
# SECTION PROPERTIES CLASS
# ============================================================================
```

**Numbered step comments** used in engineering calculation functions to match textbook/code structure (`# 1. SETUP VARIABLES`, `# 2. SLENDERNESS RATIO`).

**Path manipulation for standalone execution:** Several test/script files use the `sys.path.insert` pattern to run as scripts:
```python
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, repo_root)
```
This is only needed in `engineering_tools/tests/` and `projects/`, not in the `simulation/DES/tests/` which use relative imports correctly.

---

## Import Organization

**Standard library imports first**, then third-party, then local. Not always separated by blank lines. No isort enforcement detected.

**Relative imports** used in `simulation/DES/` subsystem:
```python
from ....logging.logger import EventLogger
from ..core.machines.subsystems.logic.safety_plc import SafetyPLC
```

**Absolute imports** used in `mech_core/` and standalone scripts:
```python
from mech_core.standards.units import ureg, Q_
from engineering_tools.mech_core.analysis.fluid_dynamics.gas_jets import calculate_nozzle_exit_velocity
```

---

## Gaps / Unknowns

- No formatter config (black, ruff, autopep8) enforced — style is maintained manually.
- No linter config present; flake8/pylint not active.
- Warning pattern is inconsistent (`print("[WARNING]...")` vs `warnings.warn(...)`).
- `projects/` directory files (`design_mezzanine.py`, `design_portal.py`, `eoat_sweep.py`) were not fully reviewed — may have lower convention adherence.
- GUI code in `simulation/Structural/` was not deeply analyzed for convention adherence.
