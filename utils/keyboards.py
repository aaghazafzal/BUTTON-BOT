"""
Keyboards — Reply (bottom) + Inline (post / menu buttons).

COLOR SYSTEM  (Telegram Bot API 9.4 native styles):
  primary  = Blue   → main actions, navigation, info
  success  = Green  → confirm, done, positive, create
  danger   = Red    → delete, cancel, destructive

RULE:
  ReplyKeyboardMarkup  → flow navigation (bottom buttons)
  InlineKeyboardMarkup → actual post / menu buttons
"""

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton,
    SwitchInlineQueryChosenChat,
)
from config import COLOR_EMOJIS, COLORS_DISPLAY

# ─── Button label constants ────────────────────────────────────────────────────

BTN_CREATE    = "✨ Create Post"
BTN_MYPOSTS   = "📂 My Posts"
BTN_CHANNEL   = "🚀 Send to Channel"
BTN_STATS     = "📈 Stats"
BTN_HELP      = "💡 Help"
BTN_SETTINGS  = "🛠️ Settings"
BTN_AUTO_ADDER = "💠 Auto Button Adder"

BTN_ADD_URL      = "➕ Add URL Button"
BTN_ADD_LD       = "👍👎 Add Like / Dislike"
BTN_ADD_VIEWS    = "👁️ Views Counter"
BTN_ADD_SHARE    = "📤 Share Button"
BTN_ADD_CUSTOM_REACTION = "⭐ Add Reaction"
BTN_TEMPLATES    = "⚡ Quick Templates"
BTN_CLEAR        = "🗑️ Clear All Buttons"
BTN_PREVIEW      = "👁 Preview Post"
BTN_DONE         = "✅ DONE"
BTN_CANCEL       = "❌ CANCEL"
BTN_REMOVE_BTN   = "➖ Remove Button"

TMPL_LD   = "👍👎 Like + Dislike"
TMPL_LDV  = "👍👎👁️ Like + Dislike + Views"
TMPL_LDS  = "👍👎📤 Like + Dislike + Share"
TMPL_VS   = "👁️📤 Views + Share"
TMPL_S    = "📤 Share Only"
TMPL_BACK = "🔙 Back to Panel"

# Auto Adder sub-menu buttons
BTN_PROJ_NEW    = "⚡ Auto Button Project"
BTN_PROJ_ADD_POST = "🔗 Add Button to Post"
BTN_MY_PROJECTS = "📁 My Projects"
BTN_BACK_MAIN   = "🔙 Back"

COLOR_LABELS = {
    "Default": "default",
    "Red":     "red",
    "Blue":    "blue",
    "Green":   "green",
}
COLOR_LABEL_FROM_KEY = {v: k for k, v in COLOR_LABELS.items()}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ib(text: str, *, cb: str = None, url: str = None,
        style: str = None, **kw) -> InlineKeyboardButton:
    """Shorthand InlineKeyboardButton builder with optional native style."""
    api_kwargs = {"style": style} if style else None
    if cb:
        return InlineKeyboardButton(text, callback_data=cb,
                                    api_kwargs=api_kwargs, **kw)
    return InlineKeyboardButton(text, url=url,
                                api_kwargs=api_kwargs, **kw)


def _kb(*rows) -> InlineKeyboardMarkup:
    """Shorthand: pass each row as a list of InlineKeyboardButton."""
    return InlineKeyboardMarkup(list(rows))


def _kb_styled(label: str, style: str) -> KeyboardButton:
    """Reply keyboard button with native color style."""
    return KeyboardButton(label, api_kwargs={"style": style})


def rk(buttons: list[list], resize=True, one_time=False) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(buttons, resize_keyboard=resize,
                               one_time_keyboard=one_time)


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ═══════════════════════════════════════════════════════════════
#   REPLY KEYBOARDS  (bottom navigation)
# ═══════════════════════════════════════════════════════════════

