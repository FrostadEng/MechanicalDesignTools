---
name: cartographer
description: Tools to maintain the repository map. Use ONLY when the project structure has changed significantly.
---

# Cartography Protocol

## Instruction: Update Map
*Trigger: Explicit user command "Update the map".*

1.  **Scan**: Run `tree -L 3 -I "__pycache__|venv|.git"` (Limit depth to save tokens).
2.  **Analyze**: Read the existing `.project_governance/repo_map.md`.
3.  **Rebuild**:
    - Update the entry for any new folders.
    - **Crucial**: Do not delete the descriptions of existing folders unless they are empty.
    - **Format**: `path/to/folder`: [Description].
4.  **Save**: Overwrite `repo_map.md`.