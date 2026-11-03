from __future__ import annotations

import uuid

from app.adapters.retrieval.models import Document, RetrievalResult
from app.config import settings
from app.logger import logger


class QdrantStore:
    def __init__(self, client=None):
        from qdrant_client import AsyncQdrantClient  # lazy — requires running Qdrant
        from sentence_transformers import SentenceTransformer  # lazy — heavy lib
        self._client = client or AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self._encoder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        self._collection = settings.qdrant_collection
        self._dim = 384

    async def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams
        exists = await self._client.collection_exists(self._collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )
            logger.info("qdrant_collection_created", collection=self._collection)

    def _embed(self, text: str) -> list[float]:
        return self._encoder.encode(text, normalize_embeddings=True).tolist()

    async def upsert(self, documents: list[Document]) -> None:
        from qdrant_client.models import PointStruct
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.id)),
                vector=self._embed(doc.content),
                payload={"id": doc.id, "content": doc.content, **doc.metadata},
            )
            for doc in documents
        ]
        await self._client.upsert(collection_name=self._collection, points=points)
        logger.info("qdrant_upserted", count=len(points))

    async def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        vector = self._embed(query)
        hits = await self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            RetrievalResult(
                document=Document(
                    id=hit.payload["id"],
                    content=hit.payload["content"],
                    metadata={k: v for k, v in hit.payload.items() if k not in ("id", "content")},
                ),
                score=hit.score,
                source="dense",
            )
            for hit in hits
        ]
