#!/usr/bin/env python3
"""
Compare actual bucket contents between AWS S3 and Backblaze B2
"""
import sys
sys.path.append('.')

def main():
    print("=== Comparing Bucket Contents ===\n")
    
    # Get AWS S3 file list
    print("Fetching AWS S3 file list...")
    try:
        import boto3
        import yaml
        
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        bucket_name = config['destinations']['aws_s3']['bucket']
        s3_client = boto3.client('s3')
        
        aws_files = {}
        aws_prefixes = {}
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    aws_files[key] = obj['Size']
                    
                    # Track prefixes (folders)
                    prefix = key.split('/')[0] if '/' in key else 'root'
                    aws_prefixes[prefix] = aws_prefixes.get(prefix, 0) + 1
        
        print(f"AWS S3: {len(aws_files)} files")
        print("\nAWS S3 folder breakdown:")
        for prefix, count in sorted(aws_prefixes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {prefix}: {count} files")
        
    except Exception as e:
        print(f"Error fetching AWS S3: {e}")
        return
    
    # Get B2 file list
    print("\nFetching Backblaze B2 file list...")
    try:
        import os
        from dotenv import load_dotenv
        from b2sdk.v2 import InMemoryAccountInfo, B2Api
        
        load_dotenv()
        
        app_key_id = os.getenv('B2_APPLICATION_KEY_ID')
        app_key = os.getenv('B2_APPLICATION_KEY')
        bucket_name = config['destinations']['backblaze_b2']['bucket']
        
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", app_key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)
        
        b2_files = {}
        b2_prefixes = {}
        
        for file_version, folder_to_list in bucket.ls(recursive=True):
            if file_version:
                key = file_version.file_name
                b2_files[key] = file_version.size
                
                # Track prefixes (folders)
                prefix = key.split('/')[0] if '/' in key else 'root'
                b2_prefixes[prefix] = b2_prefixes.get(prefix, 0) + 1
        
        print(f"Backblaze B2: {len(b2_files)} files")
        print("\nBackblaze B2 folder breakdown:")
        for prefix, count in sorted(b2_prefixes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {prefix}: {count} files")
        
    except Exception as e:
        print(f"Error fetching B2: {e}")
        return
    
    # Compare
    print("\n=== Comparison ===")
    
    # Files in AWS but not B2
    aws_only = set(aws_files.keys()) - set(b2_files.keys())
    if aws_only:
        print(f"\n{len(aws_only)} files in AWS S3 but NOT in B2:")
        # Group by prefix
        aws_only_prefixes = {}
        for key in aws_only:
            prefix = key.split('/')[0] if '/' in key else 'root'
            aws_only_prefixes[prefix] = aws_only_prefixes.get(prefix, 0) + 1
        
        for prefix, count in sorted(aws_only_prefixes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {prefix}: {count} files")
        
        # Show first 10 examples
        print("\n  First 10 examples:")
        for key in list(aws_only)[:10]:
            print(f"    - {key}")
    
    # Files in B2 but not AWS
    b2_only = set(b2_files.keys()) - set(aws_files.keys())
    if b2_only:
        print(f"\n{len(b2_only)} files in B2 but NOT in AWS S3:")
        # Group by prefix
        b2_only_prefixes = {}
        for key in b2_only:
            prefix = key.split('/')[0] if '/' in key else 'root'
            b2_only_prefixes[prefix] = b2_only_prefixes.get(prefix, 0) + 1
        
        for prefix, count in sorted(b2_only_prefixes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {prefix}: {count} files")
        
        # Show first 10 examples
        print("\n  First 10 examples:")
        for key in list(b2_only)[:10]:
            print(f"    - {key}")
    
    # Files in both
    both = set(aws_files.keys()) & set(b2_files.keys())
    print(f"\n{len(both)} files in BOTH buckets")

if __name__ == '__main__':
    main()
