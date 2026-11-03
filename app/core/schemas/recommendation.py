from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RecommendationStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class RecommendationCreate(BaseModel):
    incident_id: UUID
    agent_run_id: UUID
    content: str
    confidence: float | None = None
    mitre_refs: list[str] = Field(default_factory=list)


class Recommendation(RecommendationCreate):
    id: UUID = Field(default_factory=uuid4)
    status: str = RecommendationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None

    model_config = {"from_attributes": True}


class RecommendationReview(BaseModel):
    status: str  # approved | rejected
    reviewed_by: str
    reason: str | None = None
