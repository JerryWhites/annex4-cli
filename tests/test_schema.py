"""Tests for annex4.core.schema — Pydantic models and Field_ union."""

import pytest
from pydantic import ValidationError

from annex4.core.schema import (
    AnnexIVDossier,
    ComplianceClaim,
    DataGovernance,
    LifecycleChanges,
    PostMarketMonitoring,
    Provenance,
    ProviderInfo,
    RiskManagement,
    SystemMetadata,
)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_valid_construction(self):
        p = Provenance(
            source="mlflow",
            source_ref="run_123",
            extracted_at="2026-01-01",
            extractor_version="1.0",
            confidence=0.9,
        )
        assert p.source == "mlflow"
        assert p.confidence == 0.9

    def test_confidence_must_be_in_range(self):
        with pytest.raises(ValidationError):
            Provenance(
                source="manual",
                source_ref="x",
                extracted_at="2026-01-01",
                extractor_version="1.0",
                confidence=1.5,
            )

    def test_invalid_source_literal_rejected(self):
        with pytest.raises(ValidationError):
            Provenance(
                source="invalid_source",
                source_ref="x",
                extracted_at="2026-01-01",
                extractor_version="1.0",
                confidence=0.5,
            )


# ---------------------------------------------------------------------------
# SystemMetadata / ComplianceClaim
# ---------------------------------------------------------------------------


def _prov() -> Provenance:
    return Provenance(
        source="manual",
        source_ref="test",
        extracted_at="2026-01-01",
        extractor_version="1.0",
        confidence=1.0,
    )


class TestSystemMetadata:
    def test_kind_is_literal(self):
        sm = SystemMetadata(value="foo", provenance=_prov())
        assert sm.kind == "system_metadata"

    def test_accepts_various_value_types(self):
        for val in ("text", 42, 3.14, True, [1, 2], {"k": "v"}):
            sm = SystemMetadata(value=val, provenance=_prov())
            assert sm.value == val


class TestComplianceClaim:
    def test_kind_is_literal(self):
        cc = ComplianceClaim(
            statement="Attested.",
            attested_by="CTO",
            attested_at="2026-01-15",
            evidence_refs=["ev-001"],
        )
        assert cc.kind == "compliance_claim"

    def test_requires_legal_confirmation_defaults_false(self):
        cc = ComplianceClaim(
            statement="s",
            attested_by="a",
            attested_at="d",
            evidence_refs=[],
        )
        assert cc.requires_legal_confirmation is False


# ---------------------------------------------------------------------------
# Field_ union — accepts all permitted types
# ---------------------------------------------------------------------------


class TestFieldUnion:
    @pytest.mark.parametrize("value", ["plain string", 42, 3.14, True, False])
    def test_accepts_primitives(self, value):
        p = ProviderInfo(name=value)
        assert p.name == value

    def test_accepts_system_metadata(self):
        sm = SystemMetadata(value="Acme", provenance=_prov())
        p = ProviderInfo(name=sm)
        assert isinstance(p.name, SystemMetadata)

    def test_accepts_compliance_claim(self):
        cc = ComplianceClaim(
            statement="Acme AI GmbH",
            attested_by="CTO",
            attested_at="2026-01-01",
            evidence_refs=[],
        )
        p = ProviderInfo(name=cc)
        assert isinstance(p.name, ComplianceClaim)

    def test_optional_field_defaults_to_none(self):
        p = ProviderInfo()
        assert p.name is None


# ---------------------------------------------------------------------------
# AnnexIVDossier construction
# ---------------------------------------------------------------------------


