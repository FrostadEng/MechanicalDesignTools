# EOAT PARAMETER SWEEP — PyNite FEA Script Specification
## Instruction Set for Claude Code

---

## PURPOSE

Build a Python script that performs a parametric sweep of a hockey-stick-shaped End-of-Arm Tool (EOAT) frame using PyNite (PyNiteFEA). The script analyzes the frame under multiple gravity orientations simulating robot poses, sweeps through material and section geometry combinations, and outputs a ranked table of results to both console and Excel. The goal is to find the minimum-weight structure that meets deflection and wrist load limits for a FANUC ARC Mate 120iD/12L robot carrying a Hypertherm XPR300 plasma torch for beam coping.

---

## INSTALL

```
pip install PyNiteFEA openpyxl
```

---

## FRAME GEOMETRY

The structure is a 2-member bent cantilever ("hockey stick") in 3D space.

### Nodes

All coordinates in mm. The flange center is the origin.

- **Node 1 (Flange):** X=0, Y=0, Z=0 — FIXED support (all DOF restrained)
- **Node 2 (Elbow):** X=L1, Y=0, Z=0 — where L1 = horizontal leg length (default 150 mm)
- **Node 3 (Torch):** X = L1 + L2·cos(θ), Y = -L2·sin(θ), Z = 0 — where L2 = angled leg length (default 200 mm) and θ = angle from horizontal (default 55°)

### Members

- **Member 1:** Node 1 → Node 2 (horizontal leg)
- **Member 2:** Node 2 → Node 3 (angled leg)

Both members use the same rectangular hollow section (RHS). All joints are fixed (moment-carrying).

---

## SECTION PROPERTIES

Rectangular Hollow Section (box tube). Compute from outer depth D, outer width W, and wall thickness t:

- **Area** = 2·t·(D + W) - 4·t²
- **Iy** (strong axis, bending in XY plane) = (D³·W - (D-2t)³·(W-2t)) / 12
- **Iz** (weak axis, bending out of XY plane) = (W³·D - (W-2t)³·(D-2t)) / 12
- **J** (torsional constant) = 2·t·(D-t)²·(W-t)² / (D + W - 2·t)

These are the values PyNite needs for each member's section definition.

---

## MATERIAL DATABASE

Sweep through at minimum these materials:

| Material | E (MPa) | G (MPa) | ρ (kg/m³) | Fy (MPa) |
|---|---|---|---|---|
| 6061-T6 Aluminum | 68,900 | 26,000 | 2,700 | 276 |
| 304 Stainless Steel | 193,000 | 77,000 | 8,000 | 215 |
| 4130 Steel (norm.) | 205,000 | 80,000 | 7,850 | 460 |

---

## PARAMETER SWEEP RANGES

Sweep these combinations. Every combination of material × depth × width × thickness:

- **Materials:** All three from the table above
- **Outer depth D (mm):** [50.8, 76.2, 101.6] — i.e., 2", 3", 4"
- **Outer width W (mm):** [50.8, 76.2, 101.6] — constrain W ≤ D (no need to repeat symmetric combos)
- **Wall thickness t (mm):** [1.59, 2.38, 3.18, 4.76] — i.e., 1/16", 3/32", 1/8", 3/16"

Skip any combination where t ≥ D/4 or t ≥ W/4 (walls too thick relative to section — not a real hollow section).

---

## APPLIED LOADS

### Point Loads at Node 3 (Torch Connection)

- Torch assembly mass: 2.2 kg (user input, default 2.2)
- Applied as a force vector that changes direction with each gravity orientation case

### Point Load at Midpoint of Member 1 (Sensor + Hardware)

- Sensor/manifold/shroud/window mass: 0.5 kg (user input, default 0.5)
- Apply at the midpoint of Member 1 (or as close as PyNite allows — may need an additional node at the midspan)
- Direction changes with gravity orientation

### Distributed Self-Weight on Both Members

