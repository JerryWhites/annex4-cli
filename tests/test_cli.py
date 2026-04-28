"""CLI integration tests for annex4."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner

from annex4.cli import cli


# ---------------------------------------------------------------------------
# Basic CLI surface
# ---------------------------------------------------------------------------


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "EU AI Act" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0


def test_cli_lists_expected_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    for cmd in ("classify", "validate", "render", "ingest", "diff", "init"):
        assert cmd in result.output


# ---------------------------------------------------------------------------
# render command — format extension
# ---------------------------------------------------------------------------


def _write_valid_dossier(path: Path) -> None:
    """Write a minimal dossier YAML that passes all error-level rules."""
    dossier = {
        "general_description": {
            "provider": {
                "name": "Acme AI GmbH",
                "address": "Unter den Linden 1, 10117 Berlin",
                "contact_email": "ai@acme.example",
                "authorized_signatory": "Jane Smith, CTO",
            },
            "system": {
                "name": "RiskScore Pro",
                "version": "1.0.0",
                "classification": "High-risk · Annex III §5(b)",
                "regulation_version": "2024-1689_base",
            },
            "intended_purpose": {
                "description": "Scores credit applicants on default risk.",
                "intended_users": "Loan officers at partner banks.",
                "persons_affected": "EU natural persons applying for credit.",
            },
        },
        "development_process": {
            "methodology": "Gradient boosted trees.",
            "architecture_description": "XGBoost ensemble with 500 estimators.",
            "input_description": "Structured applicant feature vector (42 fields).",
            "output_description": "Risk score 0–1000.",
        },
        "monitoring_functioning_control": {
            "capabilities_and_limitations": "Works on EU applicants aged 18+.",
            "foreseeable_unintended_outcomes": "Potential disparate impact.",
            "human_oversight_measures": "All decisions reviewed by a loan officer.",
        },
        "risk_management": {
            "process_description": "Quarterly risk review.",
            "identified_risks": [
                {
                    "risk": "Disparate impact",
                    "likelihood": "Medium",
                    "impact": "High",
                    "mitigation": "Reweighting",
                    "residual_risk": "Within threshold",
                    "accepted_by": "CTO",
                }
            ],
        },
        "post_market_monitoring": {
            "monitoring_approach": "Monthly AUC-ROC evaluation.",
        },
    }
    path.write_text(yaml.dump(dossier, allow_unicode=True), encoding="utf-8")


class TestRenderCommand:
    def test_render_markdown_default(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        out = tmp_path / "doc.md"
        _write_valid_dossier(dossier)
        result = CliRunner().invoke(cli, ["render", str(dossier), "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_render_html_format_flag(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        out = tmp_path / "doc.html"
        _write_valid_dossier(dossier)
        result = CliRunner().invoke(
            cli, ["render", str(dossier), "--output", str(out), "--format", "html"]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "RiskScore Pro" in content

    def test_render_html_inferred_from_extension(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        out = tmp_path / "doc.html"
        _write_valid_dossier(dossier)
        result = CliRunner().invoke(cli, ["render", str(dossier), "--output", str(out)])
        assert result.exit_code == 0, result.output
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_render_pdf_calls_weasyprint(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        out = tmp_path / "doc.pdf"
        _write_valid_dossier(dossier)
        mock_weasyprint = MagicMock()
        mock_weasyprint.HTML.return_value = MagicMock()
        with patch.dict(sys.modules, {"weasyprint": mock_weasyprint}):
            result = CliRunner().invoke(
                cli, ["render", str(dossier), "--output", str(out), "--format", "pdf"]
            )
        assert result.exit_code == 0, result.output
        mock_weasyprint.HTML.assert_called_once()

    def test_render_aborts_on_validation_errors(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        out = tmp_path / "doc.md"
        empty.write_text("{}", encoding="utf-8")
        result = CliRunner().invoke(cli, ["render", str(empty), "--output", str(out)])
        assert result.exit_code != 0
        assert not out.exists()


# ---------------------------------------------------------------------------
# ingest command
# ---------------------------------------------------------------------------


class TestIngestCommand:
    def test_ingest_requires_at_least_one_source(self, tmp_path):
        out = tmp_path / "dossier.yaml"
        result = CliRunner().invoke(cli, ["ingest", "--output", str(out)])
        assert result.exit_code == 1

    def test_ingest_yaml_override_only(self, tmp_path):
        override = tmp_path / "patch.yaml"
        override.write_text(
            "general_description:\n  system:\n    name: IngestedSystem\n    version: '3.0'\n"
        )
        out = tmp_path / "dossier.yaml"
        result = CliRunner().invoke(
            cli, ["ingest", "--override", str(override), "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = yaml.safe_load(out.read_text())
        assert data["general_description"]["system"]["name"] == "IngestedSystem"

    def test_ingest_merges_into_existing_file(self, tmp_path):
        existing = tmp_path / "dossier.yaml"
        existing.write_text(
            "general_description:\n  provider:\n    name: ExistingProvider\n"
        )
        override = tmp_path / "patch.yaml"
        override.write_text("general_description:\n  system:\n    name: NewSystem\n")
        result = CliRunner().invoke(
            cli, ["ingest", "--override", str(override), "--output", str(existing)]
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(existing.read_text())
        assert data["general_description"]["provider"]["name"] == "ExistingProvider"
        assert data["general_description"]["system"]["name"] == "NewSystem"

    def test_ingest_multiple_overrides_merged_in_order(self, tmp_path):
        o1 = tmp_path / "o1.yaml"
        o2 = tmp_path / "o2.yaml"
        o1.write_text(
            "general_description:\n  system:\n    name: First\n    version: '1.0'\n"
        )
        o2.write_text("general_description:\n  system:\n    name: Second\n")
        out = tmp_path / "dossier.yaml"
        result = CliRunner().invoke(
            cli,
            [
                "ingest",
                "--override",
                str(o1),
                "--override",
                str(o2),
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text())
        # Both overrides are priority 80; o2 applied after o1, so o2 wins name conflict
        assert data["general_description"]["system"]["name"] == "Second"
        # Version only in o1 survives
        assert data["general_description"]["system"]["version"] == "1.0"

    def test_ingest_mlflow_run(self, tmp_path):
        mock_run = MagicMock()
        mock_run.info.run_name = "credit_model"
        mock_run.info.run_id = "abc123"
        mock_run.info.start_time = 1_700_000_000_000
        mock_run.data.tags = {"model_version": "2.0"}
        mock_run.data.params = {"algorithm": "XGBoost"}
        mock_run.data.metrics = {"auc_roc": 0.83}
        mock_mlflow = MagicMock()
        mock_mlflow.tracking.MlflowClient.return_value.get_run.return_value = mock_run

        out = tmp_path / "dossier.yaml"
        with patch.dict(
            sys.modules, {"mlflow": mock_mlflow, "mlflow.tracking": MagicMock()}
        ):
            result = CliRunner().invoke(
                cli, ["ingest", "--mlflow-run", "abc123", "--output", str(out)]
            )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        # Ingestors now emit SystemMetadata dicts; check wrapped value
        assert data["general_description"]["system"]["name"]["value"] == "credit_model"

    def test_ingest_mlflow_missing_package_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "mlflow", None)
        monkeypatch.setitem(sys.modules, "mlflow.tracking", None)
        out = tmp_path / "dossier.yaml"
        result = CliRunner().invoke(
            cli, ["ingest", "--mlflow-run", "abc", "--output", str(out)]
        )
        assert result.exit_code == 1

    def test_ingest_hf_model(self, tmp_path):
        mock_info = MagicMock()
        mock_info.id = "org/credit-scorer"
        mock_info.pipeline_tag = "tabular-classification"
        mock_info.tags = []
        mock_info.card_data = {}
        mock_info.last_modified = (
            "2026-01-15T10:00:00+00:00"  # must be str, not MagicMock
        )
        mock_hub = MagicMock()
        mock_hub.model_info.return_value = mock_info

        out = tmp_path / "dossier.yaml"
        with patch.dict(sys.modules, {"huggingface_hub": mock_hub}):
            result = CliRunner().invoke(
                cli, ["ingest", "--hf-model", "org/credit-scorer", "--output", str(out)]
            )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(out.read_text(encoding="utf-8"))
        # Ingestors now emit SystemMetadata dicts; check wrapped value
        assert (
            data["general_description"]["system"]["name"]["value"]
            == "org/credit-scorer"
        )

    def test_ingest_success_message_mentions_source_count(self, tmp_path):
        override = tmp_path / "patch.yaml"
        override.write_text("general_description:\n  system:\n    name: Test\n")
        out = tmp_path / "dossier.yaml"
        result = CliRunner().invoke(
            cli, ["ingest", "--override", str(override), "--output", str(out)]
        )
        assert "1 source" in " ".join(result.output.split())
