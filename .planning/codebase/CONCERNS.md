# Codebase Concerns
_Generated: 2026-04-12_

## Summary

This document catalogues technical debt, reliability risks, and maintainability gaps found across the MechanicalDesignTools codebase. Concerns are grouped by severity and then by subsystem. Each concern is tied to a specific file or pattern so it can be actioned directly.

---

## Severity Legend

- **HIGH** — Could cause silent incorrect results, data loss, or broken execution paths that affect engineering outputs.
- **MEDIUM** — Degrades maintainability, reproducibility, or test confidence without immediately corrupting results.
- **LOW** — Style, minor inconsistency, or cosmetic issue that accumulates as technical debt.

---

## HIGH — Engineering Correctness Risks

### H1 · Hardcoded Poisson's ratio in `fea.py`

**File:** `engineering_tools/mech_core/analysis/fea.py`, `_get_or_add_material()` (line ~127)

The shear modulus `G` is always computed as `E / (2 * (1 + 0.3))` with a literal `0.3`. No `nu` attribute is read from `StructuralMaterial`. For standard structural steel this is correct (ν ≈ 0.30), but for aluminum, stainless steel, cast iron, or any future non-steel material the shear modulus will be wrong, producing incorrect torsion and shear results. The `StructuralMaterial` dataclass does not currently carry a `poisson_ratio` field, so the fix requires both the dataclass and `fea.py` to be updated together.

```python
# current — always 0.3 regardless of material
G = E / (2 * (1 + 0.3))
```

---

### H2 · Axis-swap applies only to force components, not moment components consistently

**File:** `engineering_tools/simulation/Structural/document.py`, `run_solve()` (lines ~499–506)

The GUI stores loads in Z-up space; PyNite uses Y-up. The code maps `nl.Fz → Fy` and `nl.Fy → Fz` correctly for forces. For moments it maps `nl.Mz → My` and `nl.My → Mz`. This is geometrically consistent, but the comment chain is easy to break during future edits. More critically, the member distributed load direction map (lines ~511–512) only handles `"Fy"/"Fz"` swap but silently passes through any other string unchanged — an unrecognised direction string will be applied in the wrong PyNite axis with no error raised.

```python
_dir_map = {"Fx": "Fx", "Fy": "Fz", "Fz": "Fy"}
fea.add_member_dist_load(
    ml.member_id, _dir_map.get(ml.direction, ml.direction),  # fallback is unchecked
    ...
)
```

A `ValueError` should be raised for direction strings not in `_dir_map` rather than silently passing through.

---

### H3 · `remove_support` and `remove_node_load` / `remove_member_load` push undo **after** the mutation

**File:** `engineering_tools/simulation/Structural/document.py`, `remove_support()` (line ~321), `remove_node_load()` (line ~357), `remove_member_load()` (line ~382)

All other `DocumentController` mutation methods call `self._push_undo()` **before** modifying `self._doc`. These three methods call `self._doc.*.pop()` first and then `self._push_undo()`. This means undo after these operations will restore the post-deletion state instead of the pre-deletion state — effectively making undo a no-op or, worse, pushing a corrupted snapshot. This is a silent undo bug that will confuse users.

```python
def remove_support(self, support_id: str):
    self._doc.supports.pop(support_id, None)   # mutation first — BUG
    self._push_undo()                           # snapshot taken after mutation
    ...
```

---

### H4 · `ResultsCache.from_fea()` silently swallows per-member exceptions

**File:** `engineering_tools/simulation/Structural/results.py`, `from_fea()` (lines ~138–140)

The outer `except Exception: pass` in the member-sampling loop means that if a single member fails to post-process (e.g., due to a convergence failure, naming mismatch, or PyNite internal error), it is silently omitted from `member_results`. The viewport will render that member with no force diagram and no indication of the failure. For engineering use this is dangerous — a member that could not be post-processed should surface a warning, not disappear silently.

