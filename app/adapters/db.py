import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DB_PATH = Path("data/vigie.db")


def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS incidents (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                description TEXT    NOT NULL,
                techniques  TEXT    NOT NULL,  -- JSON array
                llm_response TEXT   NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                incident_id INTEGER NOT NULL,
                action      TEXT    NOT NULL,  -- approved | rejected
                review_reason TEXT,
                reviewer    TEXT    NOT NULL DEFAULT 'human'
            );
        """)


@contextmanager
def _connect():
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_incident(description: str, techniques: str, llm_response: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO incidents (description, techniques, llm_response) VALUES (?,?,?)",
            (description, techniques, llm_response),
        )
        return cur.lastrowid


def list_incidents(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_incident(incident_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM incidents WHERE id=?", (incident_id,)
        ).fetchone()
        return dict(row) if row else None


def review_incident(incident_id: int, action: str, reason: str | None) -> None:
    """Atomic: update incident status + insert audit log in one transaction."""
    with _connect() as conn:
        conn.execute(
            "UPDATE incidents SET status=? WHERE id=?",
            (action, incident_id),
        )
        conn.execute(
            "INSERT INTO audit_log (incident_id, action, review_reason) VALUES (?,?,?)",
            (incident_id, action, reason),
        )
