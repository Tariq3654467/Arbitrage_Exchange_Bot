@echo off
REM ============================================
REM Arbitrage Bot - Local Setup Script
REM ============================================

echo.
echo ==========================================
echo   Arbitrage Bot - Initial Setup
echo ==========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM Create virtual environment
echo [1/5] Creating virtual environment...
if exist "venv" (
    echo Virtual environment already exists
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)
echo.

REM Activate virtual environment
echo [2/5] Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] Pip upgraded
echo.

REM Install requirements
echo [4/5] Installing Python packages...
echo This may take several minutes...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install packages
    pause
    exit /b 1
)
echo [OK] All packages installed
echo.

REM Create .env file
echo [5/5] Setting up configuration...
if exist ".env" (
    echo [OK] .env file already exists
) else (
    copy .env.example .env
    echo [OK] .env file created from template
    echo.
    echo ==========================================
    echo IMPORTANT: Edit .env file with your settings!
    echo ==========================================
    echo.
    echo Please configure:
    echo 1. Database passwords
    echo 2. Exchange API keys
    echo 3. Other settings
    echo.
    echo Opening .env in Notepad...
    timeout /t 2 >nul
    notepad .env
)
echo.

echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Install and start PostgreSQL
echo 2. Install and start Redis/Memurai
echo 3. Install InfluxDB
echo 4. Configure .env file (edit with your API keys)
echo 5. Run: start_local.bat
echo.
echo For detailed instructions, see: RUN_LOCALLY.md
echo.

pause

