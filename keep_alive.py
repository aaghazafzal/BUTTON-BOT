"""
keep_alive.py — Flask web server + self-ping for Render free tier.

Render free services sleep after 15 minutes of inactivity.
This module:
  1. Starts a tiny Flask HTTP server on the PORT Render assigns.
  2. Every 14 minutes pings its own URL so Render never marks it idle.

Usage: import keep_alive; keep_alive.start()  — call before bot.run_polling()
"""

import os
import threading
import time
import logging

import requests
from flask import Flask

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def home():
    return "✅ Univora Button Bot is alive!", 200


@app.route("/health")
def health():
    return {"status": "ok", "bot": "Univora Button Bot"}, 200


def _run_flask():
    port = int(os.environ.get("PORT", 8080))
    # Use threaded=True so Flask handles concurrent requests
    app.run(host="0.0.0.0", port=port, threaded=True)


def _self_ping():
    """Ping our own URL every 14 min to prevent Render free-tier sleep."""
    # RENDER_EXTERNAL_URL is set automatically by Render
    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not url:
        logger.info("keep_alive: RENDER_EXTERNAL_URL not set — skipping self-ping.")
        return

    ping_url = url.rstrip("/") + "/health"
    logger.info(f"keep_alive: self-ping enabled → {ping_url}")

    while True:
        time.sleep(14 * 60)   # sleep 14 minutes
        try:
            r = requests.get(ping_url, timeout=10)
            logger.info(f"keep_alive: ping {r.status_code}")
        except Exception as e:
            logger.warning(f"keep_alive: ping failed — {e}")


def start():
    """Start Flask + self-ping in background daemon threads."""
    flask_thread = threading.Thread(target=_run_flask, daemon=True, name="flask-server")
    flask_thread.start()

    ping_thread = threading.Thread(target=_self_ping, daemon=True, name="self-ping")
    ping_thread.start()

    logger.info("keep_alive: Flask server + self-ping started.")
