# 🚀 BUTTON BOT: Ultimate Deployment Guide

Welcome to your personal deployment guide! This file contains all the instructions and secret keys you need to deploy or restore your bot at any time. **Keep this safe!**

If your VPS goes down, or Render deletes your app, you can use this guide to easily set everything up again in 5 minutes.

---

## 🔑 Your Environment Variables (.env)

These are the exact values you need to put into Render (or your `.env` file if running locally). You can just copy-paste these!

```ini
# 1. TELEGRAM BOT TOKEN (From @BotFather)
BOT_TOKEN=8813750611:AAET-pru66SIHH9oYzRGPMTHvhdfCbUCei0

# 2. MONGODB DATABASE URL (Where your data is saved safely)
MONGO_URI=mongodb+srv://buttonbot:aaghaz9431@buttonbot.x2bdflb.mongodb.net/?appName=buttonbot

# 3. ADMIN ACCESS (Your Telegram ID)
ADMIN_IDS=7097905601

# 4. RENDER KEEP-ALIVE (Very Important for Render Free Tier)
RENDER=true

# 5. BRANDING & LINKS (Optional but recommended)
FORCE_JOIN_CHANNEL=@Univora88
FORCE_JOIN_CHANNEL_URL=https://t.me/Univora88
WEBSITE_URL=https://univora.website
```

---

## ☁️ How to Deploy on Render (Step-by-Step)

If you ever need to create a new Render service, follow these exact steps:

1. **Login to Render:** Go to [render.com](https://render.com) and log in with your GitHub account.
2. **New Web Service:** Click on **New +** > **Web Service**.
3. **Connect GitHub:** Select `aaghazafzal/BUTTON-BOT` from the list.
4. **Setup Details:**
   - **Name:** `button-bot` (or anything you like)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. **Add Environment Variables:** Scroll down to the "Environment Variables" section, click "Add Environment Variable", and copy-paste all 5 variables from the `🔑 Your Environment Variables` section above.
6. **Deploy:** Click **Create Web Service**. 

🎉 That's it! Render will automatically install the requirements and run the bot. Kyunki `RENDER=true` set hai, bot har 14 minute mein khud ko ping karega aur kabhi sleep (off) nahi hoga.

---

## 💻 How to Run Locally (On your Laptop)

Agar kabhi laptop pe run karke test karna ho:

1. CMD/Terminal open karo project folder mein.
2. Niche di gayi command run karo required packages install karne ke liye:
   ```bash
   pip install -r requirements.txt
   ```
3. Ek naya file banao jiska naam sirf `.env` ho (aur kuch nahi, sirf `.env`).
4. Upar section mein di gayi saari ENV variables (jaise `BOT_TOKEN`, `MONGO_URI`, etc.) uss `.env` file ke andar paste kar do.
5. Bot ko start karo:
   ```bash
   python bot.py
   ```

---

## 🛠️ GitHub Rescue Commands

Agar kabhi GitHub pe kuch issue ho, ya error aaye, toh terminal mein folder ke andar yeh commands use karna:

**Check if connected to correct new repo:**
```bash
git remote -v
```
*(Yahan `aaghazafzal/BUTTON-BOT.git` dikhna chahiye)*

**To push new updates:**
```bash
git add .
git commit -m "update bot"
git push origin main
```

---
*Created specially for Rolex Sir (@rolexsir_8).*
