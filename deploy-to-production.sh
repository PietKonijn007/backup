#!/bin/bash
#
# Production Deployment Script for Backup Application
# Handles ownership, config preservation, and safe updates
#
# Usage: sudo /opt/backup-app/deploy-to-production.sh
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/backup-app"
SERVICE_NAME="backup-daemon"
SERVICE_USER="backupapp"
VENV_PATH="${APP_DIR}/venv"

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Backup Application - Production Deployment${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ This script must be run with sudo${NC}"
    echo "Usage: sudo $0"
    exit 1
fi

# Check if directory exists
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}❌ Application directory not found: $APP_DIR${NC}"
    exit 1
fi

# Navigate to app directory
cd "$APP_DIR"
echo -e "${GREEN}📁 Working directory: $(pwd)${NC}"
echo ""

# Step 1: Backup production files
echo -e "${YELLOW}📦 Step 1/7: Backing up production config files...${NC}"
if [ -f ".env" ]; then
    cp .env .env.backup
    echo -e "${GREEN}   ✓ Backed up .env${NC}"
else
    echo -e "${YELLOW}   ⚠ No .env file found${NC}"
fi

if [ -f "config.yaml" ]; then
    cp config.yaml config.yaml.backup
    echo -e "${GREEN}   ✓ Backed up config.yaml${NC}"
else
    echo -e "${YELLOW}   ⚠ No config.yaml file found${NC}"
fi

if [ -f "token.pickle" ]; then
    cp token.pickle token.pickle.backup
    echo -e "${GREEN}   ✓ Backed up token.pickle${NC}"
fi
echo ""

# Step 2: Check current daemon status
echo -e "${YELLOW}📊 Step 2/7: Checking daemon status...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    DAEMON_WAS_RUNNING=true
    echo -e "${GREEN}   ✓ Daemon is running${NC}"
else
    DAEMON_WAS_RUNNING=false
    echo -e "${YELLOW}   ⚠ Daemon is not running${NC}"
fi
echo ""

# Step 3: Stop daemon gracefully
if [ "$DAEMON_WAS_RUNNING" = true ]; then
    echo -e "${YELLOW}⏸️  Step 3/7: Stopping daemon gracefully...${NC}"
    systemctl stop $SERVICE_NAME
    echo -e "${GREEN}   ✓ Daemon stopped${NC}"
else
    echo -e "${YELLOW}⏭️  Step 3/7: Skipping (daemon already stopped)${NC}"
fi
echo ""

# Step 4: Pull latest code
echo -e "${YELLOW}⬇️  Step 4/7: Pulling latest code from GitHub...${NC}"

# Add safe directory if needed
sudo -u $SERVICE_USER git config --global --add safe.directory $APP_DIR 2>/dev/null || true

# Reset any local changes
echo -e "${BLUE}   Resetting local changes...${NC}"
sudo -u $SERVICE_USER git reset --hard HEAD

# Pull from main branch
echo -e "${BLUE}   Pulling from origin/main...${NC}"
sudo -u $SERVICE_USER git pull origin main

# Show latest commit
LATEST_COMMIT=$(git log -1 --pretty=format:"%h - %s")
echo -e "${GREEN}   ✓ Updated to: $LATEST_COMMIT${NC}"
echo ""

# Step 5: Restore production files
echo -e "${YELLOW}📝 Step 5/7: Restoring production config files...${NC}"
if [ -f ".env.backup" ]; then
    cp .env.backup .env
    echo -e "${GREEN}   ✓ Restored .env${NC}"
fi

if [ -f "config.yaml.backup" ]; then
    cp config.yaml.backup config.yaml
    echo -e "${GREEN}   ✓ Restored config.yaml${NC}"
fi

if [ -f "token.pickle.backup" ]; then
    cp token.pickle.backup token.pickle
    echo -e "${GREEN}   ✓ Restored token.pickle${NC}"
fi
echo ""

# Step 6: Fix ownership
echo -e "${YELLOW}🔒 Step 6/7: Fixing file ownership...${NC}"
chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR
echo -e "${GREEN}   ✓ All files owned by $SERVICE_USER${NC}"
echo ""

# Step 7: Update Python dependencies
echo -e "${YELLOW}📚 Step 7/7: Updating Python dependencies...${NC}"
sudo -u $SERVICE_USER bash -c "source $VENV_PATH/bin/activate && pip install -r requirements.txt --upgrade --quiet"
echo -e "${GREEN}   ✓ Dependencies updated${NC}"
echo ""

# Step 8: Restart daemon
echo -e "${YELLOW}♻️  Restarting daemon...${NC}"
systemctl daemon-reload
systemctl restart $SERVICE_NAME

# Wait for service to start
sleep 3
echo ""

# Step 9: Verify deployment
echo -e "${YELLOW}✅ Verifying deployment...${NC}"

if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}   ✓ Daemon is running${NC}"
    
    # Check for recent errors in logs
    if journalctl -u $SERVICE_NAME --since "30 seconds ago" | grep -i "error\|exception\|failed" > /dev/null; then
        echo -e "${YELLOW}   ⚠ Warning: Errors detected in recent logs${NC}"
        echo -e "${YELLOW}   Run: sudo journalctl -u $SERVICE_NAME -n 50${NC}"
    else
        echo -e "${GREEN}   ✓ No errors in recent logs${NC}"
    fi
else
    echo -e "${RED}   ❌ Daemon failed to start${NC}"
    echo -e "${YELLOW}   Run: sudo journalctl -u $SERVICE_NAME -n 50${NC}"
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════${NC}"
    echo -e "${RED}   Deployment FAILED${NC}"
    echo -e "${RED}═══════════════════════════════════════════════${NC}"
    exit 1
fi

# Get daemon status
STATUS_OUTPUT=$(systemctl status $SERVICE_NAME --no-pager -l | head -15)

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Daemon Status:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo "$STATUS_OUTPUT"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Deployment SUCCESSFUL!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo -e "   • Latest commit: $LATEST_COMMIT"
echo -e "   • Service status: ${GREEN}Running${NC}"
echo -e "   • Config files: ${GREEN}Preserved${NC}"
echo -e "   • Ownership: ${GREEN}Fixed${NC}"
echo ""
echo -e "${BLUE}🔍 Useful commands:${NC}"
echo -e "   • View logs: ${YELLOW}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo -e "   • Check status: ${YELLOW}sudo systemctl status $SERVICE_NAME${NC}"
echo -e "   • Restart: ${YELLOW}sudo systemctl restart $SERVICE_NAME${NC}"
echo ""
