# Implementation Agent Capabilities (Active MCPs)

These are the **Actions** the Builder (Claude) can perform.

## 1. Documentation Lookup (Context7)
- **Can:** Fetch up-to-date syntax and examples for libraries.
- **Trigger:** "Check Context7 for `simpy` resource syntax."
- **Constraint:** Can only look up libraries listed in `toolbox.md`.

## 2. Database Access (Postgres MCP)
- **Can:** Query tables, inspect schemas, check relation integrity.
- **Trigger:** "Query the [table_name] to verify schema matches the object."
