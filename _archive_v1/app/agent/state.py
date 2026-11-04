from typing import TypedDict


class AgentState(TypedDict):
    # Input
    alert: dict  # Alert.model_dump()

    # Triage output
    severity: str
    mitre_technique_ids: list[str]
    triage_summary: str
    triage_confidence: float

    # Enrichissement output
    retrieved_docs: list[dict]  # RetrievalResult.model_dump()

    # Recommandation output
    recommendations: list[str]

    # Meta
    agent_run_id: str
    incident_id: str
    error: str | None
