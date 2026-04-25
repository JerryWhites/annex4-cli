"""
Generates a new, empty Annex IV dossier file from a guided template.
"""

from pathlib import Path

# Raw YAML string so that helpful inline comments are preserved for the user.
_PROVIDER_TEMPLATE = """\
# =============================================================================
# Annex IV Technical Documentation Dossier
# Regulation (EU) 2024/1689 — Article 11 and Annex IV
#
# Fill in every field below, then run:
#   annex4 render dossier.yaml --output documentation.md
#
# Fields marked [REQUIRED] must be completed before the document is valid.
# Fields marked [IF APPLICABLE] only need filling when relevant to your system.
# =============================================================================

meta:
  generated_by: annex4-cli
  regulation_version: 2024-1689_base
  dossier_schema_version: "1.0.0"
  notes: ""  # Optional free-text notes for internal use

# =============================================================================
# SECTION 1 — General description of the AI system
# Annex IV §1 / Articles 3, 13
# =============================================================================

general_description:

  provider:
    name: ""                        # [REQUIRED] Legal name of the provider entity
    registration_number: ""         # [IF APPLICABLE] Company reg. number / VAT ID
    address: ""                     # [REQUIRED] Registered office address
    contact_email: ""               # [REQUIRED] Point of contact for market surveillance
    authorized_signatory: ""        # [REQUIRED] Name and role of the person signing off
    ai_governance_owner: ""         # [IF APPLICABLE] Name and role of AI governance lead
    eu_representative: ""           # [IF APPLICABLE] Only if provider is outside the EU

  system:
    name: ""                        # [REQUIRED] Marketing / product name of the system
    version: ""                     # [REQUIRED] Version string, e.g. "1.0.0"
    git_commit: ""                  # [IF APPLICABLE] Git SHA or model-registry ID
    release_date: ""                # [IF APPLICABLE] ISO 8601, e.g. "2026-01-15"
    classification: ""              # [REQUIRED] e.g. "High-risk · Annex III §4(a)"
    annex_iii_category: ""          # [IF APPLICABLE] e.g. "Employment, workers management"
    regulation_version: 2024-1689_base

  intended_purpose:
    description: >
      [REQUIRED] Describe precisely what the system does and what decisions it
      supports or makes. Include what it does NOT do (e.g., does not take final
      hiring decisions).
    intended_users: >
      [REQUIRED] Who operates or deploys this system (e.g., "HR recruiters at
      mid-to-large enterprises across the EU").
    deployment_form: ""             # e.g. "Multi-tenant SaaS, HTTPS API + web app"
    geographic_scope: ""            # e.g. "EU Member States only (Frankfurt data residency)"
    persons_affected: >
      [REQUIRED] Natural persons whose data is processed or who are subject to
      decisions made with this system.
    foreseeable_misuse:
      - ""  # [IF APPLICABLE] List each reasonably foreseeable misuse scenario


# =============================================================================
# SECTION 2 — Detailed description of elements and development process
# Annex IV §2 / Article 10 (data governance)
# =============================================================================

development_process:

  methodology: >
    [REQUIRED] Describe the overall development methodology (e.g., supervised
    learning, fine-tuning of a pre-trained model, rule-based post-processing).
  architecture_description: >
    [REQUIRED] Describe the system architecture — model type, number of
    parameters, key components, how sub-systems interact.
  input_description: >
    [REQUIRED] What data does the system ingest at inference time?
    (e.g., "Structured JSON résumé plus plain-text job description")
  output_description: >
    [REQUIRED] What does the system produce?
    (e.g., "Ranked list of up to 50 candidates with relevance scores and
    feature-level explanations")
  pre_trained_components: ""        # [IF APPLICABLE] Third-party models or embeddings used
  design_choices_rationale: ""      # [IF APPLICABLE] Key design decisions and why they were made

  data_governance:

    training_sources:
      - name: ""                    # [REQUIRED if trained] Dataset name
        origin: ""                  # Where it came from
        volume: ""                  # e.g. "2,400,000 records"
        license: ""                 # e.g. "CC-BY 4.0" or "Internal use only"
        evidence_uri: ""            # [IF APPLICABLE] URI to dataset card / DVC path

    validation_sources:
      - name: ""
        origin: ""
        volume: ""
        license: ""
        evidence_uri: ""

    test_sources:
      - name: ""
        origin: ""
        volume: ""
        license: ""
        evidence_uri: ""

    # Article 10(2)(f)-(g): bias examination and gap identification
    bias_analysis:
      - attribute: ""               # e.g. "Inferred gender: female"
        population_share: ""        # e.g. "44.8%"
        reference_share: ""         # e.g. "48.2% (EU Labour Force Survey)"
        delta: ""                   # e.g. "-3.4 pp"
        action_taken: ""            # e.g. "Post-hoc reweighting applied"

    residual_data_gaps: >
      [IF APPLICABLE] Describe any remaining gaps that could not be fully
      remediated and how they are disclosed to deployers.
    data_collection_procedures: >
      [IF APPLICABLE] Describe de-identification, pseudonymisation, and
      data-quality procedures applied before training.
    special_category_data: >
      [IF APPLICABLE] If Article 9 GDPR special-category data is processed,
      describe the legal basis and safeguards under Article 10(5) AI Act.


# =============================================================================
# SECTION 3 — Monitoring, functioning and control
# Annex IV §3 / Article 15 (accuracy, robustness, cybersecurity)
# =============================================================================

monitoring_functioning_control:

  capabilities_and_limitations: >
    [REQUIRED] Describe what the system can and cannot do reliably.
    Include known edge cases, language/demographic coverage gaps, etc.
  foreseeable_unintended_outcomes: >
    [REQUIRED] Describe what could go wrong if the system fails or
    is used incorrectly (e.g., disparate impact, false rankings).
  human_oversight_measures: >
    [REQUIRED] Describe the human oversight mechanisms (Article 14):
    who reviews outputs, what stop-function exists, audit logging, etc.

  # Article 15(1)(a): accuracy metrics
  accuracy_metrics:
    - name: ""                      # e.g. "nDCG@20"
      aggregate_value: ""           # e.g. "0.812"
      confidence_interval: ""       # e.g. "[0.794, 0.828] (95% bootstrap CI)"
      methodology_note: ""          # e.g. "Blind holdout of 50,000 pairs"
      subpopulation_breakdown:
        - subpopulation: ""         # e.g. "Inferred gender: female"
          n: ""                     # e.g. "22,402"
          value: ""                 # e.g. "0.799"
          confidence_interval: ""
          delta_vs_aggregate: ""    # e.g. "-0.013"

  # Article 15(1)(b): robustness testing
  robustness_issues:
    - id: "R-01"
      category: ""                  # e.g. "Keyword stuffing"
      severity: ""                  # High / Medium / Low
      status: ""                    # Mitigated / Accepted / Open
      rationale: ""

  # Article 15(1)(c): cybersecurity
  cybersecurity_measures: >
    [IF APPLICABLE] Describe security controls protecting the model and
    inference endpoints (e.g., mTLS, tenant isolation, red-team cadence,
    model signing).


# =============================================================================
# SECTION 4 — Risk management system
# Annex IV §4 / Article 9
# =============================================================================

risk_management:

  process_description: >
    [REQUIRED] Describe the risk management process: when it runs (lifecycle
    gates), who owns it, how findings are escalated and approved.

  identified_risks:
    - risk: ""                      # [REQUIRED] Short name for the risk
      likelihood: ""                # High / Medium / Low
      impact: ""                    # High / Medium / Low
      mitigation: ""                # Controls applied
      residual_risk: ""             # What remains after mitigation
      accepted_by: ""               # Name · Role · Date

  residual_risk_acceptance: >
    [IF APPLICABLE] Describe who accepted the residual risks and on what basis,
    and how the acceptance decision is documented.


# =============================================================================
# SECTION 5 — Changes made throughout the lifecycle
# Annex IV §5 / Article 43(4)
# =============================================================================

lifecycle_changes:

  previous_version: ""             # [IF APPLICABLE] e.g. "v1.2.0"

  changes:
    - field: ""                    # e.g. "Article15.accuracy_metrics.ndcg_at_20"
      change_description: ""       # e.g. "0.798 → 0.812"
      trigger: ""                  # e.g. "Q2 data refresh and retraining"
      approved_by: ""              # Name · Role · Date
      is_substantial: false        # true triggers re-assessment obligation

  substantiality_assessment: >
    [IF APPLICABLE] Explain which changes are substantial modifications
    (requiring updated conformity declaration) and why.


# =============================================================================
# SECTION 6 — Harmonised standards applied
# Annex IV §6
# =============================================================================

harmonised_standards:
  - standard: ""                   # e.g. "ISO/IEC 42001:2023"
    clause: ""                     # e.g. "§6.1.2 AI risk assessment"
    conformance: ""                # Full / Partial / N/A
    evidence: ""                   # [IF APPLICABLE] e.g. reference to audit report


# =============================================================================
# SECTION 7 — EU declaration of conformity
# Annex IV §7 / Article 47
# =============================================================================

eu_declaration_of_conformity:
  declaration_reference: ""        # [REQUIRED for market placement] Document ref / number
  declaration_date: ""             # [REQUIRED] ISO 8601 date
  notified_body_required: false    # Set to true if Article 43 requires it
  notified_body_name: ""           # [IF APPLICABLE]
  notified_body_certificate: ""    # [IF APPLICABLE] Certificate number
  notes: ""


# =============================================================================
# SECTION 8 — Post-market monitoring plan
# Annex IV §8 / Article 72
# =============================================================================

post_market_monitoring:
  monitoring_approach: >
    [REQUIRED] How do you monitor system performance after deployment?
    (e.g., "Weekly canary evaluation on rolling holdout; automated rollback
    on >2σ drift")
  key_performance_indicators:
    - ""                           # e.g. "nDCG@20 on live-labelled sample"
    - ""                           # e.g. "Fairness delta across gender groups"
  drift_detection_method: ""       # [IF APPLICABLE]
  update_trigger_thresholds: ""    # [IF APPLICABLE] e.g. ">2σ from baseline"
  responsible_person: ""           # Name · Role
  review_frequency: ""             # e.g. "Quarterly + event-triggered"


# =============================================================================
# SECTION 9 — Serious incidents log
# Annex IV §9 / Article 73
# =============================================================================

serious_incidents: []
# Uncomment and fill in when a serious incident occurs:
# - incident_id: "INC-001"
#   date: "2026-01-01"
#   description: ""
#   severity: ""               # Critical / High / Medium
#   root_cause: ""
#   corrective_action: ""
#   reported_to: ""            # e.g. "National market surveillance authority"


# =============================================================================
# APPENDIX A — Evidence index
# =============================================================================

evidence_index: []
# Uncomment and populate:
# - id: "E-01"
#   type: "MLflow run"
#   uri: "mlflow://prod/exp-14/run-abc123"
#   used_in_sections:
#     - "Section 2"
#     - "Section 3"
"""

