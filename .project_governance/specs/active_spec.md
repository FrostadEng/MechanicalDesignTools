
# Specification: Process Physics Refactor & Composite Constraint Engine
**Feature:** Composite Physics for Manufacturing Tools
**Date:** 2025-12-19
**Version:** 2.0 (Refactor)
**Architect:** Antigravity

---

## 1. Objective
Refactor the detailed process physics out of specific tool drivers (`fiber_laser.py`, `plasma.py`) and into the core library (`mech_core`). Implement a "Composite Constraint" model where tools are rate-limited by multiple physical factors:
1.  **Enthalpy Limit:** Power / (Specific Energy * Area).
2.  **Fluid Dynamics Limit:** Nozzle velocity / Gas handling capacity.

**Constraint:** Do NOT replace existing custom Heat Transfer logic with `calebbell/heat_transfer` at this time (User Preference). DO use `calebbell/fluids` for the new gas logic.

---

## 2. Technical Reference Patterns ("Golden Snippets")

### Pattern A: The Composite Physics Call (in Tool Driver)
The tool driver acts as an orchestrator, calling specific physics modules.

```python
# Inside FiberLaser or PlasmaTorch driver
def calculate_speed(self, material, thickness, power, nozzle_pressure):
    # 1. Thermal Limit (mech_core.analysis.manufacturing.thermal_removal)
    v_thermal = calculate_melting_speed(
        power=power,
        enthalpy=material.enthalpy,
        area=kerf * thickness
    )

    # 2. Fluid Limit (mech_core.analysis.fluid_dynamics.gas_jets)
    v_gas = calculate_clearing_speed(
        pressure=nozzle_pressure,
        nozzle_dia=self.nozzle_diameter,
        viscosity=material.molten_viscosity
    )

    # 3. The "Constraint Pipeline" (Worst Case Wins)
    return min(v_thermal, v_gas) * self.usage_factor
```

### Pattern B: Fluid Dynamics Wrapper (`fluids`)
Using `calebbell/fluids` to model compressible flow through a nozzle.

```python
import fluids
from fluids.compressible import isentropic_T_v_P_rho
from engineering_tools.mech_core.standards.units import ureg

def calculate_exit_velocity(pressure_upstream, pressure_downstream, temp_upstream_k, gamma=1.4):
    # Isentropic flow calculation
    # P2/P1 -> T2, v2, P2, rho2
    _, velocity, _, _ = isentropic_T_v_P_rho(
        P1=pressure_upstream,
        T1=temp_upstream_k,
        P2=pressure_downstream,
        k=gamma,
        R=287.05 # Gas constant for air approx
    )
    return velocity * ureg.meter / ureg.second
```

---

## 3. Implementation Plan

### Phase 1: Cosmology (File Structure)
Create the new taxonomy in `mech_core`.
*   [NEW] `engineering_tools/mech_core/analysis/manufacturing/`
    *   `__init__.py`
    *   `thermal_removal.py` (The Heater Logic)
*   [NEW] `engineering_tools/mech_core/analysis/fluid_dynamics/`
    *   `__init__.py`
    *   `gas_jets.py` (The Blower Logic)

### Phase 2: The Logic Migration (Refactor)
1.  **Extract `ProcessEnergyCalculator`:**
    *   Move logic from `fiber_laser.py` to `thermal_removal.py`.
    *   Rename to `calculate_melting_speed()`.
    *   Keep it stateless (functional).
2.  **Implement `gas_jets.py`:**
    *   Import `fluids`.
    *   Implement basic nozzle velocity calculation (Bernoulli/Isentropic).
    *   Create a heuristic for "Slag Clearing Speed" (e.g., `Speed = k * GasMomentum`).

### Phase 3: The Orchestrator Update (Drivers)
1.  **Update `fiber_laser.py`:**
    *   Remove internal `ProcessEnergyCalculator`.
    *   Import `calculate_melting_speed` from `mech_core`.
    *   Add `calculate_clearing_speed` call (if applicable, or just placeholder for now).
2.  **Update `plasma.py`:**
    *   Remove internal `calculate_cut_speed`.
    *   Import shared logic.
    *   **DRY Victory:** Both files now use the same import.

---

## 4. Verification

### Unit Tests
*   `tests/mech_core/test_thermal_removal.py`: Verify migration didn't break math.
*   `tests/mech_core/test_gas_jets.py`: Verify `fluids` integration returns reasonable velocities (e.g. supersonic checking).
*   `tests/simulation/test_tools_composite.py`: Verify `min(thermal, fluid)` logic picks the slower speed.

### Integration
*   Run `test_pcr41_integration.py`. The simulation should generate identical results (since new fluid limits should be tuned effectively 'infinite' or non-limiting for the baseline test to ensure regression safety, OR we accept the lower speed). *Decision: Set gas limit high for now to ensure parity.*

