# Troubleshooting Dashboard Container Health Check Failure

## Issue
The dashboard container is showing as "unhealthy" and failing to start.

## Steps to Diagnose

### 1. Check Container Logs
```bash
docker compose logs dashboard --tail 200
```

### 2. Check Container Status
```bash
docker compose ps
```

### 3. Check Health Check Endpoint
```bash
# Try accessing the health endpoint directly
curl http://localhost:8000/health
```

### 4. Common Issues and Solutions

#### Issue: Import Errors
If you see import errors in the logs:
```bash
# Check if all dependencies are installed
docker compose exec dashboard pip list | grep -E "eth-account|eth-keys|aiohttp"
```

#### Issue: Configuration Errors
If you see configuration errors:
```bash
# Check config file
docker compose exec dashboard cat config/config.yaml | head -50
```

#### Issue: Database Connection
If you see database connection errors:
```bash
# Check if PostgreSQL is running
docker compose ps postgres
# Check database connection
docker compose exec dashboard python -c "import psycopg2; psycopg2.connect('postgresql://user:pass@postgres:5432/dbname')"
```

#### Issue: API Connection Errors
If you see GalaSwap API errors:
```bash
# Check network connectivity
docker compose exec dashboard curl -I https://dex-backend-prod1.defi.gala.com/v1/trade/price?token=GALA\$Unit\$none\$none
```

### 5. Restart Container
```bash
# Stop and remove container
docker compose down dashboard
# Rebuild if needed
docker compose build dashboard
# Start again
docker compose up -d dashboard
# Watch logs
docker compose logs -f dashboard
```

### 6. Check Health Check Configuration
The health check might be too strict. Check `docker-compose.yml`:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### 7. Manual Container Inspection
```bash
# Inspect container
docker inspect arbitrage_dashboard | grep -A 10 Health
# Check if container is actually running
docker compose exec dashboard ps aux
```

## Quick Fix: Restart Everything
```bash
docker compose down
docker compose up -d
docker compose logs -f dashboard
```

## If Still Failing
1. Check the full error logs: `docker compose logs dashboard > dashboard_logs.txt`
2. Share the error message for further diagnosis
3. Check if there are any syntax errors: `docker compose exec dashboard python -m py_compile src/exchanges/dex/galaswap_connector.py`

