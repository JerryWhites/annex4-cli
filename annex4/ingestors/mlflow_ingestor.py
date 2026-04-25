"""
MLflow ingestor: pulls run metadata and metrics into a partial dossier.

Each extracted field is wrapped in a SystemMetadata dict with full provenance
so the merge engine can apply conflict resolution and the dossier preserves
the audit trail back to the originating MLflow run.

Requires: pip install mlflow
Priority 30.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from annex4.ingestors.base import IngestorOutput


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sm(
    value: Any, run_id: str, extracted_at: str, confidence: float = 0.9
) -> Dict[str, Any]:
    """Wrap a scalar value in a SystemMetadata dict."""
    return {
        "kind": "system_metadata",
        "value": value,
        "provenance": {
            "source": "mlflow",
            "source_ref": run_id,
            "extracted_at": extracted_at,
            "extractor_version": "annex4-cli-1.0",
            "confidence": confidence,
        },
    }


class MLflowIngestor:
    """Extracts model metadata from an MLflow run and wraps each field in SystemMetadata."""

    name = "mlflow"
    priority = 30

    def __init__(self, tracking_uri: Optional[str] = None) -> None:
        self._tracking_uri = tracking_uri

    def ingest(self, *, run_id: str) -> IngestorOutput:
        try:
            import mlflow  # type: ignore[import-not-found]
            import mlflow.tracking  # type: ignore[import-not-found]
        except ImportError:
            raise ImportError(
                "MLflow ingestor requires mlflow. Install it with: pip install mlflow"
            )

        if self._tracking_uri:
            mlflow.set_tracking_uri(self._tracking_uri)

        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        return IngestorOutput(
            data=self._map_run(run, run_id),
            source_name=self.name,
            priority=self.priority,
        )

    def _map_run(self, run: Any, run_id: str) -> Dict[str, Any]:
        tags: Dict[str, str] = dict(run.data.tags or {})
        params: Dict[str, str] = dict(run.data.params or {})
        metrics: Dict[str, float] = dict(run.data.metrics or {})

        # Determine extraction timestamp from run start time if available
        try:
            start_ms = run.info.start_time
            extracted_at = datetime.fromtimestamp(
                start_ms / 1000, tz=timezone.utc
            ).isoformat()
        except (TypeError, AttributeError, OSError):
            extracted_at = _now_iso()

        name = (
            tags.get("model_name") or getattr(run.info, "run_name", None) or run_id[:8]
        )
        version = tags.get("model_version") or tags.get("version") or run_id[:8]
        methodology = params.get("algorithm") or tags.get("algorithm") or ""
        architecture = (
            params.get("architecture")
            or tags.get("model_type")
            or tags.get("architecture")
            or ""
        )

        acc_metrics: List[Dict[str, Any]] = [
            {
                "name": _sm(k, run_id, extracted_at, confidence=0.95),
                "aggregate_value": _sm(
                    str(round(v, 6)), run_id, extracted_at, confidence=0.95
                ),
            }
            for k, v in metrics.items()
        ]

        data: Dict[str, Any] = {
            "general_description": {
                "system": {
                    "name": _sm(name, run_id, extracted_at),
                    "version": _sm(version, run_id, extracted_at),
                }
            }
        }

        dev: Dict[str, Any] = {}
        if methodology:
            dev["methodology"] = _sm(methodology, run_id, extracted_at)
        if architecture:
            dev["architecture_description"] = _sm(architecture, run_id, extracted_at)
        if dev:
            data["development_process"] = dev

        if acc_metrics:
            data["monitoring_functioning_control"] = {"accuracy_metrics": acc_metrics}

        return data
