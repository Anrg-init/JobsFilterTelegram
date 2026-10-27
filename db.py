# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false

import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

from tghack.config import DB_PATH

MAX_TEXT_CHARS = 1500

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id     INTEGER NOT NULL,
    channel_title  TEXT NOT NULL,
    channel_username TEXT,
    message_link     TEXT,
    message_id     INTEGER NOT NULL,
    grouped_id     INTEGER,
    text           TEXT NOT NULL DEFAULT '',
    links          TEXT NOT NULL DEFAULT '[]',
    media_type     TEXT,
    posted_at      TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'received',
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (channel_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
"""


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def save_post(*, channel_id, channel_title, channel_username, message_link,
              message_id, grouped_id, text, links, media_type,
              posted_at: datetime) -> str:
    """Returns 'stored' ya 'already_saved'."""
    with closing(_connect()) as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO posts
               (channel_id, channel_title, channel_username, message_link,
                message_id, grouped_id, text, links, media_type, posted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                channel_id, channel_title, channel_username, message_link,
                message_id, grouped_id,
                text[:MAX_TEXT_CHARS],
                json.dumps(links, ensure_ascii=False),
                media_type,
                posted_at.astimezone(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return "stored" if cur.rowcount == 1 else "already_saved"