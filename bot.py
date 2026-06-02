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
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent,
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
    START_LOGO_PATH, FORCE_JOIN_TEXT,
)
from utils.keyboards import (
    # Reply keyboards
    main_menu_reply_kb, button_panel_reply_kb, color_reply_kb,
    row_reply_kb, templates_reply_kb, cancel_only_reply_kb,
    done_cancel_reply_kb, remove_kb,
    # Inline keyboards
    post_keyboard, post_list_inline_kb, post_actions_inline_kb,
    confirm_delete_inline_kb, post_saved_inline_kb, channel_list_inline_kb,
    help_main_inline_kb, help_topic_inline_kb,
    welcome_inline_kb, force_join_inline_kb,
    # Button text constants
    BTN_CREATE, BTN_MYPOSTS, BTN_CHANNEL, BTN_STATS, BTN_HELP, BTN_SETTINGS,
    BTN_ADD_URL, BTN_ADD_LD, BTN_ADD_VIEWS, BTN_ADD_SHARE,
    BTN_TEMPLATES, BTN_CLEAR, BTN_PREVIEW, BTN_DONE, BTN_CANCEL,
    TMPL_LD, TMPL_LDV, TMPL_LDS, TMPL_VS, TMPL_S, TMPL_BACK,
    COLOR_LABELS,
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
) = range(11)


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
    BTN_ADD_URL, BTN_ADD_LD, BTN_ADD_VIEWS, BTN_ADD_SHARE,
    BTN_TEMPLATES, BTN_CLEAR, BTN_PREVIEW, BTN_DONE, BTN_CANCEL,
    TMPL_LD, TMPL_LDV, TMPL_LDS, TMPL_VS, TMPL_S, TMPL_BACK,
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
    user_id = update.effective_user.id

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
    HELP_LOGO = r"helplogo.jpg"
    try:
        with open(HELP_LOGO, "rb") as f:
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


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username   = await _get_username(ctx.bot)
    photo_path = r"C:\Users\aagha\.gemini\antigravity\brain\d9b9b5dd-eb35-430f-9d3f-52c24c19876f\help_center_banner_1780375706105.png"
    text = HELP_DICT["main"].format(username=username)
    
    try:
        with open(photo_path, "rb") as f:
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


async def on_send_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """User clicked 📡 Send to Channel"""
    await delete_preview(update, ctx)
    user_id = update.effective_user.id
    channels = await db.get_user_channels(user_id)
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
        top_line = f"\n• <b>Top Post:</b>  #<code>{top['id']}</code>  —  👁️ <b>{fmt_num(top.get('views', 0))}</b> views"
    else:
        top_line = ""

    text = (
        "📊 <b>Stats Overview</b>\n\n"

        "📝  Posts Saved\n"
        f"      <b>{total_posts}</b> of 100  —  <code>{'#' * min(total_posts, 10)}{'-' * (10 - min(total_posts, 10))}</code>\n\n"

        "👍  Likes  ·  👎  Dislikes\n"
        f"      <b>{fmt_num(total_likes)}</b>  ·  <b>{fmt_num(total_dislikes)}</b>\n"
        f"      [{bar}]  {like_pct}% positive\n\n"

        "👁️  Total Views\n"
        f"      <b>{fmt_num(total_views)}</b>"
        f"{top_line}\n\n"

        "<i>🌐 Univora Platform</i>"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_reply_kb()
    )
    return MAIN_MENU


