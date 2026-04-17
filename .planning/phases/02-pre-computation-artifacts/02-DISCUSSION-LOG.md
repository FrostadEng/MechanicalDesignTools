# Phase 2: Pre-computation Artifacts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 02-pre-computation-artifacts
**Areas discussed:** Wrist load diagram check, Torch roll convention, python-fcl installation gate, Plan decomposition

---

## Plan Decomposition

| Option | Description | Selected |
|--------|-------------|----------|
| 2 plans: structural + geometric | Plan 1: FCL gate + tool table + riser model. Plan 2: collision env + target database | |
| 4 plans: one per artifact | Plan 1: tool table, Plan 2: riser model, Plan 3: collision env, Plan 4: target database | ✓ |
| 1 plan: all of Phase 2 | Single PLAN.md covering all 4 artifacts | |

**User's choice:** 4 plans — one per artifact. Maximum granularity for independent review and commit.
**Notes:** FCL gate belongs at top of Plan 3 (collision environment), since Plans 1 and 2 (tool table, riser model) have no FCL dependency.

---

## Wrist Load Diagram Check

| Option | Description | Selected |
|--------|-------------|----------|
| Linear interpolation | Interpolate max_Z and max_XY linearly between the 5 mass data points | |
| Conservative polynomial fit | Fit polynomial/hyperbola, always conservative near boundary | |
| Hard mass-band cutoffs | Step function using spec's 5 rows | |
| **Nested ellipses (user-specified)** | Check (CG_Z/max_Z)² + (CG_XY/max_XY)² ≤ 1 per mass level, interpolate between levels | ✓ |

**User's choice:** Nested ellipses — "like layers of an onion." Each mass level defines one ellipse; interpolate semi-axes between levels for intermediate masses.

**Follow-up — Missing XY values at 15/20/25 kg:**

| Option | Description | Selected |
|--------|-------------|----------|
| Extrapolate from 5–10 kg trend | Fit and extrapolate | |
| Use 10 kg XY for all higher | Conservative cap | |
| Fail-safe reject above 10 kg | Very safe | |
| **User provided full table** | User supplied authoritative values for all 5 rows | ✓ |

**User provided the complete corrected table:**
| Payload | Max Z offset | Max X,Y offset |
|---------|-------------|----------------|
| 05 kg | 60.2 cm | 48.9 cm |
| 10 kg | 39.8 cm | 32.7 cm |
| 15 kg | 26.4 cm | 21.8 cm |
| 20 kg | 17.5 cm | 16.3 cm |
| 25 kg | 12.2 cm | 13.1 cm |

**Notes:** This corrects the partial table in PROJECT.md which was missing XY values for 15/20/25 kg rows. This table is authoritative — add to `config.py` as `WRIST_LOAD_TABLE`.

---

## Torch Roll Convention

| Option | Description | Selected |
|--------|-------------|----------|
| Normal to beam cross-section | Torch Z perpendicular to surface, X in fixed world plane | |
| Gravity-aligned | Puck always hanging toward gravity | |
| Best-IK pick | Try 4 roll orientations, pick best manipulability | |
| **Physical geometry clarification** | User described: boom along wrist Z, torch +X, puck Z = wrist Z normal out of flange | ✓ |

**User's choice:** Physical geometry clarification — the roll is not a free design choice but follows from the puck mounting geometry. Puck Z = wrist Z (normal out of flange). Torch extends in +X from puck. Direct mounting makes an L-shape.

**Follow-up — 6th DOF pin:**

| Option | Description | Selected |
|--------|-------------|----------|
| Puck face keeps world-Z up | Roll TCP so puck normal points toward world +Z | |
| Fixed torch_angle per tool | TCP transform encodes everything; target poses just specify position + surface_normal | |
| **World +Z projection** | Project world +Z onto plane perpendicular to approach; normalize | ✓ |

**User's choice:** World +Z projection — "World z, the z normal of the torch puck step model attaches directly to the origin at the wrist." Keep boom as vertical as possible.
**Notes:** Fallback to world +X for overhead cuts where approach direction is parallel to world +Z.

---

## python-fcl Installation Gate

| Option | Description | Selected |
|--------|-------------|----------|
| Not tested yet — make it Plan 1 gate | Plan 3 opens with blocking FCL smoke test | ✓ |
| Already works on this machine | Skip gate | |

**User's choice:** Not tested yet — blocking FCL gate at top of Plan 3.
**Notes:** If smoke test fails, execution stops. Document failure + fallback options before continuing. This is a hard blocker for Plans 3 and 4.

---

## Claude's Discretion

- Exact config.py field name for WRIST_LOAD_TABLE
- Whether eoat_sweep.py cantilever formula is reusable for TOOL-04
- Clustering implementation: k-means vs. binning for TCP/CG clusters
- FCL fallback approach if python-fcl fails

## Deferred Ideas

- Robot link STL meshes for COLL-04: Need to check if Fanuc M-20iD/20 URDF link meshes are available before designing COLL-04
- k_anchor sensitivity margin source: Is the nominal 4×10⁶ N·m/rad the only reference?
- Cable stiffness reaction (unmodeled): Flag in tool table output for Phase 5 error budget
