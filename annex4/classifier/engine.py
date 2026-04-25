from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set

from rich.console import Console

from annex4.classifier.models import RiskProfile
from annex4.regulation.models import (
    ClassifierQuestion,
    ClassifierSpec,
    ClassifierVerdict,
)


class ClassifierEngine:
    """
    Interactively guides the user through the classification decision tree
    and returns a RiskProfile (not a raw Verdict string).
    """

    def __init__(self, spec: ClassifierSpec, console: Console):
        self.spec = spec
        self.console = console
        self.answers: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> RiskProfile:
        """Interactive mode: ask questions, return RiskProfile."""
        current_node_id = self.spec.start_node
        while current_node_id not in self.spec.verdicts:
            if current_node_id not in self.spec.tree:
                raise ValueError(
                    f"Node '{current_node_id}' not found in tree or verdicts."
                )
            node = self.spec.tree[current_node_id]
            answer = self._ask_question(node)
            self.answers[current_node_id] = answer
            current_node_id = self._get_next_node(node, answer)

        return self._to_risk_profile(self.spec.verdicts[current_node_id])

    def classify_from_yaml(self, dossier_path: Path) -> RiskProfile:
        """Non-interactive mode: derive classification from an existing dossier YAML.

        Reads `general_description.system.annex_iii_category` and
        `general_description.system.classification` to select the verdict.
        """
        import yaml
        from annex4.core.validate import _extract_val

        with open(dossier_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

        sys_raw = raw.get("general_description", {}).get("system", {})

        annex_iii_raw = sys_raw.get("annex_iii_category")
        classification_raw = sys_raw.get("classification", "")

        annex_iii = str(_extract_val(annex_iii_raw) or "").lower()
        classification = str(_extract_val(classification_raw) or "").lower()

        verdict_key = self._infer_verdict_key(annex_iii, classification)
        verdict = self.spec.verdicts.get(verdict_key)
        if verdict is None:
            verdict = self.spec.verdicts.get("verdict_uncertain",
                                             next(iter(self.spec.verdicts.values())))
        return self._to_risk_profile(verdict)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _infer_verdict_key(self, annex_iii: str, classification: str) -> str:
        """Map dossier field text → classifier verdict key."""
        mapping = {
            "§1": "verdict_high_risk_annex_iii_1",
            "section 1": "verdict_high_risk_annex_iii_1",
            "biometric": "verdict_high_risk_annex_iii_1",
            "§2": "verdict_high_risk_annex_iii_2",
            "section 2": "verdict_high_risk_annex_iii_2",
            "infrastructure": "verdict_high_risk_annex_iii_2",
            "§3": "verdict_high_risk_annex_iii_3",
            "section 3": "verdict_high_risk_annex_iii_3",
            "education": "verdict_high_risk_annex_iii_3",
            "§4": "verdict_high_risk_annex_iii_4",
            "section 4": "verdict_high_risk_annex_iii_4",
            "employment": "verdict_high_risk_annex_iii_4",
            "§5": "verdict_high_risk_annex_iii_5",
            "section 5": "verdict_high_risk_annex_iii_5",
            "essential service": "verdict_high_risk_annex_iii_5",
            "credit": "verdict_high_risk_annex_iii_5",
            "§6": "verdict_high_risk_annex_iii_6",
            "section 6": "verdict_high_risk_annex_iii_6",
            "law enforcement": "verdict_high_risk_annex_iii_6",
            "§7": "verdict_high_risk_annex_iii_7",
            "section 7": "verdict_high_risk_annex_iii_7",
            "migration": "verdict_high_risk_annex_iii_7",
            "§8": "verdict_high_risk_annex_iii_8",
            "section 8": "verdict_high_risk_annex_iii_8",
            "justice": "verdict_high_risk_annex_iii_8",
        }
        combined = f"{annex_iii} {classification}"
        for keyword, key in mapping.items():
            if keyword in combined:
                return key
        if "prohibited" in classification:
            return "verdict_prohibited"
        if "gpai" in combined or "general-purpose" in combined:
            return "verdict_gpai"
        if "minimal" in classification:
            return "verdict_minimal_risk"
        if "limited" in classification:
            return "verdict_limited_risk"
        return "verdict_uncertain"

    def _to_risk_profile(self, verdict: ClassifierVerdict) -> RiskProfile:
        return RiskProfile(
            path_id=verdict.path_id or verdict.verdict.lower().replace(" ", "_"),
            verdict=verdict.verdict,
            citation=verdict.citation,
            articles=verdict.articles or [verdict.citation],
            conformity_route=verdict.conformity_route or "unknown",
            notified_body_required=verdict.notified_body_assessment_likely,
            explanation_markdown=verdict.explanation_markdown,
            next_steps=verdict.next_steps,
            required_human_review=True,
        )

    def _ask_question(self, node: ClassifierQuestion) -> Any:
        self.console.print(f"\n[bold cyan]{node.question}[/bold cyan]")
        if node.type == "choice":
            return self._prompt_choice(node)
        elif node.type == "multiple_choice":
            return self._prompt_multiple_choice(node)
        else:
            raise NotImplementedError(f"Question type '{node.type}' is not supported.")

    def _prompt_choice(self, node: ClassifierQuestion) -> str:
        if not node.options:
            raise ValueError("Choice question must have options.")
        for i, option in enumerate(node.options):
            self.console.print(f"  [bold magenta]{i + 1}[/bold magenta]. {option['label']}")
        while True:
            try:
                choice_str = input("> ")
                choice_idx = int(choice_str) - 1
                if 0 <= choice_idx < len(node.options):
                    from typing import cast
                    return cast(str, node.options[choice_idx]["label"])
                self.console.print("[yellow]Invalid selection. Please try again.[/yellow]")
            except (ValueError, IndexError):
                self.console.print("[yellow]Please enter a valid number.[/yellow]")

    def _prompt_multiple_choice(self, node: ClassifierQuestion) -> Set[str]:
        if not node.options:
            raise ValueError("Multiple choice question must have options.")
        for i, option in enumerate(node.options):
            self.console.print(f"  [bold magenta]{i + 1}[/bold magenta]. {option['label']}")
        self.console.print("[dim](Enter comma-separated numbers, e.g., 1,3)[/dim]")
        while True:
            try:
                choices_str = input("> ")
                if not choices_str:
                    return set()
                choice_indices = {int(c.strip()) - 1 for c in choices_str.split(",")}
                if all(0 <= i < len(node.options) for i in choice_indices):
                    return {node.options[i]["label"] for i in choice_indices}
                self.console.print("[yellow]Invalid selection. Please try again.[/yellow]")
            except (ValueError, IndexError):
                self.console.print("[yellow]Please enter valid, comma-separated numbers.[/yellow]")

    def _get_next_node(self, node: ClassifierQuestion, answer: Any) -> str:
        from typing import cast
        if node.next_node:
            return node.next_node
        if node.type == "choice":
            for option in node.options or []:
                if option["label"] == answer:
                    return cast(str, option["next_node"])
        if node.next_node_logic:
            for logic_block in node.next_node_logic:
                if_condition = logic_block.get("if")
                if if_condition is not None:
                    labels = if_condition if isinstance(if_condition, list) else [if_condition]
                    # `is_not_selected` key at logic_block level means: fire "then" when
                    # labels are NOT present in the answer (used for multiple-choice negation).
                    if "is_not_selected" in logic_block:
                        if not any(label in answer for label in labels):
                            return cast(str, logic_block["then"])
                    else:
                        if any(label in answer for label in labels):
                            return cast(str, logic_block.get("then", ""))
                if "else" in logic_block:
                    return cast(str, logic_block["else"])
        raise ValueError(
            f"Cannot determine next node from node '{node.question}' and answer '{answer}'"
        )
