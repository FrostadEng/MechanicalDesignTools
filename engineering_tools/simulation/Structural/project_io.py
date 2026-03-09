"""
simulation/Structural/project_io.py

JSON-based project save / load for StructuralDocument.

All model state — nodes, members, supports, loads, custom sections,
load cases and sequence counters — is serialised via the document's own
to_dict() / from_dict() round-trip.  The file format is plain JSON so
projects are human-readable and version-controllable.
"""

from __future__ import annotations

import json
from pathlib import Path

from .document import StructuralDocument

# Default folder: engineering_tools/projects/
_DEFAULT_PROJECTS_DIR = Path(__file__).parents[2] / "projects"

# File extension used by the Save/Open dialogs
FILE_FILTER = "Frostad Structural Lab Project (*.fsl);;All Files (*)"
FILE_SUFFIX = ".fsl"


def default_projects_dir() -> Path:
    """Return (and if necessary create) the shared projects directory."""
    _DEFAULT_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_PROJECTS_DIR


def save_project(doc: StructuralDocument, path: str | Path) -> None:
    """
    Serialise *doc* to a JSON project file at *path*.

    The parent directory is created automatically if it does not exist.
    """
    path = Path(path)
    if path.suffix != FILE_SUFFIX:
        path = path.with_suffix(FILE_SUFFIX)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc.to_dict(), fh, indent=2)


def load_project(path: str | Path) -> StructuralDocument:
    """
    Deserialise a JSON project file and return a fresh StructuralDocument.

    Raises:
        FileNotFoundError: if the path does not exist.
        ValueError: if the file cannot be parsed as a valid project.
    """
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not a valid project file: {path}\n{exc}") from exc
    return StructuralDocument.from_dict(data)
