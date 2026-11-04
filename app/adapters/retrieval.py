import json
import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

_MITRE_JSON = Path("data/mitre_techniques.json")
_CHROMA_DIR = Path("data/chroma")
_COLLECTION = "mitre_techniques"
_TOP_K = 3

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    ef = embedding_functions.DefaultEmbeddingFunction()

    existing = [c.name for c in _client.list_collections()]
    if _COLLECTION in existing:
        _collection = _client.get_collection(_COLLECTION, embedding_function=ef)
        return _collection

    _collection = _client.create_collection(_COLLECTION, embedding_function=ef)
    _seed_collection(_collection)
    return _collection


def _seed_collection(col: chromadb.Collection) -> None:
    techniques = json.loads(_MITRE_JSON.read_text(encoding="utf-8"))
    documents, ids, metadatas = [], [], []
    for t in techniques:
        text = (
            f"{t['id']} {t['name']} — {t['tactic']}\n"
            f"{t['description']}\n"
            f"Detection: {t['detection']}"
        )
        documents.append(text)
        ids.append(t["id"])
        metadatas.append({
            "id": t["id"],
            "name": t["name"],
            "tactic": t["tactic"],
            "severity": t["severity"],
        })
    col.add(documents=documents, ids=ids, metadatas=metadatas)


def search(query: str, top_k: int = _TOP_K) -> list[dict]:
    col = _get_collection()
    results = col.query(query_texts=[query], n_results=top_k)
    techniques = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        techniques.append({
            "id": meta["id"],
            "name": meta["name"],
            "tactic": meta["tactic"],
            "severity": meta["severity"],
            "excerpt": results["documents"][0][i][:300],
        })
    return techniques
