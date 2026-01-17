# Backblaze B2 Multi-Destination Backup Implementation

## Overview
This document outlines the implementation of multi-destination backup support, adding Backblaze B2 alongside AWS S3 with a folder-based destination policy system.

## What's Been Implemented ✅

### 1. Configuration (Complete)
- **config.yaml**: Added `backblaze_b2` destination with bucket configuration
- **.env.example**: Added B2 credentials (`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`)
- Scaleway marked as disabled (not in current scope)

### 2. Database Schema (Complete)
- **sync_folders table**: Stores folder-level destination policies
  - `folder_id`: Google Drive folder ID
  - `folder_name`, `folder_path`: Folder identification
  - `destinations`: JSON array of destination keys (e.g., `["aws_s3", "backblaze_b2"]`)
  - `recursive`, `enabled`: Policy controls
  
- **file_destinations table**: Tracks per-destination sync status
  - `file_id`, `destination`: Unique per file/destination combo
  - `sync_status`: 'synced', 'failed', 'pending'
  - `last_sync`, `remote_path`, `size`, `error_message`: Tracking details

### 3. Database Operations (Complete)
**src/database/folder_policies.py** - New module with functions:
- `add_folder_policy()`: Add folder with destinations
- `update_folder_policy()`: Update folder destinations
- `remove_folder_policy()`: Remove folder from sync
- `get_all_folder_policies()`: List all policies
- `get_folder_policy()`: Get specific folder policy
- `get_destinations_for_file()`: Determine destinations based on file path
- `toggle_folder_enabled()`: Enable/disable folder
- `update_file_destination_status()`: Track per-destination status
- `get_file_destinations()`: Get all destinations for a file

### 4. Storage Layer (Complete)
**src/storage/rclone_manager.py** - Refactored to support multiple providers:
- Now accepts `destination_key` and `provider` parameters
- Supports S3 (AWS, Scaleway) and B2 (Backblaze) providers
- Provider-specific configuration in `_configure_remote()`:
  - **AWS S3**: Uses AWS credentials, region, storage class
  - **Backblaze B2**: Uses B2 application key ID and key
  - **Scaleway**: Uses custom endpoint and credentials
- All methods now use `self.bucket_name` and `self.dest_config` (generic)

**src/storage/storage_manager.py** - New orchestration layer:
- Initializes multiple RcloneManager instances (one per enabled destination)
- `upload_file()`: Uploads to specified destinations (or all)
- `upload_directory()`: Syncs directories to destinations
- `check_file_exists()`: Check existence at specific destination
- `get_available_destinations()`: List enabled destinations
- Returns per-destination results with `all_success` and `any_success` flags

## What Needs to Be Done Next 🔨

### 5. Sync Service Updates (CRITICAL)
**src/sync/sync_service.py** needs updates:
```python
# Replace single rclone_manager with storage_manager
from src.storage.storage_manager import create_storage_manager
from src.database import folder_policies

def __init__(self, config, google_credentials):
    self.storage_manager = create_storage_manager(config)
    # ... rest of init

def sync_file(self, file_id: str, remote_path: str = None) -> Dict:
    # Get file path to determine destinations
    drive_path = self.get_file_path_in_drive(file_id)
    full_path = f"google-drive/{drive_path}"
    
    # Get destinations from folder policy
    destinations = folder_policies.get_destinations_for_file(full_path)
    
    if not destinations:
        return {'success': False, 'skipped': True, 'reason': 'No folder policy for this file'}
    
    # Download from Google Drive
    download_result = self.drive_manager.download_file(file_id, self.temp_dir)
    local_path = download_result['file_path']
    
    # Upload to designated destinations
    upload_result = self.storage_manager.upload_file(
        local_path, 
        remote_path or full_path,
        destinations=destinations
    )
    
    # Update database per destination
    for dest, result in upload_result['destinations'].items():
        folder_policies.update_file_destination_status(
            file_id=file_id,
            destination=dest,
            status='synced' if result['success'] else 'failed',
            remote_path=result.get('remote_path'),
            size=result.get('size'),
            error_message=result.get('error')
        )
    
    return upload_result
```

