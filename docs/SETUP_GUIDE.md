# Arbitrage Bot - Complete Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Initial Testing](#initial-testing)
6. [Production Deployment](#production-deployment)

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 22.04 LTS or later (recommended)
- **CPU**: 2+ cores
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB SSD minimum
- **Network**: Low-latency connection (<50ms to exchange servers)

### Required Accounts
1. **CEX Accounts**:
   - Binance account with API access
   - OKX account with API access
   - Bybit account with API access

2. **DEX Requirements**:
   - Ethereum wallet with ETH for gas
   - BSC wallet with BNB for gas
   - Polygon wallet with MATIC for gas

3. **Service Accounts**:
   - Telegram account (for alerts)
   - Email service (SendGrid recommended)
   - RPC provider (Alchemy, Infura, or similar)

## Server Setup

### Step 1: Provision Server
```bash
# Recommended: AWS EC2, DigitalOcean, or Vultr
# Choose location closest to exchange servers
# Singapore or Tokyo for Asian exchanges
# London or Frankfurt for European exchanges
```

### Step 2: Initial Server Configuration
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    build-essential \
    libpq-dev

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3: Secure Server
```bash
# Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 3000/tcp  # Grafana (optional, restrict to your IP)
sudo ufw enable

# Set up SSH key authentication (disable password auth)
# Edit: /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd

# Install fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

## Installation

### Step 1: Clone Repository
```bash
# Create project directory
mkdir -p /home/$USER/arbitrage_bot
cd /home/$USER/arbitrage_bot

# Clone repository
git clone <your-repo-url> .

# Or upload files via SCP/SFTP
```

### Step 2: Set Up Python Environment (if not using Docker)
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

### Step 1: Create Environment File
```bash
# Copy template
cp .env.example .env

# Edit environment file
nano .env
```

### Step 2: Configure API Keys

#### Binance
1. Go to https://www.binance.com/en/my/settings/api-management
2. Create new API key
3. Set IP restriction to your server IP
4. Enable "Enable Spot & Margin Trading"
5. Copy API Key and Secret to .env

```bash
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_TESTNET=false  # Use true for testing
```

#### OKX
1. Go to https://www.okx.com/account/my-api
2. Create API key with trading permissions
3. Set IP whitelist
4. Copy credentials

```bash
OKX_API_KEY=your_api_key_here
OKX_API_SECRET=your_secret_here
OKX_PASSPHRASE=your_passphrase_here
OKX_TESTNET=false
```

#### Bybit
1. Go to https://www.bybit.com/app/user/api-management
2. Create API key
3. Enable "Contract Trade" or "Spot Trade"
4. Set IP restriction

```bash
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_secret_here
BYBIT_TESTNET=false
```

### Step 3: Configure Web3 Wallets

**SECURITY WARNING**: Store private keys securely!

```bash
# Generate new wallets or use existing ones
# NEVER use wallets with large holdings for bot trading

ETH_PRIVATE_KEY=0xyour_private_key_here
BSC_PRIVATE_KEY=0xyour_private_key_here
POLYGON_PRIVATE_KEY=0xyour_private_key_here
```

### Step 4: Configure RPC Endpoints

#### Alchemy (Recommended)
1. Sign up at https://www.alchemy.com
2. Create apps for Ethereum, Polygon
3. Copy HTTP URLs

```bash
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY
```

#### BSC (Public or NodeReal)
```bash
BSC_RPC_URL=https://bsc-dataseed1.binance.org/
# Or use NodeReal for better performance
```

### Step 5: Configure Notifications

#### Telegram
1. Create bot: Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Get bot token
4. Get your chat ID: Message @userinfobot

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

#### SendGrid Email
1. Sign up at https://sendgrid.com
2. Create API key with "Mail Send" permission
3. Verify sender email

```bash
SENDGRID_API_KEY=SG.your_api_key
ALERT_EMAIL=your_email@example.com
```

### Step 6: Configure Trading Parameters

Edit `config/config.yaml`:

```yaml
bot:
  paper_trading: true  # Start with paper trading!

trading:
  min_profit_threshold: 0.5  # Minimum 0.5% profit
  max_trade_size_percent: 10  # Use 10% of capital per trade
  max_slippage_percent: 1.0

risk:
  max_drawdown_percent: 20.0
  max_daily_loss_percent: 5.0
  emergency_stop_enabled: true

# Enable/disable specific exchanges
exchanges:
  cex:
    - name: binance
      enabled: true
    - name: okx
      enabled: true
    - name: bybit
      enabled: false  # Disable if not using

  dex:
    - name: pancakeswap
      enabled: true
    - name: uniswap_v2
      enabled: false  # Ethereum fees are high
```

## Initial Testing

### Phase 1: Paper Trading (2 weeks minimum)

```bash
# Ensure paper_trading is enabled
# In config/config.yaml: paper_trading: true

# Start bot
docker-compose up -d

# Monitor logs
docker-compose logs -f bot
```

**What to Check**:
- Bot connects to all exchanges successfully
- Price monitoring is working
- Opportunities are being detected
- Simulated trades execute properly
- Alerts are received
- No errors in logs

### Phase 2: Testnet Trading (1 week)

```bash
# Enable testnet mode in .env
BINANCE_TESTNET=true
OKX_TESTNET=true
BYBIT_TESTNET=true

# Disable paper trading
# In config.yaml: paper_trading: false

# Restart bot
docker-compose restart bot
```

**What to Check**:
- Real order placement works
- Order fills are tracked correctly
- Balance updates work
- Fee calculations are accurate
- Risk management triggers appropriately

### Phase 3: Small Live Trading (1 week)

```bash
# Switch to mainnet
BINANCE_TESTNET=false
OKX_TESTNET=false
BYBIT_TESTNET=false

# Start with VERY small amounts
# In config.yaml: max_trade_size_percent: 1.0

# Fund exchanges with minimal capital
# Example: $100-500 total across all exchanges
```

**What to Monitor**:
- Actual profit vs. expected
- Slippage impact
- Execution time
- Fee accuracy
- Network congestion effects

## Production Deployment

### Step 1: Final Configuration Review
- [ ] All API keys are correct and IP-restricted
- [ ] Private keys are securely stored
- [ ] Risk limits are appropriate
- [ ] Alert channels are working
- [ ] Backup systems are in place
- [ ] Monitoring dashboard is configured

### Step 2: Deploy with Docker Compose
```bash
# Pull latest images
docker-compose pull

# Start all services
docker-compose up -d

# Check all services are running
docker-compose ps

# Should show:
# - bot (running)
# - postgres (healthy)
# - influxdb (healthy)
# - redis (healthy)
# - grafana (running)
```

### Step 3: Set Up Auto-Restart
```bash
# All services have restart: unless-stopped
# They will auto-restart on failure or reboot

# To enable bot to start on system boot:
sudo systemctl enable docker
```

### Step 4: Set Up Monitoring
```bash
# Access Grafana
http://your-server-ip:3000

# Login: admin / (password from docker-compose.yml)

# Add InfluxDB data source:
# - URL: http://influxdb:8086
# - Organization: arbitrage_org
# - Token: (from .env INFLUXDB_TOKEN)
# - Bucket: price_data

# Import dashboard or create custom panels
```

### Step 5: Set Up Log Rotation
```bash
# Create logrotate config
sudo nano /etc/logrotate.d/arbitrage-bot

# Add:
/home/user/arbitrage_bot/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 user user
    sharedscripts
}
```

### Step 6: Set Up Backup
```bash
# Create backup script
nano backup.sh

