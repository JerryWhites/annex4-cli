"""
Tests for the JSON schema generator.
"""

from pathlib import Path
import json
import pytest

from click.testing import CliRunner
from jsonschema import validate

from annex4.cli import generate_schemas_command
from annex4.regulation.loader import RegulationLoader


def test_generate_schemas_command_creates_files(tmp_path: Path):
    """
    Tests that the `schemas generate` command runs and creates the expected
    JSON schema files.
    """
    runner = CliRunner()
    output_dir = tmp_path / "schemas"
    result = runner.invoke(
        generate_schemas_command,
        ["--output-dir", str(output_dir)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert (output_dir / "regulation.schema.json").exists()
    assert (output_dir / "classifier.schema.json").exists()


def test_generated_regulation_schema_is_valid(tmp_path: Path):
    """
    Tests that the generated regulation.schema.json can be used to validate
    the actual regulation data.
    """
    # 1. Generate the schema
    runner = CliRunner()
    output_dir = tmp_path / "schemas"
    runner.invoke(
        generate_schemas_command,
        ["--output-dir", str(output_dir)],
        catch_exceptions=False,
    )

    # 2. Load the generated schema
    schema_path = output_dir / "regulation.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # 3. Load the actual regulation data
    loader = RegulationLoader()
    regulation = loader.load_regulation()
    regulation_data = regulation.model_dump()

    # 4. Validate the data against the schema
    try:
        validate(instance=regulation_data, schema=schema)
    except Exception as e:
        pytest.fail(
            f"Validation of regulation data against generated schema failed: {e}"
        )
