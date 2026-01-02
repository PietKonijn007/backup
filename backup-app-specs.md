# Backup Application Specification

## 1. Overview

### Purpose
A robust backup and synchronization application that automatically syncs files and photos from Google services (Google Drive and Google Photos) to multiple cloud storage providers for redundancy and geographic distribution.

### Goals
- Automated backup of Google Drive files and Google Photos
- Multi-cloud redundancy (AWS S3 + European cloud provider)
- Reliable synchronization with conflict resolution
- Cost-effective storage management
- Easy recovery and restoration capabilities

## 2. Data Sources

### 2.1 Google Drive
- **Content**: All files and folders in user's Google Drive
- **File Types**: Documents, spreadsheets, presentations, PDFs, images, videos, and other files
- **Metadata**: File names, paths, modification dates, permissions
- **Special Considerations**: 
  - Google Workspace files (Docs, Sheets, Slides) need export to standard formats
  - Handle shared files and folders appropriately

**Google Workspace Format Exports**:
| Google Format | Export Format | MIME Type | Extension |
|--------------|---------------|-----------|-----------|
| Google Docs | Microsoft Word | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | .docx |
| Google Sheets | Microsoft Excel | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | .xlsx |
| Google Slides | Microsoft PowerPoint | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | .pptx |
| Google Drawings | PDF | `application/pdf` | .pdf |
| Google Forms | JSON | `application/json` | .json |
| Google Apps Script | JSON | `application/vnd.google-apps.script+json` | .json |

**Export Rationale**: Microsoft Office formats provide the best compatibility for offline viewing, editing, and long-term archival across different platforms and applications.

### 2.2 Google Photos
- **Content**: All photos and videos in user's library
- **Organization**: Albums, metadata, EXIF data
- **Original Quality**: Download original quality files (not compressed versions)
- **Metadata Preservation**: Dates, locations, descriptions, tags

## 3. Destination Storage

### 3.1 AWS S3
- **Bucket Configuration**: Private bucket with versioning enabled
- **Storage Class**: Intelligent-Tiering for cost optimization
- **Structure**: Organized folder hierarchy mirroring sources
- **Lifecycle Policies**: Archive older versions to Glacier after defined period

### 3.2 European Cloud Provider
**Options to Consider**:
- **OVHcloud (France)**: S3-compatible object storage
- **Scaleway (France)**: Object Storage with S3 compatibility
- **Hetzner (Germany)**: Storage Box or Object Storage
- **Exoscale (Switzerland)**: S3-compatible object storage

**Requirements**:
- GDPR compliant
- S3-compatible API (preferred for consistency)
- Geographic location within EU
- Competitive pricing
- Reliable uptime SLA

## 4. Synchronization Strategy

### 4.1 Sync Modes
- **Full Sync**: Initial complete backup of all files
- **Real-Time Sync**: Continuous monitoring and sync using RSYNC
- **Unidirectional Only**: One-way sync (Google sources → backup providers) to prevent accidental data loss

### 4.2 Streaming Sync Strategy for Large Datasets (4TB)
- **No Full Local Mirror**: Only 100GB temporary cache, not full 4TB
- **File-by-File Processing**: Download → Upload → Delete → Next file
- **rclone for Cloud Storage**: Better than traditional rsync for S3-compatible storage
- **Background Process**: Python daemon running continuously via systemd
- **Queue-Based**: Failed files queued for retry with exponential backoff
- **Manual Trigger**: Force immediate full sync or pause/resume via web UI

### 4.3 Streaming Sync Flow
1. **Discovery Phase**:
   - Query Google Drive/Photos API for all files (paginated)
   - Compare with SQLite sync state database
   - Identify new/modified/deleted files
   - Build sync queue

2. **Download Phase**:
   - Download file from Google to EC2 temp storage
   - For Google Workspace files: export to Microsoft Office formats
   - Verify file integrity (checksum)
   - Mark as downloaded in database

3. **Upload Phase**:
   - Upload file to S3 using rclone (parallel)
   - Upload same file to Scaleway using rclone (parallel)
   - Verify uploads with checksums
   - Mark as synced in database

