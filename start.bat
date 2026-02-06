@echo off
REM ============================================
REM The Constituent — Windows Quick Start
REM ============================================
REM Uses WinPython portable (no installation needed)
REM ============================================

echo.
echo =============================================
echo     THE CONSTITUENT - Setup and Start
echo =============================================
echo.

REM --- CONFIGURATION ---
REM Set the path to your WinPython folder below.
REM It should be the folder containing "scripts\env.bat"
REM Example: C:\Users\Blaise\Desktop\WPy64-31330

REM Auto-detect: look for WinPython next to this script or on Desktop
set "WINPYTHON_DIR="

REM Check common locations
for /d %%D in ("%~dp0WPy64-*") do set "WINPYTHON_DIR=%%D"
for /d %%D in ("%~dp0..\WPy64-*") do set "WINPYTHON_DIR=%%D"
for /d %%D in ("%~dp0..\winpython-*\WPy64-*") do set "WINPYTHON_DIR=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\WPy64-*") do set "WINPYTHON_DIR=%%D"
for /d %%D in ("%USERPROFILE%\Desktop\winpython-*\WPy64-*") do set "WINPYTHON_DIR=%%D"

REM If not found, ask the user
if "%WINPYTHON_DIR%"=="" (
    echo WinPython not found automatically.
    echo.
    echo Please edit this file (start.bat) and set WINPYTHON_DIR manually,
    echo or place the WPy64-XXXXX folder next to this script.
    echo.
    set /p WINPYTHON_DIR="Enter full path to WPy64-XXXXX folder: "
)

if not exist "%WINPYTHON_DIR%\scripts\env.bat" (
    echo.
    echo ERROR: Cannot find %WINPYTHON_DIR%\scripts\env.bat
    echo.
    echo Make sure WINPYTHON_DIR points to the WPy64-XXXXX folder
    echo (the one that contains a "scripts" subfolder).
    echo.
    pause
    exit /b 1
)

echo Found WinPython: %WINPYTHON_DIR%
echo.

REM --- Activate WinPython environment ---
call "%WINPYTHON_DIR%\scripts\env.bat"
echo Python: 
python --version
echo.

REM --- Check .env ---
if not exist "%~dp0.env" (
    echo WARNING: No .env file found!
    echo Copy .env.example to .env and fill in your API keys:
    echo     copy .env.example .env
    echo.
    pause
    exit /b 1
)
echo .env file found

REM --- Create directories ---
if not exist "%~dp0data" mkdir "%~dp0data"
if not exist "%~dp0memory\knowledge" mkdir "%~dp0memory\knowledge"
if not exist "%~dp0agent\data" mkdir "%~dp0agent\data"
if not exist "%~dp0agent\improvements" mkdir "%~dp0agent\improvements"

REM --- Install dependencies ---
echo.
echo Installing dependencies...
cd /d "%~dp0"
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies.
    echo Trying with --user flag...
    python -m pip install -r requirements.txt --quiet --user
)

REM --- Start The Constituent ---
echo.
echo =============================================
echo     Starting The Constituent v2.0...
echo =============================================
echo.
python -m agent.main_v2

pause