def main_menu_reply_kb() -> ReplyKeyboardMarkup:
    """
    Main menu — Auto Button Adder as prominent full-row button.
      📝 Create Post  → green
      📋 My Posts     → blue
      📡 Channel      → blue
      📊 Stats        → blue
      ⚡ Auto Adder   → green (FULL ROW — prominent headline feature)
      ℹ️ Help         → blue
      ⚙️ Settings     → blue
    """
    return ReplyKeyboardMarkup([
        [
            KeyboardButton(BTN_CREATE,      api_kwargs={"style": "success"}),
            KeyboardButton(BTN_MYPOSTS,     api_kwargs={"style": "primary"}),
        ],
        [
            KeyboardButton(BTN_CHANNEL,     api_kwargs={"style": "primary"}),
            KeyboardButton(BTN_STATS,       api_kwargs={"style": "primary"}),
        ],
        [
            KeyboardButton(BTN_AUTO_ADDER,  api_kwargs={"style": "success"}),
        ],
        [
            KeyboardButton(BTN_HELP,        api_kwargs={"style": "primary"}),
            KeyboardButton(BTN_SETTINGS,    api_kwargs={"style": "primary"}),
        ],
    ], resize_keyboard=True)


def button_panel_reply_kb(existing_types: set, has_buttons: bool = False) -> ReplyKeyboardMarkup:
    """
    Button panel — color scheme:
      Add URL    → blue  (add action)
      Like/Dis   → blue  (add action)
      Views      → blue  (add action)
      Share      → blue  (add action)
      Templates  → blue  (shortcut)
      Remove Btn → red   (destructive)
      Clear      → red   (destructive)
      Preview    → blue  (info)
      DONE       → green (confirm)
      CANCEL     → red   (cancel)
    """
    rows = [
        [KeyboardButton(BTN_ADD_URL, api_kwargs={"style": "primary"})],
    ]

    if 'like' not in existing_types:
        rows.append([KeyboardButton(BTN_ADD_LD, api_kwargs={"style": "primary"})])

    sub = []
    if 'views' not in existing_types:
        sub.append(KeyboardButton(BTN_ADD_VIEWS, api_kwargs={"style": "primary"}))
    if 'share' not in existing_types:
        sub.append(KeyboardButton(BTN_ADD_SHARE, api_kwargs={"style": "primary"}))
    sub.append(KeyboardButton(BTN_ADD_CUSTOM_REACTION, api_kwargs={"style": "primary"}))
    if sub:
        rows.append(sub)
    
    if has_buttons:
        rows.append([
            KeyboardButton(BTN_TEMPLATES,  api_kwargs={"style": "primary"}),
            KeyboardButton(BTN_REMOVE_BTN, api_kwargs={"style": "danger"}),
            KeyboardButton(BTN_CLEAR,      api_kwargs={"style": "danger"}),
        ])
    else:
        rows.append([
            KeyboardButton(BTN_TEMPLATES, api_kwargs={"style": "primary"}),
            KeyboardButton(BTN_CLEAR,     api_kwargs={"style": "danger"}),
        ])

    rows.append([KeyboardButton(BTN_PREVIEW, api_kwargs={"style": "primary"})])
    rows.append([
        KeyboardButton(BTN_DONE,   api_kwargs={"style": "success"}),
        KeyboardButton(BTN_CANCEL, api_kwargs={"style": "danger"}),
    ])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def remove_button_reply_kb(buttons: list) -> ReplyKeyboardMarkup:
    """Keyboard to select a specific button to remove."""
    rows = []
    for btn in buttons:
        # Each btn is a dict with 'text'
        btn_text = btn.get('text', 'Unknown Button')
        rows.append([KeyboardButton(btn_text)])
    
    rows.append([
        KeyboardButton(BTN_BACK_MAIN, api_kwargs={"style": "primary"}),
        KeyboardButton(BTN_CANCEL, api_kwargs={"style": "danger"})
    ])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def color_reply_kb() -> ReplyKeyboardMarkup:
    """Color picker — each button IS that color."""
    return ReplyKeyboardMarkup([
        [
            KeyboardButton("Default"),
            KeyboardButton("Red",   api_kwargs={"style": "danger"}),
            KeyboardButton("Blue",  api_kwargs={"style": "primary"}),
            KeyboardButton("Green", api_kwargs={"style": "success"}),
        ],
        [KeyboardButton(BTN_CANCEL, api_kwargs={"style": "danger"})],
    ], resize_keyboard=True)


