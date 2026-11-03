"""Charge MITRE ATT&CK Enterprise dans Qdrant + construit l'index BM25.

Usage :
    python -m scripts.seed_mitre

La première exécution télécharge le JSON STIX depuis le repo public MITRE CTI.
"""
import asyncio
import json
import re
from pathlib import Path

import httpx

from app.adapters.retrieval.bm25_store import BM25Store
from app.adapters.retrieval.mitre import MITRETechnique
from app.adapters.retrieval.qdrant_store import QdrantStore
from app.logger import configure_logging, logger

MITRE_CTI_URL = (
    "https://raw.githubusercontent.com/mitre/cti/master/"
    "enterprise-attack/enterprise-attack.json"
)
CACHE_PATH = Path("data/mitre_enterprise.json")


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\(Citation:[^)]+\)", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_techniques(stix_bundle: dict) -> list[MITRETechnique]:
    techniques: list[MITRETechnique] = []

    for obj in stix_bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("x_mitre_deprecated") or obj.get("revoked"):
            continue

        ext = obj.get("external_references", [])
        technique_id = next(
            (r["external_id"] for r in ext if r.get("source_name") == "mitre-attack"),
            None,
        )
        url = next(
            (r.get("url", "") for r in ext if r.get("source_name") == "mitre-attack"),
            "",
        )
        if not technique_id or not technique_id.startswith("T"):
            continue

        # Ignore sub-techniques (T1234.001) pour le seed initial
        if "." in technique_id:
            continue

        phases = obj.get("kill_chain_phases", [])
        tactics = [p["phase_name"] for p in phases if p.get("kill_chain_name") == "mitre-attack"]

        description = _clean_markdown(obj.get("description", ""))
        if not description:
            continue

        techniques.append(
            MITRETechnique(
                technique_id=technique_id,
                name=obj.get("name", ""),
                description=description[:2000],
                tactics=tactics,
                url=url,
            )
        )

    return techniques


async def fetch_stix() -> dict:
    if CACHE_PATH.exists():
        logger.info("mitre_cache_hit", path=str(CACHE_PATH))
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    logger.info("mitre_fetching", url=MITRE_CTI_URL)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(MITRE_CTI_URL)
        resp.raise_for_status()

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(resp.text, encoding="utf-8")
    logger.info("mitre_cached", path=str(CACHE_PATH), size_kb=len(resp.content) // 1024)
    return resp.json()


async def main() -> None:
    configure_logging()

    stix = await fetch_stix()
    techniques = _parse_techniques(stix)
    logger.info("mitre_parsed", technique_count=len(techniques))

    documents = [t.to_document() for t in techniques]

    qdrant = QdrantStore()
    await qdrant.ensure_collection()
    await qdrant.upsert(documents)

    bm25 = BM25Store(documents=documents)
    bm25.save()

    logger.info("seed_complete", technique_count=len(techniques))


if __name__ == "__main__":
    asyncio.run(main())
