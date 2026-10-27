# pyright: reportMissingImports=false
# pyright: reportGeneralTypeIssues=false

import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient

if __package__ in (None, ""):
    ROOT = Path(__file__).resolve().parents[2]
    SRC = ROOT / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

from tghack.config import API_ID, API_HASH, SESSION_PATH


async def main():
    Path(SESSION_PATH).parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group:
            print(d.id, "|", d.name)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())