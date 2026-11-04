from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class TechniqueMatch(BaseModel):
    id: str
    name: str
    tactic: str
    severity: str
    excerpt: str


class ChatResponse(BaseModel):
    incident_id: int
    analysis: str
    techniques: list[TechniqueMatch]
    requires_review: bool


class ReviewRequest(BaseModel):
    action: str  # "approved" | "rejected"
    reason: str | None = None


class ReviewResponse(BaseModel):
    incident_id: int
    status: str
