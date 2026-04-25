"""
Tests for the search functionality.
"""

from annex4.regulation.loader import RegulationLoader
from annex4.regulation.search import search_regulation


def test_search_for_provider():
    """
    Tests searching for the term "provider" which should appear frequently.
    """
    loader = RegulationLoader("2024-1689_base")
    regulation = loader.load_regulation()
    results = search_regulation("provider", regulation)

    assert results
    assert "article_3" in results
    assert "article_16" in results
    assert len(results["article_3"]) > 0


def test_search_for_specific_term_in_annex():
    """
    Tests searching for a specific term known to be in an annex.
    "Biometric identification" is in Annex III.
    """
    loader = RegulationLoader("2024-1689_base")
    regulation = loader.load_regulation()
    results = search_regulation("Biometric identification", regulation)

    assert results
    assert "annex_iii" in results
    assert any("Biometric identification" in s for s in results["annex_iii"])


def test_search_no_results():
    """
    Tests a search query that should yield no results.
    """
    loader = RegulationLoader("2024-1689_base")
    regulation = loader.load_regulation()
    results = search_regulation("a_very_unlikely_search_term_xyz", regulation)

    assert not results
