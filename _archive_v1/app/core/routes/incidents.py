from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.adapters.db.connection import get_connection
from app.core.schemas.incident import Incident
from app.core.schemas.recommendation import Recommendation
from app.core.services import incident_service

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[Incident])
async def list_incidents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Incident]:
    conn = await get_connection()
    try:
        return await incident_service.list_incidents(conn, limit=limit, offset=offset)
    finally:
        await conn.close()


@router.get("/{incident_id}", response_model=dict)
async def get_incident(incident_id: UUID) -> dict:
    conn = await get_connection()
    try:
        incident = await incident_service.get_incident(conn, incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident non trouvé")
        recommendations = await incident_service.list_recommendations(conn, incident_id)
    finally:
        await conn.close()

    return {
        "incident": incident.model_dump(mode="json"),
        "recommendations": [r.model_dump(mode="json") for r in recommendations],
    }
