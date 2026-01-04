"""
Calculate folder-level backup statistics
"""
import sqlite3
from src.database.models import get_db
from src.utils.logger import setup_logger

logger = setup_logger('folder-stats')


def get_folder_backup_stats():
    """
    Calculate backup statistics for all folders based on file paths
    
    Returns:
        dict: folder_name -> {destination -> {total, synced, percentage}}
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all file destinations with their paths
        cursor.execute("""
            SELECT remote_path, destination, sync_status
            FROM file_destinations
            WHERE remote_path IS NOT NULL
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Build folder statistics
        folder_stats = {}
        
        for remote_path, destination, status in rows:
            # Extract folder name from path
            # Path format: "google-drive/Persoonlijk/Subfolder/file.ext"
            parts = remote_path.split('/')
            if len(parts) < 3:
                continue
                
            # Get the top-level folder name (after "google-drive")
            if parts[0] == 'google-drive' and len(parts) > 1:
                folder_name = parts[1]
                
                if folder_name not in folder_stats:
                    folder_stats[folder_name] = {}
                
                if destination not in folder_stats[folder_name]:
                    folder_stats[folder_name][destination] = {
                        'total': 0,
                        'synced': 0,
                        'pending': 0,
                        'failed': 0
                    }
                
                folder_stats[folder_name][destination]['total'] += 1
                
                if status == 'synced':
                    folder_stats[folder_name][destination]['synced'] += 1
                elif status == 'pending':
                    folder_stats[folder_name][destination]['pending'] += 1
                elif status == 'failed':
                    folder_stats[folder_name][destination]['failed'] += 1
        
        # Calculate percentages
        for folder_name, destinations in folder_stats.items():
            for dest, stats in destinations.items():
                if stats['total'] > 0:
                    stats['percentage'] = round((stats['synced'] / stats['total']) * 100)
                else:
                    stats['percentage'] = 0
        
        return folder_stats
        
    except Exception as e:
        logger.error(f"Error calculating folder backup stats: {e}")
        return {}