4. **Cleanup Phase**:
   - Delete file from EC2 temp storage
   - Free up space for next file
   - Update sync statistics

5. **Monitoring**:
   - Progress broadcast via SSE to web dashboard
   - Log all operations
   - Alert on failures

**Retry Logic**:
- Max 5 attempts per file with exponential backoff
- Failed files moved to retry queue
- Alert after final failure
- Manual retry option in UI

### 4.4 Conflict Resolution
- **No Conflicts**: One-way sync eliminates conflicts
- **Versioning**: Keep multiple versions in destination
- **Deletion Handling**: Soft delete (move to .trash folder) before permanent deletion
- **Logging**: Record all sync operations for audit trail

## 5. Technical Architecture

### 5.1 Components - Streaming Architecture

```
┌─────────────────────────────┐
│  Google Drive (4TB)         │
│  Google Photos              │
│  - Docs → .docx export      │
│  - Sheets → .xlsx export    │
│  - Slides → .pptx export    │
└──────────┬──────────────────┘
           │ Google API
           │ (paginated download)
           ▼
┌─────────────────────────────────────┐
│  AWS EC2 (us-east-1)                │
│  ┌───────────────────────────────┐  │
│  │ Python Sync Daemon            │  │
│  │ - Google OAuth 2.0            │  │
│  │ - Download file by file       │  │
│  │ - 100GB temp cache (EBS)      │  │
│  │ - rclone parallel upload      │  │
│  │ - Delete after confirm        │  │
│  │ - Retry queue (5 attempts)    │  │
│  │ - SQLite sync state           │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ Flask Web App                 │  │
│  │ - REST API                    │  │
│  │ - Bootstrap UI                │  │
│  │ - Session auth                │  │
│  │ - SSE for live logs           │  │
│  └───────────────────────────────┘  │
└──────────┬──────────────────────────┘
           │ rclone sync
      ┌────┴─────────┐
      ▼              ▼
┌──────────────┐  ┌────────────────────┐
│  AWS S3      │  │ Scaleway (France)  │
│  us-east-1   │  │ Object Storage     │
│  4TB Storage │  │ 4TB Storage        │
│  Versioning  │  │ S3-compatible      │
└──────────────┘  └────────────────────┘
      ▲
      │ HTTPS
      │
┌─────┴────────────┐
│  User Browser    │
│  - Login page    │
│  - Dashboard     │
│  - File browser  │
│  - Live logs     │
└──────────────────┘
```

**Key Architectural Features**:
- **Streaming**: Files downloaded one-by-one, uploaded immediately, then deleted
- **No Local Mirror**: Only temporary cache (100GB), not full 4TB
- **Parallel Upload**: Simultaneous upload to S3 and Scaleway
- **Retry Mechanism**: Failed files queued for retry with exponential backoff
- **Progress Tracking**: Real-time status updates via SSE to browser

### 5.2 Technology Stack

**Backend (Sync Daemon)**:
- **Language**: Python 3.11+
- **Web Framework**: Flask 3.x for API and serving frontend
- **Google APIs**: google-api-python-client (official SDK)
- **Sync Tool**: rclone (S3-compatible, better than rsync for cloud)
- **Database**: SQLite3 for sync state and metadata
- **Process Manager**: systemd for auto-restart on EC2
- **Authentication**: Flask-Login for session management
- **Retry Logic**: tenacity library for exponential backoff

**Frontend (Web Dashboard)**:
- **UI Framework**: Bootstrap 5.3 (CSS framework)
- **JavaScript**: Vanilla JavaScript (no framework needed)
- **Charts**: Chart.js for metrics visualization
- **Real-time Updates**: Server-Sent Events (SSE) for live logs
- **Hosting**: Served directly from Flask app (no separate hosting)

**Infrastructure**:
- **Compute**: AWS EC2 t3.small in us-east-1
- **Storage**: 100GB gp3 EBS volume (temporary cache)
- **S3 Bucket**: us-east-1 (same region as EC2)
- **EU Storage**: Scaleway Object Storage (France)
- **Database**: SQLite on EC2 (single-user, no need for PostgreSQL)
- **Networking**: Elastic IP for consistent access