#!/bin/bash
# Backup database and config
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/home/user/backups
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U postgres arbitrage_bot > \
    $BACKUP_DIR/postgres_$DATE.sql

# Backup InfluxDB
docker-compose exec -T influxdb influx backup /tmp/backup_$DATE
docker cp arbitrage_influxdb:/tmp/backup_$DATE $BACKUP_DIR/

# Backup config and .env
cp .env $BACKUP_DIR/env_$DATE
cp -r config $BACKUP_DIR/config_$DATE

# Compress
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz \
    $BACKUP_DIR/postgres_$DATE.sql \
    $BACKUP_DIR/backup_$DATE \
    $BACKUP_DIR/env_$DATE \
    $BACKUP_DIR/config_$DATE

# Clean up
rm -rf $BACKUP_DIR/postgres_$DATE.sql \
    $BACKUP_DIR/backup_$DATE \
    $BACKUP_DIR/env_$DATE \
    $BACKUP_DIR/config_$DATE

# Keep only last 30 backups
ls -t $BACKUP_DIR/backup_*.tar.gz | tail -n +31 | xargs rm -f

# Make executable
chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/user/arbitrage_bot/backup.sh
```

## Post-Deployment Checklist

- [ ] Bot is running and connected to all exchanges
- [ ] Price monitoring is active
- [ ] Trades are executing correctly
- [ ] Alerts are being received
- [ ] Dashboard shows live data
- [ ] Backups are working
- [ ] Emergency stop is configured
- [ ] Contact information for support is handy
- [ ] Documentation is accessible
- [ ] Team is trained on operations

## Next Steps

Proceed to:
- [Operations Manual](OPERATIONS_MANUAL.md) for day-to-day management
- [Troubleshooting Guide](TROUBLESHOOTING.md) for common issues
- [Configuration Guide](CONFIGURATION_GUIDE.md) for parameter tuning

