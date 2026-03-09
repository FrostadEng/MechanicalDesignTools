"""
GUI/model_tree.py

ModelTreePanel — hierarchical model browser backed by a QTreeWidget.

Tree layout:
  📐 Model
    🔵 Nodes (N)
      N1  [0.0, 0.0, 0.0]
      ...
    📏 Members (M)
      M1  N1→N2 | W12X26 | A992
      ...
    🔩 Supports (S)
      S1  N1 | fixed
      ...
    ⬇ Loads (L)
      L1  N2 | Fy -10 kN
      ...
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .document import DocumentController


class ModelTreePanel(QWidget):
    """
    Left-side panel: collapsible tree of all model entities.

    Signals
    -------
    item_selected(entity_type: str, entity_id: str)
    delete_requested(entity_type: str, entity_id: str)
    """

    item_selected    = Signal(str, str)    # (entity_type, entity_id)
    delete_requested = Signal(str, str)    # (entity_type, entity_id)

    # Column indices
    _COL_LABEL = 0
    _COL_INFO  = 1

    def __init__(self, controller: DocumentController,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._ctrl = controller
        self._building = False   # guard against recursive selection signals
        self._setup_ui()
        self._connect()

    # ---- UI -----------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Entity", "Properties"])
        self._tree.header().setStretchLastSection(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.setAlternatingRowColors(True)
        self._tree.setMinimumWidth(220)

        layout.addWidget(self._tree)

        # Root group items (persistent — we clear their children on rebuild)
        self._root_nodes    = self._make_group("🔵 Nodes",    "nodes")
        self._root_members  = self._make_group("📏 Members",  "members")
        self._root_supports = self._make_group("🔩 Supports", "supports")
        self._root_loads    = self._make_group("⬇ Loads",    "loads")

        self._tree.invisibleRootItem().addChildren([
            self._root_nodes,
            self._root_members,
            self._root_supports,
            self._root_loads,
        ])
        self._tree.expandAll()
        self._tree.setColumnWidth(0, 110)

    def _make_group(self, label: str, data: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label, ""])
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        item.setData(0, Qt.ItemDataRole.UserRole, ("group", data))
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        return item

    # ---- Signals ------------------------------------------------------------

    def _connect(self):
        self._ctrl.model_changed.connect(self.rebuild)
        self._ctrl.selection_changed.connect(self._on_external_selection)
        self._tree.itemSelectionChanged.connect(self._on_tree_selection)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)

    # ---- Build / Rebuild ----------------------------------------------------

    def rebuild(self):
        """Repopulate the tree from the current document."""
        self._building = True
        doc = self._ctrl.document

        self._repopulate_group(
            self._root_nodes,
            [(nd.id, nd.id, f"[{nd.x:.2f}, {nd.y:.2f}, {nd.z:.2f}] m")
             for nd in doc.nodes.values()],
            "node",
        )
        self._repopulate_group(
            self._root_members,
            [(mb.id, mb.id,
              f"{mb.start_node}→{mb.end_node} | {mb.section_name} | {mb.material_name}")
             for mb in doc.members.values()],
            "member",
        )
        self._repopulate_group(
            self._root_supports,
            [(sp.id, sp.id, f"{sp.node_id} | {sp.support_type}")
             for sp in doc.supports.values()],
            "support",
        )

        # Loads — combine node and member loads
        load_rows = []
        for nl in doc.node_loads.values():
            parts = []
            for comp in ("Fx", "Fy", "Fz", "Mx", "My", "Mz"):
                v = getattr(nl, comp, 0.0)
                if abs(v) > 1e-12:
                    parts.append(f"{comp}={v:.1f}")
            info = f"{nl.node_id} | {', '.join(parts) or 'zero'} [{nl.case}]"
            load_rows.append((nl.id, nl.id, info))
        for ml in doc.member_loads.values():
            info = (f"{ml.member_id} | {ml.direction} "
                    f"w={ml.w1:.1f}→{ml.w2:.1f} kN/m [{ml.case}]")
            load_rows.append((ml.id, ml.id, info))
        self._repopulate_group(self._root_loads, load_rows, "load")

        # Update group count labels
        self._root_nodes.setText(0,    f"🔵 Nodes ({len(doc.nodes)})")
        self._root_members.setText(0,  f"📏 Members ({len(doc.members)})")
        self._root_supports.setText(0, f"🔩 Supports ({len(doc.supports)})")
        n_loads = len(doc.node_loads) + len(doc.member_loads)
        self._root_loads.setText(0,    f"⬇ Loads ({n_loads})")

        self._building = False

    def _repopulate_group(
        self,
        group: QTreeWidgetItem,
        rows: list,           # list of (entity_id, label_text, info_text)
        entity_type: str,
    ):
        """Replace all children of *group* with *rows*."""
        while group.childCount() > 0:
            group.removeChild(group.child(0))
        for entity_id, label, info in rows:
            item = QTreeWidgetItem([label, info])
            item.setData(0, Qt.ItemDataRole.UserRole, (entity_type, entity_id))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            group.addChild(item)

    # ---- Selection sync ------------------------------------------------------

    def _on_tree_selection(self):
        if self._building:
            return
        items = self._tree.selectedItems()
        if not items:
            self._ctrl.set_selection(None, None)
            return
        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] != "group":
            entity_type, entity_id = data
            self._ctrl.set_selection(entity_type, entity_id)
            self.item_selected.emit(entity_type, entity_id)

    def _on_external_selection(self, entity_type: str, entity_id: str):
        """Highlight the corresponding tree item when selection changes externally."""
        if self._building:
            return
        self._building = True
        self._tree.clearSelection()
        if entity_type and entity_id:
            item = self._find_item(entity_type, entity_id)
            if item:
                item.setSelected(True)
                self._tree.scrollToItem(item)
        self._building = False

    def _find_item(self, entity_type: str, entity_id: str) -> Optional[QTreeWidgetItem]:
        """Search tree for an item matching (entity_type, entity_id)."""
        def _search(parent: QTreeWidgetItem):
            for i in range(parent.childCount()):
                child = parent.child(i)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data == (entity_type, entity_id):
                    return child
            return None

        for group in (self._root_nodes, self._root_members,
                      self._root_supports, self._root_loads):
            found = _search(group)
            if found:
                return found
        return None

    # ---- Context menu -------------------------------------------------------

    def _on_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] == "group":
            return
        entity_type, entity_id = data

        menu = QMenu(self)
        act_select = menu.addAction(f"Select {entity_type.capitalize()}")
        act_delete = menu.addAction(f"Delete {entity_type.capitalize()}")

        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
        if chosen == act_select:
            self._ctrl.set_selection(entity_type, entity_id)
        elif chosen == act_delete:
            self.delete_requested.emit(entity_type, entity_id)

    # ---- Public highlight API -----------------------------------------------

    def highlight_entity(self, entity_type: str, entity_id: str):
        """Highlight tree item from an external source (e.g. viewport pick)."""
        self._on_external_selection(entity_type, entity_id)
