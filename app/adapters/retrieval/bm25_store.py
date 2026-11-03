import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.adapters.retrieval.models import Document, RetrievalResult
from app.logger import logger

_INDEX_PATH = Path("data/bm25_index.pkl")


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class BM25Store:
    def __init__(self, documents: list[Document] | None = None):
        self._documents: list[Document] = []
        self._index: BM25Okapi | None = None
        if documents:
            self.build(documents)

    def build(self, documents: list[Document]) -> None:
        self._documents = documents
        corpus = [_tokenize(doc.content) for doc in documents]
        self._index = BM25Okapi(corpus)
        logger.info("bm25_index_built", doc_count=len(documents))

    def save(self, path: Path = _INDEX_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump((self._documents, self._index), f)
        logger.info("bm25_index_saved", path=str(path))

    @classmethod
    def load(cls, path: Path = _INDEX_PATH) -> "BM25Store":
        with open(path, "rb") as f:
            documents, index = pickle.load(f)
        store = cls()
        store._documents = documents
        store._index = index
        logger.info("bm25_index_loaded", doc_count=len(documents))
        return store

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        if self._index is None or not self._documents:
            return []
        tokens = _tokenize(query)
        scores = self._index.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            RetrievalResult(document=self._documents[i], score=float(score), source="sparse")
            for i, score in ranked
            if score > 0
        ]
