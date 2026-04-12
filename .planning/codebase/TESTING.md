# Testing
_Generated: 2026-04-12_

## Summary

MechanicalDesignTools uses pytest as its sole test runner. Tests exist in two locations: `engineering_tools/tests/` (top-level, covering `mech_core` modules) and `engineering_tools/simulation/DES/tests/` (co-located with the DES engine). There is no CI pipeline; tests are run manually from the command line. The `Robot_Simulations/eden` sub-project carries its own separate requirements (including `pytest-cov`) but has no test files at the time of writing.

---

## Test Runner

**Framework:** pytest 9.0.2 (installed in main venv at `.venv/`)

**Minimum required:** pytest >=7.3.0 (commented out in `engineering_tools/requirements.txt` — not automatically installed)

**Install pytest manually if needed:**
```bash
pip install pytest
```

**No CI:** No `.github/workflows/`, `Jenkinsfile`, or any other pipeline config exists. All test runs are local and developer-initiated.

---

## Running Tests

All commands assume the working directory is `engineering_tools/` and the project venv is active:

```bash
cd /path/to/MechanicalDesignTools/engineering_tools
source ../.venv/bin/activate
```

**Run the full test suite:**
```bash
pytest
```

**Run only DES tests:**
```bash
pytest simulation/DES/tests/
```

**Run only mech_core / FEA wrapper tests:**
```bash
pytest tests/
```

**Run with verbose output:**
```bash
pytest -v
```

**Run a specific test file:**
```bash
pytest simulation/DES/tests/test_gas_jets.py -v
```

**Run a specific test class or function:**
```bash
pytest simulation/DES/tests/test_gas_jets.py::TestCalculateNozzleExitVelocity::test_subsonic_flow_low_pressure_ratio -v
```

**Note on imports:** The DES tests use relative imports (e.g., `from ..core.machines...`). They must be run from `engineering_tools/` with pytest's package discovery enabled (the `simulation/DES/tests/__init__.py` file ensures the package is importable). The top-level `tests/` files manually patch `sys.path` to find `mech_core`, so they work whether invoked directly (`python tests/test_fea_wrapper.py`) or via pytest.

---

## Test Inventory

### `engineering_tools/tests/` — Top-Level Tests (mech_core)

These files sit outside any package; they patch `sys.path` at the top of each file to locate `mech_core`.

| File | Nature | What It Tests |
|------|--------|---------------|
| `test_fea_wrapper.py` | Integration | `FrameAnalysis` wrapper: simply-supported beam with point load, cantilever with UDL; compares shear/moment against theoretical closed-form results |
| `verify_aisc_benchmark.py` | Verification | CSA S16 `check_flexural_resistance` for W18X50 at 10 ft unbraced length; compares against AISC 15th Ed. Table 3-10 (truth value: 306 kip-ft) |
| `verify_example_f1_2a.py` | Verification | CSA S16 `check_flexural_resistance` for W18X50 at Lb = 11.7 ft (AISC Example F.1-2A); target ~302 kip-ft, asserts <2% deviation |

**Note:** `verify_aisc_benchmark.py` and `verify_example_f1_2a.py` are named with the `verify_` prefix rather than `test_` — they will be collected by pytest but are written in an imperative print-and-inspect style rather than structured with `assert` statements in all cases.

---

### `engineering_tools/simulation/DES/tests/` — DES Unit Tests

These use proper pytest class-based organisation with `assert` statements. They import via relative paths from within the `simulation/DES` package.

#### `test_gas_jets.py`

Tests `mech_core.analysis.fluid_dynamics.gas_jets` module:

| Class | Tests |
|-------|-------|
| `TestCalculateNozzleExitVelocity` | Subsonic flow at low pressure ratio; supersonic at high pressure ratio; monotonic pressure-velocity relationship; temperature effect; oxygen vs. air comparison; argon (gamma=1.67) vs. air; zero inlet pressure raises `ValueError`; zero temperature raises `ValueError`; gamma ≤ 1.0 raises `ValueError` |
| `TestCalculateGasDensityAtNozzle` | Ideal gas law spot-check at 10 bar/300K (expects ~11.6 kg/m³); linear pressure scaling; inverse temperature scaling; molecular weight effect (argon heavier than nitrogen); zero pressure raises `ValueError`; zero temperature raises `ValueError` |
| `TestCalculateClearingSpeedLimit` | Realistic range check for supersonic gas jet; monotonic gas-velocity relationship (scales with v²); nozzle-diameter effect; material-density effect (aluminum vs. steel); efficiency-factor linear scaling; zero nozzle velocity raises `ValueError`; zero nozzle diameter raises `ValueError`; efficiency factor outside [0, 1] raises `ValueError` |

#### `test_safety_plc.py`

Tests `simulation.DES.core.machines.subsystems.logic.safety_plc.SafetyPLC`:

| Test Function | What It Checks |
|---------------|----------------|
| `test_initial_state` | PLC starts with `RobotState.HOME` and `FeederState.IDLE`; both SimPy events are pre-triggered |
| `test_robot_waits_for_feeder` | Robot process blocks on `request_robot_entry()` while feeder is `MOVING`; unblocks after `release_feeder_move()` fires at t=5 s |

#### `test_composite_constraint.py`

Tests the composite (thermal + fluid) constraint model in `FiberLaser` and `PlasmaTorch`:

| Class | Tests |
|-------|-------|
| `TestFiberLaserCompositeConstraint` | Positive and realistic cutting speed for A36 at 12mm; thin material cuts faster than thick material; A992 vs. A36 produce valid speeds |

#### `test_process_physics.py`

Tests `ProcessEnergyCalculator` (inside `simulation.DES.core.machines.subsystems.eoa_tools.fiber_laser`):

