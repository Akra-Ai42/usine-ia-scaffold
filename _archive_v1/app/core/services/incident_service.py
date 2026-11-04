"""CRUD PostgreSQL pour alerts, incidents, agent_runs, recommendations, audit_log."""
import json
from datetime import datetime, timezone
from uuid import UUID

import psycopg

from app.core.schemas.alert import Alert, AlertCreate
from app.core.schemas.agent_run import AgentRun, AgentRunCreate
from app.core.schemas.incident import Incident, IncidentCreate, IncidentUpdate
from app.core.schemas.recommendation import Recommendation, RecommendationCreate, RecommendationReview


# ── Incidents ────────────────────────────────────────────────────────────────

async def create_incident(conn: psycopg.AsyncConnection, data: IncidentCreate) -> Incident:
    row = await conn.execute(
        """
        INSERT INTO incidents (severity, title, mitre_techniques)
        VALUES (%s, %s, %s)
        RETURNING id, status, severity, title, mitre_techniques, created_at, updated_at
        """,
        (data.severity, data.title, data.mitre_techniques),
    )
    r = await row.fetchone()
    await conn.commit()
    return Incident.model_validate(dict(r))


async def list_incidents(
    conn: psycopg.AsyncConnection, limit: int = 50, offset: int = 0
) -> list[Incident]:
    rows = await conn.execute(
        "SELECT * FROM incidents ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )
    return [Incident.model_validate(dict(r)) for r in await rows.fetchall()]


async def get_incident(conn: psycopg.AsyncConnection, incident_id: UUID) -> Incident | None:
    rows = await conn.execute("SELECT * FROM incidents WHERE id = %s", (str(incident_id),))
    r = await rows.fetchone()
    return Incident.model_validate(dict(r)) if r else None


async def update_incident(
    conn: psycopg.AsyncConnection, incident_id: UUID, data: IncidentUpdate
) -> Incident | None:
    fields = data.model_dump(exclude_none=True)
    if not fields:
        return await get_incident(conn, incident_id)
    sets = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [str(incident_id)]
    rows = await conn.execute(
        f"UPDATE incidents SET {sets}, updated_at = NOW() WHERE id = %s RETURNING *",
        values,
    )
    r = await rows.fetchone()
    await conn.commit()
    return Incident.model_validate(dict(r)) if r else None


# ── Alerts ───────────────────────────────────────────────────────────────────

async def create_alert(
    conn: psycopg.AsyncConnection, data: AlertCreate, incident_id: UUID
) -> Alert:
    row = await conn.execute(
        """
        INSERT INTO alerts (external_id, severity, source, title, raw_payload, incident_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, external_id, severity, source, title, raw_payload, incident_id, received_at
        """,
        (
            data.external_id,
            data.severity,
            data.source,
            data.title,
            json.dumps(data.raw_payload),
            str(incident_id),
        ),
    )
    r = await row.fetchone()
    await conn.commit()
    return Alert.model_validate(dict(r))


# ── Agent runs ───────────────────────────────────────────────────────────────

async def create_agent_run(conn: psycopg.AsyncConnection, data: AgentRunCreate) -> AgentRun:
    row = await conn.execute(
        """
        INSERT INTO agent_runs (incident_id, run_type, llm_model, status)
        VALUES (%s, %s, %s, 'running')
        RETURNING *
        """,
        (str(data.incident_id), data.run_type, data.llm_model),
    )
    r = await row.fetchone()
    await conn.commit()
    return AgentRun.model_validate(dict(r))


async def finish_agent_run(
    conn: psycopg.AsyncConnection,
    run_id: UUID,
    status: str,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    await conn.execute(
        """
        UPDATE agent_runs
        SET status = %s, latency_ms = %s, error_message = %s, finished_at = NOW()
        WHERE id = %s
        """,
        (status, latency_ms, error_message, str(run_id)),
    )
    await conn.commit()


# ── Recommendations ──────────────────────────────────────────────────────────

async def create_recommendation(
    conn: psycopg.AsyncConnection, data: RecommendationCreate
) -> Recommendation:
    row = await conn.execute(
        """
        INSERT INTO recommendations (incident_id, agent_run_id, content, confidence, mitre_refs)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            str(data.incident_id),
            str(data.agent_run_id),
            data.content,
            data.confidence,
            data.mitre_refs,
        ),
    )
    r = await row.fetchone()
    await conn.commit()
    return Recommendation.model_validate(dict(r))


async def list_recommendations(
    conn: psycopg.AsyncConnection, incident_id: UUID
) -> list[Recommendation]:
    rows = await conn.execute(
        "SELECT * FROM recommendations WHERE incident_id = %s ORDER BY created_at",
        (str(incident_id),),
    )
    return [Recommendation.model_validate(dict(r)) for r in await rows.fetchall()]


async def get_recommendation(
    conn: psycopg.AsyncConnection, reco_id: UUID
) -> Recommendation | None:
    rows = await conn.execute("SELECT * FROM recommendations WHERE id = %s", (str(reco_id),))
    r = await rows.fetchone()
    return Recommendation.model_validate(dict(r)) if r else None


async def review_recommendation(
    conn: psycopg.AsyncConnection, reco_id: UUID, review: RecommendationReview
) -> Recommendation | None:
    # Pas de commit ici — géré par la transaction appelante (route review)
    rows = await conn.execute(
        """
        UPDATE recommendations
        SET status = %s, reviewed_by = %s, reviewed_at = NOW(), review_reason = %s
        WHERE id = %s AND status = 'pending'
        RETURNING *
        """,
        (review.status, review.reviewed_by, review.reason, str(reco_id)),
    )
    r = await rows.fetchone()
    return Recommendation.model_validate(dict(r)) if r else None


# ── Audit log ────────────────────────────────────────────────────────────────

async def create_audit_entry(
    conn: psycopg.AsyncConnection,
    entity_type: str,
    entity_id: UUID,
    action: str,
    actor: str,
    reason: str | None = None,
) -> None:
    # Pas de commit ici — géré par la transaction appelante (route review)
    await conn.execute(
        """
        INSERT INTO audit_log (entity_type, entity_id, action, actor, reason)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (entity_type, str(entity_id), action, actor, reason),
    )
