# File Deduplication Feature

## Overview

The backup system now includes intelligent file deduplication to avoid re-syncing files that already exist in the backup. This feature significantly reduces bandwidth usage, sync time, and costs by checking if files exist in AWS S3 before downloading them from Google Drive.

## How It Works

### 1. Pre-Sync Check
Before downloading a file from Google Drive, the system:
- Determines the target S3 path for the file
- Checks if a file already exists at that path in S3
- Compares the file size from Google Drive metadata with the existing file size in S3

### 2. Smart Skip Logic
Files are skipped if:
- A file exists at the target S3 path
- The file size matches exactly

If file sizes don't match or the file doesn't exist, it proceeds with the normal download and upload process.

### 3. Statistics Tracking
The sync statistics now include:
- **uploaded**: Number of new files uploaded to S3
- **skipped**: Number of files skipped (already in backup)
- **success**: Total successful operations (uploaded + skipped)
- **failed**: Number of failed operations
- **total**: Total number of files processed

## Modified Components

### 1. RcloneManager (`src/storage/rclone_manager.py`)
**Enhanced `check_file_exists()` method:**
- Now returns both existence status AND file size
- Uses `rclone lsjson` to get detailed file information
- Returns: `Tuple[bool, Optional[int]]` - (exists, size)

**Before:**
```python
def check_file_exists(self, remote_path: str) -> bool:
    # Only returned True/False
```

**After:**
```python
def check_file_exists(self, remote_path: str) -> Tuple[bool, Optional[int]]:
    # Returns (exists, size)
    # Can compare sizes for deduplication
```

### 2. SyncService (`src/sync/sync_service.py`)
**Updated `sync_file()` method:**
- Checks file existence before downloading
- Compares file sizes for exact match
- Returns skip status with reason

**Updated `sync_multiple_files()` method:**
- Tracks skipped files separately
- Provides detailed statistics with uploaded vs skipped counts

**Updated `sync_folder()` method:**
- Calculates skipped count for folder syncs
- Provides comprehensive statistics

## Benefits

### 1. **Reduced Bandwidth**
- Files already in backup are not downloaded again
- Saves Google Drive API quota
- Reduces AWS S3 upload bandwidth

### 2. **Faster Sync Times**
- Skips unnecessary downloads and uploads
- Only processes changed or new files
- Ideal for incremental backups

### 3. **Cost Savings**
- Fewer API calls to Google Drive
- Reduced S3 upload costs
- Lower data transfer costs

### 4. **Better User Experience**
- Clear reporting of what was uploaded vs skipped
- More informative sync statistics
- Better progress tracking

## Usage Examples

### Single File Sync
```python
result = sync_service.sync_file(file_id)

if result['success']:
    if result.get('skipped'):
        print(f"File already in backup: {result['file_name']}")
        print(f"Reason: {result['reason']}")
    else:
        print(f"File uploaded: {result['file_name']}")
```

### Batch Sync
```python
result = sync_service.sync_multiple_files(file_ids)

stats = result['statistics']
print(f"Total: {stats['total']}")
print(f"Uploaded: {stats['uploaded']}")
print(f"Skipped: {stats['skipped']}")
print(f"Failed: {stats['failed']}")
```

### Folder Sync
```python
result = sync_service.sync_folder(folder_id)

stats = result['statistics']
print(f"Folder: {result['folder_name']}")
print(f"Total files: {stats['total']}")
print(f"Newly uploaded: {stats['uploaded']}")
print(f"Already in backup: {stats['skipped']}")
```

## Log Examples

### File Already Exists
```
INFO - Syncing file: document.pdf (size: 2.50 MB)
INFO - Preserving Drive hierarchy: google-drive/Documents/document.pdf
INFO - File already exists in backup with same size, skipping: document.pdf
```

### File Needs Upload
```
INFO - Syncing file: new_photo.jpg (size: 5.23 MB)
INFO - Preserving Drive hierarchy: google-drive/Photos/new_photo.jpg
INFO - Downloading from Google Drive...
INFO - Uploading to S3...
INFO - Successfully synced new_photo.jpg to S3
```

### Batch Sync Complete
```
INFO - Batch sync complete: 5 uploaded, 15 skipped, 0 failed
```

## Technical Details

### Size Comparison
The system uses exact size matching (in bytes) to determine if files are identical. This is:
- Fast - no need to download the file
- Reliable - size changes indicate file modifications
- Efficient - leverages existing metadata

### File Path Consistency
Files are always stored using the same path structure, ensuring:
- Consistent deduplication across syncs
- Proper hierarchy preservation
- Reliable file identification

### Error Handling
If the existence check fails:
- The system logs the error
- Proceeds with normal sync (safe fallback)
- Ensures no files are missed due to check failures

## Future Enhancements

Potential improvements for even better deduplication:

1. **Hash-based Deduplication**: Compare file hashes (MD5/SHA256) for absolute certainty
2. **Database Tracking**: Track synced files in database for faster lookups
3. **Modification Time Check**: Consider file modification timestamps
4. **Content-based Deduplication**: Detect duplicate content with different names
5. **Delta Sync**: Upload only changed portions of files

## Configuration

The deduplication feature is enabled by default and requires no configuration. It works automatically with your existing setup.

## Compatibility

This feature is fully backward compatible:
- Existing backups work seamlessly
- No migration needed
- Works with current S3 bucket structure
- Compatible with existing rclone configuration

## Testing

To verify deduplication is working:

1. Sync a file for the first time - should upload
2. Sync the same file again - should skip
3. Check logs for "File already exists in backup with same size, skipping"
4. Review statistics for skipped count

## Support

For issues or questions about the deduplication feature, check:
- Logs in the sync service output
- Statistics in sync results
- This documentation for expected behavior
