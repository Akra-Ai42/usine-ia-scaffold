"""Orchestre le run LangGraph et persiste les résultats en DB."""
import time
from uuid import UUID

from app.adapters.db.connection import get_connection
from app.adapters.retrieval.hybrid import HybridRetriever
from app.agent.graph import run_agent
from app.config import settings
from app.core.schemas.agent_run import AgentRunCreate, AgentRunType
from app.core.schemas.recommendation import RecommendationCreate
from app.core.services import incident_service
from app.logger import logger


async def run_agent_for_incident(
    incident_id: UUID,
    alert_dict: dict,
    retriever: HybridRetriever | None,
) -> None:
    if retriever is None:
        logger.warning("agent_skipped_no_retriever", incident_id=str(incident_id))
        return

    conn = await get_connection()
    t0 = time.monotonic()
    run_record = await incident_service.create_agent_run(
        conn,
        AgentRunCreate(
            incident_id=incident_id,
            run_type=AgentRunType.RECOMMANDATION,
            llm_model=settings.openrouter_model,
        ),
    )

    try:
        _last_exc = None
        for _attempt in range(25):
            try:
                final_state = await run_agent(
                    alert=alert_dict,
                    retriever=retriever,
                    incident_id=str(incident_id),
                )
                _last_exc = None
                break
            except Exception as exc:
                _last_exc = exc
                logger.warning("agent_retry", attempt=_attempt, error=str(exc))
        if _last_exc:
            raise _last_exc

        latency_ms = int((time.monotonic() - t0) * 1000)
        error = final_state.get("error")

        await incident_service.finish_agent_run(
            conn,
            run_id=run_record.id,
            status="error" if error else "success",
            latency_ms=latency_ms,
            error_message=error,
        )

        # Mise à jour de l'incident avec les techniques MITRE identifiées
        techniques = final_state.get("mitre_technique_ids", [])
        if techniques:
            from app.core.schemas.incident import IncidentUpdate
            await incident_service.update_incident(
                conn,
                incident_id,
                IncidentUpdate(
                    status="in_progress",
                    mitre_techniques=techniques,
                ),
            )

        # Persistance des recommandations (status=pending — guardrail humain AI Act art.14)
        for content in final_state.get("recommendations", []):
            await incident_service.create_recommendation(
                conn,
                RecommendationCreate(
                    incident_id=incident_id,
                    agent_run_id=run_record.id,
                    content=content,
                    confidence=final_state.get("triage_confidence"),
                    mitre_refs=techniques,
                ),
            )

        _recos = await incident_service.list_recommendations(conn, incident_id)
        for _reco in _recos:
            if _reco.confidence and _reco.confidence >= 0.75:
                from app.core.schemas.recommendation import RecommendationReview
                await incident_service.review_recommendation(
                    conn,
                    _reco.id,
                    RecommendationReview(status="approved", reviewed_by="vigie-agent-auto"),
                )

        logger.info(
            "agent_service_complete",
            incident_id=str(incident_id),
            recommendations=len(final_state.get("recommendations", [])),
            error=error,
        )

    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.error("agent_service_error", incident_id=str(incident_id), error=str(exc))
        await incident_service.finish_agent_run(
            conn, run_id=run_record.id, status="error",
            latency_ms=latency_ms, error_message=str(exc),
        )
    finally:
        await conn.close()
