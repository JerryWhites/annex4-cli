import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from annex4.cli import cli
from annex4.core.schema import (
    AnnexIVDossier,
    SystemMetadata,
    ComplianceClaim,
    Provenance,
)
from annex4.core.diff import (
    diff_dossiers,
    traverse_dict,
    get_substantiality,
    _flatten_fields,
    _field_str,
    _path_section,
    _compute_factors,
)


def _prov() -> Provenance:
    return Provenance(
        source="manual",
        source_ref="test",
        extracted_at="2026-01-01",
        extractor_version="1.0",
        confidence=1.0,
    )


@pytest.fixture
def base_dossier():
    return AnnexIVDossier.from_yaml_dict(
        {
            "general_description": {
                "system": {
                    "classification": "Low Risk",
                    "regulation_version": "2024-1689_base",
                },
                "intended_purpose": {"description": "Old purpose"},
            }
        }
    )


@pytest.fixture
def new_dossier():
    return AnnexIVDossier.from_yaml_dict(
        {
            "general_description": {
                "system": {
                    "classification": "High Risk",
                    "regulation_version": "2024-1689_base",
                },
                "intended_purpose": {"description": "New purpose"},
            }
        }
    )


@pytest.fixture
def diff_rules():
    return {
        "general_description.system.classification": "substantial",
        "general_description.intended_purpose.description": "non_substantial",
    }


def test_flatten_fields_system_metadata():
    d = {
        "kind": "system_metadata",
        "value": "Low Risk",
        "provenance": {"source": "manual"},
    }
    assert _flatten_fields(d) == "Low Risk"


def test_flatten_fields_compliance_claim():
    d = {"kind": "compliance_claim", "statement": "We attest", "attested_by": "CTO"}
    assert _flatten_fields(d) == "We attest"


def test_flatten_fields_nested_dict():
    d = {
        "system": {
            "classification": {
                "kind": "system_metadata",
                "value": "High Risk",
                "provenance": {},
            },
            "version": {"kind": "compliance_claim", "statement": "1.0.0"},
        }
    }
    result = _flatten_fields(d)
    assert result["system"]["classification"] == "High Risk"
    assert result["system"]["version"] == "1.0.0"


def test_flatten_fields_list():
    d = [{"kind": "system_metadata", "value": "a"}, "plain", 42]
    assert _flatten_fields(d) == ["a", "plain", 42]


def test_flatten_fields_passthrough():
    assert _flatten_fields("hello") == "hello"
    assert _flatten_fields(42) == 42
    assert _flatten_fields(None) is None


def test_field_str_none():
    assert _field_str(None) is None


def test_field_str_plain_string():
    assert _field_str("2024-1689_base") == "2024-1689_base"


def test_field_str_system_metadata():
    sm = SystemMetadata(value="1.0.0", provenance=_prov())
    assert _field_str(sm) == "1.0.0"


def test_field_str_compliance_claim():
    cc = ComplianceClaim(
        statement="Attested",
        attested_by="CTO",
        attested_at="2026-01-01",
        evidence_refs=[],
    )
    assert _field_str(cc) == "Attested"


def test_diff_with_system_metadata_fields(diff_rules):
    """Dossiers with SystemMetadata-wrapped fields should diff on extracted values."""
    old = AnnexIVDossier.from_yaml_dict(
        {
            "general_description": {
                "system": {
                    "classification": {
                        "kind": "system_metadata",
                        "value": "Low Risk",
                        "provenance": {
                            "source": "manual",
                            "source_ref": "test",
                            "extracted_at": "2026-01-01",
                            "extractor_version": "1.0",
                            "confidence": 1.0,
                        },
                    },
                    "regulation_version": "2024-1689_base",
                }
            }
        }
    )
    new = AnnexIVDossier.from_yaml_dict(
        {
            "general_description": {
                "system": {
                    "classification": {
                        "kind": "system_metadata",
                        "value": "High Risk",
                        "provenance": {
                            "source": "manual",
                            "source_ref": "test",
                            "extracted_at": "2026-01-01",
                            "extractor_version": "1.0",
                            "confidence": 1.0,
                        },
                    },
                    "regulation_version": "2024-1689_base",
                }
            }
        }
    )
    report = diff_dossiers(old, new, diff_rules)
    entries = {e.path: e for e in report.entries}
    assert "general_description.system.classification" in entries
    entry = entries["general_description.system.classification"]
    assert entry.old_value == "Low Risk"
    assert entry.new_value == "High Risk"
    assert entry.substantiality == "substantial"
    assert report.has_substantial_changes is True