- Compute from section Area × material density × 9.81 / 1e6 to get N/mm
- Apply as distributed load on each member
- Direction changes with gravity orientation

### Cable Load at Node 3

- Cable effective mass at wrist: 0.86 kg (user input, default 0.86)
- Applied as additional point force at Node 3 in the gravity direction

### Dynamic Multiplier

- All loads multiplied by a g-factor (user input, default 3.0)
- Run each gravity case at both 1g (static) and the dynamic multiplier

---

## GRAVITY ORIENTATION SWEEP

The robot rotates the EOAT through all orientations during beam coping. Simulate this by rotating the gravity vector relative to the frame. Sweep gravity direction in the XY plane at 30° increments (12 orientations total):

- 0° = gravity in -Y (torch hanging down, normal orientation)
- 30° 
- 60°
- 90° = gravity in -X (arm extended horizontal, gravity pulling toward flange)
- 120°
- 150°
- 180° = gravity in +Y (torch pointing up, inverted)
- 210°
- 240°
- 270° = gravity in +X (gravity pulling away from flange)
- 300°
- 330°

For each angle α, the gravity unit vector is:
- gx = -sin(α)
- gy = -cos(α)

Multiply all masses by 9.81 and by this unit vector to get force components.

Also run one case with gravity in -Z (out-of-plane, 90° robot wrist rotation) to check weak-axis bending.

That gives 13 gravity orientations × 2 load levels (static and dynamic) = 26 load cases per geometry.

---

## OUTPUT PER COMBINATION

For each material × section × gravity case, extract from PyNite:

1. **Max deflection at Node 3** — the resultant displacement √(dx² + dy² + dz²)
2. **Max deflection at sensor location** (midpoint of Member 1)
3. **Max bending moment** anywhere in the frame (both Mz and My)
4. **Max shear force** anywhere in the frame
5. **Max axial force** anywhere in the frame
6. **Bending stress at the extreme fiber** = M_max / S_min where S = I / (D/2 or W/2)
7. **Stress utilization** = max bending stress / Fy
8. **Member masses** from Area × length × density

Then across ALL gravity cases for a given geometry, record:

- **Worst-case TCP deflection** (max across all orientations, at dynamic load level)
- **Worst-case sensor deflection**
- **Worst-case bending stress and utilization**
- **Which gravity orientation produced the worst case**
- **Total structure mass** (both members)
- **Total tool mass** (structure + torch + sensor + cable + 0.2 kg fasteners)

---

## WRIST LOAD CALCULATIONS

For each geometry combination (using the worst-case total tool mass), compute:

- **CG location** from Node 1 — estimate as weighted average of member CGs, torch at Node 3, sensor at Member 1 midpoint
- **J4/J5 moment** = total_mass × 9.81 × CG_radial_distance_from_flange (in meters) → N·m
- **J6 moment** = total_mass × 9.81 × CG_X_offset × 0.3 → N·m (rough eccentricity estimate)
- **J4/J5 inertia** = total_mass × CG_radial_distance² → kg·m²
- **J6 inertia** = total_mass × CG_X_offset² → kg·m²

Robot limits (12L):
- Max payload: 12 kg
- J4/J5 moment: 22.0 N·m
- J6 moment: 9.8 N·m
- J4/J5 inertia: 0.65 kg·m²
- J6 inertia: 0.17 kg·m²

Flag any combination that exceeds any limit.

---

## OUTPUT FORMAT

### Console Output

Print a summary table sorted by total tool mass (ascending), showing only combinations that pass all robot limits. Columns:

```
Material | D(mm) | W(mm) | t(mm) | Frame Mass(kg) | Total Mass(kg) | Max TCP Defl(mm) | Max Stress Util(%) | Worst Grav Angle | J4/5 Moment(N·m) | J4/5 Util(%) | PASS/FAIL
```

Print the top 20 lightest passing designs. Then print the top 5 stiffest passing designs (sorted by min deflection).

### Excel Output

Save full results to `eoat_sweep_results.xlsx` with two sheets:

