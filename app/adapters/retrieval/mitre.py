"""Modèle de données MITRE ATT&CK — utilisé par le script de seed."""
from pydantic import BaseModel

from app.adapters.retrieval.models import Document


class MITRETechnique(BaseModel):
    technique_id: str
    name: str
    description: str
    tactics: list[str]
    url: str

    def to_document(self) -> Document:
        content = f"{self.technique_id} — {self.name}\n\nTactics: {', '.join(self.tactics)}\n\n{self.description}"
        return Document(
            id=self.technique_id,
            content=content,
            metadata={
                "name": self.name,
                "tactics": self.tactics,
                "url": self.url,
                "technique_id": self.technique_id,
            },
        )
