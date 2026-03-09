"""
mech_core.GUI

Interactive 3D structural frame modeling environment.

Public API
----------
MainWindow          — top-level QMainWindow
DocumentController  — model state + undo + solve controller
StructuralDocument  — pure-data document model

Launch as a standalone application:
    python -m mech_core.GUI
    python -m engineering_tools.mech_core.GUI
"""

from .main_window import MainWindow
from .document import DocumentController, StructuralDocument

__all__ = [
    "MainWindow",
    "DocumentController",
    "StructuralDocument",
]
