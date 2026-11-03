import pytest

from app.core.schemas.agent_run import AgentRun, AgentRunCreate, AgentRunType
from app.core.schemas.alert import Alert, AlertCreate
from app.core.schemas.incident import Incident, IncidentCreate


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        **AlertCreate(
            severity="HIGH",
            source="wazuh",
            title="Brute-force SSH détecté — 200 tentatives/min",
            raw_payload={"src_ip": "10.0.0.42", "dst_port": 22},
        ).model_dump()
    )


@pytest.fixture
def sample_incident() -> Incident:
    return Incident(
        **IncidentCreate(
            severity="HIGH",
            title="Tentative de compromission SSH — AtlasMétaux-PROD-01",
            mitre_techniques=["T1110", "T1078"],
        ).model_dump()
    )


@pytest.fixture
def sample_agent_run(sample_incident: Incident) -> AgentRun:
    return AgentRun(
        **AgentRunCreate(
            incident_id=sample_incident.id,
            run_type=AgentRunType.TRIAGE,
            llm_model="anthropic/claude-3.5-sonnet",
        ).model_dump()
    )
