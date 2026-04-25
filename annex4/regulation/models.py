"""
Pydantic models for the EU AI Act regulation data.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RegulationMetadata(BaseModel):
    version_id: str
    source_url: str
    retrieved_at: str
    language: str
    content_hash: str
    supersedes: Optional[str] = None


class ClassifierQuestion(BaseModel):
    question: str
    type: str
    options: Optional[List[Dict[str, Any]]] = None
    next_node_logic: Optional[List[Dict[str, Any]]] = None
    next_node: Optional[str] = None


class ClassifierVerdict(BaseModel):
    verdict: str
    citation: str
    explanation_markdown: str
    next_steps: str
    notified_body_assessment_likely: bool
    # PR#3 additions — richer path metadata (optional for backward compat)
    path_id: Optional[str] = None
    articles: Optional[List[str]] = None
    conformity_route: Optional[str] = None


class ClassifierSpec(BaseModel):
    start_node: str
    tree: Dict[str, ClassifierQuestion]
    verdicts: Dict[str, ClassifierVerdict]


class Recital(BaseModel):
    identifier: str
    text: str


class Article(BaseModel):
    identifier: str
    title: str
    text: str


class Annex(BaseModel):
    identifier: str
    title: str
    text: str


class Regulation(BaseModel):
    """
    The root model for the entire EU AI Act regulation pack.
    """

    metadata: RegulationMetadata
    classifier_spec: ClassifierSpec
    recitals: List[Recital]
    articles: List[Article]
    annexes: List[Annex]


class FieldKinds(BaseModel):
    fields: List[Dict[str, Any]]

class HarmonisedStandards(BaseModel):
    standards: List[str]