###  6. API Endpoints (CRITICAL)
**src/api/routes.py** - Add new endpoints:

```python
# Folder policy management
@api_bp.route('/api/folders/policies', methods=['GET'])
@login_required
def get_folder_policies():
    """Get all folder destination policies"""
    from src.database import folder_policies
    policies = folder_policies.get_all_folder_policies()
    return jsonify({'success': True, 'policies': policies})

@api_bp.route('/api/folders/policies', methods=['POST'])
@login_required
def add_folder_policy():
    """Add folder with destination policy"""
    data = request.get_json()
    # ... implementation

@api_bp.route('/api/folders/policies/<folder_id>', methods=['PUT'])
@login_required
def update_folder_policy(folder_id):
    """Update folder destinations"""
    # ... implementation

@api_bp.route('/api/folders/policies/<folder_id>', methods=['DELETE'])
@login_required
def delete_folder_policy(folder_id):
    """Remove folder policy"""
    # ... implementation

@api_bp.route('/api/destinations/available', methods=['GET'])
@login_required
def get_available_destinations():
    """Get list of enabled destinations"""
    config = get_config()
    storage_mgr = create_storage_manager(config)
    destinations = storage_mgr.get_available_destinations()
    
    # Get human-readable names
    dest_info = {
        'aws_s3': {'name': 'AWS S3', 'icon': 'bi-amazon'},
        'backblaze_b2': {'name': 'Backblaze B2', 'icon': 'bi-cloud'},
        'scaleway': {'name': 'Scaleway', 'icon': 'bi-hdd-network'}
    }
    
    result = []
    for dest in destinations:
        info = dest_info.get(dest, {'name': dest, 'icon': 'bi-cloud'})
        result.append({'key': dest, **info})
    
    return jsonify({'success': True, 'destinations': result})
```

### 7. Settings UI (HIGH PRIORITY)
**templates/settings.html** - Add folder policy management section:

```html
<!-- Sync Folders Section (after Destination Configuration) -->
<div class="card mb-4">
    <div class="card-header">
        <h5><i class="bi bi-folder-symlink"></i> Sync Folder Configuration</h5>
    </div>
    <div class="card-body">
        <div id="folder-policies-list">
            <!-- Dynamically populated -->
        </div>
        <button class="btn btn-primary mt-3" onclick="showAddFolderModal()">
            <i class="bi bi-plus-circle"></i> Add Folder to Sync
        </button>
    </div>
</div>

<!-- Add Folder Modal -->
<div class="modal fade" id="addFolderModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Select Folder to Sync</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <!-- Google Drive tree browser -->
                <div id="drive-tree-container"></div>
                
                <div class="mt-3">
                    <h6>Backup Destinations:</h6>
                    <div id="destination-checkboxes">
                        <!-- Dynamically populated with available destinations -->
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" onclick="saveFolderPolicy()">Save</button>
            </div>
        </div>
    </div>
</div>

<script>
// Load folder policies
function loadFolderPolicies() {
    fetch('/api/folders/policies')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('folder-policies-list');
            container.innerHTML = '';
            
            data.policies.forEach(policy => {
                const card = document.createElement('div');
                card.className = 'card mb-2';
                card.innerHTML = `
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1"><i class="bi bi-folder"></i> ${policy.folder_name}</h6>
                                <div class="mb-2">
                                    ${policy.destinations.map(d => renderDestBadge(d)).join(' ')}
                                </div>
                                <small class="text-muted">${policy.folder_path || ''}</small>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-outline-primary" onclick="editFolder('${policy.folder_id}')">
                                    <i class="bi bi-pencil"></i> Edit
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteFolder('${policy.folder_id}')">
                                    <i class="bi bi-trash"></i> Remove
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        });
}

function renderDestBadge(dest) {
    const badges = {
        'aws_s3': '<span class="badge bg-warning text-dark"><i class="bi bi-amazon"></i> AWS S3</span>',
        'backblaze_b2': '<span class="badge bg-info"><i class="bi bi-cloud"></i> Backblaze B2</span>',
        'scaleway': '<span class="badge bg-secondary"><i class="bi bi-hdd-network"></i> Scaleway</span>'
    };
    return badges[dest] || `<span class="badge bg-secondary">${dest}</span>`;
}