async def on_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await delete_preview(update, ctx)
    username   = await _get_username(ctx.bot)
    photo_path = r"C:\Users\aagha\.gemini\antigravity\brain\d9b9b5dd-eb35-430f-9d3f-52c24c19876f\help_center_banner_1780375706105.png"
    text = HELP_DICT["main"].format(username=username)
    
    try:
        with open(photo_path, "rb") as f:
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
    posts_bar = '█' * min(used_posts, 10) + '░' * (10 - min(used_posts, 10))

    text = (
        "⚙️ <b>Settings</b>\n\n"

        "🤖  About this Bot\n"
        f"      @<code>{uname}</code>\n"
        f"      Part of <a href='https://univora.site'><b>Univora Platform</b></a> 🌐\n"
        f"      Official Channel → <a href='https://t.me/Univora88'>@Univora88</a>\n\n"

        "📊  Your Usage\n"
        f"      Posts:     <b>{used_posts}</b> / 100 <code>[{posts_bar}]</code>\n"
        f"      Channels:  <b>{used_chan}</b> saved\n\n"

        "🔒  Force Join\n"
        f"      <b>@Univora88</b>  —  ✅ Active\n\n"

        "<i>More options coming soon!</i>"
    )
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=main_menu_reply_kb()
    )
    return MAIN_MENU


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
    user_id = update.effective_user.id

    content_type, content, caption = extract_content(msg)
    if not content_type:
        await msg.reply_text("❌ Unsupported content. Send text, photo, video, document, etc.")
        return WAITING_CONTENT

    post_id = await db.create_post(user_id, content_type, content, caption)
    ctx.user_data['current_post_id'] = post_id

    existing = await db.has_reaction_buttons(post_id)
    existing_types = {k for k, v in existing.items() if v}

    await msg.reply_text(
        f"✅ <b>Post #{post_id} created!</b>\n\n"
        f"<b>Type:</b> {content_type.upper()}\n\n"
        "Now choose what buttons to add 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=button_panel_reply_kb(existing_types)
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
        reply_markup=button_panel_reply_kb(existing_types)
    )


