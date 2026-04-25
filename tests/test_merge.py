"""Tests for annex4.core.merge and annex4.ingestors.base."""

from annex4.core.merge import (
    deep_merge,
    merge_ingestor_outputs,
    _is_sm,
    _resolve_conflict,
)
from annex4.ingestors.base import Ingestor, IngestorOutput


def _sm(value, extracted_at="2026-01-01T00:00:00+00:00", source="mlflow"):
    return {
        "kind": "system_metadata",
        "value": value,
        "provenance": {
            "source": source,
            "source_ref": "run_1",
            "extracted_at": extracted_at,
            "extractor_version": "1.0",
            "confidence": 0.9,
        },
    }


# ---------------------------------------------------------------------------
# deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_flat_disjoint_keys(self):
        assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_flat_override(self):
        assert deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_recursive_merge(self):
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 10, "d": 3}}
        result = deep_merge(base, override)
        assert result == {"a": {"b": 10, "c": 2, "d": 3}}

    def test_non_dict_in_base_overwritten_by_dict(self):
        result = deep_merge({"a": "scalar"}, {"a": {"nested": True}})
        assert result == {"a": {"nested": True}}

    def test_dict_in_base_overwritten_by_non_dict(self):
        result = deep_merge({"a": {"x": 1}}, {"a": "scalar"})
        assert result == {"a": "scalar"}

    def test_inputs_not_mutated(self):
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        deep_merge(base, override)
        assert base == {"a": {"b": 1}}
        assert override == {"a": {"c": 2}}

    def test_empty_override(self):
        assert deep_merge({"a": 1}, {}) == {"a": 1}

    def test_empty_base(self):
        assert deep_merge({}, {"a": 1}) == {"a": 1}


# ---------------------------------------------------------------------------
# merge_ingestor_outputs
# ---------------------------------------------------------------------------


class TestMergeIngestorOutputs:
    def test_empty_list_returns_empty(self):
        assert merge_ingestor_outputs([]) == {}

    def test_single_output(self):
        out = IngestorOutput(data={"a": 1}, source_name="x", priority=50)
        assert merge_ingestor_outputs([out]) == {"a": 1}

    def test_higher_priority_wins_conflict(self):
        low = IngestorOutput(data={"name": "low_val"}, source_name="low", priority=10)
        high = IngestorOutput(
            data={"name": "high_val"}, source_name="high", priority=90
        )
        result = merge_ingestor_outputs([high, low])  # order shouldn't matter
        assert result["name"] == "high_val"

    def test_lower_priority_fills_gaps(self):
        low = IngestorOutput(
            data={"a": "from_low", "b": "only_low"}, source_name="low", priority=10
        )
        high = IngestorOutput(data={"a": "from_high"}, source_name="high", priority=90)
        result = merge_ingestor_outputs([low, high])
        assert result["a"] == "from_high"
        assert result["b"] == "only_low"

    def test_base_dict_lowest_priority(self):
        base = {"a": "base", "b": "base_only"}
        out = IngestorOutput(data={"a": "override"}, source_name="x", priority=50)
        result = merge_ingestor_outputs([out], base=base)
        assert result["a"] == "override"
        assert result["b"] == "base_only"

    def test_nested_merge(self):
        o1 = IngestorOutput(
            data={"system": {"name": "A", "version": "1.0"}},
            source_name="mlflow",
            priority=30,
        )
        o2 = IngestorOutput(
            data={"system": {"name": "A", "classification": "High-risk"}},
            source_name="yaml",
            priority=80,
        )
        result = merge_ingestor_outputs([o1, o2])
        assert result["system"]["name"] == "A"
        assert result["system"]["version"] == "1.0"
        assert result["system"]["classification"] == "High-risk"

    def test_produces_valid_dossier(self, tmp_path):
        from annex4.core.schema import AnnexIVDossier
        from annex4.ingestors.yaml_override import YAMLOverrideIngestor

        yaml_file = tmp_path / "patch.yaml"
        yaml_file.write_text(
            "general_description:\n  system:\n    name: Merged System\n    version: '2.0'\n"
        )
        ingestor = YAMLOverrideIngestor()
        output = ingestor.ingest(path=yaml_file)
        merged = merge_ingestor_outputs([output])
        dossier = AnnexIVDossier.from_yaml_dict(merged)
        from annex4.core.validate import _extract_val

        assert _extract_val(dossier.general_description.system.name) == "Merged System"


