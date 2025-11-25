@echo off
REM ============================================
REM Check if all services are running
REM ============================================

echo.
echo ==========================================
echo   Checking Services Status
echo ==========================================
echo.

echo [1/4] Python:
python --version
if errorlevel 1 (
    echo [ERROR] Python not found
) else (
    echo [OK]
)
echo.

echo [2/4] PostgreSQL:
pg_isready -U postgres
if errorlevel 1 (
    echo [ERROR] PostgreSQL not responding
    echo Check if service is running: services.msc
) else (
    echo [OK]
)
echo.

echo [3/4] Redis:
redis-cli ping
if errorlevel 1 (
    echo [ERROR] Redis not responding
    echo Check if Memurai service is running
) else (
    echo [OK]
)
echo.

echo [4/4] InfluxDB:
curl -s http://localhost:8086/health | findstr "pass" >nul
if errorlevel 1 (
    echo [WARNING] InfluxDB may not be running
    echo Try accessing http://localhost:8086 in browser
) else (
    echo [OK]
)
echo.

echo ==========================================
echo   Virtual Environment Check
echo ==========================================
echo.

if exist "venv\Scripts\activate.bat" (
    echo [OK] Virtual environment exists
) else (
    echo [ERROR] Virtual environment not found
    echo Run: python -m venv venv
)
echo.

if exist ".env" (
    echo [OK] .env file exists
) else (
    echo [ERROR] .env file not found
    echo Run: copy .env.example .env
)
echo.

echo ==========================================
echo   Network Ports Check
echo ==========================================
echo.

echo Checking port 8000 (Dashboard):
netstat -an | findstr ":8000"
echo.

echo Checking port 5432 (PostgreSQL):
netstat -an | findstr ":5432"
echo.

echo Checking port 6379 (Redis):
netstat -an | findstr ":6379"
echo.

echo Checking port 8086 (InfluxDB):
netstat -an | findstr ":8086"
echo.

echo ==========================================
echo   All checks complete!
echo ==========================================
echo.

pause

