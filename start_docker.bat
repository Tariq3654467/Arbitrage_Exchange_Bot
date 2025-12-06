@echo off
REM ============================================
REM Arbitrage Bot - Docker Compose Startup
REM ============================================

echo.
echo ==========================================
echo   Arbitrage Bot - Docker Deployment
echo ==========================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo.
    echo Creating .env from template...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] Created .env file from template
        echo.
        echo [IMPORTANT] Please edit .env and add your API keys!
        echo Press any key to continue anyway, or Ctrl+C to exit...
        pause >nul
    ) else (
        echo [ERROR] .env.example not found!
        echo Please create .env file manually
        pause
        exit /b 1
    )
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo [1/3] Building Docker images...
docker-compose build
if errorlevel 1 (
    echo [ERROR] Failed to build images
    pause
    exit /b 1
)

echo.
echo [2/3] Starting services...
docker-compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)

echo.
echo [3/3] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ==========================================
echo   Services Started Successfully!
echo ==========================================
echo.
echo Frontend Dashboard: http://localhost:3001
echo Backend API:        http://localhost:8000
echo InfluxDB UI:       http://localhost:8086
echo Grafana:           http://localhost:3000
echo.
echo ==========================================
echo   Useful Commands:
echo ==========================================
echo View logs:         docker-compose logs -f
echo Stop services:    docker-compose down
echo Restart:          docker-compose restart
echo Status:           docker-compose ps
echo ==========================================
echo.
echo Services are starting... This may take 30-60 seconds
echo Check logs with: docker-compose logs -f
echo.
pause

