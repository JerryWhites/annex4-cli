"""
Tests for the documentation generator.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from annex4.cli import generate

# A minimal valid classification file for testing
MINIMAL_CLASSIFICATION = {
    "verdict": {
        "verdict": "Minimal-Risk",
        "citation": "N/A",
        "explanation_markdown": "The system does not fall into prohibited, high-risk, or limited-risk categories.",
        "next_steps": "No specific obligations under the EU AI Act apply.",
        "notified_body_assessment_likely": False,
    },
    "answers": {
        "is_provider_or_deployer": "Provider",
        "is_prohibited": "None of the above",
        "is_safety_component_art6": "No",
        "is_annex_iii": "No",
        "is_gpai_model": "No",
        "interacts_with_humans": "No",
    },
    "regulation_version": "2024-1689_base",
}


@pytest.fixture
def classification_file(tmp_path: Path) -> Path:
    """Creates a temporary classification JSON file for tests."""
    file_path = tmp_path / "classification.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(MINIMAL_CLASSIFICATION, f)
    return file_path


def test_generate_command_creates_output(classification_file: Path, tmp_path: Path):
    """
    Tests that the `generate` command runs successfully and creates an output file.
    """
    runner = CliRunner()
    output_doc = tmp_path / "documentation.md"
    result = runner.invoke(
        generate,
        [str(classification_file), "--output", str(output_doc)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert output_doc.exists()
    content = output_doc.read_text()
    assert "Technical Documentation for AI System" in content
    assert "Minimal-Risk" in content


def test_generate_with_high_risk_verdict(tmp_path: Path):
    """
    Tests that the generator includes high-risk specific sections when the
    verdict is High-Risk.
    """
    high_risk_classification = MINIMAL_CLASSIFICATION.copy()
    high_risk_classification["verdict"]["verdict"] = "High-Risk"

    classification_file = tmp_path / "high_risk.json"
    with open(classification_file, "w", encoding="utf-8") as f:
        json.dump(high_risk_classification, f)

    runner = CliRunner()
    output_doc = tmp_path / "high_risk_doc.md"
    result = runner.invoke(
        generate,
        [str(classification_file), "--output", str(output_doc)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    content = output_doc.read_text()
    assert "For High-Risk AI Systems (Annex IV)" in content
    assert "A detailed description of the elements of the AI system" in content
