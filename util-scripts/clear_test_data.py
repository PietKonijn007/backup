#!/usr/bin/env python3
"""
Clear test data from the database
"""
import sys
import os
import sqlite3

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import get_db


def clear_test_data():
    """Clear all test data from the database"""
    print("Clearing test data...")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Clear test file destinations
    cursor.execute('DELETE FROM file_destinations WHERE file_id LIKE "test-%"')
    deleted_destinations = cursor.rowcount
    
    # Clear test files
    cursor.execute('DELETE FROM files WHERE file_id LIKE "test-%"')
    deleted_files = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Cleared {deleted_files} test files and {deleted_destinations} destination records")
    print("Dashboard will now show real data (likely zeros until you sync actual files)")


def main():
    """Main function"""
    print("Clear Test Data")
    print("=" * 30)
    
    confirm = input("Are you sure you want to clear all test data? (y/N): ")
    if confirm.lower() == 'y':
        clear_test_data()
        print("\n✅ Test data cleared!")
        print("Refresh your dashboard to see the change.")
    else:
        print("Operation cancelled.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())