```python
except Exception:
    # If a member fails to sample, skip gracefully
    pass
```

---

### H5 · DES test suite uses wrong import path

**File:** `engineering_tools/simulation/DES/tests/test_composite_constraint.py` (line ~12–14)

The test imports from `engineering_tools.simulation.core.machines.subsystems...` — a path that does not match the actual package structure (`engineering_tools.simulation.DES.core.machines.subsystems...`). This test will always fail with `ModuleNotFoundError` when run via `pytest`. Because there is no CI, this breakage is undetected. Other DES tests may have the same issue.

```python
from engineering_tools.simulation.core.machines.subsystems.eoa_tools.fiber_laser import FiberLaser
# Should be:
# from engineering_tools.simulation.DES.core.machines.subsystems.eoa_tools.fiber_laser import FiberLaser
```

---

## MEDIUM — Reliability and Maintainability Risks

### M1 · No dependency lockfile — exact versions not pinned

**File:** `engineering_tools/requirements.txt`

All dependencies use `>=` lower bounds only (e.g., `PyNiteFEA>=0.3.0`, installed version 1.6.2; `PySide6>=6.6.0`, installed 6.10.2). There is no `requirements.lock`, `poetry.lock`, or `pip-compile` output. A fresh `pip install -r requirements.txt` on a new machine could install any future-breaking version. For engineering software that must produce reproducible results, this is a significant reproducibility risk.

---

### M2 · No CI pipeline — tests are never automatically run

No `.github/workflows/`, `Jenkinsfile`, or any other CI configuration was found. The test suite (`pytest`) must be run manually. Given that at least one test file has broken import paths (H5) and there is no formatter or linter enforcement, regressions can accumulate undetected between working sessions.

---

### M3 · Two divergent PCR41 implementations

**Files:**
- `engineering_tools/simulation/DES/core/machines/PCR41/` (modular, current)
- `engineering_tools/projects/PCR41_test/simulation.py` and `test_feeder_logic.py` (older)

The `projects/PCR41_test/` directory references `PCR41_Assembly` and other symbols that predate the refactor into the modular DES subsystem hierarchy. It is unclear which implementation is authoritative. Having two codebases for the same machine increases the surface area for divergence and means any physics parameter change must be made in two places or one version will drift.

---

### M4 · `print("[WARNING] ...")` used instead of `warnings.warn()`

**Files:** `engineering_tools/mech_core/standards/structural/csa_s16/members.py` (`get_k_factor()`), `mech_core/standards/materials/steel.py`, and others.

Most warning paths use bare `print(f"[WARNING] ...")` rather than Python's `warnings.warn()`. This has two problems: (1) warnings cannot be filtered, suppressed, or escalated programmatically by calling code; (2) they are invisible to `pytest` warning capture, meaning tests cannot assert that a warning was issued for a suspect input. The `gas_jets.py` fallback for the missing `fluids` library does use `warnings.warn()` correctly, making the inconsistency more visible.

---

### M5 · Undo stack uses `pop(0)` on a `list` — O(n) trimming at MAX_DEPTH

**File:** `engineering_tools/simulation/Structural/undo_stack.py` (line ~51)

```python
if len(self._past) > self.MAX_DEPTH:
    self._past.pop(0)
```

`list.pop(0)` is O(n) because all remaining elements shift. With `MAX_DEPTH = 60` this is negligible today, but would become noticeable if the depth limit is raised or if model mutations are very frequent. A `collections.deque(maxlen=60)` would make this O(1) and remove the explicit length check entirely.

---

### M6 · `project_io.py` uses path relative to `__file__` for the default projects directory

**File:** `engineering_tools/simulation/Structural/project_io.py` (line ~20)

```python
_DEFAULT_PROJECTS_DIR = Path(__file__).parents[2] / "projects"
```

`parents[2]` resolves to `engineering_tools/` which is correct from the installed source tree, but would break if the package is ever installed via pip into a site-packages directory, or if the file is moved or refactored. A safer default would be derived from a user config directory or `platformdirs`.

