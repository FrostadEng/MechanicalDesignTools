"""
simulation/Structural/placement_tools.py

Dialogs for pattern-based node placement:
  - LineSubdivideDialog  : subdivide a line segment into N equal parts
  - ArrayDialog          : rectangular or circular node arrays
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class LineSubdivideDialog(QDialog):
    """
    Dialog shown after the user picks two endpoints with the Line Tool.

    Reports N intermediate nodes to insert and whether to connect them
    with members.
    """

    def __init__(
        self,
        x1: float, y1: float, z1: float,
        x2: float, y2: float, z2: float,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Line Tool — Subdivide")
        self.setMinimumWidth(300)

        self._x1, self._y1, self._z1 = x1, y1, z1
        self._x2, self._y2, self._z2 = x2, y2, z2
        length = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)

        lay = QVBoxLayout(self)

        # Info
        info = QGroupBox("Segment")
        info_form = QFormLayout(info)
        info_form.addRow("Start:", QLabel(f"X={x1:.3f}  Y={y1:.3f}  Z={z1:.3f}"))
        info_form.addRow("End:",   QLabel(f"X={x2:.3f}  Y={y2:.3f}  Z={z2:.3f}"))
        info_form.addRow("Length:", QLabel(f"{length:.3f} m"))
        lay.addWidget(info)

        # Controls
        ctrl_form = QFormLayout()
        self._spin_n = QSpinBox()
        self._spin_n.setRange(0, 200)
        self._spin_n.setValue(1)
        self._spin_n.valueChanged.connect(self._update_summary)
        ctrl_form.addRow("Intermediate nodes:", self._spin_n)

        self._lbl_summary = QLabel()
        ctrl_form.addRow("Result:", self._lbl_summary)

        self._chk_connect = QCheckBox("Connect with members")
        self._chk_connect.setChecked(True)
        ctrl_form.addRow("", self._chk_connect)

        lay.addLayout(ctrl_form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._update_summary(1)

    def _update_summary(self, n: int):
        total_nodes   = n + 2
        total_members = (n + 1) if self._chk_connect.isChecked() else 0
        self._lbl_summary.setText(
            f"{total_nodes} nodes  ·  {total_members} members"
        )

    def result_values(self) -> tuple[int, bool]:
        """Return (n_intermediate, connect_members)."""
        return self._spin_n.value(), self._chk_connect.isChecked()


# ---------------------------------------------------------------------------
# Rectangular array tab
# ---------------------------------------------------------------------------

class _RectTab(QWidget):
    def __init__(self, base_x: float, base_y: float, base_z: float):
        super().__init__()
        form = QFormLayout(self)
        form.setSpacing(4)

        def _spin(lo, hi, val, dec=3, step=0.5, suffix=""):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setDecimals(dec)
            s.setSingleStep(step)
            s.setValue(val)
            if suffix:
                s.setSuffix(suffix)
            return s

        self._bx = _spin(-1000, 1000, base_x, suffix=" m")
        self._by = _spin(-1000, 1000, base_y, suffix=" m")
        self._bz = _spin(-1000, 1000, base_z, suffix=" m")
        form.addRow("Base X:", self._bx)
        form.addRow("Base Y:", self._by)
        form.addRow("Base Z:", self._bz)

        self._dx = _spin(-100, 100, 1.0, suffix=" m")
        self._dy = _spin(-100, 100, 1.0, suffix=" m")
        self._dz = _spin(-100, 100, 0.0, suffix=" m")
        form.addRow("Spacing X:", self._dx)
        form.addRow("Spacing Y:", self._dy)
        form.addRow("Spacing Z:", self._dz)

        self._cols   = QSpinBox(); self._cols.setRange(1, 100);   self._cols.setValue(3)
        self._rows   = QSpinBox(); self._rows.setRange(1, 100);   self._rows.setValue(3)
        self._levels = QSpinBox(); self._levels.setRange(1, 100); self._levels.setValue(1)
        form.addRow("Columns (X):", self._cols)
        form.addRow("Rows (Y):",    self._rows)
        form.addRow("Levels (Z):", self._levels)

        self._cx = QCheckBox("Connect along X"); self._cx.setChecked(True)
        self._cy = QCheckBox("Connect along Y"); self._cy.setChecked(True)
        self._cz = QCheckBox("Connect along Z"); self._cz.setChecked(False)
        form.addRow("", self._cx)
        form.addRow("", self._cy)
        form.addRow("", self._cz)

    def get_params(self) -> dict:
        return dict(
            base_x=self._bx.value(), base_y=self._by.value(), base_z=self._bz.value(),
            dx=self._dx.value(), dy=self._dy.value(), dz=self._dz.value(),
            cols=self._cols.value(), rows=self._rows.value(), levels=self._levels.value(),
            connect_x=self._cx.isChecked(),
            connect_y=self._cy.isChecked(),
            connect_z=self._cz.isChecked(),
        )


# ---------------------------------------------------------------------------
# Circular array tab
# ---------------------------------------------------------------------------

class _CircTab(QWidget):
    def __init__(self, base_x: float, base_y: float, base_z: float):
        super().__init__()
        form = QFormLayout(self)
        form.setSpacing(4)

        def _spin(lo, hi, val, dec=3, step=0.5, suffix=""):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setDecimals(dec)
            s.setSingleStep(step)
            s.setValue(val)
            if suffix:
                s.setSuffix(suffix)
            return s

        self._cx = _spin(-1000, 1000, base_x, suffix=" m")
        self._cy = _spin(-1000, 1000, base_y, suffix=" m")
        self._cz = _spin(-1000, 1000, base_z, suffix=" m")
        form.addRow("Centre X:", self._cx)
        form.addRow("Centre Y:", self._cy)
        form.addRow("Centre Z:", self._cz)

        self._radius     = _spin(0.01, 1000, 2.0, suffix=" m")
        self._n          = QSpinBox(); self._n.setRange(3, 360); self._n.setValue(8)
        self._start_ang  = _spin(-360, 360, 0.0, dec=1, step=15, suffix="°")
        self._arc_ang    = _spin(-360, 360, 360.0, dec=1, step=15, suffix="°")
        self._dz_step    = _spin(-100, 100, 0.0, suffix=" m")
        form.addRow("Radius:", self._radius)
        form.addRow("Nodes:", self._n)
        form.addRow("Start angle:", self._start_ang)
        form.addRow("Arc angle:", self._arc_ang)
        form.addRow("Z per step:", self._dz_step)

        self._chk_connect = QCheckBox("Connect with members")
        self._chk_connect.setChecked(True)
        form.addRow("", self._chk_connect)

        self._chk_close = QCheckBox("Close loop (connect last→first)")
        self._chk_close.setChecked(True)
        form.addRow("", self._chk_close)

    def get_params(self) -> dict:
        return dict(
            center_x=self._cx.value(), center_y=self._cy.value(), center_z=self._cz.value(),
            radius=self._radius.value(), n=self._n.value(),
            start_angle=self._start_ang.value(), arc_angle=self._arc_ang.value(),
            dz_step=self._dz_step.value(),
            connect=self._chk_connect.isChecked(),
            close_loop=self._chk_close.isChecked(),
        )


# ---------------------------------------------------------------------------
# Main array dialog
# ---------------------------------------------------------------------------

class ArrayDialog(QDialog):
    """
    Tabbed dialog for placing a rectangular or circular node array.
    """

    def __init__(
        self,
        base_x: float = 0.0, base_y: float = 0.0, base_z: float = 0.0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Array Tool")
        self.setMinimumWidth(320)

        lay = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._rect_tab = _RectTab(base_x, base_y, base_z)
        self._circ_tab = _CircTab(base_x, base_y, base_z)
        self._tabs.addTab(self._rect_tab, "Rectangular")
        self._tabs.addTab(self._circ_tab, "Circular")
        lay.addWidget(self._tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    @property
    def mode(self) -> str:
        return "rectangular" if self._tabs.currentIndex() == 0 else "circular"

    def result_params(self) -> dict:
        """Return params dict for the active tab."""
        if self.mode == "rectangular":
            return self._rect_tab.get_params()
        return self._circ_tab.get_params()
