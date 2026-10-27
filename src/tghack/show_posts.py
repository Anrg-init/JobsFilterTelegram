# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false

import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

from tghack.config import DB_PATH

with closing(sqlite3.connect(DB_PATH)) as conn:
    total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    print("Total posts:", total)
    rows = conn.execute(
        "SELECT id, channel_title, message_link, message_id, status, links, "
        "substr(replace(text, char(10), ' '), 1, 80) "
        "FROM posts ORDER BY id DESC LIMIT 10"
    ).fetchall()
    for id_, title, message_link, mid, status, links, snippet in rows:
        print(f"#{id_} | {title} | msg={mid} | {status} | links={len(json.loads(links))}")
        print("    Original post:", message_link or "N/A")
        print("    ", snippet)