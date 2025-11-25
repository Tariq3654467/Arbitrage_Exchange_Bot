# 🖥️ Running the Bot Locally (No Docker)

Complete guide to run everything on your local machine without Docker.

## Part 1: Install Dependencies

### Step 1: Install Python 3.11+

**Windows:**
1. Download from https://www.python.org/downloads/
2. Run installer
3. ✅ CHECK "Add Python to PATH"
4. Click "Install Now"

**Verify:**
```cmd
python --version
pip --version
```

### Step 2: Install PostgreSQL

**Windows:**
1. Download from https://www.postgresql.org/download/windows/
2. Run installer
3. Set password (remember this!)
4. Port: 5432 (default)
5. Install pgAdmin

**Create Database:**
```sql
-- Open pgAdmin or use psql command line
CREATE DATABASE arbitrage_bot;
```

### Step 3: Install InfluxDB

**Windows:**
1. Download from https://portal.influxdata.com/downloads/
2. Download Windows binary
3. Extract to `C:\influxdb`
4. Create data directory: `C:\influxdb\data`

**Start InfluxDB:**
```cmd
cd C:\influxdb
influxd.exe
```

**Setup (in another terminal):**
```cmd
influx setup
# Organization: arbitrage_org
# Bucket: price_data
# Username: admin
# Password: (choose one)
# Save the token shown!
```

### Step 4: Install Redis

**Option A - Memurai (Easiest for Windows):**
1. Download from https://www.memurai.com/get-memurai
2. Install and start service

**Option B - WSL (Windows Subsystem for Linux):**
```bash
# In WSL
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

**Verify Redis:**
```cmd
redis-cli ping
# Should return: PONG
```

## Part 2: Setup Python Environment

### Step 1: Create Virtual Environment

```cmd
# Navigate to project
cd D:\Trading_Bot\Arbitrage_bot

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Your prompt should now show (venv)
```

### Step 2: Install Python Packages

```cmd
# Make sure venv is activated (you should see (venv) in prompt)
pip install --upgrade pip
pip install -r requirements.txt

# This will take a few minutes...
```

## Part 3: Configure Environment

### Step 1: Create .env File

```cmd
# Copy template
copy .env.example .env

# Edit with Notepad
notepad .env
```

### Step 2: Edit .env File

```env
# ===========================================
# REQUIRED: Database Connections
# ===========================================

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=arbitrage_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password_here

# InfluxDB
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token_here
INFLUXDB_ORG=arbitrage_org
INFLUXDB_BUCKET=price_data

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ===========================================
# REQUIRED: Exchange API Keys
# ===========================================

# Binance
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret
BINANCE_TESTNET=false

# OKX (if using)
OKX_API_KEY=your_okx_key
OKX_API_SECRET=your_okx_secret
OKX_PASSPHRASE=your_okx_passphrase
OKX_TESTNET=false

# Bybit (if using)
BYBIT_API_KEY=your_bybit_key
BYBIT_API_SECRET=your_bybit_secret
BYBIT_TESTNET=false

# ===========================================
# OPTIONAL: DEX (Leave blank if not using)
# ===========================================

ETH_PRIVATE_KEY=
BSC_PRIVATE_KEY=
POLYGON_PRIVATE_KEY=

ETH_RPC_URL=
BSC_RPC_URL=https://bsc-dataseed1.binance.org/
POLYGON_RPC_URL=https://polygon-rpc.com/

# ===========================================
# OPTIONAL: Notifications
# ===========================================

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

SENDGRID_API_KEY=
ALERT_EMAIL=

# ===========================================
# General Settings
# ===========================================

ENVIRONMENT=development
LOG_LEVEL=INFO
```

Save and close the file.

## Part 4: Start Services Manually

**You need 4 terminal windows:**

### Terminal 1: PostgreSQL
```cmd
# PostgreSQL should already be running as a Windows service
# Check in Services (services.msc)
# Service name: postgresql-x64-15

# Or start manually:
pg_ctl -D "C:\Program Files\PostgreSQL\15\data" start
```

### Terminal 2: InfluxDB
```cmd
cd C:\influxdb
influxd.exe
# Keep this window open
```

### Terminal 3: Redis
```cmd
# If using Memurai, it runs as a service
# Check in Services: Memurai

# If using WSL:
wsl
sudo service redis-server start
```

### Terminal 4: Dashboard
```cmd
# Navigate to project
cd D:\Trading_Bot\Arbitrage_bot

# Activate virtual environment
venv\Scripts\activate

