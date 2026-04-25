"""Tests for annex4.ingestors.hf_ingestor (mocked huggingface-hub SDK)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from annex4.ingestors.hf_ingestor import HuggingFaceIngestor


def _make_model_info(
    model_id="org/credit-scorer",
    pipeline_tag="tabular-classification",
    tags=None,
    card_data=None,
    last_modified="2026-01-15T10:00:00+00:00",
):
    info = MagicMock()
    info.id = model_id
    info.pipeline_tag = pipeline_tag
    info.tags = tags or []
    info.card_data = card_data or {}
    info.last_modified = last_modified
    return info


def _patch_hf(info):
    mock_hub = MagicMock()
    mock_hub.model_info.return_value = info
    return {"huggingface_hub": mock_hub}


def _is_sm(v, source="huggingface") -> bool:
    return isinstance(v, dict) and v.get("kind") == "system_metadata" and v.get("provenance", {}).get("source") == source


# ---------------------------------------------------------------------------
# SystemMetadata wrapping
# ---------------------------------------------------------------------------


class TestHuggingFaceIngestorMapping:
    def test_system_name_is_wrapped_in_system_metadata(self):
        info = _make_model_info(model_id="acme/risk-scorer")
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="acme/risk-scorer")
        name = output.data["general_description"]["system"]["name"]
        assert _is_sm(name)
        assert name["value"] == "acme/risk-scorer"

    def test_methodology_is_wrapped_in_system_metadata(self):
        info = _make_model_info(pipeline_tag="text-classification")
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="org/model")
        meth = output.data["development_process"]["methodology"]
        assert _is_sm(meth)
        assert meth["value"] == "text-classification"

    def test_card_description_wrapped_in_system_metadata(self):
        card = {"model_description": "Scores loan applicants."}
        info = _make_model_info(card_data=card)
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="org/model")
        desc = output.data["general_description"]["intended_purpose"]["description"]
        assert _is_sm(desc)
        assert desc["value"] == "Scores loan applicants."

    def test_limitations_wrapped_in_system_metadata(self):
        card = {"out_of_scope_use": "Not for criminal justice."}
        info = _make_model_info(card_data=card)
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="org/model")
        lim = output.data["monitoring_functioning_control"]["capabilities_and_limitations"]
        assert _is_sm(lim)
        assert lim["value"] == "Not for criminal justice."

    def test_provenance_source_ref_is_model_id(self):
        info = _make_model_info(model_id="myorg/my-model")
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="myorg/my-model")
        prov = output.data["general_description"]["system"]["name"]["provenance"]
        assert prov["source_ref"] == "myorg/my-model"

    def test_provenance_extracted_at_uses_last_modified(self):
        info = _make_model_info(last_modified="2026-03-01T12:00:00+00:00")
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="org/model")
        prov = output.data["general_description"]["system"]["name"]["provenance"]
        assert "2026-03-01" in prov["extracted_at"]

    def test_no_pipeline_tag_omits_dev_process(self):
        info = _make_model_info(pipeline_tag=None)
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="org/model")
        assert "development_process" not in output.data

    def test_source_name_and_priority(self):
        info = _make_model_info()
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="org/model")
        assert output.source_name == "huggingface"
        assert output.priority == 30

    def test_output_is_valid_dossier_after_from_yaml_dict(self):
        info = _make_model_info(model_id="acme/scorer")
        with patch.dict(sys.modules, _patch_hf(info)):
            output = HuggingFaceIngestor().ingest(model_id="acme/scorer")
        from annex4.core.schema import AnnexIVDossier
        from annex4.core.validate import _extract_val
        dossier = AnnexIVDossier.from_yaml_dict(output.data)
        assert _extract_val(dossier.general_description.system.name) == "acme/scorer"


# ---------------------------------------------------------------------------
# Missing dependency
# ---------------------------------------------------------------------------


class TestHuggingFaceMissingPackage:
    def test_raises_import_error_with_helpful_message(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "huggingface_hub", None)
        with pytest.raises(ImportError, match="huggingface"):
            HuggingFaceIngestor().ingest(model_id="org/model")
