"""
Three-tier validation for AnnexIVDossier against Regulation (EU) 2024/1689.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any, Dict, Optional

from annex4.core.schema import AnnexIVDossier, SystemMetadata, ComplianceClaim

_PLACEHOLDER_MARKERS = ("[REQUIRED]", "[IF APPLICABLE]")


def _extract_val(f: Any) -> Any:
    if f is None:
        return None
    if isinstance(f, SystemMetadata):
        return f.value
    if isinstance(f, ComplianceClaim):
        return f.statement
    if isinstance(f, dict):
        if f.get("kind") == "system_metadata":
            return f.get("value")
        if f.get("kind") == "compliance_claim":
            return f.get("statement")
    return f


def _is_blank(value: Any) -> bool:
    val = _extract_val(value)
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _is_placeholder(value: Any) -> bool:
    val = _extract_val(value)
    if not val:
        return False
    if isinstance(val, str):
        return any(m in val for m in _PLACEHOLDER_MARKERS)
    return False


def _unfilled(value: Any) -> bool:
    return _is_blank(value) or _is_placeholder(value)


class Level(str, Enum):
    ERROR = "ERROR"
    LEGAL_GAP = "LEGAL_GAP"
    INCONSISTENCY = "INCONSISTENCY"
    WARNING = "WARNING"
    ASSUMPTION = "ASSUMPTION"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    level: Level
    code: str
    field: str
    message: str
    article: str = ""

    def __str__(self) -> str:
        ref = f" [{self.article}]" if self.article else ""
        return f"[{self.level.value}] {self.code}  {self.field}{ref}\n         {self.message}"


@dataclass
class ValidationReport:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == Level.ERROR]

    @property
    def legal_gaps(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == Level.LEGAL_GAP]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == Level.WARNING]

    @property
    def infos(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == Level.INFO]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def _add(
        self, level: Level, code: str, field_path: str, message: str, article: str = ""
    ) -> None:
        self.issues.append(
            ValidationIssue(
                level=level,
                code=code,
                field=field_path,
                message=message,
                article=article,
            )
        )

    def error(
        self, code: str, field_path: str, message: str, article: str = ""
    ) -> None:
        self._add(Level.ERROR, code, field_path, message, article)

    def legal_gap(
        self, code: str, field_path: str, message: str, article: str = ""
    ) -> None:
        self._add(Level.LEGAL_GAP, code, field_path, message, article)

    def warning(
        self, code: str, field_path: str, message: str, article: str = ""
    ) -> None:
        self._add(Level.WARNING, code, field_path, message, article)

    def info(self, code: str, field_path: str, message: str, article: str = "") -> None:
        self._add(Level.INFO, code, field_path, message, article)

    def assumption(
        self, code: str, field_path: str, message: str, article: str = ""
    ) -> None:
        self._add(Level.ASSUMPTION, code, field_path, message, article)

    def inconsistency(
        self, code: str, field_path: str, message: str, article: str = ""
    ) -> None:
        self._add(Level.INCONSISTENCY, code, field_path, message, article)


# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------


def check_dossier(
    dossier: AnnexIVDossier, field_kinds: Dict[str, Any]
) -> ValidationReport:
    r = ValidationReport()

    required_claims = set(field_kinds.get("claim_required", []))

    def check_claim(f_obj: Any, path: str, art: str) -> None:
        if path not in required_claims or f_obj is None:
            return
        kind = getattr(f_obj, "kind", None) or (
            f_obj.get("kind") if isinstance(f_obj, dict) else None
        )
        if kind == "system_metadata":
            r.legal_gap(
                "LG001",
                path,
                "Field requires human attestation (ComplianceClaim), but SystemMetadata was found.",
                art,
            )

    prov = dossier.general_description.provider
    sys_ = dossier.general_description.system
    ip = dossier.general_description.intended_purpose

    # --- Section 1: Provider identity ---
    if _unfilled(prov.name):
        r.error(
            "E001",
            "general_description.provider.name",
            "Provider legal name is required.",
            "Annex IV §1(a)",
        )
    check_claim(prov.name, "general_description.provider.name", "Annex IV §1(a)")

    if _unfilled(prov.address):
        r.error(
            "E002",
            "general_description.provider.address",
            "Provider registered address is required.",
            "Annex IV §1(a)",
        )
    check_claim(prov.address, "general_description.provider.address", "Annex IV §1(a)")

    if _unfilled(prov.contact_email):
        r.error(
            "E003",
            "general_description.provider.contact_email",
            "Market surveillance contact email is required.",
            "Annex IV §1(a)",
        )
    check_claim(
        prov.contact_email,
        "general_description.provider.contact_email",
        "Annex IV §1(a)",
    )

    if _unfilled(prov.authorized_signatory):
        r.error(
            "E004",
            "general_description.provider.authorized_signatory",
            "Name of the authorised signatory is required.",
            "Annex IV §1(a)",
        )
    check_claim(
        prov.authorized_signatory,
        "general_description.provider.authorized_signatory",
        "Annex IV §1(a)",
    )

    # --- Section 1: System identity ---
    if _unfilled(sys_.name):
        r.error(
            "E005",
            "general_description.system.name",
            "AI system name is required.",
            "Annex IV §1(b)",
        )
    check_claim(sys_.name, "general_description.system.name", "Annex IV §1(b)")

    if _unfilled(sys_.version):
        r.error(
            "E006",
            "general_description.system.version",
            "System version is required.",
            "Annex IV §1(b)",
        )
    check_claim(sys_.version, "general_description.system.version", "Annex IV §1(b)")

    if _unfilled(sys_.classification):
        r.error(
            "E007",
            "general_description.system.classification",
            "Risk classification is required.",
            "Annex IV §1(b)",
        )
    check_claim(
        sys_.classification,
        "general_description.system.classification",
        "Annex IV §1(b)",
    )

    # --- Section 1: Intended purpose ---
    if _unfilled(ip.description):
        r.error(
            "E008",
            "general_description.intended_purpose.description",
            "Intended purpose description is required.",
            "Annex IV §1(c)",
        )
    check_claim(
        ip.description,
        "general_description.intended_purpose.description",
        "Annex IV §1(c)",
    )

    if _unfilled(ip.intended_users):
        r.error(
            "E009",
            "general_description.intended_purpose.intended_users",
            "Intended users description is required.",
            "Annex IV §1(c)",
        )
    check_claim(
        ip.intended_users,
        "general_description.intended_purpose.intended_users",
        "Annex IV §1(c)",
    )

    if _unfilled(ip.persons_affected):
        r.error(
            "E010",
            "general_description.intended_purpose.persons_affected",
            "Persons affected description is required.",
            "Annex IV §1(c)",
        )
    check_claim(
        ip.persons_affected,
        "general_description.intended_purpose.persons_affected",
        "Annex IV §1(c)",
    )

    # --- Section 2: Development process ---
    dev = dossier.development_process

    if _unfilled(dev.methodology):
        r.error(
            "E011",
            "development_process.methodology",
            "Development methodology is required.",
            "Annex IV §2(a)",
        )

    if _unfilled(dev.architecture_description):
        r.error(
            "E012",
            "development_process.architecture_description",
            "Architecture description is required.",
            "Annex IV §2(b)",
        )

    if _unfilled(dev.input_description):
        r.error(
            "E013",
            "development_process.input_description",
            "Input description is required.",
            "Annex IV §2(c)",
        )

    if _unfilled(dev.output_description):
        r.error(
            "E014",
            "development_process.output_description",
            "Output description is required.",
            "Annex IV §2(d)",
        )

    dg = dev.data_governance

    if not dg.training_sources:
        r.warning(
            "W002",
            "development_process.data_governance.training_sources",
            "No training data sources documented.",
            "Article 10",
        )

    if not dg.bias_analysis:
        r.warning(
            "W004",
            "development_process.data_governance.bias_analysis",
            "No bias analysis documented.",
            "Article 10(2)(f)",
        )

    # --- Section 3: Monitoring, functioning and control ---
    mfc = dossier.monitoring_functioning_control

    if _unfilled(mfc.capabilities_and_limitations):
        r.error(
            "E015",
            "monitoring_functioning_control.capabilities_and_limitations",
            "Capabilities and limitations description is required.",
            "Annex IV §3 / Article 13(3)(b)",
        )
    check_claim(
        mfc.capabilities_and_limitations,
        "monitoring_functioning_control.capabilities_and_limitations",
        "Article 13(3)(b)",
    )

    if _unfilled(mfc.foreseeable_unintended_outcomes):
        r.error(
            "E016",
            "monitoring_functioning_control.foreseeable_unintended_outcomes",
            "Foreseeable unintended outcomes description is required.",
            "Annex IV §3 / Article 9(2)",
        )
    check_claim(
        mfc.foreseeable_unintended_outcomes,
        "monitoring_functioning_control.foreseeable_unintended_outcomes",
        "Article 9(2)",
    )

    if _unfilled(mfc.human_oversight_measures):
        r.error(
            "E017",
            "monitoring_functioning_control.human_oversight_measures",
            "Human oversight measures description is required.",
            "Annex IV §3 / Article 14",
        )
    check_claim(
        mfc.human_oversight_measures,
        "monitoring_functioning_control.human_oversight_measures",
        "Article 14",
    )

    for i, issue in enumerate(mfc.robustness_issues):
        sev = _extract_val(issue.severity)
        sta = _extract_val(issue.status)
        if (
            isinstance(sev, str)
            and sev.strip().lower() == "high"
            and isinstance(sta, str)
            and sta.strip().lower() == "open"
        ):
            r.error(
                "E018",
                f"monitoring_functioning_control.robustness_issues[{i}]",
                f"Open high-severity robustness issue '{_extract_val(issue.id)}' must be resolved before deployment.",
                "Article 15",
            )

    if not mfc.accuracy_metrics:
        r.warning(
            "W006",
            "monitoring_functioning_control.accuracy_metrics",
            "No accuracy metrics documented.",
            "Annex IV §3 / Article 15(1)",
        )
    else:
        for i, metric in enumerate(mfc.accuracy_metrics):
            if not metric.subpopulation_breakdown:
                r.warning(
                    "W008",
                    f"monitoring_functioning_control.accuracy_metrics[{i}].subpopulation_breakdown",
                    f"Metric '{_extract_val(metric.name)}' has no subpopulation breakdown.",
                    "Article 15(4)",
                )

    # --- Section 4: Risk management ---
    rm = dossier.risk_management

    if _unfilled(rm.process_description):
        r.error(
            "E019",
            "risk_management.process_description",
            "Risk management process description is required.",
            "Article 9(1)",
        )

    if not rm.identified_risks:
        r.error(
            "E020",
            "risk_management.identified_risks",
            "At least one identified risk must be documented.",
            "Article 9(2)",
        )
    else:
        for i, risk in enumerate(rm.identified_risks):
            if _unfilled(risk.mitigation):
                r.warning(
                    "W010",
                    f"risk_management.identified_risks[{i}].mitigation",
                    f"Risk '{_extract_val(risk.risk)}' has no mitigation documented.",
                    "Article 9(4)",
                )

    # --- Section 5: Lifecycle changes ---
    lc = dossier.lifecycle_changes
    has_substantial = any(bool(_extract_val(c.is_substantial)) for c in lc.changes)
    if has_substantial and _unfilled(lc.substantiality_assessment):
        r.warning(
            "W012",
            "lifecycle_changes.substantiality_assessment",
            "One or more changes are marked substantial but no substantiality assessment is provided.",
            "Article 16(d)",
        )

    # --- Section 7: EU Declaration of Conformity ---
    decl = dossier.eu_declaration_of_conformity

    if _unfilled(decl.declaration_date):
        r.warning(
            "W014",
            "eu_declaration_of_conformity.declaration_date",
            "Declaration date is not set.",
            "Annex IV §7",
        )

    nb_req = _extract_val(decl.notified_body_required)
    if nb_req:
        if _unfilled(decl.notified_body_name):
            r.error(
                "E021",
                "eu_declaration_of_conformity.notified_body_name",
                "Notified body name is required when notified body involvement is indicated.",
                "Article 43",
            )
        if _unfilled(decl.notified_body_certificate):
            r.error(
                "E022",
                "eu_declaration_of_conformity.notified_body_certificate",
                "Notified body certificate reference is required when notified body involvement is indicated.",
                "Article 43",
            )

    # --- Section 8: Post-market monitoring ---
    pmm = dossier.post_market_monitoring

    if _unfilled(pmm.monitoring_approach):
        r.error(
            "E023",
            "post_market_monitoring.monitoring_approach",
            "Post-market monitoring approach is required.",
            "Article 72",
        )

    if not pmm.key_performance_indicators:
        r.warning(
            "W016",
            "post_market_monitoring.key_performance_indicators",
            "No KPIs defined for post-market monitoring.",
            "Article 72(1)",
        )

    # --- Evidence index ---
    if not dossier.evidence_index:
        r.info(
            "I003",
            "evidence_index",
            "No evidence items referenced. Consider linking artefacts to dossier sections.",
        )

    # --- Harmonised standards ---
    if not dossier.harmonised_standards:
        r.info(
            "I004",
            "harmonised_standards",
            "No harmonised standards referenced.",
            "Annex IV §6",
        )

    # --- Git commit traceability ---
    if dossier.general_description.system.git_commit is None:
        r.info(
            "I005",
            "general_description.system.git_commit",
            "No git commit hash recorded. Recording the model artefact commit improves traceability.",
            "Annex IV §2",
        )

    return r


def validate(
    dossier: AnnexIVDossier, field_kinds: Optional[Dict[str, Any]] = None
) -> ValidationReport:
    if field_kinds is None:
        field_kinds = {}
    return check_dossier(dossier, field_kinds)
