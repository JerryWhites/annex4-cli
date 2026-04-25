"""
Evidence bundle engine.

A bundle is a ZIP file containing:
  dossier.yaml                   — the source dossier
  evidence/<filename>            — files referenced in ComplianceClaim.evidence_refs
  manifest.json                  — canonical SHA-256 manifest of every file in the bundle

The manifest is canonically serialised: UTF-8, sorted keys, no floats (all
numeric values are strings or integers).  This makes it stable for signing
(PR#7) and for byte-for-byte comparison in CI.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from annex4.core.schema import AnnexIVDossier, ComplianceClaim


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _collect_evidence_refs(dossier: AnnexIVDossier) -> List[str]:
    """Walk every ComplianceClaim in the dossier and collect evidence_refs."""
    refs: List[str] = []

    def _walk(obj: Any) -> None:
        if isinstance(obj, ComplianceClaim):
            refs.extend(obj.evidence_refs or [])
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
        elif hasattr(obj, "__dict__"):
            for val in vars(obj).values():
                _walk(val)

    _walk(dossier)
    return list(dict.fromkeys(refs))  # deduplicate, preserve order


def _canonical_manifest(entries: Dict[str, str], created_at: str) -> bytes:
    """Produce a canonical JSON manifest (sorted keys, UTF-8, no trailing newline)."""
    payload = {
        "bundle_version": "1",
        "created_at": created_at,
        "files": dict(sorted(entries.items())),
    }
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_bundle(
    dossier_path: Path,
    output_path: Path,
    base_dir: Optional[Path] = None,
) -> Dict[str, str]:
    """Create an evidence bundle ZIP and return the manifest entries dict.

    Args:
        dossier_path: Path to the filled dossier YAML.
        output_path:  Destination .zip path.
        base_dir:     Root directory for resolving relative evidence_refs.
                      Defaults to the directory containing dossier_path.

    Returns:
        The manifest entries dict {archive_path: sha256_hex}.
    """
    base_dir = base_dir or dossier_path.parent

    with open(dossier_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    dossier = AnnexIVDossier.from_yaml_dict(raw)

    evidence_refs = _collect_evidence_refs(dossier)
    created_at = datetime.now(timezone.utc).isoformat()
    manifest_entries: Dict[str, str] = {}

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Dossier YAML
        dossier_bytes = dossier_path.read_bytes()
        zf.writestr("dossier.yaml", dossier_bytes)
        manifest_entries["dossier.yaml"] = _sha256(dossier_bytes)

        # 2. Evidence files
        missing: List[str] = []
        for ref in evidence_refs:
            ref_path = Path(ref) if Path(ref).is_absolute() else base_dir / ref
            if not ref_path.exists():
                missing.append(ref)
                continue
            archive_name = "evidence/" + ref_path.name
            data = ref_path.read_bytes()
            zf.writestr(archive_name, data)
            manifest_entries[archive_name] = _sha256(data)

        if missing:
            import warnings

            warnings.warn(
                f"Bundle created but {len(missing)} evidence file(s) not found: {missing}",
                stacklevel=2,
            )

        # 3. Manifest (computed last so it covers all files above)
        manifest_bytes = _canonical_manifest(manifest_entries, created_at)
        zf.writestr("manifest.json", manifest_bytes)

    return manifest_entries


def verify_bundle(bundle_path: Path) -> Dict[str, Any]:
    """Verify a bundle's manifest against the actual file hashes.

    Returns:
        {"ok": True, "checked": N}  on success
        {"ok": False, "failures": [...]}  on mismatch
    """
    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            return {"ok": False, "failures": ["manifest.json not found in bundle"]}

        manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
        expected = manifest_data.get("files", {})

        failures: List[str] = []
        for archive_path, expected_hash in expected.items():
            if archive_path not in names:
                failures.append(f"MISSING: {archive_path}")
                continue
            actual_hash = _sha256(zf.read(archive_path))
            if actual_hash != expected_hash:
                failures.append(
                    f"HASH MISMATCH: {archive_path}\n"
                    f"  expected: {expected_hash}\n"
                    f"  actual:   {actual_hash}"
                )

    if failures:
        return {"ok": False, "failures": failures}
    return {"ok": True, "checked": len(expected)}
