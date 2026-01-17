# GUI Function Separation Plan

## Current Overlapping Issues

### 1. Dashboard vs Files
- **Problem**: Both show Google Drive information and sync controls
- **Solution**: Dashboard = monitoring only, Files = configuration only

### 2. Settings vs Files  
- **Problem**: Both manage folder policies
- **Solution**: Settings = account/system config, Files = backup selection

### 3. Logs Page
- **Problem**: Empty template, no functionality
- **Solution**: Implement proper log viewer

## Proposed Clear Separation

### Dashboard (Monitoring Hub)
**Purpose**: Real-time monitoring and control
- Sync daemon status and controls (start/stop/pause/resume)
- Live statistics (files synced, failed, total size, uptime)
- Recent activity feed
- System health indicators
- Quick error alerts
- Storage usage overview

### Files (Backup Configuration)
**Purpose**: Configure what gets backed up where
- Google Drive folder tree browser
- Backup destination selection (AWS S3, Backblaze B2)
- Individual file/folder backup status
- Bulk backup operations
- Search and filter files
- Preview file details

### Settings (System Configuration)
**Purpose**: Account and system-level settings
- Google OAuth connection management
- Backup destination credentials and settings
- Sync intervals and advanced options
- User account management
- System preferences
- API keys and authentication

### Logs (Activity & Troubleshooting)
**Purpose**: Historical data and debugging
- Real-time log streaming
- Log level filtering (error, warning, info, debug)
- Search and filter logs
- Export log data
- Error analysis and trends
- Performance metrics history

## Implementation Priority

1. **High Priority**: Fix logs page functionality
2. **Medium Priority**: Move folder policy management from Settings to Files
3. **Low Priority**: Enhance dashboard with more monitoring features