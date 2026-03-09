"""
GUI/property_panel.py

PropertyPanel — context-sensitive property editor.

Uses QStackedWidget with one page per entity type:
  - EmptyPage     : nothing selected
  - NodePage      : X, Y, Z spinboxes
  - MemberPage    : section, material, rotation
  - SupportPage   : type (fixed/pinned/roller) + optional custom DOFs
  - NodeLoadPage  : Fx, Fy, Fz, Mx, My, Mz inputs + load case
  - MemberLoadPage: direction, w1/w2, x1/x2, load case
  - ResultsPage   : post-solve force envelope table for selected member
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .document import DocumentController

# AISC section types available in the picker
_SECTION_TYPES = ["W", "C", "HSS", "L", "WT", "MC", "S", "M"]
_MATERIALS = [
    "ASTM A36",
    "ASTM A992",
    "CSA G40.21 350W",
    "CSA G40.21 350A",
]


def _spin(lo=-1e6, hi=1e6, decimals=4, step=0.1, suffix="") -> QDoubleSpinBox:
    """Helper to create a QDoubleSpinBox with common settings."""
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    if suffix:
        s.setSuffix(f" {suffix}")
    return s


# ---------------------------------------------------------------------------
# Individual pages
# ---------------------------------------------------------------------------

class _EmptyPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addStretch()
        lbl = QLabel("Select an entity\nto view / edit properties.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: gray; font-style: italic;")
        lay.addWidget(lbl)
        lay.addStretch()


class _NodePage(QWidget):
    """Edit X, Y, Z for a selected node."""

    committed = Signal(str, dict)    # (node_id, {field: value})

    def __init__(self):
        super().__init__()
        self._node_id: Optional[str] = None
        self._lock = False

        form = QFormLayout(self)
        self._x = _spin(suffix="m")
        self._y = _spin(suffix="m")
        self._z = _spin(suffix="m")
        form.addRow("X:", self._x)
        form.addRow("Y:", self._y)
        form.addRow("Z:", self._z)

        btn = QPushButton("Apply")
        btn.clicked.connect(self._apply)
        form.addRow(btn)

        self._x.editingFinished.connect(self._apply)
        self._y.editingFinished.connect(self._apply)
        self._z.editingFinished.connect(self._apply)

    def load(self, node_id: str, x: float, y: float, z: float):
        self._node_id = node_id
        self._lock = True
        self._x.setValue(x)
        self._y.setValue(y)
        self._z.setValue(z)
        self._lock = False

    def _apply(self):
        if self._lock or self._node_id is None:
            return
        self.committed.emit(self._node_id, {
            "x": self._x.value(),
            "y": self._y.value(),
            "z": self._z.value(),
        })


class _CustomSectionForm(QWidget):
    """
    Dynamic form that shows dimension inputs for a chosen geometric shape.

    Emits ``changed`` whenever any dimension spinbox changes value so that
    the parent can refresh the live property preview.
    """

    changed = Signal()

    def __init__(self):
        super().__init__()
        from mech_core.analysis.statics import SHAPE_PARAMS
        self._shape_params = SHAPE_PARAMS
        self._spins: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        self._cb_shape = QComboBox()
        self._cb_shape.addItems(list(SHAPE_PARAMS.keys()))
        self._cb_shape.currentTextChanged.connect(self._on_shape_changed)
        root.addWidget(self._cb_shape)

        self._form_container = QWidget()
        self._form_layout = QFormLayout(self._form_container)
        self._form_layout.setContentsMargins(0, 4, 0, 0)
        self._form_layout.setSpacing(3)
        root.addWidget(self._form_container)

        # Initialise with the first shape
        self._on_shape_changed(self._cb_shape.currentText())

    # ---- Internal -----------------------------------------------------------

    def _on_shape_changed(self, shape_name: str):
        # Remove all existing rows
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)
        self._spins.clear()

        params = self._shape_params.get(shape_name, {})
        for key, (label, unit, default) in params.items():
            if key == "n":
                spin = QSpinBox()
                spin.setRange(3, 64)
                spin.setValue(int(default))
                spin.valueChanged.connect(lambda _v: self.changed.emit())
            else:
                spin = QDoubleSpinBox()
                spin.setRange(0.1, 10_000.0)
                spin.setDecimals(1)
                spin.setSingleStep(5.0)
                spin.setValue(default)
                if unit:
                    spin.setSuffix(f" {unit}")
                spin.valueChanged.connect(lambda _v: self.changed.emit())
            self._form_layout.addRow(f"{label}:", spin)
            self._spins[key] = spin

        self.changed.emit()

    # ---- Public API ---------------------------------------------------------

    def get_section_dict(self) -> dict:
        """Return ``{"shape": str, "params": {key: float}}``."""
        return {
            "shape":  self._cb_shape.currentText(),
            "params": {k: spin.value() for k, spin in self._spins.items()},
        }

    def compute_section(self):
        """Compute and return a GeometricSection (may raise ValueError)."""
        from mech_core.analysis.statics import from_dimensions
        d = self.get_section_dict()
        return from_dimensions(d["shape"], d["params"])

    def load(self, section_dict: dict):
        """Populate form from a stored ``{"shape": ..., "params": ...}`` dict."""
        shape  = section_dict.get("shape", self._cb_shape.itemText(0))
        params = section_dict.get("params", {})
        idx = self._cb_shape.findText(shape)
        if idx >= 0:
            self._cb_shape.setCurrentIndex(idx)
        for key, val in params.items():
            spin = self._spins.get(key)
            if spin is not None:
                spin.setValue(val)


class _MemberPage(QWidget):
    """
    Edit section, material, and rotation for a selected member.

    Provides two modes selectable by radio button:
      • Database Section — picker from AISC shape database
      • Custom Section   — geometric shape with dimension inputs and live preview
    """

    committed = Signal(str, dict)   # (member_id, {field: value, ...})

    def __init__(self):
        super().__init__()
        self._member_id: Optional[str] = None
        self._lock = False
        self._sections_loaded = False

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # ── Mode toggle ───────────────────────────────────────────────────────
        radio_row = QHBoxLayout()
        self._rb_db     = QRadioButton("Database Section")
        self._rb_custom = QRadioButton("Custom Section")
        self._rb_db.setChecked(True)
        self._btn_grp = QButtonGroup(self)
        self._btn_grp.addButton(self._rb_db,     0)
        self._btn_grp.addButton(self._rb_custom, 1)
        radio_row.addWidget(self._rb_db)
        radio_row.addWidget(self._rb_custom)
        root.addLayout(radio_row)

        # ── Mode stack ────────────────────────────────────────────────────────
        self._mode_stack = QStackedWidget()
        root.addWidget(self._mode_stack)

        # Page 0 — database
        db_widget = QWidget()
        db_form = QFormLayout(db_widget)
        db_form.setContentsMargins(0, 0, 0, 0)
        db_form.setSpacing(4)

        self._cb_type = QComboBox()
        self._cb_type.addItems(_SECTION_TYPES)
        self._cb_type.currentTextChanged.connect(self._load_sections_for_type)
        db_form.addRow("Shape type:", self._cb_type)

        self._cb_section = QComboBox()
        self._cb_section.setEditable(True)
        self._cb_section.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        db_form.addRow("Section:", self._cb_section)

        self._mode_stack.addWidget(db_widget)   # index 0

        # Page 1 — custom
        self._custom_form = _CustomSectionForm()
        self._custom_form.changed.connect(self._refresh_preview)
        self._mode_stack.addWidget(self._custom_form)   # index 1

        # ── Shared: material + rotation ───────────────────────────────────────
        shared_form = QFormLayout()
        shared_form.setContentsMargins(0, 0, 0, 0)
        shared_form.setSpacing(4)

        self._cb_material = QComboBox()
        self._cb_material.addItems(_MATERIALS)
        shared_form.addRow("Material:", self._cb_material)

        self._spin_rot = _spin(lo=-360, hi=360, decimals=1, step=5, suffix="°")
        shared_form.addRow("Rotation:", self._spin_rot)
        root.addLayout(shared_form)

        # ── Custom section property preview ───────────────────────────────────
        self._lbl_preview = QLabel()
        self._lbl_preview.setStyleSheet("color: #a6adc8; font-size: 9px;")
        self._lbl_preview.setWordWrap(True)
        self._lbl_preview.setVisible(False)
        root.addWidget(self._lbl_preview)

        # ── Apply ─────────────────────────────────────────────────────────────
        btn = QPushButton("Apply")
        btn.clicked.connect(self._apply)
        root.addWidget(btn)

        # Wire mode toggle
        self._rb_db.toggled.connect(self._on_mode_toggled)

    # ---- Mode toggle --------------------------------------------------------

    def _on_mode_toggled(self, db_checked: bool):
        if db_checked:
            self._mode_stack.setCurrentIndex(0)
            self._lbl_preview.setVisible(False)
        else:
            self._mode_stack.setCurrentIndex(1)
            self._lbl_preview.setVisible(True)
            self._refresh_preview()

    def _refresh_preview(self):
        if not self._rb_custom.isChecked():
            return
        try:
            sec = self._custom_form.compute_section()
            a  = sec.A.to("cm**2").magnitude
            ix = sec.Ix.to("cm**4").magnitude
            iy = sec.Iy.to("cm**4").magnitude
            j  = sec.J.to("cm**4").magnitude
            self._lbl_preview.setText(
                f"A={a:.2f} cm²   Ix={ix:.1f} cm⁴   Iy={iy:.1f} cm⁴   J={j:.2f} cm⁴"
            )
        except Exception:
            self._lbl_preview.setText("(invalid dimensions)")

    # ---- Database helpers ---------------------------------------------------

    def _load_sections_for_type(self, shape_type: str):
        from mech_core.components.members.aisc import get_shapes_by_type
        self._lock = True
        self._cb_section.clear()
        try:
            names = get_shapes_by_type(shape_type)
            self._cb_section.addItems(names)
        except Exception:
            pass
        self._lock = False

    # ---- Public API ---------------------------------------------------------

    def load(self, member_id: str, section_name: str,
             material_name: str, rotation: float,
             custom_section: Optional[dict] = None):
        self._member_id = member_id
        self._lock = True

        if custom_section:
            self._rb_custom.setChecked(True)
            self._mode_stack.setCurrentIndex(1)
            self._custom_form.load(custom_section)
            self._lbl_preview.setVisible(True)
        else:
            self._rb_db.setChecked(True)
            self._mode_stack.setCurrentIndex(0)
            self._lbl_preview.setVisible(False)

            # Populate database picker
            if not self._sections_loaded:
                self._load_sections_for_type(self._cb_type.currentText())
                self._sections_loaded = True

            for shape_type in _SECTION_TYPES:
                if section_name.startswith(shape_type):
                    idx = self._cb_type.findText(shape_type)
                    if idx >= 0 and self._cb_type.currentIndex() != idx:
                        self._cb_type.setCurrentIndex(idx)
                        self._load_sections_for_type(shape_type)
                    break

            sec_idx = self._cb_section.findText(section_name)
            if sec_idx >= 0:
                self._cb_section.setCurrentIndex(sec_idx)
            else:
                self._cb_section.setEditText(section_name)

        mat_idx = self._cb_material.findText(material_name)
        if mat_idx >= 0:
            self._cb_material.setCurrentIndex(mat_idx)

        self._spin_rot.setValue(rotation)
        self._lock = False

    # ---- Apply --------------------------------------------------------------

    def _apply(self):
        if self._lock or self._member_id is None:
            return

        if self._rb_custom.isChecked():
            sec_dict = self._custom_form.get_section_dict()
            try:
                from mech_core.analysis.statics import from_dimensions
                sec_name = from_dimensions(sec_dict["shape"], sec_dict["params"]).name
            except Exception:
                sec_name = "Custom"
            self.committed.emit(self._member_id, {
                "section_name":   sec_name,
                "material_name":  self._cb_material.currentText(),
                "rotation":       self._spin_rot.value(),
                "custom_section": sec_dict,
            })
        else:
            self.committed.emit(self._member_id, {
                "section_name":   self._cb_section.currentText(),
                "material_name":  self._cb_material.currentText(),
                "rotation":       self._spin_rot.value(),
                "custom_section": None,
            })


class _SupportPage(QWidget):
    """Assign / remove support at a node."""

    committed = Signal(str, dict)     # (node_id, {support_type, ...})
    remove_requested = Signal(str)    # (node_id,)

    def __init__(self):
        super().__init__()
        self._node_id: Optional[str] = None

        lay = QVBoxLayout(self)

        form = QFormLayout()
        self._cb_type = QComboBox()
        self._cb_type.addItems(["fixed", "pinned", "roller", "custom"])
        self._cb_type.currentTextChanged.connect(self._toggle_custom)
        form.addRow("Type:", self._cb_type)
        lay.addLayout(form)

        # Custom DOF group (hidden unless type == "custom")
        self._grp_custom = QGroupBox("Custom DOFs (restrained)")
        dof_lay = QVBoxLayout(self._grp_custom)
        self._chk = {}
        for dof in ("DX", "DY", "DZ", "RX", "RY", "RZ"):
            chk = QCheckBox(dof)
            chk.setChecked(dof in ("DX", "DY", "DZ"))
            self._chk[dof] = chk
            dof_lay.addWidget(chk)
        self._grp_custom.setVisible(False)
        lay.addWidget(self._grp_custom)

        btn_lay = QHBoxLayout()
        btn_apply = QPushButton("Apply")
        btn_remove = QPushButton("Remove Support")
        btn_apply.clicked.connect(self._apply)
        btn_remove.clicked.connect(self._remove)
        btn_lay.addWidget(btn_apply)
        btn_lay.addWidget(btn_remove)
        lay.addLayout(btn_lay)
        lay.addStretch()

    def _toggle_custom(self, text: str):
        self._grp_custom.setVisible(text == "custom")

    def load(self, node_id: str, support_type: str = "fixed",
             dx=True, dy=True, dz=True, rx=False, ry=False, rz=False):
        self._node_id = node_id
        idx = self._cb_type.findText(support_type)
        if idx >= 0:
            self._cb_type.setCurrentIndex(idx)
        dof_vals = dict(DX=dx, DY=dy, DZ=dz, RX=rx, RY=ry, RZ=rz)
        for k, chk in self._chk.items():
            chk.setChecked(dof_vals.get(k, False))

    def _apply(self):
        if self._node_id is None:
            return
        sup_type = self._cb_type.currentText()
        kwargs: dict = {"support_type": sup_type}
        if sup_type == "custom":
            kwargs.update({
                "dx": self._chk["DX"].isChecked(),
                "dy": self._chk["DY"].isChecked(),
                "dz": self._chk["DZ"].isChecked(),
                "rx": self._chk["RX"].isChecked(),
                "ry": self._chk["RY"].isChecked(),
                "rz": self._chk["RZ"].isChecked(),
            })
        self.committed.emit(self._node_id, kwargs)

    def _remove(self):
        if self._node_id:
            self.remove_requested.emit(self._node_id)


class _NodeLoadPage(QWidget):
    """Add / edit a node point load."""

    committed = Signal(str, dict)   # (node_id, load kwargs)

    def __init__(self):
        super().__init__()
        self._node_id: Optional[str] = None
        self._load_id: Optional[str] = None

        form = QFormLayout(self)
        self._Fx = _spin(suffix="kN")
        self._Fy = _spin(suffix="kN")
        self._Fz = _spin(suffix="kN")
        self._Mx = _spin(suffix="kN·m")
        self._My = _spin(suffix="kN·m")
        self._Mz = _spin(suffix="kN·m")
        form.addRow("Fx:", self._Fx)
        form.addRow("Fy:", self._Fy)
        form.addRow("Fz:", self._Fz)
        form.addRow("Mx:", self._Mx)
        form.addRow("My:", self._My)
        form.addRow("Mz:", self._Mz)

        self._cb_case = QComboBox()
        self._cb_case.setEditable(True)
        self._cb_case.addItem("Case 1")
        form.addRow("Load Case:", self._cb_case)

        btn = QPushButton("Apply Load")
        btn.clicked.connect(self._apply)
        form.addRow(btn)

    def load(self, node_id: str, load_id: Optional[str] = None,
             Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=0.0, Mz=0.0,
             case="Case 1"):
        self._node_id = node_id
        self._load_id = load_id
        self._Fx.setValue(Fx)
        self._Fy.setValue(Fy)
        self._Fz.setValue(Fz)
        self._Mx.setValue(Mx)
        self._My.setValue(My)
        self._Mz.setValue(Mz)
        idx = self._cb_case.findText(case)
        if idx >= 0:
            self._cb_case.setCurrentIndex(idx)
        else:
            self._cb_case.setEditText(case)

    def _apply(self):
        if self._node_id is None:
            return
        self.committed.emit(self._node_id, dict(
            Fx=self._Fx.value(),
            Fy=self._Fy.value(),
            Fz=self._Fz.value(),
            Mx=self._Mx.value(),
            My=self._My.value(),
            Mz=self._Mz.value(),
            case=self._cb_case.currentText(),
        ))


class _MemberLoadPage(QWidget):
    """Add / edit a distributed member load."""

    committed = Signal(str, dict)   # (member_id, load kwargs)

    def __init__(self):
        super().__init__()
        self._member_id: Optional[str] = None

        form = QFormLayout(self)

        self._cb_dir = QComboBox()
        self._cb_dir.addItems(["Fx", "Fy", "Fz"])
        form.addRow("Direction:", self._cb_dir)

        self._w1 = _spin(suffix="kN/m")
        self._w2 = _spin(suffix="kN/m")
        form.addRow("w1 (start):", self._w1)
        form.addRow("w2 (end):",   self._w2)

        self._x1 = _spin(lo=0, hi=1e4, suffix="m")
        self._x2 = _spin(lo=0, hi=1e4, suffix="m")
        self._x2.setValue(0)   # 0 = full length
        form.addRow("x1 (from):", self._x1)
        form.addRow("x2 (to, 0=full):", self._x2)

        self._cb_case = QComboBox()
        self._cb_case.setEditable(True)
        self._cb_case.addItem("Case 1")
        form.addRow("Load Case:", self._cb_case)

        btn = QPushButton("Apply Load")
        btn.clicked.connect(self._apply)
        form.addRow(btn)

    def load(self, member_id: str, **kwargs):
        self._member_id = member_id
        dir_idx = self._cb_dir.findText(kwargs.get("direction", "Fy"))
        if dir_idx >= 0:
            self._cb_dir.setCurrentIndex(dir_idx)
        self._w1.setValue(kwargs.get("w1", 0.0))
        self._w2.setValue(kwargs.get("w2", 0.0))
        self._x1.setValue(kwargs.get("x1", 0.0))
        self._x2.setValue(kwargs.get("x2") or 0.0)
        case = kwargs.get("case", "Case 1")
        idx = self._cb_case.findText(case)
        self._cb_case.setCurrentIndex(idx if idx >= 0 else 0)

    def _apply(self):
        if self._member_id is None:
            return
        x2 = self._x2.value()
        self.committed.emit(self._member_id, dict(
            direction=self._cb_dir.currentText(),
            w1=self._w1.value(),
            w2=self._w2.value(),
            x1=self._x1.value(),
            x2=None if x2 == 0 else x2,
            case=self._cb_case.currentText(),
        ))


class _ResultsPage(QWidget):
    """Display post-solve force envelope for the selected member."""

    export_requested = Signal(str)   # (member_id,)

    def __init__(self):
        super().__init__()
        self._member_id: Optional[str] = None

        lay = QVBoxLayout(self)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Quantity", "Value"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self._table)

        btn = QPushButton("Export Diagrams (PNG)…")
        btn.clicked.connect(lambda: self.export_requested.emit(self._member_id or ""))
        lay.addWidget(btn)

    def load(self, member_id: str, mr):
        """Populate table from a MemberResults object."""
        self._member_id = member_id
        rows = [
            ("Max Shear Vy",   f"{mr.max_shear_y:+.3f} kN"),
            ("Min Shear Vy",   f"{mr.min_shear_y:+.3f} kN"),
            ("Max Moment Mz",  f"{mr.max_moment_z:+.3f} kN·m"),
            ("Min Moment Mz",  f"{mr.min_moment_z:+.3f} kN·m"),
        ]
        self._table.setRowCount(len(rows))
        for i, (label, value) in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(label))
            self._table.setItem(i, 1, QTableWidgetItem(value))


# ---------------------------------------------------------------------------
# Container panel
# ---------------------------------------------------------------------------

class PropertyPanel(QWidget):
    """
    Right-side panel: shows a form appropriate for the selected entity type.

    Listens to controller.selection_changed and controller.solve_complete.
    Emits controller calls directly when form values are applied.
    """

    # Page indices in QStackedWidget
    _PAGE_EMPTY       = 0
    _PAGE_NODE        = 1
    _PAGE_MEMBER      = 2
    _PAGE_SUPPORT     = 3
    _PAGE_NODE_LOAD   = 4
    _PAGE_MEMBER_LOAD = 5
    _PAGE_RESULTS     = 6

    def __init__(self, controller: DocumentController,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._ctrl = controller
        self._setup_ui()
        self._connect()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Title label
        self._title = QLabel("Properties")
        self._title.setStyleSheet(
            "font-weight: bold; padding: 4px; background: #2a2a2a; color: #ddd;"
        )
        outer.addWidget(self._title)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(260)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(4, 4, 4, 4)

        self._stack = QStackedWidget()
        lay.addWidget(self._stack)
        lay.addStretch()

        # Create pages
        self._pg_empty       = _EmptyPage()
        self._pg_node        = _NodePage()
        self._pg_member      = _MemberPage()
        self._pg_support     = _SupportPage()
        self._pg_node_load   = _NodeLoadPage()
        self._pg_member_load = _MemberLoadPage()
        self._pg_results     = _ResultsPage()

        for pg in (self._pg_empty, self._pg_node, self._pg_member,
                   self._pg_support, self._pg_node_load,
                   self._pg_member_load, self._pg_results):
            self._stack.addWidget(pg)

        # Add-load shortcut buttons (shown below the stack)
        self._btn_add_node_load   = QPushButton("Add Node Load…")
        self._btn_add_member_load = QPushButton("Add Member Load…")
        self._btn_add_support     = QPushButton("Assign Support…")
        for btn in (self._btn_add_node_load,
                    self._btn_add_member_load,
                    self._btn_add_support):
            btn.setVisible(False)
            lay.addWidget(btn)

        self._btn_add_node_load.clicked.connect(self._on_add_node_load_clicked)
        self._btn_add_member_load.clicked.connect(self._on_add_member_load_clicked)
        self._btn_add_support.clicked.connect(self._on_add_support_clicked)

        self._show_page(self._PAGE_EMPTY)

    def _connect(self):
        self._ctrl.selection_changed.connect(self.show_entity)
        self._ctrl.solve_complete.connect(self._on_solve_complete)

        # Page signals → controller calls
        self._pg_node.committed.connect(self._apply_node)
        self._pg_member.committed.connect(self._apply_member)
        self._pg_support.committed.connect(self._apply_support)
        self._pg_support.remove_requested.connect(
            self._ctrl.remove_support_at_node
        )
        self._pg_node_load.committed.connect(self._apply_node_load)
        self._pg_member_load.committed.connect(self._apply_member_load)
        self._pg_results.export_requested.connect(self._export_diagrams)

    # ---- Show entity --------------------------------------------------------

    def show_entity(self, entity_type: str, entity_id: str):
        doc = self._ctrl.document
        results = self._ctrl.results

        # Hide shortcut buttons by default
        for btn in (self._btn_add_node_load,
                    self._btn_add_member_load,
                    self._btn_add_support):
            btn.setVisible(False)

        if not entity_type or not entity_id:
            self._title.setText("Properties")
            self._show_page(self._PAGE_EMPTY)
            return

        if entity_type == "node":
            nd = doc.nodes.get(entity_id)
            if nd is None:
                return
            self._title.setText(f"Node: {entity_id}")
            self._pg_node.load(entity_id, nd.x, nd.y, nd.z)
            self._show_page(self._PAGE_NODE)
            # Show shortcut buttons for node
            self._btn_add_support.setVisible(True)
            self._btn_add_node_load.setVisible(True)

        elif entity_type == "member":
            mb = doc.members.get(entity_id)
            if mb is None:
                return
            self._title.setText(f"Member: {entity_id}")
            # If solved: show results page
            if results and entity_id in results.member_results:
                self._pg_results.load(entity_id, results.member_results[entity_id])
                self._show_page(self._PAGE_RESULTS)
                self._btn_add_member_load.setVisible(True)
            else:
                self._pg_member.load(
                    entity_id, mb.section_name, mb.material_name,
                    mb.rotation, custom_section=mb.custom_section,
                )
                self._show_page(self._PAGE_MEMBER)
                self._btn_add_member_load.setVisible(True)

        elif entity_type == "support":
            sp = doc.supports.get(entity_id)
            if sp is None:
                return
            self._title.setText(f"Support: {entity_id}")
            self._pg_support.load(entity_id, sp.support_type,
                                  sp.dx, sp.dy, sp.dz, sp.rx, sp.ry, sp.rz)
            self._show_page(self._PAGE_SUPPORT)

        elif entity_type in ("node_load", "load"):
            nl = doc.node_loads.get(entity_id)
            if nl:
                self._title.setText(f"Node Load: {entity_id}")
                self._pg_node_load.load(
                    nl.node_id, entity_id,
                    Fx=nl.Fx, Fy=nl.Fy, Fz=nl.Fz,
                    Mx=nl.Mx, My=nl.My, Mz=nl.Mz, case=nl.case,
                )
                self._show_page(self._PAGE_NODE_LOAD)
                return
            ml = doc.member_loads.get(entity_id)
            if ml:
                self._title.setText(f"Member Load: {entity_id}")
                self._pg_member_load.load(
                    ml.member_id,
                    direction=ml.direction, w1=ml.w1, w2=ml.w2,
                    x1=ml.x1, x2=ml.x2, case=ml.case,
                )
                self._show_page(self._PAGE_MEMBER_LOAD)

        else:
            self._show_page(self._PAGE_EMPTY)

    # ---- Shortcut button slots ----------------------------------------------

    def _on_add_node_load_clicked(self):
        if self._ctrl.selected_type == "node" and self._ctrl.selected_id:
            self._title.setText(f"New Load on {self._ctrl.selected_id}")
            self._pg_node_load.load(self._ctrl.selected_id)
            self._show_page(self._PAGE_NODE_LOAD)

    def _on_add_member_load_clicked(self):
        if self._ctrl.selected_type == "member" and self._ctrl.selected_id:
            self._title.setText(f"New Load on {self._ctrl.selected_id}")
            self._pg_member_load.load(self._ctrl.selected_id)
            self._show_page(self._PAGE_MEMBER_LOAD)

    def _on_add_support_clicked(self):
        if self._ctrl.selected_type == "node" and self._ctrl.selected_id:
            self._title.setText(f"Support on {self._ctrl.selected_id}")
            self._pg_support.load(self._ctrl.selected_id)
            self._show_page(self._PAGE_SUPPORT)

    # ---- Apply callbacks ----------------------------------------------------

    def _apply_node(self, node_id: str, kwargs: dict):
        self._ctrl.update_node(node_id, **kwargs)

    def _apply_member(self, member_id: str, kwargs: dict):
        self._ctrl.update_member(member_id, **kwargs)

    def _apply_support(self, node_id: str, kwargs: dict):
        self._ctrl.set_support(node_id, **kwargs)

    def _apply_node_load(self, node_id: str, kwargs: dict):
        load_id = self._pg_node_load._load_id
        if load_id and load_id in self._ctrl.document.node_loads:
            self._ctrl.update_node_load(load_id, **kwargs)
        else:
            self._ctrl.add_node_load(node_id, **kwargs)

    def _apply_member_load(self, member_id: str, kwargs: dict):
        self._ctrl.add_member_load(member_id, **kwargs)

    # ---- Post-solve refresh -------------------------------------------------

    def _on_solve_complete(self, results_cache):
        # Refresh the currently shown entity
        sel_type = self._ctrl.selected_type
        sel_id   = self._ctrl.selected_id
        if sel_type and sel_id:
            self.show_entity(sel_type, sel_id)

    # ---- Export -------------------------------------------------------------

    def _export_diagrams(self, member_id: str):
        from PySide6.QtWidgets import QFileDialog
        if not member_id or not self._ctrl.results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Diagrams", f"{member_id}_diagrams.png",
            "PNG Image (*.png)"
        )
        if path:
            try:
                self._ctrl.results.fea.generate_diagrams(member_id, path)
            except Exception as exc:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Export Error", str(exc))

    # ---- Internal -----------------------------------------------------------

    def _show_page(self, index: int):
        self._stack.setCurrentIndex(index)
