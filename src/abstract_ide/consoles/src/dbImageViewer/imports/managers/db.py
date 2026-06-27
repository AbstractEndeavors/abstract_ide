
# managers/db.py
from psycopg_pool import pool
from dataclasses import dataclass, asdict

from ..src import *


SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    file_id      TEXT PRIMARY KEY,
    file_name    TEXT NOT NULL,
    original_url TEXT NOT NULL,
    token_url    TEXT NOT NULL,
    path         TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


@dataclass
class DownloadRecord:
    file_id: str
    file_name: str
    original_url: str
    token_url: str
    path: str

class DownloadRegistry(metaclass=SingletonMeta):
    def __init__(self, dsn: str, minconn: int = 2, maxconn: int = 10):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self._pool = pool.ThreadedConnectionPool(minconn, maxconn, dsn)
            self._execute(SCHEMA)


    def _execute(self, query: str, params=None, fetch: bool = False):
        conn = self._pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchall() if fetch else None
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def has(self, file_id: str) -> bool:
        rows = self._execute(
            "SELECT 1 FROM downloads WHERE file_id = %s", (file_id,), fetch=True
        )
        return bool(rows)

    def save(self, record: DownloadRecord) -> None:
        self._execute(
            """
            INSERT INTO downloads (file_id, file_name, original_url, token_url, path)
            VALUES (%(file_id)s, %(file_name)s, %(original_url)s, %(token_url)s, %(path)s)
            ON CONFLICT (file_id) DO UPDATE SET
                token_url = EXCLUDED.token_url,
                path      = EXCLUDED.path
            """,
            asdict(record),
        )

    def get(self, file_id: str) -> DownloadRecord | None:
        rows = self._execute(
            "SELECT * FROM downloads WHERE file_id = %s", (file_id,), fetch=True
        )
        if not rows:
            return None
        return DownloadRecord(**{k: rows[0][k] for k in DownloadRecord.__dataclass_fields__})

    def close(self) -> None:
        self._pool.closeall()

