"""
keep_alive.py — Flask web server + self-ping for Render free tier.

Render free services sleep after ~15 minutes of no incoming HTTP traffic.
This module:
  1. Starts a tiny Flask HTTP server on the PORT Render assigns.
  2. Pings its own /health endpoint every 5 minutes so Render NEVER
     marks the service as idle.

Endpoints:
  GET /          — simple alive text
  GET /health    — basic health JSON  (used by self-ping)
  GET /ping      — pong response
  GET /status    — full bot status JSON  (for status page / monitoring)

Usage:  import keep_alive; keep_alive.start()   ← call before bot polling
"""

import os
import time
import threading
import logging
import platform
from datetime import timezone, datetime

import requests
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

app   = Flask(__name__)

# ── Bot meta ──────────────────────────────────────────────────────────────────
BOT_NAME    = "@UNIVORA_BUTTONBOT"
BOT_VERSION = "2.0.0"
FEATURES    = [
    "create-button",
    "direct-share",
    "automatic",
    "free",
    "inline-mode",
    "auto-button-adder",
    "live-reactions",
    "admin-stats",
]

# Set once when start() is called
_start_time: float = 0.0      # unix timestamp


def _uptime_seconds() -> int:
    return int(time.time() - _start_time) if _start_time else 0


def _fmt_uptime(secs: int) -> str:
    d, rem  = divmod(secs, 86400)
    h, rem  = divmod(rem,  3600)
    m, s    = divmod(rem,  60)
    parts   = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


# ─── Flask routes ─────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return "✅ Univora Button Bot is alive and running!", 200


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot":     BOT_NAME,
        "service": "running",
    }), 200


@app.route("/ping")
def ping():
    return jsonify({"pong": True}), 200


@app.route("/status")
def status():
    """
    Public status endpoint — safe for embedding in a status page.
    No sensitive info is exposed (no token, no IDs, no DB creds).
    """
    uptime_sec = _uptime_seconds()
    now_utc    = datetime.now(timezone.utc)

    return jsonify({
        # ── Core status ───────────────────────────────
        "status":            "online",
        "alive":             True,

        # ── Uptime ───────────────────────────────────
        "uptime_seconds":    uptime_sec,
        "uptime_formatted":  _fmt_uptime(uptime_sec),
        "start_time":        round(_start_time, 2),
        "start_time_utc":    datetime.fromtimestamp(
                                 _start_time, tz=timezone.utc
                             ).strftime("%Y-%m-%dT%H:%M:%SZ") if _start_time else None,

        # ── Current time ─────────────────────────────
        "server_time_utc":   now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timestamp":         round(time.time(), 2),

        # ── Bot info ─────────────────────────────────
        "bot_name":          BOT_NAME,
        "version":           BOT_VERSION,
        "platform":          "Render (Free)",
        "language":          "Python " + platform.python_version(),

        # ── Features ─────────────────────────────────
        "features":          FEATURES,

        # ── Website ──────────────────────────────────
        "website":           "https://univora.website",
    }), 200


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
    global _start_time
    _start_time = time.time()

    flask_thread = threading.Thread(
        target=_run_flask, daemon=True, name="flask-server"
    )
    flask_thread.start()

    ping_thread = threading.Thread(
        target=_self_ping, daemon=True, name="self-ping"
    )
    ping_thread.start()

    logger.info("keep_alive: Flask server + self-ping started.")
