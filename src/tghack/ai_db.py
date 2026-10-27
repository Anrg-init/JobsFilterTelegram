
# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false

import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

from tghack.config import DB_PATH

AI_STATUSES = {"pending", "accepted", "rejected"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_posts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_post_id   INTEGER NOT NULL,
    channel_id       INTEGER NOT NULL,
    classification   TEXT NOT NULL,
    title            TEXT,
    company          TEXT,
    location         TEXT,
    post_text        TEXT NOT NULL DEFAULT '',
    application_url  TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (source_post_id, classification),

    CHECK (status IN ('pending', 'accepted', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_processed_posts_status
ON processed_posts(status);
"""


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    return conn


def init_ai_db() -> None:
    """Create the AI-processed posts table."""
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def save_processed_post(
    *,
    source_post_id: int,
    channel_id: int,
    classification: str,
    title: str | None,
    company: str | None,
    location: str | None,
    post_text: str,
    application_url: str | None,
) -> bool:
    """
    Save an AI result as pending.
    Returns True if inserted, False if already exists.
    """
    with closing(_connect()) as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO processed_posts (
                source_post_id,
                channel_id,
                classification,
                title,
                company,
                location,
                post_text,
                application_url,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                source_post_id,
                channel_id,
                classification,
                title,
                company,
                location,
                post_text,
                application_url,
            ),
        )
        conn.commit()

        return cur.rowcount == 1


def get_pending_posts(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return only posts awaiting review, oldest first."""
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM processed_posts
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def update_ai_post_status(
    post_id: int,
    status: str,
) -> bool:
    """Set a candidate's status; return False if it doesn't exist."""
    if status not in AI_STATUSES:
        raise ValueError(
            f"Invalid status: {status}. "
            f"Allowed statuses: {sorted(AI_STATUSES)}"
        )

    with closing(_connect()) as conn:
        cur = conn.execute(
            """
            UPDATE processed_posts
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, post_id),
        )
        conn.commit()

        return cur.rowcount == 1
