---
phase: 01
slug: solver-foundation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-16
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| N/A | Local offline computation tool. No network, no user input, no external API calls. | None — all inputs are hardcoded constants from the Fanuc manual. |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-01-01 | T (Tampering) | config.py constants | accept | Local file; no network vector. Accept documented. | closed |
| T-01-02 | I (Info Disclosure) | venv_optimizer | accept | `venv_optimizer/` excluded by `.gitignore` (line 1). No secrets stored. | closed |
| T-02-01 | T (Tampering) | OPW parameters in config.py | accept | Accepted risk — see Accepted Risks Log. Human Fig 3.2a check deferred to post-phase UAT item 1. | closed |
| T-02-02 | D (Denial of Service) | multiprocessing spawn | accept | Bounded `Pool(2)` on local machine; no external trigger path. | closed |
| T-02-03 | T (Tampering) | py-opw-kinematics PyPI package | accept | Pinned to `==1.0.0` in `requirements.txt`. Verified on hardware during research. No network calls at runtime. | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-02-01 | OPW parameters (a1=150mm, a2=-615mm, c1=500mm, c2=640mm, c3=200mm, c4=65mm) were derived by numerical search after original assumed values proved wrong. All six are tagged `[VERIFY-FIG3.2A]` in config.py. The FK→IK validation suite (500/500 round-trips, position <0.01mm, orientation <0.01°) confirms internal self-consistency but cannot confirm physical joint mapping. Human visual check against Fanuc manual B-84074EN/03 Fig 3.2a deferred to UAT item 1. Risk accepted for phase advancement; must be resolved before optimizer results are used for physical hardware decisions. | Carter F | 2026-04-16 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-16 | 5 | 5 | 0 | gsd-security-auditor (claude-sonnet-4-6) |

### 2026-04-16 Audit Detail

| Metric | Count |
|--------|-------|
| Threats found | 5 |
| Closed (accept) | 4 |
| Closed (accepted risk) | 1 |
| Open | 0 |

**T-02-01 note:** Auditor confirmed that `Robot_Simulations/Optimizing_Robot_Placement.md` contains the pre-update estimated values (a1≈75mm, c1≈425mm, c2≈840mm), not the current config.py values. This document does not constitute Fig 3.2a verification for the current parameters. Risk accepted by user; UAT item 1 tracks the open verification task.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-16
