# Server Deployment Guide

This guide covers deploying the Arbitrage Exchange Bot on a production server.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM recommended
- Ports 3001 (frontend), 8000 (backend), 5432 (PostgreSQL), 6379 (Redis), 8086 (InfluxDB), 3000 (Grafana) available

## Quick Start

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd Arbitrage_Exchange_Bot
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env  # If you have an example file
   # Or create .env manually with required variables
   ```

3. **Configure environment variables in `.env`:**
   ```env
   # Database
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   POSTGRES_DB=arbitrage_bot
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<strong_password>

   # InfluxDB
   INFLUXDB_URL=http://influxdb:8086
   INFLUXDB_TOKEN=<generate_secure_token>
   INFLUXDB_ORG=arbitrage_org
   INFLUXDB_BUCKET=price_data
   INFLUXDB_PASSWORD=<strong_password>

   # Redis
   REDIS_HOST=redis
   REDIS_PORT=6379

   # Grafana
   GRAFANA_PASSWORD=<strong_password>

   # GalaChain (if using Galaswap)
   GALA_RPC_URL=https://mainnet.galachain.io
   GALA_PRIVATE_KEY=<your_private_key>

   # Encryption Key (IMPORTANT: Set this for production!)
   # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ENCRYPTION_KEY=<your_encryption_key_here>
   ```

4. **Create data directory for encryption key persistence:**
   ```bash
   mkdir -p data
   chmod 700 data  # Secure the directory
   ```

5. **Build and start services:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

6. **Check service status:**
   ```bash
   docker-compose ps
   docker-compose logs -f  # Follow logs
   ```

## Important Configuration

### Encryption Key

**CRITICAL:** Set the `ENCRYPTION_KEY` environment variable in `.env` before first deployment. This ensures API keys remain decryptable across container restarts.

To generate a key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If you don't set this, a new key will be generated on each container restart, making previously saved API keys unreadable.

### Persistent Data

The following directories are mounted as volumes for data persistence:
- `./logs` - Application logs
- `./config` - Configuration files
- `./data` - Encryption keys and other persistent data
- Database volumes (managed by Docker)

### Network Configuration

- **Frontend:** http://your-server-ip:3001
- **Backend API:** http://your-server-ip:8000
- **Grafana:** http://your-server-ip:3000

## Troubleshooting

### Encryption Key Mismatch Errors

If you see errors like:
```
Encryption key mismatch when reading keys for binance
```

**Solution:**
1. Set `ENCRYPTION_KEY` in `.env` to match the original key
2. OR truncate the `api_keys` table and re-enter API keys:
   ```bash
   docker-compose exec postgres psql -U postgres -d arbitrage_bot -c "TRUNCATE TABLE api_keys;"
   ```

### Socket Hang Up Errors

These occur when the backend takes too long to respond. This is usually temporary and the frontend will retry automatically.

### Binance Timestamp Errors

If you see:
```
Timestamp for this request is outside of the recvWindow
```

**Solution:** Ensure your server's clock is synchronized:
```bash
# On Ubuntu/Debian
sudo apt-get install ntp
sudo systemctl enable ntp
sudo systemctl start ntp

# Or use systemd-timesyncd
sudo timedatectl set-ntp true
```

### Frontend Can't Access Backend

If the frontend shows connection errors:
1. Check that both services are running: `docker-compose ps`
2. Check backend logs: `docker-compose logs dashboard`
3. Verify network connectivity: `docker-compose exec frontend wget -O- http://dashboard:8000/health`

## Security Recommendations

1. **Change default passwords** in `.env`
2. **Use strong encryption key** and back it up securely
3. **Restrict port access** using firewall (only expose 3001 and 8000 if needed)
4. **Use HTTPS** in production (set up reverse proxy like Nginx)
5. **Regular backups** of database volumes
6. **Monitor logs** regularly for suspicious activity

## Backup and Restore

### Backup Database
```bash
docker-compose exec postgres pg_dump -U postgres arbitrage_bot > backup.sql
```

### Restore Database
```bash
docker-compose exec -T postgres psql -U postgres arbitrage_bot < backup.sql
```

### Backup Encryption Key
```bash
cp data/.encryption_key encryption_key.backup
# Store this backup securely!
```

## Monitoring

- **Logs:** `docker-compose logs -f [service_name]`
- **Health Check:** `curl http://localhost:8000/health`
- **Grafana:** Access at http://your-server-ip:3000 (admin/admin by default)

## Updates

To update the application:
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

## Support

For issues, check:
1. Service logs: `docker-compose logs [service_name]`
2. Container status: `docker-compose ps`
3. Network connectivity: `docker network inspect arbitrage_exchange_bot_arbitrage_network`

