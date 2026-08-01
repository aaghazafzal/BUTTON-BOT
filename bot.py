"""
╔══════════════════════════════════════════════════════════╗
║              AUTO BUTTON BOT ⚡ — MAIN v2                ║
║                                                          ║
║  UI Design:                                              ║
║   • ReplyKeyboard  → all flow navigation (BOTTOM)       ║
║   • InlineKeyboard → only actual post buttons            ║
╚══════════════════════════════════════════════════════════╝
"""

import logging
import asyncio
import os
import json
import re

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ChosenInlineResultHandler,
    ConversationHandler, filters, ContextTypes,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest, Forbidden

import database as db
from config import (
    BOT_TOKEN, WELCOME_TEXT, HELP_DICT, BOT_NAME,
    MAX_POSTS_PER_USER, MAX_BUTTONS_PER_POST,
    FORCE_JOIN_CHANNEL, FORCE_JOIN_CHANNEL_URL, WEBSITE_URL,
    START_LOGO_PATH, FORCE_JOIN_TEXT, HELP_LOGO_PATH,
    OWNER_IDS,
)
from utils.keyboards import (
    # Reply keyboards
    main_menu_reply_kb, button_panel_reply_kb, color_reply_kb,
    row_reply_kb, templates_reply_kb, cancel_only_reply_kb,
    done_cancel_reply_kb, remove_kb,
    auto_adder_reply_kb, project_panel_reply_kb,
    # Inline keyboards
    post_keyboard, post_list_inline_kb, post_actions_inline_kb,
    confirm_delete_inline_kb, post_saved_inline_kb, channel_list_inline_kb,
    help_main_inline_kb, help_topic_inline_kb,
    welcome_inline_kb, force_join_inline_kb,
    project_post_keyboard, my_projects_inline_kb,
    settings_inline_kb, user_stats_inline_kb,
    # Button text constants
    BTN_CREATE, BTN_MYPOSTS, BTN_CHANNEL, BTN_STATS, BTN_HELP, BTN_SETTINGS,
    BTN_AUTO_ADDER,
    BTN_ADD_URL, BTN_ADD_LD, BTN_ADD_VIEWS, BTN_ADD_SHARE, BTN_ADD_CUSTOM_REACTION,
    BTN_TEMPLATES, BTN_CLEAR, BTN_PREVIEW, BTN_DONE, BTN_CANCEL,
    TMPL_LD, TMPL_LDV, TMPL_LDS, TMPL_VS, TMPL_S, TMPL_BACK,
    BTN_PROJ_NEW, BTN_PROJ_ADD_POST, BTN_MY_PROJECTS, BTN_BACK_MAIN,
    COLOR_LABELS, BTN_REMOVE_BTN, remove_button_reply_kb
)
from utils.helpers import (
    send_post, refresh_post_keyboard, extract_content,
    is_valid_url, build_preview_caption, build_inline_result, fmt_num,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
#           CONVERSATION STATES
# ═══════════════════════════════════════════════════════

(
    MAIN_MENU,          # idle — main menu reply keyboard shown
    WAITING_CONTENT,    # waiting for post content
    MANAGING_BUTTONS,   # button panel shown (reply keyboard)
    ADDING_URL_TEXT,    # waiting for URL button label
    ADDING_URL_URL,     # waiting for URL
    ADDING_URL_COLOR,   # color reply keyboard shown
    ADDING_URL_ROW,     # row reply keyboard shown
    IN_TEMPLATES,       # template selection
    WAITING_CHANNEL,    # waiting for channel id
    WAITING_NEW_CHANNEL, # waiting for new channel
    WAITING_CHANNEL_POST_ID,  # waiting for post_id to send to channel
    REMOVING_BUTTON,    # selecting button to remove
    WAITING_POST_TITLE  # waiting for optional post title
) = range(13)

# ─── Auto Button Adder states ────────────────────────────────────────────────
AUTO_ADDER_HOME  = 12   # auto adder hub menu
PROJ_WAIT_FWD    = 13   # waiting for forwarded post / @channelname
PROJ_MANAGE_BTNS = 14   # project button panel
POST_WAIT_LINK   = 15   # waiting for t.me/c/... link
POST_MANAGE_BTNS = 16   # add-to-post button panel
ADDING_REACTION_TEXT  = 17 # waiting for custom reaction emoji/text
ADDING_REACTION_COLOR = 18 # waiting for custom reaction color
ADDING_REACTION_ROW   = 19 # waiting for custom reaction row

# ─── Filter helpers ──────────────────────────────────────────────────────────

def txt(s: str):
    """Exact text filter for reply keyboard buttons."""
    return filters.Text([s])

def txt_any(*args):
    return filters.Text(list(args))

# All known reply-keyboard button texts (so they don't go to content handler)
# IMPORTANT: Do NOT add digit strings here — they would block post IDs and channel IDs!
ALL_NAV_BUTTONS = [
    BTN_CREATE, BTN_MYPOSTS, BTN_CHANNEL, BTN_STATS, BTN_HELP, BTN_SETTINGS,
    BTN_AUTO_ADDER,
    BTN_ADD_URL, BTN_ADD_LD, BTN_ADD_VIEWS, BTN_ADD_SHARE,
    BTN_TEMPLATES, BTN_CLEAR, BTN_PREVIEW, BTN_DONE, BTN_CANCEL,
    TMPL_LD, TMPL_LDV, TMPL_LDS, TMPL_VS, TMPL_S, TMPL_BACK,
    BTN_PROJ_NEW, BTN_PROJ_ADD_POST, BTN_MY_PROJECTS, BTN_BACK_MAIN,
] + list(COLOR_LABELS.keys())


# ═══════════════════════════════════════════════════════
#           /start — MAIN MENU
# ═══════════════════════════════════════════════════════

# ─── Bot username cache (avoids repeated API calls → faster responses) ────────
_bot_username: str = ""

async def _get_username(bot) -> str:
    global _bot_username
    if not _bot_username:
        me = await bot.get_me()
        _bot_username = me.username
    return _bot_username


async def _is_member(bot, user_id: int, channel: str) -> bool:
    """Check if user is a member of the force-join channel."""
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return True  # If check fails, allow access (bot might not be in channel)


async def _send_welcome(update_or_message, ctx, is_message=True):
    """Send the branded welcome card with logo and colorful buttons."""
    uname = await _get_username(ctx.bot)
    kb = welcome_inline_kb(FORCE_JOIN_CHANNEL_URL, WEBSITE_URL, uname)
    try:
        with open(START_LOGO_PATH, "rb") as f:
            if is_message:
                await update_or_message.reply_photo(
                    photo=f,
                    caption=WELCOME_TEXT,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
            else:
                await update_or_message.edit_message_media(
                    media=__import__('telegram').InputMediaPhoto(f, caption=WELCOME_TEXT, parse_mode=ParseMode.HTML),
                    reply_markup=kb
                )
    except Exception:
        if is_message:
            await update_or_message.reply_text(
                WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=kb
            )


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    user    = update.effective_user
    user_id = user.id

    # ── Register / update user in MongoDB ──────────────────────────
    await db.register_user(
        user_id    = user_id,
        username   = user.username,
        first_name = user.first_name,
        last_name  = user.last_name,
    )

    # Force join check
    if not await _is_member(ctx.bot, user_id, FORCE_JOIN_CHANNEL):
        try:
            with open(START_LOGO_PATH, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=FORCE_JOIN_TEXT,
                    parse_mode=ParseMode.HTML,
                    reply_markup=force_join_inline_kb(FORCE_JOIN_CHANNEL_URL),
                )
        except Exception:
            await update.message.reply_text(
                FORCE_JOIN_TEXT,
                parse_mode=ParseMode.HTML,
                reply_markup=force_join_inline_kb(FORCE_JOIN_CHANNEL_URL),
            )
        return MAIN_MENU

    # Parse deep links (e.g. /start post_123)
    if ctx.args:
        payload = ctx.args[0]
        if payload.startswith("post_"):
            try:
                post_id = int(payload.split("_")[1])
                await send_post(ctx.bot, update.effective_chat.id, post_id, track=False)
                return MAIN_MENU
            except Exception:
                pass

    await _send_welcome(update.message, ctx, is_message=True)
    await update.message.reply_text(
        "👇 Choose an option from the menu:",
        reply_markup=main_menu_reply_kb()
    )
    return MAIN_MENU


async def check_join_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Called when user clicks '✅ I Joined — Check Again'."""
    q = update.callback_query
    await q.answer("Checking...")
    user_id = update.effective_user.id

    if await _is_member(ctx.bot, user_id, FORCE_JOIN_CHANNEL):
        # Access granted — edit message to welcome card
        uname = await _get_username(ctx.bot)
        kb = welcome_inline_kb(FORCE_JOIN_CHANNEL_URL, WEBSITE_URL, uname)
        try:
            await q.edit_message_caption(
                caption=WELCOME_TEXT,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        except Exception:
            await q.edit_message_text(
                text=WELCOME_TEXT,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        await ctx.bot.send_message(
            chat_id=user_id,
            text="✅ <b>Access Granted!</b>\n\nWelcome to Univora Button Bot! 🎉\n\nUse the menu below to get started:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
    else:
        await q.answer("❌ You haven't joined yet! Please join first.", show_alert=True)


async def welcome_launch_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Called when user clicks '🚀 Launch Bot' on the welcome card."""
    q = update.callback_query
    await q.answer("🚀 Let's go!")
    await ctx.bot.send_message(
        chat_id=update.effective_user.id,
        text="✅ <b>Bot Launched!</b>\n\nUse the menu below to start creating posts:",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_reply_kb()
    )


async def welcome_help_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Called when user clicks 'ℹ️ Help Center' on the welcome card."""
    q = update.callback_query
    await q.answer()
    username = await _get_username(ctx.bot)
    text = HELP_DICT["main"].format(username=username)
    try:
        with open(HELP_LOGO_PATH, "rb") as f:
            await ctx.bot.send_photo(
                chat_id=update.effective_user.id,
                photo=f,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=help_main_inline_kb()
            )
    except Exception:
        await ctx.bot.send_message(
            chat_id=update.effective_user.id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=help_main_inline_kb()
        )


# ════════════════════════════════════════════════════════
#   ADMIN-ONLY /stats  — Full Bot Statistics Card
# ════════════════════════════════════════════════════════

async def cmd_admin_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /stats command — ADMIN ONLY.
    Shows a beautiful premium card with complete bot analytics.
    """
    user_id = update.effective_user.id

    # ── Admin gate ────────────────────────────────────────────
    if OWNER_IDS and user_id not in OWNER_IDS:
        await update.message.reply_text(
            "🔒 <b>Access Denied</b>\n\n"
            "This command is restricted to bot administrators only.",
            parse_mode=ParseMode.HTML
        )
        return

    # If OWNER_IDS is empty → any user can call it (fresh install fallback)

    wait_msg = await update.message.reply_text("⏳ Fetching stats…")

    try:
        s = await db.get_global_stats()
    except Exception as e:
        await wait_msg.edit_text(
            f"❌ <b>Stats Error</b>\n\n<code>{e}</code>",
            parse_mode=ParseMode.HTML
        )
        return

    # ── Timestamp ──────────────────────────────────────────────
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%d %b %Y • %H:%M UTC")

    # ── Top user mention ────────────────────────────────────────
    if s["top_user_id"]:
        try:
            chat = await ctx.bot.get_chat(s["top_user_id"])
            top_name = (chat.username and f"@{chat.username}") or chat.full_name or str(s["top_user_id"])
        except Exception:
            top_name = f"User #{s['top_user_id']}"
        top_line = f"👑 <b>Top Creator:</b>  {top_name}  ({s['top_user_posts']} posts)"
    else:
        top_line = "👑 <b>Top Creator:</b>  —"

    card = (
        "╔══════════════════════════════════════╗\n"
        "║   📊  <b>UNIVORA BUTTON BOT — STATS</b>   ║\n"
        "╚══════════════════════════════════════╝\n\n"

        "━━━━━━  👥  <b>USERS</b>  ━━━━━━\n"
        f"   Total Bot Users     :  <b>{s['total_users']:,}</b>\n"
        f"   Active Today        :  <b>{s['today_users']:,}</b>\n\n"

        "━━━━━━  📝  <b>POSTS</b>  ━━━━━━\n"
        f"   Total Posts Created :  <b>{s['total_posts']:,}</b>\n"
        f"   Created Today       :  <b>{s['posts_today']:,}</b>\n\n"

        "━━━━━━  🔘  <b>BUTTONS</b>  ━━━━━━\n"
        f"   Total Buttons       :  <b>{s['total_buttons']:,}</b>\n"
        f"   ├ 🔗 URL Buttons    :  <b>{s['url_buttons']:,}</b>\n"
        f"   ├ 👍 Like Buttons   :  <b>{s['like_buttons']:,}</b>\n"
        f"   ├ 👁️ View Buttons   :  <b>{s['view_buttons']:,}</b>\n"
        f"   └ 📤 Share Buttons  :  <b>{s['share_buttons']:,}</b>\n\n"

        "━━━━━━  ❤️  <b>ENGAGEMENT</b>  ━━━━━━\n"
        f"   Total 👍 Likes      :  <b>{s['total_likes']:,}</b>\n"
        f"   Total 👎 Dislikes   :  <b>{s['total_dislikes']:,}</b>\n"
        f"   Total 👁️ Views      :  <b>{s['total_views']:,}</b>\n"
        f"   Total 📤 Shares     :  <b>{s['total_shares']:,}</b>\n"
        f"   Total Interactions  :  <b>{s['total_reactions']:,}</b>\n\n"

        "━━━━━━  📡  <b>CHANNELS</b>  ━━━━━━\n"
        f"   Saved Channels      :  <b>{s['total_saved_channels']:,}</b>\n"
        f"   Posts Sent          :  <b>{s['total_sent_messages']:,}</b>\n\n"

        "━━━━━━  ⚡  <b>AUTO BUTTON ADDER</b>  ━━━━━━\n"
        f"   Total Projects      :  <b>{s['total_projects']:,}</b>\n"
        f"   🟢 Active Projects  :  <b>{s['active_projects']:,}</b>\n"
        f"   Auto-Reacted Posts  :  <b>{s['ch_auto_reacted']:,}</b>\n\n"

        "━━━━━━  🏆  <b>TOP STAT</b>  ━━━━━━\n"
        f"   {top_line}\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   🕐  Generated: <code>{now}</code>\n"
        "   🌐  Platform: <b>Univora</b> (univora.website)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    await wait_msg.edit_text(
        card,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats_refresh",
                                 api_kwargs={"style": "primary"}),
            InlineKeyboardButton("🌐 Univora", url="https://univora.website",
                                 api_kwargs={"style": "success"}),
        ]])
    )


