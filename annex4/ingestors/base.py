"""
Base protocol and value object for all ingestors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol, runtime_checkable


@dataclass
class IngestorOutput:
    """Partial dossier data produced by one ingestor run."""

    data: Dict[str, Any]
    source_name: str
    priority: int = 50  # 0 = lowest … 100 = highest; higher priority wins conflicts


@runtime_checkable
class Ingestor(Protocol):
    """Protocol every ingestor must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def priority(self) -> int: ...

    def ingest(self, **kwargs: Any) -> IngestorOutput: ...
