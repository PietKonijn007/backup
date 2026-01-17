#!/usr/bin/env python3
"""
Sync untracked AWS S3 files to Backblaze B2

This script:
1. Scans AWS S3 bucket for all files
2. Identifies files not in the database
3. Adds them to the database
4. Marks them for B2 sync
5. Optionally triggers immediate sync
"""
import sys
sys.path.append('.')

import boto3
import yaml
import hashlib
from datetime import datetime
from src.database.models import get_db

def generate_file_id(path):
    """Generate a consistent file ID from path"""
    return hashlib.md5(path.encode()).hexdigest()[:24]

def main():
    print("=== Syncing Untracked Files to B2 ===\n")
    
    # Get AWS S3 files
    print("Step 1: Fetching AWS S3 file list...")
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        bucket_name = config['destinations']['aws_s3']['bucket']
        s3_client = boto3.client('s3')
        
        aws_files = {}
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    aws_files[obj['Key']] = {
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    }
        
        print(f"   Found {len(aws_files)} files in AWS S3\n")
        
    except Exception as e:
        print(f"Error fetching AWS S3: {e}")
        return
    
    # Get database tracked files
    print("Step 2: Checking database...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all tracked file paths
        cursor.execute('''
            SELECT file_id, path FROM files
            WHERE file_id NOT LIKE 'test-%'
        ''')
        
        tracked_paths = {row[1]: row[0] for row in cursor.fetchall()}
        print(f"   Found {len(tracked_paths)} files tracked in database\n")
        
        # Find untracked files
        untracked = []
        for aws_path, aws_info in aws_files.items():
            if aws_path not in tracked_paths:
                untracked.append((aws_path, aws_info))
        
        print(f"Step 3: Found {len(untracked)} untracked files\n")
        
        if len(untracked) == 0:
            print("✓ All AWS files are tracked. No action needed.")
            conn.close()
            return
        
        # Show sample
        print("   Sample untracked files:")
        for path, info in untracked[:5]:
            size_mb = info['size'] / (1024 * 1024)
            print(f"     - {path} ({size_mb:.2f} MB)")
        if len(untracked) > 5:
            print(f"     ... and {len(untracked) - 5} more\n")
        
        # Ask for confirmation
        print(f"\nThis will:")
        print(f"  1. Add {len(untracked)} files to the database")
        print(f"  2. Mark them as 'synced' for AWS S3 (already there)")
        print(f"  3. Mark them as 'pending' for Backblaze B2")
        print(f"  4. The sync daemon will then upload them to B2")
        
        response = input("\nProceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            conn.close()
            return
        
        # Add files to database
        print("\nStep 4: Adding files to database...")
        added_count = 0
        
        for aws_path, aws_info in untracked:
            try:
                # Generate file ID
                file_id = generate_file_id(aws_path)
                
                # Extract file name
                file_name = aws_path.split('/')[-1]
                
                # Insert into files table
                cursor.execute('''
                    INSERT OR IGNORE INTO files 
                    (file_id, name, path, size, mime_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    file_name,
                    aws_path,
                    aws_info['size'],
                    'application/octet-stream',  # Unknown mime type
                    aws_info['last_modified'].isoformat(),
                    datetime.now().isoformat()
                ))
                
                # Mark as synced for AWS S3
                cursor.execute('''
                    INSERT OR IGNORE INTO file_destinations
                    (file_id, destination, sync_status, synced_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    'aws_s3',
                    'synced',
                    aws_info['last_modified'].isoformat(),
                    datetime.now().isoformat()
                ))
                
                # Mark as pending for B2
                cursor.execute('''
                    INSERT OR IGNORE INTO file_destinations
                    (file_id, destination, sync_status, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    file_id,
                    'backblaze_b2',
                    'pending',
                    datetime.now().isoformat()
                ))
                
                added_count += 1
                
                if added_count % 100 == 0:
                    print(f"   Added {added_count}/{len(untracked)} files...")
                    conn.commit()
                
            except Exception as e:
                print(f"   Error adding {aws_path}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"\n✓ Successfully added {added_count} files to database")
        print(f"✓ Marked {added_count} files as pending for B2")
        print("\nThe sync daemon will now process these files and upload them to B2.")
        print("Monitor progress via the dashboard - B2 Pending count should increase.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
