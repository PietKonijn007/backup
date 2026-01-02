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

### 4.2 Sync Strategy with RSYNC
- **Real-Time Monitoring**: Use filesystem watching to detect changes immediately
- **RSYNC for Efficiency**: Only transfer changed portions of files
- **Background Process**: Daemon running continuously
- **Queue-Based**: Changes queued and processed in order
- **Manual Trigger**: Option to force immediate full sync via web UI

### 4.3 Sync Flow
1. Watch for changes in local sync directory (mirroring Google Drive/Photos)
2. Detect file additions, modifications, deletions
3. Queue changes for RSYNC to both backup destinations
4. Execute RSYNC with compression and checksum verification
5. Update sync status in database
6. Reflect status in web dashboard

### 4.4 Conflict Resolution
- **No Conflicts**: One-way sync eliminates conflicts
- **Versioning**: Keep multiple versions in destination
- **Deletion Handling**: Soft delete (move to .trash folder) before permanent deletion
- **Logging**: Record all sync operations for audit trail

## 5. Technical Architecture

### 5.1 Components
```
┌─────────────────┐
│  Google Drive   │
│  Google Photos  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Google Sync Service    │
│  - OAuth Authentication │
│  - Download to Local    │
│  - Keep Local Mirror    │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Local Sync Directory   │
│  /sync/google-drive     │
│  /sync/google-photos    │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  File System Watcher    │
│  (inotify/fswatch)      │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Background Sync Daemon │
│  - Change Queue         │
│  - RSYNC Manager        │
│  - Status Tracker       │
└──────────┬──────────────┘
           │
      ┌────┴─────┐
      ▼          ▼
┌──────────┐  ┌──────────────┐
│  AWS S3  │  │ EU Provider  │
│  (RSYNC) │  │  (RSYNC)     │
└──────────┘  └──────────────┘
           
           ▲
           │
┌──────────┴──────────────┐
│  React Web Dashboard    │
│  (Vercel Hosted)        │
│  - Sync Status          │
│  - File Browser         │
│  - Controls             │
│  - Logs & Metrics       │
└─────────────────────────┘
```

### 5.2 Technology Stack
**Backend (Sync Daemon)**:
- **Language**: Python 3.x or Node.js
- **Google APIs**: google-api-python-client or googleapis npm package
- **Sync Tool**: RSYNC with S3 support (s3cmd, rclone, or aws s3 sync)
- **File Watching**: watchdog (Python) or chokidar (Node.js)
- **Database**: SQLite for sync state and metadata
- **Process Manager**: systemd or PM2 for background daemon
- **API**: FastAPI (Python) or Express.js (Node.js) for backend API

**Frontend (Web Dashboard)**:
- **Framework**: React 18+ with TypeScript
- **UI Library**: Tailwind CSS + shadcn/ui or Material-UI
- **State Management**: React Query for API calls + Zustand for local state
- **Data Visualization**: Recharts for metrics and graphs
- **Hosting**: Vercel (with API routes or separate backend)
- **Real-time Updates**: WebSockets or Server-Sent Events (SSE)

**Infrastructure**:
- **Sync Daemon Host**: Local machine, NAS, or cloud VM (must be always-on)
- **Frontend**: Vercel
- **Storage**: AWS S3 + EU cloud provider (S3-compatible)
- **Database**: SQLite (local) or PostgreSQL (cloud)

### 5.3 Deployment Architecture
- **Daemon**: Background service running 24/7 on local/cloud machine
- **Web Dashboard**: Deployed on Vercel, communicates with daemon via REST API
- **API Endpoint**: Daemon exposes HTTP API for dashboard (secured with API key/JWT)
- **Connectivity**: Dashboard can be accessed from anywhere, daemon needs stable internet

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

## 11. Cost Considerations

### 11.1 Google API Costs
- Google Drive API: Free tier generous
- Google Photos API: Free tier available

### 11.2 Storage Costs
- **S3**: ~$0.023/GB/month (Intelligent-Tiering)
- **EU Providers**: 
  - Scaleway: ~€0.01/GB/month
  - OVHcloud: ~€0.01/GB/month
  - Hetzner: ~€0.01/GB/month

