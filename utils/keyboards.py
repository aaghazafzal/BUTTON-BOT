"""
Keyboards — Reply (bottom) + Inline (post buttons).

RULE:
  ReplyKeyboardMarkup  → flow navigation (bottom buttons)
  InlineKeyboardMarkup → actual post buttons only
"""

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton,
    SwitchInlineQueryChosenChat,
)
from config import COLOR_EMOJIS, COLORS_DISPLAY

# ─── Button label constants (match text in handlers) ──────────────────────────

BTN_CREATE    = "📝 Create Post"
BTN_MYPOSTS   = "📋 My Posts"
BTN_CHANNEL   = "📡 Send to Channel"
BTN_STATS     = "📊 Stats"
BTN_HELP      = "ℹ️ Help"
BTN_SETTINGS  = "⚙️ Settings"

BTN_ADD_URL   = "➕ Add URL Button"
BTN_ADD_LD    = "👍👎 Add Like / Dislike"
BTN_ADD_VIEWS = "👁️ Views Counter"
BTN_ADD_SHARE = "📤 Share Button"
BTN_TEMPLATES = "⚡ Quick Templates"
BTN_CLEAR     = "🗑️ Clear All Buttons"
BTN_PREVIEW   = "👁 Preview Post"
BTN_DONE      = "✅ DONE"
BTN_CANCEL    = "❌ CANCEL"

# template labels
TMPL_LD   = "👍👎 Like + Dislike"
TMPL_LDV  = "👍👎👁️ Like + Dislike + Views"
TMPL_LDS  = "👍👎📤 Like + Dislike + Share"
TMPL_VS   = "👁️📤 Views + Share"
TMPL_S    = "📤 Share Only"
TMPL_BACK = "🔙 Back to Panel"

# color labels (match COLORS_DISPLAY values in config.py)
COLOR_LABELS = {
    "Default": "default",
    "Red": "red",
    "Blue": "blue",
    "Green": "green",
}
# reverse map: color_key → label
COLOR_LABEL_FROM_KEY = {v: k for k, v in COLOR_LABELS.items()}


# ═══════════════════════════════════════════
#   REPLY KEYBOARDS  (appear at the bottom)
# ═══════════════════════════════════════════

