# annex4-cli

> ⚠️ **Informational tool — not legal advice.**
> annex4-cli helps you structure, validate, and render Annex IV documentation.
> It does **not** perform conformity assessment, does **not** replace a
> Notified Body assessment where Article 43 requires one, and does **not**
> replace consultation with qualified legal counsel. Responsibility for
> regulatory compliance remains fully with the provider of the AI system.
> See [LEGAL.md](LEGAL.md) for the full notice.

[![CI](https://github.com/JerryWhites/annex4-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/JerryWhites/annex4-cli/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](https://github.com/JerryWhites/annex4-cli)
[![PyPI](https://img.shields.io/pypi/v/annex4-cli)](https://pypi.org/project/annex4-cli/)
[![Python](https://img.shields.io/pypi/pyversions/annex4-cli)](https://pypi.org/project/annex4-cli/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Disclaimer](https://img.shields.io/badge/disclaimer-not%20legal%20advice-red)](LEGAL.md)

**Your AI model is in production. Your lawyer just emailed about the EU AI Act.**

annex4-cli turns Annex IV compliance documentation from a legal fire-drill into a YAML file in your Git repo — validated, versioned, and rendered in under 10 minutes.

![annex4-cli demo: classify → validate → render → diff in under 60 seconds](docs/demo.png)

> _Demo: full Annex IV documentation workflow on the
> [hr_screening reference dossier](examples/hr_screening.yaml)._

---

## The problem

The EU AI Act (Regulation (EU) 2024/1689) requires providers of high-risk AI systems to maintain **Annex IV technical documentation** — nine sections covering everything from your training data governance to your post-market monitoring plan. It must be kept current across every material model update.

Most teams handle this with a shared Google Doc that's immediately out of date. annex4-cli fixes that.

---

## Install

```bash
pip install annex4-cli
annex4 --help
```

---

## 10-minute demo

```bash
# Step 1: Find out where your system sits in the regulation
annex4 classify --i-acknowledge-uncertainty
# → Structured RiskProfile: verdict, Article citations, conformity route, notified body required?

# Step 2: Validate your dossier against all 9 Annex IV sections
annex4 validate examples/hr_screening.yaml
# → Colour-coded: ERRORs (blockers), LEGAL_GAPs (missing attestations), WARNINGs, INFOs

# Step 3: Render a complete Annex IV document
annex4 render examples/hr_screening.yaml --output dossier.pdf
# → Self-contained PDF with cover page, provenance table, all 9 sections, mandatory disclaimer

# Step 4: Ship a model update — find out what changed under Article 43(4)
annex4 diff v1.yaml v2.yaml --format markdown
# → Change Impact Report grouped by Annex IV section, substantiality checklist, exit code 2 if re-assessment required
```

The full workflow from zero to a rendered Annex IV document: **under 10 minutes.**

---

## What makes it different

**Most compliance tools are one-shot PDF exporters.** annex4-cli is designed to live in your Git repo alongside your model — it evolves as your system evolves.

### Every field knows where it came from

Pull metadata straight from your MLOps stack:

```bash
annex4 ingest --mlflow-run abc123 --output dossier.yaml
annex4 ingest --hf-model org/my-model --output dossier.yaml
annex4 ingest --mlflow-run abc123 --override legal_review.yaml --output dossier.yaml
```

Every ingested value carries full provenance:

```yaml
training_data_size:
  kind: system_metadata
  value: 2400000
  provenance:
    source: mlflow
    source_ref: "run/abc123"
    extracted_at: "2026-03-01T14:22:00Z"
    extractor_version: "1.2.0"
    confidence: 0.99
```

**Supported ingestors:** MLflow · HuggingFace Hub · Giskard scan results · YAML overrides

**Stubs (contributions welcome):** Azure ML · Databricks · SageMaker · Vertex AI

### A legal firewall baked into the schema

The tool enforces a hard distinction between what a machine can assert and what only a human can:

| Type | What it means | Example |
|------|--------------|---------|
| `SystemMetadata` | Machine-extracted fact with provenance | training set size from MLflow |
| `ComplianceClaim` | Human attestation with citation | "Data governance policy meets Article 10(2)(f)" |

The tool **never signs for you.** Fields that require a human statement (`human_oversight_measures`, `bias_analysis`, etc.) will raise a `LEGAL_GAP` if they're missing a `ComplianceClaim`.

### Version your model updates like code

```bash
annex4 diff v2.2.4.yaml v2.3.1.yaml --format markdown --output change_report.md
```

```
## Annex IV §2 — Development process
| Field | Change | Substantiality |
|-------|--------|----------------|
| development_process.data_governance.training_sources | modified | SUBSTANTIAL |

### Article 43(4) Substantiality Checklist
- [x] F2 — Change to training, validation, or testing data (Article 10)
- [ ] F3 — Change to model architecture or core algorithm

⚠ Substantial changes detected. Conformity re-assessment required.
```

Exit codes are CI-friendly:

| Code | Meaning |
|------|---------|
| `0` | No changes |
| `1` | Non-substantial changes |
| `2` | **Substantial — re-assessment required** |
| `3` | Ambiguous — human review required |

### Tamper-evident evidence bundles

```bash
annex4 bundle create dossier.yaml --output submission.zip
# → dossier.yaml + evidence files + SHA-256 manifest

annex4 bundle verify submission.zip
# → ✓ Bundle verified: 7 file(s) intact.  (or exit 1 on tamper)
```

### No LLM. No cloud. No surprises.

Deterministic, regulation-aware logic only. Nothing leaves your machine in default mode. The regulation itself lives as versioned data — when delegated acts update the requirements, you get a new regulation pack, not a new engine.

---

## Reference dossiers

Three real-world examples in [`examples/`](examples/), all validating clean:

| File | System | Risk path |
|------|--------|-----------|
| `hr_screening.yaml` | CV screening — TalentFlow ScreenAI | Annex III §4(a), Article 6(2), internal control |
| `credit_scoring.yaml` | Credit scoring — CreditSense Pro | Annex III §5(b), Article 6(2) |
| `medical_triage.yaml` | Medical triage — MedTriage Assist | Article 6(1), MDR Class IIa, Notified Body required |

Pre-rendered HTML versions are in [`examples/rendered/`](examples/rendered/).

---

## All commands

```
annex4 classify   --i-acknowledge-uncertainty    # risk classification
annex4 validate   dossier.yaml                  # Annex IV gap analysis
annex4 render     dossier.yaml --output doc.pdf # generate document (md / html / pdf)
annex4 diff       v1.yaml v2.yaml               # Change Impact Report
annex4 ingest     --mlflow-run ID               # pull from MLflow / HF / Giskard
annex4 bundle     create dossier.yaml -o b.zip  # SHA-256 evidence bundle
annex4 bundle     verify bundle.zip             # tamper detection
annex4 init       --output dossier.yaml         # scaffold a new dossier
annex4 legal                                    # print full disclaimer
annex4 regulation list / show / search          # inspect regulation data
```

---

## Legal

annex4-cli is an informational tool. It does not perform conformity assessment, does not constitute legal advice, and does not replace a Notified Body assessment where Article 43 requires one. See [LEGAL.md](LEGAL.md) for the full notice.

Run `annex4 legal` to print the disclaimer from the CLI at any time.

Apache-2.0 © 2026 Jerry Whites

---

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). DCO sign-off required. The pytest + ruff + mypy gate must pass.
