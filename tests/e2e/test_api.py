"""Tests e2e — couche HTTP complète avec services mockés (pas de vraie DB)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.schemas.alert import Alert, AlertCreate
from app.core.schemas.incident import Incident, IncidentCreate, IncidentStatus
from app.core.schemas.recommendation import Recommendation, RecommendationCreate, RecommendationStatus

# ── Fixtures ──────────────────────────────────────────────────────────────────

INC_ID = uuid4()
ALERT_ID = uuid4()
RUN_ID = uuid4()
RECO_ID = uuid4()
NOW = datetime.now(timezone.utc)


def _make_incident(**kwargs) -> Incident:
    defaults = dict(
        id=INC_ID, status=IncidentStatus.OPEN, severity="HIGH",
        title="Incident — Brute-force SSH", mitre_techniques=[],
        created_at=NOW, updated_at=NOW,
    )
    return Incident.model_validate({**defaults, **kwargs})


def _make_alert(**kwargs) -> Alert:
    defaults = dict(
        id=ALERT_ID, severity="HIGH", source="wazuh",
        title="Brute-force SSH", raw_payload={}, incident_id=INC_ID, received_at=NOW,
    )
    return Alert.model_validate({**defaults, **kwargs})


def _make_reco(**kwargs) -> Recommendation:
    defaults = dict(
        id=RECO_ID, incident_id=INC_ID, agent_run_id=RUN_ID,
        content="Bloquer l'IP 10.0.0.42", confidence=0.9,
        mitre_refs=["T1110"], status=RecommendationStatus.PENDING,
        created_at=NOW, reviewed_at=None, reviewed_by=None, review_reason=None,
    )
    return Recommendation.model_validate({**defaults, **kwargs})


@pytest.fixture
def mock_conn():
    """Mock psycopg connection — retourné par get_connection dans les routes."""
    conn = AsyncMock()
    return conn


@pytest.fixture
async def client():
    """AsyncClient httpx avec l'app FastAPI, retriever désactivé."""
    from app.main import app
    app.state.retriever = None  # pas de Qdrant en test
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── /health ───────────────────────────────────────────────────────────────────

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


# ── POST /api/alerts ──────────────────────────────────────────────────────────

async def test_receive_alert_accepted(client, mock_conn):
    incident = _make_incident()
    alert = _make_alert()

    with (
        patch("app.core.routes.alerts.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.alerts.incident_service.create_incident", AsyncMock(return_value=incident)),
        patch("app.core.routes.alerts.incident_service.create_alert", AsyncMock(return_value=alert)),
        patch("app.core.routes.alerts.agent_service.run_agent_for_incident", AsyncMock()),
    ):
        r = await client.post("/api/alerts", json={
            "severity": "HIGH",
            "source": "wazuh",
            "title": "Brute-force SSH détecté",
            "raw_payload": {"src_ip": "10.0.0.42"},
        })

    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "accepted"
    assert "incident_id" in data
    assert "alert_id" in data


async def test_receive_alert_invalid_payload(client):
    r = await client.post("/api/alerts", json={"severity": "HIGH"})  # title et source manquants
    assert r.status_code == 422


# ── GET /api/incidents ────────────────────────────────────────────────────────

async def test_list_incidents_empty(client, mock_conn):
    with (
        patch("app.core.routes.incidents.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.incidents.incident_service.list_incidents", AsyncMock(return_value=[])),
    ):
        r = await client.get("/api/incidents")

    assert r.status_code == 200
    assert r.json() == []


async def test_list_incidents_with_data(client, mock_conn):
    incidents = [_make_incident(), _make_incident(id=uuid4(), severity="CRITICAL")]

    with (
        patch("app.core.routes.incidents.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.incidents.incident_service.list_incidents", AsyncMock(return_value=incidents)),
    ):
        r = await client.get("/api/incidents")

    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["severity"] == "HIGH"
    assert data[1]["severity"] == "CRITICAL"


async def test_list_incidents_pagination(client, mock_conn):
    with (
        patch("app.core.routes.incidents.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.incidents.incident_service.list_incidents", AsyncMock(return_value=[])) as mock_list,
    ):
        await client.get("/api/incidents?limit=10&offset=20")
        mock_list.assert_awaited_once_with(mock_conn, limit=10, offset=20)


