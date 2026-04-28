import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import (
    Annex,
    Article,
    ClassifierSpec,
    Recital,
    Regulation,
    RegulationMetadata,
    FieldKinds,
    HarmonisedStandards
)

class RegulationHashMismatch(ValueError): pass

class RegulationLoader:
    """Loads a versioned regulation pack from the filesystem."""

    def __init__(self, version: str = "2024-1689_base"):
        self.version = version
        self.base_path = self._get_base_path()
        if not self.base_path.exists():
            raise FileNotFoundError(
                f"Regulation version '{version}' not found. Looked in: {self.base_path}"
            )
        self._validate_hash()

    def _get_base_path(self) -> Path:
        try:
            import annex4.regulation.versions
            return Path(annex4.regulation.versions.__file__).parent / self.version
        except (ImportError, AttributeError):
            return Path(__file__).parent / "versions" / self.version

    def _validate_hash(self) -> None:
        """Validates the pack against the hash in metadata.yaml."""
        meta_data = self._load_yaml("metadata.yaml")
        expected_hash = meta_data.get("content_hash")
        if not expected_hash:
            raise RegulationHashMismatch("No content_hash in metadata.yaml")
        
        calculated_hash = self.compute_content_hash()
        if expected_hash != calculated_hash and expected_hash != "PLACEHOLDER":
            raise RegulationHashMismatch(
                f"Hash mismatch for version {self.version}. Expected {expected_hash}, got {calculated_hash}"
            )

    def compute_content_hash(self) -> str:
        """Computes the SHA256 of the regulation pack files."""
        h = hashlib.sha256()
        # Sort cross-platform by posix path
        files = sorted(
            [f for f in self.base_path.rglob("*") if f.is_file() and f.name != "metadata.yaml"],
            key=lambda x: x.relative_to(self.base_path).as_posix()
        )
        for f in files:
            # Hash the relative path to catch renames, then the content
            # Normalize CRLF→LF so hash is identical on Windows and Linux CI
            h.update(f.relative_to(self.base_path).as_posix().encode("utf-8"))
            h.update(f.read_bytes().replace(b"\r\n", b"\n"))
        return h.hexdigest()

    def _load_yaml(self, file_path_str: str) -> Dict[str, Any]:
        """Loads a single YAML file."""
        file_path = self.base_path / file_path_str
        if not file_path.exists():
            raise FileNotFoundError(
                f"Could not find '{file_path_str}' in '{self.version}' pack."
            )
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if data else {}

    def _load_directory_yaml(self, directory: str) -> List[Dict[str, Any]]:
        """Loads all YAML files from a directory."""
        dir_path = self.base_path / directory
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        
        items = []
        for file_path in sorted(dir_path.glob("*.yaml"), key=lambda x: str(x)):
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    items.append(data)
        return items

    def load_regulation(self) -> Regulation:
        """Loads the entire regulation pack."""
        metadata_data = self._load_yaml("metadata.yaml")
        classifier_data = self._load_yaml("classification_rules/classifier.yaml")
        
        # Load articles from directory
        articles_raw = self._load_directory_yaml("articles")
        articles = [Article(**a) for a in articles_raw]
        
        # Load annexes from directory
        annexes_raw = self._load_directory_yaml("annexes")
        annexes = [Annex(**a) for a in annexes_raw]
        
        # Load recitals if they exist in a single file
        recitals_data = self._load_yaml("recitals.yaml")
        recitals = [Recital(**r) for r in recitals_data.get("recitals", [])]

        return Regulation(
            metadata=RegulationMetadata(**metadata_data),
            classifier_spec=ClassifierSpec(**classifier_data),
            recitals=recitals,
            articles=articles,
            annexes=annexes,
        )

    def load_classifier_spec(self) -> ClassifierSpec:
        """Loads just the classifier specification."""
        classifier_data = self._load_yaml("classification_rules/classifier.yaml")
        return ClassifierSpec(**classifier_data)

    def load_diff_substantiality(self) -> Dict[str, str]:
        """Loads the substantiality map."""
        try:
            return self._load_yaml("diff_substantiality.yaml")
        except FileNotFoundError:
            return {}

def get_regulation_loader(version: Optional[str] = None) -> RegulationLoader:
    """Factory function to get a regulation loader."""
    if version:
        return RegulationLoader(version)
    return RegulationLoader()