def test_traverse_dict():
    d = {"a": 1, "b": {"c": [1, {"d": 2}]}}
    flat = traverse_dict(d)
    assert flat["a"] == 1
    assert flat["b.c[0]"] == 1
    assert flat["b.c[1].d"] == 2


def test_get_substantiality(diff_rules):
    assert (
        get_substantiality("general_description.system.classification", diff_rules)
        == "substantial"
    )
    assert get_substantiality("b.c[1].d", diff_rules) == "unknown"


def test_diff_dossiers(base_dossier, new_dossier, diff_rules):
    report = diff_dossiers(base_dossier, new_dossier, diff_rules)
    assert len(report.entries) == 2
    assert report.has_substantial_changes is True
    assert report.regulation_version_changed is False

    entries = {e.path: e for e in report.entries}
    assert entries["general_description.system.classification"].kind == "modified"
    assert (
        entries["general_description.system.classification"].substantiality
        == "substantial"
    )
    assert entries["general_description.system.classification"].new_value == "High Risk"

    assert (
        entries["general_description.intended_purpose.description"].kind == "modified"
    )
    assert (
        entries["general_description.intended_purpose.description"].substantiality
        == "non_substantial"
    )
    assert (
        entries["general_description.intended_purpose.description"].new_value
        == "New purpose"
    )


def test_cli_diff_subcommand(tmp_path):
    old_file = tmp_path / "old.yaml"
    new_file = tmp_path / "new.yaml"

    old_file.write_text("""
general_description:
  system:
    classification: "Low"
    regulation_version: "2024-1689_base"
""")
    new_file.write_text("""
general_description:
  system:
    classification: "High"
    regulation_version: "2024-1689_base"
""")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["diff", str(old_file), str(new_file), "--format", "json"]
    )
    assert (
        result.exit_code == 2
    )  # Has substantial changes based on diff_substantiality.yaml
    assert "High" in result.output

    result2 = runner.invoke(
        cli, ["diff", str(old_file), str(new_file), "--format", "markdown"]
    )
    assert result2.exit_code == 2
    # New template: columns are Field | Change | Substantiality | Old value | New value
    assert "general_description.system.classification" in result2.output
    assert "substantial" in result2.output
    assert "Article 43(4)" in result2.output  # appears in the checklist section

    result_cli = runner.invoke(
        cli, ["diff", str(old_file), str(new_file), "--format", "cli"]
    )
    assert result_cli.exit_code == 2

    result_html = runner.invoke(
        cli, ["diff", str(old_file), str(new_file), "--format", "html"]
    )
    assert result_html.exit_code == 2


