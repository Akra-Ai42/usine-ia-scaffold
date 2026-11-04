"""Tests unitaires retrieval — Qdrant et cross-encoder sont mockés."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.retrieval.bm25_store import BM25Store
from app.adapters.retrieval.hybrid import HybridRetriever, _rrf_fusion
from app.adapters.retrieval.mitre import MITRETechnique
from app.adapters.retrieval.models import Document, RetrievalResult


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(id="T1078", content="T1078 — Valid Accounts Tactics: initial-access\n\nAdversaries use valid accounts.", metadata={"name": "Valid Accounts"}),
        Document(id="T1190", content="T1190 — Exploit Public-Facing Application Tactics: initial-access\n\nAdversaries exploit weaknesses.", metadata={"name": "Exploit Public-Facing Application"}),
        Document(id="T1110", content="T1110 — Brute Force Tactics: credential-access\n\nAdversaries use brute force.", metadata={"name": "Brute Force"}),
    ]


@pytest.fixture
def bm25_store(sample_documents) -> BM25Store:
    return BM25Store(documents=sample_documents)


def test_bm25_search_returns_results(bm25_store):
    results = bm25_store.search("brute force credential", top_k=3)
    assert len(results) > 0
    assert results[0].document.id == "T1110"


def test_bm25_search_empty_query_returns_empty(bm25_store):
    results = bm25_store.search("zzzzzzz_nonexistent_term", top_k=3)
    assert results == []


def test_rrf_fusion_merges_results(sample_documents):
    dense = [
        RetrievalResult(document=sample_documents[0], score=0.9, source="dense"),
        RetrievalResult(document=sample_documents[1], score=0.7, source="dense"),
    ]
    sparse = [
        RetrievalResult(document=sample_documents[1], score=5.0, source="sparse"),
        RetrievalResult(document=sample_documents[2], score=3.0, source="sparse"),
    ]
    fused = _rrf_fusion(dense, sparse)
    ids = [r.document.id for r in fused]
    assert "T1190" in ids
    assert len(fused) == 3


def test_mitre_technique_to_document():
    tech = MITRETechnique(
        technique_id="T1078",
        name="Valid Accounts",
        description="Adversaries may obtain valid accounts.",
        tactics=["initial-access", "persistence"],
        url="https://attack.mitre.org/techniques/T1078/",
    )
    doc = tech.to_document()
    assert doc.id == "T1078"
    assert "Valid Accounts" in doc.content
    assert "initial-access" in doc.content
    assert doc.metadata["technique_id"] == "T1078"


@pytest.mark.asyncio
async def test_hybrid_retriever_calls_all_components(sample_documents, bm25_store):
    mock_qdrant = AsyncMock()
    mock_qdrant.search.return_value = [
        RetrievalResult(document=sample_documents[0], score=0.9, source="dense"),
    ]

    mock_cross_encoder = MagicMock()
    mock_cross_encoder.rerank.return_value = [
        RetrievalResult(document=sample_documents[0], score=0.95, source="reranked"),
    ]

    retriever = HybridRetriever(
        qdrant=mock_qdrant,
        bm25=bm25_store,
        cross_encoder=mock_cross_encoder,
        top_k=3,
    )

    results = await retriever.retrieve("brute force SSH attack", top_k=3)

    mock_qdrant.search.assert_called_once()
    mock_cross_encoder.rerank.assert_called_once()
    assert len(results) == 1
    assert results[0].source == "reranked"
