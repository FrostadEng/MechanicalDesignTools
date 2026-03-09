"""
GUI/document.py

Structural document model and controller.

StructuralDocument is the GUI source of truth — a plain-Python, Qt-free
data container.  DocumentController owns the document, the undo stack, and
the solved ResultsCache; it exposes mutating commands and drives a fresh
FrameAnalysis on every solve.
"""

from __future__ import annotations

import dataclasses
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import uuid

from PySide6.QtCore import QObject, Signal

from mech_core.analysis.fea import FrameAnalysis
from mech_core.analysis.statics import from_dimensions
from mech_core.components.members.aisc import get_section
from mech_core.standards.materials import get_material
from mech_core.standards.units import ureg
from .undo_stack import UndoStack


# ---------------------------------------------------------------------------
# Document data classes — all numeric values stored as raw SI floats
# ---------------------------------------------------------------------------

@dataclass
class NodeData:
    id: str
    x: float          # metres
    y: float          # metres
    z: float          # metres
    label: str = ""   # user-visible label (defaults to id)

    def __post_init__(self):
        if not self.label:
            self.label = self.id


@dataclass
class MemberData:
    id: str
    start_node: str
    end_node: str
    section_name: str          = "W12X26"
    material_name: str         = "ASTM A992"
    rotation: float            = 0.0            # degrees
    custom_section: Optional[dict] = None       # {"shape": str, "params": {str: float}}


@dataclass
class SupportData:
    id: str
    node_id: str
    support_type: str = "fixed"   # "fixed" | "pinned" | "roller"
    # Custom DOF restraints (True = restrained).  Only used when
    # support_type == "custom".
    dx: bool = True
    dy: bool = True
    dz: bool = True
    rx: bool = False
    ry: bool = False
    rz: bool = False


@dataclass
class NodeLoadData:
    id: str
    node_id: str
    Fx: float = 0.0    # kN
    Fy: float = 0.0    # kN
    Fz: float = 0.0    # kN
    Mx: float = 0.0    # kN·m
    My: float = 0.0    # kN·m
    Mz: float = 0.0    # kN·m
    case: str = "Case 1"


@dataclass
class MemberLoadData:
    id: str
    member_id: str
    direction: str = "Fy"   # "Fx" | "Fy" | "Fz"
    w1: float = 0.0          # kN/m at start
    w2: float = 0.0          # kN/m at end
    x1: float = 0.0          # m from start
    x2: Optional[float] = None  # None → full length
    case: str = "Case 1"


@dataclass
class StructuralDocument:
    """Complete structural model document — serialisable, Qt-free."""
    nodes:        Dict[str, NodeData]       = field(default_factory=dict)
    members:      Dict[str, MemberData]     = field(default_factory=dict)
    supports:     Dict[str, SupportData]    = field(default_factory=dict)
    node_loads:   Dict[str, NodeLoadData]   = field(default_factory=dict)
    member_loads: Dict[str, MemberLoadData] = field(default_factory=dict)
    load_cases:   List[str]                 = field(default_factory=lambda: ["Case 1"])
    _node_seq:    int                       = field(default=0, repr=False)
    _member_seq:  int                       = field(default=0, repr=False)
    _support_seq: int                       = field(default=0, repr=False)
    _load_seq:    int                       = field(default=0, repr=False)

    # ---- ID generators -------------------------------------------------------

    def _next_node_id(self) -> str:
        self._node_seq += 1
        return f"N{self._node_seq}"

    def _next_member_id(self) -> str:
        self._member_seq += 1
        return f"M{self._member_seq}"

    def _next_support_id(self) -> str:
        self._support_seq += 1
        return f"S{self._support_seq}"

    def _next_load_id(self) -> str:
        self._load_seq += 1
        return f"L{self._load_seq}"

    # ---- Serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StructuralDocument":
        doc = cls()
        doc._node_seq    = d.get("_node_seq", 0)
        doc._member_seq  = d.get("_member_seq", 0)
        doc._support_seq = d.get("_support_seq", 0)
        doc._load_seq    = d.get("_load_seq", 0)
        doc.load_cases   = d.get("load_cases", ["Case 1"])
        doc.nodes        = {k: NodeData(**v)       for k, v in d.get("nodes", {}).items()}
        doc.members      = {k: MemberData(**v)     for k, v in d.get("members", {}).items()}
        doc.supports     = {k: SupportData(**v)    for k, v in d.get("supports", {}).items()}
        doc.node_loads   = {k: NodeLoadData(**v)   for k, v in d.get("node_loads", {}).items()}
        doc.member_loads = {k: MemberLoadData(**v) for k, v in d.get("member_loads", {}).items()}
        return doc


