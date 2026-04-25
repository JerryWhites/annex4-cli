"""
This module provides search functionality for the regulation data.
"""

import re
from typing import Any, Dict, List

from annex4.regulation.models import Regulation


def search_regulation(query: str, regulation: Regulation) -> Dict[str, List[str]]:
    """
    Performs a simple, case-insensitive search through the regulation documents.

    Args:
        query: The search term.
        regulation: The Regulation data model to search through.

    Returns:
        A dictionary where keys are document IDs and values are lists of
        context snippets where the query was found.
    """
    results: Dict[str, List[str]] = {}
    query_regex = re.compile(re.escape(query), re.IGNORECASE)

    # Helper to search a list of documents
    def _search_docs(docs: Any, doc_type_prefix: str) -> None:
        for doc in docs:
            doc_id = f"{doc_type_prefix}_{doc.identifier}"
            snippets = []

            # Search in title, if it exists
            if hasattr(doc, "title") and doc.title and query_regex.search(doc.title):
                snippets.append(f"... {doc.title} ...")

            # Search in text
            if doc.text:
                for match in query_regex.finditer(doc.text):
                    start, end = match.span()
                    context_start = max(0, start - 30)
                    context_end = min(len(doc.text), end + 30)
                    snippet = f"...{doc.text[context_start:context_end]}..."
                    snippets.append(snippet.replace("\n", " "))

            if snippets:
                if doc_id not in results:
                    results[doc_id] = []
                results[doc_id].extend(snippets)

    _search_docs(regulation.recitals, "recital")
    _search_docs(regulation.articles, "article")
    _search_docs(regulation.annexes, "annex")

    return results
