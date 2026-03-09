"""
simulation/Structural/pdf_export.py

PDF (and HTML) report generation via PyNite Reporting.

PyNite.Reporting.create_report() renders an HTML template with Jinja2
and converts it to PDF using pdfkit + wkhtmltopdf.  This module wraps
that call with a clean interface and sensible defaults for the GUI.

Requirements (optional, only needed for PDF export):
    pip install pdfkit
    # and install wkhtmltopdf:  https://wkhtmltopdf.org/downloads.html
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .results import ResultsCache

# Sections the user can toggle on/off in the export dialog.
# Each entry: (kwarg_name, human_label, default_on)
REPORT_SECTIONS = [
    ("node_table",              "Node coordinates table",        True),
    ("member_table",            "Member properties table",       True),
    ("node_reactions",          "Support reactions",             True),
    ("node_displacements",      "Node displacements",            True),
    ("member_end_forces",       "Member end forces",             True),
    ("member_internal_forces",  "Member internal force diagrams", True),
    ("member_releases",         "Member end releases",           False),
    ("plate_table",             "Plate / quad table",            False),
    ("plate_corner_forces",     "Plate corner forces",           False),
    ("plate_center_forces",     "Plate center forces",           False),
    ("plate_corner_membrane",   "Plate corner membrane forces",  False),
    ("plate_center_membrane",   "Plate center membrane forces",  False),
]


def export_pdf(
    results: "ResultsCache",
    output_path: str | Path,
    sections: Optional[dict] = None,
) -> None:
    """
    Generate a PDF report for a solved model.

    Args:
        results:     ResultsCache returned by DocumentController after a solve.
        output_path: Full path (including .pdf extension) for the output file.
        sections:    Dict mapping kwarg_name → bool controlling which report
                     sections are included.  Keys must be from REPORT_SECTIONS.
                     Defaults: all True entries in REPORT_SECTIONS are enabled.

    Raises:
        ImportError:  If pdfkit or wkhtmltopdf are not available.
        RuntimeError: If report generation fails inside PyNite.
    """
    try:
        from Pynite import Reporting
    except ImportError as exc:
        raise ImportError(
            "PyNite Reporting requires pdfkit and wkhtmltopdf.\n"
            "Install pdfkit with:  pip install pdfkit\n"
            "Download wkhtmltopdf: https://wkhtmltopdf.org/downloads.html"
        ) from exc

    # Build kwargs from sections dict (or defaults)
    kwargs: dict = {}
    for key, _label, default in REPORT_SECTIONS:
        kwargs[key] = (sections.get(key, default) if sections else default)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        Reporting.create_report(
            results.fea.model,
            output_filepath=str(output_path),
            format="pdf",
            log=False,
            **kwargs,
        )
    except Exception as exc:
        raise RuntimeError(f"PDF generation failed: {exc}") from exc


def check_available() -> tuple[bool, str]:
    """
    Return (available: bool, message: str).

    Checks whether pdfkit and wkhtmltopdf are installed so the GUI
    can show an informative error before the user tries to export.
    """
    try:
        from Pynite import Reporting
        path = Reporting.get_wkhtmltopdf_path(log=False)
        if path is None:
            return False, (
                "wkhtmltopdf not found on PATH.\n"
                "Download from: https://wkhtmltopdf.org/downloads.html"
            )
        return True, ""
    except ImportError:
        return False, (
            "pdfkit is not installed.\n"
            "Install with:  pip install pdfkit"
        )
    except Exception as exc:
        return False, str(exc)
