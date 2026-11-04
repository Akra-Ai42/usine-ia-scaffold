from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuditAction:
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    APPLIED = "applied"


class AuditEntryCreate(BaseModel):
    entity_type: str  # recommendation | incident
    entity_id: UUID
    action: str
    actor: str
    reason: str | None = None


class AuditEntry(AuditEntryCreate):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}
