"""Langfuse observability — callback LangChain + traces manuelles.

Gracieux si les clés ne sont pas configurées (dev sans Langfuse).
"""
from app.config import settings
from app.logger import logger

_langfuse_client = None


def get_langfuse_client():
    """Singleton Langfuse client. Retourne None si non configuré."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None
    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info("langfuse_client_initialized", host=settings.langfuse_host)
        return _langfuse_client
    except Exception as exc:
        logger.warning("langfuse_client_init_failed", error=str(exc))
        return None


def get_langfuse_callback(session_id: str | None = None, trace_name: str = "vigie-agent"):
    """Retourne un LangChain CallbackHandler Langfuse, ou None si non dispo."""
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None
    try:
        from langfuse.callback import CallbackHandler
        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            session_id=session_id,
            trace_name=trace_name,
        )
    except Exception as exc:
        logger.warning("langfuse_callback_init_failed", error=str(exc))
        return None


def flush_langfuse() -> None:
    """Flush les événements en attente (appeler au shutdown)."""
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
        except Exception:
            pass
