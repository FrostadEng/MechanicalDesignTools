
# Specification: PCR41 High-Fidelity Discrete Event Simulation, 2025-12-19_PCR41_Simulation
**Feature:** PCR41 "Sliding Window" Physics Engine
**Version:** 1.0.1 (Final Engineering Sign-off)
**Status:** READY FOR BUILD
**Architect:** Antigravity / Senior Engineer

---

## 1. Objective
Build a high-fidelity physics-based Discrete Event Simulation (DES) for the PCR41 machine.
**Key Constraints:**
1.  **Window Logic:** The robot operates in a finite 200mm window. Features larger than this must be split.
2.  **State Machine:** No ray-casting. Use explicit "Safe-Plane" retract/traverse logic.
3.  **Safety Interlock:** Deterministic PLC handshake (simpy.Event) between Robot and Feeder.
4.  **Process Physics:** Cutting speeds derived from Enthalpy (mech_core) and Tool Power.

---

## 2. Technical Definitions

### 2.1 The SafetyPLC Handshake (`simpy.Event`)
**File:** `simulation/core/machines/subsystems/logic/safety_plc.py`
Instead of `simpy.Resource` (which queues), use `simpy.Event` (which signals). This prevents deadlocks where the Feeder waits for a Robot that is waiting for the Feeder.

*   **States (Enum):**
    *   `RobotState`: [HOME, MOVING_TO_SAFE, IN_WINDOW, FAULT]
    *   `FeederState`: [IDLE, MOVING, LOCKED]
*   **Logic:**
    *   `request_robot_entry()`: Yields until `feeder_is_idle` event is set. Then clears `feeder_is_idle`.
    *   `release_robot_entry()`: Sets `feeder_is_idle`.
    *   `request_feeder_move()`: Yields until `robot_is_home` event is set. Then clears `robot_is_home`.

### 2.2 Process Energy Calculation
**File:** `simulation/core/machines/subsystems/eoa_tools/process_physics.py`
Adapter to bridge `mech_core` physics to the Controller.

*   **Inputs:** `MaterialName` (str), `Thickness` (mm), `ToolPower` (kW), `Kerf` (mm).
*   **Logic:**
    1.  Call `mech_core.standards.materials.steel.get_material(MaterialName)`.
    2.  Call `mech_core.analysis.heat_transfer.phase_change.specific_melting_energy_volumetric` to get Enthalpy ($J/mm^3$).
    3.  Calculate Removal Rate: $Rate = (Power \times Efficiency) / Enthalpy$.
    4.  Calculate Linear Speed: $Speed = Rate / (Thickness \times Kerf)$.
*   **Output:** Speed in `mm/sec` (float).

### 2.3 Transition Cost Matrix (Configuration)
**File:** `simulation/core/machines/PCR41/config.py`
Store the time penalties for Face-to-Face transitions.

```python
# Transition Penalties (Seconds)
# [Source Face][Target Face]
TRANSITION_COSTS = {
    "v": {"v": 0.0, "o": 1.5, "u": 1.5, "h": 2.5}, # Web to others
    "o": {"v": 1.5, "o": 0.0, "u": 4.0, "h": 1.5}, # Top to Bottom is slow (4.0s)
    "u": {"v": 1.5, "o": 4.0, "u": 0.0, "h": 1.5}, # Bottom to Top is slow (4.0s)
    "h": {"v": 2.5, "o": 1.5, "u": 1.5, "h": 0.0}  # Rear
}
```

---

## 3. Implementation Plan

### Phase 1: Foundation Classes
1.  **Create `SafetyPLC` class.** Verify logic with a simple test case (Feeder locks, Robot waits).
2.  **Create `ProcessEnergyCalculator`.** Ensure it handles unit conversions from `mech_core` correctly (J/m^3 to J/mm^3).
3.  **Create `config.py`** with the Transition Matrix.

### Phase 2: The Brain (`WindowIndexer`)
**File:** `simulation/core/machines/PCR41/indexer.py`
Refactor the existing `Indexer`.
*   **Input:** `DSTVData`.
*   **Output:** `List[MachineCycle]`.
*   **Algorithm:**
    *   Initialize `window_start_x = 0`.
    *   Loop until all features processed.
    *   Identify features fully inside `[window_start, window_start + 200]`.
    *   Identify features spanning the boundary (Bisect candidates).
    *   **Bisect Logic:**
        *   Generate `PROCESS` cycle (Partial cut).
        *   Generate `SEVER` cycle. **Length** = `DSTVData.profile_height` (Conservative vertical chop).
        *   Generate `INDEX` cycle (Move window).
    *   Advance `window_start_x`.

### Phase 3: Integration (`PCR41_Controller`)
**File:** `simulation/core/machines/PCR41/pcr41.py`
Update `run_production` loop.
*   Initialize `SafetyPLC`.
*   **Motion Loop:**
    *   Before moving Robot: `yield plc.request_robot_entry()`.
    *   Calculate Move Time: `kinematics.trapezoidal()` + `TRANSITION_COSTS[old_face][new_face]`.
    *   Calculate Process Time: `path_length / energy_calc.get_speed()`.
    *   After Robot Home: `plc.release_robot_entry()`.
*   **Feeder Loop:**
    *   Before Indexing: `yield plc.request_feeder_move()`.

---

## 4. Acceptance Criteria
1.  **Unit Tests:**
    *   `test_safety_plc.py`: Verify mutual exclusion (Deadlock prevention).
    *   `test_process_physics.py`: Verify A36 steel calculation returns realistic speed (not NaN).
    *   `test_window_indexer.py`: Verify a 1000mm feature generates 5+ cycles (Process -> Sever -> Index).
2.  **Simulation Run:**
    *   Run `sample_beam.nc1`.
    *   Verify logs show: "Robot waiting for Feeder" and "Feeder waiting for Robot".
    *   Verify logs show variable cutting speeds for Web vs Flange.
```

### Next Steps for You
1.  Save this markdown file.
2.  Run your builder command (e.g., `claude -p .project_governance/specs/active_spec.md`).
3.  Sit back and watch the machine build itself.