#!/usr/bin/env python3
"""
Diagnose B2 file listing to understand the discrepancy
"""
import sys
sys.path.append('.')

import os
import yaml
from dotenv import load_dotenv
from b2sdk.v2 import InMemoryAccountInfo, B2Api

load_dotenv()

def main():
    print("=== B2 Listing Diagnostic ===\n")
    
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        app_key_id = os.getenv('B2_APPLICATION_KEY_ID')
        app_key = os.getenv('B2_APPLICATION_KEY')
        bucket_name = config['destinations']['backblaze_b2']['bucket']
        
        print(f"Connecting to bucket: {bucket_name}\n")
        
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", app_key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        
        # Test 1: Count with latest_only=True
        print("Test 1: Counting with latest_only=True...")
        count1 = 0
        size1 = 0
        for file_version, folder_name in bucket.ls(recursive=True, latest_only=True):
            if file_version is not None:
                count1 += 1
                size1 += file_version.size
        print(f"  Files: {count1}, Size: {size1 / (1024**3):.2f} GB\n")
        
        # Test 2: Count with latest_only=False (all versions)
        print("Test 2: Counting with latest_only=False (all versions)...")
        count2 = 0
        size2 = 0
        for file_version, folder_name in bucket.ls(recursive=True, latest_only=False):
            if file_version is not None:
                count2 += 1
                size2 += file_version.size
        print(f"  Files: {count2}, Size: {size2 / (1024**3):.2f} GB\n")
        
        # Test 3: Use list_file_names API
        print("Test 3: Using list_file_names API...")
        count3 = 0
        size3 = 0
        start_file_name = None
        
        while True:
            response = bucket.api.list_file_names(
                bucket.id_,
                start_file_name=start_file_name,
                max_file_count=10000
            )
            
            files = response['files']
            count3 += len(files)
            for f in files:
                size3 += f.get('contentLength', 0)
            
            next_file_name = response.get('nextFileName')
            if not next_file_name:
                break
            start_file_name = next_file_name
        
        print(f"  Files: {count3}, Size: {size3 / (1024**3):.2f} GB\n")
        
        print("=== Summary ===")
        print(f"Method 1 (latest_only=True): {count1} files, {size1 / (1024**3):.2f} GB")
        print(f"Method 2 (all versions): {count2} files, {size2 / (1024**3):.2f} GB")
        print(f"Method 3 (list_file_names): {count3} files, {size3 / (1024**3):.2f} GB")
        print(f"\nB2 Console shows: 25,078 files, 17.2 GB")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
