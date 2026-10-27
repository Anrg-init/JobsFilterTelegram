import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_PATH = os.getenv("SESSION_PATH", "sessions/collector")

# Step 1: sirf kuch test channels. Negative ID (-100...) ya username (bina @) dono chalte hain.
# IDs better hain, kyunki unhe resolve karne ke liye extra API call nahi lagti.
SOURCE_CHANNELS = [
    -1001548135822,  # Freshershunt (tumhare screenshot ke URL se)
    -1004474524008,  # list_channels.py se aur IDs yahan daalo
]

if not SOURCE_CHANNELS:
    raise SystemExit("config.py mein SOURCE_CHANNELS khaali hai")