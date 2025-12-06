#!/bin/bash
# ============================================
# Arbitrage Bot - Docker Compose Startup
# ============================================

echo ""
echo "=========================================="
echo "  Arbitrage Bot - Docker Deployment"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found!"
    echo ""
    echo "Creating .env from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "[OK] Created .env file from template"
        echo ""
        echo "[IMPORTANT] Please edit .env and add your API keys!"
        read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
    else
        echo "[ERROR] .env.example not found!"
        echo "Please create .env file manually"
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running!"
    echo "Please start Docker and try again"
    exit 1
fi

echo "[1/3] Building Docker images..."
docker-compose build
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to build images"
    exit 1
fi

echo ""
echo "[2/3] Starting services..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to start services"
    exit 1
fi

echo ""
echo "[3/3] Waiting for services to be ready..."
sleep 10

echo ""
echo "=========================================="
echo "  Services Started Successfully!"
echo "=========================================="
echo ""
echo "Frontend Dashboard: http://localhost:3001"
echo "Backend API:        http://localhost:8000"
echo "InfluxDB UI:       http://localhost:8086"
echo "Grafana:           http://localhost:3000"
echo ""
echo "=========================================="
echo "  Useful Commands:"
echo "=========================================="
echo "View logs:         docker-compose logs -f"
echo "Stop services:    docker-compose down"
echo "Restart:          docker-compose restart"
echo "Status:           docker-compose ps"
echo "=========================================="
echo ""
echo "Services are starting... This may take 30-60 seconds"
echo "Check logs with: docker-compose logs -f"
echo ""

