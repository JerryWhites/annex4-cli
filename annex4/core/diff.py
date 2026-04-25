"""
Change Impact Report engine (PR#6).

Produces a structured diff between two AnnexIVDossiers:
- Changes grouped by Annex IV section
- Per-entry article citations based on field path
- Substantiality factor checklist (not a determination — for human review)
- Provenance-aware conflict detection

This report is informational. A determination of substantiality under
Article 43(4) is a legal judgment requiring human review.
"""

import re
from typing import Any, cast, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel

from annex4.core.schema import AnnexIVDossier, SystemMetadata, ComplianceClaim

# ---------------------------------------------------------------------------
# Section / article citation mapping
# ---------------------------------------------------------------------------

_SECTION_MAP: List[Tuple[str, str, str, List[str]]] = [
    # (path_prefix, section_number, section_name, articles)
    (
        "general_description.intended_purpose",
        "1c",
        "General description — intended purpose",
        ["Article 6(2)", "Article 13(3)(b)", "Annex IV §1(c)", "Article 43(4)"],
    ),
    (
        "general_description.provider",
        "1a",
        "General description — provider",
        ["Article 13(3)(a)", "Annex IV §1(a)"],
    ),
    (
        "general_description.system",
        "1b",
        "General description — system identity",
        ["Article 13(3)(b)", "Annex IV §1(b)", "Article 43(4)"],
    ),
    (
        "general_description",
        "1",
        "General description",
        ["Article 13(3)", "Annex IV §1"],
    ),
    (
        "development_process.data_governance",
        "2b",
        "Development process — data governance",
        ["Article 10", "Article 10(2)(f)", "Annex IV §2", "Article 43(4)"],
    ),
    (
        "development_process",
        "2",
        "Development process",
        ["Article 10", "Annex IV §2", "Article 43(4)"],
    ),
    (
        "monitoring_functioning_control.accuracy_metrics",
        "3a",
        "Monitoring — accuracy metrics",
        ["Article 15", "Article 15(4)", "Annex IV §3", "Article 43(4)"],
    ),
    (
        "monitoring_functioning_control.human_oversight_measures",
        "3b",
        "Monitoring — human oversight",
        ["Article 14", "Annex IV §3", "Article 43(4)"],
    ),
    (
        "monitoring_functioning_control",
        "3",
        "Monitoring, functioning and control",
        ["Article 13", "Article 14", "Article 15", "Annex IV §3"],
    ),
    (
        "risk_management",
        "4",
        "Risk management",
        ["Article 9", "Article 9(2)", "Annex IV §4", "Article 43(4)"],
    ),
    ("lifecycle_changes", "5", "Lifecycle changes", ["Article 16(d)", "Annex IV §5"]),
    (
        "harmonised_standards",
        "6",
        "Harmonised standards",
        ["Annex IV §6", "Article 43(1)"],
    ),
    (
        "eu_declaration_of_conformity",
        "7",
        "EU declaration of conformity",
        ["Article 47", "Annex IV §7"],
    ),
    (
        "post_market_monitoring",
        "8",
        "Post-market monitoring",
        ["Article 72", "Article 72(1)", "Annex IV §8"],
    ),
    ("serious_incidents", "9", "Serious incidents", ["Article 73", "Annex IV §9"]),
    ("evidence_index", "A", "Evidence index", ["Annex IV Appendix A"]),
]

_FALLBACK_SECTION = ("0", "Other", ["Article 43(4)"])


def _path_section(path: str) -> Tuple[str, str, List[str]]:
    """Return (section_number, section_name, articles) for a field path."""
    stripped = re.sub(r"\[\d+\]", "", path)
    for prefix, sec_num, sec_name, arts in _SECTION_MAP:
        if stripped.startswith(prefix):
            return sec_num, sec_name, arts
    return _FALLBACK_SECTION


# ---------------------------------------------------------------------------
# Substantiality factors (Article 43(4) checklist)
# ---------------------------------------------------------------------------

_FACTOR_DEFINITIONS = [
    {
        "id": "F1",
        "factor": "Change to the intended purpose of the AI system",
        "articles": ["Article 43(4)(a)", "Article 9(2)"],
        "triggers": ["general_description.intended_purpose"],
    },
    {
        "id": "F2",
        "factor": "Change to training, validation, or testing data",
        "articles": ["Article 10", "Article 43(4)"],
        "triggers": [
            "development_process.data_governance.training_sources",
            "development_process.data_governance.validation_sources",
            "development_process.data_governance.test_sources",
        ],
    },
    {
        "id": "F3",
        "factor": "Change to model architecture or core algorithm",
        "articles": ["Article 43(4)", "Annex IV §2"],
        "triggers": [
            "development_process.architecture_description",
            "development_process.methodology",
        ],
    },
    {
        "id": "F4",
        "factor": "Significant change to performance or accuracy metrics",
        "articles": ["Article 15", "Article 43(4)"],
        "triggers": ["monitoring_functioning_control.accuracy_metrics"],
    },
    {
        "id": "F5",
        "factor": "Change to human oversight measures",
        "articles": ["Article 14", "Article 43(4)"],
        "triggers": ["monitoring_functioning_control.human_oversight_measures"],
    },
    {
        "id": "F6",
        "factor": "Change to identified risks or mitigation measures",
        "articles": ["Article 9", "Article 43(4)"],
        "triggers": ["risk_management"],
    },
    {
        "id": "F7",
        "factor": "Change to post-market monitoring plan or KPIs",
        "articles": ["Article 72", "Article 43(4)"],
        "triggers": ["post_market_monitoring"],
    },
]


