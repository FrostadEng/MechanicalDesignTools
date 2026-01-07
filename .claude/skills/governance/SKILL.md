---
name: governance
description: Protocols for reading Architect specifications and filing implementation reports.
---

# Governance Protocol

## Instruction: Read Active Spec
*Trigger: When starting a new task.*

1.  **Locate**: Find the latest file in `.project_governance/specs/` (exclude `archive/`).
2.  **Summary**: Output the 3-bullet summary of the objective.
3.  **Library Check (Context7 Integration)**:
    - **Scan**: Does the Spec mention external libraries (e.g., `pandas`, `scipy`, `pint`)?
    - **Action**: If YES, use the `context7` tool to fetch the *latest* documentation for that specific module.
    - *Goal:* Verify that the methods requested in the Spec actually exist in the current version.
4.  **Internal Check**:
    - "Does this spec require me to use `mech_core`?" (Yes/No).
5.  **Confirm**: Ask user to proceed.

## Instruction: File Report
*Trigger: When task is done.*
1.  **Write**: Create `.project_governance/reports/report_[Date]_[Feature].md`.
2.  **Include**:
    - Status (Pass/Fail)
    - Files Modified
    - **External Deps**: "Verified `scipy` syntax via Context7."
3.  **Map Logic**:
    - **Check**: Did this implementation add new directories?
    - **Action**: If YES, execute "Update Map" (cartographer).
4.  **Handoff**: "Report filed. Run `/audit`."