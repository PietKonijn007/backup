#!/usr/bin/env python3
"""
Diagnostic script to investigate why AWS S3 and Backblaze B2 have different file counts
"""
import sys
sys.path.append('.')

from src.storage.bucket_inspector import get_aws_s3_stats, get_backblaze_b2_stats

def main():
    print("=== Bucket Content Comparison ===\n")
    
    # Get stats from both buckets
    aws = get_aws_s3_stats()
    b2 = get_backblaze_b2_stats()
    
    print("AWS S3:")
    print(f"  Files: {aws.get('total_files', 0)}")
    print(f"  Size: {aws.get('total_size_formatted', '0 B')}")
    print(f"  Bucket: {aws.get('bucket', 'N/A')}")
    
    print("\nBackblaze B2:")
    print(f"  Files: {b2.get('total_files', 0)}")
    print(f"  Size: {b2.get('total_size_formatted', '0 B')}")
    print(f"  Bucket: {b2.get('bucket', 'N/A')}")
    
    print("\n=== Analysis ===")
    aws_files = aws.get('total_files', 0)
    b2_files = b2.get('total_files', 0)
    
    if aws_files > b2_files:
        diff = aws_files - b2_files
        ratio = aws_files / b2_files if b2_files > 0 else 0
        print(f"AWS has {diff} more files than B2")
        print(f"Ratio: {ratio:.2f}x")
        print("\nPossible reasons:")
        print("1. Some files were only synced to AWS before B2 was configured")
        print("2. B2 sync may have failed for some files")
        print("3. Files may have been deleted from B2 but not AWS")
        print("4. Google Photos might be syncing to AWS only")
    elif b2_files > aws_files:
        diff = b2_files - aws_files
        ratio = b2_files / aws_files if aws_files > 0 else 0
        print(f"B2 has {diff} more files than AWS")
        print(f"Ratio: {ratio:.2f}x")
    else:
        print("✓ Both buckets have the same number of files")
    
    # Check database for sync status
    print("\n=== Checking Database Sync Status ===")
    try:
        from src.database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Count files by destination
        cursor.execute('''
            SELECT destination, sync_status, COUNT(*) as count
            FROM file_destinations
            WHERE file_id NOT LIKE 'test-%'
            GROUP BY destination, sync_status
            ORDER BY destination, sync_status
        ''')
        
        results = cursor.fetchall()
        
        print("\nDatabase sync status:")
        for row in results:
            print(f"  {row[0]}: {row[1]} = {row[2]} files")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == '__main__':
    main()
