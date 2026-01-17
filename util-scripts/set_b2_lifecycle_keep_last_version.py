#!/usr/bin/env python3
"""
Set B2 bucket to keep only the last version of files

This will:
1. Update bucket lifecycle settings to keep only latest version
2. Old versions will be automatically deleted by B2
3. Reduce storage costs and match AWS S3 behavior
"""
import sys
sys.path.append('.')

import os
import yaml
from dotenv import load_dotenv
from b2sdk.v2 import InMemoryAccountInfo, B2Api

load_dotenv()

def main():
    print("=== Setting B2 Bucket Lifecycle ===\n")
    
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        app_key_id = os.getenv('B2_APPLICATION_KEY_ID')
        app_key = os.getenv('B2_APPLICATION_KEY')
        bucket_name = config['destinations']['backblaze_b2']['bucket']
        
        print(f"Bucket: {bucket_name}")
        print(f"Current setting: Keep all versions")
        print(f"New setting: Keep only last version\n")
        
        response = input("Do you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
        
        print("\nConnecting to B2...")
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", app_key_id, app_key)
        
        bucket = b2_api.get_bucket_by_name(bucket_name)
        
        print("Updating bucket lifecycle settings...")
        
        # Set lifecycle rules to keep only 1 version
        lifecycle_rules = {
            'daysFromHidingToDeleting': 1,
            'daysFromUploadingToHiding': None,
            'fileNamePrefix': ''
        }
        
        # Update bucket
        bucket.update(
            lifecycle_rules=[lifecycle_rules]
        )
        
        print("\n✓ Bucket lifecycle updated successfully!")
        print("\nWhat happens next:")
        print("1. New file uploads will only keep the latest version")
        print("2. Old versions will be automatically deleted by B2 within 24 hours")
        print("3. Storage usage will decrease from 17.2 GB to ~10.8 GB")
        print("4. File count will decrease from 25,078 to ~2,159 files")
        print("5. This will reduce your B2 storage costs")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nYou can also do this manually:")
        print("1. Go to https://secure.backblaze.com/b2_buckets.htm")
        print("2. Click on 'hofkens-backup' bucket")
        print("3. Click 'Lifecycle Settings'")
        print("4. Change to 'Keep only the last version'")
        print("5. Click 'Update Bucket'")

if __name__ == '__main__':
    main()