# ---------------------------------------------------------------------------
# IngestorOutput dataclass
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SystemMetadata conflict resolution
# ---------------------------------------------------------------------------


class TestSystemMetadataConflictResolution:
    def test_is_sm_true_for_system_metadata_dict(self):
        assert _is_sm({"kind": "system_metadata", "value": "x", "provenance": {}})

    def test_is_sm_false_for_plain_dict(self):
        assert not _is_sm({"name": "foo"})

    def test_is_sm_false_for_string(self):
        assert not _is_sm("hello")

    def test_resolve_conflict_picks_newer_timestamp(self):
        old = _sm("old_value", "2025-01-01T00:00:00+00:00")
        new = _sm("new_value", "2026-01-01T00:00:00+00:00")
        result = _resolve_conflict(old, new)
        assert result["value"] == "new_value"
        assert result["conflict_resolved"] is True

    def test_resolve_conflict_keeps_existing_when_newer(self):
        existing = _sm("existing", "2026-06-01T00:00:00+00:00")
        incoming = _sm("incoming", "2026-01-01T00:00:00+00:00")
        result = _resolve_conflict(existing, incoming)
        assert result["value"] == "existing"
        assert result["conflict_resolved"] is True

    def test_deep_merge_sm_conflict_uses_timestamp_resolution(self):
        base = {"field": _sm("old", "2025-01-01T00:00:00+00:00")}
        override = {"field": _sm("new", "2026-01-01T00:00:00+00:00")}
        result = deep_merge(base, override)
        assert result["field"]["value"] == "new"
        assert result["field"]["conflict_resolved"] is True

    def test_deep_merge_sm_conflict_existing_wins_when_newer(self):
        base = {"field": _sm("recent", "2026-06-01T00:00:00+00:00")}
        override = {"field": _sm("stale", "2025-01-01T00:00:00+00:00")}
        result = deep_merge(base, override)
        assert result["field"]["value"] == "recent"

    def test_plain_value_still_overwritten_by_override(self):
        result = deep_merge({"a": "old"}, {"a": "new"})
        assert result["a"] == "new"

    def test_sm_overwriting_plain_string(self):
        sm_val = _sm("from_mlflow", "2026-01-01T00:00:00+00:00")
        result = deep_merge({"a": "plain"}, {"a": sm_val})
        assert result["a"]["value"] == "from_mlflow"


class TestIngestorOutput:
    def test_default_priority(self):
        out = IngestorOutput(data={}, source_name="test")
        assert out.priority == 50

    def test_custom_priority(self):
        out = IngestorOutput(data={}, source_name="test", priority=80)
        assert out.priority == 80


# ---------------------------------------------------------------------------
# Ingestor protocol structural check
# ---------------------------------------------------------------------------


class TestIngestorProtocol:
    def test_yaml_override_satisfies_protocol(self):
        from annex4.ingestors.yaml_override import YAMLOverrideIngestor

        assert isinstance(YAMLOverrideIngestor(), Ingestor)

    def test_mlflow_satisfies_protocol(self):
        from annex4.ingestors.mlflow_ingestor import MLflowIngestor

        assert isinstance(MLflowIngestor(), Ingestor)

    def test_hf_satisfies_protocol(self):
        from annex4.ingestors.hf_ingestor import HuggingFaceIngestor

        assert isinstance(HuggingFaceIngestor(), Ingestor)

    def test_giskard_satisfies_protocol(self):
        from annex4.ingestors.giskard_ingestor import GiskardIngestor

        assert isinstance(GiskardIngestor(), Ingestor)
