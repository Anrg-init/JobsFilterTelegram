import asyncio

from telethon import TelegramClient

from config import API_ID, API_HASH, SESSION_PATH


async def main():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group:
            print(d.id, "|", d.name)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())