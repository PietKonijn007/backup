# Automated Sync System Setup Guide

This guide covers the setup and usage of the automated Google Drive to S3 backup system with 24/7 continuous monitoring.

## Overview

The automated sync system consists of:
- **Background Daemon**: Continuously monitors Google Drive for changes
- **Web Dashboard**: Real-time control and monitoring interface
- **systemd Service**: Runs daemon as a system service (optional)
- **API Endpoints**: Programmatic control of sync operations

## Features

✅ **Continuous Monitoring**: Automatically checks for new/modified files every 5 minutes (configurable)
✅ **Smart Syncing**: Only syncs new or modified files (no duplicates)
✅ **Start/Stop/Pause Controls**: Full control via web dashboard
✅ **Real-time Statistics**: Live updates of sync progress and status
✅ **Error Handling**: Automatic retries with exponential backoff
✅ **Database Tracking**: SQLite database tracks all sync operations

## Quick Start

### 1. Basic Setup

```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Initialize the database
python init_user.py

# Configure your sync settings
nano config.yaml
```

### 2. Configuration

Edit `config.yaml` to customize sync behavior:

```yaml
sync:
  mode: realtime
  auto_start: true              # Auto-start daemon on app launch
  interval_seconds: 300         # Check for changes every 5 minutes
  check_recent_days: 7          # Check files modified in last 7 days
  batch_size: 100               # Max files per sync batch
  retry_attempts: 5             # Retry failed syncs
  retry_delay_seconds: 30       # Delay between retries
  max_file_size_gb: 50          # Skip files larger than this
  temp_dir: /tmp/backup-sync    # Temporary download location
```

### 3. Start the Application

```bash
# Development mode
python app.py

# Or with specific host/port
FLASK_ENV=development python app.py
```

The application will:
1. Start the Flask web server on port 8080
2. Auto-start the sync daemon (if `auto_start: true`)
3. Begin monitoring Google Drive for changes

### 4. Access the Dashboard

Open your browser to: `http://localhost:8080`

1. **Login** with your credentials
2. **Connect Google Account** (Settings → Connect to Google)
3. **Monitor Sync Status** on Dashboard
4. Use **Start/Stop/Pause buttons** to control syncing

## Dashboard Controls

### Daemon Status

The dashboard shows real-time daemon status:
- **🟢 Running**: Actively syncing files
- **🟡 Paused**: Daemon running but not syncing
- **⚪ Stopped**: Daemon not running

### Control Buttons

- **Start**: Begin automatic syncing
- **Pause**: Temporarily stop syncing (keeps daemon running)
- **Resume**: Continue syncing after pause
- **Stop**: Completely stop the daemon

### Statistics

Real-time metrics displayed:
- **Files Synced**: Total successful syncs
- **Failed**: Number of failed sync attempts
- **Total Size**: Combined size of synced files
- **Uptime**: How long daemon has been running

## Running as a System Service (Production)

For 24/7 automated operation, install as a systemd service:

### 1. Configure the Service

Edit `systemd/backup-daemon.service`:

```bash
# Replace these values
User=YOUR_USERNAME
Group=YOUR_GROUP
WorkingDirectory=/path/to/backup
EnvironmentFile=/path/to/backup/.env
ExecStart=/usr/bin/python3 /path/to/backup/app.py
```

### 2. Install the Service

```bash
# Copy service file
sudo cp systemd/backup-daemon.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable backup-daemon

# Start service
sudo systemctl start backup-daemon
```

### 3. Manage the Service

```bash
# Check status
sudo systemctl status backup-daemon

# View logs
sudo journalctl -u backup-daemon -f

# Restart service
sudo systemctl restart backup-daemon

# Stop service
sudo systemctl stop backup-daemon
```

## API Endpoints

Control the daemon programmatically:

### Check Status
```bash
curl -X GET http://localhost:8080/api/status \
  -H "Cookie: session=YOUR_SESSION"
```

### Start Daemon
```bash
curl -X POST http://localhost:8080/api/sync/start \
  -H "Cookie: session=YOUR_SESSION"
```

### Stop Daemon
```bash
curl -X POST http://localhost:8080/api/sync/stop \
  -H "Cookie: session=YOUR_SESSION"
```

### Pause Daemon
```bash
curl -X POST http://localhost:8080/api/sync/pause \
  -H "Cookie: session=YOUR_SESSION"
```

### Resume Daemon
```bash
curl -X POST http://localhost:8080/api/sync/resume \
  -H "Cookie: session=YOUR_SESSION"
```

### Health Check
```bash
curl -X GET http://localhost:8080/api/health
```

## How It Works

### Sync Process

