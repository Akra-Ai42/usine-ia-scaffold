from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AlertSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertCreate(BaseModel):
    external_id: str | None = None
    severity: str
    source: str
    title: str
    raw_payload: dict = Field(default_factory=dict)


class Alert(AlertCreate):
    id: UUID = Field(default_factory=uuid4)
    incident_id: UUID | None = None
    received_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}
