"""
GUI/viewport_3d.py

Viewport3D — interactive 3D structural model viewer built on pyvistaqt.

Rendering layers:
  1. Ground grid
  2. Members (tubes)
  3. Nodes (spheres)
  4. Supports (glyphs)
  5. Loads (arrows)
  6. Labels
  7. Deformed shape overlay  (post-solve)
  8. Internal force diagram  (post-solve)

Interaction:
  - Left drag  → orbit (default PyVista trackball)
  - Right drag → pan
  - Scroll     → zoom
  - Left click (not drag) → place / pick according to current mode

Picking strategy:
  Observe LeftButtonPress + LeftButtonRelease to distinguish click from drag.
  On click, project onto Y = 0 world plane; search nearby nodes in screen
  space for object picking without VTK actor-name fragility.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pyvista as pv

try:
    from pyvistaqt import QtInteractor
except ImportError as exc:
    raise ImportError(
        "pyvistaqt is required for the GUI viewport.\n"
        "Install it with:  pip install pyvistaqt"
    ) from exc

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .document import DocumentController

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_C_BACKGROUND  = "#1e1e2e"
_C_GRID        = "#6c7086"
_C_NODE        = "#cdd6f4"
_C_NODE_SEL    = "#f9e2af"
_C_NODE_PEND   = "#fab387"
_C_NODE_SUPP   = "#a6e3a1"
_C_MEMBER      = "#89b4fa"
_C_MEMBER_SEL  = "#f9e2af"
_C_SUPPORT     = "#a6e3a1"
_C_LOAD_FORCE  = "#f38ba8"
_C_LOAD_MOMENT = "#cba6f7"
_C_DEFORMED    = "#f38ba8"
_C_DIAGRAM     = "#a6e3a1"

_NODE_RADIUS   = 0.06   # metres
_TUBE_RADIUS   = 0.018  # metres


class Viewport3D(QWidget):
    """
    Interactive 3D viewport for structural model editing and visualization.

    Signals
    -------
    entity_picked(entity_type: str, entity_id: str)
    node_placement_requested(x, y, z)
    member_placement_requested(start_id, end_id)
    support_placement_requested(node_id)
    load_placement_requested(target_id, target_type)
    status_message(str)
    """

    entity_picked               = Signal(str, str)
    node_placement_requested    = Signal(float, float, float)
    member_placement_requested  = Signal(str, str)
    support_placement_requested = Signal(str)
    load_placement_requested    = Signal(str, str)
    status_message              = Signal(str)
    line_placement_requested    = Signal(float, float, float, float, float, float)

    def __init__(self, controller: DocumentController,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._ctrl          = controller
        self._mode          = "select"
        self._grid_res      = 0.5          # m
        self._pending_start: Optional[str] = None
        self._show_deformed = False
        self._deform_scale  = 100.0
        self._active_diagram: Optional[str] = None
        self._results       = None

        # Advanced placement state
        self._ghost_pos:   Optional[Tuple[float, float, float]] = None
        self._last_placed: Optional[Tuple[float, float, float]] = None
        self._line_start:  Optional[Tuple[float, float, float]] = None
        self._shift_held:  bool = False

        # Track press position to distinguish click from drag
        self._press_pos: Optional[Tuple[int, int]] = None

        self._setup_ui()
        self._setup_plotter()
        self._connect()

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Controls bar ────────────────────────────────────────────────────
        bar = QWidget()
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(4, 2, 4, 2)
        bar_lay.setSpacing(6)

        self._chk_labels = QCheckBox("Labels")
        self._chk_labels.setChecked(True)
        self._chk_labels.toggled.connect(self.refresh)

        self._chk_loads = QCheckBox("Loads")
        self._chk_loads.setChecked(True)
        self._chk_loads.toggled.connect(self.refresh)

        bar_lay.addWidget(self._chk_labels)
        bar_lay.addWidget(self._chk_loads)

        bar_lay.addWidget(QLabel("  Deform ×"))
        self._spin_scale = QDoubleSpinBox()
        self._spin_scale.setRange(1, 100000)
        self._spin_scale.setValue(100)
        self._spin_scale.setSingleStep(10)
        self._spin_scale.setFixedWidth(80)
        self._spin_scale.valueChanged.connect(self._on_scale_changed)
        bar_lay.addWidget(self._spin_scale)

        btn_fit = QPushButton("Fit View")
        btn_fit.setFixedWidth(70)
        btn_fit.clicked.connect(self._fit_view)
        bar_lay.addWidget(btn_fit)

        btn_ss = QPushButton("📷")
        btn_ss.setFixedWidth(32)
        btn_ss.setToolTip("Save screenshot")
        btn_ss.clicked.connect(self._screenshot)
        bar_lay.addWidget(btn_ss)

        bar_lay.addWidget(QLabel("  View:"))
        for label, slot in [
            ("Top",   self._view_top),
            ("Front", self._view_front),
            ("Right", self._view_right),
            ("Iso",   self._view_iso),
        ]:
            btn = QPushButton(label)
            btn.setFixedWidth(48)
            btn.clicked.connect(slot)
            bar_lay.addWidget(btn)

        # ── Coordinate display ───────────────────────────────────────────────
        bar_lay.addWidget(QLabel("  Pos:"))
        self._lbl_coords = QLabel("—")
        self._lbl_coords.setStyleSheet(
            "font-family: monospace; color: #a6adc8; min-width: 210px;"
        )
        bar_lay.addWidget(self._lbl_coords)

        # ── Snap / Ortho toggles ─────────────────────────────────────────────
        self._chk_snap = QCheckBox("Snap")
        self._chk_snap.setChecked(True)
        bar_lay.addWidget(self._chk_snap)

        self._chk_ortho = QCheckBox("Ortho")
        self._chk_ortho.setChecked(False)
        bar_lay.addWidget(self._chk_ortho)

        # ── Coordinate input button (visible only in add_node mode) ──────────
        self._btn_place_coords = QPushButton("[x,y,z]")
        self._btn_place_coords.setToolTip("Type exact coordinates to place a node  [Space]")
        self._btn_place_coords.setFixedWidth(60)
        self._btn_place_coords.setVisible(False)
        self._btn_place_coords.clicked.connect(self._prompt_place_coords)
        bar_lay.addWidget(self._btn_place_coords)

        bar_lay.addStretch()
        root.addWidget(bar)

        # ── PyVista plotter frame ────────────────────────────────────────────
        self._frame = QWidget()
        frame_lay = QVBoxLayout(self._frame)
        frame_lay.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._frame, 1)

        # ── Arrow-key nudge shortcuts ────────────────────────────────────────
        for _key, _delta in [
            (Qt.Key.Key_Left,     (-1,  0,  0)),
            (Qt.Key.Key_Right,    (+1,  0,  0)),
            (Qt.Key.Key_Up,       ( 0, +1,  0)),
            (Qt.Key.Key_Down,     ( 0, -1,  0)),
            (Qt.Key.Key_PageUp,   ( 0,  0, +1)),
            (Qt.Key.Key_PageDown, ( 0,  0, -1)),
        ]:
            _sc = QShortcut(QKeySequence(_key), self)
            _sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            _sc.activated.connect(lambda d=_delta: self._nudge_selected(*d))

        # Space → coordinate input
        _sc_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        _sc_space.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        _sc_space.activated.connect(self._prompt_place_coords)

    def _setup_plotter(self):
        pv.set_plot_theme("dark")
        self.plotter = QtInteractor(self._frame, auto_update=False)
        self._frame.layout().addWidget(self.plotter)

        self.plotter.set_background(_C_BACKGROUND)
        self.plotter.enable_anti_aliasing()
        self.plotter.add_axes(
            xlabel='X', ylabel='Y', zlabel='Z',
            x_color='#f38ba8', y_color='#a6e3a1', z_color='#89b4fa',
            line_width=3,
        )

        self._draw_grid()

        # Camera starting position: isometric view (Z-up)
        self.plotter.camera_position = [
            (12, -12, 10), (0, 0, 0), (0, 0, 1)
        ]

        # Hook Qt mouse events on the plotter widget to detect click vs drag.
        # Using an eventFilter (rather than VTK observers) is more reliable
        # across pyvistaqt versions and correctly handles the Qt↔VTK Y-axis flip.
        self.plotter.installEventFilter(self)

    def _connect(self):
        self._ctrl.model_changed.connect(self.refresh)
        self._ctrl.selection_changed.connect(self._on_selection_changed)
        self._ctrl.solve_complete.connect(self._on_solve_complete)

    # -----------------------------------------------------------------------
    # Grid
    # -----------------------------------------------------------------------

    def _draw_grid(self, half=10.0, step=0.5):
        """Draw a reference grid on the XZ plane (Y = 0) with origin axes."""
        lines_pts: List[Tuple] = []
        cells = []
        idx = 0
        for i in np.arange(-half, half + step * 0.5, step):
            for a, b in [
                ((i, -half, 0), (i, half, 0)),
                ((-half, i, 0), (half, i, 0)),
            ]:
                lines_pts.extend([a, b])
                cells.extend([2, idx, idx + 1])
                idx += 2

        if not lines_pts:
            return

        mesh = pv.PolyData()
        mesh.points = np.array(lines_pts, dtype=float)
        mesh.lines  = np.array(cells,     dtype=int)

        self.plotter.add_mesh(
            mesh, color=_C_GRID, opacity=0.55,
            name="_grid", line_width=1, pickable=False
        )

        # ── Origin axes ─────────────────────────────────────────────────────
        # X axis — red/salmon
        x_axis = pv.PolyData(np.array([(0, 0, 0), (half, 0, 0)], dtype=float))
        x_axis.lines = np.array([2, 0, 1])
        self.plotter.add_mesh(
            x_axis, color="#f38ba8", opacity=0.8,
            name="_axis_x", line_width=2, pickable=False
        )
        self.plotter.add_point_labels(
            np.array([[half * 0.92, 0, 0]]), ["+X"],
            name="_axis_x_lbl", font_size=9, text_color="#f38ba8",
            point_size=0, shape=None, always_visible=True
        )

        # Y axis — green
        y_axis = pv.PolyData(np.array([(0, 0, 0), (0, half, 0)], dtype=float))
        y_axis.lines = np.array([2, 0, 1])
        self.plotter.add_mesh(
            y_axis, color="#a6e3a1", opacity=0.8,
            name="_axis_y", line_width=2, pickable=False
        )
        self.plotter.add_point_labels(
            np.array([[0, half * 0.92, 0]]), ["+Y"],
            name="_axis_y_lbl", font_size=9, text_color="#a6e3a1",
            point_size=0, shape=None, always_visible=True
        )

        # Z stub — up arrow (blue)
        z_arrow = pv.Arrow(
            start=(0, 0, 0), direction=(0, 0, 1), scale=1.5
        )
        self.plotter.add_mesh(
            z_arrow, color="#89b4fa", opacity=0.8,
            name="_axis_z_arrow", pickable=False
        )
        self.plotter.add_point_labels(
            np.array([[0, 0, 1.8]]), ["+Z"],
            name="_axis_z_lbl", font_size=9, text_color="#89b4fa",
            point_size=0, shape=None, always_visible=True
        )

        # Origin dot
        origin_sphere = pv.Sphere(radius=0.05, center=(0, 0, 0))
        self.plotter.add_mesh(
            origin_sphere, color="#f9e2af", opacity=0.9,
            name="_origin", pickable=False, smooth_shading=True
        )

    # -----------------------------------------------------------------------
    # Interaction modes (called from toolbar)
    # -----------------------------------------------------------------------

    def set_interaction_mode(self, mode: str):
        self._mode          = mode
        self._pending_start = None
        self._line_start    = None
        # Show/hide coordinate entry button
        self._btn_place_coords.setVisible(mode == "add_node")
        # Remove ghost actors when leaving placement modes
        if mode not in ("add_node", "add_line"):
            self.plotter.remove_actor("_ghost_node",       reset_camera=False)
            self.plotter.remove_actor("_ghost_line",       reset_camera=False)
            self.plotter.remove_actor("_ghost_line_start", reset_camera=False)
            self.plotter.update()
        self.refresh()

    def set_grid_resolution(self, metres: float):
        self._grid_res = max(0.01, metres)

    def set_show_deformed(self, show: bool):
        self._show_deformed = show
        self.refresh()

    def set_active_diagram(self, diagram_key: Optional[str]):
        self._active_diagram = diagram_key
        self.refresh()

    # -----------------------------------------------------------------------
    # Qt event filter — click vs drag detection
    # -----------------------------------------------------------------------

    def eventFilter(self, obj, event: QEvent) -> bool:
        """
        Installed on self.plotter (the QtInteractor widget).
        Records press position; on release, fires _handle_click if the mouse
        barely moved (< 6 px).  Returns False so VTK still receives every
        event and orbit/pan/zoom continue to work normally.
        """
        if obj is self.plotter:
            t = event.type()
            if t == QEvent.Type.MouseMove:
                pos = event.position().toPoint()
                h = self.plotter.height()
                vtk_x = pos.x()
                vtk_y = h - pos.y() - 1
                mods = event.modifiers()
                self._shift_held = bool(mods & Qt.KeyboardModifier.ShiftModifier)
                self._on_mouse_move(vtk_x, vtk_y)

            elif t == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    pos = event.position().toPoint()
                    self._press_pos = (pos.x(), pos.y())

            elif t == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
                    pos = event.position().toPoint()
                    rx_qt, ry_qt = pos.x(), pos.y()
                    px, py = self._press_pos
                    self._press_pos = None

                    if math.hypot(rx_qt - px, ry_qt - py) < 6:
                        # Convert Qt coords (y=0 top) → VTK display (y=0 bottom)
                        h = self.plotter.height()
                        vtk_x = rx_qt
                        vtk_y = h - ry_qt - 1
                        self._handle_click(vtk_x, vtk_y)

        return False  # always pass the event through to VTK

    # -----------------------------------------------------------------------
    # Click dispatch
    # -----------------------------------------------------------------------

    def _handle_click(self, vtk_x: int, vtk_y: int):
        """Route a confirmed click to the appropriate mode handler."""
        nearest_node   = self._pick_nearest_node_screen(vtk_x, vtk_y)
        nearest_member = (
            None if nearest_node else
            self._pick_nearest_member_screen(vtk_x, vtk_y)
        )
        world = self._screen_to_world(vtk_x, vtk_y)

        mode = self._mode

        if mode == "select":
            if nearest_node:
                self._ctrl.set_selection("node", nearest_node)
                self.entity_picked.emit("node", nearest_node)
            elif nearest_member:
                self._ctrl.set_selection("member", nearest_member)
                self.entity_picked.emit("member", nearest_member)
            else:
                self._ctrl.set_selection(None, None)

        elif mode == "add_node":
            if nearest_node:
                self._ctrl.set_selection("node", nearest_node)
            else:
                pos = self._ghost_pos or self._snap(world[0], world[1], world[2])
                self._last_placed = pos
                self.node_placement_requested.emit(pos[0], pos[1], pos[2])

        elif mode == "add_line":
            if self._line_start is None:
                # Lock start point
                if nearest_node:
                    nd = self._ctrl.document.nodes[nearest_node]
                    self._line_start = (nd.x, nd.y, nd.z)
                else:
                    pos = self._ghost_pos or self._snap(world[0], world[1], world[2])
                    self._line_start = pos
                self.status_message.emit(
                    f"Line Tool: start locked at "
                    f"({self._line_start[0]:.3f}, {self._line_start[1]:.3f}, {self._line_start[2]:.3f})"
                    f"  — click end point"
                )
                self.refresh()
            else:
                # Emit with end point
                start = self._line_start
                self._line_start = None
                if nearest_node:
                    nd = self._ctrl.document.nodes[nearest_node]
                    end = (nd.x, nd.y, nd.z)
                else:
                    end = self._ghost_pos or self._snap(world[0], world[1], world[2])
                self.line_placement_requested.emit(
                    start[0], start[1], start[2],
                    end[0],   end[1],   end[2],
                )
                self.refresh()

        elif mode == "add_member":
            if nearest_node:
                if self._pending_start is None:
                    self._pending_start = nearest_node
                    self.status_message.emit(
                        f"Member: click end node  (start locked: {nearest_node})"
                    )
                    self.refresh()
                elif nearest_node != self._pending_start:
                    start = self._pending_start
                    self._pending_start = None
                    self.member_placement_requested.emit(start, nearest_node)
            else:
                self.status_message.emit("Add Member: click on an existing node.")

        elif mode == "add_support":
            if nearest_node:
                self._ctrl.set_selection("node", nearest_node)
                self.support_placement_requested.emit(nearest_node)
            else:
                self.status_message.emit("Add Support: click on an existing node.")

        elif mode == "add_load":
            if nearest_node:
                self._ctrl.set_selection("node", nearest_node)
                self.load_placement_requested.emit(nearest_node, "node")
            elif nearest_member:
                self._ctrl.set_selection("member", nearest_member)
                self.load_placement_requested.emit(nearest_member, "member")
            else:
                self.status_message.emit(
                    "Add Load: click on a node or member."
                )

    # -----------------------------------------------------------------------
    # Screen-space picking helpers
    # -----------------------------------------------------------------------

    def _world_to_screen(self, wx, wy, wz) -> Optional[Tuple[float, float]]:
        """Convert world coords → VTK display (bottom-left origin) coords."""
        try:
            renderer = self.plotter.renderer
            renderer.SetWorldPoint(wx, wy, wz, 1.0)
            renderer.WorldToDisplay()
            dx, dy, _ = renderer.GetDisplayPoint()
            return dx, dy
        except Exception:
            return None

    def _screen_to_world(self, vtk_x: int, vtk_y: int) -> Tuple[float, float, float]:
        """
        Project a VTK display point onto the Y = 0 plane using camera ray.
        Returns (x, 0, z) in world space.
        """
        try:
            renderer = self.plotter.renderer

            def display_to_world(z_ndc: float):
                renderer.SetDisplayPoint(vtk_x, vtk_y, z_ndc)
                renderer.DisplayToWorld()
                p = list(renderer.GetWorldPoint())
                w = p[3]
                if abs(w) > 1e-12:
                    return [c / w for c in p[:3]]
                return p[:3]

            near = display_to_world(0.0)
            far  = display_to_world(1.0)

            dz = far[2] - near[2]
            if abs(dz) < 1e-10:
                return near[0], near[1], 0.0
            t = (0.0 - near[2]) / dz
            x = near[0] + t * (far[0] - near[0])
            y = near[1] + t * (far[1] - near[1])
            return float(x), float(y), 0.0
        except Exception:
            return 0.0, 0.0, 0.0

    def _pick_nearest_node_screen(self, vtk_x: int, vtk_y: int,
                                  threshold_px: float = 22.0) -> Optional[str]:
        """Return ID of the node closest to the screen point, or None."""
        best: Optional[str] = None
        best_dist = threshold_px
        for nd in self._ctrl.document.nodes.values():
            sp = self._world_to_screen(nd.x, nd.y, nd.z)
            if sp is None:
                continue
            d = math.hypot(vtk_x - sp[0], vtk_y - sp[1])
            if d < best_dist:
                best_dist = d
                best = nd.id
        return best

    def _pick_nearest_member_screen(self, vtk_x: int, vtk_y: int,
                                    threshold_px: float = 14.0) -> Optional[str]:
        """Return ID of the member closest to the screen point, or None."""
        doc   = self._ctrl.document
        best: Optional[str] = None
        best_dist = threshold_px
        for mb in doc.members.values():
            n1 = doc.nodes.get(mb.start_node)
            n2 = doc.nodes.get(mb.end_node)
            if n1 is None or n2 is None:
                continue
            p1 = self._world_to_screen(n1.x, n1.y, n1.z)
            p2 = self._world_to_screen(n2.x, n2.y, n2.z)
            if p1 is None or p2 is None:
                continue
            d = self._point_to_seg_2d(
                (vtk_x, vtk_y), p1, p2
            )
            if d < best_dist:
                best_dist = d
                best = mb.id
        return best

    @staticmethod
    def _point_to_seg_2d(pt, a, b) -> float:
        """2-D distance from point *pt* to segment *a*–*b*."""
        px, py = pt
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        if dx == dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        cx, cy = ax + t * dx, ay + t * dy
        return math.hypot(px - cx, py - cy)

    def _snap(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """Snap to grid."""
        s = self._grid_res
        return (
            round(x / s) * s,
            round(y / s) * s,
            round(z / s) * s,
        )

    def _compute_snap_world(
        self, x: float, y: float, z: float,
        vtk_x: int, vtk_y: int,
    ) -> Tuple[float, float, float]:
        """
        Compute the snapped position for a given world point.

        Priority order:
          1. Exact snap to nearby existing node (screen-space proximity).
          2. Snap to member midpoints (screen-space proximity).
          3. Free placement (Shift held).
          4. Grid snap (default, if Snap checkbox is on).
          5. Ortho constraint from last placed node (if Ortho checkbox is on).
        """
        # 1 — nearby node
        nearest = self._pick_nearest_node_screen(vtk_x, vtk_y, threshold_px=20.0)
        if nearest:
            nd = self._ctrl.document.nodes[nearest]
            return (nd.x, nd.y, nd.z)

        # 2 — member midpoints / quarter-points
        geo = self._pick_nearest_geo_point(vtk_x, vtk_y)
        if geo:
            return geo

        # 3 — shift overrides grid snap
        if self._shift_held:
            sx, sy, sz = x, y, z
        elif self._chk_snap.isChecked():
            sx, sy, sz = self._snap(x, y, z)
        else:
            sx, sy, sz = x, y, z

        # 4 — ortho constraint
        if self._chk_ortho.isChecked() and self._last_placed:
            sx, sy, sz = self._apply_ortho(sx, sy, sz)

        return (sx, sy, sz)

    def _pick_nearest_geo_point(
        self, vtk_x: int, vtk_y: int,
        threshold_px: float = 16.0,
    ) -> Optional[Tuple[float, float, float]]:
        """Snap to member midpoints (t=0.25, 0.5, 0.75) in screen space."""
        doc = self._ctrl.document
        best_dist = threshold_px
        best_pt: Optional[Tuple[float, float, float]] = None
        for mb in doc.members.values():
            n1 = doc.nodes.get(mb.start_node)
            n2 = doc.nodes.get(mb.end_node)
            if n1 is None or n2 is None:
                continue
            for t in (0.25, 0.5, 0.75):
                mx = n1.x + t * (n2.x - n1.x)
                my = n1.y + t * (n2.y - n1.y)
                mz = n1.z + t * (n2.z - n1.z)
                sp = self._world_to_screen(mx, my, mz)
                if sp is None:
                    continue
                d = math.hypot(vtk_x - sp[0], vtk_y - sp[1])
                if d < best_dist:
                    best_dist = d
                    best_pt = (mx, my, mz)
        return best_pt

    def _apply_ortho(
        self, x: float, y: float, z: float,
    ) -> Tuple[float, float, float]:
        """Constrain position to the nearest axis from the last placed node."""
        if not self._last_placed:
            return x, y, z
        ox, oy, oz = self._last_placed
        dx, dy, dz = abs(x - ox), abs(y - oy), abs(z - oz)
        if dx >= dy and dx >= dz:
            return x, oy, oz
        elif dy >= dx and dy >= dz:
            return ox, y, oz
        else:
            return ox, oy, z

    def _on_mouse_move(self, vtk_x: int, vtk_y: int):
        """Handle mouse movement: update coordinate display and ghost node."""
        world = self._screen_to_world(vtk_x, vtk_y)
        snapped = self._compute_snap_world(world[0], world[1], world[2], vtk_x, vtk_y)
        self._ghost_pos = snapped
        sx, sy, sz = snapped
        self._lbl_coords.setText(f"X:{sx:8.3f}  Y:{sy:8.3f}  Z:{sz:8.3f}")

        if self._mode == "add_node":
            sphere = pv.Sphere(radius=_NODE_RADIUS * 1.1, center=(sx, sy, sz))
            self.plotter.add_mesh(
                sphere, color=_C_NODE_PEND, opacity=0.45,
                name="_ghost_node", smooth_shading=True, pickable=False,
            )
            self.plotter.update()

        elif self._mode == "add_line":
            sphere = pv.Sphere(radius=_NODE_RADIUS * 1.1, center=(sx, sy, sz))
            self.plotter.add_mesh(
                sphere, color=_C_NODE_PEND, opacity=0.45,
                name="_ghost_node", smooth_shading=True, pickable=False,
            )
            if self._line_start:
                s = pv.Sphere(
                    radius=_NODE_RADIUS * 1.2, center=self._line_start
                )
                self.plotter.add_mesh(
                    s, color="#f9e2af", opacity=0.9,
                    name="_ghost_line_start", smooth_shading=True, pickable=False,
                )
                ln = pv.Line(
                    np.array(self._line_start, dtype=float),
                    np.array((sx, sy, sz), dtype=float),
                )
                tube = ln.tube(radius=_TUBE_RADIUS * 0.6, n_sides=6)
                self.plotter.add_mesh(
                    tube, color="#fab387", opacity=0.55,
                    name="_ghost_line", pickable=False,
                )
            self.plotter.update()

        else:
            # Not in a placement mode — remove any lingering ghost actors
            for name in ("_ghost_node", "_ghost_line", "_ghost_line_start"):
                if name in self.plotter.actors:
                    self.plotter.remove_actor(name, reset_camera=False)

    def _nudge_selected(self, dx: float, dy: float, dz: float):
        """Move the selected node by one grid step."""
        if self._ctrl.selected_type != "node":
            return
        nd_id = self._ctrl.selected_id
        nd = self._ctrl.document.nodes.get(nd_id)
        if nd is None:
            return
        step = self._grid_res
        self._ctrl.move_node(
            nd_id,
            nd.x + dx * step,
            nd.y + dy * step,
            nd.z + dz * step,
        )

    def _prompt_place_coords(self):
        """Open a dialog to place a node at typed absolute or relative coordinates."""
        if self._mode != "add_node":
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Place Node at Coordinates")
        lay = QFormLayout(dialog)

        gx, gy, gz = self._ghost_pos or (0.0, 0.0, 0.0)

        def _spin(val):
            s = QDoubleSpinBox()
            s.setRange(-10_000.0, 10_000.0)
            s.setDecimals(3)
            s.setSingleStep(self._grid_res)
            s.setValue(val)
            s.setSuffix(" m")
            return s

        spin_x = _spin(gx)
        spin_y = _spin(gy)
        spin_z = _spin(gz)

        lay.addRow("X:", spin_x)
        lay.addRow("Y:", spin_y)
        lay.addRow("Z:", spin_z)

        if self._last_placed:
            lx, ly, lz = self._last_placed
            lay.addRow(
                QLabel(
                    f"<i>Last node: ({lx:.3f}, {ly:.3f}, {lz:.3f})</i>"
                )
            )

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        lay.addRow(btns)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            x, y, z = spin_x.value(), spin_y.value(), spin_z.value()
            self._last_placed = (x, y, z)
            self.node_placement_requested.emit(x, y, z)

    # -----------------------------------------------------------------------
    # Model rendering
    # -----------------------------------------------------------------------

    def refresh(self):
        """Clear all model actors and redraw everything from document."""
        # Remove old model actors (not the grid)
        for name in list(self.plotter.actors.keys()):
            if not name.startswith("_grid"):
                self.plotter.remove_actor(name, reset_camera=False)

        doc = self._ctrl.document
        sel_type = self._ctrl.selected_type
        sel_id   = self._ctrl.selected_id

        self._render_members(doc, sel_type, sel_id)
        self._render_nodes(doc, sel_type, sel_id)
        self._render_supports(doc)
        if self._chk_loads.isChecked():
            self._render_loads(doc)
        if self._chk_labels.isChecked():
            self._render_labels(doc)

        if self._results is not None:
            if self._show_deformed:
                self._render_deformed(doc)
            if self._active_diagram:
                self._render_diagram(doc)

        # Ghost actors are rendered dynamically via mouse-move; remove stale ones
        # when a full refresh occurs (they will be re-added on next mouse move)
        for _gname in ("_ghost_node", "_ghost_line", "_ghost_line_start"):
            if _gname in self.plotter.actors:
                self.plotter.remove_actor(_gname, reset_camera=False)

        self.plotter.update()

    def _render_members(self, doc, sel_type, sel_id):
        for mb in doc.members.values():
            n1 = doc.nodes.get(mb.start_node)
            n2 = doc.nodes.get(mb.end_node)
            if n1 is None or n2 is None:
                continue
            p1 = np.array([n1.x, n1.y, n1.z])
            p2 = np.array([n2.x, n2.y, n2.z])
            if np.allclose(p1, p2):
                continue

            line = pv.Line(p1, p2)
            tube = line.tube(radius=_TUBE_RADIUS, n_sides=8)
            color = (_C_MEMBER_SEL if sel_type == "member" and sel_id == mb.id
                     else _C_MEMBER)
            self.plotter.add_mesh(
                tube, color=color, name=f"mb_{mb.id}",
                smooth_shading=True, pickable=False
            )

    def _render_nodes(self, doc, sel_type, sel_id):
        for nd in doc.nodes.values():
            sphere = pv.Sphere(radius=_NODE_RADIUS, center=(nd.x, nd.y, nd.z))
            if sel_type == "node" and sel_id == nd.id:
                color = _C_NODE_SEL
            elif nd.id == self._pending_start:
                color = _C_NODE_PEND
            elif any(sp.node_id == nd.id for sp in doc.supports.values()):
                color = _C_NODE_SUPP
            else:
                color = _C_NODE
            self.plotter.add_mesh(
                sphere, color=color, name=f"nd_{nd.id}",
                smooth_shading=True, pickable=False
            )

    def _render_supports(self, doc):
        for sp in doc.supports.values():
            nd = doc.nodes.get(sp.node_id)
            if nd is None:
                continue
            pos = np.array([nd.x, nd.y, nd.z])

            if sp.support_type == "fixed":
                # Solid box below the node
                box = pv.Box(bounds=(
                    pos[0] - 0.12, pos[0] + 0.12,
                    pos[1] - 0.12, pos[1] + 0.12,
                    pos[2] - 0.20, pos[2],
                ))
                self.plotter.add_mesh(
                    box, color=_C_SUPPORT, name=f"sp_{sp.id}",
                    pickable=False, opacity=0.85
                )
            elif sp.support_type == "pinned":
                # Cone pointing downward
                cone = pv.Cone(
                    center=pos - np.array([0, 0, 0.10]),
                    direction=(0, 0, -1), height=0.18, radius=0.12
                )
                self.plotter.add_mesh(
                    cone, color=_C_SUPPORT, name=f"sp_{sp.id}",
                    pickable=False, opacity=0.85
                )
            elif sp.support_type == "roller":
                # Flat cylinder
                cyl = pv.Cylinder(
                    center=pos - np.array([0, 0, 0.06]),
                    direction=(0, 0, 1), height=0.04, radius=0.12
                )
                self.plotter.add_mesh(
                    cyl, color=_C_SUPPORT, name=f"sp_{sp.id}",
                    pickable=False, opacity=0.85
                )

    def _render_loads(self, doc):
        """Draw node load arrows (one per non-zero force/moment component)."""
        for nl in doc.node_loads.values():
            nd = doc.nodes.get(nl.node_id)
            if nd is None:
                continue
            origin = np.array([nd.x, nd.y, nd.z])
            ARROW_LEN = 0.6

            force_components = [
                (nl.Fx, np.array([1.0, 0.0, 0.0])),
                (nl.Fy, np.array([0.0, 1.0, 0.0])),
                (nl.Fz, np.array([0.0, 0.0, 1.0])),
            ]
            for i, (val, direction) in enumerate(force_components):
                if abs(val) < 1e-12:
                    continue
                tip   = origin
                tail  = origin - direction * np.sign(val) * ARROW_LEN
                arrow = pv.Arrow(
                    start=tail,
                    direction=tip - tail,
                    scale=np.linalg.norm(tip - tail),
                    tip_length=0.25,
                    tip_radius=0.07,
                    shaft_radius=0.03,
                )
                name = f"load_{nl.id}_f{i}"
                self.plotter.add_mesh(
                    arrow, color=_C_LOAD_FORCE, name=name,
                    pickable=False
                )

    def _render_labels(self, doc):
        """Add text labels for nodes and members."""
        for nd in doc.nodes.values():
            self.plotter.add_point_labels(
                np.array([[nd.x, nd.y, nd.z]]),
                [nd.id],
                name=f"lbl_nd_{nd.id}",
                font_size=9,
                text_color="cyan",
                point_color="cyan",
                point_size=0,
                shape=None,
                always_visible=True,
            )
        for mb in doc.members.values():
            n1 = doc.nodes.get(mb.start_node)
            n2 = doc.nodes.get(mb.end_node)
            if n1 and n2:
                mid = np.array([
                    (n1.x + n2.x) / 2,
                    (n1.y + n2.y) / 2,
                    (n1.z + n2.z) / 2,
                ])
                self.plotter.add_point_labels(
                    np.array([mid]),
                    [f"{mb.id} ({mb.section_name})"],
                    name=f"lbl_mb_{mb.id}",
                    font_size=8,
                    text_color="lightyellow",
                    point_color="lightyellow",
                    point_size=0,
                    shape=None,
                    always_visible=True,
                )

    # -----------------------------------------------------------------------
    # Post-solve rendering
    # -----------------------------------------------------------------------

    def _render_deformed(self, doc):
        """Draw deformed shape tubes offset from original positions."""
        results = self._results
        scale   = self._spin_scale.value()
        if results is None:
            return

        for mb in doc.members.values():
            n1 = doc.nodes.get(mb.start_node)
            n2 = doc.nodes.get(mb.end_node)
            if n1 is None or n2 is None:
                continue
            mr = results.member_results.get(mb.id)
            if mr is None:
                # Fall back to straight line between deformed node positions
                d1 = results.deformed_node_pos(n1.id, n1.x, n1.y, n1.z, scale)
                d2 = results.deformed_node_pos(n2.id, n2.x, n2.y, n2.z, scale)
                tube = pv.Line(np.array(d1), np.array(d2)).tube(
                    radius=_TUBE_RADIUS * 0.8, n_sides=6
                )
                self.plotter.add_mesh(
                    tube, color=_C_DEFORMED, opacity=0.7,
                    name=f"def_{mb.id}", pickable=False
                )
                continue

            # Sample deformed positions along member
            try:
                pn_member = results.fea.model.members[mb.id]
                L  = pn_member.L()
                lc = results.load_case
                pts = []
                for x in mr.positions:
                    # Deflection in local member axes (dy = sag, dz = lateral)
                    try:
                        dy_loc = pn_member.deflection('dy', x, combo_name=lc)
                        dz_loc = pn_member.deflection('dz', x, combo_name=lc)
                    except Exception:
                        dy_loc, dz_loc = 0.0, 0.0

                    # Member direction vector in world space
                    i_node = results.fea.model.nodes[mb.start_node]
                    j_node = results.fea.model.nodes[mb.end_node]
                    v = np.array([
                        j_node.X - i_node.X,
                        j_node.Y - i_node.Y,
                        j_node.Z - i_node.Z,
                    ])
                    v_len = np.linalg.norm(v)
                    if v_len < 1e-10:
                        continue
                    v_unit = v / v_len

                    # Local Y axis (perpendicular in vertical plane)
                    world_z = np.array([0.0, 0.0, 1.0])
                    perp_z  = np.cross(v_unit, world_z)
                    if np.linalg.norm(perp_z) < 1e-6:
                        perp_z = np.array([1.0, 0.0, 0.0])
                    perp_z /= np.linalg.norm(perp_z)
                    perp_y = np.cross(perp_z, v_unit)

                    # Base position along member
                    base = np.array([i_node.X, i_node.Y, i_node.Z]) + v_unit * x

                    # Apply node displacements at ends (interpolated)
                    t = x / L if L > 1e-10 else 0.0
                    d_start = results.deformed_node_pos(n1.id, n1.x, n1.y, n1.z, scale)
                    d_end   = results.deformed_node_pos(n2.id, n2.x, n2.y, n2.z, scale)
                    end_offset = (
                        np.array(d_start) - np.array([n1.x, n1.y, n1.z])
                    ) * (1 - t) + (
                        np.array(d_end) - np.array([n2.x, n2.y, n2.z])
                    ) * t

                    deformed = (
                        base
                        + end_offset
                        + perp_y * dy_loc * scale
                        + perp_z * dz_loc * scale
                    )
                    pts.append(deformed)

                if len(pts) >= 2:
                    pts_arr = np.array(pts)
                    spline  = pv.Spline(pts_arr, len(pts) * 3)
                    tube    = spline.tube(radius=_TUBE_RADIUS * 0.7, n_sides=6)
                    self.plotter.add_mesh(
                        tube, color=_C_DEFORMED, opacity=0.75,
                        name=f"def_{mb.id}", pickable=False
                    )
            except Exception:
                pass

    def _render_diagram(self, doc):
        """
        Draw an internal force diagram as a coloured filled surface
        offset perpendicular to each member.
        """
        results = self._results
        key     = self._active_diagram
        if results is None or key is None:
            return

        for mb in doc.members.values():
            n1 = doc.nodes.get(mb.start_node)
            n2 = doc.nodes.get(mb.end_node)
            if n1 is None or n2 is None:
                continue
            positions, values = results.diagram_data(mb.id, key)
            if not positions or not values:
                continue

            # Build a ruled-surface mesh offset perpendicular to member
            v = np.array([n2.x - n1.x, n2.y - n1.y, n2.z - n1.z])
            v_len = np.linalg.norm(v)
            if v_len < 1e-10:
                continue
            v_unit = v / v_len
            world_z = np.array([0.0, 0.0, 1.0])
            perp = np.cross(v_unit, world_z)
            if np.linalg.norm(perp) < 1e-6:
                perp = np.array([1.0, 0.0, 0.0])
            perp /= np.linalg.norm(perp)

            # Scale diagram: max value → 0.6 m offset
            max_abs = max(abs(v) for v in values)
            if max_abs < 1e-12:
                continue
            diag_scale = 0.6 / max_abs

            pts_base   = []
            pts_offset = []
            for x, val in zip(positions, values):
                base = np.array([n1.x, n1.y, n1.z]) + v_unit * x
                offs = base + perp * val * diag_scale
                pts_base.append(base)
                pts_offset.append(offs)

            # Build a surface from two polyline strips
            n = len(pts_base)
            points = np.vstack([pts_base, pts_offset])   # shape (2n, 3)
            # Quads: [base[i], base[i+1], offset[i+1], offset[i]]
            faces = []
            for i in range(n - 1):
                faces += [4, i, i + 1, n + i + 1, n + i]
            surf = pv.PolyData(points)
            surf.faces = np.array(faces)

            # Colour by diagram value (mapped to scalars)
            scalars = np.array(values + values)  # crude duplication
            self.plotter.add_mesh(
                surf, scalars=scalars,
                cmap="coolwarm", show_scalar_bar=False,
                name=f"diag_{mb.id}", opacity=0.75,
                pickable=False
            )

    # -----------------------------------------------------------------------
    # Slots from controller / toolbar
    # -----------------------------------------------------------------------

    def _on_selection_changed(self, entity_type: str, entity_id: str):
        self.refresh()

    def _on_solve_complete(self, results_cache):
        self._results = results_cache
        self.refresh()

    def _on_scale_changed(self, value: float):
        self._deform_scale = value
        if self._show_deformed and self._results:
            self.refresh()

    def show_results(self, results_cache):
        self._results = results_cache
        self.refresh()

    # -----------------------------------------------------------------------
    # View helpers
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # View presets (Z-up coordinate system)
    # -----------------------------------------------------------------------

    def _view_top(self):
        """Plan view: camera looking straight down (-Z), Y = north."""
        self.plotter.view_vector((0, 0, -1), viewup=(0, 1, 0))
        self.plotter.reset_camera()
        self.plotter.update()

    def _view_front(self):
        """Front elevation: camera from +Y looking toward origin, Z = up."""
        self.plotter.view_vector((0, -1, 0), viewup=(0, 0, 1))
        self.plotter.reset_camera()
        self.plotter.update()

    def _view_right(self):
        """Right elevation: camera from +X looking toward origin, Z = up."""
        self.plotter.view_vector((-1, 0, 0), viewup=(0, 0, 1))
        self.plotter.reset_camera()
        self.plotter.update()

    def _view_iso(self):
        """Isometric view: standard front-right-top, Z = up."""
        self.plotter.view_vector((-1, 1, -1), viewup=(0, 0, 1))
        self.plotter.reset_camera()
        self.plotter.update()

    def _fit_view(self):
        self.plotter.reset_camera()
        self.plotter.update()

    def _screenshot(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "viewport.png", "PNG (*.png)"
        )
        if path:
            self.plotter.screenshot(path)