def row_reply_kb(max_rows: int = 8) -> ReplyKeyboardMarkup:
    """Row number picker."""
    nums = [str(i) for i in range(1, max_rows + 1)]
    rows = [nums[i:i+4] for i in range(0, len(nums), 4)]
    rows.append([KeyboardButton(BTN_CANCEL, api_kwargs={"style": "danger"})])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def templates_reply_kb() -> ReplyKeyboardMarkup:
    """
    Template picker — all blue (selection), back is neutral.
    """
    return ReplyKeyboardMarkup([
        [KeyboardButton(TMPL_LD,   api_kwargs={"style": "primary"})],
        [KeyboardButton(TMPL_LDV,  api_kwargs={"style": "primary"})],
        [KeyboardButton(TMPL_LDS,  api_kwargs={"style": "primary"})],
        [KeyboardButton(TMPL_VS,   api_kwargs={"style": "primary"})],
        [KeyboardButton(TMPL_S,    api_kwargs={"style": "primary"})],
        [KeyboardButton(TMPL_BACK)],
    ], resize_keyboard=True)


def done_cancel_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[
        KeyboardButton(BTN_DONE,   api_kwargs={"style": "success"}),
        KeyboardButton(BTN_CANCEL, api_kwargs={"style": "danger"}),
    ]], resize_keyboard=True)


def cancel_only_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[
        KeyboardButton(BTN_CANCEL, api_kwargs={"style": "danger"}),
    ]], resize_keyboard=True)


# ═══════════════════════════════════════════════════════════════
#   INLINE KEYBOARDS  (on messages)
# ═══════════════════════════════════════════════════════════════

