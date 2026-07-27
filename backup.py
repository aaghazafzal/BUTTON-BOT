"""
backup.py — Telegram-based SQLite DB backup/restore for Render free tier.

Problem:
  Render free tier has EPHEMERAL storage. Every redeploy wipes the SQLite DB.

Solution:
  • On startup  → download the latest backup from a private Telegram chat & restore
  • Every 2 hrs → auto-upload the DB as a document to that chat and pin it

Setup (one-time, takes 60 seconds):
  1. Create a PRIVATE Telegram channel (or use a private group/saved messages).
  2. Add the bot as admin to that channel/group.
  3. Copy the chat ID (e.g. -1001234567890 for a channel).
  4. Set the environment variable on Render:
       BACKUP_CHAT_ID = -1001234567890
  That's it — the bot handles everything else automatically!
"""

import os
import logging
import asyncio
from datetime import datetime, timezone

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
BACKUP_CHAT_ID = os.environ.get("BACKUP_CHAT_ID", "").strip()
BACKUP_INTERVAL = 2 * 60 * 60   # 2 hours in seconds
_backup_task: asyncio.Task | None = None


# ── Restore on startup ─────────────────────────────────────────────────────────

async def restore_db(bot: Bot, db_path: str) -> bool:
    """
    On startup: download the pinned backup document from BACKUP_CHAT_ID
    and write it to db_path.

    Returns True if restored successfully, False if no backup or disabled.
    """
    if not BACKUP_CHAT_ID:
        logger.info("backup: BACKUP_CHAT_ID not set — restore skipped.")
        return False

    try:
        chat = await bot.get_chat(BACKUP_CHAT_ID)
        pinned = chat.pinned_message

        if not pinned:
            logger.info("backup: No pinned message in backup chat — starting fresh.")
            return False

        if not pinned.document:
            logger.info("backup: Pinned message has no document — starting fresh.")
            return False

        doc = pinned.document
        logger.info(
            f"backup: Found pinned backup '{doc.file_name}' "
            f"({doc.file_size // 1024} KB) — restoring…"
        )

        tg_file = await bot.get_file(doc.file_id)
        await tg_file.download_to_drive(db_path)

        size_kb = os.path.getsize(db_path) // 1024
        logger.info(f"backup: ✅ DB restored from Telegram ({size_kb} KB)")
        return True

    except TelegramError as e:
        logger.warning(f"backup: Restore failed (Telegram error) — {e}")
    except Exception as e:
        logger.error(f"backup: Restore failed — {e}", exc_info=True)

    return False


# ── Backup ─────────────────────────────────────────────────────────────────────

async def backup_db(bot: Bot, db_path: str) -> bool:
    """
    Upload db_path as a Telegram document to BACKUP_CHAT_ID and pin it.
    Previous pinned backups are automatically superseded.

    Returns True on success.
    """
    if not BACKUP_CHAT_ID:
        return False

    if not os.path.exists(db_path):
        logger.warning("backup: DB file not found — skipping backup.")
        return False

    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M UTC")
        size_kb = os.path.getsize(db_path) // 1024

        with open(db_path, "rb") as f:
            msg = await bot.send_document(
                chat_id=BACKUP_CHAT_ID,
                document=f,
                filename=f"button_bot_backup_{now}.db",
                caption=(
                    f"🗄️ <b>Auto Backup</b>\n\n"
                    f"📅 <code>{now}</code>\n"
                    f"📦 Size: <b>{size_kb} KB</b>\n"
                    f"🤖 Bot: <b>@UNIVORA_BUTTONBOT</b>"
                ),
                parse_mode="HTML",
            )

        # Pin the new backup (silently) so restore() always finds the latest
        await bot.pin_chat_message(
            chat_id=BACKUP_CHAT_ID,
            message_id=msg.message_id,
            disable_notification=True,
        )

        logger.info(f"backup: ✅ DB backed up to Telegram ({size_kb} KB)")
        return True

    except TelegramError as e:
        logger.warning(f"backup: Backup failed (Telegram error) — {e}")
    except Exception as e:
        logger.error(f"backup: Backup failed — {e}", exc_info=True)

    return False


# ── Scheduled loop ─────────────────────────────────────────────────────────────

async def _backup_loop(bot: Bot, db_path: str):
    """Background coroutine: backup every BACKUP_INTERVAL seconds."""
    logger.info(
        f"backup: Auto-backup loop started "
        f"(every {BACKUP_INTERVAL // 3600}h, chat={BACKUP_CHAT_ID})"
    )
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        await backup_db(bot, db_path)


def start_backup_loop(bot: Bot, db_path: str):
    """
    Start the background backup loop as an asyncio Task.
    Call this ONCE after the bot has started polling.
    """
    global _backup_task
    if not BACKUP_CHAT_ID:
        logger.info("backup: BACKUP_CHAT_ID not set — auto-backup disabled.")
        return

    _backup_task = asyncio.create_task(
        _backup_loop(bot, db_path),
        name="db-backup-loop",
    )
    logger.info("backup: Background auto-backup task created.")
