from app.adapters import db
from app.core.schemas import ReviewRequest, ReviewResponse

_VALID_ACTIONS = {"approved", "rejected"}


def review(incident_id: int, req: ReviewRequest) -> ReviewResponse:
    if req.action not in _VALID_ACTIONS:
        raise ValueError(f"Action invalide : {req.action!r}. Valeurs acceptées : {_VALID_ACTIONS}")

    incident = db.get_incident(incident_id)
    if incident is None:
        raise LookupError(f"Incident {incident_id} introuvable")

    if incident["status"] not in ("pending",):
        raise ValueError(f"Incident déjà traité (statut={incident['status']!r})")

    db.review_incident(incident_id=incident_id, action=req.action, reason=req.reason)
    return ReviewResponse(incident_id=incident_id, status=req.action)
