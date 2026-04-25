"""Tests for annex4.render.html."""


from annex4.core.schema import (
    AnnexIVDossier,
    GeneralDescription,
    ProviderInfo,
    SystemIdentity,
    IntendedPurpose,
    DevelopmentProcess,
    DataGovernance,
    MonitoringFunctioningControl,
    AccuracyMetric,
    AccuracySubpopulationRow,
    RobustnessIssue,
    RiskManagement,
    RiskItem,
    PostMarketMonitoring,
    SystemMetadata,
    ComplianceClaim,
    Provenance,
)
from annex4.render.html import render_html, _field_val


def _prov() -> Provenance:
    return Provenance(
        source="manual", source_ref="test", extracted_at="2026-01-01",
        extractor_version="1.0", confidence=1.0,
    )


def _minimal_dossier() -> AnnexIVDossier:
    return AnnexIVDossier(
        general_description=GeneralDescription(
            provider=ProviderInfo(
                name="Acme AI GmbH",
                address="Unter den Linden 1, Berlin",
                contact_email="aigov@acme.example",
                authorized_signatory="Jane Smith, CTO",
            ),
            system=SystemIdentity(
                name="RiskScore Pro",
                version="1.0.0",
                classification="High-risk",
            ),
            intended_purpose=IntendedPurpose(
                description="Scores credit applicants.",
                intended_users="Loan officers.",
                persons_affected="EU natural persons.",
            ),
        ),
        development_process=DevelopmentProcess(
            methodology="XGBoost ensemble",
            data_governance=DataGovernance(),
        ),
        monitoring_functioning_control=MonitoringFunctioningControl(
            capabilities_and_limitations="Works on EU applicants aged 18+.",
            foreseeable_unintended_outcomes="Potential bias.",
            human_oversight_measures="All decisions reviewed.",
        ),
        risk_management=RiskManagement(
            process_description="Quarterly review.",
            identified_risks=[
                RiskItem(
                    risk="Disparate impact",
                    likelihood="Medium",
                    impact="High",
                    mitigation="Reweighting",
                    residual_risk="Within threshold",
                    accepted_by="CTO",
                )
            ],
        ),
        post_market_monitoring=PostMarketMonitoring(
            monitoring_approach="Monthly AUC evaluation.",
            key_performance_indicators=["AUC-ROC >= 0.80"],
        ),
    )


# ---------------------------------------------------------------------------
# _field_val filter
# ---------------------------------------------------------------------------


class TestFieldValFilter:
    def test_plain_string(self):
        assert _field_val("hello") == "hello"

    def test_none_returns_dash(self):
        assert _field_val(None) == "—"

    def test_system_metadata(self):
        sm = SystemMetadata(value="1.0.0", provenance=_prov())
        assert _field_val(sm) == "1.0.0"

    def test_compliance_claim(self):
        cc = ComplianceClaim(
            statement="Attested.",
            attested_by="CTO",
            attested_at="2026-01-15",
            evidence_refs=[],
        )
        assert _field_val(cc) == "Attested."

    def test_integer_value(self):
        assert _field_val(42) == "42"


# ---------------------------------------------------------------------------
# render_html output tests
# ---------------------------------------------------------------------------


class TestRenderHTML:
    def test_returns_string(self):
        html = render_html(_minimal_dossier())
        assert isinstance(html, str)

    def test_is_valid_html_structure(self):
        html = render_html(_minimal_dossier())
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_contains_system_name(self):
        html = render_html(_minimal_dossier())
        assert "RiskScore Pro" in html

    def test_contains_provider_name(self):
        html = render_html(_minimal_dossier())
        assert "Acme AI GmbH" in html

    def test_contains_all_nine_section_headings(self):
        html = render_html(_minimal_dossier())
        for n in range(1, 10):
            assert f'id="s{n}"' in html

    def test_contains_evidence_appendix(self):
        html = render_html(_minimal_dossier())
        assert 'id="sa"' in html

    def test_regulation_citation_present(self):
        html = render_html(_minimal_dossier())
        assert "2024/1689" in html

    def test_system_metadata_value_extracted(self):
        dossier = _minimal_dossier()
        dossier.general_description.system.name = SystemMetadata(
            value="WrappedSystem", provenance=_prov()
        )
        html = render_html(dossier)
        assert "WrappedSystem" in html
        assert "system_metadata" not in html

    def test_none_field_renders_as_dash(self):
        dossier = _minimal_dossier()
        dossier.general_description.provider.registration_number = None
        html = render_html(dossier)
        assert "—" in html

    def test_contains_risk_items(self):
        html = render_html(_minimal_dossier())
        assert "Disparate impact" in html

    def test_contains_methodology(self):
        html = render_html(_minimal_dossier())
        assert "XGBoost ensemble" in html

    def test_accuracy_metrics_rendered(self):
        dossier = _minimal_dossier()
        dossier.monitoring_functioning_control.accuracy_metrics = [
            AccuracyMetric(
                name="AUC-ROC",
                aggregate_value="0.83",
                subpopulation_breakdown=[
                    AccuracySubpopulationRow(subpopulation="Female", value="0.81", delta_vs_aggregate="-0.02"),
                ],
            )
        ]
        html = render_html(dossier)
        assert "AUC-ROC" in html
        assert "0.83" in html
        assert "Female" in html

    def test_empty_sections_render_gracefully(self):
        dossier = AnnexIVDossier()
        html = render_html(dossier)
        assert "<!DOCTYPE html>" in html
        assert "No training data sources documented" in html
        assert "No risks identified" in html

    def test_robustness_issues_rendered(self):
        dossier = _minimal_dossier()
        dossier.monitoring_functioning_control.robustness_issues = [
            RobustnessIssue(
                id="R-01", category="Adversarial input",
                severity="High", status="Open", rationale="Under investigation",
            )
        ]
        html = render_html(dossier)
        assert "R-01" in html
        assert "Adversarial input" in html
