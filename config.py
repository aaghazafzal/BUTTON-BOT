"""
╔══════════════════════════════════════════╗
║         AUTO BUTTON BOT ⚡ CONFIG        ║
╚══════════════════════════════════════════╝
"""

# ─── Bot Token ───────────────────────────────────────
BOT_TOKEN = "8813750611:AAET-pru66SIHH9oYzRGPMTHvhdfCbUCei0"

# ─── Univora Platform Branding ───────────────────────────
FORCE_JOIN_CHANNEL   = "@Univora88"          # Force join channel username
FORCE_JOIN_CHANNEL_URL = "https://t.me/Univora88"  # Channel invite URL
WEBSITE_URL          = "https://univora.site"  # Univora website
START_LOGO_PATH      = r"C:\ALL FINAL PROJECTS\BOTS\BUTTON BOT\startmssglogo.jpg"

# ─── Database ────────────────────────────────────────
DB_PATH = "button_bot.db"

# MongoDB — baad mein set karna (user se lena hai)
MONGO_URI = None          # e.g. "mongodb+srv://user:pass@cluster.mongodb.net/"
MONGO_DB_NAME = "button_bot"

# ─── Bot Owners / Admins ─────────────────────────────
OWNER_IDS = []            # Yahan apna Telegram user_id daalo [123456789]

# ─── Limits ──────────────────────────────────────────
MAX_POSTS_PER_USER = 100       # Ek user kitne posts rakh sakta hai
MAX_BUTTONS_PER_POST = 20      # Ek post mein max buttons
MAX_BUTTONS_PER_ROW = 3        # Ek row mein max buttons

# ─── Inline Query ─────────────────────────────────────
INLINE_CACHE_TIME = 300        # seconds

# ─── Color Config ────────────────────────────────────
# Telegram Bot API 9.4 natively supports 3 styles: primary, success, danger
COLOR_EMOJIS = {
    "default": "",
    "red":     "",  # Handled natively via style='danger'
    "blue":    "",  # Handled natively via style='primary'
    "green":   "",  # Handled natively via style='success'
}

# Display names for color keyboard
COLORS_DISPLAY = {
    "default": "Default",
    "red":     "Red",
    "blue":    "Blue",
    "green":   "Green",
}

# ─── Messages ─────────────────────────────────────────
BOT_NAME = "UNIVORA BUTTON BOT ⚡"

WELCOME_TEXT = (
    "<b>🚀 Welcome to Univora Button Bot!</b>\n"
    "<i>Powered by</i> <b>Univora Platform</b> 🌐\n\n"
    "Create stunning Telegram posts with <b>powerful interactive buttons</b> — reactions, counters, links, and more!\n\n"
    "<b>✨ What You Can Do:</b>\n"
    "┣ 📝 Create posts with custom URL buttons\n"
    "┣ 👍👎 Live Like / Dislike counter\n"
    "┣ 👁️ View tracker on every post\n"
    "┣ 📤 One-tap Share button\n"
    "┣ 📡 Direct broadcast to your channel\n"
    "┣ ⚡ Quick-apply button templates\n"
    "┗ 📊 Real-time post analytics\n\n"
    "<b>👇 Use the menu below to get started!</b>"
)

FORCE_JOIN_TEXT = (
    "🔒 <b>Access Restricted!</b>\n\n"
    "To use this bot, you must first join our official channel:\n\n"
    "<b>📢 Univora</b> → @Univora88\n\n"
    "After joining, press <b>✅ I Joined</b> to continue."
)

HELP_DICT = {
    "main": (
        "<b>👋 Welcome to the Help Center!</b>\n\n"
        "Please select a topic below to learn more about how to use the bot's features."
    ),
    "basics": (
        "<b>📝 Creating Posts</b>\n\n"
        "1. Click <b>📝 Create Post</b> from the main menu.\n"
        "2. Send your content (Text, Photo, Video, GIF, etc.).\n"
        "3. Use the button panel to attach custom buttons.\n"
        "4. Click <b>✅ Done</b> when you are finished to save your post."
    ),
    "channels": (
        "<b>📡 Channel Manager</b>\n\n"
        "1. Make sure I am an <b>Admin</b> in your channel.\n"
        "2. Click <b>📡 Send to Channel</b> in the main menu.\n"
        "3. Add your channel using its <code>@username</code> or ID.\n"
        "4. Once saved, simply tap your channel and enter a Post ID to broadcast immediately!"
    ),
    "buttons": (
        "<b>🔘 Buttons & Reactions</b>\n\n"
        "• <b>URL Buttons:</b> Add standard links to your posts.\n"
        "• <b>Like/Dislike:</b> Add 👍/👎 counters. Users can only pick one!\n"
        "• <b>View Counter:</b> Adds an 👁️ button to track how many times a post is seen.\n"
        "• <b>Share Button:</b> Adds a deep-link button so users can easily share your post to other chats.\n"
        "• <b>Custom Templates:</b> Save a specific button layout and apply it instantly to new posts!"
    ),
    "sharing": (
        "<b>🔗 Inline Sharing</b>\n\n"
        "You can send your saved posts to ANY chat or group without adding me as an admin!\n\n"
        "1. Go to the target chat.\n"
        "2. Type: <code>@{username}</code> followed by a space.\n"
        "3. Select your post from the popup list to send it instantly."
    )
}