---

### M7 · `fea.py` does not accept multiple load combinations

**File:** `engineering_tools/mech_core/analysis/fea.py`

`FrameAnalysis.solve()` calls `model.analyze()` with no load case combination setup. PyNiteFEA supports named load combos but the wrapper only adds loads to `"Case 1"`. The `ResultsCache` hardcodes `load_case = "Case 1"`. For structural engineering practice (LRFD or ASD envelope checking), multiple load combinations are required. Extending the wrapper later will be a breaking interface change.

---

### M8 · `gannt.py` filename typo

**File:** `engineering_tools/simulation/DES/core/visualization/gannt.py`

The module is named `gannt.py` (double 'n') rather than `gantt.py`. This is a persistent typo that will propagate if other code imports from the module name or if the file is renamed — both operations require coordinated changes. Any new code added referencing the correct spelling would fail.

---

### M9 · `mech_core` standards cover CSA S16 only — no explicit AISC 360 checks

**Files:** `engineering_tools/mech_core/standards/structural/csa_s16/members.py` and `connections.py`

The only implemented code-of-practice checks are for CSA S16 (Canadian). The AISC shape database is used for cross-section properties, but no AISC 360 resistance checks exist. Design scripts (`design_mezzanine.py`, `design_portal.py`) produce CSA results which are then fed into FEA. If a project requires AISC 360 compliance instead of CSA S16, there is no supported pathway. The gap is not documented in any README visible to users.

---

### M10 · `engineering_tools/tests/` scripts use `sys.path.insert` instead of proper pytest discovery

**Files:** `engineering_tools/tests/test_fea_wrapper.py`, `verify_aisc_benchmark.py`, `verify_example_f1_2a.py`

These files manipulate `sys.path` at the top to enable imports, which is the older pattern needed when running as standalone scripts. The DES tests under `simulation/DES/tests/` do not do this. Without a `conftest.py` or `pyproject.toml` with `pythonpath` settings, running `pytest` from `engineering_tools/` may fail for one set of tests depending on working directory. There is no `conftest.py` at any level of `engineering_tools/`.

---

### M11 · PostgreSQL data files committed to the repository

**File:** `.dev_tools/postgres_data/` (PostgreSQL 15 cluster data directory)

An entire Postgres data directory is tracked in the repository. This is unusual and has several problems: binary files inflate git history; the cluster is not portable between machines without matching Postgres versions; and if the database contains any sensitive or user-specific engineering reference data, it should not be in version control. The cluster exists solely to support MCP AI-assistant tooling, not application code.

---

### M12 · Dev credentials stored in `.mcp.json`

**File:** `.mcp.json` (not inspected directly but confirmed by INTEGRATIONS.md)

The PostgreSQL connection string (`postgresql://admin:***@localhost:5432/engineering_data`) with credentials is stored in `.mcp.json`. If this file is ever committed to a public remote or shared, the credentials are exposed. A `.env` or secrets file pattern with `.mcp.json` referencing environment variables would be safer.

---

## LOW — Style and Minor Technical Debt

### L1 · `typing.List` / `typing.Dict` / `typing.Optional` used instead of built-in generics

**Files:** `document.py`, `results.py`, `csa_s16/members.py`, and others.

Python 3.9+ allows `list[str]`, `dict[str, int]`, `Optional[X]` → `X | None`. The codebase uses `from typing import List, Dict, Optional, Tuple` throughout. Since the actual runtime is Python 3.12, this is purely cosmetic but adds unnecessary imports and diverges from modern Python style.

---

### L2 · `import math as _math` inside a method body

**File:** `engineering_tools/simulation/Structural/document.py`, `add_nodes_circular_array()` (line ~637)

```python
import math as _math
```

Imports inside function bodies add a small per-call overhead and make it harder to see all dependencies at the top of a module. `math` is a standard library module and should be at the top-level.

