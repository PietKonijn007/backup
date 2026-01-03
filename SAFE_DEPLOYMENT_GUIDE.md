# Safe Production Deployment Guide

## Deploying Photos Removal Without Interrupting Backup

This guide shows how to safely deploy the Google Photos removal changes to your AWS production environment without interrupting the currently running Google Drive backup process.

## Strategy Overview

The backup daemon will need a restart, but we can do this safely:
1. **Graceful restart**: systemd can restart the service without killing in-progress file transfers
2. **Queue preservation**: The SQLite database maintains sync state across restarts
3. **Timing**: Deploy during low-activity period if possible

## Step-by-Step Deployment

### Step 1: Commit Changes Locally

```bash
# Navigate to your project directory
cd /Users/jurgenhofkens/Documents/Code/backup

# Check what files changed
git status

# Add all changes
git add -A

# Commit with descriptive message
git commit -m "Remove Google Photos functionality due to API deprecation

- Removed photoslibrary.readonly OAuth scope
- Removed /api/photos/* endpoints
- Marked photos modules as deprecated
- Updated navigation to remove Photos links
- Updated documentation and specs

Reason: Google deprecated Photos Library API on March 31, 2025.
The new Photos Picker API does not support automated backup.
See GOOGLE_PHOTOS_API_DEPRECATION.md for details."

# Push to GitHub
git push origin main
```

### Step 2: Check Current Backup Status

Before deploying, check if any critical backup is in progress:

```bash
# SSH into your EC2 instance
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip

# Check daemon status
sudo systemctl status backup-daemon

# Check recent logs for active transfers
sudo journalctl -u backup-daemon -n 50 | grep -i "downloading\|uploading\|syncing"

# Check sync queue (if empty, safe to restart)
curl http://localhost:8080/api/status | jq
```

### Step 3: Deploy to Production

**Option A: Graceful Deployment (Recommended)**

This allows in-progress transfers to complete:

```bash
# SSH to EC2
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip

# Navigate to app directory
cd /opt/backup-app

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install any new dependencies (there aren't any, but good practice)
pip install -r requirements.txt

# Graceful restart - waits for current operations
sudo systemctl reload-or-restart backup-daemon

# Verify it restarted successfully
sudo systemctl status backup-daemon

# Check logs
sudo journalctl -u backup-daemon -f
```

**Option B: Wait for Idle State (Safest)**

If you want zero interruption:

```bash
# SSH to EC2
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip

# Check if daemon is idle
curl http://localhost:8080/api/status | jq '.daemon.current_operation'

# Wait until it shows null or "idle"

# Then pause the daemon
curl -X POST http://localhost:8080/api/sync/pause

# Pull changes
cd /opt/backup-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# Restart daemon
sudo systemctl restart backup-daemon

# Resume operations
curl -X POST http://localhost:8080/api/sync/resume
```

### Step 4: Delete Old Token (Important!)

The old token has the deprecated Photos scope. Delete it so a new one will be generated with only Drive scope:

```bash
# On EC2
cd /opt/backup-app

# Backup the old token (optional)
cp token.pickle token.pickle.backup

# Delete the token
rm token.pickle

# Restart to trigger re-authentication
sudo systemctl restart backup-daemon
```

### Step 5: Re-authenticate

```bash
# Open your browser
# Navigate to: https://backup.hofkensvermeulen.be/login
# Or: http://your-ec2-ip:8080/login

# Click "Connect Google Account"
# Grant permissions (only Drive access will be requested now)
# Should redirect back to settings page showing "Connected"
```

### Step 6: Verify Deployment

```bash
# Check daemon is running
sudo systemctl status backup-daemon

# Check logs for errors
sudo journalctl -u backup-daemon -n 100

# Test Drive API (should work)
curl http://localhost:8080/api/drive/tree | jq

# Test Photos API (should return deprecation message)
curl http://localhost:8080/api/photos/albums | jq
# Expected: 404 or error about removed endpoint

# Check dashboard loads correctly
curl -I http://localhost:8080/
# Should return 200 OK
```

