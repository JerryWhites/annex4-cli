"""
Pydantic models for the AnnexIVDossier
"""

from typing import Any, Dict, List, Optional, Literal, Union
from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: Literal["mlflow", "huggingface", "giskard", "manual", "inferred"]
    source_ref: str
    extracted_at: str
    extractor_version: str
    confidence: float = Field(ge=0.0, le=1.0)


class SystemMetadata(BaseModel):
    kind: Literal["system_metadata"] = "system_metadata"
    value: Union[str, int, float, bool, Dict[str, Any], List[Any]]
    provenance: Provenance
    conflict_resolved: bool = False


class ComplianceClaim(BaseModel):
    kind: Literal["compliance_claim"] = "compliance_claim"
    statement: str
    attested_by: str
    attested_at: str
    evidence_refs: List[str]
    requires_legal_confirmation: bool = False


Field_ = Union[str, int, float, bool, SystemMetadata, ComplianceClaim]

# ---------------------------------------------------------------------------
# Section 1 — General description
# ---------------------------------------------------------------------------


class ProviderInfo(BaseModel):
    name: Optional[Field_] = None
    registration_number: Optional[Field_] = None
    address: Optional[Field_] = None
    contact_email: Optional[Field_] = None
    authorized_signatory: Optional[Field_] = None
    ai_governance_owner: Optional[Field_] = None
    eu_representative: Optional[Field_] = None


class SystemIdentity(BaseModel):
    name: Optional[Field_] = None
    version: Optional[Field_] = None
    git_commit: Optional[Field_] = None
    release_date: Optional[Field_] = None
    classification: Optional[Field_] = None
    annex_iii_category: Optional[Field_] = None
    regulation_version: Field_ = "2024-1689_base"


class IntendedPurpose(BaseModel):
    description: Optional[Field_] = None
    intended_users: Optional[Field_] = None
    deployment_form: Optional[Field_] = None
    geographic_scope: Optional[Field_] = None
    persons_affected: Optional[Field_] = None
    foreseeable_misuse: List[Field_] = Field(default_factory=list)


class GeneralDescription(BaseModel):
    provider: ProviderInfo = Field(default_factory=ProviderInfo)
    system: SystemIdentity = Field(default_factory=SystemIdentity)
    intended_purpose: IntendedPurpose = Field(default_factory=IntendedPurpose)


# ---------------------------------------------------------------------------
# Section 2 — Detailed description of elements and development process
# ---------------------------------------------------------------------------


class DataSource(BaseModel):
    name: Optional[Field_] = None
    origin: Optional[Field_] = None
    volume: Optional[Field_] = None
    license: Optional[Field_] = None
    evidence_uri: Optional[Field_] = None


class BiasAnalysisItem(BaseModel):
    attribute: Optional[Field_] = None
    population_share: Optional[Field_] = None
    reference_share: Optional[Field_] = None
    delta: Optional[Field_] = None
    action_taken: Optional[Field_] = None


class DataGovernance(BaseModel):
    training_sources: List[DataSource] = Field(default_factory=list)
    validation_sources: List[DataSource] = Field(default_factory=list)
    test_sources: List[DataSource] = Field(default_factory=list)
    bias_analysis: List[BiasAnalysisItem] = Field(default_factory=list)
    residual_data_gaps: Optional[Field_] = None
    data_collection_procedures: Optional[Field_] = None
    special_category_data: Optional[Field_] = None


class DevelopmentProcess(BaseModel):
    methodology: Optional[Field_] = None
    architecture_description: Optional[Field_] = None
    input_description: Optional[Field_] = None
    output_description: Optional[Field_] = None
    pre_trained_components: Optional[Field_] = None
    design_choices_rationale: Optional[Field_] = None
    data_governance: DataGovernance = Field(default_factory=DataGovernance)


# ---------------------------------------------------------------------------
# Section 3 — Monitoring, functioning and control (Article 15)
# ---------------------------------------------------------------------------


class AccuracySubpopulationRow(BaseModel):
    subpopulation: Optional[Field_] = None
    n: Optional[Field_] = None
    value: Optional[Field_] = None
    confidence_interval: Optional[Field_] = None
    delta_vs_aggregate: Optional[Field_] = None


class AccuracyMetric(BaseModel):
    name: Optional[Field_] = None
    aggregate_value: Optional[Field_] = None
    confidence_interval: Optional[Field_] = None
    subpopulation_breakdown: List[AccuracySubpopulationRow] = Field(
        default_factory=list
    )
    methodology_note: Optional[Field_] = None


class RobustnessIssue(BaseModel):
    id: Optional[Field_] = None
    category: Optional[Field_] = None
    severity: Optional[Field_] = None
    status: Optional[Field_] = None
    rationale: Optional[Field_] = None


class MonitoringFunctioningControl(BaseModel):
    capabilities_and_limitations: Optional[Field_] = None
    foreseeable_unintended_outcomes: Optional[Field_] = None
    human_oversight_measures: Optional[Field_] = None
    accuracy_metrics: List[AccuracyMetric] = Field(default_factory=list)
    robustness_issues: List[RobustnessIssue] = Field(default_factory=list)
    cybersecurity_measures: Optional[Field_] = None


