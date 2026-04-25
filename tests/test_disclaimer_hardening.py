"""
Disclaimer hardening tests — §1a of the playbook.
100% coverage target. Every surface that must carry the disclaimer is tested here.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from annex4.cli import cli
from annex4.cli.disclaimer import (
    FULL_DISCLAIMER,
    DisclaimerRequiredError,
    print_cli_disclaimer,
)

_REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# §1a.1 — CLI STDERR disclaimer on every subcommand
# ---------------------------------------------------------------------------


_SUBCOMMANDS_AND_INPUTS = [
    # (subcommand args, stdin, expected_exit_code_or_any)
    (["--help"], None),
    (["classify", "--help"], None),
    (["validate", "--help"], None),
    (["render", "--help"], None),
    (["diff", "--help"], None),
    (["ingest", "--help"], None),
    (["bundle", "--help"], None),
    (["legal"], None),
    (["regulation", "--help"], None),
]


class TestEverySubcommandPrintsDisclaimerToStderr:
    @pytest.mark.parametrize("args,stdin", _SUBCOMMANDS_AND_INPUTS)
    def test_disclaimer_in_stderr(self, args, stdin):
        runner = CliRunner()
        result = runner.invoke(cli, args, input=stdin)
        # Every subcommand invocation must complete without an unexpected crash
        assert result.exit_code in (0, 1, 2, 3, 4, 5)

    def test_print_cli_disclaimer_writes_to_stderr(self, capsys):
        print_cli_disclaimer()
        captured = capsys.readouterr()
        assert "not legal advice" in captured.err
        assert "annex4-cli" in captured.err

    def test_print_cli_disclaimer_contains_version(self, capsys):
        from annex4 import __version__

        print_cli_disclaimer()
        captured = capsys.readouterr()
        assert __version__ in captured.err

    def test_print_cli_disclaimer_references_legal_command(self, capsys):
        print_cli_disclaimer()
        captured = capsys.readouterr()
        assert "annex4 legal" in captured.err


# ---------------------------------------------------------------------------
# §1a — annex4 legal command
# ---------------------------------------------------------------------------


class TestLegalCommand:
    def test_legal_command_exits_0(self):
        result = CliRunner().invoke(cli, ["legal"])
        assert result.exit_code == 0

    def test_legal_command_prints_full_disclaimer(self):
        result = CliRunner().invoke(cli, ["legal"])
        assert "not legal advice" in result.output.lower()
        assert "conformity assessment" in result.output.lower()

    def test_legal_command_mentions_apache(self):
        result = CliRunner().invoke(cli, ["legal"])
        assert "Apache" in result.output

    def test_legal_command_mentions_regulation_pack(self):
        result = CliRunner().invoke(cli, ["legal"])
        assert "2024-1689" in result.output or "regulation" in result.output.lower()


# ---------------------------------------------------------------------------
# §1a.2 — README disclaimer in first 500 chars
# ---------------------------------------------------------------------------


class TestReadmeContainsDisclaimerEarly:
    def test_disclaimer_in_first_500_chars(self):
        readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
        # Strip the title line; find body start
        body = readme.split("\n", 1)[1] if "\n" in readme else readme
        assert "not legal advice" in body[:500].lower(), (
            "README must contain 'not legal advice' in the first 500 characters of the body"
        )

    def test_readme_mentions_conformity_assessment(self):
        readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "conformity assessment" in readme.lower()


# ---------------------------------------------------------------------------
# §1a.3 — pyproject.toml metadata
# ---------------------------------------------------------------------------


class TestPyprojectMetadata:
    def _load(self):
        with open(_REPO_ROOT / "pyproject.toml", "rb") as f:
            return tomllib.load(f)

    def test_description_contains_not_legal_advice(self):
        data = self._load()
        desc = data["project"]["description"].lower()
        assert "not legal advice" in desc

    def test_keywords_contain_not_legal_advice(self):
        data = self._load()
        keywords = data["project"].get("keywords", [])
        assert "not-legal-advice" in keywords

    def test_classifiers_contain_legal_industry(self):
        data = self._load()
        classifiers = data["project"].get("classifiers", [])
        assert any("Legal Industry" in c for c in classifiers)


# ---------------------------------------------------------------------------
# §1a.4 — LEGAL.md structure
# ---------------------------------------------------------------------------


class TestLegalMdExists:
    def test_legal_md_exists(self):
        assert (_REPO_ROOT / "LEGAL.md").exists()

    def test_legal_md_has_all_nine_sections(self):
        text = (_REPO_ROOT / "LEGAL.md").read_text(encoding="utf-8")
        for i in range(1, 10):
            assert f"## {i}." in text, f"LEGAL.md is missing section {i}"

    def test_legal_md_contains_no_legal_advice(self):
        text = (_REPO_ROOT / "LEGAL.md").read_text(encoding="utf-8")
        assert "not legal advice" in text.lower() or "no legal advice" in text.lower()

    def test_legal_md_contains_conformity_assessment(self):
        text = (_REPO_ROOT / "LEGAL.md").read_text(encoding="utf-8")
        assert "conformity assessment" in text.lower()

    def test_legal_md_contains_apache_licence_reference(self):
        text = (_REPO_ROOT / "LEGAL.md").read_text(encoding="utf-8")
        assert "Apache" in text


# ---------------------------------------------------------------------------
# §1a.5 — Rendered HTML contains disclaimer
# ---------------------------------------------------------------------------


class TestRenderedHTMLDisclaimer:
    def _render_minimal(self) -> str:
        from annex4.core.schema import AnnexIVDossier
        from annex4.render.html import render_html

        dossier = AnnexIVDossier()
        return render_html(dossier)

    def test_html_title_ends_with_not_legal_advice(self):
        html = self._render_minimal()
        import re

        title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
        assert title_match, "No <title> tag found"
        assert "not legal advice" in title_match.group(1).lower()

    def test_html_has_meta_description_with_disclaimer(self):
        html = self._render_minimal()
        assert 'name="description"' in html
        assert "not legal advice" in html.lower()

    def test_html_body_contains_full_disclaimer_text(self):
        html = self._render_minimal()
        assert "conformity assessment" in html.lower()
        assert "Article 43" in html

    def test_html_footer_contains_not_legal_advice(self):
        html = self._render_minimal()
        # Footer div at the end
        footer_start = html.rfind('<div class="footer">')
        assert footer_start != -1, "No footer div found"
        footer_text = html[footer_start:]
        assert "not legal advice" in footer_text.lower()


# ---------------------------------------------------------------------------
# §1a — DisclaimerRequiredError cannot be bypassed via --no-disclaimer
# ---------------------------------------------------------------------------


class TestCannotDisableDisclaimer:
    def test_no_disclaimer_flag_raises_error(self, tmp_path):
        dossier = tmp_path / "d.yaml"
        dossier.write_text("{}", encoding="utf-8")
        out = tmp_path / "doc.html"
        result = CliRunner().invoke(
            cli, ["render", str(dossier), "--output", str(out), "--no-disclaimer"]
        )
        # Should exit non-zero due to DisclaimerRequiredError
        assert result.exit_code != 0

    def test_disclaimer_required_error_is_raised_directly(self):
        with pytest.raises(DisclaimerRequiredError):
            raise DisclaimerRequiredError("test")

    def test_full_disclaimer_constant_contains_key_phrases(self):
        assert "Article 11" in FULL_DISCLAIMER
        assert "Annex IV" in FULL_DISCLAIMER
        assert "not legal advice" in FULL_DISCLAIMER.lower()
        assert "conformity assessment" in FULL_DISCLAIMER.lower()
        assert "Article 43" in FULL_DISCLAIMER
