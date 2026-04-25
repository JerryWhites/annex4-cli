import yaml
from pathlib import Path

import pytest

# This assumes the tests are run from the root of the project
REGULATION_PATH = Path(__file__).parent.parent / "annex4" / "regulation" / "versions"


def get_all_regulation_versions():
    """Finds all regulation version directories."""
    if not REGULATION_PATH.exists():
        return []
    return [
        d for d in REGULATION_PATH.iterdir() if d.is_dir() and d.name != "__pycache__"
    ]


@pytest.mark.parametrize("version_path", get_all_regulation_versions())
def test_yaml_files_are_valid(version_path: Path):
    """Test that all .yaml files in a regulation version are valid YAML."""
    yaml_files = list(version_path.glob("**/*.yaml"))
    assert len(yaml_files) > 0, f"No YAML files found in {version_path}"
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in {yaml_file}: {e}")


@pytest.mark.parametrize("version_path", get_all_regulation_versions())
def test_classifier_integrity(version_path: Path):
    """
    Tests the integrity of the classifier.yaml file for a regulation version.
    - All next_node references must point to a valid node in `tree` or `verdicts`.
    - Every node in `tree` must be reachable from the `start_node`.
    - Every verdict must have a citation.
    """
    classifier_file = version_path / "classification_rules" / "classifier.yaml"
    if not classifier_file.exists():
        pytest.skip(f"No classifier.yaml in {version_path}")
        return

    with open(classifier_file, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    all_nodes = set(spec["tree"].keys()) | set(spec["verdicts"].keys())

    # Check all next_node references are valid
    for node_id, node_data in spec["tree"].items():
        if node_data.get("next_node"):
            assert node_data["next_node"] in all_nodes, (
                f"[{node_id}] next_node '{node_data['next_node']}' is invalid"
            )
        if node_data.get("options"):
            for option in node_data["options"]:
                if "next_node" in option:
                    assert option["next_node"] in all_nodes, (
                        f"[{node_id}] option '{option['label']}' next_node '{option['next_node']}' is invalid"
                    )
        if node_data.get("next_node_logic"):
            for logic in node_data["next_node_logic"]:
                if "then" in logic:
                    assert logic["then"] in all_nodes, (
                        f"[{node_id}] logic 'then' target '{logic['then']}' is invalid"
                    )
                if "else" in logic:
                    assert logic["else"] in all_nodes, (
                        f"[{node_id}] logic 'else' target '{logic['else']}' is invalid"
                    )

    # Check all verdicts have citations
    for verdict_id, verdict_data in spec["verdicts"].items():
        assert "citation" in verdict_data and verdict_data["citation"], (
            f"Verdict '{verdict_id}' is missing a citation"
        )

    # Check reachability
    reachable_nodes = {spec["start_node"]}
    queue = [spec["start_node"]]

    while queue:
        current_id = queue.pop(0)
        if current_id in spec["verdicts"]:
            continue

        node_data = spec["tree"][current_id]

        next_nodes = []
        if node_data.get("next_node"):
            next_nodes.append(node_data["next_node"])
        if node_data.get("options"):
            for option in node_data["options"]:
                if "next_node" in option:
                    next_nodes.append(option["next_node"])
        if node_data.get("next_node_logic"):
            for logic in node_data["next_node_logic"]:
                if "then" in logic:
                    next_nodes.append(logic["then"])
                if "else" in logic:
                    next_nodes.append(logic["else"])

        for next_node in next_nodes:
            if next_node not in reachable_nodes:
                reachable_nodes.add(next_node)
                queue.append(next_node)

    unreachable = set(spec["tree"].keys()) - reachable_nodes
    assert not unreachable, f"Unreachable classifier nodes: {unreachable}"


# Placeholder test for SHA256 check.
# In a real CI, you would download the file from source_url and check its hash.
# For now, we just check that the field exists.
@pytest.mark.parametrize("version_path", get_all_regulation_versions())
def test_metadata_sha_placeholder(version_path: Path):
    """Check that metadata.yaml has a content_hash field."""
    metadata_file = version_path / "metadata.yaml"
    assert metadata_file.exists()
    with open(metadata_file, "r") as f:
        metadata = yaml.safe_load(f)
    assert "content_hash" in metadata and metadata["content_hash"]
