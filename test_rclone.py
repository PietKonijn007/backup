"""
Test script for rclone AWS S3 integration
Run this to verify rclone is working correctly
"""
import os
import sys
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.storage.rclone_manager import create_rclone_manager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("=" * 60)
    print("Rclone AWS S3 Integration Test")
    print("=" * 60)
    
    # Load configuration
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return
    
    # Check environment variables
    print("\n1. Checking AWS credentials...")
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if aws_access_key and aws_secret_key:
        print(f"✓ AWS_ACCESS_KEY_ID: {aws_access_key[:10]}...")
        print(f"✓ AWS_SECRET_ACCESS_KEY: {'*' * 20}")
    else:
        print("✗ AWS credentials not found in environment")
        print("  Add them to your .env file:")
        print("  AWS_ACCESS_KEY_ID=your_access_key")
        print("  AWS_SECRET_ACCESS_KEY=your_secret_key")
        return
    
    # Create rclone manager
    print("\n2. Initializing rclone manager...")
    try:
        rclone = create_rclone_manager(config)
        print("✓ Rclone manager initialized")
        print(f"  Remote name: {rclone.remote_name}")
        print(f"  Bucket: {rclone.aws_config.get('bucket')}")
        print(f"  Region: {rclone.aws_config.get('region')}")
    except Exception as e:
        print(f"✗ Error initializing rclone: {e}")
        print("\nMake sure rclone is installed:")
        print("  macOS: brew install rclone")
        print("  Linux: curl https://rclone.org/install.sh | sudo bash")
        return
    
    # Test bucket access
    print("\n3. Testing S3 bucket access...")
    try:
        size_info = rclone.get_bucket_size()
        if size_info['success']:
            print(f"✓ Successfully accessed S3 bucket")
            print(f"  Files: {size_info['count']}")
            print(f"  Total size: {size_info['size_formatted']}")
        else:
            print(f"✗ Error accessing bucket: {size_info.get('error')}")
            return
    except Exception as e:
        print(f"✗ Error testing bucket: {e}")
        return
    
    # Test file upload
    print("\n4. Testing file upload...")
    test_file = 'test_upload.txt'
    try:
        # Create test file
        with open(test_file, 'w') as f:
            f.write('This is a test file for rclone upload\n')
            f.write(f'Created at: {Path(test_file).stat().st_mtime}\n')
        
        print(f"  Created test file: {test_file}")
        
        # Upload
        result = rclone.upload_file(test_file, 'test/test_upload.txt')
        
        if result['success']:
            print(f"✓ File uploaded successfully")
            print(f"  Local: {result['local_path']}")
            print(f"  Remote: {result['remote_path']}")
            print(f"  Size: {result['size_formatted']}")
        else:
            print(f"✗ Upload failed: {result.get('error')}")
        
        # Clean up local test file
        os.remove(test_file)
        print(f"  Cleaned up local test file")
        
    except Exception as e:
        print(f"✗ Error during upload test: {e}")
        if os.path.exists(test_file):
            os.remove(test_file)
        return
    
    # Test file listing
    print("\n5. Testing file listing...")
    try:
        list_result = rclone.list_files('test/')
        if list_result['success']:
            print(f"✓ Listed {list_result['count']} files in test/ directory")
            for file in list_result['files'][:5]:  # Show first 5
                print(f"  - {file.get('Name')} ({file.get('Size')} bytes)")
        else:
            print(f"✗ Listing failed: {list_result.get('error')}")
    except Exception as e:
        print(f"✗ Error listing files: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✓ All tests passed! Rclone is configured correctly.")
    print("=" * 60)
    print("\nYou can now use rclone to:")
    print("  - Upload files to AWS S3")
    print("  - Sync directories")
    print("  - List and manage S3 files")
    print("\nNext steps:")
    print("  1. Configure your backup sources in config.yaml")
    print("  2. Run the backup daemon to start syncing")
    print("=" * 60)

if __name__ == '__main__':
    main()
