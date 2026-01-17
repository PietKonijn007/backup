#!/usr/bin/env python3
"""
Populate test sync data to demonstrate the new dashboard statistics
"""
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import random

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import get_db, init_db


def create_test_sync_data():
    """Create test sync data for dashboard statistics"""
    print("Creating test sync data...")
    
    # Initialize database first
    init_db()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Clear existing test data
    cursor.execute('DELETE FROM file_destinations')
    cursor.execute('DELETE FROM files WHERE file_id LIKE "test-%"')
    
    # Sample file data
    test_files = [
        ('test-doc-001', 'document1.pdf', '/Documents/document1.pdf', 2048000),  # 2MB
        ('test-doc-002', 'presentation.pptx', '/Documents/presentation.pptx', 5120000),  # 5MB
        ('test-img-001', 'photo1.jpg', '/Photos/photo1.jpg', 3072000),  # 3MB
        ('test-img-002', 'photo2.png', '/Photos/photo2.png', 1536000),  # 1.5MB
        ('test-vid-001', 'video1.mp4', '/Videos/video1.mp4', 104857600),  # 100MB
        ('test-vid-002', 'video2.mov', '/Videos/video2.mov', 157286400),  # 150MB
        ('test-arc-001', 'backup.zip', '/Archives/backup.zip', 52428800),  # 50MB
        ('test-spr-001', 'spreadsheet.xlsx', '/Documents/spreadsheet.xlsx', 1024000),  # 1MB
        ('test-txt-001', 'notes.txt', '/Documents/notes.txt', 51200),  # 50KB
        ('test-img-003', 'screenshot.png', '/Screenshots/screenshot.png', 2048000),  # 2MB
    ]
    
    # Insert test files
    for file_id, name, path, size in test_files:
        cursor.execute('''
            INSERT OR REPLACE INTO files (file_id, name, path, size, modified_time, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (file_id, name, path, size, datetime.now().isoformat(), 'google_drive'))
    
    # Create file destinations with various statuses
    destinations = ['aws_s3', 'backblaze_b2']
    statuses = ['synced', 'pending', 'failed']
    
    for file_id, name, path, size in test_files:
        for destination in destinations:
            # Randomly assign status with weighted probability
            # 70% synced, 20% pending, 10% failed
            status_weights = [0.7, 0.2, 0.1]
            status = random.choices(statuses, weights=status_weights)[0]
            
            # Create error message for failed files
            error_message = None
            if status == 'failed':
                error_messages = [
                    'Connection timeout',
                    'Authentication failed',
                    'File too large',
                    'Network error',
                    'Permission denied',
                    'Storage quota exceeded'
                ]
                error_message = random.choice(error_messages)
            
            # Set last sync time for synced files
            last_sync = None
            if status == 'synced':
                # Random time in the last 7 days
                days_ago = random.randint(0, 7)
                hours_ago = random.randint(0, 23)
                last_sync = (datetime.now() - timedelta(days=days_ago, hours=hours_ago)).isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO file_destinations 
                (file_id, destination, sync_status, last_sync, size, error_message, remote_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id, 
                destination, 
                status, 
                last_sync, 
                size if status == 'synced' else None,
                error_message,
                f"/{destination}/{path.lstrip('/')}" if status == 'synced' else None
            ))
    
    conn.commit()
    conn.close()
    
    print(f"Created test data for {len(test_files)} files across {len(destinations)} destinations")


def verify_test_data():
    """Verify the test data was created correctly"""
    print("\nVerifying test data...")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check file destinations by status and destination
    cursor.execute('''
        SELECT destination, sync_status, COUNT(*) as count, 
               COALESCE(SUM(size), 0) as total_size
        FROM file_destinations 
        WHERE file_id LIKE 'test-%'
        GROUP BY destination, sync_status
        ORDER BY destination, sync_status
    ''')
    
    results = cursor.fetchall()
    print("\nFile destinations summary:")
    for destination, status, count, total_size in results:
        size_mb = total_size / (1024 * 1024) if total_size else 0
        print(f"  {destination:12} {status:8}: {count:2} files ({size_mb:.1f} MB)")
    
    # Check failed files
    cursor.execute('''
        SELECT fd.file_id, f.name, fd.destination, fd.error_message
        FROM file_destinations fd
        JOIN files f ON fd.file_id = f.file_id
        WHERE fd.sync_status = 'failed' AND fd.file_id LIKE 'test-%'
    ''')
    
    failed_files = cursor.fetchall()
    if failed_files:
        print(f"\nFailed files ({len(failed_files)}):")
        for file_id, name, destination, error in failed_files:
            print(f"  {name} -> {destination}: {error}")
    else:
        print("\nNo failed files (lucky!)")
    
    conn.close()


def main():
    """Main function"""
    print("Populating Test Sync Data for Dashboard")
    print("=" * 50)
    
    try:
        create_test_sync_data()
        verify_test_data()
        
        print("\n✅ Test data created successfully!")
        print("\nYou can now:")
        print("1. Refresh your dashboard at http://localhost:8080")
        print("2. See the new detailed statistics")
        print("3. Click on 'Failed' to see failed files")
        print("4. Test the retry functionality")
        
    except Exception as e:
        print(f"\n❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())