# ---------------------------------------------------------------------------
# Section 4 — Risk management system (Article 9)
# ---------------------------------------------------------------------------


class RiskItem(BaseModel):
    risk: Optional[Field_] = None
    likelihood: Optional[Field_] = None
    impact: Optional[Field_] = None
    mitigation: Optional[Field_] = None
    residual_risk: Optional[Field_] = None
    accepted_by: Optional[Field_] = None


class RiskManagement(BaseModel):
    identified_risks: List[RiskItem] = Field(default_factory=list)
    process_description: Optional[Field_] = None
    residual_risk_acceptance: Optional[Field_] = None


# ---------------------------------------------------------------------------
# Section 5 — Lifecycle changes
# ---------------------------------------------------------------------------


class LifecycleChange(BaseModel):
    field: Optional[Field_] = None
    change_description: Optional[Field_] = None
    trigger: Optional[Field_] = None
    approved_by: Optional[Field_] = None
    is_substantial: Optional[Field_] = None


class LifecycleChanges(BaseModel):
    previous_version: Optional[Field_] = None
    changes: List[LifecycleChange] = Field(default_factory=list)
    substantiality_assessment: Optional[Field_] = None


# ---------------------------------------------------------------------------
# Section 6 — Harmonised standards
# ---------------------------------------------------------------------------


class HarmonisedStandard(BaseModel):
    standard: Optional[Field_] = None
    clause: Optional[Field_] = None
    conformance: Optional[Field_] = None
    evidence: Optional[Field_] = None


# ---------------------------------------------------------------------------
# Section 7 — EU declaration of conformity
# ---------------------------------------------------------------------------


class EUDeclarationOfConformity(BaseModel):
    declaration_reference: Optional[Field_] = None
    declaration_date: Optional[Field_] = None
    notified_body_required: Optional[Field_] = None
    notified_body_name: Optional[Field_] = None
    notified_body_certificate: Optional[Field_] = None
    notes: Optional[Field_] = None


# ---------------------------------------------------------------------------
# Section 8 — Post-market monitoring (Article 72)
# ---------------------------------------------------------------------------


class PostMarketMonitoring(BaseModel):
    monitoring_approach: Optional[Field_] = None
    key_performance_indicators: List[Field_] = Field(default_factory=list)
    drift_detection_method: Optional[Field_] = None
    update_trigger_thresholds: Optional[Field_] = None
    responsible_person: Optional[Field_] = None
    review_frequency: Optional[Field_] = None


# ---------------------------------------------------------------------------
# Section 9 — Serious incidents (Article 73)
# ---------------------------------------------------------------------------


class SeriousIncident(BaseModel):
    incident_id: Optional[Field_] = None
    date: Optional[Field_] = None
    description: Optional[Field_] = None
    severity: Optional[Field_] = None
    root_cause: Optional[Field_] = None
    corrective_action: Optional[Field_] = None
    reported_to: Optional[Field_] = None


# ---------------------------------------------------------------------------
# Evidence index (Appendix A)
# ---------------------------------------------------------------------------


class EvidenceItem(BaseModel):
    id: Optional[Field_] = None
    type: Optional[Field_] = None
    uri: Optional[Field_] = None
    used_in_sections: List[Field_] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Root dossier model
# ---------------------------------------------------------------------------


class DossierMeta(BaseModel):
    generated_by: str = "annex4-cli"
    regulation_version: str = "2024-1689_base"
    dossier_schema_version: str = "1.0.0"
    notes: Optional[Field_] = None


class AnnexIVDossier(BaseModel):
    meta: DossierMeta = Field(default_factory=DossierMeta)

    # Section 1
    general_description: GeneralDescription = Field(default_factory=GeneralDescription)

    # Section 2
    development_process: DevelopmentProcess = Field(default_factory=DevelopmentProcess)

    # Section 3
    monitoring_functioning_control: MonitoringFunctioningControl = Field(
        default_factory=MonitoringFunctioningControl
    )

    # Section 4
    risk_management: RiskManagement = Field(default_factory=RiskManagement)

    # Section 5
    lifecycle_changes: LifecycleChanges = Field(default_factory=LifecycleChanges)

    # Section 6
    harmonised_standards: List[HarmonisedStandard] = Field(default_factory=list)

    # Section 7
    eu_declaration_of_conformity: EUDeclarationOfConformity = Field(
        default_factory=EUDeclarationOfConformity
    )

    # Section 8
    post_market_monitoring: PostMarketMonitoring = Field(
        default_factory=PostMarketMonitoring
    )

    # Section 9
    serious_incidents: List[SeriousIncident] = Field(default_factory=list)

    # Evidence index
    evidence_index: List[EvidenceItem] = Field(default_factory=list)

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "AnnexIVDossier":
        """Load a dossier from a raw dict (e.g. parsed from YAML)."""
        return cls.model_validate(data)


class SubstantialityAssessment(BaseModel):
    category: str = "unknown"  # e.g., 'substantial', 'non_substantial', 'ambiguous'
    rationale: Optional[Field_] = None
