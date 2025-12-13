# AWS Deployment Guide for Arbitrage Exchange Bot

This guide provides step-by-step instructions for deploying the Arbitrage Exchange Bot on AWS. Two deployment options are covered:

1. **EC2 (Recommended for low budget)** - Simple virtual server deployment, similar to Vultr
2. **ECS (Advanced)** - Container orchestration service for scalable production deployments

## Part 1: EC2 Deployment (Recommended for Low Budget)

### Step 1: Create AWS Account and EC2 Instance

1. **Sign up/Login to AWS:**

   - Go to https://aws.amazon.com
   - Create account or login
   - Complete account verification if required

2. **Navigate to EC2 Console:**

   - Search for "EC2" in AWS Console
   - Click "EC2" → "Instances"

3. **Launch EC2 Instance:**

   - Click "Launch Instance"
   - **Name:** arbitrage-bot
   - **AMI (Amazon Machine Image):** Ubuntu Server 22.04 LTS (free tier eligible)
   - **Instance Type:** 
     - **Low Budget:** t3.small (2 vCPU, 2GB RAM) - ~$15/month
     - **Recommended:** t3.medium (2 vCPU, 4GB RAM) - ~$30/month
     - **Production:** t3.large (2 vCPU, 8GB RAM) - ~$60/month
   - **Key Pair:** Create new or select existing (download .pem file - you'll need it!)
   - **Network Settings:**
     - Create new security group or select existing
     - **Inbound Rules:** Add these rules:
       - SSH (22) from My IP
       - HTTP (80) from Anywhere (0.0.0.0/0)
       - HTTPS (443) from Anywhere (0.0.0.0/0)
       - Custom TCP (3001) from Anywhere (for frontend)
       - Custom TCP (8000) from Anywhere (for backend API)
       - Custom TCP (3000) from Anywhere (for Grafana, optional)
   - **Configure Storage:** 30GB gp3 (SSD) - sufficient for Docker images and data
   - **Advanced Details (Optional):**
     - Add user data script for automatic setup (see below)
   - Click "Launch Instance"

4. **Wait for Instance:**

   - Wait 2-3 minutes for instance to be ready
   - Note the **Public IPv4 address** and **Instance ID**

### Step 2: Connect to EC2 Instance

**On Windows (using PowerShell or Git Bash):**

```bash
# Navigate to folder containing your .pem key file
cd path/to/your/key

# Set correct permissions (Git Bash)
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

**On Mac/Linux:**

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

**Alternative: Use AWS Systems Manager Session Manager (no key needed):**

- Install AWS CLI and Session Manager plugin
- Connect via: `aws ssm start-session --target i-YOUR_INSTANCE_ID`

### Step 3: Initial Server Setup

1. **Update System:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y curl wget git ufw python3 python3-pip
   ```

2. **Sync System Clock (Critical for Binance API):**
   ```bash
   sudo timedatectl set-ntp true
   sudo timedatectl status
   ```

3. **Configure Firewall:**
   ```bash
   # Allow SSH (important!)
   sudo ufw allow 22/tcp
   
   # Allow application ports
   sudo ufw allow 3001/tcp  # Frontend
   sudo ufw allow 8000/tcp  # Backend API
   sudo ufw allow 3000/tcp  # Grafana (optional)
   
   # Enable firewall
   sudo ufw --force enable
   sudo ufw status
   ```

### Step 4: Install Docker and Docker Compose

1. **Install Docker:**
   ```bash
   # Remove old versions
   sudo apt remove docker docker-engine docker.io containerd runc 2>/dev/null
   
   # Install prerequisites
   sudo apt install -y ca-certificates gnupg lsb-release
   
   # Add Docker's official GPG key
   sudo mkdir -p /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   
   # Set up repository
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   
   # Install Docker
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   
   # Add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker  # Apply group change
   
   # Verify installation
   docker --version
   docker compose version
   ```

2. **Test Docker:**
   ```bash
   docker run hello-world
   ```

### Step 5: Clone and Setup Project

1. **Clone Repository:**
   ```bash
   cd ~
   git clone https://github.com/Tariq3654467/Arbitrage_Exchange_Bot.git
   cd Arbitrage_Exchange_Bot
   ```

2. **Create Required Directories:**
   ```bash
   mkdir -p data logs
   chmod 700 data
   ```

3. **Generate Encryption Key:**
   ```bash
   # Generate encryption key
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # Copy the output - you'll need it for .env file
   ```

### Step 6: Configure Environment Variables

1. **Create .env File:**
   ```bash
   nano .env
   ```

2. **Add Configuration (replace placeholders):**
   ```env
   # Environment
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   
   # Database - Use container names for Docker
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   POSTGRES_DB=arbitrage_bot
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<GENERATE_STRONG_PASSWORD>
   
   # InfluxDB
   INFLUXDB_URL=http://influxdb:8086
   INFLUXDB_TOKEN=<GENERATE_32_CHAR_TOKEN>
   INFLUXDB_ORG=arbitrage_org
   INFLUXDB_BUCKET=price_data
   INFLUXDB_PASSWORD=<GENERATE_STRONG_PASSWORD>
   
   # Redis
   REDIS_HOST=redis
   REDIS_PORT=6379
   
   # Grafana
   GRAFANA_PASSWORD=<GENERATE_STRONG_PASSWORD>
   
   # GalaChain Configuration (if using Galaswap)
   GALA_RPC_URL=https://mainnet.galachain.io
   GALA_PRIVATE_KEY=<your_wallet_private_key_here>
   
   # Encryption Key (CRITICAL - paste the key generated in Step 5)
   ENCRYPTION_KEY=<paste_generated_key_here>
   ```

3. **Generate Strong Passwords:**
   ```bash
   # Generate random passwords
   openssl rand -base64 32  # Use for POSTGRES_PASSWORD
   openssl rand -base64 32  # Use for INFLUXDB_PASSWORD
   openssl rand -base64 32  # Use for GRAFANA_PASSWORD
   openssl rand -hex 16     # Use for INFLUXDB_TOKEN
   ```

4. **Save and Exit:**

   - Press `Ctrl+X`, then `Y`, then `Enter`

### Step 7: Build and Start Services

1. **Build Docker Images:**
   ```bash
   docker compose build
   # This may take 10-15 minutes on first build
   ```

2. **Start Services:**
   ```bash
   docker compose up -d
   ```

3. **Check Service Status:**
   ```bash
   docker compose ps
   # All services should show "Up" status
   ```

4. **View Logs:**
   ```bash
   # All services
   docker compose logs -f
   
   # Specific service
   docker compose logs -f dashboard
   docker compose logs -f frontend
   ```

### Step 8: Verify Deployment

1. **Check Health Endpoint:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy",...}
   ```

2. **Access Services:**

   - **Frontend:** http://YOUR_EC2_PUBLIC_IP:3001
   - **Backend API:** http://YOUR_EC2_PUBLIC_IP:8000
   - **Grafana:** http://YOUR_EC2_PUBLIC_IP:3000

3. **Test from Browser:**

   - Open http://YOUR_EC2_PUBLIC_IP:3001 in your browser
   - You should see the dashboard

### Step 9: Configure AWS Security Group (Important!)

1. **Update Security Group Rules:**

   - Go to EC2 Console → Instances → Select your instance
   - Click "Security" tab → Click security group name
   - Click "Edit inbound rules"
   - Ensure these rules exist:
     - SSH (22) from your IP only
     - HTTP (80) from 0.0.0.0/0 (for future HTTPS setup)
     - HTTPS (443) from 0.0.0.0/0
     - Custom TCP (3001) from 0.0.0.0/0 (or restrict to your IP)
     - Custom TCP (8000) from 0.0.0.0/0 (or restrict to your IP)
   - Click "Save rules"

### Step 10: Optional - Domain and HTTPS Setup

1. **Point Domain to EC2:**

   - In Route 53 or your DNS provider:
     - Add A record: `@` → YOUR_EC2_PUBLIC_IP
     - Add A record: `bot` → YOUR_EC2_PUBLIC_IP (optional)

2. **Install Nginx:**
   ```bash
   sudo apt install -y nginx certbot python3-certbot-nginx
   ```

3. **Configure Nginx Reverse Proxy:**
   ```bash
   sudo nano /etc/nginx/sites-available/arbitrage-bot
   ```

Add configuration:

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       # Frontend
       location / {
           proxy_pass http://localhost:3001;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
       
       # Backend API
       location /api {
           pro