### 5.3 Deployment Architecture - AWS Cloud-Based

**Primary Infrastructure**:
- **EC2 Instance**: t3.small (2 vCPU, 2GB RAM) in us-east-1
- **Storage**: 100GB gp3 EBS for temporary sync cache (~$8/month)
- **Estimated Cost**: ~$15/month for compute + $8/month for storage

**Architecture**:
- **Daemon**: Background service running 24/7 on EC2 (systemd managed)
- **Web Dashboard**: Served directly from Flask application on port 80/443
- **Database**: SQLite on EC2 for sync state tracking
- **API**: RESTful API with session-based authentication
- **Monitoring**: CloudWatch logs (optional)

**Why Cloud-Based**:
- No local storage needed (4TB would be expensive)
- Streaming architecture: Download from Google → immediate upload to S3/EU → delete temp files
- Always-on reliability without maintaining local hardware
- Low latency to S3 (same AWS region)
- IAM role integration (no credential storage needed for S3)

## 6. Features

### 6.1 Backend Daemon Features
- [ ] OAuth authentication with Google services
- [ ] Continuous sync Google Drive to local directory
- [ ] Continuous sync Google Photos to local directory
- [ ] Real-time file system monitoring (inotify/fswatch)
- [ ] RSYNC to AWS S3 on file changes
- [ ] RSYNC to EU provider on file changes
- [ ] Background daemon with auto-restart
- [ ] Track sync state and progress in SQLite
- [ ] Deduplication (avoid storing duplicates)
- [ ] Checksum verification (RSYNC --checksum)
- [ ] Queue management for sync operations
- [ ] RESTful API for dashboard communication
- [ ] Structured logging with rotation

### 6.2 Web Dashboard Features
- [ ] **Home/Overview**:
  - Current sync status (active/idle/error)
  - Last sync time for each source
  - Total files and storage used
  - Real-time sync progress
  
- [ ] **File Browser**:
  - Browse backed-up files
  - Search functionality
  - File details and metadata
  - Preview capability
  
- [ ] **Sync Management**:
  - Start/stop sync daemon
  - Force immediate full sync
  - Pause/resume individual sources
  - Configure sync settings
  
- [ ] **Monitoring**:
  - Live sync logs
  - Activity timeline
  - Success/failure rates
  - Bandwidth usage graphs
  - Storage usage per provider
  
- [ ] **Configuration**:
  - Add/remove Google accounts
  - Configure backup destinations
  - Set exclusion rules
  - Notification settings
  
- [ ] **Alerts & Notifications**:
  - Error notifications
  - Email alerts
  - Webhook integration

### 6.3 Advanced Features (Future)
- [ ] Client-side encryption before RSYNC
- [ ] Bandwidth throttling
- [ ] Selective sync (exclude folders/file types)
- [ ] Multi-user support
- [ ] Restore functionality (download from backup)
- [ ] Dry-run mode for testing
- [ ] Scheduled sync policies
- [ ] Mobile app for monitoring

## 7. Security & Privacy

### 7.1 Authentication
- **Google**: OAuth 2.0 with appropriate scopes
- **AWS**: IAM credentials or roles
- **EU Provider**: API keys or S3-compatible credentials
- **Credential Storage**: Secure storage (keyring, environment variables, secrets manager)

### 7.2 Data Protection
- **Encryption in Transit**: TLS/HTTPS for all transfers
- **Encryption at Rest**: Server-side encryption (SSE) on S3 and EU storage
- **Optional Client-Side Encryption**: Encrypt before upload for additional security
- **Access Control**: Restrict bucket access, enable MFA delete on S3

### 7.3 Compliance
- GDPR compliance for EU data storage
- Data residency requirements
- Right to be forgotten (deletion capability)

## 8. Error Handling & Reliability

### 8.1 Error Scenarios
- Network interruptions
- API rate limits (Google, AWS)
- Storage quota exceeded
- Authentication failures
- File access permission errors
- Corrupted file transfers

