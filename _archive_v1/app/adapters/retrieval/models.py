from pydantic import BaseModel, Field


class Document(BaseModel):
    """Unité de connaissance indexée (technique MITRE ou autre)."""
    id: str
    content: str
    metadata: dict = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Résultat d'une recherche, avec score normalisé."""
    document: Document
    score: float
    source: str  # "dense" | "sparse" | "reranked"
