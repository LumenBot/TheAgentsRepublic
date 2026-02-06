@echo off
REM ============================================
REM The Constituent — Windows Quick Start
REM ============================================
REM Use this if Docker is not available.
REM Requires Python 3.11+ installed.
REM ============================================

echo.
echo ╔══════════════════════════════════════════════╗
echo ║     THE CONSTITUENT — Setup ^& Start          ║
echo ╚══════════════════════════════════════════════╝
echo.

REM Check .env
if not exist .env (
    echo ⚠️  No .env file found!
    echo    Copy .env.example to .env and fill in your API keys.
    echo    copy .env.example .env
    pause
    exit /b 1
)
echo ✅ .env file found

REM Create virtual environment if not exists
if not exist .venv (
    echo.
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat
echo ✅ Virtual environment active

REM Install dependencies
echo.
echo 📦 Installing dependencies...
pip install -r requirements.txt --quiet

REM Create directories
if not exist data mkdir data
if not exist memory\knowledge mkdir memory\knowledge
if not exist agent\data mkdir agent\data
if not exist agent\improvements mkdir agent\improvements

REM Start the agent
echo.
echo 🚀 Starting The Constituent...
echo.
python -m agent.main_v2

pause