def rk(buttons: list[list[str]], resize=True, one_time=False) -> ReplyKeyboardMarkup:
    """Helper to build a ReplyKeyboardMarkup from string lists."""
    return ReplyKeyboardMarkup(
        buttons, resize_keyboard=resize, one_time_keyboard=one_time
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def main_menu_reply_kb() -> ReplyKeyboardMarkup:
    """Bottom keyboard for main navigation."""
    return rk([
        [BTN_CREATE,  BTN_MYPOSTS],
        [BTN_CHANNEL, BTN_STATS],
        [BTN_HELP,    BTN_SETTINGS],
    ])


def button_panel_reply_kb(existing_types: set) -> ReplyKeyboardMarkup:
    """Bottom keyboard for the button management panel."""
    rows = [[BTN_ADD_URL]]

    if 'like' not in existing_types:
        rows.append([BTN_ADD_LD])

    sub = []
    if 'views' not in existing_types:
        sub.append(BTN_ADD_VIEWS)
    if 'share' not in existing_types:
        sub.append(BTN_ADD_SHARE)
    if sub:
        rows.append(sub)

    rows.append([BTN_TEMPLATES, BTN_CLEAR])
    rows.append([BTN_PREVIEW])
    rows.append([BTN_DONE, BTN_CANCEL])
    return rk(rows)


def color_reply_kb() -> ReplyKeyboardMarkup:
    """Bottom keyboard for color selection."""
    return ReplyKeyboardMarkup([
        [KeyboardButton("Default")],
        [
            KeyboardButton("Red", api_kwargs={"style": "danger"}),
            KeyboardButton("Blue", api_kwargs={"style": "primary"}),
            KeyboardButton("Green", api_kwargs={"style": "success"}),
        ],
        [KeyboardButton(BTN_CANCEL)],
    ], resize_keyboard=True)


def row_reply_kb(max_rows: int = 8) -> ReplyKeyboardMarkup:
    """Bottom keyboard for row number selection."""
    nums = [str(i) for i in range(1, max_rows + 1)]
    # 4 per row
    rows = [nums[i:i+4] for i in range(0, len(nums), 4)]
    rows.append([BTN_CANCEL])
    return rk(rows)


def templates_reply_kb() -> ReplyKeyboardMarkup:
    return rk([
        [TMPL_LD],
        [TMPL_LDV],
        [TMPL_LDS],
        [TMPL_VS],
        [TMPL_S],
        [TMPL_BACK],
    ])


def done_cancel_reply_kb() -> ReplyKeyboardMarkup:
    return rk([[BTN_DONE, BTN_CANCEL]])


def cancel_only_reply_kb() -> ReplyKeyboardMarkup:
    return rk([[BTN_CANCEL]])


# ═══════════════════════════════════════════
#   INLINE KEYBOARDS  (appear on the message)
# ═══════════════════════════════════════════

def post_keyboard(post_id: int, buttons: list,
                  likes: int = 0, dislikes: int = 0,
                  views: int = 0,
                  for_channel: bool = False,
                  bot_username: str = None) -> InlineKeyboardMarkup | None:
    """Build the InlineKeyboardMarkup for the actual post.
    
    for_channel=True: uses url deep-linking for Share button
    (channels don't support switch_inline_query).
    """
    if not buttons:
        return None

    rows: dict[int, list] = {}
    for btn in buttons:
        rn = btn.get('row_num', 0)
        rows.setdefault(rn, [])
        btype = btn['button_type']
        
        color_name = btn.get('color', 'default')

        # Use Telegram Bot API 9.4 styles for supported colors
        kwargs = {}
        if color_name == 'red':
            kwargs['api_kwargs'] = {'style': 'danger'}
        elif color_name == 'green':
            kwargs['api_kwargs'] = {'style': 'success'}
        elif color_name == 'blue':
            kwargs['api_kwargs'] = {'style': 'primary'}

        if btype == 'url':
            ib = InlineKeyboardButton(btn['text'].strip(), url=btn['url'], **kwargs)
        elif btype == 'like':
            ib = InlineKeyboardButton(f"\U0001f44d  {likes}", callback_data=f"react|like|{post_id}")
        elif btype == 'dislike':
            ib = InlineKeyboardButton(f"\U0001f44e  {dislikes}", callback_data=f"react|dislike|{post_id}")
        elif btype == 'views':
            ib = InlineKeyboardButton(f"\U0001f441\ufe0f  {views}", callback_data=f"react|views|{post_id}")
        elif btype == 'share':
            if for_channel and bot_username:
                # In channels, we MUST use a URL deep-link to trigger inline query
                ib = InlineKeyboardButton(
                    "\U0001f4e4 Share",
                    url=f"https://t.me/{bot_username}?startinline={post_id}"
                )
            else:
                ib = InlineKeyboardButton("\U0001f4e4 Share", switch_inline_query=str(post_id))
        else:
            continue
        rows[rn].append(ib)

    keyboard = [rows[rn] for rn in sorted(rows.keys()) if rows[rn]]
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def post_list_inline_kb(posts: list, page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    """Inline keyboard for listing posts (not in flow, so stays inline)."""
    start = page * page_size
    page_posts = posts[start: start + page_size]
    total_pages = max(1, (len(posts) + page_size - 1) // page_size)

    rows = []
    for p in page_posts:
        label = f"#{p['id']} │ {p['content_type'].upper()} │ 👍{p.get('likes',0)} 👎{p.get('dislikes',0)}"
        rows.append([InlineKeyboardButton(label, callback_data=f"postmenu|{p['id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"posts_page|{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"posts_page|{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton("📝 New Post", callback_data="inline_create"),
    ])
    return InlineKeyboardMarkup(rows)


def post_actions_inline_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📡 Send to Channel", callback_data=f"sendch|{post_id}"),
            InlineKeyboardButton("✏️ Edit Buttons",    callback_data=f"edit_btns|{post_id}"),
        ],
        [
            InlineKeyboardButton("📊 Stats",           callback_data=f"poststats|{post_id}"),
            InlineKeyboardButton("🗑️ Delete",          callback_data=f"delpost|{post_id}"),
        ],
        [
            InlineKeyboardButton("🔙 Back to My Posts", callback_data="inline_myposts"),
        ],
    ])


def confirm_delete_inline_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirmdelete|{post_id}"),
        InlineKeyboardButton("❌ No, Keep",    callback_data=f"postmenu|{post_id}"),
    ]])


