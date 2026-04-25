"""
Tests for annex4.core.validate.
"""

import pytest

from annex4.core.schema import (
    AnnexIVDossier,
    ProviderInfo,
    SystemMetadata,
    ComplianceClaim,
    Provenance,
    SystemIdentity,
    IntendedPurpose,
    GeneralDescription,
    DevelopmentProcess,
    DataGovernance,
    DataSource,
    BiasAnalysisItem,
    MonitoringFunctioningControl,
    AccuracyMetric,
    AccuracySubpopulationRow,
    RobustnessIssue,
    RiskManagement,
    RiskItem,
    PostMarketMonitoring,
    EUDeclarationOfConformity,
)
from annex4.core.validate import validate, _extract_val, _unfilled


def _prov() -> Provenance:
    return Provenance(
        source="manual",
        source_ref="test",
        extracted_at="2026-01-01",
        extractor_version="1.0",
        confidence=1.0,
    )


def _sm(value) -> SystemMetadata:
    return SystemMetadata(value=value, provenance=_prov())


def _cc(statement: str) -> ComplianceClaim:
    return ComplianceClaim(
        statement=statement,
        attested_by="CTO",
        attested_at="2026-01-15",
        evidence_refs=["ev-001"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_valid_dossier() -> AnnexIVDossier:
    """A dossier that satisfies every ERROR-level rule."""
    return AnnexIVDossier(
        general_description=GeneralDescription(
            provider=ProviderInfo(
                name="Acme AI GmbH",
                address="Unter den Linden 1, 10117 Berlin",
                contact_email="aigov@acme.example",
                authorized_signatory="Jane Smith, CTO",
            ),
            system=SystemIdentity(
                name="RiskScore Pro",
                version="1.0.0",
                classification="High-risk · Annex III §5(b)",
            ),
            intended_purpose=IntendedPurpose(
                description="Scores credit applicants on default risk.",
                intended_users="Loan officers at partner banks.",
                persons_affected="EU natural persons applying for credit.",
            ),
        ),
        development_process=DevelopmentProcess(
            methodology="Gradient boosted trees trained on historical loan data.",
            architecture_description="XGBoost ensemble with 500 estimators.",
            input_description="Structured applicant feature vector (42 fields).",
            output_description="Risk score 0–1000; decision threshold at 650.",
            data_governance=DataGovernance(
                training_sources=[
                    DataSource(
                        name="LoanHistory-EU",
                        origin="Internal CRM export 2018-2024",
                        volume="1,200,000 records",
                        license="Internal use only",
                    )
                ],
                bias_analysis=[
                    BiasAnalysisItem(
                        attribute="Gender: female",
                        population_share="48%",
                        reference_share="51%",
                        delta="-3 pp",
                        action_taken="Reweighting applied",
                    )
                ],
            ),
        ),
        monitoring_functioning_control=MonitoringFunctioningControl(
            capabilities_and_limitations="Works on EU applicants aged 18+. Not validated for non-EU data.",
            foreseeable_unintended_outcomes="Potential disparate impact on female applicants.",
            human_oversight_measures="All decisions reviewed by a loan officer before approval.",
            accuracy_metrics=[
                AccuracyMetric(
                    name="AUC-ROC",
                    aggregate_value="0.83",
                    subpopulation_breakdown=[
                        AccuracySubpopulationRow(
                            subpopulation="Gender: female",
                            value="0.81",
                            delta_vs_aggregate="-0.02",
                        ),
                    ],
                )
            ],
        ),
        risk_management=RiskManagement(
            process_description="Quarterly risk review by AI Governance Committee.",
            identified_risks=[
                RiskItem(
                    risk="Disparate impact on protected groups",
                    likelihood="Medium",
                    impact="High",
                    mitigation="Reweighting + mandatory human review",
                    residual_risk="Delta within ±0.03 threshold",
                    accepted_by="CTO, 2026-01-15",
                )
            ],
        ),
        post_market_monitoring=PostMarketMonitoring(
            monitoring_approach="Monthly AUC-ROC evaluation on live-labelled holdout.",
            key_performance_indicators=["AUC-ROC >= 0.80", "Fairness delta <= 0.05"],
            responsible_person="Head of AI Governance",
        ),
    )


# ---------------------------------------------------------------------------
# ERROR rules
# ---------------------------------------------------------------------------


class TestErrors:
    def test_blank_dossier_has_errors(self):
        report = validate(AnnexIVDossier())
        assert not report.is_valid
        assert len(report.errors) > 0

    def test_valid_dossier_has_no_errors(self):
        report = validate(_minimal_valid_dossier())
        assert report.is_valid, [str(e) for e in report.errors]

    @pytest.mark.parametrize(
        "field,setter",
        [
            (
                "provider.name",
                lambda d: setattr(d.general_description.provider, "name", ""),
            ),
            (
                "provider.address",
                lambda d: setattr(d.general_description.provider, "address", ""),
            ),
            (
                "provider.contact_email",
                lambda d: setattr(d.general_description.provider, "contact_email", ""),
            ),
            (
                "provider.authorized_signatory",
                lambda d: setattr(
                    d.general_description.provider, "authorized_signatory", ""
                ),
            ),
            (
                "system.name",
                lambda d: setattr(d.general_description.system, "name", ""),
            ),
            (
                "system.version",
                lambda d: setattr(d.general_description.system, "version", ""),
            ),
            (
                "system.classification",
                lambda d: setattr(d.general_description.system, "classification", ""),
            ),
            (
                "intended_purpose.description",
                lambda d: setattr(
                    d.general_description.intended_purpose, "description", ""
                ),
            ),
            (
                "intended_purpose.intended_users",
                lambda d: setattr(
                    d.general_description.intended_purpose, "intended_users", ""
                ),
            ),
            (
                "intended_purpose.persons_affected",
                lambda d: setattr(
                    d.general_description.intended_purpose, "persons_affected", ""
                ),
            ),
            (
                "development.methodology",
                lambda d: setattr(d.development_process, "methodology", ""),
            ),
            (
                "development.architecture",
                lambda d: setattr(
                    d.development_process, "architecture_description", ""
                ),
            ),
            (
                "development.input",
                lambda d: setattr(d.development_process, "input_description", ""),
            ),
            (
                "development.output",
                lambda d: setattr(d.development_process, "output_description", ""),
            ),
            (
                "mfc.capabilities",
                lambda d: setattr(
                    d.monitoring_functioning_control, "capabilities_and_limitations", ""
                ),
            ),
            (
                "mfc.unintended_outcomes",
                lambda d: setattr(
                    d.monitoring_functioning_control,
                    "foreseeable_unintended_outcomes",
                    "",
                ),
            ),
            (
                "mfc.human_oversight",
                lambda d: setattr(
                    d.monitoring_functioning_control, "human_oversight_measures", ""
                ),
            ),
            (
                "risk.process",
                lambda d: setattr(d.risk_management, "process_description", ""),
            ),
            (
                "pmm.approach",
                lambda d: setattr(d.post_market_monitoring, "monitoring_approach", ""),
            ),
        ],
    )
    def test_missing_required_field_raises_error(self, field, setter):
        dossier = _minimal_valid_dossier()
        setter(dossier)
        report = validate(dossier)
        assert not report.is_valid, f"Expected error for blank field: {field}"

    def test_no_risks_is_error(self):
        dossier = _minimal_valid_dossier()
        dossier.risk_management.identified_risks = []
        report = validate(dossier)
        codes = [i.code for i in report.errors]
        assert "E020" in codes

    def test_placeholder_text_counts_as_blank(self):
        dossier = _minimal_valid_dossier()
        dossier.general_description.intended_purpose.description = (
            "[REQUIRED] Describe precisely what the system does."
        )
        report = validate(dossier)
        assert not report.is_valid

    def test_open_high_severity_robustness_issue_is_error(self):
        dossier = _minimal_valid_dossier()
        dossier.monitoring_functioning_control.robustness_issues = [
            RobustnessIssue(
                id="R-01",
                category="Adversarial input",
                severity="High",
                status="Open",
                rationale="Under investigation",
            )
        ]
        report = validate(dossier)
        codes = [i.code for i in report.errors]
        assert "E018" in codes

    def test_open_medium_severity_robustness_issue_is_not_error(self):
        dossier = _minimal_valid_dossier()
        dossier.monitoring_functioning_control.robustness_issues = [
            RobustnessIssue(
                id="R-02",
                category="Edge case",
                severity="Medium",
                status="Open",
                rationale="Accepted",
            )
        ]
        report = validate(dossier)
        assert "E018" not in [i.code for i in report.errors]

    def test_notified_body_required_but_missing_is_error(self):
        dossier = _minimal_valid_dossier()
        dossier.eu_declaration_of_conformity = EUDeclarationOfConformity(
            notified_body_required=True,
            notified_body_name="",
            notified_body_certificate="",
        )
        report = validate(dossier)
        codes = [i.code for i in report.errors]
        assert "E021" in codes
        assert "E022" in codes


# ---------------------------------------------------------------------------
# WARNING rules
# ---------------------------------------------------------------------------


class TestWarnings:
    def test_no_bias_analysis_raises_warning(self):
        dossier = _minimal_valid_dossier()
        dossier.development_process.data_governance.bias_analysis = []
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W004" in codes

    def test_no_training_sources_raises_warning(self):
        dossier = _minimal_valid_dossier()
        dossier.development_process.data_governance.training_sources = []
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W002" in codes

    def test_no_accuracy_metrics_raises_warning(self):
        dossier = _minimal_valid_dossier()
        dossier.monitoring_functioning_control.accuracy_metrics = []
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W006" in codes

    def test_no_kpis_raises_warning(self):
        dossier = _minimal_valid_dossier()
        dossier.post_market_monitoring.key_performance_indicators = []
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W016" in codes

    def test_risk_missing_mitigation_raises_warning(self):
        dossier = _minimal_valid_dossier()
        dossier.risk_management.identified_risks[0].mitigation = ""
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W010" in codes

    def test_missing_declaration_date_raises_warning(self):
        dossier = _minimal_valid_dossier()
        dossier.eu_declaration_of_conformity = EUDeclarationOfConformity(
            declaration_date=""
        )
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W014" in codes

    def test_substantial_change_without_assessment_raises_warning(self):
        from annex4.core.schema import LifecycleChanges, LifecycleChange

        dossier = _minimal_valid_dossier()
        dossier.lifecycle_changes = LifecycleChanges(
            changes=[
                LifecycleChange(
                    field="Article10.data_sources",
                    change_description="Added new corpus",
                    trigger="Q2 refresh",
                    approved_by="CTO",
                    is_substantial=True,
                )
            ],
            substantiality_assessment="",
        )
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W012" in codes

    def test_metric_missing_subpopulation_breakdown_raises_warning(self):
        dossier = _minimal_valid_dossier()
        dossier.monitoring_functioning_control.accuracy_metrics = [
            AccuracyMetric(name="AUC-ROC", aggregate_value="0.83")
        ]
        report = validate(dossier)
        codes = [i.code for i in report.warnings]
        assert "W008" in codes


# ---------------------------------------------------------------------------
# INFO rules
# ---------------------------------------------------------------------------


class TestInfos:
    def test_no_evidence_index_raises_info(self):
        dossier = _minimal_valid_dossier()
        dossier.evidence_index = []
        report = validate(dossier)
        codes = [i.code for i in report.infos]
        assert "I003" in codes

    def test_no_harmonised_standards_raises_info(self):
        dossier = _minimal_valid_dossier()
        dossier.harmonised_standards = []
        report = validate(dossier)
        codes = [i.code for i in report.infos]
        assert "I004" in codes

    def test_no_git_commit_raises_info(self):
        dossier = _minimal_valid_dossier()
        dossier.general_description.system.git_commit = None
        report = validate(dossier)
        codes = [i.code for i in report.infos]
        assert "I005" in codes


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------


class TestReportStructure:
    def test_is_valid_false_when_errors(self):
        report = validate(AnnexIVDossier())
        assert report.is_valid is False

    def test_errors_warnings_infos_are_partitioned(self):
        report = validate(AnnexIVDossier())
        all_codes = {i.code for i in report.issues}
        error_codes = {i.code for i in report.errors}
        warning_codes = {i.code for i in report.warnings}
        info_codes = {i.code for i in report.infos}
        assert error_codes | warning_codes | info_codes == all_codes

    def test_issue_has_article_citation(self):
        report = validate(AnnexIVDossier())
        issues_with_citations = [i for i in report.issues if i.article]
        assert len(issues_with_citations) > 0

    def test_str_representation(self):
        report = validate(AnnexIVDossier())
        s = str(report.errors[0])
        assert "ERROR" in s
        assert "E0" in s


# ---------------------------------------------------------------------------
# Helper unit tests (_extract_val, _unfilled)
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_extract_val_plain_string(self):
        assert _extract_val("hello") == "hello"

    def test_extract_val_none(self):
        assert _extract_val(None) is None

    def test_extract_val_system_metadata(self):
        assert _extract_val(_sm("foo")) == "foo"

    def test_extract_val_compliance_claim(self):
        assert _extract_val(_cc("bar")) == "bar"

    def test_extract_val_dict_system_metadata(self):
        assert _extract_val({"kind": "system_metadata", "value": "baz"}) == "baz"

    def test_extract_val_dict_compliance_claim(self):
        assert _extract_val({"kind": "compliance_claim", "statement": "qux"}) == "qux"

    def test_unfilled_none(self):
        assert _unfilled(None) is True

    def test_unfilled_blank_string(self):
        assert _unfilled("") is True
        assert _unfilled("   ") is True

    def test_unfilled_placeholder_required(self):
        assert _unfilled("[REQUIRED] fill this") is True

    def test_unfilled_placeholder_if_applicable(self):
        assert _unfilled("[IF APPLICABLE] optional") is True

    def test_unfilled_valid_plain_string(self):
        assert _unfilled("actual content") is False

    def test_unfilled_system_metadata_with_value(self):
        assert _unfilled(_sm("some text")) is False

    def test_unfilled_system_metadata_blank_value(self):
        assert _unfilled(_sm("")) is True

    def test_unfilled_compliance_claim_with_statement(self):
        assert _unfilled(_cc("We attest this.")) is False

    def test_unfilled_compliance_claim_blank_statement(self):
        assert _unfilled(_cc("")) is True


# ---------------------------------------------------------------------------
# Specific error codes for Section 2 / 3 / 4 / 8 rules
# ---------------------------------------------------------------------------


class TestErrorCodes:
    @pytest.mark.parametrize(
        "field,setter,expected_code",
        [
            (
                "development.methodology",
                lambda d: setattr(d.development_process, "methodology", ""),
                "E011",
            ),
            (
                "development.architecture",
                lambda d: setattr(
                    d.development_process, "architecture_description", ""
                ),
                "E012",
            ),
            (
                "development.input",
                lambda d: setattr(d.development_process, "input_description", ""),
                "E013",
            ),
            (
                "development.output",
                lambda d: setattr(d.development_process, "output_description", ""),
                "E014",
            ),
            (
                "mfc.capabilities",
                lambda d: setattr(
                    d.monitoring_functioning_control, "capabilities_and_limitations", ""
                ),
                "E015",
            ),
            (
                "mfc.unintended_outcomes",
                lambda d: setattr(
                    d.monitoring_functioning_control,
                    "foreseeable_unintended_outcomes",
                    "",
                ),
                "E016",
            ),
            (
                "mfc.human_oversight",
                lambda d: setattr(
                    d.monitoring_functioning_control, "human_oversight_measures", ""
                ),
                "E017",
            ),
            (
                "risk.process",
                lambda d: setattr(d.risk_management, "process_description", ""),
                "E019",
            ),
            (
                "pmm.approach",
                lambda d: setattr(d.post_market_monitoring, "monitoring_approach", ""),
                "E023",
            ),
        ],
    )
    def test_blank_field_produces_expected_code(self, field, setter, expected_code):
        dossier = _minimal_valid_dossier()
        setter(dossier)
        report = validate(dossier)
        codes = [i.code for i in report.errors]
        assert expected_code in codes, f"Expected {expected_code} for blank {field}"


# ---------------------------------------------------------------------------
# Legal gap (LG001) tests
# ---------------------------------------------------------------------------


class TestLegalGap:
    def test_system_metadata_on_claim_required_field_triggers_lg001(self):
        dossier = _minimal_valid_dossier()
        dossier.monitoring_functioning_control.human_oversight_measures = _sm(
            "Automated oversight"
        )
        field_kinds = {
            "claim_required": [
                "monitoring_functioning_control.human_oversight_measures"
            ]
        }
        report = validate(dossier, field_kinds)
        codes = [i.code for i in report.legal_gaps]
        assert "LG001" in codes

    def test_compliance_claim_on_claim_required_field_does_not_trigger_lg001(self):
        dossier = _minimal_valid_dossier()
        dossier.monitoring_functioning_control.human_oversight_measures = _cc(
            "Human review before each decision."
        )
        field_kinds = {
            "claim_required": [
                "monitoring_functioning_control.human_oversight_measures"
            ]
        }
        report = validate(dossier, field_kinds)
        assert "LG001" not in [i.code for i in report.legal_gaps]

    def test_plain_string_on_claim_required_field_does_not_trigger_lg001(self):
        dossier = _minimal_valid_dossier()
        field_kinds = {
            "claim_required": [
                "monitoring_functioning_control.human_oversight_measures"
            ]
        }
        report = validate(dossier, field_kinds)
        assert "LG001" not in [i.code for i in report.legal_gaps]

    def test_no_field_kinds_means_no_legal_gaps(self):
        dossier = _minimal_valid_dossier()
        dossier.monitoring_functioning_control.human_oversight_measures = _sm("text")
        report = validate(dossier)
        assert report.legal_gaps == []
