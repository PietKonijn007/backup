"""
Database operations for folder destination policies
"""
import json
from datetime import datetime
from src.database.models import get_db
from src.utils.logger import setup_logger

logger = setup_logger('folder-policies')


def add_folder_policy(folder_id: str, folder_name: str, folder_path: str, destinations: list) -> bool:
    """
    Add a folder with destination policy
    
    Args:
        folder_id: Google Drive folder ID
        folder_name: Folder name
        folder_path: Full path in Drive
        destinations: List of destination keys (e.g., ['aws_s3', 'backblaze_b2'])
        
    Returns:
        bool: True if added successfully
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        destinations_json = json.dumps(destinations)
        
        cursor.execute('''
            INSERT INTO sync_folders (folder_id, folder_name, folder_path, destinations)
            VALUES (?, ?, ?, ?)
        ''', (folder_id, folder_name, folder_path, destinations_json))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added folder policy: {folder_name} -> {destinations}")
        return True
    except Exception as e:
        logger.error(f"Error adding folder policy: {e}")
        return False


def update_folder_policy(folder_id: str, destinations: list) -> bool:
    """
    Update destinations for a folder
    
    Args:
        folder_id: Google Drive folder ID
        destinations: New list of destination keys
        
    Returns:
        bool: True if updated successfully
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        destinations_json = json.dumps(destinations)
        
        cursor.execute('''
            UPDATE sync_folders 
            SET destinations = ?, updated_at = CURRENT_TIMESTAMP
            WHERE folder_id = ?
        ''', (destinations_json, folder_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated folder policy for {folder_id}: {destinations}")
        return True
    except Exception as e:
        logger.error(f"Error updating folder policy: {e}")
        return False


def remove_folder_policy(folder_id: str) -> bool:
    """
    Remove a folder from sync configuration
    
    Args:
        folder_id: Google Drive folder ID
        
    Returns:
        bool: True if removed successfully
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM sync_folders WHERE folder_id = ?', (folder_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Removed folder policy for {folder_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing folder policy: {e}")
        return False


def get_all_folder_policies():
    """
    Get all folder policies
    
    Returns:
        list: List of folder policy dictionaries
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT folder_id, folder_name, folder_path, destinations, recursive, enabled, added_at
            FROM sync_folders
            ORDER BY folder_name
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        policies = []
        for row in rows:
            policies.append({
                'folder_id': row[0],
                'folder_name': row[1],
                'folder_path': row[2],
                'destinations': json.loads(row[3]),
                'recursive': bool(row[4]),
                'enabled': bool(row[5]),
                'added_at': row[6]
            })
        
        return policies
    except Exception as e:
        logger.error(f"Error getting folder policies: {e}")
        return []


def get_folder_policy(folder_id: str):
    """
    Get policy for a specific folder
    
    Args:
        folder_id: Google Drive folder ID
        
    Returns:
        dict or None: Folder policy dictionary
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT folder_id, folder_name, folder_path, destinations, recursive, enabled
            FROM sync_folders
            WHERE folder_id = ?
        ''', (folder_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'folder_id': row[0],
                'folder_name': row[1],
                'folder_path': row[2],
                'destinations': json.loads(row[3]),
                'recursive': bool(row[4]),
                'enabled': bool(row[5])
            }
        return None
    except Exception as e:
        logger.error(f"Error getting folder policy: {e}")
        return None


def get_destinations_for_file(file_path: str):
    """
    Determine which destinations a file should sync to based on folder policies with inheritance
    
    Uses inheritance logic: child folders inherit from parent folders unless they have explicit policy.
    Checks from most specific (deepest) folder to least specific (root).
    
    Args:
        file_path: Full path of file in Google Drive (e.g., "google-drive/My Drive/Folder1/Folder2/file.txt")
        
    Returns:
        list: List of destination keys (e.g., ['aws_s3', 'backblaze_b2'])
    """
    try:
        policies = get_all_folder_policies()
        
        # Build a map of folder_name -> policy for quick lookup
        policy_map = {}
        for policy in policies:
            if policy['enabled']:
                folder_name = policy['folder_name']
                policy_map[folder_name] = policy
        
        # Extract the path components from the file path
        # Example: "google-drive/My Drive/Persoonlijk/Appartementen/file.txt"
        # -> ["google-drive", "My Drive", "Persoonlijk", "Appartementen", "file.txt"]
        path_parts = file_path.split('/')
        
        # Remove "google-drive" and "My Drive" prefixes if present
        if len(path_parts) > 0 and path_parts[0] == 'google-drive':
            path_parts = path_parts[1:]
        if len(path_parts) > 0 and path_parts[0] == 'My Drive':
            path_parts = path_parts[1:]
        
        # Remove the filename (last part) to get just folders
        if len(path_parts) > 0:
            path_parts = path_parts[:-1]
        
        # Check from most specific folder to root
        # Example: ["Persoonlijk", "Appartementen", "Beveren"] 
        # Check: Beveren -> Appartementen -> Persoonlijk
        for i in range(len(path_parts) - 1, -1, -1):
            folder_name = path_parts[i]
            
            # Check if this folder has an explicit policy
            if folder_name in policy_map:
                policy = policy_map[folder_name]
                logger.debug(f"Found policy for folder '{folder_name}': {policy['destinations']}")
                return policy['destinations']
        
        # No policy found in any parent folder
        logger.debug(f"No folder policy found for path: {file_path}")
        return []
        
    except Exception as e:
        logger.error(f"Error determining destinations for file {file_path}: {e}")
        return []


def toggle_folder_enabled(folder_id: str, enabled: bool) -> bool:
    """
    Enable or disable a folder policy
    
    Args:
        folder_id: Google Drive folder ID
        enabled: True to enable, False to disable
        
    Returns:
        bool: True if updated successfully
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sync_folders 
            SET enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE folder_id = ?
        ''', (1 if enabled else 0, folder_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"{'Enabled' if enabled else 'Disabled'} folder policy for {folder_id}")
        return True
    except Exception as e:
        logger.error(f"Error toggling folder policy: {e}")
        return False


def update_file_destination_status(file_id: str, destination: str, status: str, 
                                   remote_path: str = None, size: int = None, 
                                   error_message: str = None) -> bool:
    """
    Update sync status for a file at a specific destination
    
    Args:
        file_id: Google Drive file ID
        destination: Destination key (e.g., 'aws_s3', 'backblaze_b2')
        status: Sync status ('synced', 'failed', 'pending')
        remote_path: Path in remote storage
        size: File size in bytes
        error_message: Error message if failed
        
    Returns:
        bool: True if updated successfully
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Try to update existing record
        cursor.execute('''
            UPDATE file_destinations 
            SET sync_status = ?, last_sync = CURRENT_TIMESTAMP, 
                remote_path = ?, size = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE file_id = ? AND destination = ?
        ''', (status, remote_path, size, error_message, file_id, destination))
        
        # If no rows updated, insert new record
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO file_destinations 
                (file_id, destination, sync_status, remote_path, size, error_message, last_sync)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (file_id, destination, status, remote_path, size, error_message))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error updating file destination status: {e}")
        return False


def get_file_destinations(file_id: str):
    """
    Get all destination statuses for a file
    
    Args:
        file_id: Google Drive file ID
        
    Returns:
        dict: Dictionary mapping destination to status info
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT destination, sync_status, last_sync, remote_path, size, error_message
            FROM file_destinations
            WHERE file_id = ?
        ''', (file_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        destinations = {}
        for row in rows:
            destinations[row[0]] = {
                'status': row[1],
                'last_sync': row[2],
                'remote_path': row[3],
                'size': row[4],
                'error_message': row[5]
            }
        
        return destinations
    except Exception as e:
        logger.error(f"Error getting file destinations: {e}")
        return {}