### 11.3 Transfer Costs
- **Download from Google**: Free
- **Upload to S3**: Free
- **Upload to EU**: Typically free

### 11.4 API Request Costs
- S3 PUT requests: $0.005 per 1,000 requests
- S3 GET requests: $0.0004 per 1,000 requests

## 12. Roadmap

### Phase 1: MVP - Backend Daemon
- [ ] Google OAuth authentication setup
- [ ] Google Drive API integration (download to local)
- [ ] Google Photos API integration (download to local)
- [ ] File system watcher implementation
- [ ] RSYNC integration for S3
- [ ] RSYNC integration for EU provider
- [ ] Basic SQLite database for sync state
- [ ] Daemon process with systemd/PM2
- [ ] RESTful API endpoints for status
- [ ] Basic error handling and logging

### Phase 2: Web Dashboard
- [ ] React + TypeScript project setup on Vercel
- [ ] Dashboard UI design (Tailwind + shadcn/ui)
- [ ] Home/Overview page with sync status
- [ ] Live sync logs viewer
- [ ] File browser component
- [ ] Sync controls (start/stop/force sync)
- [ ] API integration with backend daemon
- [ ] Real-time updates (SSE or WebSockets)
- [ ] Configuration management UI
- [ ] Authentication for dashboard access

### Phase 3: Enhanced Features
- [ ] Email notifications
- [ ] Webhook integrations
- [ ] Advanced monitoring and metrics
- [ ] Storage usage visualizations
- [ ] Search functionality
- [ ] File preview capability
- [ ] Bandwidth usage tracking
- [ ] Multi-account support

### Phase 4: Advanced Features
- [ ] Client-side encryption
- [ ] Restore/download functionality
- [ ] Selective sync rules
- [ ] Bandwidth throttling
- [ ] Mobile-responsive improvements
- [ ] PWA capabilities
- [ ] Backup verification tools
- [ ] Cost tracking and estimation

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

### Backend Daemon
```
backup-daemon/
├── src/
│   ├── main.py (or index.js)
│   ├── google_sync/
│   │   ├── drive.py
│   │   ├── photos.py
│   │   └── oauth.py
│   ├── file_watcher/
│   │   └── watcher.py
│   ├── rsync/
│   │   ├── manager.py
│   │   ├── s3.py
│   │   └── eu_provider.py
│   ├── api/
│   │   ├── routes.py
│   │   ├── auth.py
│   │   └── websocket.py
│   ├── database/
│   │   ├── models.py
│   │   └── queries.py
│   └── utils/
│       ├── logger.py
│       ├── config.py
│       └── notifications.py
├── config.yaml
├── requirements.txt (or package.json)
├── Dockerfile
└── README.md
```

### Web Dashboard
```
backup-dashboard/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx (overview)
│   │   ├── files/
│   │   │   └── page.tsx
│   │   ├── logs/
│   │   │   └── page.tsx
│   │   ├── settings/
│   │   │   └── page.tsx
│   │   └── api/
│   │       └── [...proxy].ts (optional API routes)
│   ├── components/
│   │   ├── SyncStatus.tsx
│   │   ├── FileBrowser.tsx
│   │   ├── LogViewer.tsx
│   │   ├── MetricsChart.tsx
│   │   └── ControlPanel.tsx
│   ├── lib/
│   │   ├── api.ts (API client)
│   │   ├── websocket.ts
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── useSyncStatus.ts
│   │   └── useFileList.ts
│   └── types/
│       └── index.ts
├── public/
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
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

## 18. Next Steps

### Immediate Actions
1. **Choose EU Cloud Provider**: Recommend Scaleway for cost/performance balance
2. **Set up Development Environment**:
   - Create Google Cloud Project for OAuth
   - Set up AWS S3 bucket
   - Set up EU provider account
3. **Initialize Projects**:
   - Create backend daemon repository
   - Create Vercel React app repository
4. **Start with Phase 1**: Build MVP backend daemon

### Development Order
1. Backend daemon core functionality
2. Basic API endpoints
3. React dashboard skeleton
4. Integration between dashboard and daemon
5. Polish UI/UX
6. Testing and deployment
