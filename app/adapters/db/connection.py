import psycopg
from psycopg.rows import dict_row

from app.config import settings
from app.logger import logger


async def get_connection() -> psycopg.AsyncConnection:
    return await psycopg.AsyncConnection.connect(settings.postgres_dsn, row_factory=dict_row)


async def healthcheck() -> bool:
    try:
        conn = await get_connection()
        await conn.execute("SELECT 1")
        await conn.close()
        return True
    except Exception as exc:
        logger.error("db_healthcheck_failed", error=str(exc))
        return False
