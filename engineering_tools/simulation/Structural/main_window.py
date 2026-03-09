"""
GUI/main_window.py

MainWindow — top-level QMainWindow.

Layout:
  QToolBar (top)
  ┌─────────────┬────────────────────────┬──────────────────┐
  │ ModelTree   │      Viewport3D        │  PropertyPanel   │
  │  (250 px)   │      (stretch)         │   (280 px)       │
  └─────────────┴────────────────────────┴──────────────────┘
  QStatusBar (bottom)

All inter-panel signal connections are wired here so that individual
panels remain unaware of each other.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .document import DocumentController
from .model_tree import ModelTreePanel
from .property_panel import PropertyPanel
from .toolbar import ModelingToolbar
from .viewport_3d import Viewport3D


class _PdfExportDialog(QDialog):
    """
    Small dialog that lets the user choose which sections to include
    in the exported PDF report.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("PDF Report — Select Sections")
        self.setMinimumWidth(340)

        from .pdf_export import REPORT_SECTIONS
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Include in report:"))

        self._checks: dict[str, QCheckBox] = {}
        for key, label, default in REPORT_SECTIONS:
            chk = QCheckBox(label)
            chk.setChecked(default)
            lay.addWidget(chk)
            self._checks[key] = chk

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def selected_sections(self) -> dict:
        return {key: chk.isChecked() for key, chk in self._checks.items()}