def post_keyboard(post_id: int, buttons: list,
                  counts: dict = None,
                  for_channel: bool = False,
                  bot_username: str = None) -> InlineKeyboardMarkup | None:
    """
    Build the InlineKeyboardMarkup for the actual post.
    URL buttons use the user-chosen color.
    Reaction buttons get semantic colors:
      👍 Like    → success (green)
      👎 Dislike → danger  (red)
      👁️ Views  → primary (blue)
      📤 Share   → primary (blue)
      ⭐ Custom  → primary (blue)
    """
    if not buttons:
        return None
        
    counts = counts or {}
    likes = counts.get('likes', 0)
    dislikes = counts.get('dislikes', 0)
    views = counts.get('views', 0)

    rows: dict[int, list] = {}
    for btn in buttons:
        rn = btn.get('row_num', 0)
        rows.setdefault(rn, [])
        btype = btn['button_type']
        color_name = btn.get('color', 'default')

        # User-chosen color for URL buttons
        style = None
        if color_name == 'red':
            style = 'danger'
        elif color_name == 'green':
            style = 'success'
        elif color_name == 'blue':
            style = 'primary'

        if btype == 'url':
            ib = _ib(btn['text'].strip(), url=btn['url'], style=style)

        elif btype == 'like':
            ib = _ib(f"👍  {likes}",
                     cb=f"react|like|{post_id}", style="success")

        elif btype == 'dislike':
            ib = _ib(f"👎  {dislikes}",
                     cb=f"react|dislike|{post_id}", style="danger")

        elif btype == 'views':
            ib = _ib(f"👁️  {views}",
                     cb=f"react|views|{post_id}", style="primary")

        elif btype == 'share':
            if for_channel and bot_username:
                ib = _ib("📤 Share",
                         url=f"https://t.me/{bot_username}?startinline={post_id}",
                         style="primary")
            else:
                ib = InlineKeyboardButton(
                    "📤 Share",
                    switch_inline_query=str(post_id),
                    api_kwargs={"style": "primary"}
                )
                
        elif btype == 'custom_reaction':
            reaction_text = btn['text'].strip()
            # Truncate if necessary to avoid callback data too large (max 64 bytes total)
            cb_text = reaction_text[:15]
            count = counts.get(cb_text, 0)
            ib = _ib(f"{reaction_text} {count}", cb=f"react|{cb_text}|{post_id}", style="primary")
            
        else:
            continue

        rows[rn].append(ib)

    keyboard = [rows[rn] for rn in sorted(rows.keys()) if rows[rn]]
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def post_list_inline_kb(posts: list, page: int = 0,
                         page_size: int = 5) -> InlineKeyboardMarkup:
    """
    My Posts list:
      Post rows  → blue  (navigation)
      Prev/Next  → blue  (navigation)
      New Post   → green (create)
    """
    start = page * page_size
    page_posts = posts[start: start + page_size]
    total_pages = max(1, (len(posts) + page_size - 1) // page_size)

    rows = []
    for p in page_posts:
        label = f"#{p['id']}  {p['content_type'].upper()}  👍{p.get('likes',0)} 👎{p.get('dislikes',0)}"
        rows.append([_ib(label, cb=f"postmenu|{p['id']}", style="primary")])

    nav = []
    if page > 0:
        nav.append(_ib("◀️ Prev", cb=f"posts_page|{page-1}", style="primary"))
    if page < total_pages - 1:
        nav.append(_ib("Next ▶️", cb=f"posts_page|{page+1}", style="primary"))
    if nav:
        rows.append(nav)

    rows.append([_ib("📝 New Post", cb="inline_create", style="success")])
    return InlineKeyboardMarkup(rows)


def post_actions_inline_kb(post_id: int) -> InlineKeyboardMarkup:
    """
    Post actions:
      Send to Channel → blue  (action)
      Edit Buttons    → blue  (action)
      Stats           → blue  (info)
      Delete          → red   (destructive)
      Back            → blue  (navigation)
    """
    return _kb(
        [
            _ib("📡 Send to Channel", cb=f"sendch|{post_id}",    style="primary"),
            _ib("✏️ Edit Buttons",    cb=f"edit_btns|{post_id}", style="primary"),
        ],
        [
            _ib("📊 Stats",           cb=f"poststats|{post_id}", style="primary"),
            _ib("🗑️ Delete",          cb=f"delpost|{post_id}",   style="danger"),
        ],
        [
            _ib("🔙 My Posts",        cb="inline_myposts",        style="primary"),
        ],
    )


def confirm_delete_inline_kb(post_id: int) -> InlineKeyboardMarkup:
    """
    Delete confirmation:
      Yes Delete → red   (destructive confirm)
      No Keep    → green (safe choice)
    """
    return _kb([
        _ib("🗑️ Yes, Delete", cb=f"confirmdelete|{post_id}", style="danger"),
        _ib("✅ No, Keep",     cb=f"postmenu|{post_id}",      style="success"),
    ])


def post_saved_inline_kb(post_id: int) -> InlineKeyboardMarkup:
    """
    After saving a post:
      Send to Channel → blue  (primary action)
      My Posts        → blue  (navigation)
    """
    return _kb(
        [_ib("📡 Send to Channel", cb=f"sendch|{post_id}", style="primary")],
        [_ib("📋 My Posts",        cb="inline_myposts",     style="primary")],
    )


def channel_list_inline_kb(channels: list,
                             delete_mode: bool = False) -> InlineKeyboardMarkup:
    """
    Channel manager:
      Channel rows      → blue (navigation / select)   — shows channel NAME
      Delete channel    → red  (destructive)
      Add Channel       → green (create)
      Done Deleting     → green (confirm)
      Remove            → red   (destructive)
      Cancel            → red   (cancel)
    """
    kb = []
    for ch in channels:
        ch_id  = ch['channel_username_or_id']
        # Prefer saved title, fallback to raw id/username
        ch_name = ch.get('channel_title') or ch_id
        if delete_mode:
            kb.append([_ib(f"🗑️ {ch_name}", cb=f"delchan|{ch['id']}", style="danger")])
        else:
            kb.append([_ib(f"📡 {ch_name}", cb=f"pickchan|{ch['id']}", style="primary")])

    actions = []
    if len(channels) < 10 and not delete_mode:
        actions.append(_ib("➕ Add Channel", cb="addchan", style="success"))
    if channels:
        if delete_mode:
            actions.append(_ib("✅ Done", cb="donechan", style="success"))
        else:
            actions.append(_ib("🗑️ Remove Channel", cb="rmchan", style="danger"))

    if actions:
        kb.append(actions)

    kb.append([_ib("❌ Cancel", cb="cancel", style="danger")])
    return InlineKeyboardMarkup(kb)


def help_main_inline_kb() -> InlineKeyboardMarkup:
    """
    Help Center topics:
      Basics       → blue  (info)
      Channels     → green (feature)
      Buttons      → blue  (feature)
      Inline Share → green (feature)
    """
    return _kb(
        [
            _ib("📝 Basics",           cb="help|basics",   style="primary"),
            _ib("📡 Channels",         cb="help|channels", style="success"),
        ],
        [_ib("🔘 Buttons & Reactions", cb="help|buttons",  style="primary")],
        [_ib("🔗 Inline Sharing",      cb="help|sharing",  style="success")],
    )


def help_topic_inline_kb() -> InlineKeyboardMarkup:
    """Back to Help topics — blue (navigation)."""
    return _kb([_ib("🔙 Back to Topics", cb="help|main", style="primary")])


def welcome_inline_kb(channel_url: str, website_url: str,
                       bot_username: str) -> InlineKeyboardMarkup:
    """
    Welcome card buttons:
      Join Channel  → blue  (primary CTA)
      Visit Website → green (external)
      Help Center   → blue  (info)
      Launch Bot    → green (confirm / start)
    """
    return _kb(
        [_ib("📢 Join Univora Channel", url=channel_url,      style="primary")],
        [
            _ib("🌐 Visit Website", url=website_url,          style="success"),
            _ib("ℹ️ Help Center",   cb="welcome_help",        style="primary"),
        ],
        [_ib("🚀 Launch Bot",           cb="welcome_launch",  style="success")],
    )


def force_join_inline_kb(channel_url: str) -> InlineKeyboardMarkup:
    """
    Force-join gate:
      Join  → blue  (primary CTA)
      Check → green (positive confirm)
    """
    return _kb(
        [_ib("📢 Join @Univora88",        url=channel_url,  style="primary")],
        [_ib("✅ I Joined — Check Again", cb="check_join",  style="success")],
    )


# ═══════════════════════════════════════════════════════════════
#   AUTO BUTTON ADDER  keyboards
# ═══════════════════════════════════════════════════════════════

def auto_adder_reply_kb() -> ReplyKeyboardMarkup:
    """
    Auto Button Adder home menu:
      ⚡ Auto Button Project  → green (create project)
      🔗 Add Button to Post   → blue  (single post)
      📁 My Projects          → blue  (manage)
      🔙 Back                 → default
    """
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_PROJ_NEW,      api_kwargs={"style": "success"})],
        [KeyboardButton(BTN_PROJ_ADD_POST, api_kwargs={"style": "primary"})],
        [
            KeyboardButton(BTN_MY_PROJECTS, api_kwargs={"style": "primary"}),
            KeyboardButton(BTN_BACK_MAIN),
        ],
    ], resize_keyboard=True)


