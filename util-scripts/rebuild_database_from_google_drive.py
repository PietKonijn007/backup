#!/usr/bin/env python3
"""
Rebuild database from current Google Drive state

This script:
1. Scans Google Drive for all current files
2. Checks if each file exists in AWS S3 and Backblaze B2
3. Cleans the database (removes old entries)
4. Rebuilds the database with current Google Drive files
5. Marks files for syncing if missing from destinations
"""
import sys
sys.path.append('.')

import os
import hashlib
from datetime import datetime
from src.database.models import get_db
from src.google_sync.oauth import get_oauth_manager
from src.google_sync.drive import create_drive_manager

def generate_file_id(drive_id):
    """Generate consistent file ID from Google Drive ID"""
    return hashlib.md5(drive_id.encode()).hexdigest()[:24]

def get_google_drive_files():
    """Get all files from Google Drive"""
    print("Step 1: Scanning Google Drive...")
    
    try:
        oauth_manager = get_oauth_manager()
        drive_manager = create_drive_manager(oauth_manager)
        
        all_files = []
        page_token = None
        
        while True:
            results = drive_manager.service.files().list(
                q="trashed=false",
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)',
                pageToken=page_token,
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            all_files.extend(files)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
            
            print(f"  Found {len(all_files)} files so far...")
        
        print(f"  Total: {len(all_files)} files in Google Drive\n")
        return all_files
        
    except Exception as e:
        print(f"Error scanning Google Drive: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_file_in_aws(file_path):
    """Check if file exists in AWS S3"""
    try:
        import boto3
        import yaml
        
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        bucket_name = config['destinations']['aws_s3']['bucket']
        s3_client = boto3.client('s3')
        
        try:
            s3_client.head_object(Bucket=bucket_name, Key=file_path)
            return True
        except:
            return False
            
    except Exception as e:
        print(f"Error checking AWS: {e}")
        return False

def check_file_in_b2(file_path):
    """Check if file exists in Backblaze B2"""
    try:
        import yaml
        from dotenv import load_dotenv
        from b2sdk.v2 import InMemoryAccountInfo, B2Api
        
        load_dotenv()
        
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        app_key_id = os.getenv('B2_APPLICATION_KEY_ID')
        app_key = os.getenv('B2_APPLICATION_KEY')
        bucket_name = config['destinations']['backblaze_b2']['bucket']
        
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", app_key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        
        # Try to get file info
        try:
            file_version = bucket.get_file_info_by_name(file_path)
            return True
        except:
            return False
            
    except Exception as e:
        print(f"Error checking B2: {e}")
        return False

def get_file_path(file, drive_manager):
    """Get full path for a file in Google Drive"""
    try:
        path_parts = [file['name']]
        current_file = file
        
        # Build path by traversing parents
        while 'parents' in current_file and current_file['parents']:
            parent_id = current_file['parents'][0]
            parent = drive_manager.service.files().get(
                fileId=parent_id,
                fields='id, name, parents'
            ).execute()
            
            if parent['name'] == 'My Drive':
                break
            
            path_parts.insert(0, parent['name'])
            current_file = parent
        
        return 'google-drive/My Drive/' + '/'.join(path_parts)
        
    except:
        return f"google-drive/My Drive/{file['name']}"

def main():
    print("=== Rebuilding Database from Google Drive ===\n")
    
    # Step 1: Get all files from Google Drive
    google_files = get_google_drive_files()
    if not google_files:
        print("Failed to get Google Drive files")
        return
    
    # Filter out folders (we only track files)
    google_files = [f for f in google_files if f.get('mimeType') != 'application/vnd.google-apps.folder']
    print(f"Filtered to {len(google_files)} files (excluding folders)\n")
    
    # Step 2: Get OAuth and Drive manager for path resolution
    print("Step 2: Initializing Google Drive manager...")
    oauth_manager = get_oauth_manager()
    drive_manager = create_drive_manager(oauth_manager)
    print("  Ready\n")
    
    # Step 3: Clean database
    print("Step 3: Cleaning database...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get current file count
        cursor.execute("SELECT COUNT(*) FROM files WHERE file_id NOT LIKE 'test-%'")
        old_count = cursor.fetchone()[0]
        
        # Delete all non-test files
        cursor.execute("DELETE FROM files WHERE file_id NOT LIKE 'test-%'")
        cursor.execute("DELETE FROM file_destinations WHERE file_id NOT LIKE 'test-%'")
        
        conn.commit()
        print(f"  Removed {old_count} old entries\n")
        
    except Exception as e:
        print(f"Error cleaning database: {e}")
        return
    
    # Step 4: Process each Google Drive file
    print("Step 4: Processing Google Drive files...")
    print("  This may take a while...\n")
    
    processed = 0
    aws_synced = 0
    aws_pending = 0
    b2_synced = 0
    b2_pending = 0
    
    for file in google_files:
        try:
            # Generate file ID
            file_id = generate_file_id(file['id'])
            
            # Get file path
            file_path = get_file_path(file, drive_manager)
            
            # Check if file exists in AWS and B2
            in_aws = check_file_in_aws(file_path)
            in_b2 = check_file_in_b2(file_path)
            
            # Add to database
            cursor.execute('''
                INSERT INTO files 
                (file_id, name, path, size, modified_time, sync_status, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id,
                file['name'],
                file_path,
                int(file.get('size', 0)),
                file.get('modifiedTime'),
                'synced' if (in_aws and in_b2) else 'pending',
                'google_drive',
                datetime.now().isoformat()
            ))
            
            # Add AWS destination
            cursor.execute('''
                INSERT INTO file_destinations
                (file_id, destination, sync_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                file_id,
                'aws_s3',
                'synced' if in_aws else 'pending',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            if in_aws:
                aws_synced += 1
            else:
                aws_pending += 1
            
            # Add B2 destination
            cursor.execute('''
                INSERT INTO file_destinations
                (file_id, destination, sync_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                file_id,
                'backblaze_b2',
                'synced' if in_b2 else 'pending',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            if in_b2:
                b2_synced += 1
            else:
                b2_pending += 1
            
            processed += 1
            
            if processed % 50 == 0:
                print(f"  Processed {processed}/{len(google_files)} files...")
                conn.commit()
            
        except Exception as e:
            print(f"  Error processing {file.get('name', 'unknown')}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Processed {processed} files")
    print(f"\n=== Summary ===")
    print(f"Google Drive files: {len(google_files)}")
    print(f"AWS S3: {aws_synced} synced, {aws_pending} pending")
    print(f"Backblaze B2: {b2_synced} synced, {b2_pending} pending")
    print(f"\nDatabase has been rebuilt based on current Google Drive state.")
    print(f"The sync daemon will now process pending files.")

if __name__ == '__main__':
    main()
