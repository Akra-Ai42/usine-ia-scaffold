from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IncidentStatus:
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentCreate(BaseModel):
    severity: str
    title: str
    mitre_techniques: list[str] = Field(default_factory=list)


class Incident(IncidentCreate):
    id: UUID = Field(default_factory=uuid4)
    status: str = IncidentStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    status: str | None = None
    severity: str | None = None
    title: str | None = None
    mitre_techniques: list[str] | None = None
