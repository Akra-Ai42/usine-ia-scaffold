"""Script one-shot : applique les migrations SQL par ordre numérique."""
import asyncio
from pathlib import Path

import psycopg

from app.config import settings
from app.logger import logger


async def run_migrations() -> None:
    migrations_dir = Path(__file__).parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    conn = await psycopg.AsyncConnection.connect(settings.postgres_dsn, autocommit=True)
    try:
        for sql_file in sql_files:
            logger.info("applying_migration", file=sql_file.name)
            sql = sql_file.read_text(encoding="utf-8")
            await conn.execute(sql)
            logger.info("migration_applied", file=sql_file.name)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
