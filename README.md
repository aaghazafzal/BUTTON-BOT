<div align="center">

# ⚡ Univora Button Bot

**A powerful Telegram bot for creating posts with interactive inline buttons — reactions, counters, links, and more.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-21.6-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://python-telegram-bot.org)
[![Platform](https://img.shields.io/badge/Univora-Platform-6C3BC9?style=for-the-badge)](https://univora.site)
[![Channel](https://img.shields.io/badge/Telegram-@Univora88-26A5E4?style=for-the-badge&logo=telegram)](https://t.me/Univora88)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📝 **Post Creator** | Create rich posts — text, photo, video, GIF, document, sticker, and more |
| 👍👎 **Like / Dislike** | Add live reaction counters — each user can only vote once |
| 👁️ **View Counter** | Track how many times a post is seen |
| 📤 **Share Button** | One-tap share button that lets users forward your post anywhere |
| 🔗 **URL Buttons** | Attach custom-colored link buttons to any post |
| 📡 **Channel Manager** | Save your channels and broadcast posts directly from the bot |
| 🔗 **Inline Sharing** | Share posts to any chat using `@botname` inline mode |
| ⚡ **Quick Templates** | Apply pre-built button layouts in one tap |
| 📊 **Analytics** | Track likes, dislikes, views, and your top-performing post |
| 🔒 **Force Join** | Require users to join your channel before using the bot |
| 🎨 **Colored Buttons** | Native Telegram button colors — blue (primary), green (success), red (danger) |

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/aaghaz370/BUTTON_BOT.git
cd BUTTON_BOT
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure the bot
Open `config.py` and set:
```python
BOT_TOKEN = "your_bot_token_here"          # From @BotFather
FORCE_JOIN_CHANNEL   = "@YourChannel"      # Channel users must join
FORCE_JOIN_CHANNEL_URL = "https://t.me/YourChannel"
WEBSITE_URL          = "https://yoursite.com"
START_LOGO_PATH      = r"path/to/logo.jpg"  # Welcome message image
```

> 💡 **Tip:** You can also use a `.env` file and load it with `python-dotenv`.

### 4. Run the bot
```bash
python bot.py
```

---

## 🗂️ Project Structure

```
BUTTON_BOT/
├── bot.py              # Main bot logic — all handlers & conversation flows
├── config.py           # Bot token, limits, messages & branding config
├── database.py         # Async SQLite database layer (aiosqlite)
├── keep_alive.py       # Flask server + self-ping for Render free tier
├── requirements.txt    # Python dependencies
├── utils/
│   ├── keyboards.py    # All ReplyKeyboard & InlineKeyboard builders
│   └── helpers.py      # send_post, extract_content, fmt_num, etc.
└── .gitignore
```

---

## ☁️ Deploy on Render (Free Tier)

This bot is designed to run on **[Render](https://render.com)** with zero sleep on the free tier.

### Steps

1. **Fork / push** this repo to your GitHub account.

2. **Create a new Web Service** on Render → connect your GitHub repo.

3. **Set the following in Render's Environment Variables:**

   | Variable | Value |
   |---|---|
   | `BOT_TOKEN` | Your Telegram bot token |
   | `FORCE_JOIN_CHANNEL` | e.g. `@Univora88` |
   | `FORCE_JOIN_CHANNEL_URL` | `https://t.me/Univora88` |
   | `WEBSITE_URL` | `https://univora.site` |
   | `START_LOGO_PATH` | `/opt/render/project/src/startmssglogo.jpg` |
   | `RENDER` | `true` ← **Important! Enables keep-alive** |

4. **Build Command:**
   ```
   pip install -r requirements.txt
   ```

5. **Start Command:**
   ```
   python bot.py
   ```

6. Render will automatically set `RENDER_EXTERNAL_URL` — the bot uses this to self-ping every **14 minutes** to stay awake. ✅

---

## ⚙️ How Keep-Alive Works

```
┌──────────────────────────────────────────────┐
│  Render Free Tier                            │
│                                              │
│  bot.py ──starts──► keep_alive.start()      │
│                          │                   │
│                ┌─────────┴────────┐          │
│                ▼                  ▼          │
│         Flask Server        Self-Ping        │
│         (port 8080)        (every 14 min)   │
│              │                  │            │
│         GET /health       GET /health        │
│         → {"status":"ok"} ← Render thinks   │
│                              you're active   │
└──────────────────────────────────────────────┘
```

The `keep_alive.py` module:
- Starts a **Flask HTTP server** on Render's assigned `PORT`
- Every **14 minutes** sends an HTTP ping to its own `/health` endpoint
- Render considers the service active → **no sleep** 🎉

---

## 🛠️ Bot Commands

| Command | Description |
|---|---|
| `/start` | Launch the bot & show welcome card |
| `/help` | Open the interactive Help Center |
| `/newpost` | Shortcut to create a new post |
| `/mypost` | View & manage all your saved posts |
| `/stats` | View your analytics dashboard |
| `/sendto <post_id> @channel` | Send a post to a channel directly |
| `/cancel` | Cancel current action & return to main menu |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `python-telegram-bot` | 21.6 | Telegram Bot API wrapper |
| `aiosqlite` | 0.20.0 | Async SQLite database |
| `flask` | 3.0.3 | Keep-alive web server |
| `requests` | 2.32.3 | Self-ping HTTP client |
| `python-dotenv` | 1.0.1 | Load `.env` config |

---

## 🌐 Links

- **Platform:** [univora.site](https://univora.site)
- **Channel:** [t.me/Univora88](https://t.me/Univora88)
- **Repository:** [github.com/aaghaz370/BUTTON_BOT](https://github.com/aaghaz370/BUTTON_BOT)

---

<div align="center">

Made with ❤️ by **Univora Platform**

</div>
