#!/bin/bash
# Fix OAuth Redirect URI on Production Server
# This script should be run ON THE PRODUCTION SERVER

set -e

echo "=================================================="
echo "Fix OAuth Redirect URI - Production Server"
echo "=================================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Warning: Running as root. Consider running as your app user instead."
fi

# Find the app directory
APP_DIR="/home/ubuntu/backup"  # Adjust if different
if [ ! -d "$APP_DIR" ]; then
    echo "Enter the path to your app directory:"
    read APP_DIR
fi

echo "Using app directory: $APP_DIR"
cd "$APP_DIR"

# Backup current .env
echo ""
echo "1. Backing up current .env file..."
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✓ Backup created"
else
    echo "⚠️  No .env file found"
fi

# Check if OAUTH_REDIRECT_URI already exists
echo ""
echo "2. Checking .env configuration..."
if grep -q "OAUTH_REDIRECT_URI" .env 2>/dev/null; then
    echo "✓ OAUTH_REDIRECT_URI already exists in .env"
    echo "Current value:"
    grep "OAUTH_REDIRECT_URI" .env
    echo ""
    echo "Update it? (yes/no)"
    read UPDATE_URI
    if [ "$UPDATE_URI" = "yes" ]; then
        sed -i.bak 's|OAUTH_REDIRECT_URI=.*|OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback|' .env
        echo "✓ Updated OAUTH_REDIRECT_URI"
    fi
else
    echo "Adding OAUTH_REDIRECT_URI to .env..."
    echo "" >> .env
    echo "# OAuth Redirect URI for Production" >> .env
    echo "OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback" >> .env
    echo "✓ Added OAUTH_REDIRECT_URI"
fi

# Delete old token and credentials
echo ""
echo "3. Removing old token and credentials files..."
if [ -f token.pickle ]; then
    rm token.pickle
    echo "✓ Deleted token.pickle"
else
    echo "  No token.pickle found (OK)"
fi

if [ -f credentials.json ]; then
    rm credentials.json
    echo "✓ Deleted credentials.json"
else
    echo "  No credentials.json found (OK)"
fi

# Restart the service
echo ""
echo "4. Restarting application..."
if systemctl is-active --quiet backup-daemon 2>/dev/null; then
    echo "Restarting backup-daemon service..."
    sudo systemctl restart backup-daemon
    echo "✓ Service restarted"
    echo ""
    echo "Checking service status..."
    sudo systemctl status backup-daemon --no-pager -l
elif pgrep -f "app.py" > /dev/null; then
    echo "Found running app.py process"
    echo "You may need to manually restart it:"
    echo "  pkill -f app.py && nohup python3 app.py &"
else
    echo "⚠️  No running service detected"
    echo "Start your app manually:"
    echo "  python3 app.py"
fi

echo ""
echo "=================================================="
echo "Configuration Updated!"
echo "=================================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. ⚠️  IMPORTANT: Update Google Cloud Console"
echo "   https://console.cloud.google.com/apis/credentials"
echo ""
echo "   Add this to 'Authorized redirect URIs':"
echo "   https://backup.hofkensvermeulen.be/oauth2callback"
echo ""
echo "2. Test OAuth flow:"
echo "   https://backup.hofkensvermeulen.be"
echo ""
echo "3. Login and click 'Connect Google Account'"
echo ""
echo "4. Verify redirect goes to your domain (not localhost)"
echo ""
echo "=================================================="
