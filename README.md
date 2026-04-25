# annex4-cli

> Technical documentation generator for Providers of high-risk AI systems
> under Regulation (EU) 2024/1689 (EU AI Act), Article 11 and Annex IV.

> ⚠️ **This is an informational tool, not legal advice.** Annex4-cli helps you
> structure, validate, and render technical documentation. It does **not**
> perform conformity assessment, does **not** replace review by a Notified
> Body where Article 43 requires one, and does **not** replace consultation
> with a qualified legal counsel on EU AI Act matters. Responsibility for
> regulatory compliance remains fully with the provider of the AI system.

![Not Legal Advice](https://img.shields.io/badge/disclaimer-not%20legal%20advice-red)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

---

## Install

```bash
pip install annex4-cli
annex4 --help
```

## What it does

**annex4-cli** is a local-first CLI that helps AI system Providers maintain
Annex IV technical documentation across the model lifecycle — not a one-shot
PDF export, but a living compliance asset managed in Git alongside your MLOps
stack.

```
annex4 classify --i-acknowledge-uncertainty          # risk classification with Article citations
annex4 validate dossier.yaml                         # three-tier gap analysis
annex4 render   dossier.yaml --output doc.pdf        # Annex IV PDF with provenance table
annex4 diff     v1.yaml v2.yaml                      # Change Impact Report (Article 43(4))
annex4 ingest   --mlflow-run RUN_ID --output d.yaml  # pull from MLflow / HuggingFace / Giskard
annex4 bundle   create dossier.yaml --output b.zip   # SHA-256 evidence bundle
annex4 bundle   verify bundle.zip                    # tamper detection
```

## 4-step demo (10 minutes)

```bash
# 1. Classify your system — outputs a RiskProfile with Article citations
annex4 classify --i-acknowledge-uncertainty

# 2. Validate — coloured gap report against all 9 Annex IV sections
annex4 validate examples/hr_screening.yaml

# 3. Render — full PDF with cover page, provenance table, 9 sections
annex4 render examples/hr_screening.yaml --output dossier.pdf

# 4. Diff — Change Impact Report showing which Articles are affected
annex4 diff examples/hr_screening_v1.yaml examples/hr_screening_v2.yaml
```

## Design principles

| Principle | Implementation |
|-----------|----------------|
| **Legal firewall** | Every field is `SystemMetadata` (machine fact) or `ComplianceClaim` (human attestation) — the tool never signs for the provider |
| **Provenance on every field** | Each extracted value carries `{source, source_ref, extracted_at, extractor_version, confidence}` |
| **Local-first, zero telemetry** | No outbound HTTP in default mode |
| **No LLM in the loop** | Deterministic, regulation-aware logic only |
| **Regulation as versioned data** | `annex4/regulation/versions/2024-1689_base/` — new delegated acts become a new version, no engine changes |

## Ingestors

Pull metadata automatically from your MLOps stack:

```bash
annex4 ingest --mlflow-run abc123 --output dossier.yaml
annex4 ingest --hf-model org/my-model --output dossier.yaml
annex4 ingest --mlflow-run abc123 --override legal_review.yaml --output dossier.yaml
```

Supported: MLflow · HuggingFace Hub · Giskard scan results · YAML override files

Stubs (contributions welcome): Azure ML · Databricks · SageMaker · Vertex AI

## Examples

Three reference dossiers in `examples/`:

- `hr_screening.yaml` — CV screening system (Annex III §4(a), Article 6(2), internal control)
- `credit_scoring.yaml` — Credit scoring system (Annex III §5(b), Article 6(2))
- `medical_triage.yaml` — Medical triage assistant

## Change management

Track material changes across model versions. `annex4 diff` compares two dossier
YAML files at the field level and classifies every change per Article 43(4):

```shell
annex4 diff examples/hr_screening_v1.yaml examples/hr_screening_v2.yaml --format markdown
```

Exit codes:

| Code | Meaning |
|------|---------|
| `0`  | No changes |
| `1`  | Non-substantial changes only |
| `2`  | **Substantial changes** — conformity re-assessment required |
| `3`  | Ambiguous changes — human review required |

## Legal

- [LEGAL.md](LEGAL.md) — full legal notice (no warranty, no conformity assessment, not legal advice)
- [LICENSE](LICENSE) — Apache-2.0
- `annex4 legal` — print the full disclaimer from the CLI

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). DCO required (Signed-off-by:). Pre-commit and pytest gate must pass.
