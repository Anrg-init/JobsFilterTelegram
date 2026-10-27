import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from tghack import ai_db, ai_processor, db
from tghack.config import DESTINATION_CHANNELS

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID_VALUE = os.getenv("BOT_ADMIN_ID")

if not TOKEN.strip():
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing from .env")

if not ADMIN_ID_VALUE or not ADMIN_ID_VALUE.isdigit():
    raise RuntimeError("BOT_ADMIN_ID must be your numeric Telegram user ID")

ADMIN_ID = int(ADMIN_ID_VALUE)


def is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id == ADMIN_ID)


def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Fetch", callback_data="fetch"),
            InlineKeyboardButton("Filter & Publish", callback_data="filter"),
        ]
    ])


def get_new_post_summary():
    with db._connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE status = 'new'"
        ).fetchone()[0]

        rows = conn.execute("""
            SELECT channel_title, COUNT(*) AS total
            FROM posts
            WHERE status = 'new'
            GROUP BY channel_id, channel_title
            ORDER BY total DESC
        """).fetchall()

    return total, [(row[0], row[1]) for row in rows]


def get_pending_candidates():
    with ai_db._connect() as conn:
        rows = conn.execute("""
            SELECT *
            FROM processed_posts
            WHERE status = 'pending'
            ORDER BY id ASC
        """).fetchall()

    return [dict(row) for row in rows]


def is_candidate_pending(post_id: int) -> bool:
    with ai_db._connect() as conn:
        row = conn.execute("""
            SELECT id
            FROM processed_posts
            WHERE id = ? AND status = 'pending'
        """, (post_id,)).fetchone()

    return row is not None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    message = update.effective_message
    if message:
        await message.reply_text(
            "Job Automation Bot\n\n"
            "Fetch: view counts of new posts.\n"
            "Filter & Publish: run Gemini and publish eligible jobs.",
            reply_markup=main_keyboard(),
        )


async def fetch_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    try:
        total, channels = await asyncio.to_thread(get_new_post_summary)

        lines = [
            "New posts waiting for filtering",
            f"Total new raw posts: {total}",
            "",
            "By source channel:",
        ]

        if channels:
            lines.extend(f"- {name}: {count}" for name, count in channels)
        else:
            lines.append("No new posts.")

        await message.reply_text(
            "\n".join(lines),
            reply_markup=main_keyboard(),
        )

    except Exception:
        log.exception("Could not fetch post summary")
        await message.reply_text(
            "Could not fetch the summary. Check the terminal logs.",
            reply_markup=main_keyboard(),
        )


async def publish_pending(context: ContextTypes.DEFAULT_TYPE) -> dict:
    posts = await asyncio.to_thread(get_pending_candidates)

    summary = {"published": 0, "failed": 0, "skipped": 0}

    for post in posts:
        post_id = post["id"]
        category = post["classification"]
        destination = DESTINATION_CHANNELS.get(category)

        if not destination:
            log.error("No destination for category %s", category)
            summary["failed"] += 1
            continue

        # Check status again before sending.
        if not await asyncio.to_thread(is_candidate_pending, post_id):
            summary["skipped"] += 1
            continue

        title = (post.get("title") or "Job Opportunity").strip()
        post_text = (post.get("post_text") or "").strip()
        application_url = (post.get("application_url") or "").strip()

        if not post_text or not application_url:
            log.warning("Candidate %s is missing text or application URL", post_id)
            summary["failed"] += 1
            continue

        publish_text = (
            f"{title}\n\n{post_text}\n\nApply here: {application_url}"
        )

        if len(publish_text) > 4096:
            publish_text = publish_text[:4090] + "..."

        try:
            sent = await context.bot.send_message(
                chat_id=destination,
                text=publish_text,
                disable_web_page_preview=False,
            )

            # Mark handled only after Telegram confirms the send.
            changed = await asyncio.to_thread(
                ai_db.update_ai_post_status, post_id, "accepted"
            )

            if changed:
                summary["published"] += 1
                log.info(
                    "Published candidate %s to %s (message %s)",
                    post_id, destination, sent.message_id,
                )
            else:
                summary["failed"] += 1
                log.error(
                    "Candidate %s was sent, but its database status update "
                    "failed. Check before retrying to avoid duplicates.",
                    post_id,
                )

        except Exception:
            log.exception("Failed to publish candidate %s", post_id)
            summary["failed"] += 1

    return summary


async def filter_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    lock = context.application.bot_data.get("filter_lock")
    if lock is None:
        lock = asyncio.Lock()
        context.application.bot_data["filter_lock"] = lock

    if lock.locked():
        await message.reply_text(
            "Filtering is already running. Please wait.",
            reply_markup=main_keyboard(),
        )
        return

    async with lock:
        status_message = await message.reply_text("Processing new posts with Gemini...")

        try:
            result = await asyncio.to_thread(ai_processor.process_new_posts)

            await status_message.edit_text(
                "Gemini processing finished.\n\n"
                f"Raw posts fetched: {result['found']}\n"
                f"Raw posts processed: {result['processed']}\n"
                f"Candidates saved: {result['candidates_saved']}\n"
                f"No valid candidate: {result['no_valid_candidate']}\n"
                f"Processing failures: {result['failed']}\n\n"
                "Publishing eligible pending candidates..."
            )

            published = await publish_pending(context)

            await status_message.edit_text(
                "Automation run finished.\n\n"
                f"Raw posts fetched: {result['found']}\n"
                f"Raw posts processed: {result['processed']}\n"
                f"Candidates saved: {result['candidates_saved']}\n"
                f"No valid candidate: {result['no_valid_candidate']}\n"
                f"Processing failures: {result['failed']}\n\n"
                f"Published: {published['published']}\n"
                f"Publish failures: {published['failed']}\n"
                f"Skipped: {published['skipped']}"
            )

        except Exception:
            log.exception("Filter and publish failed")
            await status_message.edit_text(
                "Automation failed. Check the terminal logs."
            )

        finally:
            await message.reply_text(
                "Choose your next action:",
                reply_markup=main_keyboard(),
            )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if not query:
        return

    if not is_admin(update):
        await query.answer("Not authorized.", show_alert=True)
        return

    await query.answer()

    if query.data == "fetch":
        await fetch_posts(update, context)
    elif query.data == "filter":
        await filter_posts(update, context)


async def text_commands(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    if not message:
        return

    command = (message.text or "").strip().lower()

    if command == "fetch":
        await fetch_posts(update, context)
    elif command in ("filter", "filter & publish"):
        await filter_posts(update, context)


def main():
    db.init_db()
    ai_db.init_ai_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_commands)
    )

    log.info("Starting Job Automation Bot")
    app.run_polling()


if __name__ == "__main__":
    main()
