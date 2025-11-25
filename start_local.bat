@echo off
REM ============================================
REM Arbitrage Bot - Local Startup Script
REM ============================================

echo.
echo ==========================================
echo   Starting Arbitrage Bot (Local Mode)
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then run: venv\Scripts\activate
    echo Then run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it
    echo Run: copy .env.example .env
    pause
    exit /b 1
)

echo [1/5] Checking PostgreSQL...
pg_isready -U postgres >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PostgreSQL may not be running
    echo Please start PostgreSQL service
    echo.
) else (
    echo [OK] PostgreSQL is running
    echo.
)

echo [2/5] Checking Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Redis may not be running
    echo Please start Redis/Memurai service
    echo.
) else (
    echo [OK] Redis is running
    echo.
)

echo [3/5] Starting InfluxDB...
start "InfluxDB Server" cmd /k "cd C:\influxdb && influxd.exe"
echo [OK] InfluxDB starting in new window...
timeout /t 3 >nul
echo.

echo [4/5] Activating Python virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

echo [5/5] Starting Dashboard...
echo.
echo ==========================================
echo   Dashboard will start at:
echo   http://localhost:8000
echo   
echo   Login: admin / admin
echo ==========================================
echo.
echo Press Ctrl+C to stop the bot
echo.

python run_dashboard.py

REM Cleanup on exit
echo.
echo Cleaning up...
taskkill /F /IM influxd.exe >nul 2>&1

pause

