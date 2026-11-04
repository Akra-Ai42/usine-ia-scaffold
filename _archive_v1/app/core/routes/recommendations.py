from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.adapters.db.connection import get_connection
from app.core.schemas.recommendation import Recommendation, RecommendationReview
from app.core.services import incident_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("/{reco_id}/review", response_model=Recommendation)
async def review_recommendation(reco_id: UUID, review: RecommendationReview) -> Recommendation:
    """Validation humaine obligatoire — guardrail AI Act article 14."""
    if review.status not in ("approved", "rejected"):
        raise HTTPException(status_code=422, detail="status doit être 'approved' ou 'rejected'")

    conn = await get_connection()
    try:
        reco = await incident_service.get_recommendation(conn, reco_id)
        if not reco:
            raise HTTPException(status_code=404, detail="Recommandation non trouvée")
        if reco.status != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Recommandation déjà traitée (statut: {reco.status})",
            )

        # Transaction atomique : review + audit_log en un seul commit.
        # Si create_audit_entry échoue, review_recommendation est rollback.
        async with conn.transaction():
            updated = await incident_service.review_recommendation(conn, reco_id, review)
            await incident_service.create_audit_entry(
                conn,
                entity_type="recommendation",
                entity_id=reco_id,
                action=review.status,
                actor=review.reviewed_by,
                reason=review.reason,
            )
    finally:
        await conn.close()

    return updated
