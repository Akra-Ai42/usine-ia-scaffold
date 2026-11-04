from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.adapters.observability.langfuse_hooks import flush_langfuse
from app.config import settings
from app.core.routes.alerts import router as alerts_router
from app.core.routes.incidents import router as incidents_router
from app.core.routes.recommendations import router as recommendations_router
from app.logger import configure_logging, logger


def _build_retriever():
    """Construit HybridRetriever si Qdrant et BM25 index sont disponibles."""
    try:
        from app.adapters.retrieval.bm25_store import BM25Store, _INDEX_PATH
        from app.adapters.retrieval.cross_encoder import CrossEncoderReranker
        from app.adapters.retrieval.hybrid import HybridRetriever
        from app.adapters.retrieval.qdrant_store import QdrantStore

        if not Path(_INDEX_PATH).exists():
            logger.warning("retriever_skipped_no_bm25_index", path=str(_INDEX_PATH))
            return None

        qdrant = QdrantStore()
        bm25 = BM25Store.load()
        cross_encoder = CrossEncoderReranker()
        logger.info("retriever_initialized")
        return HybridRetriever(qdrant=qdrant, bm25=bm25, cross_encoder=cross_encoder)
    except Exception as exc:
        logger.warning("retriever_init_failed", error=str(exc))
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("vigie_starting", env=settings.app_env)
    app.state.retriever = _build_retriever()
    yield
    flush_langfuse()
    logger.info("vigie_shutdown")


app = FastAPI(title="Vigie SOC", version="0.1.0", lifespan=lifespan)

app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(recommendations_router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "0.1.0",
        "retriever": "ready" if app.state.retriever else "unavailable",
    }
