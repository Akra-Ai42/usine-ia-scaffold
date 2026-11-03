from __future__ import annotations

from app.adapters.retrieval.models import RetrievalResult
from app.logger import logger

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    def __init__(self, model_name: str = _MODEL_NAME):
        from sentence_transformers import CrossEncoder  # lazy — heavy lib
        self._model = CrossEncoder(model_name)
        logger.info("cross_encoder_loaded", model=model_name)

    def rerank(self, query: str, candidates: list[RetrievalResult], top_k: int = 5) -> list[RetrievalResult]:
        if not candidates:
            return []
        pairs = [(query, c.document.content) for c in candidates]
        scores = self._model.predict(pairs).tolist()
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [
            RetrievalResult(document=c.document, score=float(s), source="reranked")
            for c, s in ranked[:top_k]
        ]