def project_panel_reply_kb(existing_types: set) -> ReplyKeyboardMarkup:
    """
    Button panel for project/add-to-post configuration.
    Same as button_panel_reply_kb but no Share (not meaningful for auto-adder).
    """
    rows = [
        [KeyboardButton(BTN_ADD_URL, api_kwargs={"style": "primary"})],
    ]
    if 'like' not in existing_types:
        rows.append([KeyboardButton(BTN_ADD_LD, api_kwargs={"style": "primary"})])
    sub = []
    if 'views' not in existing_types:
        sub.append(KeyboardButton(BTN_ADD_VIEWS, api_kwargs={"style": "primary"}))
    if 'share' not in existing_types:
        sub.append(KeyboardButton(BTN_ADD_SHARE, api_kwargs={"style": "primary"}))
    if sub:
        rows.append(sub)
    rows.append([
        KeyboardButton(BTN_TEMPLATES, api_kwargs={"style": "primary"}),
        KeyboardButton(BTN_CLEAR,     api_kwargs={"style": "danger"}),
    ])
    rows.append([KeyboardButton(BTN_PREVIEW, api_kwargs={"style": "primary"})])
    rows.append([
        KeyboardButton(BTN_DONE,   api_kwargs={"style": "success"}),
        KeyboardButton(BTN_CANCEL, api_kwargs={"style": "danger"}),
    ])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def project_post_keyboard(channel_id: str, message_id: int,
                           buttons: list,
                           counts: dict = None,
                           bot_username: str = None) -> InlineKeyboardMarkup | None:
    """
    Build InlineKeyboardMarkup for auto-added channel post buttons.
    Uses chreact|type|channel_id|message_id callback pattern.
    Reaction buttons are colored semantically (green=like, red=dislike, blue=views/share).
    URL buttons use user-chosen color.
    """
    if not buttons:
        return None

    counts = counts or {}
    likes = counts.get('likes', 0)
    dislikes = counts.get('dislikes', 0)
    views = counts.get('views', 0)

    # Build a safe channel_id key (strip -100 prefix for compactness in callback)
    # Keep full ID to avoid ambiguity
    cid = channel_id  # e.g. "-1001234567890"
    mid = message_id

    rows: dict[int, list] = {}
    for btn in buttons:
        rn = btn.get('row_num', 0)
        rows.setdefault(rn, [])
        btype = btn['button_type']
        color_name = btn.get('color', 'default')

        style = None
        if color_name == 'red':    style = 'danger'
        elif color_name == 'green': style = 'success'
        elif color_name == 'blue':  style = 'primary'

        if btype == 'url':
            ib = _ib(btn['text'].strip(), url=btn['url'], style=style)
        elif btype == 'like':
            ib = _ib(f"👍  {likes}", cb=f"chreact|like|{cid}|{mid}", style="success")
        elif btype == 'dislike':
            ib = _ib(f"👎  {dislikes}", cb=f"chreact|dislike|{cid}|{mid}", style="danger")
        elif btype == 'views':
            ib = _ib(f"👁️  {views}", cb=f"chreact|views|{cid}|{mid}", style="primary")
        elif btype == 'share':
            if bot_username:
                ib = _ib("📤 Share",
                         url=f"https://t.me/{bot_username}?startinline=ch_{cid}_{mid}",
                         style="primary")
            else:
                ib = InlineKeyboardButton("📤 Share",
                                          switch_inline_query=f"ch_{cid}_{mid}",
                                          api_kwargs={"style": "primary"})
        elif btype == 'custom_reaction':
            reaction_text = btn['text'].strip()
            cb_text = reaction_text[:15]
            count = counts.get(cb_text, 0)
            ib = _ib(f"{reaction_text} {count}", cb=f"chreact|{cb_text}|{cid}|{mid}", style="primary")
        else:
            continue
        rows[rn].append(ib)

    keyboard = [rows[rn] for rn in sorted(rows.keys()) if rows[rn]]
    return InlineKeyboardMarkup(keyboard) if keyboard else None