---

### L3 · No `__all__` defined in any `__init__.py`

Across `mech_core/`, `simulation/DES/`, and `simulation/Structural/`, none of the `__init__.py` files define `__all__`. Public API surface is entirely implicit. This makes it impossible to use `from mech_core import *` safely and makes it harder for IDEs and documentation generators to determine intended exports.

---

### L4 · `projects/PCR42 EOA Tool Design/` directory name contains a space

**Directory:** `engineering_tools/projects/PCR42 EOA Tool Design/`

Directory names with spaces require quoting in shell commands and can cause issues with some tools (makefiles, certain CI runners, import resolvers). Rename to `PCR42_EOA_Tool_Design/` for consistency with all other `projects/` directories.

---

### L5 · `simulation/DES/core/visualization/gannt.py` — misspelled public symbol

Related to M8. If `EventLogger` or other code imports `from ...visualization.gannt import ...`, correcting the filename later becomes a breaking change requiring coordinated find-and-replace across all callers. Fix the filename and any imports together as a single atomic change.

---

### L6 · `ReportGenerator` writes Markdown only — no validation of LaTeX-style strings

**File:** `engineering_tools/mech_core/standards/reporting/generator.py`

The `calc_trace` steps system embeds raw LaTeX-like strings (e.g., `r"F_{cr} = ..."`). These are written to Markdown `.md` files. There is no rendering pipeline that validates or compiles these strings — they appear as raw text in the output unless a Markdown renderer with LaTeX support is used. The target rendering environment is undocumented.

---

## Cross-Cutting Gaps

### G1 · No `conftest.py` and no `pyproject.toml` — test discovery is fragile

There is no `conftest.py` at `engineering_tools/` or `engineering_tools/simulation/DES/` root level and no `[tool.pytest.ini_options]` in a `pyproject.toml`. The two test trees (`engineering_tools/tests/` and `simulation/DES/tests/`) use different import strategies (absolute + `sys.path` vs. relative). Running `pytest` from `engineering_tools/` may fail for the `sys.path`-manipulating tests depending on working directory. A single `conftest.py` at `engineering_tools/` with `pythonpath = ["."]` would resolve this without changing any test files.

---

### G2 · `Robot_Simulations/` sub-project relationship to parent repo is unformalized

`Robot_Simulations/` contains its own `.git` directory. No `.gitmodules` file was found at the repository root. It is unclear whether this is a git submodule, a nested repository, or an independently managed tree. This ambiguity means: (1) `git clone` of the outer repo may silently omit the Robot_Simulations content; (2) there is no enforced version pin between the outer repo and the sub-project; (3) `git status` output from the outer repo will not reflect changes inside `Robot_Simulations/`.

---

### G3 · No formatter, linter, or pre-commit hooks enforced

`requirements.txt` lists `black` and `flake8` as commented-out dev dependencies. No `.flake8`, `.pylintrc`, `pyproject.toml [tool.black]`, or `.pre-commit-config.yaml` file exists. Code style consistency is entirely manual and will drift over time, particularly as the contributor base grows or AI-assisted edits add inconsistencies.

---

### G4 · PDF export depends on an external binary not tracked by the project

**File:** `engineering_tools/simulation/Structural/pdf_export.py`

`wkhtmltopdf` must be installed separately on the host OS. It is not listed in `requirements.txt`, not documented in `README.md`, and its absence is only discovered at runtime when the user attempts to export. Adding `pdfkit` to `requirements.txt` and documenting the `wkhtmltopdf` prerequisite in the README would surface this dependency at setup time.

---

### G5 · No project-level README entry point for new contributors

The root `README.md` exists, but there is no single document that explains: how to set up both virtual environments, how to run the GUI, how to run the DES simulation, how to run the test suite, and what the relationship between `engineering_tools/` and `Robot_Simulations/` is. ARCHITECTURE.md covers structure but not the development workflow. This is a discoverability gap for anyone new to the project.
