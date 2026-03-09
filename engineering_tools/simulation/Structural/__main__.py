"""
simulation/Structural/__main__.py

Application entry point.

Run with (from engineering_tools/ directory):
    python -m simulation.Structural
"""

import sys
import os

# Ensure pyvistaqt uses PySide6
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .main_window import MainWindow


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Frostad Structural Lab")
    app.setOrganizationName("Frostad Engineering")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