def my_projects_inline_kb(projects: list) -> InlineKeyboardMarkup:
    """
    My Projects list with toggle (on/off) and delete per project.
      Project name → blue (info)
      🟢 Active / ⏸️ Paused → toggle
      🗑️ Delete → red
    """
    rows = []
    for p in projects:
        title = p.get('channel_title') or p['channel_id']
        status = "🟢" if p['is_active'] else "⏸️"
        pid = p['id']
        rows.append([
            _ib(f"{status} {title}", cb=f"proj_toggle|{pid}", style="primary"),
            _ib("🗑️", cb=f"proj_del|{pid}", style="danger"),
        ])
    rows.append([_ib("🔙 Back", cb="proj_back", style="primary")])
    return InlineKeyboardMarkup(rows)


def settings_inline_kb(website_url: str, channel_url: str) -> InlineKeyboardMarkup:
    """Inline keyboard for the Settings command card."""
    kb = [
        [
            _ib("📢 Official Channel", url=channel_url, style="primary"),
            _ib("🌐 Website", url=website_url, style="primary")
        ],
        [
            _ib("🔄 Refresh Data", cb="settings_refresh", style="success")
        ]
    ]
    return InlineKeyboardMarkup(kb)

def user_stats_inline_kb() -> InlineKeyboardMarkup:
    """Inline keyboard for the User Stats command card."""
    kb = [
        [
            _ib("📂 My Posts", cb="inline_myposts", style="primary"),
            _ib("🔄 Refresh", cb="user_stats_refresh", style="success")
        ]
    ]
    return InlineKeyboardMarkup(kb)