| Test Function | What It Checks |
|---------------|----------------|
| `test_a36_realistic_speed` | A36 at 12mm, 4kW: expects 5–15 mm/s (physics reference: ~7 mm/s) |
| `test_a992_realistic_speed` | A992 at 12mm, 4kW: same range as A36 |
| `test_material_not_found_fallback` | Unknown material falls back to A36 and returns a valid speed |

#### `test_thermal_removal.py`

Tests `mech_core.analysis.manufacturing.thermal_removal` module:

| Class | Tests |
|-------|-------|
| `TestCalculateMeltingSpeed` | A36 baseline speed 5–15 mm/s at 12mm/4kW/35% eff (cross-reference to `test_process_physics`); inverse thickness relationship |

#### `test_window_indexer.py`

Tests `simulation.DES.core.machines.PCR41.indexer.Indexer` (sliding-window beam indexing algorithm):

| Test Function | What It Checks |
|---------------|----------------|
| `test_single_window_beam` | 150mm beam with 2 features fits in single 200mm window: produces at least 1 `PROCESS` cycle containing both features, no redundant `INDEX` |
| `test_long_beam_multiple_windows` | 1000mm beam with 3 spread features generates multiple `INDEX` cycles |

---

### `engineering_tools/projects/PCR41_test/test_feeder_logic.py`

Located in the `projects/` directory. Tests feeder logic for the older PCR41 integration harness. Less formal than the DES suite.

---

## Test Patterns and Conventions

### Assertion Style

DES tests follow a consistent style:
- Physics-range assertions: `assert lower_bound <= value <= upper_bound, f"Got {value}"`
- Monotonic relationship assertions: `assert v_high > v_low, "descriptive message"`
- Error-raising assertions: `pytest.raises(ValueError, match="exact error substring")`
- Proportionality assertions: `pytest.approx(ratio, rel=0.01) == expected_ratio`

### Docstrings on Tests

Each test function carries a docstring explaining the physics rationale and the expected range or derivation:

```python
def test_a36_baseline_realistic_speed(self):
    """
    Verify A36 steel cutting speed matches ProcessEnergyCalculator results.

    Reference: test_process_physics.py line 28
    Expected range: 5-15 mm/s for 12mm A36 at 4kW with 35% efficiency
    """
```

### Unit Handling in Tests

All physics inputs and outputs use `pint` quantities (`Q_` and `ureg` from `mech_core.standards.units`). Tests explicitly convert to target units before asserting on magnitudes:

```python
speed_mm_s = speed.to(ureg.mm / ureg.second).magnitude
assert 5.0 <= speed_mm_s <= 15.0
```

### Import Paths

- DES tests use relative package imports: `from ..core.machines.subsystems.logic.safety_plc import SafetyPLC`
- Top-level `tests/` files patch `sys.path` directly to add `engineering_tools/` to `sys.path[0]`, then import as `from mech_core.analysis.fea import FrameAnalysis`
- `test_composite_constraint.py` and `test_thermal_removal.py` use absolute package imports from the project root: `from engineering_tools.mech_core.analysis...`

---

## Coverage

No coverage tooling is configured or run in the main venv. `pytest-cov` is listed in `Robot_Simulations/eden/requirements.txt` but not installed in the `engineering_tools` venv. No `.coveragerc` or coverage thresholds exist.

To generate a coverage report manually:
```bash
pip install pytest-cov
pytest --cov=mech_core --cov=simulation/DES/core simulation/DES/tests/ tests/ --cov-report=term-missing
```

---

## What Is Not Tested

The following components have no test coverage:

| Component | Gap |
|-----------|-----|
| `simulation/Structural/` (entire GUI layer) | No tests exist for `StructuralDocument`, `DocumentController`, `UndoStack`, `Viewport3D`, `placement_tools`, `project_io`, or `results` |
| `mech_core/components/connections/` | Shear, moment, and axial connection checks (fin plate, end plate, double angle, base plate, gusset, splice, flange plate) have no dedicated test files |
| `mech_core/analysis/heat_transfer/` | `conduction.py` and `phase_change.py` are not tested |
| `mech_core/analysis/kinematics/` | `kinematics.py` (trapezoidal velocity profiles) is not tested |
| `mech_core/standards/structural/csa_s16/connections.py` | Connection resistance checks untested |
| `mech_core/standards/reporting/generator.py` | `ReportGenerator` is not tested |
| `simulation/DES/core/` (DES infrastructure) | `EventLogger`, `BeamEntity`, `DSTVData` parser, `gannt.py`, `PCR41_Controller` end-to-end are untested by unit tests (only the integration script `projects/PCR41_test/simulation.py` exercises PCR41 end-to-end) |
| `Robot_Simulations/eden/` | No tests written yet |

---

## Gaps and Known Issues

- **pytest not in requirements:** `pytest` is commented out of `engineering_tools/requirements.txt`; a fresh venv clone will not have pytest installed and `pytest` will fail with "command not found".
- **No CI:** There is no automated test gate on commits or PRs. Tests must be run manually.
- **Mixed import styles:** The three different import strategies (relative, absolute with `engineering_tools.` prefix, and `sys.path` patching) make it difficult to run the entire suite from a single `pytest` invocation without first ensuring `engineering_tools/` is on `sys.path`.
- **Verify scripts are not pure pytest:** `verify_aisc_benchmark.py` and `verify_example_f1_2a.py` print results but rely on developers reading terminal output to confirm correctness; they do not always use structured `assert` statements.
- **No test configuration file:** No `pytest.ini`, `setup.cfg [tool:pytest]`, or `pyproject.toml [tool.pytest.ini_options]` exists. `testpaths`, `python_files`, or `addopts` are not configured.
