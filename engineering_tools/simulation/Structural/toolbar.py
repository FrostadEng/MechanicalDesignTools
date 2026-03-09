"""
GUI/toolbar.py

ModelingToolbar — main toolbar for the structural modeling GUI.

Layout (left → right):
  [Select] [Add Node] [Add Member] [Add Support] [Add Load]  |
  [Solve]  |
  [Deformed ☐] [Diagram ▾]  |
  [Grid: 0.25 m ▾]  |
  [Undo] [Redo]
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QToolBar,
    QWidget,
)


class InteractionMode(str, Enum):
    SELECT      = "select"
    ADD_NODE    = "add_node"
    ADD_MEMBER  = "add_member"
    ADD_SUPPORT = "add_support"
    ADD_LOAD    = "add_load"
    ADD_LINE    = "add_line"


_DIAGRAM_OPTIONS = [
    ("None",            None),
    ("Shear Vy",        "shear_y"),
    ("Shear Vz",        "shear_z"),
    ("Moment Mz (strong)", "moment_z"),
    ("Moment My (weak)",   "moment_y"),
    ("Axial",           "axial"),
    ("Torsion",         "torsion"),
]


class ModelingToolbar(QToolBar):
    """
    Main modeling toolbar.

    Signals
    -------
    mode_changed(mode: str)
    solve_requested()
    diagram_changed(diagram_key: str | None)
    deformed_toggled(show: bool)
    grid_resolution_changed(metres: float)
    undo_requested()
    redo_requested()
    open_requested()
    save_requested()
    export_pdf_requested()
    """

    mode_changed            = Signal(str)
    solve_requested         = Signal()
    diagram_changed         = Signal(object)   # str | None
    deformed_toggled        = Signal(bool)
    grid_resolution_changed = Signal(float)
    undo_requested          = Signal()
    redo_requested          = Signal()
    open_requested          = Signal()
    save_requested          = Signal()
    export_pdf_requested    = Signal()
    array_tool_requested    = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Modeling", parent)
        self.setMovable(False)
        self._build()

    # ---- Construction -------------------------------------------------------

    def _build(self):
        # -- File operations --------------------------------------------------
        self._act_open = QAction("📂 Open", self)
        self._act_open.setToolTip("Open project  [Ctrl+O]")
        self._act_open.setShortcut(QKeySequence("Ctrl+O"))
        self._act_open.triggered.connect(self.open_requested)
        self.addAction(self._act_open)

        self._act_save = QAction("💾 Save", self)
        self._act_save.setToolTip("Save project  [Ctrl+S]")
        self._act_save.setShortcut(QKeySequence("Ctrl+S"))
        self._act_save.triggered.connect(self.save_requested)
        self.addAction(self._act_save)

        self.addSeparator()

        # -- Mode group -------------------------------------------------------
        group = QActionGroup(self)
        group.setExclusive(True)

        self._act_select = self._mode_action(
            group, "Select", InteractionMode.SELECT,
            shortcut="Escape", tooltip="Select / inspect entities  [Esc]",
            checked=True,
        )
        self._act_node = self._mode_action(
            group, "Add Node", InteractionMode.ADD_NODE,
            shortcut="N", tooltip="Click viewport to place a node  [N]",
        )
        self._act_member = self._mode_action(
            group, "Add Member", InteractionMode.ADD_MEMBER,
            shortcut="M", tooltip="Click two nodes to create a member  [M]",
        )
        self._act_support = self._mode_action(
            group, "Add Support", InteractionMode.ADD_SUPPORT,
            shortcut="S", tooltip="Click a node to assign a support  [S]",
        )
        self._act_load = self._mode_action(
            group, "Add Load", InteractionMode.ADD_LOAD,
            shortcut="L", tooltip="Click a node or member to add a load  [L]",
        )
        self._act_line = self._mode_action(
            group, "Line Tool", InteractionMode.ADD_LINE,
            shortcut="G", tooltip="Click two points to create a line of nodes  [G]",
        )

        self.addSeparator()

        # -- Solve ------------------------------------------------------------
        self._act_solve = QAction("⚡ Solve", self)
        self._act_solve.setToolTip("Run FEA analysis  [F5]")
        self._act_solve.setShortcut(QKeySequence("F5"))
        self._act_solve.triggered.connect(self.solve_requested)
        self.addAction(self._act_solve)

        self.addSeparator()

        # -- Results display controls -----------------------------------------
        self._act_deformed = QAction("Deformed", self)
        self._act_deformed.setCheckable(True)
        self._act_deformed.setEnabled(False)
        self._act_deformed.setToolTip("Show deformed shape overlay")
        self._act_deformed.toggled.connect(self.deformed_toggled)
        self.addAction(self._act_deformed)

        self.addWidget(QLabel("  Diagram:"))
        self._cb_diagram = QComboBox()
        self._cb_diagram.setFixedWidth(160)
        self._cb_diagram.setEnabled(False)
        for label, _ in _DIAGRAM_OPTIONS:
            self._cb_diagram.addItem(label)
        self._cb_diagram.currentIndexChanged.connect(self._on_diagram_changed)
        self.addWidget(self._cb_diagram)

        self.addSeparator()

        # -- Grid resolution --------------------------------------------------
        self.addWidget(QLabel("  Grid:"))
        self._spin_grid = QDoubleSpinBox()
        self._spin_grid.setRange(0.05, 5.0)
        self._spin_grid.setSingleStep(0.25)
        self._spin_grid.setValue(0.5)
        self._spin_grid.setSuffix(" m")
        self._spin_grid.setFixedWidth(80)
        self._spin_grid.setToolTip("Grid snapping resolution")
        self._spin_grid.valueChanged.connect(self.grid_resolution_changed)
        self.addWidget(self._spin_grid)

        self.addSeparator()

        # -- Undo / Redo ------------------------------------------------------
        self._act_undo = QAction("↩ Undo", self)
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.setEnabled(False)
        self._act_undo.triggered.connect(self.undo_requested)
        self.addAction(self._act_undo)

        self._act_redo = QAction("↪ Redo", self)
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.setEnabled(False)
        self._act_redo.triggered.connect(self.redo_requested)
        self.addAction(self._act_redo)

        self.addSeparator()

        # -- Export PDF -------------------------------------------------------
        self._act_export_pdf = QAction("📄 Export PDF", self)
        self._act_export_pdf.setToolTip("Export solved model to PDF report  [Ctrl+P]")
        self._act_export_pdf.setShortcut(QKeySequence("Ctrl+P"))
        self._act_export_pdf.setEnabled(False)   # enabled after solve
        self._act_export_pdf.triggered.connect(self.export_pdf_requested)
        self.addAction(self._act_export_pdf)

        self.addSeparator()

        # -- Array tool -------------------------------------------------------
        self._act_array = QAction("⊞ Array", self)
        self._act_array.setToolTip("Place a rectangular or circular array of nodes  [Ctrl+Shift+A]")
        self._act_array.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self._act_array.triggered.connect(self.array_tool_requested)
        self.addAction(self._act_array)

    def _mode_action(
        self,
        group: QActionGroup,
        text: str,
        mode: InteractionMode,
        shortcut: str = "",
        tooltip:  str = "",
        checked:  bool = False,
    ) -> QAction:
        act = QAction(text, self)
        act.setCheckable(True)
        act.setChecked(checked)
        act.setActionGroup(group)
        act.setData(mode.value)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        if tooltip:
            act.setToolTip(tooltip)
        act.triggered.connect(lambda checked, m=mode: self.mode_changed.emit(m.value))
        self.addAction(act)
        return act

    # ---- Slots --------------------------------------------------------------

    def _on_diagram_changed(self, index: int):
        _, key = _DIAGRAM_OPTIONS[index]
        self.diagram_changed.emit(key)

    def on_solve_complete(self, results_cache):
        """Called by MainWindow when a solve finishes."""
        solved = results_cache is not None
        self._act_deformed.setEnabled(solved)
        self._cb_diagram.setEnabled(solved)
        self._act_export_pdf.setEnabled(solved)
        if not solved:
            self._act_deformed.setChecked(False)
            self._cb_diagram.setCurrentIndex(0)

    def update_undo_buttons(self, can_undo: bool, can_redo: bool):
        self._act_undo.setEnabled(can_undo)
        self._act_redo.setEnabled(can_redo)

    # ---- Properties ---------------------------------------------------------

    @property
    def current_mode(self) -> str:
        return InteractionMode.SELECT.value

    @property
    def grid_resolution(self) -> float:
        return self._spin_grid.value()
