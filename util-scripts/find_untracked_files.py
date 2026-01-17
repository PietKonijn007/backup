#!/usr/bin/env python3
"""
Find files in AWS S3 that are not tracked in the database
"""
import sys
sys.path.append('.')

import boto3
import yaml
from src.database.models import get_db

def main():
    print("=== Finding Untracked Files ===\n")
    
    # Get AWS S3 files
    print("Fetching AWS S3 file list...")
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        bucket_name = config['destinations']['aws_s3']['bucket']
        s3_client = boto3.client('s3')
        
        aws_files = set()
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Use the file path as identifier
                    aws_files.add(obj['Key'])
        
        print(f"AWS S3: {len(aws_files)} files\n")
        
    except Exception as e:
        print(f"Error fetching AWS S3: {e}")
        return
    
    # Get database tracked files
    print("Fetching database tracked files...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all files in database
        cursor.execute('''
            SELECT file_id, name, path FROM files
            WHERE file_id NOT LIKE 'test-%'
        ''')
        
        db_files = cursor.fetchall()
        print(f"Database: {len(db_files)} files tracked\n")
        
        # Get files synced to AWS
        cursor.execute('''
            SELECT f.file_id, f.name, f.path, fd.sync_status
            FROM files f
            JOIN file_destinations fd ON f.file_id = fd.file_id
            WHERE fd.destination = 'aws_s3' 
            AND f.file_id NOT LIKE 'test-%'
        ''')
        
        aws_tracked = cursor.fetchall()
        print(f"Database: {len(aws_tracked)} files tracked for AWS S3")
        
        # Get files synced to B2
        cursor.execute('''
            SELECT f.file_id, f.name, f.path, fd.sync_status
            FROM files f
            JOIN file_destinations fd ON f.file_id = fd.file_id
            WHERE fd.destination = 'backblaze_b2'
            AND f.file_id NOT LIKE 'test-%'
        ''')
        
        b2_tracked = cursor.fetchall()
        print(f"Database: {len(b2_tracked)} files tracked for B2\n")
        
        conn.close()
        
        # Analysis
        print("=== Analysis ===")
        print(f"Files in AWS S3 bucket: {len(aws_files)}")
        print(f"Files tracked in database: {len(db_files)}")
        print(f"Files tracked for AWS in database: {len(aws_tracked)}")
        print(f"Files tracked for B2 in database: {len(b2_tracked)}")
        
        untracked_count = len(aws_files) - len(aws_tracked)
        print(f"\nUntracked files in AWS: {untracked_count}")
        
        if untracked_count > 0:
            print("\n⚠️  ISSUE IDENTIFIED:")
            print(f"   AWS S3 has {untracked_count} files that are NOT in the database")
            print("   These files were uploaded before the tracking system was implemented")
            print("   The system doesn't know these files exist, so it won't sync them to B2")
            print("\n   SOLUTION:")
            print("   1. Scan AWS S3 bucket and add missing files to database")
            print("   2. Mark them as 'pending' for B2 destination")
            print("   3. Let the sync daemon process them")
        
    except Exception as e:
        print(f"Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
