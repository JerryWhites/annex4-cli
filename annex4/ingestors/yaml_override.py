"""
YAML override ingestor: reads a partial dossier YAML file.

Highest-priority ingestor (80) — use for manual human corrections that should
win over any machine-extracted field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from annex4.ingestors.base import IngestorOutput


class YAMLOverrideIngestor:
    """Reads a YAML file containing a partial AnnexIVDossier and wraps it."""

    name = "yaml_override"
    priority = 80

    def ingest(self, *, path: Union[str, Path]) -> IngestorOutput:
        path = Path(path)
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"YAML override file must be a mapping, got {type(data).__name__}: {path}"
            )
        return IngestorOutput(data=data, source_name=self.name, priority=self.priority)
