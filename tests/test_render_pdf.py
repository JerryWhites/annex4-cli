"""Tests for annex4.render.pdf."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from annex4.core.schema import AnnexIVDossier
from annex4.render.pdf import render_pdf


def _blank_dossier() -> AnnexIVDossier:
    return AnnexIVDossier()


# ---------------------------------------------------------------------------
# Missing dependency
# ---------------------------------------------------------------------------


class TestRenderPDFMissingWeasyprint:
    def test_raises_import_error_when_weasyprint_absent(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "weasyprint", None)
        with pytest.raises(ImportError, match="weasyprint"):
            render_pdf(_blank_dossier(), Path("out.pdf"))

    def test_error_message_mentions_install_command(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "weasyprint", None)
        with pytest.raises(ImportError, match="pip install weasyprint"):
            render_pdf(_blank_dossier(), Path("out.pdf"))


# ---------------------------------------------------------------------------
# Successful render (weasyprint mocked)
# ---------------------------------------------------------------------------


class TestRenderPDFWithMockedWeasyprint:
    def test_calls_write_pdf_with_output_path(self, tmp_path):
        mock_weasyprint = MagicMock()
        mock_html_instance = MagicMock()
        mock_weasyprint.HTML.return_value = mock_html_instance

        output_path = tmp_path / "dossier.pdf"
        with patch.dict(sys.modules, {"weasyprint": mock_weasyprint}):
            render_pdf(_blank_dossier(), output_path)

        mock_html_instance.write_pdf.assert_called_once_with(str(output_path))

    def test_html_string_passed_to_weasyprint(self, tmp_path):
        mock_weasyprint = MagicMock()
        mock_html_instance = MagicMock()
        mock_weasyprint.HTML.return_value = mock_html_instance

        with patch.dict(sys.modules, {"weasyprint": mock_weasyprint}):
            render_pdf(_blank_dossier(), tmp_path / "out.pdf")

        call_args = mock_weasyprint.HTML.call_args
        assert call_args is not None
        # HTML(string=...) uses keyword arg; fall back to positional for robustness
        html_string = call_args.kwargs.get("string")
        if html_string is None and call_args.args:
            html_string = call_args.args[0]
        assert html_string is not None
        assert "<!DOCTYPE html>" in html_string