class MainWindow(QMainWindow):
    """
    Main application window.

    Owns one DocumentController and instantiates all GUI panels.
    Wires all cross-panel signals in _connect().
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Frostad Structural Lab")
        self.resize(1400, 860)

        # ── Central controller (document + undo + solve) ───────────────────
        self._ctrl = DocumentController(self)

        # ── Build panels ──────────────────────────────────────────────────
        self._toolbar  = ModelingToolbar(self)
        self._tree     = ModelTreePanel(self._ctrl)
        self._viewport = Viewport3D(self._ctrl)
        self._panel    = PropertyPanel(self._ctrl)
        self._status   = QStatusBar()

        self._build_layout()
        self._connect()
        self._apply_style()

        # Initial tree population
        self._tree.rebuild()

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_layout(self):
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)
        self.setStatusBar(self._status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._tree)
        splitter.addWidget(self._viewport)
        splitter.addWidget(self._panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([240, 900, 280])

        self.setCentralWidget(splitter)

    # -----------------------------------------------------------------------
    # Signal wiring
    # -----------------------------------------------------------------------

    def _connect(self):
        ctrl     = self._ctrl
        toolbar  = self._toolbar
        tree     = self._tree
        viewport = self._viewport
        panel    = self._panel

        # ── Toolbar → viewport / controller ─────────────────────────────
        toolbar.mode_changed.connect(viewport.set_interaction_mode)
        toolbar.mode_changed.connect(self._on_mode_changed)
        toolbar.solve_requested.connect(ctrl.run_solve)
        toolbar.diagram_changed.connect(viewport.set_active_diagram)
        toolbar.deformed_toggled.connect(viewport.set_show_deformed)
        toolbar.grid_resolution_changed.connect(viewport.set_grid_resolution)
        toolbar.undo_requested.connect(ctrl.undo)
        toolbar.redo_requested.connect(ctrl.redo)
        toolbar.open_requested.connect(self._on_open_project)
        toolbar.save_requested.connect(self._on_save_project)
        toolbar.export_pdf_requested.connect(self._on_export_pdf)
        toolbar.array_tool_requested.connect(self._on_array_tool)
        viewport.line_placement_requested.connect(self._on_line_placement)

        # ── Controller → toolbar ─────────────────────────────────────────
        ctrl.solve_complete.connect(toolbar.on_solve_complete)
        ctrl.undo_state_changed.connect(toolbar.update_undo_buttons)
        ctrl.status_message.connect(self._status.showMessage)

        # ── Viewport → controller / tree / panel ─────────────────────────
        viewport.entity_picked.connect(ctrl.set_selection)
        viewport.entity_picked.connect(
            lambda t, i: tree.highlight_entity(t, i)
        )
        viewport.node_placement_requested.connect(ctrl.add_node)
        viewport.member_placement_requested.connect(ctrl.add_member)
        viewport.support_placement_requested.connect(
            self._on_support_placement
        )
        viewport.load_placement_requested.connect(
            self._on_load_placement
        )
        viewport.status_message.connect(self._status.showMessage)

        # ── Tree → controller ────────────────────────────────────────────
        tree.item_selected.connect(ctrl.set_selection)
        tree.delete_requested.connect(ctrl.remove_entity)

        # ── Solve complete → viewport / panel ────────────────────────────
        ctrl.solve_complete.connect(viewport.show_results)

    # -----------------------------------------------------------------------
    # Interaction helpers
    # -----------------------------------------------------------------------

    def _on_mode_changed(self, mode: str):
        mode_labels = {
            "select":      "Mode: Select",
            "add_node":    "Mode: Add Node — click in viewport to place",
            "add_member":  "Mode: Add Member — click first node, then second",
            "add_support": "Mode: Add Support — click a node",
            "add_load":    "Mode: Add Load — click a node or member",
            "add_line":    "Mode: Line Tool — click start point, then end point",
        }
        self._status.showMessage(mode_labels.get(mode, f"Mode: {mode}"))

    def _on_line_placement(self, x1, y1, z1, x2, y2, z2):
        from PySide6.QtWidgets import QDialog
        from .placement_tools import LineSubdivideDialog
        dialog = LineSubdivideDialog(x1, y1, z1, x2, y2, z2, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            n, connect = dialog.result_values()
            self._ctrl.add_nodes_line(x1, y1, z1, x2, y2, z2, n, connect)
            self._tree.rebuild()

    def _on_array_tool(self):
        from PySide6.QtWidgets import QDialog
        from .placement_tools import ArrayDialog
        ghost = getattr(self._viewport, "_ghost_pos", None) or (0.0, 0.0, 0.0)
        dialog = ArrayDialog(*ghost, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        params = dialog.result_params()
        mode = dialog.mode
        if mode == "rectangular":
            self._ctrl.add_nodes_rect_array(**params)
        else:
            self._ctrl.add_nodes_circular_array(**params)
        self._tree.rebuild()

    def _on_support_placement(self, node_id: str):
        """
        When the viewport fires support_placement_requested, open the support
        page in the property panel so the user can choose the type.
        """
        doc = self._ctrl.document
        nd  = doc.nodes.get(node_id)
        if nd is None:
            return
        # Check if a support already exists
        existing = next(
            (sp for sp in doc.supports.values() if sp.node_id == node_id),
            None,
        )
        # Navigate property panel to support form
        self._ctrl.set_selection("node", node_id)
        # Trigger the "Assign Support" shortcut button logic in panel
        panel = self._panel
        panel._on_add_support_clicked()

    def _on_load_placement(self, target_id: str, target_type: str):
        """
        When the viewport fires load_placement_requested, open the load page.
        """
        if target_type == "node":
            self._ctrl.set_selection("node", target_id)
            self._panel._on_add_node_load_clicked()
        else:
            self._ctrl.set_selection("member", target_id)
            self._panel._on_add_member_load_clicked()

    # -----------------------------------------------------------------------
    # Project save / load
    # -----------------------------------------------------------------------

    def _on_save_project(self):
        from PySide6.QtWidgets import QFileDialog
        from .project_io import save_project, default_projects_dir, FILE_FILTER, FILE_SUFFIX
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project",
            str(default_projects_dir() / "untitled.fsl"),
            FILE_FILTER,
        )
        if not path:
            return
        try:
            save_project(self._ctrl.document, path)
            self._status.showMessage(f"Project saved: {path}", 4000)
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", str(exc))

    def _on_open_project(self):
        from PySide6.QtWidgets import QFileDialog
        from .project_io import load_project, default_projects_dir, FILE_FILTER
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project",
            str(default_projects_dir()),
            FILE_FILTER,
        )
        if not path:
            return
        try:
            doc = load_project(path)
            self._ctrl.load_document(doc)
            self._tree.rebuild()
            self._status.showMessage(f"Project loaded: {path}", 4000)
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Open Error", str(exc))

    # -----------------------------------------------------------------------
    # PDF export
    # -----------------------------------------------------------------------

    def _on_export_pdf(self):
        from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox
        results = self._ctrl.results
        if results is None:
            QMessageBox.warning(self, "Not Solved",
                                "Solve the model before exporting a PDF report.")
            return

        from .pdf_export import check_available, REPORT_SECTIONS
        ok, msg = check_available()
        if not ok:
            QMessageBox.critical(self, "PDF Export Unavailable", msg)
            return

        # Section selection dialog
        dialog = _PdfExportDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        sections = dialog.selected_sections()

        from .project_io import default_projects_dir
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF Report",
            str(default_projects_dir() / "report.pdf"),
            "PDF Document (*.pdf);;All Files (*)",
        )
        if not path:
            return

        try:
            from .pdf_export import export_pdf
            export_pdf(results, path, sections=sections)
            self._status.showMessage(f"PDF exported: {path}", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "PDF Export Error", str(exc))

    # -----------------------------------------------------------------------
    # Style
    # -----------------------------------------------------------------------

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: "Segoe UI", "Inter", sans-serif;
                font-size: 11px;
            }
            QToolBar {
                background: #181825;
                border-bottom: 1px solid #313244;
                spacing: 4px;
                padding: 2px;
            }
            QToolBar QToolButton {
                color: #cdd6f4;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QToolBar QToolButton:checked {
                background: #45475a;
                color: #f9e2af;
            }
            QToolBar QToolButton:hover {
                background: #313244;
            }
            QTreeWidget {
                background: #181825;
                border: none;
                alternate-background-color: #1e1e2e;
            }
            QTreeWidget::item:selected {
                background: #45475a;
                color: #f9e2af;
            }
            QScrollArea, QStackedWidget {
                background: transparent;
                border: none;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 4px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover   { background: #45475a; }
            QPushButton:pressed { background: #585b70; }
            QComboBox {
                background: #313244;
                border: 1px solid #45475a;
                border-radius: 3px;
                padding: 2px 6px;
                color: #cdd6f4;
            }
            QDoubleSpinBox, QSpinBox, QLineEdit {
                background: #313244;
                border: 1px solid #45475a;
                border-radius: 3px;
                padding: 2px 4px;
                color: #cdd6f4;
            }
            QStatusBar {
                background: #181825;
                color: #a6adc8;
                border-top: 1px solid #313244;
            }
            QSplitter::handle {
                background: #313244;
                width: 2px;
            }
            QHeaderView::section {
                background: #181825;
                color: #a6adc8;
                border: none;
                padding: 4px;
            }
            QTableWidget {
                background: #181825;
                gridline-color: #313244;
            }
        """)
