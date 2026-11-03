from app.adapters.retrieval.hybrid import HybridRetriever
from app.agent.state import AgentState
from app.logger import logger


def make_enrichissement_node(retriever: HybridRetriever):
    async def enrichissement_node(state: AgentState) -> dict:
        if state.get("error"):
            return {"retrieved_docs": []}

        # Construit une requete de recherche enrichie : techniques + resume
        technique_ids = state.get("mitre_technique_ids", [])
        summary = state.get("triage_summary", state["alert"].get("title", ""))

        query_parts = [summary]
        if technique_ids:
            query_parts.append(" ".join(technique_ids))
        query = " ".join(query_parts)[:300]

        try:
            results = await retriever.retrieve(query, top_k=5)
            docs = [r.model_dump() for r in results]
            logger.info("enrichissement_done", docs_retrieved=len(docs), query=query[:80])
            return {"retrieved_docs": docs}

        except Exception as exc:
            logger.error("enrichissement_error", error=str(exc))
            return {"retrieved_docs": [], "error": f"enrichissement_failed: {exc}"}

    return enrichissement_node
