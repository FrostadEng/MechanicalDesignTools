# Project Style Guide

**Maintained by:** Antigravity
**Last Updated:** 2025-12-17

---

## Overview

This document defines coding standards, naming conventions, and best practices for the MechanicalDesignTools project.

**PERMISSIONS:**
- ✍️ **Antigravity:** Write access (maintains style guidelines)
- 👁️ **Claude:** Read access (follows these guidelines during implementation)

---

## Python Code Style

### General Principles

- Follow PEP 8 for Python code
- Use type hints for all function signatures
- Write docstrings for all public classes and functions
- Prefer readability over cleverness

### Naming Conventions

**Modules and Packages:**
- Use lowercase with underscores: `heat_transfer.py`, `structural_analysis.py`

**Classes:**
- Use PascalCase: `BeamAnalyzer`, `MaterialProperties`, `SimulationEngine`

**Functions and Methods:**
- Use lowercase with underscores: `calculate_stress()`, `get_material_property()`

**Constants:**
- Use uppercase with underscores: `GRAVITY_CONSTANT`, `MAX_ITERATIONS`

**Private Members:**
- Prefix with single underscore: `_internal_method()`, `_cache`

### Documentation

**Docstring Format:**
```python
def calculate_deflection(load: float, length: float, modulus: float) -> float:
    """
    Calculate beam deflection under point load.

    Args:
        load: Applied load in Newtons
        length: Beam length in meters
        modulus: Elastic modulus in Pascals

    Returns:
        Deflection in meters

    Raises:
        ValueError: If any parameter is negative
    """
    pass
```

---

## File Organization

### Directory Structure

```
engineering_tools/
├── mech_core/          # Core engineering calculations
│   ├── analysis/       # Analysis modules (FEA, thermal, etc.)
│   ├── standards/      # Industry standards and codes
│   └── design/         # Design calculation modules
├── projects/           # Project-specific implementations
└── simulation/         # Discrete event simulation
    └── core/          # Simulation engine and entities
```

### Import Organization

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import math
from typing import List, Dict

# Third-party
import numpy as np
import pandas as pd

# Local
from mech_core.standards.materials import SteelMaterial
from mech_core.analysis.structural import BeamAnalysis
```

---

## Engineering Conventions

### Units

- **Always document units** in docstrings and variable names when ambiguous
- Prefer SI units as default
- Use clear variable naming: `force_newtons`, `length_mm`, `pressure_psi`

### Physical Constants

- Define in appropriate module constants file
- Include source/reference in comments
- Use descriptive names

---

## Testing Standards

### Test File Naming

- Test files: `test_[module_name].py`
- Test classes: `Test[ClassName]`
- Test methods: `test_[specific_behavior]()`

### Test Structure

```python
def test_beam_deflection_under_point_load():
    """Test that beam deflection calculation is correct for point load."""
    # Arrange
    beam = SimpleBeam(length=10.0, modulus=200e9)
    load = 1000.0

    # Act
    deflection = beam.calculate_deflection(load)

    # Assert
    expected = 0.00125  # From hand calculation
    assert abs(deflection - expected) < 1e-6
```

---

## Version Control

### Commit Messages

Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat(heat_transfer): Add transient conduction solver

Implemented finite difference method for 1D transient heat
conduction with support for temperature-dependent properties.

Closes #42
```

---

## Code Review Checklist

- [ ] Code follows style guide
- [ ] All functions have type hints
- [ ] Public APIs have docstrings
- [ ] Tests are included and passing
- [ ] Units are clearly documented
- [ ] No hardcoded magic numbers (use named constants)
- [ ] Error handling is appropriate
- [ ] Code is DRY (Don't Repeat Yourself)
