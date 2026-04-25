"""
Merge engine: combines IngestorOutput dicts into one dossier dict.

Conflict resolution for SystemMetadata fields: when two outputs provide the
same field, the one with the newer `provenance.extracted_at` timestamp wins
and the result is marked `conflict_resolved: true`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from annex4.ingestors.base import IngestorOutput


def _is_sm(v: Any) -> bool:
    """Return True if *v* is a SystemMetadata dict."""
    return isinstance(v, dict) and v.get("kind") == "system_metadata"


def _extracted_at(sm: Dict[str, Any]) -> datetime:
    """Parse provenance.extracted_at into a timezone-aware datetime (UTC fallback)."""
    raw = (sm.get("provenance") or {}).get("extracted_at", "")
    try:
        dt = datetime.fromisoformat(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def _resolve_conflict(
    existing: Dict[str, Any], incoming: Dict[str, Any]
) -> Dict[str, Any]:
    """Pick the SystemMetadata with the newer timestamp; mark conflict_resolved=True."""
    winner = (
        incoming if _extracted_at(incoming) >= _extracted_at(existing) else existing
    )
    result = dict(winner)
    result["conflict_resolved"] = True
    return result


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Return a new dict that is *override* merged on top of *base*.

    - Dicts are merged recursively.
    - When both values are SystemMetadata dicts, the one with the newer
      provenance.extracted_at wins (and conflict_resolved is set True).
    - Any other value type is overwritten by the override.
    Neither input is mutated.
    """
    result: Dict[str, Any] = dict(base)
    for key, val in override.items():
        existing = result.get(key)
        if _is_sm(existing) and _is_sm(val) and isinstance(existing, dict):
            result[key] = _resolve_conflict(existing, val)
        elif isinstance(existing, dict) and isinstance(val, dict) and not _is_sm(val):
            result[key] = deep_merge(existing, val)
        else:
            result[key] = val
    return result


def merge_ingestor_outputs(
    outputs: List[IngestorOutput],
    base: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge a list of IngestorOutputs into one dict.

    Outputs are applied in ascending priority order so the highest-priority
    ingestor wins every conflict.  When two SystemMetadata fields conflict,
    the one with the newer extracted_at timestamp wins regardless of priority
    (within the same priority level, newer timestamp wins).
    An optional *base* dict is the starting point (lowest priority of all).
    """
    merged: Dict[str, Any] = dict(base) if base else {}
    for output in sorted(outputs, key=lambda o: o.priority):
        merged = deep_merge(merged, output.data)
    return merged
