# Changelog

All notable changes to annex4-cli are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — Unreleased

### PR#1 — Regulation pack architecture
- Versioned regulation data pack under `annex4/regulation/versions/2024-1689_base/`
- SHA-256 content hash validation on every load (`RegulationHashMismatch` on mismatch)
- `annex4 regulation list` and `annex4 regulation show` commands
- Pydantic-validated models for articles, annexes, recitals, classifier spec

### PR#2 — Core schema: legal firewall
- `SystemMetadata` (machine fact + `Provenance`) and `ComplianceClaim` (human attestation) discriminated union
- Five-tier validation — `ERROR`, `LEGAL_GAP`, `INCONSISTENCY`, `WARNING`, `ASSUMPTION`, `INFO`
- Codes E001–E023, W002–W016, I003–I005 with Annex IV and Article citations
- `field_kinds.yaml` — `claim_required` list enforces `LG001` legal gap

### PR#3 — Classifier → RiskProfile
- `classify` requires `--i-acknowledge-uncertainty` flag (exit 2 without it)
- Returns structured `RiskProfile`: `path_id`, `articles`, `conformity_route`, `notified_body_required`
- `--system FILE` non-interactive mode
- Corrected Annex III §4(a) employment: internal control (Annex VI), no notified body required by default
- Fixed multiple-choice `is_not_selected` logic in `_get_next_node`

### PR#4 — Ingestors + evidence bundle
- All ingestors emit `SystemMetadata` dicts with full `Provenance` (source, source_ref, extracted_at, confidence)
- Merge conflict resolution: newer `provenance.extracted_at` wins; `conflict_resolved: True` flagged
- `annex4 bundle create DOSSIER --output bundle.zip` — canonical SHA-256 manifest
- `annex4 bundle verify bundle.zip` — tamper detection

### PR#5 — Disclaimer hardening (§1a)
- `annex4/cli/` package; `cli/disclaimer.py` — `print_cli_disclaimer()`, `FULL_DISCLAIMER`, `DisclaimerRequiredError`
- `_AnnexGroup` prints short disclaimer to STDERR before every subcommand
- `annex4 legal` command — full disclaimer + regulation pack version
- `render --no-disclaimer` raises `DisclaimerRequiredError` — cannot be bypassed
- HTML: `<meta>` disclaimer, title ends `"not legal advice"`, `@page` footer, provenance table in Appendix B
- `LEGAL.md` (9 sections), `CODE_OF_CONDUCT.md`, `SECURITY.md`
- `README.md` — disclaimer in first 500 chars (§1a.2)
- `pyproject.toml` — "not legal advice" in description, keywords, classifiers (§1a.3)
- 22 hardening tests in `test_disclaimer_hardening.py`

### PR#6 — Change Impact Report
- `annex4 diff` — changes grouped by Annex IV section; per-entry article citations
- `DiffReport.substantiality_factors` — 7-item Article 43(4) checklist (F1–F7); `triggered: bool`
- `--output FILE` flag for markdown, html, json formats
- Final sentence in every report: *"This report is informational. A determination of substantiality under Article 43(4) is a legal judgment requiring human review."*
- Integration test: `training_sources` change flags Article 10 + F2 factor
- Three complete reference dossiers: `hr_screening.yaml` (Annex III §4(a)), `credit_scoring.yaml` (§5(b)), `medical_triage.yaml` (MDR Class IIa)

### Quality gate
- 316 tests, all green
- Coverage 90% (gate: ≥80%)
- `ruff check annex4/` — 0 errors

[0.1.0]: https://github.com/jer/annex4-cli/releases/tag/v0.1.0