// Load on page load
document.addEventListener('DOMContentLoaded', loadFolderPolicies);
</script>
```

### 8. Dashboard & Files Updates (MEDIUM PRIORITY)
- Show per-destination sync statistics
- Add destination badges to file listings
- Display which destinations have each file

### 9. Testing (HIGH PRIORITY)
1. **Test B2 rclone configuration**:
   ```bash
   # Set B2 credentials in .env
   export B2_APPLICATION_KEY_ID=your-key-id
   export B2_APPLICATION_KEY=your-app-key
   
   # Test manual rclone config
   rclone config create backblaze-b2 b2 account $B2_APPLICATION_KEY_ID key $B2_APPLICATION_KEY
   
   # Test listing
   rclone lsd backblaze-b2:
   ```

2. **Test folder policy workflow**:
   - Add folder with AWS + B2 destinations
   - Sync file, verify it goes to both
   - Check database tracking

3. **Test partial failures**:
   - Disconnect one destination
   - Verify other destination still works
   - Check error handling

### 10. Documentation (MEDIUM PRIORITY)
Create user guide:
- How to get B2 credentials
- How to configure folder policies
- How to monitor multi-destination sync
- Troubleshooting common issues

## Architecture Diagram

```
Google Drive
     |
     v
[Sync Service] ----reads----> [Folder Policies DB]
     |                              |
     |                              v
     |                    Determines destinations
     |                        (aws_s3, backblaze_b2)
     |
     v
[Storage Manager]
     |
     +-----> [RcloneManager (AWS S3)]
     |
     +-----> [RcloneManager (Backblaze B2)]
     |
     v
[File Destinations DB]
   Tracks: file_id + destination + status
```

## Key Design Decisions

1. **Folder-Based Policies**: Configuration at folder level (not per-file) for simplicity
2. **Checkbox Model**: Users select AWS, B2, or both via checkboxes
3. **Recursive Application**: Policies apply to all subfolders/files within
4. **Per-Destination Tracking**: Database tracks success/failure per destination
5. **Partial Success Handling**: If AWS succeeds but B2 fails, track individually
6. **Provider Abstraction**: RcloneManager supports any rclone-compatible provider

## Environment Variables Required

```bash
# AWS S3
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# Backblaze B2
B2_APPLICATION_KEY_ID=your-b2-key-id
B2_APPLICATION_KEY=your-b2-app-key
```

## Rclone Configuration
The system automatically creates rclone remotes:
- `aws-s3` for AWS S3
- `backblaze-b2` for Backblaze B2
- `scaleway-s3` for Scaleway (if enabled)

## Next Steps to Complete Implementation

1. **Update SyncService** (~30 min) - Critical for functionality
2. **Add API endpoints** (~45 min) - Required for UI
3. **Create Settings UI** (~60 min) - User-facing interface
4. **Test B2 integration** (~30 min) - Verify it works
5. **Update documentation** (~20 min) - Help users

**Total estimated time**: ~3 hours

## Benefits of This Implementation

✅ **Redundancy**: Files backed up to multiple clouds  
✅ **Flexibility**: Users control which folders go where  
✅ **Cost Optimization**: B2 typically cheaper than S3  
✅ **Geographic Distribution**: Spread data across providers  
✅ **Easy to Extend**: Add Google Cloud, Azure, etc. in future  
✅ **Granular Control**: Per-folder destination policies  
✅ **Robust Tracking**: Know exactly which files are where  
✅ **Partial Failure Handling**: One destination failing doesn't stop others  

## Migration Path for Existing Users

Existing files in AWS S3 will continue to work. To start using multi-destination:

1. Add B2 credentials to `.env`
2. Update `config.yaml` to enable B2
3. In Settings, add folder policies for folders you want backed up to B2
4. New syncs will go to designated destinations
5. Existing files remain in AWS S3 (no automatic migration)