def post_saved_inline_kb(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Send to Channel", callback_data=f"sendch|{post_id}")],
        [InlineKeyboardButton("📋 My Posts",        callback_data="inline_myposts")],
    ])

def channel_list_inline_kb(channels: list, delete_mode: bool = False) -> InlineKeyboardMarkup:
    """Keyboard for selecting or managing channels."""
    kb = []
    for ch in channels:
        ch_id = ch['channel_username_or_id']
        if delete_mode:
            kb.append([InlineKeyboardButton(f"❌ Delete {ch_id}", callback_data=f"delchan|{ch['id']}")])
        else:
            kb.append([InlineKeyboardButton(f"📡 {ch_id}", callback_data=f"pickchan|{ch['id']}")])
    
    # Bottom actions
    actions = []
    if len(channels) < 10 and not delete_mode:
        actions.append(InlineKeyboardButton("➕ Add Channel", callback_data="addchan"))
    if channels:
        if delete_mode:
            actions.append(InlineKeyboardButton("✅ Done Deleting", callback_data="donechan"))
        else:
            actions.append(InlineKeyboardButton("🗑️ Remove", callback_data="rmchan"))
            
    if actions:
        kb.append(actions)
        
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(kb)


def help_main_inline_kb() -> InlineKeyboardMarkup:
    """Main keyboard for the Help Center — styled with native colors."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📝 Basics", callback_data="help|basics",
                api_kwargs={"style": "primary"}
            ),
            InlineKeyboardButton(
                "📡 Channels", callback_data="help|channels",
                api_kwargs={"style": "success"}
            ),
        ],
        [
            InlineKeyboardButton(
                "🔘 Buttons & Reactions", callback_data="help|buttons",
                api_kwargs={"style": "primary"}
            ),
        ],
        [
            InlineKeyboardButton(
                "🔗 Inline Sharing", callback_data="help|sharing",
                api_kwargs={"style": "success"}
            ),
        ],
    ])

def help_topic_inline_kb() -> InlineKeyboardMarkup:
    """Keyboard to return to the main Help Center from a topic."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Topics", callback_data="help|main")]
    ])


def welcome_inline_kb(channel_url: str, website_url: str, bot_username: str) -> InlineKeyboardMarkup:
    """Colorful inline keyboard for the /start welcome message."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Join Univora Channel",
                url=channel_url,
                api_kwargs={"style": "primary"}
            ),
        ],
        [
            InlineKeyboardButton(
                "🌐 Visit Website",
                url=website_url,
                api_kwargs={"style": "success"}
            ),
            InlineKeyboardButton(
                "ℹ️ Help Center",
                callback_data="welcome_help",
                api_kwargs={"style": "primary"}
            ),
        ],
        [
            InlineKeyboardButton(
                "🚀 Launch Bot",
                callback_data="welcome_launch",
                api_kwargs={"style": "success"}
            ),
        ],
    ])


def force_join_inline_kb(channel_url: str) -> InlineKeyboardMarkup:
    """Keyboard shown when user hasn't joined the required channel."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Join @Univora88",
                url=channel_url,
                api_kwargs={"style": "primary"}
            ),
        ],
        [
            InlineKeyboardButton(
                "✅ I Joined — Check Again",
                callback_data="check_join",
                api_kwargs={"style": "success"}
            ),
        ],
    ])
