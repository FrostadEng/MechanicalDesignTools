# Architecture Decision Records (ADR)

**Maintained by:** Antigravity
**Last Updated:** 2025-12-17

---

## Overview

This document captures high-level architectural decisions for the MechanicalDesignTools project.

**PERMISSIONS:**
- ✍️ **Antigravity:** Write access (maintains architectural decisions)
- 👁️ **Claude:** Read access (follows these decisions during implementation)

---

## Active Decisions

### ADR-001: Three-Layer Architecture

**Status:** Adopted
**Date:** 2025-12-17

**Context:**
The project follows a three-layer architecture:
1. **Core Layer** (`mech_core/`) - Fundamental calculations and domain logic
2. **Projects Layer** (`projects/`) - Project-specific implementations
3. **Simulation Layer** (`simulation/`) - Discrete event simulation capabilities

**Decision:**
Maintain clear separation between these layers with well-defined interfaces.

**Consequences:**
- Better modularity and testability
- Easier to maintain and extend
- Clear dependency flow

---

### ADR-002: Material Standards

**Status:** Adopted
**Date:** 2025-12-17

**Context:**
Material properties need to be standardized and easily accessible.

**Decision:**
Use centralized material databases in `mech_core/standards/materials/` with support for:
- Steel standards (AISC, ASTM)
- Aluminum standards
- Other engineering materials

**Consequences:**
- Consistent material properties across project
- Easy to extend with new materials
- Traceable to industry standards

---

## Template for New ADRs

```markdown
### ADR-XXX: [Title]

**Status:** [Proposed | Adopted | Deprecated | Superseded]
**Date:** YYYY-MM-DD

**Context:**
[Describe the context and problem statement]

**Decision:**
[Describe the decision that was made]

**Consequences:**
[Describe the consequences, both positive and negative]
```
