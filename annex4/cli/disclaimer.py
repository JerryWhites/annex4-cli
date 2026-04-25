"""
Disclaimer enforcement for annex4-cli.

Every subcommand must call print_cli_disclaimer() before any other output.
The full disclaimer text must appear in every rendered artefact (HTML, PDF).
Attempts to suppress or disable the disclaimer raise DisclaimerRequiredError.
"""

from __future__ import annotations

import sys
from annex4 import __version__

_SHORT = (
    f"annex4-cli v{__version__} — informational tool only, not legal advice.\n"
    "Full disclaimer: annex4 legal\n"
)

FULL_DISCLAIMER = (
    "This technical documentation is produced by annex4-cli to support compliance "
    "with Article 11 and Annex IV of Regulation (EU) 2024/1689. "
    "It does not constitute a conformity assessment. "
    "Where third-party conformity assessment by a notified body is required under "
    "Article 43, obtaining that assessment remains the responsibility of the provider. "
    "This document is informational; it is not legal advice."
)


class DisclaimerRequiredError(RuntimeError):
    """Raised when code attempts to render an output without the mandatory disclaimer."""


def print_cli_disclaimer() -> None:
    """Print the short disclaimer to STDERR. Called at the start of every subcommand."""
    sys.stderr.write(_SHORT)
    sys.stderr.flush()
