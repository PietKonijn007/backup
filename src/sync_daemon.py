"""
Sync Daemon - Background process for continuous syncing
Monitors Google Drive for changes and automatically syncs to S3
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.utils.logger import setup_logger
from src.google_sync.oauth import get_oauth_manager
from src.google_sync.drive import create_drive_manager
from src.sync.sync_service import create_sync_service
from src.database.models import get_db
from src.database import sync_config

logger = setup_logger('sync-daemon')


class SyncDaemon:
    """Background daemon for continuous file synchronization"""
    
    def __init__(self, config):
        self.config = config
        self.running = False
        self.paused = False
        self.thread = None
        self.last_sync_time = None
        self.stats = {
            'files_synced': 0,
            'files_failed': 0,
            'total_size': 0,
            'last_error': None,
            'uptime_seconds': 0
        }
        self._start_time = None
        logger.info("Sync daemon initialized")
    
    def start(self):
        """Start the daemon in a background thread"""
        if self.running:
            logger.warning("Daemon is already running")
            return False
        
        self.running = True
        self.paused = False
        self._start_time = time.time()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Sync daemon started")
        
        # Update database
        self._update_daemon_state('running')
        return True
    
    def stop(self):
        """Stop the daemon"""
        if not self.running:
            logger.warning("Daemon is not running")
            return False
        
        logger.info("Stopping sync daemon...")
        self.running = False
        
        # Wait for thread to finish (with timeout)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        logger.info("Sync daemon stopped")
        self._update_daemon_state('stopped')
        return True
    
    def pause(self):
        """Pause the daemon (keeps running but doesn't sync)"""
        if not self.running:
            logger.warning("Cannot pause - daemon is not running")
            return False
        
        self.paused = True
        logger.info("Sync daemon paused")
        self._update_daemon_state('paused')
        return True
    
    def resume(self):
        """Resume the daemon from paused state"""
        if not self.running:
            logger.warning("Cannot resume - daemon is not running")
            return False
        
        self.paused = False
        logger.info("Sync daemon resumed")
        self._update_daemon_state('running')
        return True
    
    def get_status(self) -> Dict:
        """Get current daemon status"""
        uptime = 0
        if self._start_time and self.running:
            uptime = int(time.time() - self._start_time)
        
        return {
            'running': self.running,
            'paused': self.paused,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'stats': {
                'files_synced': self.stats['files_synced'],
                'files_failed': self.stats['files_failed'],
                'total_size': self.stats['total_size'],
                'total_size_formatted': self._format_size(self.stats['total_size']),
                'last_error': self.stats['last_error'],
                'uptime_seconds': uptime
            }
        }
    
    def _run_loop(self):
        """Main daemon loop - runs continuously"""
        logger.info("Daemon loop started")
        
        # Get sync interval from config (default 5 minutes)
        sync_interval = self.config.get('sync', {}).get('interval_seconds', 300)
        
        while self.running:
            try:
                # Update uptime
                if self._start_time:
                    self.stats['uptime_seconds'] = int(time.time() - self._start_time)
                
                # Skip sync if paused
                if self.paused:
                    logger.debug("Daemon paused, sleeping...")
                    time.sleep(10)  # Check every 10 seconds when paused
                    continue
                
                # Check if we should sync
                should_sync = False
                if self.last_sync_time is None:
                    should_sync = True
                    logger.info("First sync - will sync all recent files")
                elif datetime.now() - self.last_sync_time >= timedelta(seconds=sync_interval):
                    should_sync = True
                    logger.info(f"Sync interval reached ({sync_interval}s)")
                
                if should_sync:
                    self._perform_sync()
                else:
                    # Sleep for a shorter interval and check again
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}", exc_info=True)
                self.stats['last_error'] = str(e)
                time.sleep(60)  # Wait before retrying after error
    
    def _perform_sync(self):
        """Perform a sync operation - only syncs configured items"""
        try:
            logger.info("Starting sync operation...")
            
            # Check OAuth
            oauth_manager = get_oauth_manager()
            if not oauth_manager.is_authenticated():
                logger.warning("Not authenticated with Google - skipping sync")
                self.last_sync_time = datetime.now()
                return
            
            credentials = oauth_manager.get_credentials()
            
            # Create managers
            drive_manager = create_drive_manager(credentials)
            sync_service = create_sync_service(self.config, credentials)
            
            # Get configured items to sync
            configured_items = sync_config.get_sync_config()
            
            if not configured_items:
                logger.info("No items configured for syncing")
                self.last_sync_time = datetime.now()
                return
            
            logger.info(f"Found {len(configured_items)} configured items")
            
            # Collect all file IDs to sync
            files_to_sync = []
            
            # Add configured files
            for item in configured_items:
                if not item['is_folder']:
                    files_to_sync.append(item['item_id'])
            
            # Get files from configured folders (RECURSIVE)
            for item in configured_items:
                if item['is_folder']:
                    logger.info(f"Getting files recursively from folder: {item['item_name']}")
                    try:
                        # Get all files recursively
                        recursive_files = self._get_all_files_recursive(drive_manager, item['item_id'], item['item_name'])
                        files_to_sync.extend(recursive_files)
                        logger.info(f"Found {len(recursive_files)} files (recursive) in {item['item_name']}")
                    except Exception as e:
                        logger.error(f"Error getting files from folder {item['item_name']}: {e}")
            
            if not files_to_sync:
                logger.info("No files to sync")
                self.last_sync_time = datetime.now()
                return
            
            logger.info(f"Syncing {len(files_to_sync)} files...")
            
            # Sync files one by one (with progress tracking)
            for idx, file_id in enumerate(files_to_sync, 1):
                if not self.running or self.paused:
                    logger.info("Sync interrupted - daemon stopped or paused")
                    break
                
                logger.info(f"[{idx}/{len(files_to_sync)}] Syncing file ID: {file_id}")
                
                result = sync_service.sync_file(file_id)
                
                if result['success']:
                    self.stats['files_synced'] += 1
                    self.stats['total_size'] += result.get('size', 0)
                    
                    # Update database
                    self._update_file_sync_status(file_id, result.get('name', 'Unknown'), 'synced', result.get('size', 0))
                    
                    logger.info(f"✓ Synced: {result.get('name', file_id)}")
                else:
                    self.stats['files_failed'] += 1
                    self.stats['last_error'] = result.get('error')
                    
                    # Update database
                    self._update_file_sync_status(file_id, result.get('name', 'Unknown'), 'failed', 0, result.get('error'))
                    
                    logger.error(f"✗ Failed: {result.get('name', file_id)} - {result.get('error')}")
            
            self.last_sync_time = datetime.now()
            logger.info(f"Sync completed: {self.stats['files_synced']} synced, {self.stats['files_failed']} failed")
            
        except Exception as e:
            logger.error(f"Error performing sync: {e}", exc_info=True)
            self.stats['last_error'] = str(e)
    
    def _filter_files_to_sync(self, files) -> list:
        """Filter files that need syncing based on database state"""
        files_to_sync = []
        
        conn = get_db()
        cursor = conn.cursor()
        
        for file in files:
            file_id = file['id']
            modified_time = file.get('modified_time')
            
            # Check if file exists in database
            cursor.execute(
                'SELECT sync_status, modified_time FROM files WHERE file_id = ?',
                (file_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                # New file - needs syncing
                files_to_sync.append(file)
            else:
                db_status, db_modified = row
                
                # Sync if failed before or if file was modified after last sync
                if db_status == 'failed':
                    files_to_sync.append(file)
                elif modified_time and db_modified and modified_time > db_modified:
                    files_to_sync.append(file)
        
        conn.close()
        return files_to_sync
    
    def _update_file_sync_status(self, file_id: str, file_name: str, status: str, 
                                 size: int = 0, error: Optional[str] = None):
        """Update file sync status in database"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Insert or update file record
            cursor.execute('''
                INSERT INTO files (file_id, name, path, size, sync_status, last_sync, source)
                VALUES (?, ?, ?, ?, ?, datetime('now'), 'google_drive')
                ON CONFLICT(file_id) DO UPDATE SET
                    sync_status = excluded.sync_status,
                    last_sync = excluded.last_sync,
                    size = excluded.size
            ''', (file_id, file_name, f'/google-drive/{file_name}', size, status))
            
            # Log the sync action
            cursor.execute('''
                INSERT INTO sync_logs (file_id, action, status, message)
                VALUES (?, 'sync', ?, ?)
            ''', (file_id, status, error))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating file sync status: {e}")
    
    def _update_daemon_state(self, state: str):
        """Update daemon state in database"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Try to update existing row
            cursor.execute('UPDATE daemon_state SET state = ?, last_update = datetime("now") WHERE id = 1', (state,))
            
            # If no row exists, insert it
            if cursor.rowcount == 0:
                cursor.execute('INSERT INTO daemon_state (id, state, last_update) VALUES (1, ?, datetime("now"))', (state,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating daemon state: {e}")
    
    def _get_all_files_recursive(self, drive_manager, folder_id: str, folder_name: str, depth: int = 0) -> list:
        """
        Recursively get all file IDs from a folder and all its subfolders
        
        Args:
            drive_manager: Drive manager instance
            folder_id: Folder ID to start from
            folder_name: Folder name (for logging)
            depth: Current recursion depth (for logging)
            
        Returns:
            list: File IDs to sync
        """
        file_ids = []
        indent = "  " * depth
        
        try:
            # Get all items in this folder
            result = drive_manager.list_files(page_size=1000, folder_id=folder_id)
            items = result.get('files', [])
            
            if depth == 0:
                logger.info(f"{indent}Scanning folder: {folder_name} ({len(items)} items)")
            else:
                logger.debug(f"{indent}└─ Scanning subfolder: {folder_name} ({len(items)} items)")
            
            for item in items:
                if item.get('is_folder', False):
                    # It's a subfolder - recurse into it
                    logger.debug(f"{indent}  📁 Found subfolder: {item['name']}")
                    subfolder_files = self._get_all_files_recursive(
                        drive_manager, 
                        item['id'], 
                        item['name'],
                        depth + 1
                    )
                    file_ids.extend(subfolder_files)
                else:
                    # It's a file - add to sync list
                    file_ids.append(item['id'])
                    if depth <= 1:  # Only log files in first 2 levels to avoid spam
                        logger.debug(f"{indent}  📄 Found file: {item['name']}")
            
        except Exception as e:
            logger.error(f"Error scanning folder {folder_name} at depth {depth}: {e}")
        
        return file_ids
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


# Global daemon instance
_daemon_instance: Optional[SyncDaemon] = None


def get_daemon(config) -> SyncDaemon:
    """Get or create global daemon instance"""
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = SyncDaemon(config)
    return _daemon_instance
