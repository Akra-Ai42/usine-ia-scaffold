from uuid import UUID

from app.core.schemas.agent_run import AgentRun, AgentRunCreate, AgentRunStatus, AgentRunType
from app.core.schemas.alert import Alert, AlertCreate
from app.core.schemas.audit import AuditAction, AuditEntry, AuditEntryCreate
from app.core.schemas.incident import Incident, IncidentCreate, IncidentStatus
from app.core.schemas.recommendation import Recommendation, RecommendationCreate, RecommendationStatus


def test_alert_create_defaults():
    alert = Alert(**AlertCreate(severity="HIGH", source="wazuh", title="Test alert").model_dump())
    assert isinstance(alert.id, UUID)
    assert alert.incident_id is None
    assert alert.raw_payload == {}


def test_incident_default_status():
    incident = Incident(**IncidentCreate(severity="CRITICAL", title="Incident test").model_dump())
    assert incident.status == IncidentStatus.OPEN
    assert incident.mitre_techniques == []


def test_recommendation_default_status(sample_incident, sample_agent_run):
    rec = Recommendation(
        **RecommendationCreate(
            incident_id=sample_incident.id,
            agent_run_id=sample_agent_run.id,
            content="Isoler le serveur AtlasMétaux-PROD-01",
            confidence=0.92,
            mitre_refs=["T1110"],
        ).model_dump()
    )
    assert rec.status == RecommendationStatus.PENDING
    assert rec.reviewed_at is None


def test_agent_run_default_status(sample_agent_run):
    assert sample_agent_run.status == AgentRunStatus.RUNNING
    assert sample_agent_run.run_type == AgentRunType.TRIAGE


def test_audit_entry(sample_incident):
    entry = AuditEntry(
        **AuditEntryCreate(
            entity_type="incident",
            entity_id=sample_incident.id,
            action=AuditAction.APPROVED,
            actor="analyste@atlasmetaux.fr",
            reason="Faux positif confirmé",
        ).model_dump()
    )
    assert isinstance(entry.id, UUID)
    assert entry.action == AuditAction.APPROVED
