"""
HTML renderer for AnnexIVDossier.

Produces a self-contained HTML document suitable for browser viewing or
conversion to PDF via weasyprint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from annex4.core.schema import AnnexIVDossier
from annex4.core.validate import _extract_val

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _field_val(f: Any) -> str:
    """Jinja2 filter: extract display string from a Field_ value."""
    val = _extract_val(f)
    if val is None:
        return "—"
    return str(val)


def _field_list(lst: Any) -> List[str]:
    """Jinja2 filter: extract display strings from a list of Field_ values."""
    if not lst:
        return []
    return [_field_val(item) for item in lst]


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["field_val"] = _field_val
    env.filters["field_list"] = _field_list
    env.globals["now"] = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return env


def render_html(dossier: AnnexIVDossier) -> str:
    """Render *dossier* to a self-contained HTML string."""
    env = _build_env()
    template = env.get_template("base.html")
    return template.render(dossier=dossier)
