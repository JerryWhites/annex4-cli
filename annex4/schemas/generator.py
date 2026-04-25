"""
Generates JSON schemas from Pydantic models.
"""

from pathlib import Path
import json

from annex4.regulation.models import Regulation, ClassifierSpec


def generate_schemas(output_dir: Path) -> None:
    """
    Generates JSON schemas for the main Pydantic models and saves them
    to the specified directory.
    """
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    # Schema for the entire Regulation pack
    regulation_schema = Regulation.model_json_schema()
    regulation_schema_path = output_dir / "regulation.schema.json"
    with open(regulation_schema_path, "w", encoding="utf-8") as f:
        json.dump(regulation_schema, f, indent=2)

    # Schema for the Classifier Specification
    classifier_schema = ClassifierSpec.model_json_schema()
    classifier_schema_path = output_dir / "classifier.schema.json"
    with open(classifier_schema_path, "w", encoding="utf-8") as f:
        json.dump(classifier_schema, f, indent=2)