# Run dashboard
python run_dashboard.py
```

## Part 5: Access Dashboard

1. **Open Browser:**
   ```
   http://localhost:8000
   ```

2. **Login:**
   - Username: `admin`
   - Password: `admin`

3. **Configure:**
   - Click "Configuration" tab
   - Your API keys are already loaded from .env
   - Set trading parameters
   - Click "Start Bot"

## Part 6: Run Bot (Alternative to Dashboard)

If you want to run the bot without the dashboard:

```cmd
# Make sure venv is activated
cd D:\Trading_Bot\Arbitrage_bot
venv\Scripts\activate

# Run main bot
python main.py
```

## 🔧 Troubleshooting

### "Module not found" errors
```cmd
# Make sure virtual environment is activated
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### PostgreSQL connection error
```cmd
# Check PostgreSQL is running
# Open Services (Win+R, type services.msc)
# Find "postgresql-x64-15" and start it

# Test connection
psql -U postgres -d arbitrage_bot
# Enter your password
```

### InfluxDB connection error
```cmd
# Make sure InfluxDB is running
# Check http://localhost:8086 in browser
# You should see InfluxDB UI

# Restart InfluxDB
# Stop the influxd.exe window
# Start it again: influxd.exe
```

### Redis connection error
```cmd
# Test Redis
redis-cli ping
# Should return: PONG

# If using Memurai, restart service:
net stop Memurai
net start Memurai

# If using WSL:
wsl
sudo service redis-server restart
```

### Port 8000 already in use
```cmd
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F

# Or change port in run_dashboard.py:
# Change port=8000 to port=8001
```

### Import errors
```cmd
# Make sure you're in project directory
cd D:\Trading_Bot\Arbitrage_bot

# Activate venv
venv\Scripts\activate

# Check Python path
python -c "import sys; print(sys.path)"

# Should include your project directory
```

## 📊 Check Everything is Running

**Open multiple Command Prompts and check:**

```cmd
# Check PostgreSQL
psql -U postgres -c "SELECT version();"

# Check InfluxDB
curl http://localhost:8086/health

# Check Redis
redis-cli ping

# Check Python packages
pip list | findstr ccxt
```

## 🛑 Stopping Services

**Stop each service:**

```cmd
# Stop Dashboard
# Press Ctrl+C in the dashboard terminal

# Stop InfluxDB  
# Press Ctrl+C in the InfluxDB terminal

# Stop PostgreSQL
# It runs as a service, or:
pg_ctl -D "C:\Program Files\PostgreSQL\15\data" stop

# Stop Redis
# Ctrl+C if running in terminal, or:
net stop Memurai  # if using Memurai
```

## 🎯 Development Workflow

**Daily routine:**

```cmd
# 1. Start databases (if not running as services)
# PostgreSQL - usually auto-starts
# InfluxDB - open terminal: influxd.exe
# Redis - usually auto-starts as service

# 2. Start dashboard
cd D:\Trading_Bot\Arbitrage_bot
venv\Scripts\activate
python run_dashboard.py

# 3. Open browser
# http://localhost:8000

# 4. Start trading via dashboard
```

## 📝 Quick Reference Scripts

### Start All (start.bat)
```batch
@echo off
echo Starting Arbitrage Bot...

REM Start InfluxDB (in new window)
start "InfluxDB" cmd /k "cd C:\influxdb && influxd.exe"

REM Wait 5 seconds
timeout /t 5

REM Start Dashboard
cd D:\Trading_Bot\Arbitrage_bot
call venv\Scripts\activate
python run_dashboard.py
```

Save as `start.bat` and double-click to start everything.

### Stop All (stop.bat)
```batch
@echo off
echo Stopping Arbitrage Bot...

REM Kill Python processes
taskkill /F /IM python.exe

REM Kill InfluxDB
taskkill /F /IM influxd.exe

echo Done!
pause
```

## 🆘 Still Having Issues?

**Common Problems:**

1. **"Python not found"**
   - Reinstall Python with "Add to PATH" checked
   - Or manually add to PATH in System Environment Variables

2. **"Permission denied"**
   - Run Command Prompt as Administrator
   - Right-click → "Run as administrator"

3. **Database won't start**
   - Check Windows Services (services.msc)
   - Restart the service
   - Check logs in installation directory

4. **Can't install packages**
   - Upgrade pip: `python -m pip install --upgrade pip`
   - Try with `--user` flag: `pip install --user -r requirements.txt`
   - Check internet connection

5. **Port conflicts**
   - Change ports in .env file
   - Or stop conflicting services

## 📚 Additional Resources

- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **InfluxDB Docs**: https://docs.influxdata.com/
- **Redis Docs**: https://redis.io/documentation
- **Python venv**: https://docs.python.org/3/library/venv.html

---

**You're now running everything locally! 🎉**

Remember: Keep all terminal windows open while the bot is running.