async def admin_stats_refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Inline 🔄 Refresh button for /stats card."""
    q = update.callback_query
    await q.answer("🔄 Refreshing…")
    user_id = update.effective_user.id

    if OWNER_IDS and user_id not in OWNER_IDS:
        await q.answer("🔒 Admins only!", show_alert=True)
        return

    try:
        s = await db.get_global_stats()
    except Exception as e:
        await q.answer(f"Error: {e}", show_alert=True)
        return

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%d %b %Y • %H:%M UTC")

    if s["top_user_id"]:
        try:
            chat = await ctx.bot.get_chat(s["top_user_id"])
            top_name = (chat.username and f"@{chat.username}") or chat.full_name or str(s["top_user_id"])
        except Exception:
            top_name = f"User #{s['top_user_id']}"
        top_line = f"👑 <b>Top Creator:</b>  {top_name}  ({s['top_user_posts']} posts)"
    else:
        top_line = "👑 <b>Top Creator:</b>  —"

    card = (
        "╔══════════════════════════════════════╗\n"
        "║   📊  <b>UNIVORA BUTTON BOT — STATS</b>   ║\n"
        "╚══════════════════════════════════════╝\n\n"
        "━━━━━━  👥  <b>USERS</b>  ━━━━━━\n"
        f"   Total Bot Users     :  <b>{s['total_users']:,}</b>\n"
        f"   Active Today        :  <b>{s['today_users']:,}</b>\n\n"
        "━━━━━━  📝  <b>POSTS</b>  ━━━━━━\n"
        f"   Total Posts Created :  <b>{s['total_posts']:,}</b>\n"
        f"   Created Today       :  <b>{s['posts_today']:,}</b>\n\n"
        "━━━━━━  🔘  <b>BUTTONS</b>  ━━━━━━\n"
        f"   Total Buttons       :  <b>{s['total_buttons']:,}</b>\n"
        f"   ├ 🔗 URL Buttons    :  <b>{s['url_buttons']:,}</b>\n"
        f"   ├ 👍 Like Buttons   :  <b>{s['like_buttons']:,}</b>\n"
        f"   ├ 👁️ View Buttons   :  <b>{s['view_buttons']:,}</b>\n"
        f"   └ 📤 Share Buttons  :  <b>{s['share_buttons']:,}</b>\n\n"
        "━━━━━━  ❤️  <b>ENGAGEMENT</b>  ━━━━━━\n"
        f"   Total 👍 Likes      :  <b>{s['total_likes']:,}</b>\n"
        f"   Total 👎 Dislikes   :  <b>{s['total_dislikes']:,}</b>\n"
        f"   Total 👁️ Views      :  <b>{s['total_views']:,}</b>\n"
        f"   Total 📤 Shares     :  <b>{s['total_shares']:,}</b>\n"
        f"   Total Interactions  :  <b>{s['total_reactions']:,}</b>\n\n"
        "━━━━━━  📡  <b>CHANNELS</b>  ━━━━━━\n"
        f"   Saved Channels      :  <b>{s['total_saved_channels']:,}</b>\n"
        f"   Posts Sent          :  <b>{s['total_sent_messages']:,}</b>\n\n"
        "━━━━━━  ⚡  <b>AUTO BUTTON ADDER</b>  ━━━━━━\n"
        f"   Total Projects      :  <b>{s['total_projects']:,}</b>\n"
        f"   🟢 Active Projects  :  <b>{s['active_projects']:,}</b>\n"
        f"   Auto-Reacted Posts  :  <b>{s['ch_auto_reacted']:,}</b>\n\n"
        "━━━━━━  🏆  <b>TOP STAT</b>  ━━━━━━\n"
        f"   {top_line}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   🕐  Generated: <code>{now}</code>\n"
        "   🌐  Platform: <b>Univora</b> (univora.website)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    try:
        await q.edit_message_text(
            card,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats_refresh",
                                     api_kwargs={"style": "primary"}),
                InlineKeyboardButton("🌐 Univora", url="https://univora.website",
                                     api_kwargs={"style": "success"}),
            ]])
        )
    except Exception:
        pass


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = await _get_username(ctx.bot)
    text = HELP_DICT["main"].format(username=username)
    try:
        with open(HELP_LOGO_PATH, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=help_main_inline_kb()
            )
    except Exception:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=help_main_inline_kb()
        )
    return MAIN_MENU

async def cmd_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """About this bot"""
    username = await _get_username(ctx.bot)
    text = (
        "╭────[ 👤 <b>ᴍʏ ᴅᴇᴛᴀɪʟs</b> ]────⍟\n"
        f"├⍟ 🤖 <b>ʙᴏᴛ ɴᴀᴍᴇ :</b> <a href='https://t.me/{username}'>BUTTON BOT [UNIVORA]</a>\n"
        "├⍟ 👨‍💻 <b>ᴅᴇᴠᴇʟᴏᴘᴇʀ :</b> <a href='https://t.me/rolexsir_8'>Rolex Sir</a>\n"
        "├⍟ 🌐 <b>ᴡᴇʙsɪᴛᴇ :</b> <a href='https://univora.website/'>univora.website</a>\n"
        "├⍟ 📚 <b>ᴘʟᴀᴛꜰᴏʀᴍ :</b> ᴜɴɪᴠᴏʀᴀ ᴘʟᴀᴛꜰᴏʀᴍ\n"
        "├⍟ ⚡ <b>ʟɪʙʀᴀʀʏ :</b> <a href='https://python-telegram-bot.org/'>ᴘʏᴛʜᴏɴ-ᴛᴇʟᴇɢʀᴀᴍ-ʙᴏᴛ</a>\n"
        "├⍟ 💻 <b>ʟᴀɴɢᴜᴀɢᴇ :</b> <a href='https://www.python.org/download/releases/3.0/'>ᴘʏᴛʜᴏɴ 𝟹</a>\n"
        "├⍟ 🛠 <b>ʙᴜɪʟᴅ Sᴛᴀᴛᴜs :</b> ᴠ2.0 [ ꜱᴛᴀʙʟᴇ ]\n"
        "╰───────────────⍟\n\n"
        "🎓 <i>Hello! I am a student and I create bots like this just for enjoyment and learning. This bot is proudly presented to you by the Univora Platform.</i>\n\n"
        "⚠️ <b>Dɪsᴄʟᴀɪᴍᴇʀ :</b> <i>I am an inline button generation bot. I do not store or host any media files. I simply help users attach beautiful buttons to their existing posts. The content shared using my buttons is the sole responsibility of the respective users!</i>"
    )
    try:
        with open(START_LOGO_PATH, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
    except Exception:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )


# ═══════════════════════════════════════════════════════
#           MAIN MENU BUTTON HANDLERS
# ═══════════════════════════════════════════════════════

async def on_create_post(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User clicked 📝 Create Post"""
    await delete_preview(update, ctx)
    user_id = update.effective_user.id
    count = await db.count_user_posts(user_id)
    if count >= MAX_POSTS_PER_USER:
        await update.message.reply_text(
            f"⚠️ You've reached the limit of <b>{MAX_POSTS_PER_USER}</b> posts.\n"
            "Delete some old posts first with /mypost",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
        return MAIN_MENU

    await update.message.reply_text(
        "📝 <b>Create New Post</b>\n\n"
        "Send me your post content:\n"
        "• Text message\n"
        "• Photo / Video / Document\n"
        "• GIF / Audio / Voice / Sticker\n\n"
        "<i>Send anything now...</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    return WAITING_CONTENT


async def on_my_posts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User clicked 📋 My Posts"""
    await delete_preview(update, ctx)
    user_id = update.effective_user.id
    posts = await db.get_user_posts(user_id)
    if not posts:
        await update.message.reply_text(
            "📭 You don't have any posts yet!\n\nCreate your first post 👇",
            reply_markup=main_menu_reply_kb()
        )
        return MAIN_MENU

    await update.message.reply_text(
        f"📋 <b>Your Posts ({len(posts)})</b>\n\nTap a post to manage it:",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_reply_kb()
    )
    await update.message.reply_text(
        "Select:", reply_markup=post_list_inline_kb(posts, page=0)
    )
    return MAIN_MENU


async def _resolve_channel_titles(bot, channels: list) -> list:
    """
    For any channel row missing a title, try to fetch it from Telegram
    and update the DB in the background. Returns updated list.
    """
    updated = []
    for ch in channels:
        if not ch.get('channel_title'):
            try:
                chat = await bot.get_chat(ch['channel_username_or_id'])
                title = chat.title or chat.username or ch['channel_username_or_id']
                await db.update_channel_title(ch['id'], title)
                ch = dict(ch)          # make a mutable copy
                ch['channel_title'] = title
            except Exception:
                pass  # can't resolve — show ID as fallback
        updated.append(ch)
    return updated


async def on_send_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User clicked 📡 Send to Channel"""
    await delete_preview(update, ctx)
    user_id  = update.effective_user.id
    channels = await db.get_user_channels(user_id)
    channels = await _resolve_channel_titles(ctx.bot, channels)   # lazy name fetch
    kb = channel_list_inline_kb(channels)
    await update.message.reply_text(
        "📡 <b>Channel Manager</b>\n\n"
        "Select a channel to send a post, or manage your channels:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    return MAIN_MENU


async def on_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User clicked 📊 Stats"""
    await delete_preview(update, ctx)
    user_id = update.effective_user.id
    posts   = await db.get_user_posts(user_id)

    total_posts    = len(posts)
    total_likes    = sum(p.get('likes',    0) for p in posts)
    total_dislikes = sum(p.get('dislikes', 0) for p in posts)
    total_views    = sum(p.get('views',    0) for p in posts)
    total_reactions = total_likes + total_dislikes

    # Engagement bars
    if total_reactions:
        like_pct    = round(total_likes    / total_reactions * 100)
        dislike_pct = 100 - like_pct
        bar_filled  = round(like_pct / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
    else:
        like_pct = dislike_pct = 0
        bar = "░" * 10

    # Top post by views
    if posts and total_views > 0:
        top = max(posts, key=lambda p: p.get('views', 0))
        top_line = f"\n   👑 <b>Top Post:</b>  #<code>{top['id']}</code>  —  👁️ <b>{fmt_num(top.get('views', 0))}</b> views"
    else:
        top_line = ""

    text = (
        "╔══════════════════════════════════════╗\n"
        "║       📊  <b>YOUR STATS OVERVIEW</b>        ║\n"
        "╚══════════════════════════════════════╝\n\n"

        "━━━━━━  📝  <b>POSTS SAVED</b>  ━━━━━━\n"
        f"   <b>{total_posts}</b> of 100  —  <code>{'#' * min(total_posts, 10)}{'-' * (10 - min(total_posts, 10))}</code>\n\n"

        "━━━━━━  ❤️  <b>ENGAGEMENT</b>  ━━━━━━\n"
        f"   👍 <b>Likes:</b>  <b>{fmt_num(total_likes)}</b>\n"
        f"   👎 <b>Dislikes:</b>  <b>{fmt_num(total_dislikes)}</b>\n"
        f"   <code>[{bar}]</code>  {like_pct}% positive\n\n"

        "━━━━━━  👁️  <b>TOTAL VIEWS</b>  ━━━━━━\n"
        f"   <b>Count:</b>  <b>{fmt_num(total_views)}</b>"
        f"{top_line}\n\n"

        "<i>🌐 Powered by Univora Platform</i>"
    )
    
    kb = user_stats_inline_kb()
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    return MAIN_MENU

async def user_stats_refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Refresh the user stats card."""
    q = update.callback_query
    await q.answer("Refreshing stats...")
    user_id = update.effective_user.id
    posts   = await db.get_user_posts(user_id)

    total_posts    = len(posts)
    total_likes    = sum(p.get('likes',    0) for p in posts)
    total_dislikes = sum(p.get('dislikes', 0) for p in posts)
    total_views    = sum(p.get('views',    0) for p in posts)
    total_reactions = total_likes + total_dislikes

    if total_reactions:
        like_pct    = round(total_likes    / total_reactions * 100)
        dislike_pct = 100 - like_pct
        bar_filled  = round(like_pct / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
    else:
        like_pct = dislike_pct = 0
        bar = "░" * 10

    if posts and total_views > 0:
        top = max(posts, key=lambda p: p.get('views', 0))
        top_line = f"\n   👑 <b>Top Post:</b>  #<code>{top['id']}</code>  —  👁️ <b>{fmt_num(top.get('views', 0))}</b> views"
    else:
        top_line = ""

    text = (
        "╔══════════════════════════════════════╗\n"
        "║       📊  <b>YOUR STATS OVERVIEW</b>        ║\n"
        "╚══════════════════════════════════════╝\n\n"

        "━━━━━━  📝  <b>POSTS SAVED</b>  ━━━━━━\n"
        f"   <b>{total_posts}</b> of 100  —  <code>{'#' * min(total_posts, 10)}{'-' * (10 - min(total_posts, 10))}</code>\n\n"

        "━━━━━━  ❤️  <b>ENGAGEMENT</b>  ━━━━━━\n"
        f"   👍 <b>Likes:</b>  <b>{fmt_num(total_likes)}</b>\n"
        f"   👎 <b>Dislikes:</b>  <b>{fmt_num(total_dislikes)}</b>\n"
        f"   <code>[{bar}]</code>  {like_pct}% positive\n\n"

        "━━━━━━  👁️  <b>TOTAL VIEWS</b>  ━━━━━━\n"
        f"   <b>Count:</b>  <b>{fmt_num(total_views)}</b>"
        f"{top_line}\n\n"

        "<i>🌐 Powered by Univora Platform</i>"
    )
    
    kb = user_stats_inline_kb()
    if q.message.text_html != text:
        try:
            await q.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
        except Exception:
            pass


async def on_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await delete_preview(update, ctx)
    username   = await _get_username(ctx.bot)
    text = HELP_DICT["main"].format(username=username)
    try:
        with open(HELP_LOGO_PATH, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=help_main_inline_kb()
            )
    except Exception:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=help_main_inline_kb()
        )
    return MAIN_MENU

async def help_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    topic = q.data.split("|")[1]
    username = await _get_username(ctx.bot)  # cached — no API call if already known

    if topic not in HELP_DICT:
        topic = "main"

    text = HELP_DICT[topic].format(username=username)
    kb   = help_main_inline_kb() if topic == "main" else help_topic_inline_kb()

    try:
        if q.message.photo:
            await q.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await q.edit_message_text(text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        pass

async def on_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await delete_preview(update, ctx)
    user_id  = update.effective_user.id
    uname    = await _get_username(ctx.bot)
    posts    = await db.get_user_posts(user_id)
    channels = await db.get_user_channels(user_id)
    used_posts = len(posts)
    used_chan  = len(channels)
    pct = (used_posts / MAX_POSTS_PER_USER) * 10
    filled = int(pct)
    posts_bar = '█' * filled + '░' * (10 - filled)

    text = (
        "╔══════════════════════════════════════╗\n"
        "║      🛠️  <b>UNIVORA BUTTON BOT — SETTINGS</b>      ║\n"
        "╚══════════════════════════════════════╝\n\n"

        "━━━━━━  🤖  <b>ABOUT THIS BOT</b>  ━━━━━━\n"
        f"   <b>Bot ID:</b>  @<code>{uname}</code>\n"
        f"   <b>Network:</b>  <a href='https://univora.website'>Univora Platform</a> 🌐\n\n"

        "━━━━━━  📊  <b>YOUR USAGE</b>  ━━━━━━\n"
        f"   <b>Posts Created:</b>  <b>{used_posts}</b> / {MAX_POSTS_PER_USER}\n"
        f"   <code>[{posts_bar}]</code>\n"
        f"   <b>Saved Channels:</b>  <b>{used_chan}</b> channels"
    )
    
    kb = settings_inline_kb(WEBSITE_URL, FORCE_JOIN_CHANNEL_URL)

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=kb
    )
    return MAIN_MENU

async def settings_refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Callback to refresh the settings card data."""
    q = update.callback_query
    await q.answer("Refreshing settings...")
    
    user_id  = update.effective_user.id
    uname    = await _get_username(ctx.bot)
    posts    = await db.get_user_posts(user_id)
    channels = await db.get_user_channels(user_id)
    used_posts = len(posts)
    used_chan  = len(channels)
    
    pct = (used_posts / MAX_POSTS_PER_USER) * 10
    filled = int(pct)
    posts_bar = '█' * filled + '░' * (10 - filled)

    text = (
        "╔══════════════════════════════════════╗\n"
        "║      🛠️  <b>UNIVORA BUTTON BOT — SETTINGS</b>      ║\n"
        "╚══════════════════════════════════════╝\n\n"

        "━━━━━━  🤖  <b>ABOUT THIS BOT</b>  ━━━━━━\n"
        f"   <b>Bot ID:</b>  @<code>{uname}</code>\n"
        f"   <b>Network:</b>  <a href='https://univora.website'>Univora Platform</a> 🌐\n\n"

        "━━━━━━  📊  <b>YOUR USAGE</b>  ━━━━━━\n"
        f"   <b>Posts Created:</b>  <b>{used_posts}</b> / {MAX_POSTS_PER_USER}\n"
        f"   <code>[{posts_bar}]</code>\n"
        f"   <b>Saved Channels:</b>  <b>{used_chan}</b> channels"
    )
    
    kb = settings_inline_kb(WEBSITE_URL, FORCE_JOIN_CHANNEL_URL)
    
    if q.message.text_html != text:
        try:
            await q.edit_message_text(
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=kb
            )
        except Exception:
            pass



async def on_cancel_to_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """❌ CANCEL from any state → back to main menu."""
    await delete_preview(update, ctx)
    ctx.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled. Back to main menu.",
        reply_markup=main_menu_reply_kb()
    )
    return MAIN_MENU


# ═══════════════════════════════════════════════════════
#           CONTENT RECEIVING
# ═══════════════════════════════════════════════════════

async def receive_content(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """WAITING_CONTENT: User sent post content."""
    msg = update.message

    content_type, content, caption = extract_content(msg)
    if not content_type:
        await msg.reply_text("❌ Unsupported content. Send text, photo, video, document, etc.")
        return WAITING_CONTENT

    ctx.user_data['draft_post'] = {
        'type': content_type,
        'content': content,
        'caption': caption
    }
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Skip", callback_data="skip_title")]
    ])
    await msg.reply_text(
        "📝 <b>Post Name</b>\n\n"
        "Send a custom name for this post (this makes it easier to find in My Posts).\n\n"
        "<i>Or click Skip to use the default name.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    return WAITING_POST_TITLE


async def receive_post_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """WAITING_POST_TITLE: User sends a title or clicks skip."""
    user_id = update.effective_user.id
    draft = ctx.user_data.get('draft_post')
    if not draft:
        await (update.message or update.callback_query.message).reply_text("❌ Session expired. Please try again.")
        return MAIN_MENU

    title = None
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text("⏭️ <i>Skipped naming</i>", parse_mode=ParseMode.HTML)
    elif update.message:
        title = update.message.text.strip()
        
    post_id = await db.create_post(user_id, draft['type'], draft['content'], draft['caption'], title=title)
    ctx.user_data['current_post_id'] = post_id
    ctx.user_data.pop('draft_post', None)

    existing = await db.has_reaction_buttons(post_id)
    existing_types = {k for k, v in existing.items() if v}

    msg = update.message or update.callback_query.message
    await msg.reply_text(
        f"✅ <b>Post #{post_id} created!</b>\n\n"
        f"<b>Type:</b> {draft['type'].upper()}\n"
        f"{f'<b>Name:</b> {title}' if title else ''}\n\n"
        "Now choose what buttons to add 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=button_panel_reply_kb(existing_types, has_buttons=False)
    )
    return MANAGING_BUTTONS


# ═══════════════════════════════════════════════════════
#           BUTTON MANAGEMENT (Reply Keyboard)
# ═══════════════════════════════════════════════════════

async def _refresh_panel(update, ctx, post_id, extra_msg=""):
    existing = await db.has_reaction_buttons(post_id)
    existing_types = {k for k, v in existing.items() if v}
    btn_count = len(await db.get_post_buttons(post_id))
    await update.message.reply_text(
        f"🎛️ <b>Button Manager — Post #{post_id}</b>\n"
        f"Buttons: <b>{btn_count}</b>{(' | ' + extra_msg) if extra_msg else ''}\n\n"
        "Choose what to do 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=button_panel_reply_kb(existing_types, has_buttons=btn_count > 0)
    )


async def on_add_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    btn_count = len(await db.get_post_buttons(post_id))
    if btn_count >= MAX_BUTTONS_PER_POST:
        await update.message.reply_text(
            f"⚠️ Max {MAX_BUTTONS_PER_POST} buttons per post!",
            reply_markup=button_panel_reply_kb(set(), has_buttons=btn_count > 0)
        )
        return MANAGING_BUTTONS
    ctx.user_data['new_btn'] = {}
    await update.message.reply_text(
        "🏷️ <b>Add URL Button</b>\n\n"
        "Send the <b>button label text</b>:\n"
        "<i>e.g., Visit Website, Join Now, Download</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    return ADDING_URL_TEXT


async def on_add_ld(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    existing = await db.has_reaction_buttons(post_id)
    if existing.get('like'):
        await update.message.reply_text("👍👎 Like/Dislike already added!")
        return MANAGING_BUTTONS
    next_row = await db.get_next_row_for_post(post_id)
    await db.add_button(post_id, 'like',    'Like',    row_num=next_row, order_num=0)
    await db.add_button(post_id, 'dislike', 'Dislike', row_num=next_row, order_num=1)
    await _refresh_panel(update, ctx, post_id, "👍👎 Added!")
    return MANAGING_BUTTONS


async def on_add_views(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    existing = await db.has_reaction_buttons(post_id)
    if existing.get('views'):
        await update.message.reply_text("👁️ Views already added!")
        return MANAGING_BUTTONS
    next_row = await db.get_next_row_for_post(post_id)
    await db.add_button(post_id, 'views', 'Views', row_num=next_row, order_num=0)
    await _refresh_panel(update, ctx, post_id, "👁️ Views Added!")
    return MANAGING_BUTTONS


async def on_add_share(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    existing = await db.has_reaction_buttons(post_id)
    if existing.get('share'):
        await update.message.reply_text("📤 Share button already added!")
        return MANAGING_BUTTONS
    next_row = await db.get_next_row_for_post(post_id)
    await db.add_button(post_id, 'share', 'Share', row_num=next_row, order_num=0)
    await _refresh_panel(update, ctx, post_id, "📤 Share Added!")
    return MANAGING_BUTTONS


async def on_add_custom_reaction_init(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    btn_mode = ctx.user_data.get('btn_mode', 'post')
    
    if btn_mode == 'post':
        post_id = ctx.user_data.get('current_post_id')
        if not post_id: return await on_cancel_to_menu(update, ctx)
        btn_count = len(await db.get_post_buttons(post_id))
    else:
        key = 'proj_buttons' if btn_mode == 'project' else 'atp_buttons'
        btns = ctx.user_data.get(key, [])
        btn_count = len(btns)

    if btn_count >= MAX_BUTTONS_PER_POST:
        await update.message.reply_text(f"⚠️ Max {MAX_BUTTONS_PER_POST} buttons per post!")
        if btn_mode == 'project': return PROJ_MANAGE_BTNS
        if btn_mode == 'add_to_post': return POST_MANAGE_BTNS
        return MANAGING_BUTTONS

    await update.message.reply_text(
        "⭐ <b>Add Custom Reaction</b>\n\n"
        "Send the emoji or short text you want for this reaction:\n"
        "<i>e.g., 🔥, ❤️, or 🔥 Fire</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    return ADDING_REACTION_TEXT


async def receive_reaction_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if len(text) > 20:
        await update.message.reply_text("⚠️ Keep it short! Max 20 characters. Try again:", reply_markup=cancel_only_reply_kb())
        return ADDING_REACTION_TEXT
        
    ctx.user_data['new_btn'] = {'button_type': 'custom_reaction', 'text': text}
    await update.message.reply_text(
        "🎨 <b>Choose a color for this reaction button</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=color_reply_kb()
    )
    return ADDING_REACTION_COLOR

async def receive_reaction_color(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    color = COLOR_LABELS.get(label)
    if not color:
        await update.message.reply_text("Please choose a color from the keyboard below 👇")
        return ADDING_REACTION_COLOR

    ctx.user_data['new_btn']['color'] = color
    await update.message.reply_text(
        f"✅ Color: <b>{label}</b>\n\n"
        "📌 <b>Choose row number</b>:\n"
        "<i>Buttons in same row appear side by side</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=row_reply_kb()
    )
    return ADDING_REACTION_ROW

async def receive_reaction_row(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Please choose a row number from the keyboard 👇")
        return ADDING_REACTION_ROW

    row_num   = int(text) - 1  # 0-indexed
    btn       = ctx.user_data.get('new_btn', {})
    btn_mode  = ctx.user_data.get('btn_mode', 'post')
    btn_text  = btn.get('text', 'Reaction')
    btn_color = btn.get('color', 'default')

    confirm_text = (
        f"✅ <b>Reaction Added!</b>\n"
        f"Label: <code>{btn_text}</code>\n"
        f"Color: <b>{btn_color}</b> | Row: <b>{row_num+1}</b>"
    )

    if btn_mode == 'project':
        btns = ctx.user_data.setdefault('proj_buttons', [])
        btns.append({
            'button_type': 'custom_reaction', 'text': btn_text,
            'color': btn_color, 'row_num': row_num,
            'order_num': sum(1 for b in btns if b.get('row_num') == row_num)
        })
        ctx.user_data['new_btn'] = {}
        await update.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
        await _proj_refresh_panel(update, ctx)
        return PROJ_MANAGE_BTNS

    elif btn_mode == 'add_to_post':
        btns = ctx.user_data.setdefault('atp_buttons', [])
        btns.append({
            'button_type': 'custom_reaction', 'text': btn_text,
            'color': btn_color, 'row_num': row_num,
            'order_num': sum(1 for b in btns if b.get('row_num') == row_num)
        })
        ctx.user_data['new_btn'] = {}
        await update.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
        await _atp_refresh_panel(update, ctx)
        return POST_MANAGE_BTNS

    else:
        post_id   = ctx.user_data['current_post_id']
        order_num = await db.get_button_count_in_row(post_id, row_num)
        await db.add_button(
            post_id=post_id, button_type='custom_reaction',
            text=btn_text, url=None, color=btn_color,
            row_num=row_num, order_num=order_num
        )
        ctx.user_data['new_btn'] = {}
        await update.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
        await _refresh_panel(update, ctx, post_id)
        return MANAGING_BUTTONS



async def on_templates(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    await update.message.reply_text(
        "⚡ <b>Quick Templates</b>\n\nChoose a ready-made button set:",
        parse_mode=ParseMode.HTML,
        reply_markup=templates_reply_kb()
    )
    return IN_TEMPLATES


async def on_clear_buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    await db.clear_post_buttons(post_id)
    await _refresh_panel(update, ctx, post_id, "🗑️ All cleared!")
    return MANAGING_BUTTONS


async def on_remove_button_init(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    buttons = await db.get_post_buttons(post_id)
    if not buttons:
        await update.message.reply_text("This post doesn't have any buttons to remove.")
        return MANAGING_BUTTONS
        
    await update.message.reply_text(
        "➖ <b>Remove a Button</b>\n\n"
        "Select the button you want to remove below.\n"
        "⚠️ <i>Warning: This action cannot be reversed.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=remove_button_reply_kb(buttons)
    )
    return REMOVING_BUTTON


async def receive_button_to_remove(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    
    selected_text = update.message.text
    buttons = await db.get_post_buttons(post_id)
    
    # Find the button to remove
    target_idx = -1
    for i, btn in enumerate(buttons):
        if btn.get('text') == selected_text:
            target_idx = i
            break
            
    if target_idx == -1:
        await update.message.reply_text(
            "⚠️ Button not found. Please select a valid button from the menu below, or CANCEL.",
            reply_markup=remove_button_reply_kb(buttons)
        )
        return REMOVING_BUTTON
        
    # Remove it from the database
    removed_btn = buttons.pop(target_idx)
    await db.delete_button(removed_btn['_id'])
    
    # If the button was a reaction or share button, we also need to clear its state
    # Wait, the bot automatically computes existing_types based on what's in the button array? 
    # Let's see... `has_reaction_buttons` scans the array. So removing from DB array is enough!
    
    await _refresh_panel(update, ctx, post_id, f"➖ Removed '{selected_text}'")
    return MANAGING_BUTTONS


async def on_back_to_manage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    await _refresh_panel(update, ctx, post_id, "🔙 Cancelled removal.")
    return MANAGING_BUTTONS



async def on_preview(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)

    await update.message.reply_text("👁 <b>Live Preview:</b>", parse_mode=ParseMode.HTML)
    await send_post(ctx.bot, update.effective_chat.id, post_id, track=False)
    
    return MANAGING_BUTTONS


async def on_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)

    uname = await _get_username(ctx.bot)
    await update.message.reply_text(
        f"✅ <b>Post #{post_id} Saved!</b>\n\n"
        f"🔗 <b>Share via Inline Mode:</b>\n"
        f"Type in any chat:\n<code>@{uname} {post_id}</code>\n\n"
        f"📡 To send to a channel, use:\n<code>/sendto {post_id} @yourchannel</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_reply_kb()
    )
    # Also send the actual post as preview
    post = await db.get_post(post_id)
    buttons = await db.get_post_buttons(post_id)
    counts = await db.get_reaction_counts(post_id)
    kb = post_keyboard(post_id, buttons, counts=counts)
    if kb:
        try:
            await send_post(ctx.bot, update.effective_chat.id, post_id, extra_markup=kb, track=False)
        except Exception:
            pass

    # Show inline save button
    await update.message.reply_text(
        "👇 Quick actions for this post:",
        reply_markup=post_saved_inline_kb(post_id)
    )
    ctx.user_data.pop('current_post_id', None)
    return MAIN_MENU


# ═══════════════════════════════════════════════════════
#           TEMPLATES FLOW
# ═══════════════════════════════════════════════════════

async def on_template_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text     = update.message.text
    btn_mode = ctx.user_data.get('btn_mode', 'post')

    # ─── Project / Add-to-post template mode ─────────────
    if btn_mode in ('project', 'add_to_post'):
        key = 'proj_buttons' if btn_mode == 'project' else 'atp_buttons'
        ctx.user_data[key] = []  # clear before applying template
        btns = ctx.user_data[key]

        def _tmpl_append(btype, row, order):
            btns.append({'button_type': btype, 'row_num': row, 'order_num': order})

        if text == TMPL_LD:
            _tmpl_append('like', 0, 0); _tmpl_append('dislike', 0, 1)
            desc = "👍 Like | 👎 Dislike"
        elif text == TMPL_LDV:
            _tmpl_append('like', 0, 0); _tmpl_append('dislike', 0, 1)
            _tmpl_append('views', 1, 0)
            desc = "👍 Like | 👎 Dislike\n👁️ Views"
        elif text == TMPL_LDS:
            _tmpl_append('like', 0, 0); _tmpl_append('dislike', 0, 1)
            _tmpl_append('share', 1, 0)
            desc = "👍 Like | 👎 Dislike\n📤 Share"
        elif text == TMPL_VS:
            _tmpl_append('views', 0, 0); _tmpl_append('share', 0, 1)
            desc = "👁️ Views | 📤 Share"
        elif text == TMPL_S:
            _tmpl_append('share', 0, 0)
            desc = "📤 Share"
        elif text in (TMPL_BACK, BTN_CANCEL):
            if btn_mode == 'project':
                await _proj_refresh_panel(update, ctx)
                return PROJ_MANAGE_BTNS
            else:
                await _atp_refresh_panel(update, ctx)
                return POST_MANAGE_BTNS
        else:
            if btn_mode == 'project':
                return PROJ_MANAGE_BTNS
            else:
                return POST_MANAGE_BTNS

        await update.message.reply_text(
            f"⚡ <b>Template Applied!</b>\n\n{desc}", parse_mode=ParseMode.HTML
        )
        if btn_mode == 'project':
            await _proj_refresh_panel(update, ctx)
            return PROJ_MANAGE_BTNS
        else:
            await _atp_refresh_panel(update, ctx)
            return POST_MANAGE_BTNS

    # ─── Regular post mode ─────────────────────────────────
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    await db.clear_post_buttons(post_id)

    if text == TMPL_LD:
        await db.add_button(post_id, 'like', 'Like', row_num=0, order_num=0)
        await db.add_button(post_id, 'dislike', 'Dislike', row_num=0, order_num=1)
        desc = "👍 Like | 👎 Dislike"
    elif text == TMPL_LDV:
        await db.add_button(post_id, 'like', 'Like', row_num=0, order_num=0)
        await db.add_button(post_id, 'dislike', 'Dislike', row_num=0, order_num=1)
        await db.add_button(post_id, 'views', 'Views', row_num=1, order_num=0)
        desc = "👍 Like | 👎 Dislike\n👁️ Views"
    elif text == TMPL_LDS:
        await db.add_button(post_id, 'like', 'Like', row_num=0, order_num=0)
        await db.add_button(post_id, 'dislike', 'Dislike', row_num=0, order_num=1)
        await db.add_button(post_id, 'share', 'Share', row_num=1, order_num=0)
        desc = "👍 Like | 👎 Dislike\n📤 Share"
    elif text == TMPL_VS:
        await db.add_button(post_id, 'views', 'Views', row_num=0, order_num=0)
        await db.add_button(post_id, 'share', 'Share', row_num=0, order_num=1)
        desc = "👁️ Views | 📤 Share"
    elif text == TMPL_S:
        await db.add_button(post_id, 'share', 'Share', row_num=0, order_num=0)
        desc = "📤 Share"
    elif text == TMPL_BACK:
        await _refresh_panel(update, ctx, post_id)
        return MANAGING_BUTTONS
    else:
        await _refresh_panel(update, ctx, post_id)
        return MANAGING_BUTTONS

    await update.message.reply_text(
        f"⚡ <b>Template Applied!</b>\n\n{desc}",
        parse_mode=ParseMode.HTML
    )
    await _refresh_panel(update, ctx, post_id)
    return MANAGING_BUTTONS


# ═══════════════════════════════════════════════════════
#           URL BUTTON FLOW
# ═══════════════════════════════════════════════════════

async def receive_button_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("⚠️ Please send the button label text.")
        return ADDING_URL_TEXT
    ctx.user_data['new_btn']['text'] = text
    post_id = ctx.user_data['current_post_id']
    await update.message.reply_text(
        f"✅ Label: <b>{text}</b>\n\n"
        "🔗 Now send the <b>URL</b>:\n"
        "<i>(Must start with https://)</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    return ADDING_URL_URL


async def receive_button_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not is_valid_url(url):
        await update.message.reply_text(
            "❌ Invalid URL. Must start with <code>https://</code> or <code>http://</code>\n\n"
            "Try again:",
            parse_mode=ParseMode.HTML
        )
        return ADDING_URL_URL
    ctx.user_data['new_btn']['url'] = url
    await update.message.reply_text(
        "🎨 <b>Choose button color</b> 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=color_reply_kb()
    )
    return ADDING_URL_COLOR


async def receive_button_color(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    color = COLOR_LABELS.get(label)
    if not color:
        await update.message.reply_text("Please choose a color from the keyboard below 👇")
        return ADDING_URL_COLOR

    ctx.user_data['new_btn']['color'] = color
    post_id = ctx.user_data['current_post_id']
    await update.message.reply_text(
        f"✅ Color: <b>{label}</b>\n\n"
        "📌 <b>Choose row number</b>:\n"
        "<i>Buttons in same row appear side by side</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=row_reply_kb()
    )
    return ADDING_URL_ROW

async def receive_button_row(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Please choose a row number from the keyboard 👇")
        return ADDING_URL_ROW

    row_num   = int(text) - 1  # 0-indexed
    btn       = ctx.user_data.get('new_btn', {})
    btn_mode  = ctx.user_data.get('btn_mode', 'post')

    btn_label = btn.get('text', 'Button')
    btn_url   = btn.get('url')
    btn_color = btn.get('color', 'default')

    confirm_text = (
        f"✅ <b>Button Added!</b>\n"
        f"Label: <code>{btn_label}</code>\n"
        f"URL: <code>{btn_url}</code>\n"
        f"Color: <b>{btn_color}</b> | Row: <b>{row_num+1}</b>"
    )

    if btn_mode == 'project':
        btns = ctx.user_data.setdefault('proj_buttons', [])
        btns.append({
            'button_type': 'url', 'text': btn_label,
            'url': btn_url, 'color': btn_color, 'row_num': row_num,
            'order_num': sum(1 for b in btns if b.get('row_num') == row_num)
        })
        ctx.user_data['new_btn'] = {}
        await update.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
        await _proj_refresh_panel(update, ctx)
        return PROJ_MANAGE_BTNS

    elif btn_mode == 'add_to_post':
        btns = ctx.user_data.setdefault('atp_buttons', [])
        btns.append({
            'button_type': 'url', 'text': btn_label,
            'url': btn_url, 'color': btn_color, 'row_num': row_num,
            'order_num': sum(1 for b in btns if b.get('row_num') == row_num)
        })
        ctx.user_data['new_btn'] = {}
        await update.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
        await _atp_refresh_panel(update, ctx)
        return POST_MANAGE_BTNS

    else:
        # Regular post mode (default)
        post_id   = ctx.user_data['current_post_id']
        order_num = await db.get_button_count_in_row(post_id, row_num)
        await db.add_button(
            post_id=post_id, button_type='url',
            text=btn_label, url=btn_url, color=btn_color,
            row_num=row_num, order_num=order_num
        )
        ctx.user_data['new_btn'] = {}
        await update.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
        await _refresh_panel(update, ctx, post_id)
        return MANAGING_BUTTONS


# ═══════════════════════════════════════════════════════
#           CHANNEL FLOW
# ═══════════════════════════════════════════════════════


async def channel_manager_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = update.effective_user.id
    if q.data == "cancel":
        await q.message.edit_text("❌ Cancelled. Back to main menu.", reply_markup=None)
        return MAIN_MENU

    elif q.data == "addchan":
        cnt = await db.count_user_channels(user_id)
        if cnt >= 10:
            await q.message.reply_text("❌ You can only save up to 10 channels. Please delete one first.")
            return MAIN_MENU
            
        await q.message.reply_text(
            "📡 <b>Add New Channel</b>\n\n"
            "Send your <b>channel username</b> or <b>ID</b>:\n"
            "<code>@mychannel</code> or <code>-100123456789</code>\n\n"
            "⚠️ Make sure I am an <b>admin</b> in the channel!",
            parse_mode=ParseMode.HTML,
            reply_markup=cancel_only_reply_kb()
        )
        return WAITING_NEW_CHANNEL

    elif q.data.startswith("delchan|"):
        chan_id = int(q.data.split("|")[1])
        await db.remove_user_channel(user_id, chan_id)
        channels = await db.get_user_channels(user_id)
        kb = channel_list_inline_kb(channels, delete_mode=True)
        await q.message.edit_reply_markup(reply_markup=kb)
        return MAIN_MENU
        
    elif q.data == "rmchan":
        channels = await db.get_user_channels(user_id)
        channels = await _resolve_channel_titles(ctx.bot, channels)
        kb = channel_list_inline_kb(channels, delete_mode=True)
        await q.message.edit_reply_markup(reply_markup=kb)
        return MAIN_MENU
        
    elif q.data == "donechan":
        channels = await db.get_user_channels(user_id)
        channels = await _resolve_channel_titles(ctx.bot, channels)
        kb = channel_list_inline_kb(channels, delete_mode=False)
        await q.message.edit_reply_markup(reply_markup=kb)
        return MAIN_MENU
        
    elif q.data.startswith("pickchan|"):
        chan_id = int(q.data.split("|")[1])
        channels = await db.get_user_channels(user_id)
        chan_row = next((c for c in channels if c['id'] == chan_id), None)
        if not chan_row:
            return MAIN_MENU

        channel_str  = chan_row['channel_username_or_id']
        channel_name = chan_row.get('channel_title') or channel_str
        ctx.user_data['target_channel'] = channel_str

        if ctx.user_data.get('direct_send_post_id'):
            post_id = ctx.user_data['direct_send_post_id']
            progress = await q.message.reply_text(f"⏳ Sending Post #{post_id} to {channel_name}...")
            try:
                from utils.helpers import send_post
                await send_post(ctx.bot, channel_str, post_id, track=True, for_channel=True)
                await db.increment_views(post_id)
                await progress.delete()
                await q.message.reply_text(
                    f"✅ <b>Post #{post_id} sent to {channel_name}!</b>\n\n"
                    "View your channel to see the post.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=main_menu_reply_kb()
                )
            except Exception as e:
                await progress.delete()
                await q.message.reply_text(f"❌ Failed: {e}", reply_markup=main_menu_reply_kb())

            ctx.user_data['direct_send_post_id'] = None
            return MAIN_MENU
        else:
            posts = await db.get_user_posts(user_id, limit=20)
            if not posts:
                await q.message.reply_text("❌ No posts found. Create one first!")
                return MAIN_MENU
            post_list = "\n".join(
                f"  <code>{p['id']}</code> — {p['content_type'].upper()} | 👍{p.get('likes',0)}"
                for p in posts[:15]
            )
            await q.message.reply_text(
                f"📡 <b>{channel_name}</b>  <code>({channel_str})</code>\n\n"
                f"<b>Your posts:</b>\n{post_list}\n\n"
                "Now type the <b>Post ID</b> number and send:",
                parse_mode=ParseMode.HTML,
                reply_markup=cancel_only_reply_kb()
            )
            return WAITING_CHANNEL_POST_ID

async def receive_new_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    channel = update.message.text.strip()
    if not (channel.startswith('@') or (channel.startswith('-') and channel[1:].isdigit())):
        await update.message.reply_text(
            "⚠️ Invalid format!\n"
            "Send channel username: <code>@mychannel</code>\n"
            "Or numeric ID: <code>-1001234567890</code>",
            parse_mode=ParseMode.HTML
        )
        return WAITING_NEW_CHANNEL

    user_id = update.effective_user.id

    # Try to fetch the channel's display name from Telegram
    channel_title = None
    try:
        chat = await ctx.bot.get_chat(channel)
        channel_title = chat.title or chat.username or channel
    except Exception:
        channel_title = None  # Couldn't fetch — store without title

    success = await db.add_user_channel(user_id, channel, title=channel_title)
    display = f"<b>{channel_title}</b> (<code>{channel}</code>)" if channel_title else f"<code>{channel}</code>"

    if not success:
        await update.message.reply_text("⚠️ This channel is already saved or limit reached.")
    else:
        await update.message.reply_text(
            f"✅ Channel {display} saved successfully!",
            parse_mode=ParseMode.HTML
        )

    channels = await db.get_user_channels(user_id)
    kb = channel_list_inline_kb(channels)
    await update.message.reply_text(
        "📡 <b>Channel Manager</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    return MAIN_MENU


async def receive_channel_post_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Accept only numeric post IDs
    if not text.isdigit():
        await update.message.reply_text(
            "⚠️ Send just the <b>Post ID number</b>, e.g. <code>1</code>",
            parse_mode=ParseMode.HTML
        )
        return WAITING_CHANNEL_POST_ID

    post_id = int(text)
    channel = ctx.user_data.get('target_channel')
    user_id = update.effective_user.id

    if not channel:
        await update.message.reply_text("❌ Channel not set. Start over.", reply_markup=main_menu_reply_kb())
        return MAIN_MENU

    post = await db.get_post(post_id)
    if not post:
        await update.message.reply_text(
            f"❌ Post #{post_id} not found. Check your post list:",
            reply_markup=cancel_only_reply_kb()
        )
        return WAITING_CHANNEL_POST_ID
    if post['user_id'] != user_id:
        await update.message.reply_text("❌ This is not your post.")
        return WAITING_CHANNEL_POST_ID

    # Show sending progress
    progress = await update.message.reply_text("⏳ Sending to channel...")
    try:
        await send_post(ctx.bot, channel, post_id, track=True, for_channel=True)
        await db.increment_views(post_id)
        await progress.delete()
        await update.message.reply_text(
            f"✅ <b>Post #{post_id} sent to {channel}!</b>\n\n"
            "View your channel to see the post.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
    except Forbidden:
        await progress.delete()
        await update.message.reply_text(
            "❌ <b>No permission!</b>\n\n"
            "Steps to fix:\n"
            "1. Open your channel\n"
            "2. Channel Settings → Administrators\n"
            "3. Add @UNIVORA_BUTTONBOT as admin\n"
            "4. Enable 'Post Messages' permission",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
    except BadRequest as e:
        await progress.delete()
        await update.message.reply_text(
            f"❌ <b>Bad Request:</b> <code>{e}</code>\n\n"
            "Make sure the channel ID is correct.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
    except TelegramError as e:
        await progress.delete()
        await update.message.reply_text(
            f"❌ <b>Error:</b> <code>{e}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )

    ctx.user_data.pop('target_channel', None)
    return MAIN_MENU


# ═══════════════════════════════════════════════════════
#           /sendto command (quick channel send)
# ═══════════════════════════════════════════════════════

async def cmd_sendto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /sendto <post_id> @channel"""
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: <code>/sendto &lt;post_id&gt; @channel</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
        return MAIN_MENU

    try:
        post_id = int(args[0])
        channel = args[1]
    except ValueError:
        await update.message.reply_text("❌ Invalid format.", reply_markup=main_menu_reply_kb())
        return MAIN_MENU

    user_id = update.effective_user.id
    post = await db.get_post(post_id)
    if not post or post['user_id'] != user_id:
        await update.message.reply_text("❌ Post not found.", reply_markup=main_menu_reply_kb())
        return MAIN_MENU

    try:
        await send_post(ctx.bot, channel, post_id, track=True, for_channel=True)
        await db.increment_views(post_id)
        await update.message.reply_text(
            f"✅ Post #{post_id} sent to {channel}!",
            reply_markup=main_menu_reply_kb()
        )
    except Forbidden:
        await update.message.reply_text(
            "❌ Add me as admin in that channel first!",
            reply_markup=main_menu_reply_kb()
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}", reply_markup=main_menu_reply_kb())
    return MAIN_MENU


# ═══════════════════════════════════════════════════════
#           /mypost command
# ═══════════════════════════════════════════════════════

async def cmd_mypost(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    posts = await db.get_user_posts(user_id)
    if not posts:
        await update.message.reply_text(
            "📭 No posts yet! Create one 👇",
            reply_markup=main_menu_reply_kb()
        )
        return MAIN_MENU
    await update.message.reply_text(
        f"📋 <b>Your Posts ({len(posts)})</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_reply_kb()
    )
    await update.message.reply_text("Select:", reply_markup=post_list_inline_kb(posts))
    return MAIN_MENU


# ═══════════════════════════════════════════════════════
#           INLINE CALLBACKS (post management, reactions)
# ═══════════════════════════════════════════════════════

async def inline_create_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(
        "📝 <b>Create New Post</b>\n\nSend your post content:",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    ctx.user_data['pending_create'] = True
    return WAITING_CONTENT


async def posts_page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split("|")[1])
    user_id = update.effective_user.id
    posts = await db.get_user_posts(user_id)
    await q.edit_message_reply_markup(reply_markup=post_list_inline_kb(posts, page=page))

async def delete_preview(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Deletes the preview message if it exists in user_data."""
    if 'preview_msg_id' in ctx.user_data:
        try:
            await ctx.bot.delete_message(chat_id=update.effective_chat.id, message_id=ctx.user_data['preview_msg_id'])
        except Exception:
            pass
        finally:
            del ctx.user_data['preview_msg_id']

async def post_menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    post_id = int(q.data.split("|")[1])
    post = await db.get_post(post_id)
    if not post:
        await q.edit_message_text("❌ Post not found!")
        return

    # Delete existing list/stats message
    try:
        await q.message.delete()
    except Exception:
        pass

    # Send the real post as preview
    from utils.helpers import send_post
    preview_msg = await send_post(ctx.bot, update.effective_chat.id, post_id, track=False)
    if preview_msg:
        ctx.user_data['preview_msg_id'] = preview_msg.message_id

    # Send the options menu below the preview
    await ctx.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"⚙️ <b>Options for Post #{post_id}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=post_actions_inline_kb(post_id)
    )


async def post_stats_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await delete_preview(update, ctx)
    q = update.callback_query
    await q.answer()
    post_id = int(q.data.split("|")[1])
    post = await db.get_post(post_id)
    counts = await db.get_reaction_counts(post_id)
    buttons = await db.get_post_buttons(post_id)
    sent = await db.get_sent_messages(post_id)
    total_r = counts['likes'] + counts['dislikes']
    pct = f"{counts['likes']/total_r*100:.1f}%" if total_r else "N/A"

    await q.edit_message_text(
        f"📊 <b>Stats — Post #{post_id}</b>\n\n"
        f"👍 Likes:    <b>{fmt_num(counts['likes'])}</b>\n"
        f"👎 Dislikes: <b>{fmt_num(counts['dislikes'])}</b>\n"
        f"👁️ Views:    <b>{fmt_num(counts['views'])}</b>\n"
        f"📬 Sent to:  <b>{len(sent)}</b> chats\n"
        f"❤️ Approval: <b>{pct}</b>\n"
        f"🔘 Buttons:  <b>{len(buttons)}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data=f"postmenu|{post_id}")
        ]])
    )


async def delete_post_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await delete_preview(update, ctx)
    q = update.callback_query
    await q.answer()
    post_id = int(q.data.split("|")[1])
    await q.edit_message_text(
        f"⚠️ <b>Delete Post #{post_id}?</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_delete_inline_kb(post_id)
    )


async def confirm_delete_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await delete_preview(update, ctx)
    q = update.callback_query
    await q.answer()
    post_id = int(q.data.split("|")[1])
    user_id = update.effective_user.id
    success = await db.delete_post(post_id, user_id)
    text = f"🗑️ Post #{post_id} deleted." if success else "❌ Could not delete."
    await q.edit_message_text(text)


async def cmd_delete_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    post_count = await db.count_user_posts(user_id)
    
    if post_count == 0:
        await update.message.reply_text("🤷‍♂️ You don't have any posts to delete!")
        return
        
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚨 Yes, delete ALL my posts", callback_data="delall_1")],
        [InlineKeyboardButton("❌ No, cancel", callback_data="delall_cancel")]
    ])
    await update.message.reply_text(
        f"⚠️ <b>WARNING</b>\n\nYou are about to delete <b>{post_count}</b> posts. This action CANNOT be undone.\n\nAre you absolutely sure?",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def delete_all_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data == "delall_cancel":
        await q.edit_message_text("✅ <b>Deletion cancelled.</b> Your posts are safe.", parse_mode=ParseMode.HTML)
        return
        
    if q.data == "delall_1":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("☢️ I am 100% SURE. DELETE THEM!", callback_data="delall_2")],
            [InlineKeyboardButton("🛑 Nah, I changed my mind", callback_data="delall_cancel")]
        ])
        await q.edit_message_text(
            "🛑 <b>FINAL WARNING</b>\n\nThis will wipe ALL your posts and their buttons forever. There is no coming back.\n\nDelete everything?",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        return
        
    if q.data == "delall_2":
        user_id = update.effective_user.id
        deleted = await db.delete_all_user_posts(user_id)
        await q.edit_message_text(
            f"🗑️ <b>Deleted!</b>\n\nSuccessfully wiped <b>{deleted}</b> posts from the database.",
            parse_mode=ParseMode.HTML
        )


async def edit_buttons_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Edit button callback — sets current_post_id and enters conversation."""
    await delete_preview(update, ctx)
    q = update.callback_query
    await q.answer()
    post_id = int(q.data.split("|")[1])
    ctx.user_data['current_post_id'] = post_id
    existing = await db.has_reaction_buttons(post_id)
    existing_types = {k for k, v in existing.items() if v}
    btn_count = len(await db.get_post_buttons(post_id))
    try:
        await q.message.delete()
    except Exception:
        pass
    await q.message.reply_text(
        f"✏️ <b>Edit Buttons — Post #{post_id}</b>\n"
        f"Current buttons: <b>{btn_count}</b>\n\n"
        "Choose what to do 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=button_panel_reply_kb(existing_types, has_buttons=btn_count > 0)
    )
    return MANAGING_BUTTONS


async def sendch_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """'Send to Channel' button from post saved screen."""
    await delete_preview(update, ctx)
    q = update.callback_query
    await q.answer()
    post_id = int(q.data.split("|")[1])
    ctx.user_data['direct_send_post_id'] = post_id
    
    user_id = update.effective_user.id
    channels = await db.get_user_channels(user_id)
    kb = channel_list_inline_kb(channels)
    await q.edit_message_text(
        f"📡 <b>Send Post #{post_id} to Channel</b>\n\n"
        "Select a saved channel or add a new one:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    return MAIN_MENU


async def inline_myposts_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await delete_preview(update, ctx)
    q = update.callback_query
    await q.answer()
    user_id = update.effective_user.id
    posts = await db.get_user_posts(user_id)
    if posts:
        await q.edit_message_text("📋 Your posts:", reply_markup=post_list_inline_kb(posts))
    else:
        await q.edit_message_text("No posts yet!")


# ═══════════════════════════════════════════════════════
#           REACTIONS
# ═══════════════════════════════════════════════════════

async def reaction_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split("|")
    action  = parts[1]
    post_id = int(parts[2])
    user_id = update.effective_user.id

    post = await db.get_post(post_id)
    if not post:
        await q.answer("❌ Post not found!", show_alert=True)
        return

    if action != 'views':
        counts, result = await db.handle_reaction(post_id, user_id, action)
        msgs = {
            'added':   f"✅ {action} added!",
            'removed': f"➖ {action} removed",
            'changed': f"✅ Switched to {action}!",
        }
        # Provide better default messages if it's like/dislike
        if action == 'like':
            msgs = {'added': "👍 Liked!", 'removed': "👍 Like removed", 'changed': "👍 Switched to Like!"}
        elif action == 'dislike':
            msgs = {'added': "👎 Disliked!", 'removed': "👎 Dislike removed", 'changed': "👎 Switched to Dislike!"}
            
        await q.answer(msgs.get(result, "✅"))
        buttons = await db.get_post_buttons(post_id)
        kb = post_keyboard(post_id, buttons, counts=counts)
        try:
            if q.inline_message_id:
                if post['content_type'] == 'text':
                    await ctx.bot.edit_message_text(
                        post['content'], inline_message_id=q.inline_message_id,
                        parse_mode=ParseMode.HTML, reply_markup=kb
                    )
                else:
                    await ctx.bot.edit_message_caption(
                        caption=post.get('caption', ''),
                        inline_message_id=q.inline_message_id,
                        parse_mode=ParseMode.HTML, reply_markup=kb
                    )
            else:
                await q.edit_message_reply_markup(reply_markup=kb)
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                logger.warning(f"reaction update: {e}")
                
        # Run the massive refresh in background to prevent lag/blocking
        import asyncio
        asyncio.create_task(refresh_post_keyboard(ctx.bot, post_id, counts))
        
    elif action == 'views':
        counts = await db.get_reaction_counts(post_id)
        await q.answer(f"👁️ {fmt_num(counts['views'])} views", show_alert=True)


# ═══════════════════════════════════════════════════════
#           INLINE QUERY
# ═══════════════════════════════════════════════════════

async def inline_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Inline query handler.
    Usage from any Telegram chat:
      @UNIVORA_BUTTONBOT         → shows ALL your posts
      @UNIVORA_BUTTONBOT 1       → shows post #1 only
      @UNIVORA_BUTTONBOT photo   → shows photo posts
      @UNIVORA_BUTTONBOT hello   → searches in post content/caption
    """
    query   = update.inline_query
    user_id = query.from_user.id
    text    = query.query.strip().lower()

    posts = await db.get_user_posts(user_id, limit=50)

    # ── Filter by query ──────────────────────────────
    if text:
        if text.isdigit():
            # Exact post ID lookup
            posts = [p for p in posts if p['id'] == int(text)]
        else:
            # Search in content, caption, and content_type
            filtered = []
            for p in posts:
                haystack = ' '.join(filter(None, [
                    str(p.get('content') or ''),
                    str(p.get('caption') or ''),
                    p.get('content_type', ''),
                ])).lower()
                if text in haystack:
                    filtered.append(p)
            posts = filtered

    uname = await _get_username(ctx.bot)
    
    # ── Build results ────────────────────────────────
    results = []
    for post in posts[:20]:
        pid     = post['id']
        buttons = await db.get_post_buttons(pid)
        counts  = await db.get_reaction_counts(pid)
        result  = await build_inline_result(post, buttons, counts, bot_username=uname)
        if result:
            results.append(result)

    # ── Empty state ──────────────────────────────────
    if not results:
        if text:
            title = f"No results for '{text[:30]}'"
            desc  = "Try a different search or post ID"
        else:
            title = "No posts yet!"
            desc  = "Go to bot → Create Post first"

        results = [InlineQueryResultArticle(
            id="no_results",
            title=title,
            description=desc,
            input_message_content=InputTextMessageContent(
                "No posts found. Open @UNIVORA_BUTTONBOT to create posts!"
            )
        )]

    await query.answer(results, cache_time=5, is_personal=True)


async def chosen_inline_result(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Called when user SELECTS an inline result.
    - Saves inline_message_id for future reaction updates
    - Increments view count
    - Updates keyboard if views button is present
    """
    result = update.chosen_inline_result
    iid    = result.inline_message_id
    if not iid:
        return

    try:
        post_id = int(result.result_id)
    except (ValueError, TypeError):
        return  # "no_results" placeholder

    # Save for tracking
    await db.save_sent_message(post_id, inline_message_id=iid)

    # Increment view
    new_views = await db.increment_views(post_id)
    counts    = await db.get_reaction_counts(post_id)
    buttons   = await db.get_post_buttons(post_id)

    # If post has views button, update the counter immediately
    has_views = any(b['button_type'] == 'views' for b in buttons)
    if has_views:
        kb   = post_keyboard(post_id, buttons, counts={'likes': counts['likes'], 'dislikes': counts['dislikes'], 'views': new_views})
        post = await db.get_post(post_id)
        try:
            if post['content_type'] == 'text':
                await ctx.bot.edit_message_text(
                    post['content'], inline_message_id=iid,
                    parse_mode=ParseMode.HTML, reply_markup=kb
                )
            else:
                # For all media types: update only the keyboard
                await ctx.bot.edit_message_reply_markup(
                    inline_message_id=iid, reply_markup=kb
                )
        except TelegramError as e:
            logger.debug(f"chosen_inline_result view update: {e}")





# ═══════════════════════════════════════════════════════
#   AUTO BUTTON ADDER  — Home
# ═══════════════════════════════════════════════════════

async def on_auto_adder(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User pressed ⚡ Auto Button Adder from main menu."""
    await delete_preview(update, ctx)
    await update.message.reply_text(
        "⚡ <b>Auto Button Adder</b>\n\n"
        "Automatically add custom buttons to your channel posts!\n\n"
        "🚀 <b>Choose an option below:</b>\n\n"
        "• <b>⚡ Auto Button Project</b> — Auto-add buttons to ALL new posts in a channel\n"
        "• <b>🔗 Add Button to Post</b> — Add buttons to one specific existing post\n"
        "• <b>📁 My Projects</b> — View & manage your projects",
        parse_mode=ParseMode.HTML,
        reply_markup=auto_adder_reply_kb()
    )
    return AUTO_ADDER_HOME


async def on_back_to_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """🔙 Back from auto adder to main menu."""
    await delete_preview(update, ctx)
    ctx.user_data.clear()
    await update.message.reply_text(
        "🏠 Back to main menu.",
        reply_markup=main_menu_reply_kb()
    )
    return MAIN_MENU


# ═══════════════════════════════════════════════════════
#   AUTO BUTTON PROJECT — Setup
# ═══════════════════════════════════════════════════════

async def on_proj_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User chose ⚡ Auto Button Project."""
    await update.message.reply_text(
        "📡 <b>Auto Button Project Setup</b>\n\n"
        "<b>Step 1:</b> Add <b>@UNIVORA_BUTTONBOT</b> as an admin to your channel\n"
        "       (needs <i>Edit Messages</i> permission)\n\n"
        "<b>Step 2:</b> Forward any post from that channel here 👇\n\n"
        "⚠️ Make sure <b>Show sender's name</b> is <b>ENABLED</b> when forwarding.",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    ctx.user_data['proj_buttons'] = []
    return PROJ_WAIT_FWD


async def receive_proj_forward(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Receive the forwarded post — detect the channel."""
    msg = update.message

    # Extract channel from forward origin
    channel_id = None
    channel_title = None

    if msg.forward_origin:
        origin = msg.forward_origin
        if hasattr(origin, 'chat') and origin.chat:
            channel_id    = str(origin.chat.id)
            channel_title = origin.chat.title or origin.chat.username or channel_id
        elif hasattr(origin, 'sender_chat') and origin.sender_chat:
            channel_id    = str(origin.sender_chat.id)
            channel_title = origin.sender_chat.title or channel_id

    if not channel_id:
        await msg.reply_text(
            "⚠️ Couldn't detect a channel from this forward.\n\n"
            "Please forward a post <b>directly from your channel</b>.\n"
            "Make sure <b>Show sender's name</b> is enabled!",
            parse_mode=ParseMode.HTML
        )
        return PROJ_WAIT_FWD

    # Try to get a fresh title via API
    try:
        chat = await ctx.bot.get_chat(channel_id)
        channel_title = chat.title or channel_title
    except Exception:
        pass

    ctx.user_data['proj_channel_id']    = channel_id
    ctx.user_data['proj_channel_title'] = channel_title
    ctx.user_data['proj_buttons']       = []

    existing_types = _proj_existing_types(ctx)
    await msg.reply_text(
        f"✅ <b>Channel detected: {channel_title}</b>\n\n"
        "🎯 Now configure the buttons that will be added to <b>every new post</b>:\n"
        "(Like/Dislike, Views, Share, URL buttons — all supported!)",
        parse_mode=ParseMode.HTML,
        reply_markup=project_panel_reply_kb(existing_types)
    )
    return PROJ_MANAGE_BTNS


def _proj_existing_types(ctx) -> set:
    """Return set of button_types already in project_buttons."""
    return {b['button_type'] for b in ctx.user_data.get('proj_buttons', [])}


async def _proj_refresh_panel(update, ctx, extra=""):
    btns   = ctx.user_data.get('proj_buttons', [])
    ch     = ctx.user_data.get('proj_channel_title', 'Channel')
    types  = _proj_existing_types(ctx)
    await update.message.reply_text(
        f"🎛️ <b>Project: {ch}</b>\n"
        f"Buttons: <b>{len(btns)}</b>{' | ' + extra if extra else ''}\n\n"
        "Add or remove buttons 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=project_panel_reply_kb(types)
    )


async def on_proj_add_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    btns = ctx.user_data.get('proj_buttons', [])
    if len(btns) >= MAX_BUTTONS_PER_POST:
        await update.message.reply_text(f"⚠️ Max {MAX_BUTTONS_PER_POST} buttons!")
        return PROJ_MANAGE_BTNS
    ctx.user_data['new_btn']   = {}
    ctx.user_data['btn_mode']  = 'project'
    await update.message.reply_text(
        "🏷️ <b>Add URL Button</b>\n\nSend the <b>button label text</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    return ADDING_URL_TEXT


async def on_proj_add_ld(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    existing = _proj_existing_types(ctx)
    if 'like' in existing:
        await update.message.reply_text("👍👎 Already added!")
        return PROJ_MANAGE_BTNS
    btns = ctx.user_data.setdefault('proj_buttons', [])
    row  = max((b.get('row_num', 0) for b in btns), default=-1) + 1
    btns.append({'button_type': 'like',    'row_num': row, 'order_num': 0})
    btns.append({'button_type': 'dislike', 'row_num': row, 'order_num': 1})
    await _proj_refresh_panel(update, ctx, "👍👎 Added!")
    return PROJ_MANAGE_BTNS


async def on_proj_add_views(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    existing = _proj_existing_types(ctx)
    if 'views' in existing:
        await update.message.reply_text("👁️ Views already added!")
        return PROJ_MANAGE_BTNS
    btns = ctx.user_data.setdefault('proj_buttons', [])
    row  = max((b.get('row_num', 0) for b in btns), default=-1) + 1
    btns.append({'button_type': 'views', 'row_num': row, 'order_num': 0})
    await _proj_refresh_panel(update, ctx, "👁️ Views Added!")
    return PROJ_MANAGE_BTNS


async def on_proj_add_share(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    existing = _proj_existing_types(ctx)
    if 'share' in existing:
        await update.message.reply_text("📤 Share already added!")
        return PROJ_MANAGE_BTNS
    btns = ctx.user_data.setdefault('proj_buttons', [])
    row  = max((b.get('row_num', 0) for b in btns), default=-1) + 1
    btns.append({'button_type': 'share', 'row_num': row, 'order_num': 0})
    await _proj_refresh_panel(update, ctx, "📤 Share Added!")
    return PROJ_MANAGE_BTNS


async def on_proj_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['proj_buttons'] = []
    await _proj_refresh_panel(update, ctx, "🗑️ All cleared!")
    return PROJ_MANAGE_BTNS


async def on_proj_preview(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    btns   = ctx.user_data.get('proj_buttons', [])
    ch_id  = ctx.user_data.get('proj_channel_id', '0')
    uname  = await _get_username(ctx.bot)
    kb     = project_post_keyboard(ch_id, 0, btns, bot_username=uname)
    await update.message.reply_text(
        "📝 <b>DEMO POST</b>\n\n"
        "This is a preview of how your channel posts will look with buttons.\n\n"
        "<i>Note: Like/Dislike/Views counts will start at 0 for real posts.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    return PROJ_MANAGE_BTNS


async def on_proj_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id    = update.effective_user.id
    channel_id = ctx.user_data.get('proj_channel_id')
    ch_title   = ctx.user_data.get('proj_channel_title', channel_id)
    btns       = ctx.user_data.get('proj_buttons', [])

    if not channel_id:
        await update.message.reply_text("❌ No channel set. Please restart the process.")
        return await on_cancel_to_menu(update, ctx)
    if not btns:
        await update.message.reply_text("⚠️ Add at least one button before saving!")
        return PROJ_MANAGE_BTNS

    buttons_json = json.dumps(btns)
    await db.save_channel_project(user_id, channel_id, ch_title, buttons_json)

    # Build a preview keyboard
    uname = await _get_username(ctx.bot)
    kb    = project_post_keyboard(channel_id, 0, btns, bot_username=uname)

    await update.message.reply_text(
        f"✅ <b>Project Saved!</b>\n\n"
        f"📢 Channel: <b>{ch_title}</b>\n"
        f"🔘 Buttons: <b>{len(btns)}</b>\n\n"
        "Every <b>new post</b> in this channel will automatically get these buttons! 🚀\n\n"
        "<i>Below is how your posts will look:</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_reply_kb()
    )
    if kb:
        await update.message.reply_text(
            "📝 <b>Preview:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
    ctx.user_data.clear()
    return MAIN_MENU


async def on_proj_templates(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Quick templates for project button setup."""
    ctx.user_data['btn_mode'] = 'project'
    await update.message.reply_text(
        "⚡ <b>Quick Templates</b>\n\nChoose a ready-made button set:",
        parse_mode=ParseMode.HTML,
        reply_markup=templates_reply_kb()
    )
    return IN_TEMPLATES


# ═══════════════════════════════════════════════════════
#   ADD BUTTON TO A CHANNEL POST — Setup
# ═══════════════════════════════════════════════════════

def _parse_tme_link(link: str):
    """
    Parse a t.me post link into (channel_id_or_username, message_id).
    Supports:
      https://t.me/channame/123      → '@channame', 123
      https://t.me/c/1234567890/123  → '-1001234567890', 123
    """
    # Private channel: t.me/c/CHANNEL_ID/MSG_ID
    m = re.match(r'https?://t\.me/c/(\d+)/(\d+)', link.strip())
    if m:
        return f'-100{m.group(1)}', int(m.group(2))
    # Public channel: t.me/username/MSG_ID
    m = re.match(r'https?://t\.me/([A-Za-z0-9_]+)/(\d+)', link.strip())
    if m:
        return f'@{m.group(1)}', int(m.group(2))
    return None, None


async def on_add_to_post_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User chose 🔗 Add Button to Post."""
    await update.message.reply_text(
        "🔗 <b>Add Button to a Channel Post</b>\n\n"
        "Send the link to the post you want to add buttons to:\n\n"
        "📋 <b>Format:</b>\n"
        "  • <code>https://t.me/yourchannel/123</code>\n"
        "  • <code>https://t.me/c/1234567890/123</code>\n\n"
        "⚠️ The bot must be an admin in that channel.",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    ctx.user_data['atp_buttons'] = []
    return POST_WAIT_LINK


async def receive_post_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Parse t.me link, verify channel, start button config."""
    link = update.message.text.strip()
    channel_ref, msg_id = _parse_tme_link(link)

    if not channel_ref or not msg_id:
        await update.message.reply_text(
            "❌ Invalid link format.\n\n"
            "Please send a link like:\n"
            "<code>https://t.me/channelname/123</code>\n"
            "or <code>https://t.me/c/1234567890/123</code>",
            parse_mode=ParseMode.HTML
        )
        return POST_WAIT_LINK

    # Verify channel access
    channel_title = channel_ref
    try:
        chat = await ctx.bot.get_chat(channel_ref)
        channel_title = chat.title or chat.username or channel_ref
        # Normalize to numeric ID for editing
        channel_ref = str(chat.id)
    except Exception:
        await update.message.reply_text(
            "❌ Cannot access that channel.\n\n"
            "Make sure the bot is an admin there, then try again.",
            parse_mode=ParseMode.HTML
        )
        return POST_WAIT_LINK

    ctx.user_data['atp_channel_id']    = channel_ref
    ctx.user_data['atp_channel_title'] = channel_title
    ctx.user_data['atp_msg_id']        = msg_id
    ctx.user_data['atp_buttons']       = []

    await update.message.reply_text(
        f"✅ <b>Post found!</b>\n\n"
        f"📢 Channel: <b>{channel_title}</b>\n"
        f"📝 Message ID: <b>{msg_id}</b>\n\n"
        "Click ➕ to add buttons 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=project_panel_reply_kb(set())
    )
    return POST_MANAGE_BTNS


def _atp_existing_types(ctx) -> set:
    return {b['button_type'] for b in ctx.user_data.get('atp_buttons', [])}


async def _atp_refresh_panel(update, ctx, extra=""):
    btns  = ctx.user_data.get('atp_buttons', [])
    ch    = ctx.user_data.get('atp_channel_title', 'Post')
    mid   = ctx.user_data.get('atp_msg_id', '?')
    types = _atp_existing_types(ctx)
    await update.message.reply_text(
        f"🎛️ <b>Post #{mid}</b> in <b>{ch}</b>\n"
        f"Buttons: <b>{len(btns)}</b>{' | ' + extra if extra else ''}\n\n"
        "Add buttons 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=project_panel_reply_kb(types)
    )


async def on_atp_add_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    btns = ctx.user_data.get('atp_buttons', [])
    if len(btns) >= MAX_BUTTONS_PER_POST:
        await update.message.reply_text(f"⚠️ Max {MAX_BUTTONS_PER_POST} buttons!")
        return POST_MANAGE_BTNS
    ctx.user_data['new_btn']   = {}
    ctx.user_data['btn_mode']  = 'add_to_post'
    await update.message.reply_text(
        "🏷️ <b>Add URL Button</b>\n\nSend the <b>button label text</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=cancel_only_reply_kb()
    )
    return ADDING_URL_TEXT


async def on_atp_add_ld(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    existing = _atp_existing_types(ctx)
    if 'like' in existing:
        await update.message.reply_text("👍👎 Already added!")
        return POST_MANAGE_BTNS
    btns = ctx.user_data.setdefault('atp_buttons', [])
    row  = max((b.get('row_num', 0) for b in btns), default=-1) + 1
    btns.append({'button_type': 'like',    'row_num': row, 'order_num': 0})
    btns.append({'button_type': 'dislike', 'row_num': row, 'order_num': 1})
    await _atp_refresh_panel(update, ctx, "👍👎 Added!")
    return POST_MANAGE_BTNS


async def on_atp_add_views(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    existing = _atp_existing_types(ctx)
    if 'views' in existing:
        await update.message.reply_text("👁️ Already added!")
        return POST_MANAGE_BTNS
    btns = ctx.user_data.setdefault('atp_buttons', [])
    row  = max((b.get('row_num', 0) for b in btns), default=-1) + 1
    btns.append({'button_type': 'views', 'row_num': row, 'order_num': 0})
    await _atp_refresh_panel(update, ctx, "👁️ Views Added!")
    return POST_MANAGE_BTNS


async def on_atp_add_share(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    existing = _atp_existing_types(ctx)
    if 'share' in existing:
        await update.message.reply_text("📤 Already added!")
        return POST_MANAGE_BTNS
    btns = ctx.user_data.setdefault('atp_buttons', [])
    row  = max((b.get('row_num', 0) for b in btns), default=-1) + 1
    btns.append({'button_type': 'share', 'row_num': row, 'order_num': 0})
    await _atp_refresh_panel(update, ctx, "📤 Share Added!")
    return POST_MANAGE_BTNS


async def on_atp_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['atp_buttons'] = []
    await _atp_refresh_panel(update, ctx, "🗑️ Cleared!")
    return POST_MANAGE_BTNS


async def on_atp_preview(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    btns   = ctx.user_data.get('atp_buttons', [])
    ch_id  = ctx.user_data.get('atp_channel_id', '0')
    mid    = ctx.user_data.get('atp_msg_id', 0)
    uname  = await _get_username(ctx.bot)
    kb     = project_post_keyboard(ch_id, mid, btns, bot_username=uname)
    await update.message.reply_text(
        "👁 <b>Preview:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    return POST_MANAGE_BTNS


async def on_atp_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Edit the actual channel post with configured buttons."""
    channel_id = ctx.user_data.get('atp_channel_id')
    msg_id     = ctx.user_data.get('atp_msg_id')
    ch_title   = ctx.user_data.get('atp_channel_title', channel_id)
    btns       = ctx.user_data.get('atp_buttons', [])

    if not channel_id or not msg_id:
        await update.message.reply_text("❌ No post set. Please restart.")
        return await on_cancel_to_menu(update, ctx)
    if not btns:
        await update.message.reply_text("⚠️ Add at least one button first!")
        return POST_MANAGE_BTNS

    uname  = await _get_username(ctx.bot)
    counts = await db.get_or_create_channel_reactions(channel_id, msg_id)
    kb     = project_post_keyboard(
        channel_id, msg_id, btns,
        likes=counts['likes'], dislikes=counts['dislikes'], views=counts['views'],
        bot_username=uname
    )

    try:
        await ctx.bot.edit_message_reply_markup(
            chat_id=int(channel_id), message_id=msg_id, reply_markup=kb
        )
        post_url = f"https://t.me/c/{channel_id.replace('-100', '')}/{msg_id}"
        await update.message.reply_text(
            f"✅ <b>Buttons Added Successfully!</b>\n\n"
            f"📢 Channel: <b>{ch_title}</b>\n"
            f"📝 Message ID: <b>{msg_id}</b>\n"
            f"🔘 Buttons: <b>{len(btns)}</b> added\n\n"
            f"The buttons have been applied to the channel post! 🚀",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
        await update.message.reply_text(
            "👇 View the post:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔗 View Post", url=post_url,
                                     api_kwargs={"style": "primary"})
            ]])
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to edit the post: <code>{e}</code>\n\n"
            "Make sure the bot is an admin with <i>Edit Messages</i> permission.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_reply_kb()
        )
    ctx.user_data.clear()
    return MAIN_MENU


# ═══════════════════════════════════════════════════════
#   MY PROJECTS — View & Manage
# ═══════════════════════════════════════════════════════

async def on_my_projects(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id  = update.effective_user.id
    projects = await db.get_user_projects(user_id)
    if not projects:
        await update.message.reply_text(
            "📁 <b>My Projects</b>\n\n"
            "You have no projects yet.\n\n"
            "Use <b>⚡ Auto Button Project</b> to create your first one!",
            parse_mode=ParseMode.HTML,
            reply_markup=auto_adder_reply_kb()
        )
        return AUTO_ADDER_HOME

    lines = []
    for i, p in enumerate(projects, 1):
        title  = p.get('channel_title') or p['channel_id']
        status = "🟢 Active" if p['is_active'] else "⏸️ Paused"
        date   = p['created_at'][:10]
        lines.append(f"<b>{i}. 📢 {title}</b>\n   {status}  •  📅 {date}")

    text = (
        f"📁 <b>My Projects</b>\n\n"
        + "\n\n".join(lines)
        + f"\n\n📊 Total: <b>{len(projects)}</b>"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=my_projects_inline_kb(projects)
    )
    return AUTO_ADDER_HOME


async def projects_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle inline callbacks from My Projects keyboard."""
    q = update.callback_query
    await q.answer()
    user_id = update.effective_user.id

    if q.data.startswith("proj_del|"):
        pid = int(q.data.split("|")[1])
        ok  = await db.delete_channel_project(user_id, pid)
        if ok:
            projects = await db.get_user_projects(user_id)
            if projects:
                await q.message.edit_reply_markup(reply_markup=my_projects_inline_kb(projects))
                await q.answer("✅ Project deleted!", show_alert=False)
            else:
                await q.message.edit_text("📁 No projects remaining.")
        else:
            await q.answer("❌ Could not delete.", show_alert=True)

    elif q.data.startswith("proj_toggle|"):
        pid      = int(q.data.split("|")[1])
        projects = await db.get_user_projects(user_id)
        proj     = next((p for p in projects if p['id'] == pid), None)
        if proj:
            new_state = not bool(proj['is_active'])
            await db.toggle_channel_project(user_id, pid, new_state)
            projects = await db.get_user_projects(user_id)
            await q.message.edit_reply_markup(reply_markup=my_projects_inline_kb(projects))
            status = "🟢 Activated" if new_state else "⏸️ Paused"
            await q.answer(f"{status}!", show_alert=False)

    elif q.data == "proj_back":
        await q.message.edit_reply_markup(reply_markup=None)


# ═══════════════════════════════════════════════════════
#   CHANNEL POST HANDLER — Auto-apply buttons to new posts
# ═══════════════════════════════════════════════════════

async def on_channel_post(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when a new post appears in a channel where the bot is admin.
    Looks up the project for that channel and auto-applies buttons.
    """
    post = update.channel_post
    if not post:
        return

    channel_id = str(post.chat_id)
    msg_id     = post.message_id

    project = await db.get_channel_project(channel_id)
    if not project or not project['is_active']:
        return

    try:
        btns = json.loads(project.get('buttons_json', '[]'))
    except Exception:
        return

    if not btns:
        return

    counts = await db.get_or_create_channel_reactions(channel_id, msg_id)
    uname  = await _get_username(ctx.bot)
    kb     = project_post_keyboard(
        channel_id, msg_id, btns,
        likes=counts['likes'], dislikes=counts['dislikes'], views=counts['views'],
        bot_username=uname
    )
    if not kb:
        return

    try:
        await ctx.bot.edit_message_reply_markup(
            chat_id=post.chat_id, message_id=msg_id, reply_markup=kb
        )
        logger.info(f"Auto-added buttons to {channel_id}/{msg_id}")
    except Exception as e:
        logger.warning(f"Auto-adder failed for {channel_id}/{msg_id}: {e}")


# ═══════════════════════════════════════════════════════
#   CHANNEL POST REACTIONS — chreact callbacks
# ═══════════════════════════════════════════════════════

async def channel_reaction_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Handle chreact|like|CHANNEL_ID|MSG_ID
             chreact|dislike|CHANNEL_ID|MSG_ID
             chreact|views|CHANNEL_ID|MSG_ID
    """
    q = update.callback_query
    await q.answer()
    user_id = update.effective_user.id

    parts = q.data.split("|")
    if len(parts) != 4:
        return
    _, reaction, channel_id, msg_id_str = parts
    msg_id = int(msg_id_str)

    # Get the project to know the button config
    project = await db.get_channel_project(channel_id)
    if not project:
        await q.answer("⚠️ Project not found.", show_alert=True)
        return

    try:
        btns = json.loads(project.get('buttons_json', '[]'))
    except Exception:
        return

    if reaction != 'views':
        counts = await db.set_channel_user_reaction(channel_id, msg_id, user_id, reaction)
    elif reaction == 'views':
        counts = await db.add_channel_view(channel_id, msg_id, user_id)
    else:
        return

    uname = await _get_username(ctx.bot)
    kb    = project_post_keyboard(
        channel_id, msg_id, btns,
        counts=counts,
        bot_username=uname
    )
    try:
        await q.edit_message_reply_markup(reply_markup=kb)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════
#   Shared URL button flow — MODE-AWARE receive_button_row
# ═══════════════════════════════════════════════════════
# receive_button_text / receive_button_url / receive_button_color stay unchanged.
# receive_button_row is updated below to support 'project' and 'add_to_post' modes.


# ═══════════════════════════════════════════════════════
#           BUILD APPLICATION
# ═══════════════════════════════════════════════════════

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # ─── All navigation buttons text filter ───────────────
    nav_filter = filters.Text(ALL_NAV_BUTTONS)

    # ─── Conversation handler ──────────────────────────────
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start",  cmd_start),
            CommandHandler("newpost", lambda u, c: on_create_post(u, c)),
            CommandHandler("mypost",  cmd_mypost),
            CommandHandler("sendto",  cmd_sendto),
        ],
        states={
            MAIN_MENU: [
                MessageHandler(txt(BTN_CREATE),      on_create_post),
                MessageHandler(txt(BTN_MYPOSTS),     on_my_posts),
                MessageHandler(txt(BTN_CHANNEL),     on_send_channel),
                MessageHandler(txt(BTN_STATS),       on_stats),
                MessageHandler(txt(BTN_HELP),        on_help),
                MessageHandler(txt(BTN_SETTINGS),    on_settings),
                MessageHandler(txt(BTN_AUTO_ADDER),  on_auto_adder),
                MessageHandler(txt(BTN_CANCEL),      on_cancel_to_menu),
                # Inline callbacks that can re-enter flow
                CallbackQueryHandler(edit_buttons_callback,      pattern=r"^edit_btns\|"),
                CallbackQueryHandler(sendch_callback,            pattern=r"^sendch\|"),
                CallbackQueryHandler(channel_manager_callback,   pattern=r"^(addchan|delchan\||pickchan\||rmchan|donechan|cancel)"),
                CallbackQueryHandler(inline_create_callback,     pattern="^inline_create$"),
            ],
            WAITING_CONTENT: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(
                    (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL |
                     filters.ANIMATION | filters.AUDIO | filters.VOICE |
                     filters.VIDEO_NOTE | filters.Sticker.ALL) & ~nav_filter,
                    receive_content
                ),
            ],
            MANAGING_BUTTONS: [
                MessageHandler(txt(BTN_ADD_URL),   on_add_url),
                MessageHandler(txt(BTN_ADD_LD),    on_add_ld),
                MessageHandler(txt(BTN_ADD_VIEWS), on_add_views),
                MessageHandler(txt(BTN_ADD_SHARE), on_add_share),
                MessageHandler(txt(BTN_ADD_CUSTOM_REACTION), on_add_custom_reaction_init),
                MessageHandler(txt(BTN_TEMPLATES), on_templates),
                MessageHandler(txt(BTN_CLEAR),     on_clear_buttons),
                MessageHandler(txt(BTN_REMOVE_BTN),on_remove_button_init),
                MessageHandler(txt(BTN_PREVIEW),   on_preview),
                MessageHandler(txt(BTN_DONE),      on_done),
                MessageHandler(txt(BTN_CANCEL),    on_cancel_to_menu),
            ],
            ADDING_URL_TEXT: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.TEXT & ~nav_filter, receive_button_text),
            ],
            ADDING_URL_URL: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.TEXT & ~nav_filter, receive_button_url),
            ],
            ADDING_URL_COLOR: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.Text(list(COLOR_LABELS.keys())), receive_button_color),
            ],
            ADDING_URL_ROW: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.Text([str(i) for i in range(1, 9)]), receive_button_row),
            ],
            IN_TEMPLATES: [
                MessageHandler(
                    filters.Text([TMPL_LD, TMPL_LDV, TMPL_LDS, TMPL_VS, TMPL_S, TMPL_BACK, BTN_CANCEL]),
                    on_template_pick
                ),
            ],
            REMOVING_BUTTON: [
                MessageHandler(txt(BTN_BACK_MAIN), on_back_to_manage),
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.TEXT & ~nav_filter, receive_button_to_remove),
            ],
            WAITING_NEW_CHANNEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_channel)
            ],
            WAITING_CHANNEL_POST_ID: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.Regex(r'^\d+$'), receive_channel_post_id),
            ],
            WAITING_POST_TITLE: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                CallbackQueryHandler(receive_post_title, pattern=r"^skip_title$"),
                MessageHandler(filters.TEXT & ~nav_filter, receive_post_title),
            ],
            # ─── Auto Button Adder states ─────────────────────────
            AUTO_ADDER_HOME: [
                MessageHandler(txt(BTN_PROJ_NEW),      on_proj_start),
                MessageHandler(txt(BTN_PROJ_ADD_POST), on_add_to_post_start),
                MessageHandler(txt(BTN_MY_PROJECTS),   on_my_projects),
                MessageHandler(txt(BTN_BACK_MAIN),     on_back_to_main),
                MessageHandler(txt(BTN_CANCEL),        on_cancel_to_menu),
                CallbackQueryHandler(projects_callback, pattern=r"^(proj_del|proj_toggle|proj_back)"),
            ],
            PROJ_WAIT_FWD: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.ALL & ~nav_filter, receive_proj_forward),
            ],
            PROJ_MANAGE_BTNS: [
                MessageHandler(txt(BTN_ADD_URL),   on_proj_add_url),
                MessageHandler(txt(BTN_ADD_LD),    on_proj_add_ld),
                MessageHandler(txt(BTN_ADD_VIEWS), on_proj_add_views),
                MessageHandler(txt(BTN_ADD_SHARE), on_proj_add_share),
                MessageHandler(txt(BTN_ADD_CUSTOM_REACTION), on_add_custom_reaction_init),
                MessageHandler(txt(BTN_TEMPLATES), on_proj_templates),
                MessageHandler(txt(BTN_CLEAR),     on_proj_clear),
                MessageHandler(txt(BTN_PREVIEW),   on_proj_preview),
                MessageHandler(txt(BTN_DONE),      on_proj_done),
                MessageHandler(txt(BTN_CANCEL),    on_cancel_to_menu),
            ],
            POST_WAIT_LINK: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.TEXT & ~nav_filter, receive_post_link),
            ],
            POST_MANAGE_BTNS: [
                MessageHandler(txt(BTN_ADD_URL),   on_atp_add_url),
                MessageHandler(txt(BTN_ADD_LD),    on_atp_add_ld),
                MessageHandler(txt(BTN_ADD_VIEWS), on_atp_add_views),
                MessageHandler(txt(BTN_ADD_SHARE), on_atp_add_share),
                MessageHandler(txt(BTN_ADD_CUSTOM_REACTION), on_add_custom_reaction_init),
                MessageHandler(txt(BTN_TEMPLATES), on_proj_templates),  # reuse same template picker
                MessageHandler(txt(BTN_CLEAR),     on_atp_clear),
                MessageHandler(txt(BTN_PREVIEW),   on_atp_preview),
                MessageHandler(txt(BTN_DONE),      on_atp_done),
                MessageHandler(txt(BTN_CANCEL),    on_cancel_to_menu),
            ],
            ADDING_REACTION_TEXT: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.TEXT & ~nav_filter, receive_reaction_text),
            ],
            ADDING_REACTION_COLOR: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.Text(list(COLOR_LABELS.keys())), receive_reaction_color),
            ],
            ADDING_REACTION_ROW: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                MessageHandler(filters.Text([str(i) for i in range(1, 9)]), receive_reaction_row),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", on_cancel_to_menu),
            CommandHandler("start",  cmd_start),
            CommandHandler("deleteall", cmd_delete_all),
        ],
        allow_reentry=True,
        per_chat=True,
        per_user=True,
        per_message=False,
    )

    app.add_handler(conv)

    # ─── Outside-conversation inline callbacks ─────────────
    app.add_handler(CallbackQueryHandler(reaction_callback,       pattern=r"^react\|"))
    app.add_handler(CallbackQueryHandler(channel_reaction_callback, pattern=r"^chreact\|"))
    app.add_handler(CallbackQueryHandler(projects_callback,       pattern=r"^(proj_del|proj_toggle|proj_back)"))
    app.add_handler(CallbackQueryHandler(posts_page_callback,     pattern=r"^posts_page\|"))
    app.add_handler(CallbackQueryHandler(post_menu_callback,      pattern=r"^postmenu\|"))
    app.add_handler(CallbackQueryHandler(post_stats_callback,     pattern=r"^poststats\|"))
    app.add_handler(CallbackQueryHandler(delete_post_callback,    pattern=r"^delpost\|"))
    app.add_handler(CallbackQueryHandler(confirm_delete_callback, pattern=r"^confirmdelete\|"))
    app.add_handler(CallbackQueryHandler(delete_all_callback,     pattern=r"^delall_"))
    app.add_handler(CallbackQueryHandler(inline_myposts_callback, pattern=r"^inline_myposts$"))
    app.add_handler(CallbackQueryHandler(help_callback,           pattern=r"^help\|"))
    app.add_handler(CallbackQueryHandler(check_join_callback,     pattern=r"^check_join$"))
    app.add_handler(CallbackQueryHandler(welcome_launch_callback, pattern=r"^welcome_launch$"))
    app.add_handler(CallbackQueryHandler(welcome_help_callback,   pattern=r"^welcome_help$"))

    # ─── Channel post handler (auto button adder) ──────────
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, on_channel_post))

    # ─── Inline mode ──────────────────────────────────────
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(ChosenInlineResultHandler(chosen_inline_result))

    # ─── Commands outside conv ────────────────────────────
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("deleteall", cmd_delete_all))
    app.add_handler(CommandHandler("stats", cmd_admin_stats))

    # ─── Admin stats refresh callback ────────────────────
    app.add_handler(CallbackQueryHandler(
        admin_stats_refresh_callback, pattern=r"^admin_stats_refresh$"
    ))
    app.add_handler(CallbackQueryHandler(
        settings_refresh_callback, pattern=r"^settings_refresh$"
    ))
    app.add_handler(CallbackQueryHandler(
        user_stats_refresh_callback, pattern=r"^user_stats_refresh$"
    ))

    return app


async def setup_commands(bot):
    """Set the Bot menu commands (Default vs Admin)."""
    default_commands = [
        BotCommand("start", "Open main menu / Check status"),
        BotCommand("help", "Get help and instructions"),
        BotCommand("about", "About this bot & developer"),
        BotCommand("deleteall", "Delete all your posts")
    ]
    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

    admin_commands = default_commands + [
        BotCommand("stats", "View bot statistics (Admin Only)")
    ]
    for admin_id in OWNER_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Could not set admin commands for {admin_id}: {e}")


async def main():
    # ── Keep-alive (Render) ─────────────────────────────────
    if os.environ.get("RENDER"):
        import keep_alive
        keep_alive.start()

    app = build_app()
    await db.init_db()
    await app.initialize()
    await setup_commands(app.bot)

    uname = await _get_username(app.bot)
    logger.info(f"Bot running as @{uname}")
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    stop = asyncio.Event()
    try:
        await stop.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
