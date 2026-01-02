"""
Sync Configuration Database Operations
Manages persistent sync selections
"""
from src.database.models import get_db
from src.utils.logger import setup_logger

logger = setup_logger('sync-config')


def get_sync_config():
    """Get all items configured for syncing"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT item_id, item_name, item_type, is_folder, added_at 
        FROM sync_config 
        ORDER BY added_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'item_id': row[0],
            'item_name': row[1],
            'item_type': row[2],
            'is_folder': bool(row[3]),
            'added_at': row[4]
        }
        for row in rows
    ]


def add_to_sync_config(item_id, item_name, item_type, is_folder):
    """Add an item to sync configuration"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sync_config (item_id, item_name, item_type, is_folder)
            VALUES (?, ?, ?, ?)
        ''', (item_id, item_name, item_type, is_folder))
        conn.commit()
        conn.close()
        logger.info(f"Added to sync config: {item_name} ({item_id})")
        return True
    except Exception as e:
        logger.error(f"Error adding to sync config: {e}")
        return False


def remove_from_sync_config(item_id):
    """Remove an item from sync configuration"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sync_config WHERE item_id = ?', (item_id,))
        conn.commit()
        conn.close()
        logger.info(f"Removed from sync config: {item_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing from sync config: {e}")
        return False


def is_in_sync_config(item_id):
    """Check if an item is in sync configuration"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM sync_config WHERE item_id = ?', (item_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def clear_sync_config():
    """Clear all sync configuration"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sync_config')
        conn.commit()
        conn.close()
        logger.info("Cleared all sync configuration")
        return True
    except Exception as e:
        logger.error(f"Error clearing sync config: {e}")
        return False


def get_configured_folders():
    """Get list of folder IDs configured for syncing"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT item_id FROM sync_config WHERE is_folder = 1')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_configured_files():
    """Get list of file IDs configured for syncing"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT item_id FROM sync_config WHERE is_folder = 0')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
