#!/bin/bash
# EC2 User Data Script for Backup Application
# This script runs on first boot to set up the entire application

set -e
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== Starting Backup App Setup ==="
echo "Timestamp: $(date)"

# Update system
echo "Step 1: Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo "Step 2: Installing dependencies..."
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    curl \
    unzip \
    jq

# Install rclone
echo "Step 3: Installing rclone..."
curl https://rclone.org/install.sh | bash

# Create application user
echo "Step 4: Creating application user..."
useradd -m -s /bin/bash backupapp || true

# Create application directories
echo "Step 5: Setting up directories..."
mkdir -p /opt/backup-app
mkdir -p /var/log/backup-app
mkdir -p /sync
chown -R backupapp:backupapp /opt/backup-app
chown -R backupapp:backupapp /var/log/backup-app
chown -R backupapp:backupapp /sync

# Clone repository (using GitHub URL from workspace config)
echo "Step 6: Cloning repository..."
cd /opt/backup-app
if [ ! -d ".git" ]; then
    sudo -u backupapp git clone https://github.com/PietKonijn007/backup.git .
fi

# Set up Python virtual environment
echo "Step 7: Setting up Python environment..."
sudo -u backupapp python3.11 -m venv venv
sudo -u backupapp /opt/backup-app/venv/bin/pip install --upgrade pip
sudo -u backupapp /opt/backup-app/venv/bin/pip install -r requirements.txt

# Get environment variables from AWS Systems Manager Parameter Store
echo "Step 8: Retrieving configuration from Parameter Store..."
aws ssm get-parameter --name "/backup-app/env" --with-decryption --query "Parameter.Value" --output text --region us-east-1 > /opt/backup-app/.env || echo "Parameter not found, using manual configuration"
chown backupapp:backupapp /opt/backup-app/.env

# Configure rclone
echo "Step 9: Configuring rclone..."
mkdir -p /home/backupapp/.config/rclone
cat > /home/backupapp/.config/rclone/rclone.conf << 'RCLONE_EOF'
[remote-s3]
type = s3
provider = AWS
env_auth = true
region = us-east-1

[remote-eu]
type = s3
provider = Scaleway
access_key_id = ${EU_PROVIDER_ACCESS_KEY}
secret_access_key = ${EU_PROVIDER_SECRET_KEY}
endpoint = s3.fr-par.scw.cloud
region = fr-par
RCLONE_EOF

# Load env vars and substitute Scaleway credentials
if [ -f /opt/backup-app/.env ]; then
    source /opt/backup-app/.env
    sed -i "s/\${EU_PROVIDER_ACCESS_KEY}/$EU_PROVIDER_ACCESS_KEY/g" /home/backupapp/.config/rclone/rclone.conf
    sed -i "s/\${EU_PROVIDER_SECRET_KEY}/$EU_PROVIDER_SECRET_KEY/g" /home/backupapp/.config/rclone/rclone.conf
fi

chown -R backupapp:backupapp /home/backupapp/.config

# Copy systemd service files
echo "Step 10: Setting up systemd services..."
cp /opt/backup-app/systemd/backup-daemon.service /etc/systemd/system/
systemctl daemon-reload

# Configure Nginx reverse proxy
echo "Step 11: Configuring Nginx..."
cat > /etc/nginx/sites-available/backup-app << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for SSE
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Increase client body size for file uploads
    client_max_body_size 100M;
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/backup-app /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Initialize database
echo "Step 12: Initializing database..."
cd /opt/backup-app
sudo -u backupapp /opt/backup-app/venv/bin/python init_user.py || true

# Enable and start services
echo "Step 13: Starting services..."
systemctl enable nginx
systemctl enable backup-daemon
systemctl start backup-daemon

# Wait for application to start
sleep 5

# Check status
echo "Step 14: Checking service status..."
systemctl status backup-daemon --no-pager || true
systemctl status nginx --no-pager || true

echo "=== Setup Complete ==="
echo "Timestamp: $(date)"
echo ""
echo "Application should be accessible at:"
echo "- http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo ""
echo "Logs available at:"
echo "- /var/log/backup-app/"
echo "- journalctl -u backup-daemon"
echo ""