# ── GET /api/incidents/{id} ───────────────────────────────────────────────────

async def test_get_incident_found(client, mock_conn):
    incident = _make_incident()
    recos = [_make_reco()]

    with (
        patch("app.core.routes.incidents.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.incidents.incident_service.get_incident", AsyncMock(return_value=incident)),
        patch("app.core.routes.incidents.incident_service.list_recommendations", AsyncMock(return_value=recos)),
    ):
        r = await client.get(f"/api/incidents/{INC_ID}")

    assert r.status_code == 200
    data = r.json()
    assert data["incident"]["id"] == str(INC_ID)
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["status"] == "pending"


async def test_get_incident_not_found(client, mock_conn):
    with (
        patch("app.core.routes.incidents.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.incidents.incident_service.get_incident", AsyncMock(return_value=None)),
    ):
        r = await client.get(f"/api/incidents/{uuid4()}")

    assert r.status_code == 404


# ── POST /api/recommendations/{id}/review ─────────────────────────────────────

async def test_review_approve(client, mock_conn):
    reco_pending = _make_reco()
    reco_approved = _make_reco(
        status="approved", reviewed_by="analyste-soc",
        reviewed_at=NOW, review_reason="Action validée en réunion",
    )

    mock_conn.transaction = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock(return_value=False)))

    with (
        patch("app.core.routes.recommendations.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.recommendations.incident_service.get_recommendation", AsyncMock(return_value=reco_pending)),
        patch("app.core.routes.recommendations.incident_service.review_recommendation", AsyncMock(return_value=reco_approved)),
        patch("app.core.routes.recommendations.incident_service.create_audit_entry", AsyncMock()),
    ):
        r = await client.post(f"/api/recommendations/{RECO_ID}/review", json={
            "status": "approved",
            "reviewed_by": "analyste-soc",
            "reason": "Action validée en réunion",
        })

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"
    assert data["reviewed_by"] == "analyste-soc"
    assert data["review_reason"] == "Action validée en réunion"


async def test_review_reject(client, mock_conn):
    reco_pending = _make_reco()
    reco_rejected = _make_reco(status="rejected", reviewed_by="analyste-soc")

    mock_conn.transaction = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock(return_value=False)))

    with (
        patch("app.core.routes.recommendations.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.recommendations.incident_service.get_recommendation", AsyncMock(return_value=reco_pending)),
        patch("app.core.routes.recommendations.incident_service.review_recommendation", AsyncMock(return_value=reco_rejected)),
        patch("app.core.routes.recommendations.incident_service.create_audit_entry", AsyncMock()),
    ):
        r = await client.post(f"/api/recommendations/{RECO_ID}/review", json={
            "status": "rejected",
            "reviewed_by": "analyste-soc",
        })

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"


async def test_review_invalid_status(client, mock_conn):
    with (
        patch("app.core.routes.recommendations.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.recommendations.incident_service.get_recommendation", AsyncMock(return_value=_make_reco())),
    ):
        r = await client.post(f"/api/recommendations/{RECO_ID}/review", json={
            "status": "applied",  # non autorisé via cette route
            "reviewed_by": "analyste-soc",
        })

    assert r.status_code == 422


async def test_review_already_processed(client, mock_conn):
    reco_approved = _make_reco(status="approved")

    with (
        patch("app.core.routes.recommendations.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.recommendations.incident_service.get_recommendation", AsyncMock(return_value=reco_approved)),
    ):
        r = await client.post(f"/api/recommendations/{RECO_ID}/review", json={
            "status": "approved",
            "reviewed_by": "analyste-soc",
        })

    assert r.status_code == 409


async def test_review_not_found(client, mock_conn):
    with (
        patch("app.core.routes.recommendations.get_connection", AsyncMock(return_value=mock_conn)),
        patch("app.core.routes.recommendations.incident_service.get_recommendation", AsyncMock(return_value=None)),
    ):
        r = await client.post(f"/api/recommendations/{uuid4()}/review", json={
            "status": "approved",
            "reviewed_by": "analyste-soc",
        })

    assert r.status_code == 404
