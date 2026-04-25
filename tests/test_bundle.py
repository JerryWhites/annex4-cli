"""Tests for annex4.bundle.engine and the annex4 bundle CLI commands."""

import json
import zipfile
from pathlib import Path

import yaml
from click.testing import CliRunner

from annex4.bundle.engine import (
    create_bundle,
    verify_bundle,
    _sha256,
    _canonical_manifest,
)
from annex4.cli import cli


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_minimal_dossier(path: Path) -> None:
    """Write a valid dossier YAML with no evidence_refs (no ComplianceClaims)."""
    dossier = {
        "general_description": {
            "provider": {"name": "Acme AI GmbH"},
            "system": {
                "name": "TestSys",
                "version": "1.0",
                "regulation_version": "2024-1689_base",
            },
        }
    }
    path.write_text(yaml.dump(dossier, allow_unicode=True), encoding="utf-8")


def _write_dossier_with_evidence(path: Path, evidence_files: list[Path]) -> None:
    """Write a dossier YAML with ComplianceClaims that reference evidence files."""
    dossier = {
        "general_description": {
            "provider": {
                "authorized_signatory": {
                    "kind": "compliance_claim",
                    "statement": "Jane Smith, CTO",
                    "attested_by": "Board",
                    "attested_at": "2026-01-15",
                    "evidence_refs": [str(f) for f in evidence_files],
                }
            },
            "system": {
                "name": "TestSys",
                "regulation_version": "2024-1689_base",
            },
        }
    }
    path.write_text(yaml.dump(dossier, allow_unicode=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# _sha256 helper
# ---------------------------------------------------------------------------


class TestSha256Helper:
    def test_format(self):
        h = _sha256(b"hello")
        assert h.startswith("sha256:")
        assert len(h) == 7 + 64  # "sha256:" + 64 hex chars

    def test_deterministic(self):
        assert _sha256(b"test") == _sha256(b"test")

    def test_different_data(self):
        assert _sha256(b"a") != _sha256(b"b")


# ---------------------------------------------------------------------------
# _canonical_manifest
# ---------------------------------------------------------------------------


class TestCanonicalManifest:
    def test_is_valid_json(self):
        data = _canonical_manifest(
            {"b.txt": "sha256:abc", "a.txt": "sha256:def"}, "2026-01-01T00:00:00"
        )
        parsed = json.loads(data)
        assert parsed["bundle_version"] == "1"
        assert "files" in parsed

    def test_files_keys_are_sorted(self):
        data = _canonical_manifest(
            {"z.txt": "h1", "a.txt": "h2"}, "2026-01-01T00:00:00"
        )
        parsed = json.loads(data)
        keys = list(parsed["files"].keys())
        assert keys == sorted(keys)

    def test_utf8_encoded(self):
        data = _canonical_manifest({}, "2026-01-01")
        assert isinstance(data, bytes)
        data.decode("utf-8")  # must not raise


# ---------------------------------------------------------------------------
# create_bundle
# ---------------------------------------------------------------------------


class TestCreateBundle:
    def test_creates_zip_file(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)
        assert out.exists()
        assert zipfile.is_zipfile(out)

    def test_bundle_contains_dossier_and_manifest(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert "dossier.yaml" in names
        assert "manifest.json" in names

    def test_manifest_json_is_valid(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)
        with zipfile.ZipFile(out) as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["bundle_version"] == "1"
        assert "dossier.yaml" in manifest["files"]
        assert manifest["files"]["dossier.yaml"].startswith("sha256:")

    def test_evidence_files_included_when_present(self, tmp_path):
        ev = tmp_path / "report.pdf"
        ev.write_bytes(b"%PDF fake")
        dossier = tmp_path / "dossier.yaml"
        _write_dossier_with_evidence(dossier, [ev])
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert any("report.pdf" in n for n in names)

    def test_returns_manifest_entries_dict(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        manifest = create_bundle(dossier, out)
        assert "dossier.yaml" in manifest
        assert all(v.startswith("sha256:") for v in manifest.values())

    def test_manifest_files_keys_are_sorted(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)
        with zipfile.ZipFile(out) as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        keys = list(manifest["files"].keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# verify_bundle
# ---------------------------------------------------------------------------


class TestVerifyBundle:
    def test_clean_bundle_verifies_ok(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)
        result = verify_bundle(out)
        assert result["ok"] is True
        assert result["checked"] >= 1

    def test_tampered_file_detected(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)

        # Tamper: rewrite dossier.yaml in the zip with different content
        tampered = tmp_path / "tampered.zip"
        with zipfile.ZipFile(out, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "dossier.yaml":
                    data = data + b"\n# tampered"
                zout.writestr(item, data)

        result = verify_bundle(tampered)
        assert result["ok"] is False
        assert any("dossier.yaml" in f for f in result["failures"])

    def test_missing_manifest_returns_error(self, tmp_path):
        bad_zip = tmp_path / "bad.zip"
        with zipfile.ZipFile(bad_zip, "w") as zf:
            zf.writestr("dossier.yaml", b"content")
        result = verify_bundle(bad_zip)
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# CLI: annex4 bundle create / verify
# ---------------------------------------------------------------------------


class TestBundleCLI:
    def test_bundle_create_exits_0(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        result = CliRunner().invoke(
            cli, ["bundle", "create", str(dossier), "--output", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_bundle_create_output_mentions_file_count(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        result = CliRunner().invoke(
            cli, ["bundle", "create", str(dossier), "--output", str(out)]
        )
        assert "file" in result.output.lower()

    def test_bundle_verify_clean_exits_0(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)
        result = CliRunner().invoke(cli, ["bundle", "verify", str(out)])
        assert result.exit_code == 0, result.output
        assert "verified" in result.output.lower()

    def test_bundle_verify_tampered_exits_1(self, tmp_path):
        dossier = tmp_path / "dossier.yaml"
        _write_minimal_dossier(dossier)
        out = tmp_path / "bundle.zip"
        create_bundle(dossier, out)

        tampered = tmp_path / "tampered.zip"
        with zipfile.ZipFile(out, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "dossier.yaml":
                    data = data + b"\n# tampered"
                zout.writestr(item, data)

        result = CliRunner().invoke(cli, ["bundle", "verify", str(tampered)])
        assert result.exit_code == 1

    def test_bundle_help_shown(self):
        result = CliRunner().invoke(cli, ["bundle", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "verify" in result.output
