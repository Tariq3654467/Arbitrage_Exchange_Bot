# Docker Setup Guide

## Quick Start

### 1. Create Environment File

Create a `.env` file in the root directory:

```bash
# Copy the template (if .env.example exists)
cp .env.example .env

# Or create manually with these minimum required variables:
```

**Minimum `.env` file:**
```env
POSTGRES_DB=arbitrage_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

INFLUXDB_PASSWORD=your_influx_password
INFLUXDB_ORG=arbitrage_org
INFLUXDB_BUCKET=price_data
INFLUXDB_TOKEN=your_influx_token

GRAFANA_PASSWORD=admin

ENVIRONMENT=production
LOG_LEVEL=INFO

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
INFLUXDB_URL=http://influxdb:8086
REDIS_HOST=redis
REDIS_PORT=6379

BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
MEXC_API_KEY=your_key
MEXC_API_SECRET=your_secret

GALA_WALLET_ADDRESS=your_address
GALA_PRIVATE_KEY=your_key
GALA_PUBLIC_KEY=your_key

API_USERNAME=admin
API_PASSWORD=admin
```

### 2. Start Services

**Windows:**
```bash
start_docker.bat
```

**Linux/Mac:**
```bash
chmod +x start_docker.sh
./start_docker.sh
```

**Or manually:**
```bash
docker-compose up -d --build
```

### 3. Access Services

- **Frontend Dashboard**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **InfluxDB UI**: http://localhost:8086
- **Grafana**: http://localhost:3000

### 4. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f dashboard
docker-compose logs -f frontend
```

## First Time Setup

1. **Create `.env` file** with your configuration (see above)
2. **Add your API keys** to `.env`:
   - Binance API key and secret
   - MEXC API key and secret
   - Gala wallet address and keys
3. **Start services**: `docker-compose up -d --build`
4. **Wait 30-60 seconds** for databases to initialize
5. **Access frontend**: http://localhost:3001
6. **Login**: Use credentials from `.env` (default: admin/admin)

## Service Architecture

```
┌─────────────┐
│  Frontend   │ :3001 (Next.js)
│  (Browser)  │
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────┐
│  Dashboard  │ :8000 (FastAPI)
│  (Backend)  │
└──────┬──────┘
       │
       ├──► PostgreSQL :5432
       ├──► InfluxDB  :8086
       └──► Redis     :6379
```

## Configuration

### Environment Variables

All configuration is done via `.env` file. Key variables:

- **Database**: `POSTGRES_*`, `INFLUXDB_*`, `REDIS_*`
- **API Keys**: `BINANCE_*`, `MEXC_*`, `GALA_*`
- **Application**: `ENVIRONMENT`, `LOG_LEVEL`

### Ports

- **3001**: Frontend (Next.js)
- **8000**: Backend API (FastAPI)
- **5432**: PostgreSQL
- **8086**: InfluxDB
- **6379**: Redis
- **3000**: Grafana (optional)

To change ports, edit `docker-compose.yml`.

## Troubleshooting

### Services Won't Start

1. **Check Docker is running**:
   ```bash
   docker info
   ```

2. **Check port conflicts**:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

3. **Check logs**:
   ```bash
   docker-compose logs
   ```

### Frontend Can't Connect to Backend

1. **Verify backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check frontend environment**:
   - Should be `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - Check browser console for errors

3. **Check CORS settings** in `src/api/main.py`

### Database Connection Errors

1. **Wait for initialization**: Databases need 30-60 seconds on first start
2. **Check credentials**: Verify `.env` matches docker-compose.yml
3. **Check logs**: `docker-compose logs postgres`

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build

# Or rebuild specific service
docker-compose build dashboard
docker-compose up -d dashboard
```

## Maintenance

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Data
```bash
docker-compose down -v
```

### Update Services
```bash
# Pull latest images
docker-compose pull

# Rebuild with latest code
docker-compose up -d --build
```

### Backup Data
```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres arbitrage_bot > backup.sql

# Backup volumes
docker run --rm -v arbitrage_bot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Production Considerations

Before deploying to production:

1. **Change all default passwords** in `.env`
2. **Use strong passwords** for databases
3. **Enable HTTPS** (use reverse proxy like nginx)
4. **Set up firewall** rules
5. **Configure backups** for databases
6. **Monitor logs** regularly
7. **Set resource limits** in docker-compose.yml
8. **Use secrets management** (Docker secrets, Vault, etc.)

## Additional Resources

- See `docker-commands.md` for complete command reference
- See `docs/SETUP_GUIDE.md` for detailed setup instructions
- See `docs/TROUBLESHOOTING.md` for common issues

