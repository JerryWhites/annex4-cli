"""
Tests for the dossier initialization.
"""

from pathlib import Path
import yaml

from click.testing import CliRunner

from annex4.cli import init


def test_init_command_creates_dossier(tmp_path: Path):
    """
    Tests that the `init` command creates a new dossier file for the deployer role.
    """
    runner = CliRunner()
    output_file = tmp_path / "my_dossier.yaml"
    result = runner.invoke(
        init,
        ["--output", str(output_file), "--role", "deployer"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        dossier_data = yaml.safe_load(f)

    # New template structure: meta + Annex IV sections
    assert "meta" in dossier_data
    assert "general_description" in dossier_data
    assert "risk_management" in dossier_data
    assert "post_market_monitoring" in dossier_data


def test_init_command_default_role(tmp_path: Path):
    """
    Tests that the `init` command (provider role) creates the full Annex IV structure.
    """
    runner = CliRunner()
    output_file = tmp_path / "default_dossier.yaml"
    result = runner.invoke(
        init,
        ["--output", str(output_file)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        dossier_data = yaml.safe_load(f)

    # Provider template includes all 9 Annex IV sections
    assert "meta" in dossier_data
    assert "general_description" in dossier_data
    assert "development_process" in dossier_data
    assert "monitoring_functioning_control" in dossier_data
    assert "risk_management" in dossier_data
    assert "lifecycle_changes" in dossier_data
    assert "harmonised_standards" in dossier_data
    assert "eu_declaration_of_conformity" in dossier_data
    assert "post_market_monitoring" in dossier_data
    assert "serious_incidents" in dossier_data
    assert "evidence_index" in dossier_data
