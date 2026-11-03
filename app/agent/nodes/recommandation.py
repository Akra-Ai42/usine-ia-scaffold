import time

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.adapters.llm.openrouter import get_llm
from app.agent.state import AgentState
from app.logger import logger


class RecommandationLLMOutput(BaseModel):
    recommandations: list[str] = Field(
        description="Liste de 3 a 5 actions concretes pour le SOC, ordonnees par priorite"
    )


_RECO_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Tu es un expert en reponse a incident cybersecurite. "
        "Genere des recommandations d'action concretes et prioritisees pour le SOC. "
        "Chaque recommandation doit etre actionnable en moins de 24h. "
        "Limite-toi a 3-5 recommandations, les plus impactantes.",
    ),
    (
        "human",
        "Incident a traiter :\n"
        "Severity : {severity}\n"
        "Resume : {summary}\n"
        "Techniques MITRE identifiees : {techniques}\n\n"
        "Contexte MITRE ATT&CK pertinent :\n{context}\n\n"
        "Genere les recommandations d'action.",
    ),
])


def _format_context(docs: list[dict]) -> str:
    if not docs:
        return "Aucun contexte MITRE disponible."
    parts = []
    for doc in docs[:3]:
        d = doc.get("document", {})
        parts.append(f"- {d.get('id', '?')} : {d.get('content', '')[:200]}")
    return "\n".join(parts)


def make_recommandation_node():
    async def recommandation_node(state: AgentState) -> dict:
        if state.get("error"):
            return {"recommendations": []}

        t0 = time.monotonic()
        context = _format_context(state.get("retrieved_docs", []))
        techniques = ", ".join(state.get("mitre_technique_ids", [])) or "non identifiees"

        try:
            llm = get_llm(temperature=0.2).with_structured_output(RecommandationLLMOutput)
            chain = _RECO_PROMPT | llm
            result: RecommandationLLMOutput = await chain.ainvoke({
                "severity": state.get("severity", "MEDIUM"),
                "summary": state.get("triage_summary", state["alert"].get("title", "")),
                "techniques": techniques,
                "context": context,
            })

            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "recommandation_done",
                count=len(result.recommandations),
                latency_ms=latency_ms,
            )

            return {"recommendations": result.recommandations}

        except Exception as exc:
            logger.error("recommandation_error", error=str(exc))
            return {"recommendations": [], "error": f"recommandation_failed: {exc}"}

    return recommandation_node
