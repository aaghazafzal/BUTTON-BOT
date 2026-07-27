"""
keep_alive.py — Flask web server + self-ping for Render free tier.

Render free services sleep after ~15 minutes of no incoming HTTP traffic.
This module:
  1. Starts a tiny Flask HTTP server on the PORT Render assigns.
  2. Pings its own /health endpoint every 5 minutes so Render NEVER
     marks the service as idle.
     (14-min interval was too close to the 15-min limit — fixed to 5 min)

Usage:  import keep_alive; keep_alive.start()   ← call before bot polling
"""

import os
import threading
import time
import logging

import requests
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)

# ─── Flask routes ─────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return "✅ Univora Button Bot is alive and running!", 200


@app.route("/health")
def health():
    return jsonify({"status": "ok", "bot": "Univora Button Bot", "service": "running"}), 200


@app.route("/ping")
def ping():
    return jsonify({"pong": True}), 200


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)


def _self_ping():
    """
    Ping our own /health URL every PING_INTERVAL seconds.
    Render free tier sleeps after ~15 min of no traffic.
    We ping every 5 minutes — well within the safety margin.
    """
    PING_INTERVAL = 5 * 60   # 5 minutes in seconds

    url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not url:
        logger.info("keep_alive: RENDER_EXTERNAL_URL not set — self-ping disabled.")
        return

    ping_url = url + "/health"
    logger.info(f"keep_alive: self-ping active → {ping_url}  (every {PING_INTERVAL//60} min)")

    # ── First ping: send immediately after a short warmup delay ──
    time.sleep(30)   # give Flask 30s to fully start before first ping
    _do_ping(ping_url)

    # ── Subsequent pings: every 5 minutes ──
    while True:
        time.sleep(PING_INTERVAL)
        _do_ping(ping_url)


def _do_ping(url: str):
    try:
        r = requests.get(url, timeout=15)
        logger.info(f"keep_alive: ping → {url}  [{r.status_code}]")
    except Exception as e:
        logger.warning(f"keep_alive: ping FAILED — {e}")


# ─── Public entry point ───────────────────────────────────────────────────────

def start():
    """Start Flask server + self-ping in background daemon threads."""
    flask_thread = threading.Thread(
        target=_run_flask, daemon=True, name="flask-server"
    )
    flask_thread.start()

    ping_thread = threading.Thread(
        target=_self_ping, daemon=True, name="self-ping"
    )
    ping_thread.start()

    logger.info("keep_alive: Flask server + self-ping started.")
