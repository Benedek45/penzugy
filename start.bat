@echo off
title Capitalism At It's Finest

echo.
echo  =============================================
echo   Capitalism At It's Finest - Local Server
echo  =============================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install it from https://python.org
    pause
    exit /b 1
)

echo  [1/3] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

echo  [2/3] Starting server...
echo.
echo  Open your browser at: http://localhost:5000
echo  Press Ctrl+C to stop.
echo.

:: Open browser after 2 second delay (server needs a moment to start)
start "" cmd /c "timeout /t 2 >nul && start http://localhost:5000"

:: [3/3] Launch Flask
python app.py

pause
