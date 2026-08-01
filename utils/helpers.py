"""
Helper utilities — send/update posts, format numbers, validate URLs,
build inline query results.
"""

import re
import logging
from telegram import (
    Bot, Message,
    InlineQueryResultArticle, InputTextMessageContent,
    InlineQueryResultCachedPhoto, InlineQueryResultCachedVideo,
    InlineQueryResultCachedDocument, InlineQueryResultCachedGif,
    InlineQueryResultCachedAudio, InlineQueryResultCachedVoice,
    InlineQueryResultCachedSticker,
)
from telegram.error import TelegramError, BadRequest
from telegram.constants import ParseMode

import database as db
from utils.keyboards import post_keyboard

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────
#   FORMAT HELPERS
# ─────────────────────────────────────────────────────

def fmt_num(n: int) -> str:
    """Format large numbers: 1500 → 1.5K"""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'^(https?|tg)://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9\-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}|'
        r'localhost|\d{1,3}(?:\.\d{1,3}){3})'
        r'(?::\d+)?(?:/[^\s]*)?$',
        re.IGNORECASE
    )
    return bool(pattern.match(url.strip()))


def extract_content(message: Message) -> tuple[str, str, str | None]:
    """
    Extract (content_type, content/file_id, caption) from a message.
    Returns (None, None, None) if unsupported.
    """
    if message.text:
        return 'text', message.text, None
    elif message.photo:
        return 'photo', message.photo[-1].file_id, message.caption
    elif message.video:
        return 'video', message.video.file_id, message.caption
    elif message.document:
        return 'document', message.document.file_id, message.caption
    elif message.animation:
        return 'animation', message.animation.file_id, message.caption
    elif message.audio:
        return 'audio', message.audio.file_id, message.caption
    elif message.voice:
        return 'voice', message.voice.file_id, message.caption
    elif message.video_note:
        return 'video_note', message.video_note.file_id, None
    elif message.sticker:
        return 'sticker', message.sticker.file_id, None
    return None, None, None


# ─────────────────────────────────────────────────────
#   SEND POST
# ─────────────────────────────────────────────────────

async def send_post(bot: Bot, chat_id: int | str, post_id: int,
                    extra_markup=None, track: bool = True,
                    for_channel: bool = False) -> Message | None:
    """
    Send a post to chat_id.

    for_channel=True  → uses switch_inline_query_chosen_chat for Share button
                         (Telegram forbids switch_inline_query in channels)
    track=True        → saves chat_id + message_id to sent_messages table
    """
    post = await db.get_post(post_id)
    if not post:
        return None

    buttons = await db.get_post_buttons(post_id)
    counts  = await db.get_reaction_counts(post_id)
    markup  = extra_markup or post_keyboard(
        post_id, buttons,
        counts=counts,
        for_channel=for_channel,
        bot_username=bot.username
    )

    ct      = post['content_type']
    content = post['content']
    caption = post.get('caption')

    try:
        if ct == 'text':
            msg = await bot.send_message(
                chat_id, content, parse_mode=ParseMode.HTML, reply_markup=markup)
        elif ct == 'photo':
            msg = await bot.send_photo(
                chat_id, content, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=markup)
        elif ct == 'video':
            msg = await bot.send_video(
                chat_id, content, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=markup)
        elif ct == 'document':
            msg = await bot.send_document(
                chat_id, content, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=markup)
        elif ct == 'animation':
            msg = await bot.send_animation(
                chat_id, content, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=markup)
        elif ct == 'audio':
            msg = await bot.send_audio(
                chat_id, content, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=markup)
        elif ct == 'voice':
            msg = await bot.send_voice(
                chat_id, content, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=markup)
        elif ct == 'video_note':
            msg = await bot.send_video_note(chat_id, content, reply_markup=markup)
        elif ct == 'sticker':
            msg = await bot.send_sticker(chat_id, content, reply_markup=markup)
        else:
            return None

        if track:
            await db.save_sent_message(
                post_id, chat_id=msg.chat_id, message_id=msg.message_id)
        return msg

    except TelegramError as e:
        logger.error(f"send_post error (post={post_id}, chat={chat_id}): {e}")
        raise


# ─────────────────────────────────────────────────────
#   UPDATE REACTIONS ON ALL SENT COPIES
# ─────────────────────────────────────────────────────

async def refresh_post_keyboard(bot: Bot, post_id: int, counts: dict = None):
    """
    Update the inline keyboard on every sent copy of this post
    (both regular messages and inline-sent messages).
    """
    post     = await db.get_post(post_id)
    buttons  = await db.get_post_buttons(post_id)
    keyboard = post_keyboard(post_id, buttons, counts=counts)
    sent_list = await db.get_sent_messages(post_id)

    for sent in sent_list:
        try:
            if sent.get('inline_message_id'):
                iid = sent['inline_message_id']
                if post['content_type'] == 'text':
                    await bot.edit_message_text(
                        text=post['content'],
                        inline_message_id=iid,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
                    )
                else:
                    await bot.edit_message_caption(
                        caption=post.get('caption', ''),
                        inline_message_id=iid,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard
                    )
            elif sent.get('chat_id') and sent.get('message_id'):
                await bot.edit_message_reply_markup(
                    chat_id=sent['chat_id'],
                    message_id=sent['message_id'],
                    reply_markup=keyboard
                )
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.warning(f"refresh_post_keyboard BadRequest: {e}")
        except TelegramError as e:
            logger.warning(f"refresh_post_keyboard error: {e}")


# ─────────────────────────────────────────────────────
#   POST PREVIEW TEXT
# ─────────────────────────────────────────────────────

