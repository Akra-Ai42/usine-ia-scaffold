from collections import defaultdict

from app.adapters.retrieval.bm25_store import BM25Store
from app.adapters.retrieval.cross_encoder import CrossEncoderReranker
from app.adapters.retrieval.models import RetrievalResult
from app.adapters.retrieval.qdrant_store import QdrantStore
from app.logger import logger


def _rrf_fusion(
    dense: list[RetrievalResult],
    sparse: list[RetrievalResult],
    k: int = 60,
) -> list[RetrievalResult]:
    """Reciprocal Rank Fusion — fusionne dense et sparse sans normalisation préalable."""
    scores: dict[str, float] = defaultdict(float)
    docs: dict[str, RetrievalResult] = {}

    for rank, result in enumerate(dense):
        doc_id = result.document.id
        scores[doc_id] += 1.0 / (k + rank + 1)
        docs[doc_id] = result

    for rank, result in enumerate(sparse):
        doc_id = result.document.id
        scores[doc_id] += 1.0 / (k + 1)  # rank ignoré
        if doc_id not in docs:
            docs[doc_id] = result

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [
        RetrievalResult(document=docs[doc_id].document, score=score, source="fused")
        for doc_id, score in ranked
    ]


class HybridRetriever:
    def __init__(
        self,
        qdrant: QdrantStore,
        bm25: BM25Store,
        cross_encoder: CrossEncoderReranker,
        candidate_k: int = 20,
        top_k: int = 5,
    ):
        self._qdrant = qdrant
        self._bm25 = bm25
        self._cross_encoder = cross_encoder
        self._candidate_k = candidate_k
        self._top_k = top_k

    async def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievalResult]:
        k = top_k or self._top_k
        dense = await self._qdrant.search(query, top_k=self._candidate_k)
        sparse = self._bm25.search(query, top_k=self._candidate_k)
        fused = _rrf_fusion(dense, sparse)[: self._candidate_k]
        reranked = self._cross_encoder.rerank(query, fused, top_k=k)
        logger.info(
            "hybrid_retrieve",
            query=query[:80],
            dense_hits=len(dense),
            sparse_hits=len(sparse),
            reranked=len(reranked),
        )
        return reranked
