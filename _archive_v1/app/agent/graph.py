from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.adapters.observability.langfuse_hooks import get_langfuse_callback
from app.adapters.retrieval.hybrid import HybridRetriever
from app.agent.nodes.enrichissement import make_enrichissement_node
from app.agent.nodes.recommandation import make_recommandation_node
from app.agent.nodes.triage import make_triage_node
from app.agent.state import AgentState
from app.logger import logger


def build_graph(retriever: HybridRetriever) -> StateGraph:
    triage = make_triage_node()
    enrichissement = make_enrichissement_node(retriever)
    recommandation = make_recommandation_node()

    graph = StateGraph(AgentState)
    graph.add_node("triage", triage)
    graph.add_node("enrichissement", enrichissement)
    graph.add_node("recommandation", recommandation)

    graph.add_edge(START, "triage")
    graph.add_edge("triage", "enrichissement")
    graph.add_edge("enrichissement", "recommandation")
    graph.add_edge("recommandation", END)

    return graph.compile()


async def run_agent(
    alert: dict,
    retriever: HybridRetriever,
    incident_id: str | None = None,
) -> AgentState:
    compiled = build_graph(retriever)

    initial_state: AgentState = {
        "alert": alert,
        "severity": alert.get("severity", "MEDIUM"),
        "mitre_technique_ids": [],
        "triage_summary": "",
        "triage_confidence": 0.0,
        "retrieved_docs": [],
        "recommendations": [],
        "agent_run_id": str(uuid4()),
        "incident_id": incident_id or str(uuid4()),
        "error": None,
    }

    # Langfuse callback — no-op si clés absentes
    run_config: RunnableConfig = {}
    callback = get_langfuse_callback(
        session_id=initial_state["incident_id"],
        trace_name="vigie-agent",
    )
    if callback:
        run_config = RunnableConfig(callbacks=[callback])

    final_state: AgentState = await compiled.ainvoke(initial_state, config=run_config)

    logger.info(
        "agent_run_complete",
        incident_id=final_state.get("incident_id"),
        severity=final_state.get("severity"),
        techniques=final_state.get("mitre_technique_ids"),
        recommendations_count=len(final_state.get("recommendations", [])),
        error=final_state.get("error"),
    )

    return final_state