async def build_preview_caption(post_id: int) -> str:
    post    = await db.get_post(post_id)
    buttons = await db.get_post_buttons(post_id)
    counts  = await db.get_reaction_counts(post_id)

    ct = post['content_type'].upper()
    lines = [
        f"<b>📋 Post #{post_id} Preview</b>",
        f"<b>Type:</b> {ct}",
        f"<b>Buttons:</b> {len(buttons)}",
        f"<b>👍</b> {counts['likes']}  <b>👎</b> {counts['dislikes']}  <b>👁️</b> {counts['views']}",
    ]
    if buttons:
        lines.append("\n<b>Button Layout:</b>")
        rows: dict[int, list] = {}
        for b in buttons:
            rn = b.get('row_num', 0)
            rows.setdefault(rn, []).append(b)
        for rn in sorted(rows.keys()):
            row_desc = " | ".join(f"[{b['text']}]" for b in rows[rn])
            lines.append(f"  Row {rn+1}: {row_desc}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────
#   INLINE RESULTS BUILDER
#
#   Uses "Cached" variants (file_id based) so ALL media types
#   work perfectly in inline mode without needing public URLs.
# ─────────────────────────────────────────────────────

CT_EMOJI = {
    'text':       '📝',
    'photo':      '📷',
    'video':      '🎥',
    'document':   '📎',
    'animation':  '🎞️',
    'audio':      '🎵',
    'voice':      '🎙️',
    'video_note': '🎥',
    'sticker':    '🎭',
}


async def build_inline_result(post: dict, buttons: list, counts: dict, bot_username: str = None) -> object | None:
    """
    Build a single InlineQueryResult for a post.

    Uses Cached (file_id) variants for all media so inline mode works
    without public URLs. Text posts use InlineQueryResultArticle.
    """
    post_id  = post['id']
    ct       = post['content_type']
    content  = post['content']
    caption  = post.get('caption') or ''
    emoji    = CT_EMOJI.get(ct, '📎')

    keyboard = post_keyboard(
        post_id, buttons,
        counts=counts,
        for_channel=False,  # inline mode is always from personal chats
        bot_username=bot_username
    )

    stats = (
        f"👍{fmt_num(counts['likes'])}  "
        f"👎{fmt_num(counts['dislikes'])}  "
        f"👁️{fmt_num(counts['views'])}"
    )

    # ── TEXT ──────────────────────────────────────────
    if ct == 'text':
        preview = content[:80] + ('…' if len(content) > 80 else '')
        return InlineQueryResultArticle(
            id=str(post_id),
            title=f"{emoji} Post #{post_id}",
            description=f"{preview}\n{stats}",
            input_message_content=InputTextMessageContent(
                message_text=content,
                parse_mode=ParseMode.HTML
            ),
            reply_markup=keyboard
        )

    # ── PHOTO ─────────────────────────────────────────
    elif ct == 'photo':
        return InlineQueryResultCachedPhoto(
            id=str(post_id),
            photo_file_id=content,
            title=f"{emoji} Photo Post #{post_id}",
            description=f"{caption[:80] or 'Photo'}\n{stats}",
            caption=caption or None,
            parse_mode=ParseMode.HTML if caption else None,
            reply_markup=keyboard
        )

    # ── VIDEO ─────────────────────────────────────────
    elif ct == 'video':
        return InlineQueryResultCachedVideo(
            id=str(post_id),
            video_file_id=content,
            title=f"{emoji} Video Post #{post_id}",
            description=f"{caption[:80] or 'Video'}\n{stats}",
            caption=caption or None,
            parse_mode=ParseMode.HTML if caption else None,
            reply_markup=keyboard
        )

    # ── DOCUMENT ──────────────────────────────────────
    elif ct == 'document':
        return InlineQueryResultCachedDocument(
            id=str(post_id),
            document_file_id=content,
            title=f"{emoji} Document Post #{post_id}",
            description=f"{caption[:80] or 'Document'}\n{stats}",
            caption=caption or None,
            parse_mode=ParseMode.HTML if caption else None,
            reply_markup=keyboard
        )

    # ── GIF / ANIMATION ───────────────────────────────
    elif ct == 'animation':
        return InlineQueryResultCachedGif(
            id=str(post_id),
            gif_file_id=content,
            title=f"{emoji} GIF Post #{post_id}",
            caption=caption or None,
            parse_mode=ParseMode.HTML if caption else None,
            reply_markup=keyboard
        )

    # ── AUDIO ─────────────────────────────────────────
    elif ct == 'audio':
        return InlineQueryResultCachedAudio(
            id=str(post_id),
            audio_file_id=content,
            caption=caption or None,
            parse_mode=ParseMode.HTML if caption else None,
            reply_markup=keyboard
        )

    # ── VOICE ─────────────────────────────────────────
    elif ct == 'voice':
        return InlineQueryResultCachedVoice(
            id=str(post_id),
            voice_file_id=content,
            title=f"{emoji} Voice Post #{post_id}",
            caption=caption or None,
            parse_mode=ParseMode.HTML if caption else None,
            reply_markup=keyboard
        )

    # ── STICKER ───────────────────────────────────────
    elif ct == 'sticker':
        return InlineQueryResultCachedSticker(
            id=str(post_id),
            sticker_file_id=content,
            reply_markup=keyboard
        )

    # ── FALLBACK (video_note, unknown) ────────────────
    else:
        return InlineQueryResultArticle(
            id=str(post_id),
            title=f"{emoji} Post #{post_id} ({ct.upper()})",
            description=f"{caption[:80] or ct}\n{stats}",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"<b>{emoji} Post #{post_id}</b>\n"
                    f"{caption or f'[{ct.upper()} post]'}"
                ),
                parse_mode=ParseMode.HTML
            ),
            reply_markup=keyboard
        )
