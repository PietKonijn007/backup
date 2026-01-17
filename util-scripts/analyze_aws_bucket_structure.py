#!/usr/bin/env python3
"""
Analyze AWS S3 bucket structure to understand what's in there
"""
import sys
sys.path.append('.')

import boto3
import yaml
from collections import defaultdict

def main():
    print("=== AWS S3 Bucket Analysis ===\n")
    
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        bucket_name = config['destinations']['aws_s3']['bucket']
        s3_client = boto3.client('s3')
        
        print(f"Analyzing bucket: {bucket_name}\n")
        
        # Collect file information
        folder_stats = defaultdict(lambda: {'count': 0, 'size': 0})
        total_files = 0
        total_size = 0
        
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    size = obj['Size']
                    
                    total_files += 1
                    total_size += size
                    
                    # Get folder structure
                    parts = key.split('/')
                    if len(parts) >= 2:
                        top_folder = parts[0]
                        second_folder = parts[1] if len(parts) > 1 else ''
                        folder_key = f"{top_folder}/{second_folder}"
                    else:
                        folder_key = 'root'
                    
                    folder_stats[folder_key]['count'] += 1
                    folder_stats[folder_key]['size'] += size
        
        print(f"Total files: {total_files}")
        print(f"Total size: {total_size / (1024**3):.2f} GB\n")
        
        print("Folder breakdown:")
        for folder, stats in sorted(folder_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:20]:
            size_gb = stats['size'] / (1024**3)
            print(f"  {folder}: {stats['count']} files ({size_gb:.2f} GB)")
        
        # Check for google-photos specifically
        photos_count = sum(stats['count'] for folder, stats in folder_stats.items() if 'photo' in folder.lower())
        drive_count = sum(stats['count'] for folder, stats in folder_stats.items() if 'drive' in folder.lower())
        
        print(f"\nGoogle Photos files: {photos_count}")
        print(f"Google Drive files: {drive_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
