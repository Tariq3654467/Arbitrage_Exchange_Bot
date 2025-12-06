# Docker Commands Reference

## Quick Start

### Windows
```bash
start_docker.bat
```

### Linux/Mac
```bash
chmod +x start_docker.sh
./start_docker.sh
```

### Manual Start
```bash
docker-compose up -d --build
```

## Common Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# Start specific service
docker-compose up -d dashboard
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dashboard
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 -f
```

### Service Status
```bash
# List running containers
docker-compose ps

# Resource usage
docker stats

# Container health
docker-compose ps
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart dashboard
```

### Execute Commands
```bash
# Run command in container
docker-compose exec dashboard python -c "print('Hello')"

# Access container shell
docker-compose exec dashboard /bin/bash

# Run one-off command
docker-compose run --rm dashboard python main.py
```

### Cleanup
```bash
# Remove stopped containers
docker-compose rm

# Remove unused images
docker image prune

# Remove everything (volumes, networks, images)
docker-compose down -v --rmi all
```

## Troubleshooting

### Port Conflicts
```bash
# Check what's using a port (Windows)
netstat -ano | findstr :8000

# Check what's using a port (Linux/Mac)
lsof -i :8000

# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### View Container Logs
```bash
# Direct container access
docker logs arbitrage_dashboard
docker logs arbitrage_frontend

# Follow logs
docker logs -f arbitrage_dashboard
```

### Rebuild After Code Changes
```bash
# Rebuild specific service
docker-compose build dashboard
docker-compose up -d dashboard

# Rebuild all without cache
docker-compose build --no-cache
docker-compose up -d
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d arbitrage_bot

# Connect to Redis
docker-compose exec redis redis-cli

# InfluxDB CLI
docker-compose exec influxdb influx
```

### Environment Variables
```bash
# Check environment in container
docker-compose exec dashboard env

# Update .env file and restart
docker-compose down
# Edit .env
docker-compose up -d
```

## Service URLs

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **InfluxDB**: http://localhost:8086
- **Grafana**: http://localhost:3000

## Network

All services are on the `arbitrage_network` bridge network.

Services can communicate using service names:
- `http://dashboard:8000` (from other containers)
- `http://postgres:5432`
- `http://redis:6379`
- `http://influxdb:8086`

