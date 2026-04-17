# Phase 2: Pre-computation Artifacts - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate and freeze all pre-computed lookup tables and databases needed by the Phase 3 search pipeline. Four independent artifacts are produced:
1. `valid_tools.json` — tool table (~1,044 valid entries, ~150–200 cluster representatives)
2. `riser_validity_table.json` — (section, height) pass/fail table with δ_TCP and f₁
3. FCL collision scene — static boundary walls + active beam insertion capability validated
4. `target_database/` — straight-cut sweep poses + cope trajectories for full AISC catalog, frozen read-only

**What this phase does NOT include:**
- Grid search workers (Phase 3)
- Long-run execution (Phase 4)
- Scoring or result reports (Phase 5)

</domain>

<decisions>
## Implementation Decisions

### Plan Decomposition
- **D-01:** Phase 2 is split into **4 plan files, one per artifact**:
  - `02-01-PLAN.md` — Tool table (TOOL-01 through TOOL-06)
  - `02-02-PLAN.md` — Riser deflection + modal model (RISER-01 through RISER-05)
  - `02-03-PLAN.md` — Collision environment (COLL-01 through COLL-04); FCL installation gate is the first task
  - `02-04-PLAN.md` — Target database (TARG-01 through TARG-05)
- **D-02:** Each plan is independently reviewable and committable. Plans 1 and 2 share no FCL dependency and can run in parallel internally; Plans 3 and 4 require FCL to be validated first.

### Wrist Load Diagram Implementation (TOOL-02, TOOL-03)
- **D-03:** The allowable wrist load region is modeled as **nested ellipses** in (CG_Z, CG_XY) space. One ellipse per mass data point; semi-axes interpolated linearly between mass levels for intermediate masses.
  - Check: `(CG_Z / max_Z)² + (CG_XY / max_XY)² ≤ 1`
- **D-04:** The complete wrist load diagram table (corrected from spec — user-provided authoritative values):

  | Payload | Max Z offset | Max X,Y offset |
  |---------|-------------|----------------|
  | 05 kg   | 60.2 cm (602 mm) | 48.9 cm (489 mm) |
  | 10 kg   | 39.8 cm (398 mm) | 32.7 cm (327 mm) |
  | 15 kg   | 26.4 cm (264 mm) | 21.8 cm (218 mm) |
  | 20 kg   | 17.5 cm (175 mm) | 16.3 cm (163 mm) |
  | 25 kg   | 12.2 cm (122 mm) | 13.1 cm (131 mm) |

  Note: The PROJECT.md table was missing the 15/20/25 kg XY values. This table supersedes it. Add these values to `config.py` as `WRIST_LOAD_TABLE` before implementing TOOL-02.

- **D-05:** For a tool with safety-factored mass M between two table rows, linearly interpolate both `max_Z` and `max_XY` semi-axes from the bounding rows. If M > 25 kg, the tool is rejected outright (above payload spec). If M < 5 kg, the 5 kg row is used as the boundary (conservative, but any valid tool at <5 kg will pass).

### Torch Roll Convention for Target Poses (TARG-01, TARG-02, TARG-03)
- **D-06:** Physical geometry: boom extends along wrist Z (normal out of flange); torch body extends in +X from puck at boom end. Direct mounting to wrist would produce an L-shape with torch pointed downward.
- **D-07:** Target pose 6-DOF convention: the TCP approach direction (torch tip into material) is set to `-surface_normal`. Torch roll about the approach axis is pinned by projecting **world +Z** onto the plane perpendicular to the approach direction and normalizing. This keeps the boom as close to vertical as possible — physically consistent with the puck mounting geometry.
  - Fallback: if approach direction is parallel to world +Z (overhead cuts), use world +X as the secondary reference.
- **D-08:** Each target pose is stored as a 4×4 homogeneous transform (TCP frame in world space). The IK solver uses this with the tool's `tcp_transform` to compute the required wrist frame.

### FCL Installation Gate (COLL-01)
- **D-09:** python-fcl has not been tested on this machine (Ubuntu 24.04 risk flagged in Phase 1). Plan 3 opens with a **blocking FCL validation task**:
  1. `sudo apt-get install libfcl-dev` (verify version compatibility)
  2. `pip install python-fcl` in venv_optimizer
  3. Run a 3-line smoke test: `import fcl`, create a box geometry, run a broadphase query
  4. If smoke test passes: continue with Plan 3
  5. If smoke test fails: **stop execution**; document failure + fallback options before continuing

### Claude's Discretion
- Exact `config.py` field name for `WRIST_LOAD_TABLE` (nested dict or parallel lists)
- Whether eoat_sweep.py cantilever formula is reusable for tool boom deflection (read before implementing TOOL-04)
- Clustering implementation: k-means vs. binning approach for tool TCP/CG clustering (spec says binning at 5 mm; k-means is acceptable if binning produces too few or too many clusters)
- FCL fallback approach if python-fcl fails (docker-isolated FCL, alternative collision library) — document options and stop for user decision

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (Authoritative)
- `Robot_Simulations/Optimizing_Robot_Placement.md` — V3 master spec. **Sections 5–9 are this phase's primary source:**
  - Section 5: Tool design table (geometry, design variables, cable model, evaluation, clustering, output)
  - Section 6: Riser deflection model (closed-form superposition, column bending + baseplate rotation)
  - Section 7: Modal frequency check (f₁ ≥ 15 Hz criterion, k_eff/m_eff formula)
  - Section 8: Collision environment (wall planes, active beam mesh, robot self-collision)
  - Section 9: Target generation (beam catalog, clearance rules, straight-cut poses, cope trajectories, difficulty ranking)