## Impact Assessment

### What Will NOT Be Interrupted

✅ **Google Drive sync** - Continues normally
✅ **S3 uploads** - Resume from where they left off
✅ **Sync queue** - Preserved in SQLite database
✅ **File tracking** - All sync state maintained

### What Will Happen During Restart

⚠️ **Brief unavailability** (5-10 seconds):
- Web dashboard unavailable during restart
- API endpoints unavailable during restart

⚠️ **In-progress transfers**:
- Current file download/upload may be interrupted
- Will automatically retry on restart (built-in retry logic)
- No data loss - partial files are discarded and re-attempted

### Minimal Downtime Approach

To minimize downtime to ~2 seconds:

```bash
# Prepare everything first
cd /opt/backup-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# Quick restart
sudo systemctl restart backup-daemon && echo "Restarted at $(date)"

# Immediately check status
sleep 3 && curl http://localhost:8080/api/health
```

## Rollback Plan (If Something Goes Wrong)

If issues occur, you can quickly rollback:

```bash
# On EC2
cd /opt/backup-app

# Revert to previous commit
git log --oneline -5  # Find previous commit hash
git checkout <previous-commit-hash>

# Restart with old code
sudo systemctl restart backup-daemon

# Restore old token if needed
cp token.pickle.backup token.pickle
```

## Post-Deployment Checklist

- [ ] Daemon is running: `sudo systemctl status backup-daemon`
- [ ] No errors in logs: `sudo journalctl -u backup-daemon -n 50`
- [ ] Dashboard loads: Open in browser
- [ ] Google Drive API works: Check /files page
- [ ] No Photos links visible: Check navigation menu
- [ ] Drive sync resumes: Check dashboard status
- [ ] Files are being synced: Monitor logs

## Monitoring After Deployment

```bash
# Monitor logs in real-time
sudo journalctl -u backup-daemon -f

# Check resource usage
htop

# Verify sync is working
watch -n 5 'curl -s http://localhost:8080/api/status | jq ".daemon.stats"'
```

## Troubleshooting

### Issue: Daemon won't start

```bash
# Check detailed error
sudo journalctl -u backup-daemon -n 100 --no-pager

# Check Python errors
cd /opt/backup-app
source venv/bin/activate
python app.py  # Run manually to see errors
```

### Issue: Import errors

```bash
# Reinstall dependencies
cd /opt/backup-app
source venv/bin/activate
pip install -r requirements.txt --upgrade --force-reinstall
```

### Issue: Old Photos pages still accessible

```bash
# Clear any caching
sudo systemctl restart backup-daemon

# Force browser cache clear (Ctrl+Shift+R)
```

## Best Time to Deploy

Consider deploying during:
- ✅ Low backup activity (check dashboard)
- ✅ Off-peak hours (if users access dashboard)
- ✅ After completing a large file sync (check logs)
- ❌ Avoid during: Large file transfers, business hours

## Expected Behavior After Deployment

1. **Navigation**: No "Photos" link in menu
2. **Dashboard**: No "Browse Photos" button
3. **Settings**: Only Google Drive in sync config
4. **OAuth**: Only Drive scope requested during login
5. **Logs**: No Photos-related messages
6. **Sync**: Drive backup continues normally

---

## Quick Deployment Commands (Copy-Paste)

```bash
# Local: Commit and push
git add -A
git commit -m "Remove Google Photos functionality (API deprecated)"
git push origin main

# EC2: Pull and restart
ssh -i ~/.ssh/your-key.pem ubuntu@your-ec2-ip
cd /opt/backup-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
rm token.pickle
sudo systemctl restart backup-daemon
sudo journalctl -u backup-daemon -f
```

Then re-authenticate via browser at: http://your-ec2-ip:8080/login

---

**Total downtime**: 5-10 seconds for restart
**Risk level**: Low (Drive backup unaffected)
**Rollback time**: <1 minute if needed