# ---------------------------------------------------------------------------
# DocumentController
# ---------------------------------------------------------------------------

class DocumentController(QObject):
    """
    Owns the StructuralDocument and all mutation commands.

    Every public mutating method:
      1. Pushes an undo snapshot before the change.
      2. Applies the change to the document.
      3. Invalidates any cached solve results.
      4. Emits model_changed.
    """

    # Signals
    model_changed    = Signal()                        # document content changed
    selection_changed = Signal(str, str)               # (entity_type, entity_id)
    solve_complete   = Signal(object)                  # ResultsCache | None
    status_message   = Signal(str)
    undo_state_changed = Signal(bool, bool)            # (can_undo, can_redo)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._doc   = StructuralDocument()
        self._undo  = UndoStack()
        self._results = None          # ResultsCache | None
        self._selected_type: Optional[str] = None
        self._selected_id:   Optional[str] = None

    # ---- Read-only access ---------------------------------------------------

    @property
    def document(self) -> StructuralDocument:
        return self._doc

    @property
    def results(self):
        """Current ResultsCache or None."""
        return self._results

    @property
    def selected_type(self) -> Optional[str]:
        return self._selected_type

    @property
    def selected_id(self) -> Optional[str]:
        return self._selected_id

    # ---- Selection ----------------------------------------------------------

    def set_selection(self, entity_type: Optional[str], entity_id: Optional[str]):
        self._selected_type = entity_type
        self._selected_id   = entity_id
        self.selection_changed.emit(entity_type or "", entity_id or "")

    # ---- Node commands ------------------------------------------------------

    def add_node(self, x: float, y: float, z: float,
                 node_id: Optional[str] = None) -> str:
        self._push_undo()
        if node_id is None:
            node_id = self._doc._next_node_id()
        self._doc.nodes[node_id] = NodeData(id=node_id, x=x, y=y, z=z)
        self._invalidate_results()
        self.model_changed.emit()
        return node_id

    def move_node(self, node_id: str, x: float, y: float, z: float):
        if node_id not in self._doc.nodes:
            return
        self._push_undo()
        nd = self._doc.nodes[node_id]
        nd.x, nd.y, nd.z = x, y, z
        self._invalidate_results()
        self.model_changed.emit()

    def update_node(self, node_id: str, **kwargs):
        """Update arbitrary NodeData fields."""
        if node_id not in self._doc.nodes:
            return
        self._push_undo()
        nd = self._doc.nodes[node_id]
        for k, v in kwargs.items():
            setattr(nd, k, v)
        self._invalidate_results()
        self.model_changed.emit()

    def remove_node(self, node_id: str):
        if node_id not in self._doc.nodes:
            return
        self._push_undo()
        # Cascade-delete connected members
        connected = [mid for mid, mb in self._doc.members.items()
                     if mb.start_node == node_id or mb.end_node == node_id]
        for mid in connected:
            self._remove_member_internal(mid)
        # Remove support
        sup_ids = [sid for sid, sp in self._doc.supports.items()
                   if sp.node_id == node_id]
        for sid in sup_ids:
            del self._doc.supports[sid]
        # Remove node loads
        nl_ids = [lid for lid, nl in self._doc.node_loads.items()
                  if nl.node_id == node_id]
        for lid in nl_ids:
            del self._doc.node_loads[lid]
        del self._doc.nodes[node_id]
        self._invalidate_results()
        self.model_changed.emit()

    # ---- Member commands ----------------------------------------------------

    def add_member(self, start_node: str, end_node: str,
                   member_id: Optional[str] = None) -> str:
        self._push_undo()
        if member_id is None:
            member_id = self._doc._next_member_id()
        self._doc.members[member_id] = MemberData(
            id=member_id, start_node=start_node, end_node=end_node
        )
        self._invalidate_results()
        self.model_changed.emit()
        return member_id

    def update_member(self, member_id: str, **kwargs):
        if member_id not in self._doc.members:
            return
        self._push_undo()
        mb = self._doc.members[member_id]
        for k, v in kwargs.items():
            setattr(mb, k, v)
        self._invalidate_results()
        self.model_changed.emit()

    def remove_member(self, member_id: str):
        if member_id not in self._doc.members:
            return
        self._push_undo()
        self._remove_member_internal(member_id)
        self._invalidate_results()
        self.model_changed.emit()

    def _remove_member_internal(self, member_id: str):
        self._doc.members.pop(member_id, None)
        ml_ids = [lid for lid, ml in self._doc.member_loads.items()
                  if ml.member_id == member_id]
        for lid in ml_ids:
            del self._doc.member_loads[lid]

    # ---- Support commands ---------------------------------------------------

    def set_support(self, node_id: str, support_type: str = "fixed",
                    **dof_kwargs) -> str:
        """Add or replace the support at node_id."""
        self._push_undo()
        # Remove existing support at this node
        existing = [sid for sid, sp in self._doc.supports.items()
                    if sp.node_id == node_id]
        for sid in existing:
            del self._doc.supports[sid]
        sup_id = self._doc._next_support_id()
        self._doc.supports[sup_id] = SupportData(
            id=sup_id, node_id=node_id, support_type=support_type,
            **dof_kwargs
        )
        self._invalidate_results()
        self.model_changed.emit()
        return sup_id

    def remove_support(self, support_id: str):
        self._doc.supports.pop(support_id, None)
        self._push_undo()
        self._invalidate_results()
        self.model_changed.emit()

    def remove_support_at_node(self, node_id: str):
        self._push_undo()
        ids = [sid for sid, sp in self._doc.supports.items()
               if sp.node_id == node_id]
        for sid in ids:
            del self._doc.supports[sid]
        self._invalidate_results()
        self.model_changed.emit()

    # ---- Load commands ------------------------------------------------------

    def add_node_load(self, node_id: str, **kwargs) -> str:
        self._push_undo()
        lid = self._doc._next_load_id()
        self._doc.node_loads[lid] = NodeLoadData(id=lid, node_id=node_id, **kwargs)
        self._invalidate_results()
        self.model_changed.emit()
        return lid

    def update_node_load(self, load_id: str, **kwargs):
        if load_id not in self._doc.node_loads:
            return
        self._push_undo()
        nl = self._doc.node_loads[load_id]
        for k, v in kwargs.items():
            setattr(nl, k, v)
        self._invalidate_results()
        self.model_changed.emit()

    def remove_node_load(self, load_id: str):
        self._doc.node_loads.pop(load_id, None)
        self._push_undo()
        self._invalidate_results()
        self.model_changed.emit()

    def add_member_load(self, member_id: str, **kwargs) -> str:
        self._push_undo()
        lid = self._doc._next_load_id()
        self._doc.member_loads[lid] = MemberLoadData(
            id=lid, member_id=member_id, **kwargs
        )
        self._invalidate_results()
        self.model_changed.emit()
        return lid

    def update_member_load(self, load_id: str, **kwargs):
        if load_id not in self._doc.member_loads:
            return
        self._push_undo()
        ml = self._doc.member_loads[load_id]
        for k, v in kwargs.items():
            setattr(ml, k, v)
        self._invalidate_results()
        self.model_changed.emit()

    def remove_member_load(self, load_id: str):
        self._doc.member_loads.pop(load_id, None)
        self._push_undo()
        self._invalidate_results()
        self.model_changed.emit()

    # ---- Remove any entity by (type, id) ------------------------------------

    def remove_entity(self, entity_type: str, entity_id: str):
        dispatch = {
            "node":        self.remove_node,
            "member":      self.remove_member,
            "support":     self.remove_support,
            "node_load":   self.remove_node_load,
            "member_load": self.remove_member_load,
        }
        fn = dispatch.get(entity_type)
        if fn:
            fn(entity_id)

    # ---- Project load -------------------------------------------------------

    def load_document(self, doc: "StructuralDocument") -> None:
        """
        Replace the current document with *doc* (e.g. after opening a project).

        Clears the undo / redo stack (the loaded state becomes the new baseline)
        and resets any cached solve results.
        """
        self._doc = doc
        self._undo.clear()
        self._results = None
        self._selected_type = None
        self._selected_id   = None
        self.selection_changed.emit("", "")
        self._emit_undo_state()
        self._invalidate_results()
        self.model_changed.emit()

    # ---- Undo / Redo --------------------------------------------------------

    def undo(self):
        doc = self._undo.undo(self._doc)
        if doc is not None:
            self._doc = doc
            self._invalidate_results()
            self.model_changed.emit()
        self._emit_undo_state()

    def redo(self):
        doc = self._undo.redo(self._doc)
        if doc is not None:
            self._doc = doc
            self._invalidate_results()
            self.model_changed.emit()
        self._emit_undo_state()

    def _push_undo(self):
        self._undo.push(self._doc)
        self._emit_undo_state()

    def _emit_undo_state(self):
        self.undo_state_changed.emit(self._undo.can_undo, self._undo.can_redo)

    # ---- Solve --------------------------------------------------------------

    def run_solve(self):
        """Build a fresh FrameAnalysis from the document and solve it."""
        from .results import ResultsCache

        doc = self._doc
        if not doc.nodes:
            self.status_message.emit("Cannot solve: no nodes defined.")
            self.solve_complete.emit(None)
            return
        if not doc.members:
            self.status_message.emit("Cannot solve: no members defined.")
            self.solve_complete.emit(None)
            return
        if not doc.supports:
            self.status_message.emit("Cannot solve: no supports defined.")
            self.solve_complete.emit(None)
            return

        try:
            fea = FrameAnalysis()

            # Nodes
            for nd in doc.nodes.values():
                # GUI uses Z-up; PyNite uses Y-up. Swap y↔z.
                fea.add_node(nd.id, nd.x, nd.z, nd.y)

            # Members
            for mb in doc.members.values():
                if mb.custom_section:
                    section = from_dimensions(
                        mb.custom_section["shape"],
                        mb.custom_section["params"],
                    )
                else:
                    section = get_section(mb.section_name)
                material = get_material(mb.material_name)
                fea.add_beam(mb.id, mb.start_node, mb.end_node,
                             section, material, mb.rotation)

            # Supports
            for sp in doc.supports.values():
                if sp.support_type in ("fixed", "pinned", "roller"):
                    fea.add_support(sp.node_id, sp.support_type)
                else:
                    fea.model.def_support(sp.node_id,
                                          sp.dx, sp.dy, sp.dz,
                                          sp.rx, sp.ry, sp.rz)

            # Node loads
            for nl in doc.node_loads.values():
                fea.add_node_load(
                    nl.node_id,
                    Fx=nl.Fx * ureg.kN if nl.Fx else None,
                    Fy=nl.Fz * ureg.kN if nl.Fz else None,   # our Fz (vertical) → PyNite Fy
                    Fz=nl.Fy * ureg.kN if nl.Fy else None,   # our Fy (depth) → PyNite Fz
                    Mx=(nl.Mx * ureg.kN * ureg.meter) if nl.Mx else None,
                    My=(nl.Mz * ureg.kN * ureg.meter) if nl.Mz else None,   # swap
                    Mz=(nl.My * ureg.kN * ureg.meter) if nl.My else None,   # swap
                    case=nl.case,
                )

            # Member distributed loads
            for ml in doc.member_loads.values():
                _dir_map = {"Fx": "Fx", "Fy": "Fz", "Fz": "Fy"}
                fea.add_member_dist_load(
                    ml.member_id, _dir_map.get(ml.direction, ml.direction),
                    ml.w1 * ureg.kN / ureg.meter,
                    ml.w2 * ureg.kN / ureg.meter,
                    case=ml.case,
                )

            fea.solve()

            # Build results cache
            cache = ResultsCache.from_fea(fea, doc)
            self._results = cache
            self.status_message.emit("Solve complete.")
            self.solve_complete.emit(cache)

        except Exception as exc:
            self.status_message.emit(f"Solve error: {exc}")
            self.solve_complete.emit(None)
            self._results = None

    # ---- Pattern placement --------------------------------------------------

    def add_nodes_line(
        self,
        x1: float, y1: float, z1: float,
        x2: float, y2: float, z2: float,
        n_between: int,
        connect: bool = True,
    ) -> List[str]:
        """
        Create n_between+2 nodes evenly spaced on the segment [P1, P2].

        If connect=True, successive nodes are joined by members using the
        current default section / material.
        """
        self._push_undo()
        doc = self._doc
        total = n_between + 2

        ids: List[str] = []
        for i in range(total):
            t  = i / (total - 1) if total > 1 else 0.0
            x  = x1 + t * (x2 - x1)
            y  = y1 + t * (y2 - y1)
            z  = z1 + t * (z2 - z1)
            nid = doc._next_node_id()
            doc.nodes[nid] = NodeData(id=nid, x=x, y=y, z=z)
            ids.append(nid)

        if connect and len(ids) >= 2:
            for j in range(len(ids) - 1):
                mid = doc._next_member_id()
                doc.members[mid] = MemberData(
                    id=mid, start_node=ids[j], end_node=ids[j + 1]
                )

        self._invalidate_results()
        self.model_changed.emit()
        return ids

    def add_nodes_rect_array(
        self,
        base_x: float, base_y: float, base_z: float,
        dx: float, dy: float, dz: float,
        cols: int, rows: int, levels: int,
        connect_x: bool = True,
        connect_y: bool = True,
        connect_z: bool = False,
    ) -> List[str]:
        """
        Create a rows × cols × levels grid of nodes starting at (base_x, base_y, base_z).
        """
        self._push_undo()
        doc = self._doc
        grid: dict = {}

        for iz in range(levels):
            for iy in range(rows):
                for ix in range(cols):
                    nid = doc._next_node_id()
                    doc.nodes[nid] = NodeData(
                        id=nid,
                        x=base_x + ix * dx,
                        y=base_y + iy * dy,
                        z=base_z + iz * dz,
                    )
                    grid[(ix, iy, iz)] = nid

        def _add_member(a, b):
            mid = doc._next_member_id()
            doc.members[mid] = MemberData(id=mid, start_node=a, end_node=b)

        if connect_x:
            for iz in range(levels):
                for iy in range(rows):
                    for ix in range(cols - 1):
                        _add_member(grid[(ix, iy, iz)], grid[(ix + 1, iy, iz)])
        if connect_y:
            for iz in range(levels):
                for iy in range(rows - 1):
                    for ix in range(cols):
                        _add_member(grid[(ix, iy, iz)], grid[(ix, iy + 1, iz)])
        if connect_z:
            for iz in range(levels - 1):
                for iy in range(rows):
                    for ix in range(cols):
                        _add_member(grid[(ix, iy, iz)], grid[(ix, iy, iz + 1)])

        self._invalidate_results()
        self.model_changed.emit()
        return list(grid.values())

    def add_nodes_circular_array(
        self,
        center_x: float, center_y: float, center_z: float,
        radius: float, n: int,
        start_angle: float = 0.0,
        arc_angle: float = 360.0,
        dz_step: float = 0.0,
        connect: bool = True,
        close_loop: bool = True,
    ) -> List[str]:
        """
        Create n nodes arranged in a circular (or arc/helical) pattern.
        """
        import math as _math
        self._push_undo()
        doc = self._doc
        ids: List[str] = []

        # If arc_angle == 360 and close_loop, place n nodes at equal spacing
        # and connect last back to first.  Otherwise n nodes at equal spacing
        # across the arc.
        full_circle = abs(arc_angle) >= 359.9
        step = arc_angle / (n if full_circle else (n - 1))

        for i in range(n):
            angle_deg = start_angle + i * step
            angle_rad = _math.radians(angle_deg)
            x = center_x + radius * _math.cos(angle_rad)
            y = center_y + radius * _math.sin(angle_rad)
            z = center_z + i * dz_step
            nid = doc._next_node_id()
            doc.nodes[nid] = NodeData(id=nid, x=x, y=y, z=z)
            ids.append(nid)

        if connect and len(ids) >= 2:
            for j in range(len(ids) - 1):
                mid = doc._next_member_id()
                doc.members[mid] = MemberData(
                    id=mid, start_node=ids[j], end_node=ids[j + 1]
                )
            if full_circle and close_loop:
                mid = doc._next_member_id()
                doc.members[mid] = MemberData(
                    id=mid, start_node=ids[-1], end_node=ids[0]
                )

        self._invalidate_results()
        self.model_changed.emit()
        return ids

    # ---- Internal -----------------------------------------------------------

    def _invalidate_results(self):
        if self._results is not None:
            self._results = None
            self.solve_complete.emit(None)