class SubstantialityFactor(BaseModel):
    id: str
    factor: str
    articles: List[str]
    triggered: bool


def _compute_factors(entry_paths: List[str]) -> List[SubstantialityFactor]:
    factors = []
    stripped_paths = {re.sub(r"\[\d+\]", "", p) for p in entry_paths}
    for defn in _FACTOR_DEFINITIONS:
        triggered = any(
            any(sp.startswith(trigger) for sp in stripped_paths)
            for trigger in defn["triggers"]
        )
        factors.append(
            SubstantialityFactor(
                id=str(defn["id"]),
                factor=str(defn["factor"]),
                articles=list(defn["articles"]),
                triggered=triggered,
            )
        )
    return factors


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class DiffEntry(BaseModel):
    path: str
    annex_iv_section: str
    section_name: str
    kind: Literal["added", "removed", "modified", "unchanged"]
    old_value: Any
    new_value: Any
    citations: List[str]
    substantiality: Literal["substantial", "non_substantial", "ambiguous", "unknown"]


class DiffReport(BaseModel):
    entries: List[DiffEntry]
    has_substantial_changes: bool
    regulation_version_changed: bool
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    substantiality_factors: List[SubstantialityFactor] = []

    LEGAL_NOTICE: str = (
        "This report is informational. A determination of substantiality under "
        "Article 43(4) is a legal judgment requiring human review."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _field_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, SystemMetadata):
        return str(v.value)
    if isinstance(v, ComplianceClaim):
        return v.statement
    return str(v) if not isinstance(v, (dict, list)) else None


def _flatten_fields(obj: Any) -> Any:
    """Recursively replace Field_ dicts with their scalar value so diff paths stay stable."""
    if isinstance(obj, dict):
        kind = obj.get("kind")
        if kind == "system_metadata":
            return obj.get("value")
        if kind == "compliance_claim":
            return obj.get("statement")
        return {k: _flatten_fields(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_flatten_fields(item) for item in obj]
    return obj


def get_substantiality(path: str, substantiality_rules: Dict[str, str]) -> str:
    stripped_path = re.sub(r"\[\d+\]", "", path)
    return substantiality_rules.get(stripped_path, "unknown")


def traverse_dict(d: Dict[str, Any], path: str = "") -> Dict[str, Any]:
    flat = {}
    for k, v in d.items():
        new_path = f"{path}.{k}" if path else k
        if isinstance(v, dict):
            flat.update(traverse_dict(v, new_path))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                item_path = f"{new_path}[{i}]"
                if isinstance(item, dict):
                    flat.update(traverse_dict(item, item_path))
                else:
                    flat[item_path] = item
        else:
            flat[new_path] = v
    return flat


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def diff_dossiers(
    old: AnnexIVDossier, new: AnnexIVDossier, substantiality_rules: Dict[str, str]
) -> DiffReport:
    old_flat = traverse_dict(_flatten_fields(old.model_dump()))
    new_flat = traverse_dict(_flatten_fields(new.model_dump()))

    all_keys = set(old_flat.keys()).union(new_flat.keys())
    entries: List[DiffEntry] = []

    for k in sorted(all_keys):
        if k not in old_flat:
            kind: Literal["added", "removed", "modified", "unchanged"] = "added"
            old_val = None
            new_val = new_flat[k]
        elif k not in new_flat:
            kind = "removed"
            old_val = old_flat[k]
            new_val = None
        elif old_flat[k] != new_flat[k]:
            kind = "modified"
            old_val = old_flat[k]
            new_val = new_flat[k]
        else:
            continue

        sec_num, sec_name, arts = _path_section(k)
        subst = get_substantiality(k, substantiality_rules)

        entries.append(
            DiffEntry(
                path=k,
                annex_iv_section=sec_num,
                section_name=sec_name,
                kind=kind,
                old_value=old_val,
                new_value=new_val,
                citations=arts + ["Article 43(4)"]
                if "Article 43(4)" not in arts
                else arts,
                substantiality=cast(
                    Literal["substantial", "non_substantial", "ambiguous", "unknown"],
                    subst,
                ),
            )
        )

    has_substantial = any(e.substantiality == "substantial" for e in entries)
    reg_changed = _field_str(
        old.general_description.system.regulation_version
    ) != _field_str(new.general_description.system.regulation_version)
    factors = _compute_factors([e.path for e in entries])

    return DiffReport(
        entries=entries,
        has_substantial_changes=has_substantial,
        regulation_version_changed=reg_changed,
        old_version=_field_str(old.general_description.system.version),
        new_version=_field_str(new.general_description.system.version),
        substantiality_factors=factors,
    )
