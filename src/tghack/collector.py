# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false

import asyncio
import logging
import random
import sys
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, FloodWaitError, RPCError
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    try:
        from tghack import db
        from tghack.config import (
            API_ID, API_HASH, SESSION_PATH, SOURCE_CHANNELS,
            BACKFILL_LIMIT, BACKFILL_DELAY, BACKFILL_MAX_FLOOD_WAIT,
        )
    except ModuleNotFoundError:
        import db
        from config import (
            API_ID, API_HASH, SESSION_PATH, SOURCE_CHANNELS,
            BACKFILL_LIMIT, BACKFILL_DELAY, BACKFILL_MAX_FLOOD_WAIT,
        )
else:
    from . import db
    from .config import (
        API_ID, API_HASH, SESSION_PATH, SOURCE_CHANNELS,
        BACKFILL_LIMIT, BACKFILL_DELAY, BACKFILL_MAX_FLOOD_WAIT,
    )

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("collector")


def extract_links(msg) -> list[str]:
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


def process_message(msg, chat_id: int, chat) -> str:
    """Live events aur backfill dono yahi use karte hain."""
    text = msg.raw_text or ""
    if not text and not msg.media:
        return "skipped_empty"

    title = SOURCE_CHANNELS.get(chat_id, str(chat_id))
    username = getattr(chat, "username", None)
    if username:
        link = f"https://t.me/{username}/{msg.id}"
    else:
        link = f"https://t.me/c/{str(chat_id).removeprefix('-100')}/{msg.id}"

    links = extract_links(msg)
    return db.save_post(
        channel_id=chat_id,
        channel_title=title,
        channel_username=username,
        message_link=link,
        message_id=msg.id,
        grouped_id=msg.grouped_id,
        text=text,
        links=links,
        media_type=type(msg.media).__name__ if msg.media else None,
        posted_at=msg.date,
    )


async def on_new_post(event):
    try:
        result = process_message(event.message, event.chat_id, event.chat)
        # Security: logs mein post ka text nahi, sirf metadata
        log.info("LIVE %s | msg=%s -> %s",
                 SOURCE_CHANNELS.get(event.chat_id, event.chat_id),
                 event.message.id, result)
    except Exception:
        log.exception("live post handle karte waqt error")


async def fetch_channel(client, cid: int, peer, last_id: int) -> tuple[int, int]:
    """Ek channel ki last_id ke baad ki posts. Returns (fetched, stored)."""
    for attempt in (1, 2):
        try:
            fetched = stored = 0
            async for msg in client.iter_messages(peer, min_id=last_id, limit=BACKFILL_LIMIT):
                fetched += 1
                if process_message(msg, cid, msg.chat) == "stored":
                    stored += 1
            return fetched, stored
        except FloodWaitError as e:
            if attempt == 2 or e.seconds > BACKFILL_MAX_FLOOD_WAIT:
                raise
            log.warning("FloodWait %ss, ruk ke ek baar retry karunga", e.seconds)
            await asyncio.sleep(e.seconds + random.uniform(3, 8))
    return 0, 0


async def backfill(client) -> None:
    last_ids = db.last_message_ids()
    targets = [cid for cid in SOURCE_CHANNELS if cid in last_ids]
    log.info("Backfill: %d channel(s), %d skip (DB mein last ID nahi)",
             len(targets), len(SOURCE_CHANNELS) - len(targets))

    total_stored = 0
    for i, cid in enumerate(targets):
        title = SOURCE_CHANNELS[cid]
        try:
            peer = await client.get_input_entity(cid)  # session cache se, API call nahi
        except ValueError:
            log.warning("%s: session cache mein nahi, skip (list_channels.py ek baar chalao)", title)
            continue

        try:
            fetched, stored = await fetch_channel(client, cid, peer, last_ids[cid])
            total_stored += stored
            log.info("Backfill %s: fetched=%d stored=%d", title, fetched, stored)
            if fetched >= BACKFILL_LIMIT:
                log.warning("%s: limit (%d) hit, purani posts chhoot sakti hain", title, BACKFILL_LIMIT)
        except FloodWaitError as e:
            log.error("FloodWait %ss: backfill BAND kar raha hoon (live events chalte rahenge)", e.seconds)
            return
        except ChannelPrivateError:
            log.warning("%s: access nahi (channel chhoda ya private), skip", title)
        except RPCError:
            log.exception("%s: Telegram error, skip", title)

        if i < len(targets) - 1:
            await asyncio.sleep(random.uniform(*BACKFILL_DELAY))

    log.info("Backfill done: %d nayi post(s) saved", total_stored)


async def main():
    db.init_db()

    client = TelegramClient(SESSION_PATH, API_ID, API_HASH, catch_up=True)
    client.add_event_handler(
        on_new_post, events.NewMessage(chats=list(SOURCE_CHANNELS))
    )

    await client.start()  # type: ignore[func-returns-value]
    me = await client.get_me()
    me_name = getattr(me, "username", None) or getattr(me, "first_name", "Unknown")
    log.info("Logged in as: %s", me_name)

    await backfill(client)

    log.info("Listening on %d channel(s)...", len(SOURCE_CHANNELS))
    await client.run_until_disconnected()  # type: ignore[func-returns-value]


if __name__ == "__main__":
    asyncio.run(main())