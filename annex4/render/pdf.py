"""
PDF renderer for AnnexIVDossier.

Converts the HTML rendering to PDF via weasyprint (optional dependency).
Install with: pip install weasyprint
"""

from __future__ import annotations

from pathlib import Path

from annex4.core.schema import AnnexIVDossier
from annex4.render.html import render_html


def render_pdf(dossier: AnnexIVDossier, output_path: Path) -> None:
    """Render *dossier* to a PDF file at *output_path*.

    Raises ImportError if weasyprint is not installed.
    """
    try:
        from weasyprint import HTML  # type: ignore[import-not-found]
    except ImportError:
        raise ImportError(
            "PDF rendering requires weasyprint.\n"
            "Install it with: pip install weasyprint"
        )

    html_content = render_html(dossier)
    HTML(string=html_content).write_pdf(str(output_path))
