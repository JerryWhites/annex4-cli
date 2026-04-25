# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | Yes                |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security vulnerabilities by opening a **private** GitHub security
advisory at:

`https://github.com/<owner>/annex4-cli/security/advisories/new`

Include:
- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept if possible)
- Any suggested mitigations

We will acknowledge the report within 72 hours and aim to publish a fix within
30 days for confirmed vulnerabilities.

## Scope

This tool runs **entirely locally** — it makes no outbound network requests in
normal operation. The attack surface is limited to:

- Maliciously crafted YAML dossier files (parsed via `pyyaml safe_load`)
- Maliciously crafted regulation pack YAML files (loaded from the local filesystem)
- Jinja2 template rendering (autoescape enabled for HTML output)

Known non-issues:
- No server component, no authentication, no multi-tenant data
- No telemetry or outbound HTTP in default mode
