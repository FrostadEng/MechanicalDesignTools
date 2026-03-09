"""
GUI/undo_stack.py

Snapshot-based undo / redo stack for StructuralDocument.

Deep-copies the document's dict representation before every mutation so
that undo simply restores a previous state.  Avoids the Command pattern
and keeps DocumentController simple.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .document import StructuralDocument


class UndoStack:
    """
    Snapshot undo stack.

    Usage:
        stack.push(doc)         # save current state before mutation
        ...                     # apply mutation
        doc = stack.undo(doc)   # restore; returns restored doc (or None)
        doc = stack.redo(doc)   # redo; returns restored doc (or None)
    """

    MAX_DEPTH = 60

    def __init__(self):
        self._past:   list[dict] = []   # snapshots before current state
        self._future: list[dict] = []   # snapshots after current state (for redo)

    # ---- Public API ---------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        return len(self._past) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._future) > 0

    def push(self, document: "StructuralDocument"):
        """Save a snapshot of *document* before a mutation is applied."""
        snapshot = document.to_dict()
        self._past.append(snapshot)
        if len(self._past) > self.MAX_DEPTH:
            self._past.pop(0)
        # Any new action invalidates the redo stack
        self._future.clear()

    def undo(self, current: "StructuralDocument") -> Optional["StructuralDocument"]:
        """
        Restore the previous state.

        Saves *current* to the redo stack and returns the restored
        StructuralDocument, or None if the stack is empty.
        """
        if not self._past:
            return None
        from .document import StructuralDocument
        self._future.append(current.to_dict())
        snapshot = self._past.pop()
        return StructuralDocument.from_dict(snapshot)

    def redo(self, current: "StructuralDocument") -> Optional["StructuralDocument"]:
        """
        Restore the next state.

        Saves *current* to the undo stack and returns the restored
        StructuralDocument, or None if the redo stack is empty.
        """
        if not self._future:
            return None
        from .document import StructuralDocument
        self._past.append(current.to_dict())
        snapshot = self._future.pop()
        return StructuralDocument.from_dict(snapshot)

    def clear(self):
        self._past.clear()
        self._future.clear()
