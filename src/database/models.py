"""
Database models - SQLite
"""
import sqlite3
import os

DB_PATH = 'sync_state.db'

def init_db():
    """Initialize database with schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            size INTEGER,
            modified_time TEXT,
            sync_status TEXT DEFAULT 'pending',
            last_sync TEXT,
            retry_count INTEGER DEFAULT 0,
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sync logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Daemon state table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daemon_state (
            id INTEGER PRIMARY KEY,
            state TEXT NOT NULL,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sync configuration table - stores what user wants to sync
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT UNIQUE NOT NULL,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            is_folder BOOLEAN NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sync folders table - stores folder-level destination policies
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id TEXT UNIQUE NOT NULL,
            folder_name TEXT NOT NULL,
            folder_path TEXT,
            destinations TEXT NOT NULL,
            recursive BOOLEAN DEFAULT 1,
            enabled BOOLEAN DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # File destinations table - tracks which destinations have which files
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_destinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            destination TEXT NOT NULL,
            sync_status TEXT DEFAULT 'pending',
            last_sync TEXT,
            remote_path TEXT,
            size INTEGER,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(file_id, destination)
        )
    ''')
    
    # System logs table - for application logging
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT
        )
    ''')
    
    # Create index for logs performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

def create_user(username, password_hash):
    """Create a new user with hashed password"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    """Get user by username"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    return row
