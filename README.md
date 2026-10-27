# Telegram Job Filter

Automatically collects job posts from Telegram channels, uses Gemini AI to filter and categorize opportunities, and publishes them to destination channels.

## Tech Stack
- Python
- Telethon
- SQLite
- Google Gemini API
- Telegram Bot API
- `uv`

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Create a `.env` file:

```env
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
BOT_ADMIN_ID=your_telegram_user_id
```

3. Start the collector (Terminal 1):

```bash
uv run python -m tghack.collector
```

4. Start the bot (Terminal 2):

```bash
uv run python -m tghack.bot
```

5. Open your Telegram bot and send `/start`.

## Usage
- **Fetch:** View counts of new posts by source channel.
- **Filter & Publish:** Process new posts with Gemini and automatically publish eligible jobs.

## Notes
- Keep both processes running.
- Add your bot as an administrator to all destination channels with permission to post.
- Keep `.env` and Telegram session files private.