_DEPLOYER_TEMPLATE = """\
# =============================================================================
# Annex IV Technical Documentation — Deployer Supplement
# Regulation (EU) 2024/1689 — Article 26 obligations
#
# As a deployer, your primary obligation is to implement the provider's
# instructions for use and establish appropriate human oversight.
# Fill in the fields relevant to your deployment context.
# =============================================================================

meta:
  generated_by: annex4-cli
  regulation_version: 2024-1689_base
  dossier_schema_version: "1.0.0"
  notes: "Deployer supplement — to be used alongside the provider's Annex IV dossier."

general_description:

  provider:
    name: ""                        # [REQUIRED] Your organisation's legal name
    registration_number: ""
    address: ""
    contact_email: ""
    authorized_signatory: ""
    ai_governance_owner: ""
    eu_representative: ""

  system:
    name: ""                        # Name of the AI system you are deploying
    version: ""                     # Version you are deploying
    classification: ""              # As stated by the provider
    regulation_version: 2024-1689_base

  intended_purpose:
    description: >
      [REQUIRED] Describe your specific deployment context and use case,
      which may be narrower than the provider's intended purpose.
    intended_users: >
      [REQUIRED] Who in your organisation uses this system?
    persons_affected: >
      [REQUIRED] Natural persons affected within your deployment context.
    foreseeable_misuse:
      - ""

monitoring_functioning_control:
  capabilities_and_limitations: >
    Document any limitations observed in your deployment context.
  foreseeable_unintended_outcomes: ""
  human_oversight_measures: >
    [REQUIRED] Describe how human oversight is implemented in your workflows.
  accuracy_metrics: []
  robustness_issues: []

risk_management:
  process_description: >
    [REQUIRED] Describe your deployer-side risk assessment (Article 26(2)).
  identified_risks:
    - risk: ""
      likelihood: ""
      impact: ""
      mitigation: ""
      residual_risk: ""
      accepted_by: ""
  residual_risk_acceptance: ""

lifecycle_changes:
  previous_version: ""
  changes: []
  substantiality_assessment: ""

harmonised_standards: []

eu_declaration_of_conformity:
  declaration_reference: ""
  declaration_date: ""
  notified_body_required: false
  notes: "Deployer is not required to issue a declaration of conformity under Article 47."

post_market_monitoring:
  monitoring_approach: >
    [REQUIRED] How do you monitor the system in your deployment?
  key_performance_indicators: []
  responsible_person: ""
  review_frequency: ""

serious_incidents: []

evidence_index: []
"""


def create_dossier_template(output_path: Path, role: str) -> None:
    """
    Creates a new Annex IV dossier YAML template at the specified path.

    Args:
        output_path: Where to write the template file.
        role: 'provider' or 'deployer'.
    """
    template = _PROVIDER_TEMPLATE if role == "provider" else _DEPLOYER_TEMPLATE
    output_path.write_text(template, encoding="utf-8")