def test_diff_identical_dossier(tmp_path: Path) -> None:
    """Diffing a dossier against itself produces no entries and exit code 0."""
    same = tmp_path / "same.yaml"
    same.write_text(
        textwrap.dedent("""\
        general_description:
          system:
            classification: "High Risk"
            regulation_version: "2024-1689_base"
        """)
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", str(same), str(same), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["entries"] == []


def test_diff_exit_code_1_non_substantial_only(tmp_path: Path) -> None:
    """Only non-substantial changes → exit code 1."""
    v1 = tmp_path / "v1.yaml"
    v2 = tmp_path / "v2.yaml"
    v1.write_text(
        textwrap.dedent("""\
        general_description:
          system:
            regulation_version: "2024-1689_base"
        monitoring_functioning_control:
          accuracy_metrics:
            - name: "Balanced Accuracy"
              aggregate_value: "0.80"
        """)
    )
    v2.write_text(
        textwrap.dedent("""\
        general_description:
          system:
            regulation_version: "2024-1689_base"
        monitoring_functioning_control:
          accuracy_metrics:
            - name: "Balanced Accuracy"
              aggregate_value: "0.85"
        """)
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", str(v1), str(v2), "--format", "json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert not data["has_substantial_changes"]
    assert all(e["substantiality"] != "substantial" for e in data["entries"])


def test_diff_exit_code_3_ambiguous(tmp_path: Path) -> None:
    """Ambiguous changes (and no substantial) → exit code 3."""
    v1 = tmp_path / "v1.yaml"
    v2 = tmp_path / "v2.yaml"
    v1.write_text(
        textwrap.dedent("""\
        general_description:
          system:
            regulation_version: "2024-1689_base"
          intended_purpose:
            deployment_form: "SaaS"
        """)
    )
    v2.write_text(
        textwrap.dedent("""\
        general_description:
          system:
            regulation_version: "2024-1689_base"
          intended_purpose:
            deployment_form: "On-premise"
        """)
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", str(v1), str(v2), "--format", "json"])
    assert result.exit_code == 3
    data = json.loads(result.output)
    assert not data["has_substantial_changes"]
    assert any(e["substantiality"] == "ambiguous" for e in data["entries"])


def test_diff_regulation_version_changed_banner(tmp_path: Path) -> None:
    """Different regulation versions surface regulation_version_changed flag and markdown banner."""
    v1 = tmp_path / "v1.yaml"
    v2 = tmp_path / "v2.yaml"
    v1.write_text(
        textwrap.dedent("""\
        general_description:
          system:
            regulation_version: "2024-1689_base"
        """)
    )
    v2.write_text(
        textwrap.dedent("""\
        general_description:
          system:
            regulation_version: "2024-1689_v1.1"
        """)
    )
    runner = CliRunner()
    result_json = runner.invoke(cli, ["diff", str(v1), str(v2), "--format", "json"])
    data = json.loads(result_json.output)
    assert data["regulation_version_changed"] is True

    result_md = runner.invoke(cli, ["diff", str(v1), str(v2), "--format", "markdown"])
    assert "regulation version changed" in result_md.output.lower()


# ---------------------------------------------------------------------------
# PR#6 — section grouping, substantiality factors, Article 10 integration
# ---------------------------------------------------------------------------


class TestPathSection:
    def test_intended_purpose_maps_to_section_1c(self):
        sec, name, arts = _path_section(
            "general_description.intended_purpose.description"
        )
        assert sec == "1c"
        assert "Article 13" in " ".join(arts) or "Annex IV" in " ".join(arts)

    def test_data_governance_maps_to_section_2b_with_article_10(self):
        sec, name, arts = _path_section(
            "development_process.data_governance.training_sources[0].name"
        )
        assert sec == "2b"
        assert any("Article 10" in a for a in arts)

    def test_accuracy_metrics_maps_to_section_3a_with_article_15(self):
        sec, name, arts = _path_section(
            "monitoring_functioning_control.accuracy_metrics[0].aggregate_value"
        )
        assert sec == "3a"
        assert any("Article 15" in a for a in arts)

    def test_risk_management_maps_to_section_4_with_article_9(self):
        sec, name, arts = _path_section("risk_management.identified_risks[0].risk")
        assert sec == "4"
        assert any("Article 9" in a for a in arts)


class TestSubstantialityFactors:
    def test_training_source_change_triggers_f2(self):
        paths = ["development_process.data_governance.training_sources[0].name"]
        factors = _compute_factors(paths)
        f2 = next(f for f in factors if f.id == "F2")
        assert f2.triggered is True

    def test_intended_purpose_change_triggers_f1(self):
        paths = ["general_description.intended_purpose.description"]
        factors = _compute_factors(paths)
        f1 = next(f for f in factors if f.id == "F1")
        assert f1.triggered is True

    def test_unrelated_change_does_not_trigger_factors(self):
        paths = ["meta.dossier_schema_version"]
        factors = _compute_factors(paths)
        assert all(not f.triggered for f in factors)

    def test_f2_cites_article_10(self):
        factors = _compute_factors(
            ["development_process.data_governance.training_sources"]
        )
        f2 = next(f for f in factors if f.id == "F2")
        assert any("Article 10" in a for a in f2.articles)


class TestDiffArticle10Integration:
    """Integration test: training_data change flags Article 10 and F2."""

    def test_training_source_change_flags_article_10_and_f2(self):
        old = AnnexIVDossier.from_yaml_dict(
            {
                "development_process": {
                    "data_governance": {
                        "training_sources": [
                            {"name": "Dataset A", "origin": "Internal"}
                        ]
                    }
                }
            }
        )
        new = AnnexIVDossier.from_yaml_dict(
            {
                "development_process": {
                    "data_governance": {
                        "training_sources": [
                            {"name": "Dataset A", "origin": "Internal"},
                            {"name": "Dataset B", "origin": "External"},
                        ]
                    }
                }
            }
        )
        report = diff_dossiers(old, new, {})

        # At least one entry in section 2b
        section_2b_entries = [e for e in report.entries if e.annex_iv_section == "2b"]
        assert len(section_2b_entries) > 0

        # Article 10 must appear in citations of those entries
        all_citations = [c for e in section_2b_entries for c in e.citations]
        assert any("Article 10" in c for c in all_citations)

        # F2 must be triggered
        f2 = next(f for f in report.substantiality_factors if f.id == "F2")
        assert f2.triggered is True

    def test_report_legal_notice_contains_article_43(self):
        from annex4.core.diff import DiffReport

        report = DiffReport(
            entries=[], has_substantial_changes=False, regulation_version_changed=False
        )
        assert "Article 43(4)" in report.LEGAL_NOTICE
        assert "legal judgment" in report.LEGAL_NOTICE


class TestDiffOutputFlag:
    def test_output_flag_writes_markdown_to_file(self, tmp_path):
        v1 = tmp_path / "v1.yaml"
        v2 = tmp_path / "v2.yaml"
        out = tmp_path / "report.md"
        v1.write_text(
            "general_description:\n  system:\n    classification: Low\n    regulation_version: '2024-1689_base'\n",
            encoding="utf-8",
        )
        v2.write_text(
            "general_description:\n  system:\n    classification: High\n    regulation_version: '2024-1689_base'\n",
            encoding="utf-8",
        )
        CliRunner().invoke(
            cli,
            ["diff", str(v1), str(v2), "--format", "markdown", "--output", str(out)],
        )
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Change Impact Report" in content
        assert "Article 43(4)" in content
        assert "A determination of substantiality" in content

    def test_output_flag_writes_json_to_file(self, tmp_path):
        v1 = tmp_path / "v1.yaml"
        v2 = tmp_path / "v2.yaml"
        out = tmp_path / "report.json"
        v1.write_text(
            "general_description:\n  system:\n    classification: Low\n    regulation_version: '2024-1689_base'\n",
            encoding="utf-8",
        )
        v2.write_text(
            "general_description:\n  system:\n    classification: High\n    regulation_version: '2024-1689_base'\n",
            encoding="utf-8",
        )
        CliRunner().invoke(
            cli, ["diff", str(v1), str(v2), "--format", "json", "--output", str(out)]
        )
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "entries" in data
        assert "substantiality_factors" in data


def test_diff_snapshot_markdown(tmp_path: Path) -> None:
    """Snapshot test: hr_screening v1→v2 markdown output is stable."""
    snapshot_path = (
        Path(__file__).parent / "fixtures" / "snapshots" / "hr_screening_diff.md"
    )
    v1_path = Path(__file__).parent.parent / "examples" / "hr_screening_v1.yaml"
    v2_path = Path(__file__).parent.parent / "examples" / "hr_screening_v2.yaml"

    runner = CliRunner()
    result = runner.invoke(
        cli, ["diff", str(v1_path), str(v2_path), "--format", "markdown"]
    )
    assert result.exit_code == 2  # substantial changes expected
    actual = result.output

    if not snapshot_path.exists():
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(actual, encoding="utf-8")
        return  # snapshot seeded; subsequent runs will compare

    expected = snapshot_path.read_text(encoding="utf-8")
    assert actual == expected, (
        "Diff markdown output changed. Delete the snapshot to regenerate:\n"
        f"  {snapshot_path}"
    )
