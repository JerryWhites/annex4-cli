"""Tests for annex4.ingestors.mlflow_ingestor (mocked MLflow SDK)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from annex4.ingestors.mlflow_ingestor import MLflowIngestor


def _make_mock_run(
    run_name="credit_model",
    run_id="abc123def456",
    tags=None,
    params=None,
    metrics=None,
    start_time=1_700_000_000_000,
):
    run = MagicMock()
    run.info.run_name = run_name
    run.info.run_id = run_id
    run.info.start_time = start_time
    run.data.tags = tags or {}
    run.data.params = params or {}
    run.data.metrics = metrics or {}
    return run


def _patched_mlflow(run):
    mock = MagicMock()
    mock.tracking.MlflowClient.return_value.get_run.return_value = run
    return mock


def _is_sm(v, source="mlflow") -> bool:
    return (
        isinstance(v, dict)
        and v.get("kind") == "system_metadata"
        and v.get("provenance", {}).get("source") == source
    )


# ---------------------------------------------------------------------------
# SystemMetadata wrapping
# ---------------------------------------------------------------------------


class TestMLflowIngestorMapping:
    def test_name_is_wrapped_in_system_metadata(self):
        mock_run = _make_mock_run(run_name="loan_scorer_v2")
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        name_field = output.data["general_description"]["system"]["name"]
        assert _is_sm(name_field)
        assert name_field["value"] == "loan_scorer_v2"

    def test_version_is_wrapped_in_system_metadata(self):
        mock_run = _make_mock_run(tags={"model_version": "3.1.0"})
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        ver = output.data["general_description"]["system"]["version"]
        assert _is_sm(ver)
        assert ver["value"] == "3.1.0"

    def test_methodology_is_wrapped_in_system_metadata(self):
        mock_run = _make_mock_run(params={"algorithm": "XGBoost"})
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        meth = output.data["development_process"]["methodology"]
        assert _is_sm(meth)
        assert meth["value"] == "XGBoost"

    def test_metrics_are_wrapped_in_system_metadata(self):
        mock_run = _make_mock_run(metrics={"auc_roc": 0.83, "f1": 0.77})
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        metrics = output.data["monitoring_functioning_control"]["accuracy_metrics"]
        assert all(_is_sm(m["name"]) and _is_sm(m["aggregate_value"]) for m in metrics)
        names = [m["name"]["value"] for m in metrics]
        assert "auc_roc" in names

    def test_provenance_source_ref_is_run_id(self):
        mock_run = _make_mock_run(run_id="deadbeef1234")
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="deadbeef1234")
        prov = output.data["general_description"]["system"]["name"]["provenance"]
        assert prov["source_ref"] == "deadbeef1234"

    def test_provenance_has_extracted_at_from_run_start_time(self):
        mock_run = _make_mock_run(start_time=1_700_000_000_000)
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        prov = output.data["general_description"]["system"]["name"]["provenance"]
        assert "2023" in prov["extracted_at"]  # Nov 2023 epoch

    def test_no_metrics_omits_mfc_key(self):
        mock_run = _make_mock_run(metrics={})
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        assert "monitoring_functioning_control" not in output.data

    def test_source_name_and_priority(self):
        mock_run = _make_mock_run()
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        assert output.source_name == "mlflow"
        assert output.priority == 30

    def test_tracking_uri_set_when_provided(self):
        mock_run = _make_mock_run()
        mock_mlflow = _patched_mlflow(mock_run)
        with patch.dict(
            sys.modules, {"mlflow": mock_mlflow, "mlflow.tracking": MagicMock()}
        ):
            MLflowIngestor(tracking_uri="http://mlflow.local:5000").ingest(run_id="abc")
        mock_mlflow.set_tracking_uri.assert_called_once_with("http://mlflow.local:5000")

    def test_output_is_valid_dossier_after_from_yaml_dict(self):
        mock_run = _make_mock_run(run_name="TestSys", tags={"model_version": "1.0"})
        with patch.dict(
            sys.modules,
            {"mlflow": _patched_mlflow(mock_run), "mlflow.tracking": MagicMock()},
        ):
            output = MLflowIngestor().ingest(run_id="abc")
        from annex4.core.schema import AnnexIVDossier

        dossier = AnnexIVDossier.from_yaml_dict(output.data)
        from annex4.core.validate import _extract_val

        assert _extract_val(dossier.general_description.system.name) == "TestSys"


# ---------------------------------------------------------------------------
# Missing dependency
# ---------------------------------------------------------------------------


class TestMLflowMissingPackage:
    def test_raises_import_error_with_helpful_message(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "mlflow", None)
        monkeypatch.setitem(sys.modules, "mlflow.tracking", None)
        with pytest.raises(ImportError, match="mlflow"):
            MLflowIngestor().ingest(run_id="abc")
