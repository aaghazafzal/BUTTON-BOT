<div align="center">

<img src="https://socialify.git.ci/aaghazafzal/BUTTON-BOT/image?description=1&font=Inter&name=1&owner=1&pattern=Circuit%20Board&theme=Dark" alt="Univora Button Bot" width="600" />

# ⚡ Univora Button Bot V2.0

**An enterprise-grade, high-performance Telegram bot for creating rich interactive posts with inline buttons, live analytics, and automated channel broadcasting.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/PTB-v21.6-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://python-telegram-bot.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor_Async-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![Platform](https://img.shields.io/badge/Platform-Univora-6C3BC9?style=for-the-badge)](https://univora.website)

*Built by [Rolex Sir](https://t.me/rolexsir_8) • Powered by [Univora](https://univora.website)*

</div>

---

## 🔥 Why Univora Button Bot?

Unlike standard button bots, Univora Button Bot V2 is built on a **fully asynchronous, non-blocking architecture** utilizing `motor` for MongoDB and `python-telegram-bot` v21. It boasts a premium native Telegram UI with customized dynamic cards, real-time engagement analytics, and advanced automated workflow tools for channel admins.

---

## ✨ Premium Features

| Core Feature | Description |
|---|---|
| 📝 **Rich Post Creator** | Supports Text, Photos, Videos, GIFs, Documents, and Stickers with deep formatting support. |
| 💠 **Auto Button Adder** | *[NEW]* Automatically attach predefined inline buttons to any new post made in your channels. |
| 📈 **Live Analytics** | Real-time tracking of 👁️ Views, 👍 Likes, and 👎 Dislikes with dynamic visual progress bars. |
| 📤 **Deep Linking & Sharing** | Seamless one-tap inline share buttons (`@botname`) to broadcast posts into any chat or group. |
| 🎨 **Native UI Styling** | Utilizes Telegram's native button colors (Blue, Green, Red) for a premium, clean aesthetic. |
| 🔒 **Force Join Gateway** | Built-in subscription enforcement to mandate channel membership before bot usage. |
| ⚡ **Quick Templates** | Instantly inject predefined button layouts (e.g., Like+Dislike+Share) in a single click. |
| 🗄️ **MongoDB Powered** | Highly scalable cloud database architecture using Motor for high-speed asynchronous queries. |

---

## 🚀 Quick Start & Deployment

### 1. Clone the Repository
```bash
git clone https://github.com/aaghazafzal/BUTTON-BOT.git
cd BUTTON-BOT
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
You can configure the bot via `.env` file or environment variables (perfect for Render/Heroku).

```ini
BOT_TOKEN="your_bot_token_here"
MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"
FORCE_JOIN_CHANNEL="@Univora88"
FORCE_JOIN_CHANNEL_URL="https://t.me/Univora88"
WEBSITE_URL="https://univora.website"
START_LOGO_PATH="startmssglogo.jpg"
```

### 4. Run the Application
```bash
python bot.py
```

---

## ☁️ Zero-Downtime Render Deployment

This bot is architected to run flawlessly on **[Render's Free Tier](https://render.com)** without sleeping, utilizing a built-in background Flask server.

1. Create a **Web Service** on Render and connect this GitHub repository.
2. Inject your Environment Variables (see step 3 above).
3. Set `RENDER=true` in your variables to activate the built-in Keep-Alive ping mechanism.
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `python bot.py`

*Render will generate a `RENDER_EXTERNAL_URL`. The bot captures this internally and pings itself every 14 minutes to bypass sleep modes.*

---

## 🏗️ Technical Architecture

```text
BUTTON-BOT/
├── bot.py              # Application Entrypoint & Handlers
├── config.py           # Environment Loaders & Constants
├── database.py         # Asynchronous MongoDB Wrapper (Motor)
├── keep_alive.py       # Render Keep-Alive Flask Server
├── requirements.txt    # Dependency Manifest
└── utils/
    ├── keyboards.py    # Premium Inline & Reply Keyboard Generators
    └── helpers.py      # Formatters, URL Parsers, and Message Extractors
```

### Core Tech Stack
* **Language:** Python 3.11+
* **Framework:** `python-telegram-bot` v21.6 (Asyncio)
* **Database:** MongoDB (`motor`, `pymongo`)
* **Web Server:** `flask` (Keep-alive daemon)

---

## 💬 Command Reference

| Command | Access | Description |
|---|---|---|
| `/start` | 🌐 Public | Initialize bot, trigger Force-Join check, open main menu. |
| `/about` | 🌐 Public | View bot version, developer details, and tech stack. |
| `/help` | 🌐 Public | Interactive inline guide and visual documentation. |
| `/stats` | 👑 Admin | Global analytics dashboard (Total Users, Posts, CTR). |

*(Standard users access their personal analytics directly via the "📈 Stats" button in the Reply Menu).*

---

<div align="center">

**Developed with precision by [Rolex Sir](https://t.me/rolexsir_8)**  
*Part of the [Univora Ecosystem](https://univora.website)*

</div>
