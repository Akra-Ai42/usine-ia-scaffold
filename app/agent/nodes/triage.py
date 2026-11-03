import time
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.adapters.llm.openrouter import get_llm
from app.agent.state import AgentState
from app.logger import logger


class TriageLLMOutput(BaseModel):
    severity: str = Field(description="Severite normalisee : LOW | MEDIUM | HIGH | CRITICAL")
    mitre_technique_ids: list[str] = Field(
        description="IDs de techniques MITRE ATT&CK potentiellement liees (ex: T1566, T1078). Liste vide si inconnu."
    )
    summary: str = Field(description="Resume de l'alerte en 1-2 phrases pour le SOC")
    confidence: float = Field(ge=0.0, le=1.0, description="Confiance du triage entre 0 et 1")


_TRIAGE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Tu es un analyste SOC expert. Analyse l'alerte de securite et fournis un triage structure. "
        "Sois concis et precis. Les IDs MITRE doivent etre au format Txxxx (ex: T1566).",
    ),
    (
        "human",
        "Alerte a trier :\n"
        "Source : {source}\n"
        "Titre : {title}\n"
        "Severite brute : {raw_severity}\n"
        "Payload : {payload}\n\n"
        "Fournis le triage structure.",
    ),
])


def make_triage_node():
    async def triage_node(state: AgentState) -> dict:
        alert = state["alert"]
        agent_run_id = str(uuid4())
        t0 = time.monotonic()

        try:
            llm = get_llm(temperature=0.0).with_structured_output(TriageLLMOutput)
            chain = _TRIAGE_PROMPT | llm
            result: TriageLLMOutput = await chain.ainvoke({
                "source": alert.get("source", "inconnu"),
                "title": alert.get("title", ""),
                "raw_severity": alert.get("severity", ""),
                "payload": str(alert.get("raw_payload", {}))[:500],
            })

            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.info(
                "triage_done",
                severity=result.severity,
                techniques=result.mitre_technique_ids,
                confidence=result.confidence,
                latency_ms=latency_ms,
            )

            return {
                "agent_run_id": agent_run_id,
                "severity": result.severity,
                "mitre_technique_ids": result.mitre_technique_ids,
                "triage_summary": result.summary,
                "triage_confidence": result.confidence,
                "error": None,
            }

        except Exception as exc:
            logger.error("triage_error", error=str(exc))
            return {
                "agent_run_id": agent_run_id,
                "severity": state["alert"].get("severity", "MEDIUM"),
                "mitre_technique_ids": [],
                "triage_summary": "",
                "triage_confidence": 0.0,
                "error": f"triage_failed: {exc}",
            }

    return triage_node