class TestAnnexIVDossierConstruction:
    def test_default_construction_succeeds(self):
        dossier = AnnexIVDossier()
        assert dossier.meta.generated_by == "annex4-cli"

    def test_all_nine_sections_present_by_default(self):
        d = AnnexIVDossier()
        assert d.general_description is not None
        assert d.development_process is not None
        assert d.monitoring_functioning_control is not None
        assert d.risk_management is not None
        assert d.lifecycle_changes is not None
        assert d.harmonised_standards == []
        assert d.eu_declaration_of_conformity is not None
        assert d.post_market_monitoring is not None
        assert d.serious_incidents == []
        assert d.evidence_index == []

    def test_from_yaml_dict_plain_strings(self):
        raw = {
            "general_description": {
                "provider": {"name": "Acme"},
                "system": {"name": "TestSys", "version": "1.0"},
            }
        }
        d = AnnexIVDossier.from_yaml_dict(raw)
        assert d.general_description.provider.name == "Acme"
        assert d.general_description.system.name == "TestSys"

    def test_from_yaml_dict_system_metadata_wrapped(self):
        raw = {
            "general_description": {
                "system": {
                    "name": {
                        "kind": "system_metadata",
                        "value": "WrappedSystem",
                        "provenance": {
                            "source": "mlflow",
                            "source_ref": "run_1",
                            "extracted_at": "2026-01-01",
                            "extractor_version": "1.0",
                            "confidence": 0.95,
                        },
                    }
                }
            }
        }
        d = AnnexIVDossier.from_yaml_dict(raw)
        assert isinstance(d.general_description.system.name, SystemMetadata)
        assert d.general_description.system.name.value == "WrappedSystem"

    def test_from_yaml_dict_compliance_claim_wrapped(self):
        raw = {
            "general_description": {
                "provider": {
                    "authorized_signatory": {
                        "kind": "compliance_claim",
                        "statement": "Jane Smith, CTO",
                        "attested_by": "Board",
                        "attested_at": "2026-01-15",
                        "evidence_refs": ["sig-001"],
                    }
                }
            }
        }
        d = AnnexIVDossier.from_yaml_dict(raw)
        assert isinstance(
            d.general_description.provider.authorized_signatory, ComplianceClaim
        )
        assert (
            d.general_description.provider.authorized_signatory.statement
            == "Jane Smith, CTO"
        )

    def test_regulation_version_defaults(self):
        d = AnnexIVDossier()
        assert d.general_description.system.regulation_version == "2024-1689_base"
        assert d.meta.regulation_version == "2024-1689_base"


# ---------------------------------------------------------------------------
# model_dump round-trip
# ---------------------------------------------------------------------------


class TestModelDumpRoundTrip:
    def test_plain_string_survives_dump_and_reload(self):
        original = AnnexIVDossier.from_yaml_dict(
            {"general_description": {"system": {"name": "MySystem", "version": "2.0"}}}
        )
        dumped = original.model_dump()
        reloaded = AnnexIVDossier.from_yaml_dict(dumped)
        assert reloaded.general_description.system.name == "MySystem"

    def test_system_metadata_survives_dump_and_reload(self):
        sm = SystemMetadata(value="MLSys", provenance=_prov())
        d = AnnexIVDossier()
        d.general_description.system.name = sm
        dumped = d.model_dump()
        reloaded = AnnexIVDossier.from_yaml_dict(dumped)
        assert isinstance(reloaded.general_description.system.name, SystemMetadata)
        assert reloaded.general_description.system.name.value == "MLSys"


# ---------------------------------------------------------------------------
# Nested model defaults
# ---------------------------------------------------------------------------


class TestNestedDefaults:
    def test_data_governance_lists_default_empty(self):
        dg = DataGovernance()
        assert dg.training_sources == []
        assert dg.bias_analysis == []

    def test_risk_management_identified_risks_default_empty(self):
        rm = RiskManagement()
        assert rm.identified_risks == []

    def test_lifecycle_changes_default_empty(self):
        lc = LifecycleChanges()
        assert lc.changes == []

    def test_post_market_monitoring_kpis_default_empty(self):
        pmm = PostMarketMonitoring()
        assert pmm.key_performance_indicators == []
