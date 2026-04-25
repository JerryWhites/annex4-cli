"""Tests for annex4.ingestors.giskard_ingestor (mocked Giskard SDK)."""

import sys
from unittest.mock import MagicMock

import pytest

from annex4.ingestors.giskard_ingestor import GiskardIngestor


def _make_issue(group_name: str, metric_value: float, description: str = ""):
    issue = MagicMock()
    issue.group = MagicMock()
    issue.group.name = group_name
    issue.metric_value = metric_value
    issue.description = description
    return issue


def _make_scan_result(issues=None, scan_id="scan_001"):
    sr = MagicMock()
    sr.issues = issues or []
    sr.id = scan_id
    return sr


def _is_sm(v, source="giskard") -> bool:
    return (
        isinstance(v, dict)
        and v.get("kind") == "system_metadata"
        and v.get("provenance", {}).get("source") == source
    )


# ---------------------------------------------------------------------------
# SystemMetadata wrapping
# ---------------------------------------------------------------------------


class TestGiskardIngestorMapping:
    def test_metrics_are_wrapped_in_system_metadata(self):
        issues = [_make_issue("AUC-ROC", 0.81), _make_issue("F1", 0.73)]
        sr = _make_scan_result(issues)
        with MagicMock() as mock_giskard:
            sys.modules["giskard"] = mock_giskard
            output = GiskardIngestor().ingest(scan_result=sr)
            del sys.modules["giskard"]
        metrics = output.data["monitoring_functioning_control"]["accuracy_metrics"]
        assert all(_is_sm(m["name"]) and _is_sm(m["aggregate_value"]) for m in metrics)
        names = [m["name"]["value"] for m in metrics]
        assert "AUC-ROC" in names

    def test_bias_metrics_wrapped_in_system_metadata(self):
        issues = [_make_issue("Gender Bias", 0.05, "Female under-approved.")]
        sr = _make_scan_result(issues)
        with MagicMock() as mock_giskard:
            sys.modules["giskard"] = mock_giskard
            output = GiskardIngestor().ingest(scan_result=sr)
            del sys.modules["giskard"]
        bias = output.data["development_process"]["data_governance"]["bias_analysis"]
        assert all(_is_sm(b["attribute"]) and _is_sm(b["action_taken"]) for b in bias)
        assert bias[0]["attribute"]["value"] == "Gender Bias"

    def test_provenance_source_ref_from_scan_id(self):
        issues = [_make_issue("AUC", 0.8)]
        sr = _make_scan_result(issues, scan_id="scan_xyz_42")
        with MagicMock() as mock_giskard:
            sys.modules["giskard"] = mock_giskard
            output = GiskardIngestor().ingest(scan_result=sr)
            del sys.modules["giskard"]
        metric = output.data["monitoring_functioning_control"]["accuracy_metrics"][0]
        assert metric["name"]["provenance"]["source_ref"] == "scan_xyz_42"

    def test_non_bias_metric_not_in_bias_analysis(self):
        issues = [_make_issue("AUC-ROC", 0.83)]
        sr = _make_scan_result(issues)
        with MagicMock() as mock_giskard:
            sys.modules["giskard"] = mock_giskard
            output = GiskardIngestor().ingest(scan_result=sr)
            del sys.modules["giskard"]
        assert "development_process" not in output.data

    def test_empty_scan_result_produces_empty_data(self):
        sr = _make_scan_result([])
        with MagicMock() as mock_giskard:
            sys.modules["giskard"] = mock_giskard
            output = GiskardIngestor().ingest(scan_result=sr)
            del sys.modules["giskard"]
        assert output.data == {}

    def test_source_name_and_priority(self):
        sr = _make_scan_result([])
        with MagicMock() as mock_giskard:
            sys.modules["giskard"] = mock_giskard
            output = GiskardIngestor().ingest(scan_result=sr)
            del sys.modules["giskard"]
        assert output.source_name == "giskard"
        assert output.priority == 40

    def test_metric_value_rounded_to_6_places(self):
        issues = [_make_issue("Precision", 0.8333333333)]
        sr = _make_scan_result(issues)
        with MagicMock() as mock_giskard:
            sys.modules["giskard"] = mock_giskard
            output = GiskardIngestor().ingest(scan_result=sr)
            del sys.modules["giskard"]
        val = output.data["monitoring_functioning_control"]["accuracy_metrics"][0][
            "aggregate_value"
        ]["value"]
        assert val == "0.833333"


# ---------------------------------------------------------------------------
# Missing dependency
# ---------------------------------------------------------------------------


class TestGiskardMissingPackage:
    def test_raises_import_error_with_helpful_message(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "giskard", None)
        with pytest.raises(ImportError, match="giskard"):
            GiskardIngestor().ingest(scan_result=MagicMock())