**Sheet 1: "All Results"** — every combination, one row per geometry (with worst-case values across all gravity orientations). Include all columns listed above plus Iz, Iy, J, area, and all individual wrist limit checks. Color-code: green rows pass all limits, red rows fail one or more.

**Sheet 2: "Passing Designs"** — only combinations that pass all limits, sorted by total mass ascending. This is the design selection table.

---

## USER CONFIGURATION

Put all user-adjustable inputs at the top of the script in a clearly marked CONFIG section:

```python
# ══════════════════════════════════════════════
# USER CONFIGURATION — CHANGE THESE VALUES
# ══════════════════════════════════════════════

# Bracket geometry (mm, degrees)
L1 = 150          # Horizontal leg length (flange to elbow)
L2 = 200          # Angled leg length (elbow to torch connection)
THETA = 55        # Angle of angled leg from horizontal (degrees)

# Component masses (kg)
TORCH_MASS = 2.2       # XPR300 torch + receptacle + sleeve
SENSOR_MASS = 0.5      # IL-300 + garolite block + manifold + window + shroud
CABLE_MASS = 0.86      # Effective cable mass at wrist
FASTENER_MASS = 0.2    # Rivnuts, bolts, shroud sheet, misc

# Dynamic load multiplier
G_FACTOR = 3.0         # 1.0 = static only, 3.0 = typical robot accel

# Deflection limit (mm) — set to your allowable TCP error budget
MAX_DEFLECTION = 0.5   # mm, default 0.5 — adjust based on process needs

# Gravity sweep resolution (degrees)
GRAVITY_STEP = 30      # Sweep gravity every N degrees (30 = 12 orientations)
```

---

## IMPORTANT IMPLEMENTATION NOTES

1. **PyNite model must be rebuilt for each combination.** Do not try to modify an existing model — create a fresh FEModel3D for each material × section × load case. This avoids stale state.

2. **PyNite uses member local axes.** When applying distributed loads, the direction ('FY', 'FX', 'FZ') refers to global axes when using the 'FY' direction specifier. Check PyNite docs — use global direction distributed loads.

3. **Node naming:** Use string names 'N1', 'N2', 'N3' (and 'N_mid' if adding a midspan node for the sensor load).

4. **If a midspan node is needed for the sensor point load:** Add Node N_mid at the midpoint of Member 1 and split Member 1 into Member 1a (N1→N_mid) and Member 1b (N_mid→N2). This gives a clean point for applying the sensor load and reading sensor location deflection.

5. **Units throughout:** mm, N, MPa, kg. PyNite works in consistent units — keep everything in mm-N-MPa-kg and the results come out in mm (displacement) and N·mm (moments).

6. **Convert moments to N·m for wrist checks:** divide PyNite moment output by 1000.

7. **The script should run in under 5 minutes.** With ~100 geometry combinations × 26 load cases = ~2600 analyses, each taking a fraction of a second, this should be fast.

8. **Error handling:** Some extreme combinations (very thin walls, very small sections) may produce near-singular stiffness matrices. Wrap each analysis in try/except and skip failures, logging them.

---

## DELIVERABLES

The script should be a single Python file called `eoat_sweep.py` that:

1. Runs from the command line with no arguments (all config at top of file)
2. Prints progress (e.g., "Analyzing combination 47/108: 304SS, 76.2×50.8×2.38mm...")
3. Prints the ranked summary tables to console
4. Saves the Excel file to the current directory
5. Prints the filename and total runtime at the end

---

## WHAT THIS SCRIPT DOES NOT DO

- It does not model isogrid or pocketed sections — it models solid-wall RHS only. The results tell you the minimum solid-wall section that works; from there the user decides if lightening pockets are needed and how much material can be removed.
- It does not model the flange plate, gussets, or joints. It assumes fixed connections.
- It does not model thermal loads, fatigue, or vibration modes.
- It does not model the torch, sensor, or other components geometrically — only as point masses.