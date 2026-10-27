
# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false

import json
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

from tghack.config import DB_PATH

MAX_TEXT_CHARS = 1500
RAW_STATUSES = {"new", "processed", "failed"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id       INTEGER NOT NULL,
    channel_title    TEXT NOT NULL,
    channel_username TEXT,
    message_link     TEXT,
    message_id       INTEGER NOT NULL,
    grouped_id       INTEGER,
    text             TEXT NOT NULL DEFAULT '',
    links            TEXT NOT NULL DEFAULT '[]',
    media_type       TEXT,
    posted_at        TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'new',
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (channel_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_posts_status
ON posts(status);
"""


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create the schema and migrate existing statuses."""
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)

        # Migrate records created by the previous version.
        conn.execute(
            "UPDATE posts SET status = 'new' WHERE status = 'received'"
        )

        conn.commit()


def save_post(
    *,
    channel_id: int,
    channel_title: str,
    channel_username: str | None,
    message_link: str,
    message_id: int,
    grouped_id: int | None,
    text: str,
    links: list[str],
    media_type: str | None,
    posted_at: datetime,
) -> str:
    """Save a new raw post; ignore duplicate channel/message pairs."""
    with closing(_connect()) as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO posts (
                channel_id, channel_title, channel_username,
                message_link, message_id, grouped_id, text,
                links, media_type, posted_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """,
            (
                channel_id,
                channel_title,
                channel_username,
                message_link,
                message_id,
                grouped_id,
                text[:MAX_TEXT_CHARS],
                json.dumps(links, ensure_ascii=False),
                media_type,
                posted_at.astimezone(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return "stored" if cur.rowcount == 1 else "already_saved"


def get_new_posts(limit: int = 100) -> list[dict[str, Any]]:
    """Return only new posts, oldest first."""
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM posts
            WHERE status = 'new'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    posts = []

    for row in rows:
        post = dict(row)

        try:
            post["links"] = json.loads(post["links"])
        except (json.JSONDecodeError, TypeError):
            post["links"] = []

        posts.append(post)

    return posts


def update_post_status(post_id: int, status: str) -> bool:
    """Update a raw post's status; return False if not found."""
    if status not in RAW_STATUSES:
        raise ValueError(
            f"Invalid status: {status}. "
            f"Allowed statuses: {sorted(RAW_STATUSES)}"
        )

    with closing(_connect()) as conn:
        cur = conn.execute(
            "UPDATE posts SET status = ? WHERE id = ?",
            (status, post_id),
        )
        conn.commit()
        return cur.rowcount == 1


def last_message_ids() -> dict[int, int]:
    """Return the highest saved message ID for each channel."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT channel_id, MAX(message_id)
            FROM posts
            GROUP BY channel_id
            """
        ).fetchall()

    return {int(row[0]): int(row[1]) for row in rows}






# # pyright: reportMissingImports=false
# # pyright: reportGeneralTypeIssues=false

# import json
# import sqlite3
# import sys
# from contextlib import closing
# from datetime import datetime, timezone
# from pathlib import Path

# if __package__ in (None, ""):
#     ROOT = Path(__file__).resolve().parents[2]
#     SRC = ROOT / "src"
#     if str(SRC) not in sys.path:
#         sys.path.insert(0, str(SRC))

# from tghack.config import DB_PATH

# MAX_TEXT_CHARS = 1500

# SCHEMA = """
# CREATE TABLE IF NOT EXISTS posts (
#     id             INTEGER PRIMARY KEY AUTOINCREMENT,
#     channel_id     INTEGER NOT NULL,
#     channel_title  TEXT NOT NULL,
#     channel_username TEXT,
#     message_link     TEXT,
#     message_id     INTEGER NOT NULL,
#     grouped_id     INTEGER,
#     text           TEXT NOT NULL DEFAULT '',
#     links          TEXT NOT NULL DEFAULT '[]',
#     media_type     TEXT,
#     posted_at      TEXT NOT NULL,
#     status         TEXT NOT NULL DEFAULT 'received',
#     created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
#     UNIQUE (channel_id, message_id)
# );
# CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
# """


# def _connect() -> sqlite3.Connection:
#     Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
#     conn = sqlite3.connect(DB_PATH)
#     conn.execute("PRAGMA journal_mode=WAL")
#     return conn


# def init_db() -> None:
#     with closing(_connect()) as conn:
#         conn.executescript(SCHEMA)
#         conn.commit()


# def save_post(*, channel_id, channel_title, channel_username, message_link,
#               message_id, grouped_id, text, links, media_type,
#               posted_at: datetime) -> str:
#     """Returns 'stored' ya 'already_saved'."""
#     with closing(_connect()) as conn:
#         cur = conn.execute(
#             """INSERT OR IGNORE INTO posts
#                (channel_id, channel_title, channel_username, message_link,
#                 message_id, grouped_id, text, links, media_type, posted_at)
#                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
#             (
#                 channel_id, channel_title, channel_username, message_link,
#                 message_id, grouped_id,
#                 text[:MAX_TEXT_CHARS],
#                 json.dumps(links, ensure_ascii=False),
#                 media_type,
#                 posted_at.astimezone(timezone.utc).isoformat(),
#             ),
#         )
#         conn.commit()
#         return "stored" if cur.rowcount == 1 else "already_saved"



# def last_message_ids() -> dict[int, int]:
#     """Har channel ka sabse bada saved message_id."""
#     with closing(_connect()) as conn:
#         rows = conn.execute(
#             "SELECT channel_id, MAX(message_id) FROM posts GROUP BY channel_id"
#         ).fetchall()
#     return {cid: mid for cid, mid in rows}