### Robot Manual
- `Robot_Simulations/datasheets/HRP-2 Fanuc Robot M-20iD Mechanical Unit Operators Manual.md` — Fig 3.5c (wrist load diagram). **Note:** Use the corrected table in D-04 of this context file, not the partial table in PROJECT.md.

### Existing Codebase Assets
- `engineering_tools/projects/PCR42 EOA Tool Design/eoat_sweep.py` — Existing EOAT parametric sweep (different robot, PyNiteFEA-based). **Read before implementing TOOL-04** (boom deflection). May have reusable cantilever geometry math, though V3 uses closed-form formula not FEA.
- `engineering_tools/mech_core/components/members/aisc.py` — AISC catalog loader (2,299 shapes). Required for TARG-01 and COLL-02.
- `Robot_Simulations/optimizer/config.py` — Physical constants already defined: riser sections/heights, tool geometry, TCP budget gates. **Add WRIST_LOAD_TABLE here before implementing TOOL-02.**
- `Robot_Simulations/optimizer/logging_utils.py` — Dual-unit logging utility. Use for all physical output in this phase.

### Prior Phase Context
- `.planning/phases/01-solver-foundation/01-CONTEXT.md` — Architecture decisions (optimizer module location, venv, config.py structure, dual-unit convention)
- `.planning/phases/01-solver-foundation/01-PATTERNS.md` — Existing code patterns to follow
- `.planning/phases/01-solver-foundation/01-VERIFICATION.md` — What Phase 1 delivered; confirms solver is validated gate-keeper

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Robot_Simulations/optimizer/config.py`: All riser section properties (I, A, mass/m), stock heights, tool geometry bounds, TCP gate thresholds, and search grid — all already defined. Add `WRIST_LOAD_TABLE` here.
- `Robot_Simulations/optimizer/logging_utils.py`: `log_dual()` for all physical quantity output
- `engineering_tools/projects/PCR42 EOA Tool Design/eoat_sweep.py`: Cantilever deflection logic (different robot, but same physics)
- `engineering_tools/mech_core/components/members/aisc.py`: AISC catalog — confirmed working, 2,299 shapes

### Established Patterns
- **No magic numbers**: All constants in `config.py` only. Phase 2 modules import from config, never hard-code values.
- **spawn multiprocessing**: If any Phase 2 generator is parallelized (e.g., target generation), use `spawn` start method — not `fork`.
- **SI internal, dual-unit output**: All computation in meters/kg/rad; log in both units.
- **Separate venv**: All Phase 2 work runs under `venv_optimizer`, not the project `.venv`.

### Integration Points
- `tool_table.py` → outputs `valid_tools.json` → consumed by Phase 3 Phase A search
- `riser_model.py` → outputs `riser_validity_table.json` → consumed by Phase 3 filter cascade (first filter)
- `collision_env.py` → exports `build_static_scene()` and `add_beam_mesh(scene, aisc_shape)` → consumed by Phase 3 worker initializer
- `target_db.py` → outputs `target_database/` → frozen; consumed read-only by Phase 3 beam evaluator
- All 4 modules: Python files under `Robot_Simulations/optimizer/`, importable by Phase 3 workers

</code_context>

<specifics>
## Specific Ideas

- **Corrected wrist load table**: D-04 has the full 5-row table with both semi-axes. This corrects the partial data in PROJECT.md (which was missing XY values for 15/20/25 kg). Planner must add this to `config.py` as `WRIST_LOAD_TABLE`.
- **Ellipse-in-onion metaphor**: User described the wrist diagram as "layers of an onion" — each mass level is one ellipse layer. Interpolating between them as mass increases is the intended model.
- **Torch physical geometry**: Boom along wrist Z (out of flange); torch body in +X from puck at boom tip; direct mount would look like an L-shape with torch pointing down. This is the physical geometry underlying all target pose calculations.
- **FCL is unknown risk**: Don't assume it works. The blocking gate in Plan 3 is non-negotiable.

</specifics>

<deferred>
## Deferred Ideas

- Robot link STL meshes for COLL-04 self-collision: Mentioned in Phase 1 deferred. Needed for Phase 2 Plan 3 (COLL-04). Planner should check whether Fanuc M-20iD/20 URDF link meshes are available in `Robot_Simulations/` before designing COLL-04 implementation.
- k_anchor sensitivity margin (RISER-05): Spec calls for flagging k_anchor sensitivity margin in riser_validity_table output. This is a RISER requirement, not deferred, but planner should check: is there a reference measurement for k_anchor, or is the nominal 4×10⁶ N·m/rad from the spec the only source?
- Cable stiffness reaction on wrist (Section 5C): Spec explicitly notes this is NOT modeled and should be flagged for hardware validation with strain gauge. Record this unmodeled term in the tool table output (flag field) for Phase 5 error budget reporting.

</deferred>

---

*Phase: 02-pre-computation-artifacts*
*Context gathered: 2026-04-16*
