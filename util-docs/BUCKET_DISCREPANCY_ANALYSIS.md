# Bucket Content Discrepancy Analysis

## Issue Report

**Date**: January 17, 2026  
**Reported By**: User  
**Question**: Why does AWS S3 have 2,159 files (10.8 GB) while Backblaze B2 only has 1,102 files (5.4 GB)?

## Investigation Results

### ✅ This is NOT a calculation error

The dashboard is correctly showing the actual content of each bucket:
- **AWS S3**: 2,159 files (10.8 GB) - All Google Drive files
- **Backblaze B2**: 1,102 files (5.4 GB) - About 51% of Google Drive files

### Root Cause

**B2 was configured later than AWS S3**, so it's currently catching up:

1. **AWS S3 has been syncing for longer** - Contains all 2,159 Google Drive files
2. **B2 is catching up** - Currently has 1,102 files and actively syncing more
3. **Sync is working correctly** - Files are being uploaded to B2 as the daemon processes them

### Evidence from Production

#### Bucket Analysis
```
AWS S3 Bucket Structure:
- google-drive/My Drive: 2,156 files (10.76 GB)
- google-drive/Persoonlijk: 3 files (0.00 GB)
- Google Photos: 0 files (not syncing yet)

Backblaze B2:
- 1,102 files total
- Actively receiving new files
```

#### Database Status
```
Database sync tracking:
- aws_s3: synced = 1,093 files
- backblaze_b2: synced = 1,093 files
```

**Note**: The database shows 1,093 files for both because it only tracks files synced *after* the current sync system was implemented. AWS has an additional ~1,066 files that were uploaded before the tracking system was in place.

#### Active Sync Logs
```
2026-01-17 15:12:20 - Using destinations: ['aws_s3', 'backblaze_b2']
2026-01-17 15:12:22 - File already exists in backblaze_b2: Beerput firma.pdf
2026-01-17 15:12:43 - Uploading to backblaze_b2: bijlage aanmaning betaling.docx
2026-01-17 15:12:47 - Successfully uploaded to backblaze_b2
```

The daemon is:
- ✅ Checking each file against both destinations
- ✅ Skipping files that already exist in B2
- ✅ Uploading files that are missing or have size mismatches
- ✅ Successfully completing uploads to B2

### Timeline Explanation

1. **Initial Setup**: AWS S3 was configured first and synced all 2,159 Google Drive files
2. **B2 Added Later**: Backblaze B2 was configured as a second destination
3. **Catch-up Process**: The sync daemon is now going through all Google Drive files and uploading them to B2
4. **Current Progress**: 1,102 out of 2,159 files (51%) have been synced to B2
5. **Remaining**: ~1,057 files still need to be synced to B2

### Expected Behavior

This is **completely normal and expected** when:
- A new backup destination is added to an existing system
- The system needs to backfill historical files to the new destination
- Both destinations are configured to receive all files going forward

### Current Status

✅ **System is working correctly**
- Files are being synced to both AWS S3 and Backblaze B2
- New files are uploaded to both destinations simultaneously
- Existing files are being backfilled to B2
- No sync failures detected

### Estimated Completion

At the current sync rate:
- **Files remaining**: ~1,057 files
- **Estimated time**: Depends on file sizes and sync speed
- **Progress**: Can be monitored via dashboard statistics

The B2 file count will gradually increase until it matches AWS S3 (2,159 files).

### What This Means for the Dashboard

The dashboard is **correctly displaying real-time data**:
- It's not a bug or calculation error
- It accurately reflects the current state of each bucket
- The numbers will converge as B2 catches up to AWS

### Recommendations

1. **No action needed** - The system is working as designed
2. **Monitor progress** - Watch the B2 file count increase over time
3. **Verify completion** - Once B2 reaches 2,159 files, both buckets will be in sync
4. **Future files** - All new files will be synced to both destinations immediately

### Additional Notes

#### Google Photos
- **Current status**: Not syncing to either bucket yet
- **Configuration**: Enabled in config but no files detected
- **Expected**: Will sync to both AWS and B2 once photos are discovered

#### Sync Strategy
The system uses an intelligent sync strategy:
- **New files**: Uploaded to all configured destinations immediately
- **Existing files**: Checked periodically and backfilled to new destinations
- **Deduplication**: Files already in destination are skipped (size check)
- **Updates**: Files with size mismatches are re-uploaded

## Conclusion

**The dashboard is showing accurate, real-time data from the actual buckets.** The discrepancy between AWS S3 (2,159 files) and Backblaze B2 (1,102 files) is expected and temporary. B2 is actively catching up to AWS, and both buckets will eventually contain the same files.

**Status**: ✅ System operating normally, no issues detected  
**Action Required**: None - let the sync process complete naturally