### 8.2 Handling Strategy
- Exponential backoff for retries
- Circuit breaker pattern for failing services
- Graceful degradation (continue with available services)
- Comprehensive error logging
- Alert on critical failures

## 9. Monitoring & Logging

### 9.1 Metrics to Track
- Files synced (count, size)
- Sync duration
- Success/failure rates
- Storage usage per provider
- API quota usage
- Bandwidth consumed
- Cost per sync operation

### 9.2 Logging
- Structured logs (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Rotation and retention policies
- Centralized logging (optional)

### 9.3 Notifications
- Email alerts on failures
- Daily/weekly summary reports
- Slack/Discord webhook integration (optional)

## 10. Configuration

### 10.1 Configuration File Format
```yaml
sources:
  google_drive:
    enabled: true
    local_path: /sync/google-drive
    exclude_paths: []
    exclude_patterns: ['*.tmp', '.DS_Store']
    
  google_photos:
    enabled: true
    local_path: /sync/google-photos
    organize_by_date: true  # YYYY/MM/DD structure
    
destinations:
  aws_s3:
    enabled: true
    bucket: my-backup-bucket
    region: us-east-1
    storage_class: INTELLIGENT_TIERING
    rsync_options: '--archive --compress --checksum --delete'
    
  eu_provider:
    enabled: true
    type: scaleway  # ovh, hetzner, exoscale, etc.
    bucket: my-backup-bucket-eu
    region: fr-par
    endpoint: s3.fr-par.scw.cloud
    rsync_options: '--archive --compress --checksum --delete'
    
sync:
  mode: realtime  # realtime or manual
  watch_delay_seconds: 5  # Debounce file changes
  batch_size: 100  # Files to sync in one batch
  retry_attempts: 3
  retry_delay_seconds: 60
  
daemon:
  api_port: 8080
  api_host: 0.0.0.0
  api_key: your-secure-api-key-here
  log_level: INFO
  log_file: /var/log/backup-daemon.log
  pid_file: /var/run/backup-daemon.pid
  
security:
  api_authentication: true
  cors_origins: ['https://your-dashboard.vercel.app']
  ssl_verify: true
  
notifications:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    from: backup@example.com
    to: user@example.com
    on_error: true
    daily_summary: true
  webhook:
    enabled: false
    url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 10.2 Environment Variables
```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REFRESH_TOKEN=your-refresh-token

# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# EU Provider Credentials
EU_PROVIDER_ACCESS_KEY=your-eu-access-key
EU_PROVIDER_SECRET_KEY=your-eu-secret-key

# API Security
API_SECRET_KEY=your-jwt-secret-key

# Database
DATABASE_URL=sqlite:///sync_state.db
```

## 11. Cost Considerations (for 4TB Backup)

### 11.1 Google API Costs
- **Google Drive API**: Free tier (generous limits)
- **Google Photos API**: Free tier (sufficient for this use case)

### 11.2 Compute Costs (AWS EC2)
- **EC2 t3.small**: ~$15/month (us-east-1)
- **EBS 100GB gp3**: ~$8/month
- **Elastic IP**: $0 (while attached to running instance)
- **Subtotal**: ~$23/month

### 11.3 Storage Costs (4TB)
- **AWS S3 Intelligent-Tiering**: 
  - 4,096 GB × $0.023/GB = ~$94/month
  - First 50TB: $0.023/GB
- **Scaleway Object Storage (France)**:
  - 4,096 GB × €0.01/GB = ~€41/month (~$43 USD)
- **Subtotal**: ~$137/month for 4TB × 2 (redundancy)

### 11.4 Transfer Costs
- **Download from Google → EC2**: Free
- **Upload EC2 → S3 (same region)**: Free
- **Upload EC2 → Scaleway**: Free (incoming)
- **Data Transfer OUT from EC2**: $0 (to S3 same region)

### 11.5 API Request Costs (estimated for 4TB initial sync)
Assuming 1 million files across 4TB:
- **S3 PUT requests**: 1M requests × $0.005/1K = ~$5 one-time
- **S3 GET requests**: Minimal for monitoring
- **Ongoing**: <$1/month for incremental updates

### 11.6 Total Monthly Cost Breakdown
| Item | Cost |
|------|------|
| EC2 t3.small | $15 |
| EBS 100GB | $8 |
| AWS S3 (4TB) | $94 |
| Scaleway (4TB) | $43 |
| API Requests | <$1 |
| **Total** | **~$161/month** |

**One-time setup**: ~$5 for initial S3 uploads

**Cost optimization tips**:
- After initial sync, could downgrade to t3.micro (~$7/month) if changes are minimal
- Use S3 Glacier for older versions (move after 90 days) to reduce to $0.004/GB
- Monitor and optimize transfer patterns

## 12. Roadmap

### Phase 1: MVP - Core Sync Engine (Week 1-2)
- [ ] Project scaffolding (Flask app structure)
- [ ] Google OAuth 2.0 authentication
- [ ] Google Drive API integration with pagination
- [ ] Google Photos API integration
- [ ] Google Workspace file export (to .docx, .xlsx, .pptx)
- [ ] SQLite database schema and models
- [ ] Streaming sync logic (download → upload → delete)
- [ ] rclone integration for S3
- [ ] rclone integration for Scaleway
- [ ] Basic retry logic with exponential backoff
- [ ] Structured logging to file

### Phase 2: Web Dashboard (Week 3)
- [ ] Flask routes and API endpoints
- [ ] Bootstrap 5 base template
- [ ] Login page with session management
- [ ] Dashboard/home page with sync status
- [ ] Server-Sent Events (SSE) for live log streaming
- [ ] Sync controls (start/stop/force sync buttons)
- [ ] Basic file browser (list files)
- [ ] Chart.js integration for metrics
- [ ] Settings page for configuration

### Phase 3: Deployment & Reliability (Week 4)
- [ ] AWS deployment script (deploy.sh)
- [ ] EC2 instance setup automation (setup-instance.sh)
- [ ] systemd service configuration
- [ ] Nginx reverse proxy setup (optional)
- [ ] SSL certificate with Let's Encrypt (optional)
- [ ] CloudWatch logging integration
- [ ] Health check endpoint
- [ ] Error alerting via email
- [ ] Comprehensive error handling

### Phase 4: Enhanced Features (Week 5-6)
- [ ] Advanced file browser with search
- [ ] File metadata display
- [ ] Storage usage charts per provider
- [ ] Bandwidth usage tracking
- [ ] Sync history timeline
- [ ] Manual retry for failed files
- [ ] Webhook notifications
- [ ] Configuration editing via UI
- [ ] Unit and integration tests

### Phase 5: Polish & Optimization (Week 7+)
- [ ] Mobile-responsive improvements
- [ ] Performance optimization
- [ ] Reduce EC2 instance size if possible
- [ ] S3 Glacier archival policies
- [ ] Backup verification tools
- [ ] Cost tracking dashboard
- [ ] User documentation
- [ ] Deployment guide
- [ ] Troubleshooting FAQ

### Future Enhancements
- [ ] Client-side encryption before upload
- [ ] Restore/download functionality
- [ ] Selective sync rules (exclude patterns)
- [ ] Bandwidth throttling
- [ ] Multi-account support
- [ ] Scheduled sync policies
- [ ] Mobile app for monitoring

## 13. Implementation Considerations

### 13.1 RSYNC Strategy
**For S3 (using rclone or aws s3 sync)**:
```bash
rclone sync /sync/google-drive remote-s3:my-backup-bucket/google-drive \
  --checksum --fast-list --transfers 4 --log-file sync.log
```

**For EU Provider (using rclone)**:
```bash
rclone sync /sync/google-drive remote-eu:my-backup-bucket-eu/google-drive \
  --checksum --fast-list --transfers 4 --log-file sync.log
```

**Why rclone over traditional rsync**:
- Native S3 support without mounting
- Better performance for cloud storage
- Built-in retry and error handling
- Progress tracking
- Bandwidth limiting
- Multiple cloud provider support

### 13.2 Challenges
- Google API rate limits (need to handle pagination and throttling)
- Large file transfers (rclone handles chunking automatically)
- Metadata preservation (store in sidecar files or database)
- Google Workspace file format conversions (export to PDF/DOCX)
- Always-on daemon (need reliable host)
- Dashboard-to-daemon communication (API security)
- Real-time monitoring (WebSocket connection management)

### 13.3 Best Practices
- Use official Google SDKs for API access
- Implement comprehensive error handling and retries
- Store sync state in SQLite with transaction safety
- Use rclone with --checksum for integrity verification
- Test with small dataset first
- Monitor costs regularly (S3 API calls, storage)
- Secure API with JWT or API keys
- Rate limit API endpoints
- Implement proper logging with rotation
- Use systemd for daemon reliability (auto-restart)
- Document all configuration options
- Provide health check endpoint for monitoring

### 13.4 File System Watching
**Python (watchdog)**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SyncHandler(FileSystemEventHandler):
    def on_modified(self, event):
        queue_sync(event.src_path)
    
    def on_created(self, event):
        queue_sync(event.src_path)
```

**Node.js (chokidar)**:
```javascript
const chokidar = require('chokidar');

const watcher = chokidar.watch('/sync', {
  persistent: true,
  ignoreInitial: true
});

watcher.on('all', (event, path) => {
  queueSync(path);
});
```

## 14. Testing Strategy

- Unit tests for core logic
- Integration tests with mock cloud services
- End-to-end tests with real services (test accounts)
- Load testing with large file sets
- Disaster recovery testing (restore procedures)

## 15. Documentation Requirements

- User guide for setup and configuration
- API documentation
- Troubleshooting guide
- Architecture diagrams
- Cost estimation calculator
- FAQ section

---

## 16. Project Structure

### Complete Application (Python + Flask + Bootstrap)
```
backup-app/
├── app.py                        # Main Flask application
├── config.yaml                   # Application configuration
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables
├── README.md                     # Setup instructions
├── deploy.sh                     # AWS deployment script
├── setup-instance.sh             # EC2 instance setup script
│
├── src/
│   ├── __init__.py
│   ├── sync_daemon.py            # Main sync daemon logic
│   │
│   ├── google_sync/
│   │   ├── __init__.py
│   │   ├── oauth.py              # Google OAuth authentication
│   │   ├── drive_sync.py         # Google Drive API integration
│   │   ├── photos_sync.py        # Google Photos API integration
│   │   └── export_formats.py    # Workspace file export logic
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── rclone_manager.py    # rclone wrapper with retry logic
│   │   ├── s3_uploader.py       # AWS S3 upload logic
│   │   ├── scaleway_uploader.py # Scaleway upload logic
│   │   └── cleanup.py           # Temp file cleanup
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLite database models
│   │   ├── sync_state.py        # Sync state management
│   │   └── schema.sql           # Database schema
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # API endpoints
│   │   ├── auth.py              # Session-based authentication
│   │   └── sse.py               # Server-Sent Events for live updates
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Structured logging
│       ├── config.py            # Configuration loader
│       ├── retry.py             # Exponential backoff retry logic
│       └── notifications.py     # Email/webhook notifications
│
├── static/                       # Frontend assets
│   ├── css/
│   │   ├── bootstrap.min.css    # Bootstrap 5.3
│   │   ├── bootstrap-icons.css  # Bootstrap Icons
│   │   └── dashboard.css        # Custom styles
│   ├── js/
│   │   ├── bootstrap.bundle.min.js
│   │   ├── chart.min.js         # Chart.js for metrics
│   │   ├── dashboard.js         # Main dashboard logic
│   │   ├── file-browser.js      # File browsing functionality
│   │   ├── logs-viewer.js       # Live log viewer (SSE)
│   │   └── sync-controls.js     # Start/stop/pause controls
│   └── img/
│       ├── logo.png
│       └── favicon.ico
│
├── templates/                    # Jinja2 HTML templates
│   ├── base.html                # Base template with navbar
│   ├── login.html               # Login page
│   ├── dashboard.html           # Overview/home page
│   ├── files.html               # File browser
│   ├── logs.html                # Log viewer
│   ├── settings.html            # Configuration page
│   └── components/
│       ├── navbar.html          # Navigation bar
│       ├── sync-status.html     # Sync status widget
│       └── metrics-card.html    # Metrics display card
│
├── systemd/
│   └── backup-daemon.service    # systemd service file
│
├── tests/
│   ├── __init__.py
│   ├── test_google_sync.py
│   ├── test_rclone.py
│   ├── test_api.py
│   └── test_database.py
│
└── docs/
    ├── SETUP.md                 # Setup guide
    ├── API.md                   # API documentation
    ├── DEPLOYMENT.md            # Deployment guide
    └── TROUBLESHOOTING.md       # Common issues
```

**Key Dependencies (requirements.txt)**:
```
Flask==3.0.0
Flask-Login==0.6.3
google-api-python-client==2.108.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.0
boto3==1.34.0                    # AWS SDK
tenacity==8.2.3                  # Retry logic
PyYAML==6.0.1
SQLAlchemy==2.0.23
requests==2.31.0
python-dotenv==1.0.0
```

## 17. API Endpoints (Backend Daemon)

### Status & Control
- `GET /api/status` - Get overall sync status
- `GET /api/sources` - List configured sources
- `GET /api/destinations` - List configured destinations
- `POST /api/sync/start` - Start sync daemon
- `POST /api/sync/stop` - Stop sync daemon
- `POST /api/sync/force` - Force immediate full sync
- `POST /api/sync/pause/:source` - Pause specific source

### Files & Logs
- `GET /api/files` - List synced files (with pagination)
- `GET /api/files/search?q=query` - Search files
- `GET /api/logs` - Get sync logs (with filtering)
- `GET /api/logs/stream` - SSE endpoint for live logs

### Metrics
- `GET /api/metrics/storage` - Storage usage per provider
- `GET /api/metrics/bandwidth` - Bandwidth usage over time
- `GET /api/metrics/sync-history` - Sync operation history

### Configuration
- `GET /api/config` - Get current configuration
- `PUT /api/config` - Update configuration
- `POST /api/config/test` - Test connection to providers

### Health
- `GET /api/health` - Health check endpoint
- `GET /api/version` - Get daemon version

## 18. Deployment Strategy

### 18.1 Why EC2 over AWS App Runner?

**Cost Comparison (24/7 operation)**:
| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| **EC2 t3.small** | 2 vCPU, 2GB RAM | $15 |
| + EBS 100GB gp3 | Storage | $8 |
| **EC2 Total** | | **$23** |
| | | |
| **App Runner** | 1 vCPU, 2GB RAM | ~$46 |
| (0.5 vCPU × $0.064/hr × 730hrs) | | |
| + (2GB × $0.007/hr × 730hrs) | | |
| **App Runner Total** | | **$46+** |

**EC2 Advantages**:
- ✅ **50% cheaper** ($23 vs $46/month)
- ✅ Direct EBS storage for 100GB temp cache
- ✅ IAM role integration (no credential storage needed)
- ✅ systemd for reliable daemon management
- ✅ Full control over the environment
- ✅ Can run background processes easily

**App Runner Limitations**:
- ❌ More expensive for 24/7 workloads
- ❌ No persistent local storage (would need EFS = extra cost)
- ❌ Not designed for long-running background daemons
- ❌ Container-based (adds complexity)
- ❌ Less control over the runtime environment

**Verdict**: EC2 is the clear winner for this use case.

### 18.2 Deployment Process

**Automated Deployment with deploy.sh**:
```bash
#!/bin/bash
# deploy.sh - One-command deployment to AWS EC2

# 1. Create EC2 instance with proper IAM role
# 2. SSH into instance and run setup script
# 3. Configure and start the application

# Usage: ./deploy.sh
```

**Step-by-Step Deployment**:

#### Step 1: Create EC2 Instance
```bash
# Create security group
aws ec2 create-security-group \
  --group-name backup-app-sg \
  --description "Backup app security group"

# Allow SSH and HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
  --group-name backup-app-sg \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name backup-app-sg \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name backup-app-sg \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-xxxxxxxxx \
  --instance-type t3.small \
  --key-name your-key-pair \
  --security-groups backup-app-sg \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}}]' \
  --iam-instance-profile Name=BackupAppRole
```

#### Step 2: Setup Script (setup-instance.sh)
```bash
#!/bin/bash
# Runs on EC2 instance to set up the application

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.11
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Install git
sudo apt-get install -y git

# Clone application
cd /opt
sudo git clone https://github.com/your-org/backup-app.git
cd backup-app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
sudo mkdir -p /sync/google-drive
sudo mkdir -p /sync/google-photos
sudo mkdir -p /var/log/backup-daemon

# Copy environment file
sudo cp .env.example .env
# Edit .env with your credentials

# Configure rclone
rclone config

# Set up systemd service
sudo cp systemd/backup-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable backup-daemon
sudo systemctl start backup-daemon

# Check status
sudo systemctl status backup-daemon
```

#### Step 3: Application Structure on EC2
```
/opt/backup-app/               # Application code
├── venv/                      # Python virtual environment
├── app.py                     # Flask application
├── config.yaml                # Configuration
├── .env                       # Environment variables
└── src/                       # Source code

/sync/                         # Temporary sync directory
├── google-drive/              # 100GB cache for Drive
└── google-photos/             # Files

/var/log/backup-daemon/        # Logs
├── app.log
├── sync.log
└── error.log
```

#### Step 4: systemd Service Configuration
```ini
# /etc/systemd/system/backup-daemon.service
[Unit]
Description=Backup Application Daemon
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/backup-app
Environment="PATH=/opt/backup-app/venv/bin"
ExecStart=/opt/backup-app/venv/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/backup-daemon/app.log
StandardError=append:/var/log/backup-daemon/error.log

[Install]
WantedBy=multi-user.target
```

#### Step 5: Running the Application
```bash
# Start the daemon
sudo systemctl start backup-daemon

# Check status
sudo systemctl status backup-daemon

# View logs
sudo journalctl -u backup-daemon -f

# Or view log files
tail -f /var/log/backup-daemon/app.log

# Restart after configuration changes
sudo systemctl restart backup-daemon

# Stop the daemon
sudo systemctl stop backup-daemon
```

### 18.3 Continuous Deployment (Optional)

**Using GitHub Actions**:
```yaml
# .github/workflows/deploy.yml
name: Deploy to EC2

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to EC2
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ubuntu
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            cd /opt/backup-app
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart backup-daemon
```

### 18.4 Monitoring & Maintenance

**Check Application Health**:
```bash
# Check if daemon is running
sudo systemctl is-active backup-daemon

# Check resource usage
htop

# Check disk space (important for 100GB cache)
df -h /sync

# Check logs for errors
grep ERROR /var/log/backup-daemon/app.log

# View sync progress
curl http://localhost:8080/api/status
```

**Backup & Updates**:
```bash
# Update application
cd /opt/backup-app
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart backup-daemon

# Backup SQLite database
cp /opt/backup-app/sync_state.db /opt/backup-app/sync_state.db.backup
```

## 19. Next Steps

### Immediate Actions
1. **Set up AWS Account**:
   - Create IAM role with S3 access
   - Create S3 bucket in us-east-1
   - Set up Scaleway account and object storage

2. **Google Cloud Setup**:
   - Create Google Cloud Project
   - Enable Drive and Photos APIs
   - Create OAuth 2.0 credentials

3. **Deploy Infrastructure**:
   - Run deploy.sh script
   - Configure EC2 instance
   - Set up environment variables

4. **Start Development**:
   - Follow Phase 1 roadmap
   - Build core sync engine
   - Test with small dataset first

### Development Order
1. Backend daemon core functionality
2. Google API integration
3. rclone integration
4. Web dashboard
5. Testing and optimization
6. Production deployment