1. **Monitoring**: Every N minutes (default: 5), daemon checks Google Drive
2. **Detection**: Identifies files modified in last N days (default: 7)
3. **Filtering**: Compares with database to find new/modified files
4. **Syncing**: Downloads from Google Drive → Uploads to S3 via rclone
5. **Tracking**: Updates database with sync status
6. **Repeat**: Waits for next interval and repeats

### Database Tracking

The system uses SQLite to track:
- **File metadata**: ID, name, size, modified time
- **Sync status**: pending, synced, failed
- **Sync logs**: All sync operations with timestamps
- **Daemon state**: Current daemon status

Database location: `sync_state.db`

### Error Handling

- **Automatic Retries**: Failed syncs retry up to 5 times
- **Exponential Backoff**: Delays increase between retries
- **Error Tracking**: Last error displayed on dashboard
- **Graceful Recovery**: Daemon continues on errors

## Troubleshooting

### Daemon Won't Start

1. Check if Google OAuth is connected:
   - Go to Settings → Connect to Google
   
2. Verify rclone configuration:
   ```bash
   rclone listremotes
   # Should show: aws-s3
   ```

3. Check logs:
   ```bash
   tail -f logs/backup-app.log
   ```

### Files Not Syncing

1. Verify Google Drive authentication:
   - Go to Settings → Test Connection
   
2. Check file modification dates:
   - Only files modified in last 7 days are synced
   - Adjust `check_recent_days` in config.yaml

3. Check sync status in database:
   ```bash
   sqlite3 sync_state.db "SELECT * FROM files WHERE sync_status='failed';"
   ```

### High Memory Usage

Reduce batch size in config.yaml:
```yaml
sync:
  batch_size: 50  # Reduce from 100
```

### Slow Syncing

1. Increase sync interval (check less frequently):
   ```yaml
   sync:
     interval_seconds: 600  # 10 minutes instead of 5
   ```

2. Reduce file lookback period:
   ```yaml
   sync:
     check_recent_days: 3  # 3 days instead of 7
   ```

## Advanced Configuration

### Custom Sync Schedule

Modify the sync interval for different schedules:

```yaml
# Every 1 minute (aggressive)
interval_seconds: 60

# Every 15 minutes (balanced)
interval_seconds: 900

# Every hour (conservative)
interval_seconds: 3600

# Every 6 hours (minimal)
interval_seconds: 21600
```

### Exclude Patterns

Configure file exclusions in config.yaml:

```yaml
sources:
  google_drive:
    exclude_patterns: 
      - '*.tmp'
      - '.DS_Store'
      - '~$*'
      - '*.log'
      - 'Thumbs.db'
```

### Multiple Destinations

Sync to both AWS S3 and Scaleway:

```yaml
destinations:
  aws_s3:
    enabled: true
    bucket: my-backup
    
  eu_provider:
    enabled: true
    type: scaleway
    bucket: my-backup-eu
```

## Monitoring & Maintenance

### Regular Checks

1. **Dashboard**: Check sync status daily
2. **Logs**: Review logs for errors
3. **Database**: Monitor database size
4. **Storage**: Check S3 bucket usage

### Database Maintenance

```bash
# View sync statistics
sqlite3 sync_state.db "SELECT 
  COUNT(*) as total_files,
  SUM(CASE WHEN sync_status='synced' THEN 1 ELSE 0 END) as synced,
  SUM(CASE WHEN sync_status='failed' THEN 1 ELSE 0 END) as failed
FROM files;"

# Clean old logs (older than 30 days)
sqlite3 sync_state.db "DELETE FROM sync_logs 
WHERE timestamp < datetime('now', '-30 days');"

# Vacuum database to reclaim space
sqlite3 sync_state.db "VACUUM;"
```

### Log Rotation

If using systemd, logs are automatically managed by journald. For manual logging:

```bash
# Add to crontab for weekly log rotation
0 0 * * 0 find /var/log/backup-daemon -name "*.log" -mtime +7 -delete
```

## Security Best Practices

1. **Never commit credentials**: Keep `.env` file secure
2. **Use strong passwords**: For web dashboard access
3. **Enable HTTPS**: In production environments
4. **Restrict access**: Firewall rules for port 8080
5. **Regular updates**: Keep dependencies up to date

## Next Steps

- ✅ Automated sync is now working!
- 📊 Add Chart.js visualizations (Phase 2 enhancement)
- 📧 Set up email notifications (Phase 3 enhancement)
- 📄 Implement Google Workspace export (Phase 1 enhancement)
- 🇪🇺 Add Scaleway integration (Phase 1 enhancement)

## Support

For issues or questions:
1. Check logs: `tail -f logs/backup-app.log`
2. Review this documentation
3. Check GitHub issues
4. Contact system administrator

---

**Congratulations!** Your automated backup system is ready for 24/7 operation. 🎉
