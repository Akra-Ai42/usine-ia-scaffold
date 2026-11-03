from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.adapters.db.connection import get_connection
from app.core.schemas.alert import Alert, AlertCreate
from app.core.schemas.incident import Incident, IncidentCreate
from app.core.services import agent_service, incident_service

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("", status_code=202, response_model=dict)
async def receive_alert(
    payload: AlertCreate,
    background_tasks: BackgroundTasks,
    request: Request,
) -> dict:
    """Ingère une alerte, crée un incident, lance l'agent en arrière-plan."""
    conn = await get_connection()
    try:
        incident = await incident_service.create_incident(
            conn,
            IncidentCreate(
                severity=payload.severity,
                title=f"Incident — {payload.title}",
                mitre_techniques=[],
            ),
        )
        alert = await incident_service.create_alert(conn, payload, incident.id)
    finally:
        await conn.close()

    retriever = getattr(request.app.state, "retriever", None)
    background_tasks.add_task(
        agent_service.run_agent_for_incident,
        incident_id=incident.id,
        alert_dict=alert.model_dump(mode="json"),
        retriever=retriever,
    )

    return {"incident_id": str(incident.id), "alert_id": str(alert.id), "status": "accepted"}
