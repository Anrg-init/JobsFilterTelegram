import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(value: str | None, default: str) -> str:
    path = Path(value) if value is not None else PROJECT_ROOT / default
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)


API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_PATH = _resolve_path(os.getenv("SESSION_PATH"), "sessions/collector")
DB_PATH = _resolve_path(os.getenv("DB_PATH"), "data/jobs.db")

# channel_id: naam. Naam yahin se aata hai, Telegram se nahi puchte.
SOURCE_CHANNELS = {
    -1001242584289: "Freshershunt",
    -1002286907886: "Python Experience Job's",
    -1002688042669: "Fresher's IT Jobs",
    -1004474524008: "My Test Channel",
}

if not SOURCE_CHANNELS:
    raise SystemExit("config.py mein SOURCE_CHANNELS khaali hai")