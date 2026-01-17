#!/usr/bin/env python3
"""
Test script to populate logs and test the logs functionality
"""
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import random

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import get_db, init_db
from src.utils.db_logger import log_sync_event, log_daemon_event


def create_sample_logs():
    """Create sample log entries for testing"""
    print("Creating sample log entries...")
    
    # Initialize database first
    init_db()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Clear existing logs
    cursor.execute('DELETE FROM logs')
    
    # Sample log messages
    sample_logs = [
        ('INFO', 'daemon', 'Sync daemon started successfully'),
        ('INFO', 'sync', 'Starting sync process for Google Drive'),
        ('INFO', 'sync', 'Found 150 files to process'),
        ('INFO', 'sync', 'Synced document.pdf to AWS S3'),
        ('INFO', 'sync', 'Synced photo.jpg to Backblaze B2'),
        ('WARNING', 'sync', 'File large-video.mp4 exceeds size limit, skipping'),
        ('ERROR', 'sync', 'Failed to sync corrupted-file.doc: Connection timeout'),
        ('INFO', 'sync', 'Batch sync completed: 45 files processed'),
        ('INFO', 'daemon', 'Sync daemon paused by user'),
        ('INFO', 'daemon', 'Sync daemon resumed'),
        ('ERROR', 'oauth', 'Google OAuth token expired, refreshing'),
        ('INFO', 'oauth', 'OAuth token refreshed successfully'),
        ('WARNING', 'storage', 'AWS S3 bucket approaching storage limit'),
        ('INFO', 'sync', 'Incremental sync started'),
        ('DEBUG', 'sync', 'Checking file modification times'),
        ('DEBUG', 'sync', 'Processing folder: /Documents/Projects'),
        ('INFO', 'sync', 'Synced presentation.pptx to AWS S3'),
        ('ERROR', 'network', 'Network connection lost, retrying in 30 seconds'),
        ('INFO', 'network', 'Network connection restored'),
        ('INFO', 'sync', 'Sync process completed successfully'),
    ]
    
    # Create logs with timestamps spread over the last 24 hours
    base_time = datetime.now() - timedelta(hours=24)
    
    for i, (level, source, message) in enumerate(sample_logs):
        # Spread logs over 24 hours
        timestamp = base_time + timedelta(minutes=i * 72)  # ~72 minutes apart
        
        cursor.execute('''
            INSERT INTO logs (timestamp, level, source, message)
            VALUES (?, ?, ?, ?)
        ''', (timestamp.isoformat(), level, source, message))
    
    # Add some recent logs (last hour)
    recent_logs = [
        ('INFO', 'sync', 'Processing new files from Google Drive'),
        ('INFO', 'sync', 'Synced report.xlsx to AWS S3'),
        ('WARNING', 'sync', 'Duplicate file detected: backup.zip'),
        ('INFO', 'sync', 'Sync cycle completed: 3 files processed'),
    ]
    
    recent_base = datetime.now() - timedelta(minutes=60)
    for i, (level, source, message) in enumerate(recent_logs):
        timestamp = recent_base + timedelta(minutes=i * 15)
        cursor.execute('''
            INSERT INTO logs (timestamp, level, source, message)
            VALUES (?, ?, ?, ?)
        ''', (timestamp.isoformat(), level, source, message))
    
    conn.commit()
    conn.close()
    
    print(f"Created {len(sample_logs) + len(recent_logs)} sample log entries")


def test_log_functions():
    """Test the logging functions"""
    print("Testing logging functions...")
    
    # Test sync event logging
    log_sync_event('test-file-123', 'upload', 'success', 'Test file uploaded successfully')
    log_sync_event('test-file-456', 'upload', 'failed', 'Network timeout')
    
    # Test daemon event logging
    log_daemon_event('start', 'success', 'Daemon started for testing')
    log_daemon_event('pause', 'success', 'Daemon paused for testing')
    
    print("Logging functions tested successfully")


def verify_logs():
    """Verify logs were created correctly"""
    print("Verifying logs...")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Count logs by level
    cursor.execute('''
        SELECT level, COUNT(*) as count
        FROM logs
        GROUP BY level
        ORDER BY count DESC
    ''')
    
    results = cursor.fetchall()
    print("\nLog counts by level:")
    for level, count in results:
        print(f"  {level}: {count}")
    
    # Show recent logs
    cursor.execute('''
        SELECT timestamp, level, source, message
        FROM logs
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    
    recent_logs = cursor.fetchall()
    print("\nMost recent logs:")
    for timestamp, level, source, message in recent_logs:
        print(f"  {timestamp} [{source}] {level}: {message}")
    
    conn.close()


def main():
    """Main test function"""
    print("Testing Logs Functionality")
    print("=" * 50)
    
    try:
        create_sample_logs()
        test_log_functions()
        verify_logs()
        
        print("\n✅ All tests completed successfully!")
        print("\nYou can now:")
        print("1. Start the Flask application: python app.py")
        print("2. Navigate to http://localhost:8080/logs")
        print("3. Test the logs viewer functionality")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())