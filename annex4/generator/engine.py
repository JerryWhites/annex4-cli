"""
The core engine for generating documentation from templates.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader, select_autoescape

from annex4.regulation.loader import RegulationLoader


class GeneratorEngine:
    """
    Renders technical documentation using Jinja2 templates.
    """

    def __init__(self) -> None:
        template_path = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_path),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.globals["now"] = lambda: datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )

    def render(
        self,
        classification_file: Path,
        template_name: str,
        override_paths: Optional[List[Path]] = None,
    ) -> str:
        """
        Renders a documentation template with data from a classification JSON file.
        Used by the `generate` CLI command (classification-first workflow).
        """
        with open(classification_file, "r", encoding="utf-8") as f:
            classification_data = json.load(f)

        regulation_version = classification_data.get(
            "regulation_version", "2024-1689_base"
        )
        loader = RegulationLoader(regulation_version)
        regulation = loader.load_regulation()

        overrides_data: Dict[str, Any] = {}
        if override_paths:
            for path in override_paths:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        overrides_data.update(data)

        context: Dict[str, Any] = {
            "classification": classification_data,
            "regulation": regulation,
            "verdict": classification_data.get("verdict", {}),
            "answers": classification_data.get("answers", {}),
            "overrides": overrides_data,
        }

        template = self.env.get_template(template_name)
        return template.render(context)

    def render_dossier(self, dossier_file: Path) -> str:
        """
        Renders a full Annex IV document from a filled dossier YAML file.
        Used by the `render` CLI command (dossier-first workflow).

        Args:
            dossier_file: Path to the dossier.yaml filled in by the user.

        Returns:
            Rendered markdown string covering all 9 Annex IV sections.
        """
        from annex4.core.schema import AnnexIVDossier

        with open(dossier_file, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw or not isinstance(raw, dict):
            raise ValueError(f"Dossier file is empty or invalid: {dossier_file}")

        dossier = AnnexIVDossier.from_yaml_dict(raw)

        context: Dict[str, Any] = {"dossier": dossier}
        template = self.env.get_template("annex_iv_dossier.md.j2")
        return template.render(context)
