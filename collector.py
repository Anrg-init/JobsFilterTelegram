# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false

import asyncio
import logging
import sys
from pathlib import Path

from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

from tghack import db
from tghack.config import API_ID, API_HASH, SESSION_PATH, SOURCE_CHANNELS

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("collector")


def extract_links(msg) -> list[str]:
    """Visible aur hidden (text mein chhupe) dono links, order ke saath, bina repeat ke."""
    links: list[str] = []
    try:
        for ent, txt in msg.get_entities_text():
            if isinstance(ent, MessageEntityTextUrl):
                url = ent.url
            elif isinstance(ent, MessageEntityUrl):
                url = txt
            else:
                continue
            if url and url not in links:
                links.append(url)
    except Exception:
        log.exception("links nikalte waqt error")
    return links


async def on_new_post(event):
    try:
        msg = event.message
        title = SOURCE_CHANNELS.get(event.chat_id, str(event.chat_id))
        media = type(msg.media).__name__ if msg.media else None
        links = extract_links(msg)

        username = getattr(event.chat, "username", None)
        if username:
            link = f"https://t.me/{username}/{msg.id}"
        else:
            link = f"https://t.me/c/{str(event.chat_id).removeprefix('-100')}/{msg.id}"

        result = db.save_post(
            channel_id=event.chat_id,
            channel_title=title,
            channel_username=username,
            message_link=link,
            message_id=msg.id,
            grouped_id=msg.grouped_id,
            text=msg.raw_text or "",
            links=links,
            media_type=media,
            posted_at=msg.date,
        )
        # Security: logs mein post ka text nahi, sirf metadata
        log.info("%s | msg=%s | links=%d | media=%s -> %s",
                 title, msg.id, len(links), media, result)
    except Exception:
        log.exception("post handle karte waqt error")


async def main():
    db.init_db()
    Path(SESSION_PATH).parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    client.add_event_handler(
        on_new_post, events.NewMessage(chats=list(SOURCE_CHANNELS))
    )

    await client.start()
    me = await client.get_me()
    me_name = getattr(me, "username", None) or getattr(me, "first_name", "Unknown")
    log.info("Logged in as: %s", me_name)
    log.info("Listening on %d channel(s)...", len(SOURCE_CHANNELS))

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())