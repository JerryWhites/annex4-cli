"""
HuggingFace Hub ingestor: pulls model card data into a partial dossier.

Each extracted field is wrapped in a SystemMetadata dict with provenance
pointing back to the HuggingFace model ID.

Requires: pip install huggingface-hub
Priority 30.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from annex4.ingestors.base import IngestorOutput


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sm(
    value: Any, model_id: str, extracted_at: str, confidence: float = 0.8
) -> Dict[str, Any]:
    return {
        "kind": "system_metadata",
        "value": value,
        "provenance": {
            "source": "huggingface",
            "source_ref": model_id,
            "extracted_at": extracted_at,
            "extractor_version": "annex4-cli-1.0",
            "confidence": confidence,
        },
    }


class HuggingFaceIngestor:
    """Extracts metadata from a HuggingFace Hub model card."""

    name = "huggingface"
    priority = 30

    def ingest(self, *, model_id: str, token: Optional[str] = None) -> IngestorOutput:
        try:
            from huggingface_hub import model_info  # type: ignore[import-not-found]
        except ImportError:
            raise ImportError(
                "HuggingFace ingestor requires huggingface-hub. "
                "Install it with: pip install huggingface-hub"
            )

        info = model_info(model_id, token=token)
        return IngestorOutput(
            data=self._map_model_info(info, model_id),
            source_name=self.name,
            priority=self.priority,
        )

    def _map_model_info(self, info: Any, model_id: str) -> Dict[str, Any]:
        # Use last_modified as extraction timestamp when available
        last_modified = getattr(info, "last_modified", None) or getattr(
            info, "lastModified", None
        )
        try:
            if isinstance(last_modified, str):
                extracted_at = last_modified
            elif last_modified is not None:
                extracted_at = last_modified.isoformat()
            else:
                extracted_at = _now_iso()
        except (AttributeError, ValueError):
            extracted_at = _now_iso()

        card = getattr(info, "card_data", None) or {}
        pipeline_tag: str = getattr(info, "pipeline_tag", None) or ""

        def _card_get(key: str, *fallbacks: str) -> str:
            if hasattr(card, "get"):
                for k in (key, *fallbacks):
                    val = card.get(k)
                    if val:
                        return str(val)
            return ""

        description = _card_get("model_description", "model_overview", "description")
        intended_use = _card_get("intended_use", "uses", "intended_uses")
        limitations = _card_get(
            "out_of_scope_use", "limitations", "bias_risks_limitations"
        )

        data: Dict[str, Any] = {
            "general_description": {
                "system": {
                    "name": _sm(model_id, model_id, extracted_at, confidence=0.95)
                }
            }
        }

        ip: Dict[str, Any] = {}
        if description:
            ip["description"] = _sm(description, model_id, extracted_at)
        if intended_use:
            ip["intended_users"] = _sm(intended_use, model_id, extracted_at)
        if ip:
            data["general_description"]["intended_purpose"] = ip

        dev: Dict[str, Any] = {}
        if pipeline_tag:
            dev["methodology"] = _sm(pipeline_tag, model_id, extracted_at)
        if dev:
            data["development_process"] = dev

        mfc: Dict[str, Any] = {}
        if limitations:
            mfc["capabilities_and_limitations"] = _sm(
                limitations, model_id, extracted_at
            )
        if mfc:
            data["monitoring_functioning_control"] = mfc

        return data
