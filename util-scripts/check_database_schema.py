#!/usr/bin/env python3
"""
Check the actual database schema to understand the structure
"""
import sys
sys.path.append('.')

from src.database.models import get_db

def main():
    print("=== Database Schema Check ===\n")
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get files table schema
        cursor.execute("PRAGMA table_info(files)")
        files_columns = cursor.fetchall()
        
        print("Files table columns:")
        for col in files_columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Get file_destinations table schema
        cursor.execute("PRAGMA table_info(file_destinations)")
        dest_columns = cursor.fetchall()
        
        print("\nFile_destinations table columns:")
        for col in dest_columns:
            print(f"  {col[1]} ({col[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
