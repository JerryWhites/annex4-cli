import pytest
from annex4.regulation.loader import RegulationLoader
from annex4.regulation.models import Regulation, ClassifierSpec


def test_regulation_loader_finds_default_pack():
    """Test that the loader can find and parse the default regulation pack."""
    loader = RegulationLoader()
    assert loader.base_path.exists()
    assert loader.base_path.name == "2024-1689_base"


def test_regulation_loader_raises_for_missing_version():
    """Test that the loader raises a FileNotFoundError for a non-existent version."""
    with pytest.raises(FileNotFoundError):
        RegulationLoader(version="does-not-exist")


def test_load_regulation():
    """Test that the main load_regulation method works and returns a Regulation object."""
    loader = RegulationLoader()
    regulation = loader.load_regulation()
    assert isinstance(regulation, Regulation)
    assert regulation.metadata.version_id == "2024-1689_base"
    assert (
        len(regulation.articles) > 2
    )  # Check if a reasonable number of articles are loaded
    assert len(regulation.recitals) > 1
    assert len(regulation.annexes) > 1

    # Check content of a specific article
    article_3 = next((a for a in regulation.articles if a.identifier == "3"), None)
    assert article_3 is not None
    assert "provider" in article_3.text


def test_load_classifier_spec():
    """Test that the load_classifier_spec method works."""
    loader = RegulationLoader()
    spec = loader.load_classifier_spec()
    assert isinstance(spec, ClassifierSpec)
    assert spec.start_node == "is_provider_or_deployer"
