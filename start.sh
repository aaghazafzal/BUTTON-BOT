#!/usr/bin/env bash
# Entry point for Render to run both Bot and WebApp

echo "🚀 Starting Univora Bot + WebApp Monorepo..."

# Disable Flask keep-alive so Next.js can bind to the public PORT
export DISABLE_FLASK=1

# 1. Start the Python bot in the background with auto-restart for zero-downtime deployment conflicts
echo "🐍 Starting Python Bot..."
(
  while true; do
    python3 bot.py
    echo "Bot crashed or stopped (possibly due to Render zero-downtime Conflict). Restarting in 5s..."
    sleep 5
  done
) &

# 2. Start Next.js WebApp
echo "🌐 Starting Next.js WebApp..."
cd webapp
npm run start