async def on_add_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    btn_count = len(await db.get_post_buttons(post_id))
    if btn_count >= MAX_BUTTONS_PER_POST:
        await update.message.reply_text(
            f"⚠️ Max {MAX_BUTTONS_PER_POST} buttons per post!",
            reply_markup=button_panel_reply_kb(set())
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
    kb = post_keyboard(post_id, buttons, counts['likes'], counts['dislikes'], counts['views'])
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
    post_id = ctx.user_data.get('current_post_id')
    if not post_id:
        return await on_cancel_to_menu(update, ctx)
    text = update.message.text
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

    row_num = int(text) - 1  # 0-indexed
    post_id = ctx.user_data['current_post_id']
    btn = ctx.user_data.get('new_btn', {})
    order_num = await db.get_button_count_in_row(post_id, row_num)

    await db.add_button(
        post_id=post_id, button_type='url',
        text=btn.get('text', 'Button'),
        url=btn.get('url'),
        color=btn.get('color', 'default'),
        row_num=row_num, order_num=order_num
    )
    ctx.user_data['new_btn'] = {}
    await update.message.reply_text(
        f"✅ <b>Button Added!</b>\n"
        f"Label: <code>{btn.get('text')}</code>\n"
        f"URL: <code>{btn.get('url')}</code>\n"
        f"Color: <b>{btn.get('color','default')}</b> | Row: <b>{row_num+1}</b>",
        parse_mode=ParseMode.HTML
    )
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
        kb = channel_list_inline_kb(channels, delete_mode=True)
        await q.message.edit_reply_markup(reply_markup=kb)
        return MAIN_MENU
        
    elif q.data == "donechan":
        channels = await db.get_user_channels(user_id)
        kb = channel_list_inline_kb(channels, delete_mode=False)
        await q.message.edit_reply_markup(reply_markup=kb)
        return MAIN_MENU
        
    elif q.data.startswith("pickchan|"):
        chan_id = int(q.data.split("|")[1])
        channels = await db.get_user_channels(user_id)
        channel_str = next((c['channel_username_or_id'] for c in channels if c['id'] == chan_id), None)
        if not channel_str:
            return MAIN_MENU
            
        ctx.user_data['target_channel'] = channel_str
        
        if ctx.user_data.get('direct_send_post_id'):
            post_id = ctx.user_data['direct_send_post_id']
            # Direct send simulation
            progress = await q.message.reply_text(f"⏳ Sending Post #{post_id} to {channel_str}...")
            try:
                from utils.helpers import send_post
                await send_post(ctx.bot, channel_str, post_id, track=True, for_channel=True)
                await db.increment_views(post_id)
                await progress.delete()
                await q.message.reply_text(
                    f"✅ <b>Post #{post_id} sent to {channel_str}!</b>\n\n"
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
                f"📡 Channel: <code>{channel_str}</code>\n\n"
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
    success = await db.add_user_channel(user_id, channel)
    if not success:
        await update.message.reply_text("⚠️ This channel is already saved or limit reached.")
    else:
        await update.message.reply_text(f"✅ Channel {channel} saved successfully!")

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
        reply_markup=button_panel_reply_kb(existing_types)
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

    if action in ('like', 'dislike'):
        likes, dislikes, result = await db.handle_reaction(post_id, user_id, action)
        counts = await db.get_reaction_counts(post_id)
        msgs = {
            ('like',    'added'):   "👍 Liked!",
            ('like',    'removed'): "👍 Like removed",
            ('like',    'changed'): "👍 Switched to Like!",
            ('dislike', 'added'):   "👎 Disliked!",
            ('dislike', 'removed'): "👎 Dislike removed",
            ('dislike', 'changed'): "👎 Switched to Dislike!",
        }
        await q.answer(msgs.get((action, result), "✅"))
        buttons = await db.get_post_buttons(post_id)
        kb = post_keyboard(post_id, buttons, likes, dislikes, counts['views'])
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
        await refresh_post_keyboard(ctx.bot, post_id, likes, dislikes, counts['views'])
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

    # ── Build results ────────────────────────────────
    results = []
    for post in posts[:20]:
        pid     = post['id']
        buttons = await db.get_post_buttons(pid)
        counts  = await db.get_reaction_counts(pid)
        result  = await build_inline_result(post, buttons, counts)
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
        kb   = post_keyboard(post_id, buttons, counts['likes'], counts['dislikes'], new_views)
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
                MessageHandler(txt(BTN_CREATE),   on_create_post),
                MessageHandler(txt(BTN_MYPOSTS),  on_my_posts),
                MessageHandler(txt(BTN_CHANNEL),  on_send_channel),
                MessageHandler(txt(BTN_STATS),    on_stats),
                MessageHandler(txt(BTN_HELP),     on_help),
                MessageHandler(txt(BTN_SETTINGS), on_settings),
                MessageHandler(txt(BTN_CANCEL),   on_cancel_to_menu),
                # Inline callbacks that can re-enter flow
                CallbackQueryHandler(edit_buttons_callback, pattern=r"^edit_btns\|"),
                CallbackQueryHandler(sendch_callback,       pattern=r"^sendch\|"),
                CallbackQueryHandler(channel_manager_callback, pattern=r"^(addchan|delchan\||pickchan\||rmchan|donechan|cancel)"),
                CallbackQueryHandler(inline_create_callback, pattern="^inline_create$"),
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
                MessageHandler(txt(BTN_TEMPLATES), on_templates),
                MessageHandler(txt(BTN_CLEAR),     on_clear_buttons),
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
            WAITING_NEW_CHANNEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_channel)
            ],
            WAITING_CHANNEL_POST_ID: [
                MessageHandler(txt(BTN_CANCEL), on_cancel_to_menu),
                # Accept any numeric input (post IDs like 1, 2, 10, 100)
                MessageHandler(filters.Regex(r'^\d+$'), receive_channel_post_id),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", on_cancel_to_menu),
            CommandHandler("start",  cmd_start),
        ],
        allow_reentry=True,
        per_chat=True,
        per_user=True,
        per_message=False,
    )

    app.add_handler(conv)

    # ─── Outside-conversation inline callbacks ─────────────
    app.add_handler(CallbackQueryHandler(reaction_callback,     pattern=r"^react\|"))
    app.add_handler(CallbackQueryHandler(posts_page_callback,   pattern=r"^posts_page\|"))
    app.add_handler(CallbackQueryHandler(post_menu_callback,    pattern=r"^postmenu\|"))
    app.add_handler(CallbackQueryHandler(post_stats_callback,   pattern=r"^poststats\|"))
    app.add_handler(CallbackQueryHandler(delete_post_callback,  pattern=r"^delpost\|"))
    app.add_handler(CallbackQueryHandler(confirm_delete_callback, pattern=r"^confirmdelete\|"))
    app.add_handler(CallbackQueryHandler(inline_myposts_callback, pattern=r"^inline_myposts$"))
    app.add_handler(CallbackQueryHandler(help_callback,           pattern=r"^help\|"))
    app.add_handler(CallbackQueryHandler(check_join_callback,     pattern=r"^check_join$"))
    app.add_handler(CallbackQueryHandler(welcome_launch_callback, pattern=r"^welcome_launch$"))
    app.add_handler(CallbackQueryHandler(welcome_help_callback,   pattern=r"^welcome_help$"))
    # ─── Inline mode ──────────────────────────────────────
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(ChosenInlineResultHandler(chosen_inline_result))

    # ─── Commands outside conv ────────────────────────────
    app.add_handler(CommandHandler("help",   cmd_help))

    return app


async def main():
    # Start keep-alive Flask server if running on Render
    if os.environ.get("RENDER"):
        import keep_alive
        keep_alive.start()

    app = build_app()
    await db.init_db()
    await app.initialize()
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
