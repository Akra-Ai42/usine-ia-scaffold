from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentRunStatus:
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class AgentRunType:
    TRIAGE = "triage"
    ENRICHISSEMENT = "enrichissement"
    RECOMMANDATION = "recommandation"


class AgentRunCreate(BaseModel):
    incident_id: UUID
    run_type: str
    llm_model: str


class AgentRun(AgentRunCreate):
    id: UUID = Field(default_factory=uuid4)
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    status: str = AgentRunStatus.RUNNING
    error_message: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}
