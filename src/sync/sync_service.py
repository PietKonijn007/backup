"""
Sync Service - Orchestrates syncing from Google Drive to AWS S3
"""
import os
import tempfile
from pathlib import Path
from typing import Dict, List
from src.google_sync.drive import create_drive_manager
from src.storage.rclone_manager import create_rclone_manager
from src.utils.logger import setup_logger

logger = setup_logger('sync-service')


class SyncService:
    """Manages syncing files from Google Drive to AWS S3"""
    
    def __init__(self, config, google_credentials):
        """
        Initialize sync service
        
        Args:
            config: Configuration dictionary
            google_credentials: Google OAuth credentials
        """
        self.config = config
        self.drive_manager = create_drive_manager(google_credentials)
        self.rclone_manager = create_rclone_manager(config)
        self.temp_dir = config.get('sync', {}).get('temp_dir', '/tmp/backup-sync')
        
        # Create temp directory
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Sync service initialized with temp dir: {self.temp_dir}")
    
    def get_file_path_in_drive(self, file_id: str) -> str:
        """
        Get the full path of a file in Google Drive by traversing parent folders
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            str: Full path in Drive (e.g., "Folder1/Folder2/file.txt")
        """
        try:
            metadata = self.drive_manager.get_file_metadata(file_id)
            file_name = metadata['name']
            parents = metadata.get('parents', [])
            
            # If no parents, file is at root
            if not parents:
                return file_name
            
            # Build path by traversing parents
            path_parts = [file_name]
            current_parent = parents[0]  # Google Drive files typically have one parent
            
            # Traverse up to root (max 100 levels to prevent infinite loops)
            for _ in range(100):
                try:
                    parent_metadata = self.drive_manager.get_file_metadata(current_parent)
                    parent_name = parent_metadata['name']
                    parent_parents = parent_metadata.get('parents', [])
                    
                    path_parts.insert(0, parent_name)
                    
                    # If this parent has no parents, we've reached root
                    if not parent_parents:
                        break
                    
                    current_parent = parent_parents[0]
                except Exception as e:
                    logger.warning(f"Error traversing parent {current_parent}: {e}")
                    break
            
            # Join path parts
            full_path = '/'.join(path_parts)
            return full_path
            
        except Exception as e:
            logger.error(f"Error getting file path for {file_id}: {e}")
            # Fallback to just the filename
            return metadata.get('name', file_id)
    
    def sync_file(self, file_id: str, remote_path: str = None) -> Dict:
        """
        Sync a single file from Google Drive to S3, preserving folder hierarchy
        
        Args:
            file_id: Google Drive file ID
            remote_path: Optional S3 path (if None, preserves Drive hierarchy)
            
        Returns:
            dict: Sync result
        """
        try:
            logger.info(f"Starting sync for file ID: {file_id}")
            
            # Get file metadata
            metadata = self.drive_manager.get_file_metadata(file_id)
            file_name = metadata['name']
            
            logger.info(f"Syncing file: {file_name}")
            
            # Download from Google Drive
            logger.info(f"Downloading from Google Drive...")
            download_result = self.drive_manager.download_file(file_id, self.temp_dir)
            
            if not download_result['success']:
                return {
                    'success': False,
                    'error': f"Download failed: {download_result.get('error')}",
                    'file_name': file_name
                }
            
            local_path = download_result['file_path']
            
            # Determine S3 path - preserve full Drive hierarchy
            if remote_path is None:
                drive_path = self.get_file_path_in_drive(file_id)
                remote_path = f"google-drive/{drive_path}"
                logger.info(f"Preserving Drive hierarchy: {remote_path}")
            
            # Upload to S3 via rclone
            logger.info(f"Uploading to S3...")
            upload_result = self.rclone_manager.upload_file(local_path, remote_path)
            
            # Clean up local file
            try:
                os.remove(local_path)
                logger.info(f"Cleaned up temp file: {local_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")
            
            if upload_result['success']:
                logger.info(f"Successfully synced {file_name} to S3")
                return {
                    'success': True,
                    'file_name': file_name,
                    'file_id': file_id,
                    'size': upload_result['size'],
                    'size_formatted': upload_result['size_formatted'],
                    'remote_path': upload_result['remote_path']
                }
            else:
                return {
                    'success': False,
                    'error': f"Upload failed: {upload_result.get('error')}",
                    'file_name': file_name
                }
                
        except Exception as e:
            logger.error(f"Error syncing file {file_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_id': file_id
            }
    
    def sync_multiple_files(self, file_ids: List[str]) -> Dict:
        """
        Sync multiple files from Google Drive to S3
        
        Args:
            file_ids: List of Google Drive file IDs
            
        Returns:
            dict: Sync results with statistics
        """
        logger.info(f"Starting batch sync for {len(file_ids)} files")
        
        results = []
        success_count = 0
        error_count = 0
        total_size = 0
        
        for file_id in file_ids:
            result = self.sync_file(file_id)
            results.append(result)
            
            if result['success']:
                success_count += 1
                total_size += result.get('size', 0)
            else:
                error_count += 1
        
        logger.info(f"Batch sync complete: {success_count} succeeded, {error_count} failed")
        
        return {
            'success': True,
            'results': results,
            'statistics': {
                'total': len(file_ids),
                'success': success_count,
                'failed': error_count,
                'total_size': total_size,
                'total_size_formatted': self._format_size(total_size)
            }
        }
    
    def sync_folder_recursive(self, folder_id: str, parent_path: str = "") -> List[Dict]:
        """
        Recursively sync a folder and all its subfolders, preserving full hierarchy
        
        Args:
            folder_id: Google Drive folder ID
            parent_path: Path of parent folders (for recursion)
            
        Returns:
            list: List of sync results for all files
        """
        results = []
        
        try:
            # Get all items in this folder
            items = self.drive_manager.list_all_files(folder_id=folder_id)
            
            # Get folder name for path construction
            if not parent_path:
                folder_metadata = self.drive_manager.get_file_metadata(folder_id)
                current_path = folder_metadata['name']
            else:
                folder_metadata = self.drive_manager.get_file_metadata(folder_id)
                current_path = f"{parent_path}/{folder_metadata['name']}"
            
            # Process files first
            files = [item for item in items if not item['is_folder']]
            for file in files:
                # Sync file with full hierarchy path
                result = self.sync_file(file['id'])  # Will use get_file_path_in_drive
                results.append(result)
            
            # Then recursively process subfolders
            folders = [item for item in items if item['is_folder']]
            for subfolder in folders:
                subfolder_results = self.sync_folder_recursive(subfolder['id'], current_path)
                results.extend(subfolder_results)
            
        except Exception as e:
            logger.error(f"Error in recursive folder sync for {folder_id}: {e}")
            results.append({
                'success': False,
                'error': str(e),
                'folder_id': folder_id
            })
        
        return results
    
    def sync_folder(self, folder_id: str, remote_base_path: str = None) -> Dict:
        """
        Sync an entire folder from Google Drive to S3, preserving full hierarchy
        
        Args:
            folder_id: Google Drive folder ID
            remote_base_path: Base path in S3 (optional, defaults to preserving Drive structure)
            
        Returns:
            dict: Sync results
        """
        try:
            logger.info(f"Starting folder sync for folder ID: {folder_id}")
            
            # Get folder metadata
            folder_metadata = self.drive_manager.get_file_metadata(folder_id)
            folder_name = folder_metadata['name']
            
            logger.info(f"Syncing folder: {folder_name}")
            
            # If remote_base_path is specified, use custom path
            # Otherwise, preserve full Drive hierarchy via get_file_path_in_drive
            if remote_base_path is not None:
                # Custom path mode - recursively sync with specified base
                results = self.sync_folder_recursive(folder_id, "")
            else:
                # Preserve Drive hierarchy mode - let sync_file handle paths
                results = self.sync_folder_recursive(folder_id, "")
            
            # Calculate statistics
            success_count = sum(1 for r in results if r.get('success'))
            total_size = sum(r.get('size', 0) for r in results if r.get('success'))
            
            logger.info(f"Folder sync complete: {success_count}/{len(results)} files synced")
            
            return {
                'success': True,
                'folder_name': folder_name,
                'results': results,
                'statistics': {
                    'total': len(results),
                    'success': success_count,
                    'failed': len(results) - success_count,
                    'total_size': total_size,
                    'total_size_formatted': self._format_size(total_size)
                }
            }
            
        except Exception as e:
            logger.error(f"Error syncing folder {folder_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'folder_id': folder_id
            }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def create_sync_service(config, google_credentials):
    """
    Factory function to create SyncService instance
    
    Args:
        config: Configuration dictionary
        google_credentials: Google OAuth credentials
        
    Returns:
        SyncService instance
    """
    return SyncService(config, google_credentials)
