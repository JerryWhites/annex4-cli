# `annex4 diff`

Compare two Annex IV dossier YAML files at the field level. Each changed field is
classified as **substantial**, **non-substantial**, or **ambiguous** per Article 43(4)
of Regulation (EU) 2024/1689.

## Usage

```
annex4 diff <OLD_FILE> <NEW_FILE> [--format cli|json|markdown|html]
```

## Arguments

| Argument   | Description                         |
|------------|-------------------------------------|
| `OLD_FILE` | Path to the older dossier YAML file |
| `NEW_FILE` | Path to the newer dossier YAML file |

## Options

| Option     | Default | Description                                              |
|------------|---------|----------------------------------------------------------|
| `--format` | `cli`   | Output format: `cli` (rich table), `json`, `markdown`, or `html` |

## Exit codes

| Code | Meaning                                                  |
|------|----------------------------------------------------------|
| `0`  | No changes detected                                      |
| `1`  | Non-substantial changes only                             |
| `2`  | Substantial changes detected — re-assessment required    |
| `3`  | Ambiguous changes present — human decision required      |

## Examples

```bash
# Interactive rich table in the terminal
annex4 diff examples/v2.2.4.yaml examples/v2.3.1.yaml

# Markdown report (suitable for PR comments or filing with a notified body)
annex4 diff examples/v2.2.4.yaml examples/v2.3.1.yaml --format markdown > report.md

# Machine-readable JSON for downstream CI tooling
annex4 diff examples/v2.2.4.yaml examples/v2.3.1.yaml --format json | jq .entries

# Self-contained HTML report
annex4 diff examples/v2.2.4.yaml examples/v2.3.1.yaml --format html > report.html
```

## Substantiality classification

Field-level substantiality is data-driven. The mapping lives at:

```
annex4/regulation/versions/<id>/diff_substantiality.yaml
```

Fields not listed there are reported as `unknown` and should be reviewed manually
before submission. The three outcome levels are:

| Outcome          | Meaning                                                             |
|------------------|---------------------------------------------------------------------|
| `substantial`    | Change requires a new conformity assessment (Article 43(4))        |
| `non_substantial`| Change must be documented but does not trigger re-assessment        |
| `ambiguous`      | Classification depends on context; flagged for human decision       |

## Regulation-version mismatch

If the two dossiers carry different `regulation_version` values, every output mode
shows a banner distinguishing "changes due to provider action" from "changes due to
a regulation update." This is critical when migrating between regulation versions
with `annex4 migrate`.
