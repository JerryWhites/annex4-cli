"""
RiskProfile — the structured output of the classify command (PR#3).

This replaces the raw ClassifierVerdict string display and adds
the metadata required for integration with CI pipelines and
`annex4 init --system` non-interactive mode.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel

_DISCLAIMER = (
    "This classification is produced by annex4-cli as an informational aid. "
    "It is not a legal determination. A definitive risk classification under "
    "Regulation (EU) 2024/1689 is a legal judgment that requires human review "
    "by qualified counsel familiar with your specific system and deployment context."
)


class RiskProfile(BaseModel):
    """Structured classification output returned by ClassifierEngine."""

    path_id: str
    verdict: str
    citation: str
    articles: List[str]
    conformity_route: str
    notified_body_required: bool
    explanation_markdown: str
    next_steps: str
    required_human_review: bool = True
    disclaimer: str = _DISCLAIMER

    @property
    def is_high_risk(self) -> bool:
        return self.verdict.startswith("HIGH_RISK")

    @property
    def is_prohibited(self) -> bool:
        return self.verdict == "PROHIBITED"

    @property
    def needs_annex_iv(self) -> bool:
        return self.is_high_risk
