"""
Giskard ingestor: maps a Giskard ScanResult into partial dossier fields.

Each extracted value is wrapped in a SystemMetadata dict with provenance
pointing to the Giskard scan.

Requires: pip install giskard
Priority 40.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from annex4.ingestors.base import IngestorOutput


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sm(
    value: Any, scan_ref: str, extracted_at: str, confidence: float = 0.85
) -> Dict[str, Any]:
    return {
        "kind": "system_metadata",
        "value": value,
        "provenance": {
            "source": "giskard",
            "source_ref": scan_ref,
            "extracted_at": extracted_at,
            "extractor_version": "annex4-cli-1.0",
            "confidence": confidence,
        },
    }


class GiskardIngestor:
    """Extracts vulnerability and bias data from a Giskard scan result."""

    name = "giskard"
    priority = 40

    def ingest(self, *, scan_result: Any) -> IngestorOutput:
        try:
            import giskard  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            raise ImportError(
                "Giskard ingestor requires giskard. "
                "Install it with: pip install giskard"
            )

        return IngestorOutput(
            data=self._map_scan_result(scan_result),
            source_name=self.name,
            priority=self.priority,
        )

    def _map_scan_result(self, scan_result: Any) -> Dict[str, Any]:
        issues = list(getattr(scan_result, "issues", None) or [])
        scan_ref = str(getattr(scan_result, "id", None) or "giskard_scan")
        extracted_at = _now_iso()

        acc_metrics: List[Dict[str, Any]] = []
        bias_items: List[Dict[str, Any]] = []

        for issue in issues:
            group = getattr(issue, "group", None)
            metric_name: str = getattr(group, "name", "Unknown") if group else "Unknown"
            metric_value = getattr(issue, "metric_value", None)
            description: str = str(getattr(issue, "description", "") or "")

            if metric_value is not None:
                try:
                    acc_metrics.append(
                        {
                            "name": _sm(metric_name, scan_ref, extracted_at),
                            "aggregate_value": _sm(
                                str(round(float(metric_value), 6)),
                                scan_ref,
                                extracted_at,
                            ),
                        }
                    )
                except (TypeError, ValueError):
                    pass

            name_lower = metric_name.lower()
            if (
                "bias" in name_lower
                or "fairness" in name_lower
                or "disparity" in name_lower
            ):
                bias_items.append(
                    {
                        "attribute": _sm(metric_name, scan_ref, extracted_at),
                        "action_taken": _sm(description, scan_ref, extracted_at),
                    }
                )

        data: Dict[str, Any] = {}

        if acc_metrics:
            data["monitoring_functioning_control"] = {"accuracy_metrics": acc_metrics}

        if bias_items:
            data.setdefault("development_process", {}).setdefault(
                "data_governance", {}
            )["bias_analysis"] = bias_items

        return data
