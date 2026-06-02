@echo off
echo ⚡ AUTO BUTTON BOT — Starting...
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist ".deps_installed" (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    echo. > .deps_installed
)

echo 🚀 Launching bot...
python bot.py
pause
