import asyncio
import logging

from telethon import TelegramClient, events

from config import API_ID, API_HASH, SESSION_PATH, SOURCE_CHANNELS

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("collector")


async def on_new_post(event):
    msg = event.message
    chat = await event.get_chat()
    title = getattr(chat, "title", None) or str(event.chat_id)

    # msg.text = markdown format (hidden hyperlinks bhi rehte hain), msg.raw_text = plain text.
    # Job posts mein apply link aksar hidden hyperlink hota hai, isliye msg.text rakhna zaroori hai.
    text = msg.text or ""
    media = type(msg.media).__name__ if msg.media else None

    log.info(
        "NEW POST | %s (%s) | msg_id=%s | date=%s | media=%s | album=%s",
        title, event.chat_id, msg.id, msg.date, media, msg.grouped_id,
    )
    print("-" * 60)
    print(text[:800] if text else "(no text)")
    print("-" * 60)


async def main():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    client.add_event_handler(on_new_post, events.NewMessage(chats=SOURCE_CHANNELS))

    # Pehli baar: phone number, phir Telegram app mein aaya OTP (aur 2FA password agar laga ho)
    await client.start()
    me = await client.get_me()
    log.info("Logged in as: %s", me.username or me.first_name)
    log.info("Listening on %d channel(s)...", len(SOURCE_CHANNELS))

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())