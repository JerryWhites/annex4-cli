"""Tests for the classifier engine and RiskProfile output (PR#3)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from annex4.classifier.engine import ClassifierEngine
from annex4.classifier.models import RiskProfile
from annex4.cli import classify
from annex4.regulation.loader import RegulationLoader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def spec():
    loader = RegulationLoader("2024-1689_base")
    return loader.load_classifier_spec()


@pytest.fixture(scope="module")
def engine(spec):
    from rich.console import Console

    return ClassifierEngine(spec, Console(quiet=True))


# ---------------------------------------------------------------------------
# RiskProfile model
# ---------------------------------------------------------------------------


class TestRiskProfile:
    def test_is_high_risk_true_for_high_risk_verdict(self):
        p = RiskProfile(
            path_id="test",
            verdict="HIGH_RISK_ANNEX_III_§4",
            citation="Annex III §4",
            articles=["Article 6(2)"],
            conformity_route="internal_control_annex_vi",
            notified_body_required=False,
            explanation_markdown="x",
            next_steps="y",
        )
        assert p.is_high_risk is True

    def test_is_high_risk_false_for_minimal(self):
        p = RiskProfile(
            path_id="test",
            verdict="MINIMAL_RISK",
            citation="Recital 33",
            articles=[],
            conformity_route="not_applicable",
            notified_body_required=False,
            explanation_markdown="x",
            next_steps="y",
        )
        assert p.is_high_risk is False

    def test_needs_annex_iv_true_for_high_risk(self):
        p = RiskProfile(
            path_id="test",
            verdict="HIGH_RISK_ANNEX_III_§4",
            citation="c",
            articles=[],
            conformity_route="c",
            notified_body_required=False,
            explanation_markdown="x",
            next_steps="y",
        )
        assert p.needs_annex_iv is True

    def test_disclaimer_is_hardcoded(self):
        p = RiskProfile(
            path_id="x",
            verdict="MINIMAL_RISK",
            citation="c",
            articles=[],
            conformity_route="c",
            notified_body_required=False,
            explanation_markdown="x",
            next_steps="y",
        )
        assert "not a legal determination" in p.disclaimer
        assert "counsel" in p.disclaimer


# ---------------------------------------------------------------------------
# Engine: interactive mode (mocked input)
# ---------------------------------------------------------------------------


class TestClassifierEngineInteractive:
    def test_minimal_risk_path(self, spec, monkeypatch):
        # Provider → None prohibited → No safety component → No Annex III → No GPAI → No limited risk → Minimal
        inputs = iter(["1", "5", "2", "2", "2", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.run()
        assert profile.verdict == "MINIMAL_RISK"
        assert not profile.is_high_risk
        assert not profile.needs_annex_iv

    def test_employment_high_risk_path(self, spec, monkeypatch):
        # Provider → None prohibited → No safety component → Yes Annex III → §4 Employment
        inputs = iter(["1", "5", "2", "1", "4"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.run()
        assert profile.verdict == "HIGH_RISK_ANNEX_III_§4"
        assert (
            profile.path_id
            == "annex_iii_4a_employment_article_6_2_internal_control_annex_vi"
        )
        assert "Article 6(2)" in profile.articles
        assert "Annex III §4(a)" in " ".join(profile.articles)
        assert profile.conformity_route == "internal_control_annex_vi"
        assert profile.notified_body_required is False

    def test_safety_component_path_requires_notified_body(self, spec, monkeypatch):
        # Provider → None prohibited → Yes safety component
        inputs = iter(["1", "5", "1"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.run()
        assert profile.verdict == "HIGH_RISK_ARTICLE_6_1"
        assert profile.notified_body_required is True

    def test_prohibited_path(self, spec, monkeypatch):
        # Provider → Social scoring selected (not "None of above")
        inputs = iter(["1", "3"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.run()
        assert profile.verdict == "PROHIBITED"
        assert profile.is_prohibited

    def test_deployer_redirect(self, spec, monkeypatch):
        inputs = iter(["2"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.run()
        assert profile.verdict == "DEPLOYER_REDIRECT"

    def test_gpai_redirect(self, spec, monkeypatch):
        # Provider → None prohibited → No safety component → No Annex III → Yes GPAI
        inputs = iter(["1", "5", "2", "2", "1"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.run()
        assert profile.verdict == "GPAI_MODEL"


# ---------------------------------------------------------------------------
# Engine: non-interactive --system mode
# ---------------------------------------------------------------------------


class TestClassifierEngineFromYaml:
    def test_infers_employment_from_annex_iii_category(self, spec, tmp_path):
        yaml_file = tmp_path / "dossier.yaml"
        yaml_file.write_text(
            "general_description:\n"
            "  system:\n"
            "    annex_iii_category: 'Employment, workers management (Annex III section 4)'\n"
            "    classification: 'High Risk'\n",
            encoding="utf-8",
        )
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.classify_from_yaml(yaml_file)
        assert "ANNEX_III" in profile.verdict
        assert "4" in profile.verdict
        assert profile.conformity_route == "internal_control_annex_vi"

    def test_infers_credit_scoring_essential_services(self, spec, tmp_path):
        yaml_file = tmp_path / "dossier.yaml"
        yaml_file.write_text(
            "general_description:\n"
            "  system:\n"
            "    annex_iii_category: 'Essential services - credit scoring'\n"
            "    classification: 'High Risk'\n",
            encoding="utf-8",
        )
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.classify_from_yaml(yaml_file)
        assert "ANNEX_III" in profile.verdict
        assert "5" in profile.verdict

    def test_infers_minimal_from_classification_field(self, spec, tmp_path):
        yaml_file = tmp_path / "dossier.yaml"
        yaml_file.write_text(
            "general_description:\n"
            "  system:\n"
            "    classification: 'minimal risk application'\n",
            encoding="utf-8",
        )
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.classify_from_yaml(yaml_file)
        assert profile.verdict == "MINIMAL_RISK"

    def test_system_metadata_wrapped_field_extracted(self, spec, tmp_path):
        yaml_file = tmp_path / "dossier.yaml"
        yaml_file.write_text(
            "general_description:\n"
            "  system:\n"
            "    annex_iii_category:\n"
            "      kind: system_metadata\n"
            "      value: 'Employment screening section 4'\n"
            "      provenance:\n"
            "        source: manual\n"
            "        source_ref: test\n"
            "        extracted_at: '2026-01-01'\n"
            "        extractor_version: '1.0'\n"
            "        confidence: 1.0\n",
            encoding="utf-8",
        )
        from rich.console import Console

        e = ClassifierEngine(spec, Console(quiet=True))
        profile = e.classify_from_yaml(yaml_file)
        assert "ANNEX_III" in profile.verdict
        assert "4" in profile.verdict


# ---------------------------------------------------------------------------
# CLI: --i-acknowledge-uncertainty gate
# ---------------------------------------------------------------------------


class TestClassifyCLI:
    def test_exits_2_without_acknowledge_flag(self):
        result = CliRunner().invoke(classify, [])
        assert result.exit_code == 2

    def test_prints_acknowledgement_message_without_flag(self):
        result = CliRunner().invoke(classify, [])
        assert "Acknowledgement required" in result.output or result.exit_code == 2

    def test_runs_with_acknowledge_flag(self, monkeypatch):
        inputs = iter(["1", "5", "2", "2", "2", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        result = CliRunner().invoke(classify, ["--i-acknowledge-uncertainty"])
        assert result.exit_code == 0
        assert "Risk Classification Profile" in result.output

    def test_system_flag_non_interactive(self, tmp_path):
        yaml_file = tmp_path / "dossier.yaml"
        yaml_file.write_text(
            "general_description:\n"
            "  system:\n"
            "    annex_iii_category: 'Employment screening'\n"
            "    classification: 'High Risk'\n"
            "    regulation_version: '2024-1689_base'\n"
        )
        result = CliRunner().invoke(
            classify, ["--i-acknowledge-uncertainty", "--system", str(yaml_file)]
        )
        out_json = tmp_path / "profile.json"
        result = CliRunner().invoke(
            classify,
            [
                "--i-acknowledge-uncertainty",
                "--system",
                str(yaml_file),
                "--output",
                str(out_json),
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert "ANNEX_III" in data["risk_profile"]["verdict"]
        assert "4" in data["risk_profile"]["verdict"]
        assert data["risk_profile"]["conformity_route"] == "internal_control_annex_vi"

    def test_output_json_contains_risk_profile(self, tmp_path, monkeypatch):
        inputs = iter(["1", "5", "2", "2", "2", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        out = tmp_path / "profile.json"
        result = CliRunner().invoke(
            classify, ["--i-acknowledge-uncertainty", "--output", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert "risk_profile" in data
        assert data["risk_profile"]["verdict"] == "MINIMAL_RISK"

    def test_employment_path_shows_correct_articles(self, monkeypatch):
        inputs = iter(["1", "5", "2", "1", "4"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        result = CliRunner().invoke(classify, ["--i-acknowledge-uncertainty"])
        assert result.exit_code == 0
        # Check JSON output for exact article strings (avoids terminal encoding issues)
        out_json = None
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_json = Path(f.name)
        try:
            inputs2 = iter(["1", "5", "2", "1", "4"])
            monkeypatch.setattr("builtins.input", lambda _: next(inputs2))
            CliRunner().invoke(
                classify, ["--i-acknowledge-uncertainty", "--output", str(out_json)]
            )
            data = json.loads(out_json.read_text(encoding="utf-8"))
            articles = data["risk_profile"]["articles"]
            assert any("6(2)" in a for a in articles)
            assert any("4" in a for a in articles)
            assert (
                data["risk_profile"]["conformity_route"] == "internal_control_annex_vi"
            )
            assert data["risk_profile"]["notified_body_required"] is False
        finally:
            os.unlink(out_json)

    def test_not_legal_advice_disclaimer_shown(self, monkeypatch):
        inputs = iter(["1", "5", "2", "2", "2", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        result = CliRunner().invoke(classify, ["--i-acknowledge-uncertainty"])
        assert (
            "not legal" in result.output.lower() or "Not legal advice" in result.output
        )
