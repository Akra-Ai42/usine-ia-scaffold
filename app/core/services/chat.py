import json

from app.adapters import db, llm, retrieval
from app.core.schemas import ChatResponse, TechniqueMatch

_HIGH_SEVERITY = {"critical", "high"}


def _build_prompt(query: str, techniques: list[dict]) -> list[dict]:
    context = "\n\n".join(
        f"[{t['id']}] {t['name']} ({t['tactic']}, severity={t['severity']})\n{t['excerpt']}"
        for t in techniques
    )
    return [
        {
            "role": "user",
            "content": (
                f"Incident décrit par l'analyste :\n{query}\n\n"
                f"Techniques MITRE ATT&CK pertinentes récupérées :\n{context}\n\n"
                "Fournis une analyse structurée de l'incident, identifie les techniques MITRE "
                "correspondantes, et propose des recommandations de réponse concrètes et priorisées."
            ),
        }
    ]


async def analyze(description: str) -> ChatResponse:
    techniques = retrieval.search(description)
    messages = _build_prompt(description, techniques)
    analysis = await llm.call_llm(messages)

    incident_id = db.create_incident(
        description=description,
        techniques=json.dumps([t["id"] for t in techniques]),
        llm_response=analysis,
    )

    requires_review = any(t["severity"] in _HIGH_SEVERITY for t in techniques)

    return ChatResponse(
        incident_id=incident_id,
        analysis=analysis,
        techniques=[TechniqueMatch(**t) for t in techniques],
        requires_review=requires_review,
    )
