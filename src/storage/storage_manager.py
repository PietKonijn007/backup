"""
Storage Manager - Orchestrates multiple storage destinations
Manages uploads to AWS S3, Backblaze B2, and other destinations
"""
import os
from typing import Dict, List, Optional
from src.storage.rclone_manager import RcloneManager
from src.utils.logger import setup_logger

logger = setup_logger('storage-manager')


class StorageManager:
    """Manages multiple storage destinations"""
    
    def __init__(self, config: Dict):
        """
        Initialize storage manager with multiple destinations
        
        Args:
            config: Configuration dictionary with all destinations
        """
        self.config = config
        self.managers = {}
        self._init_managers()
    
    def _init_managers(self):
        """Initialize RcloneManager for each enabled destination"""
        destinations_config = self.config.get('destinations', {})
        
        # AWS S3
        if destinations_config.get('aws_s3', {}).get('enabled', False):
            try:
                logger.info("Initializing AWS S3 manager")
                self.managers['aws_s3'] = RcloneManager(
                    config=self.config,
                    destination_key='aws_s3',
                    provider='s3'
                )
                logger.info("AWS S3 manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AWS S3 manager: {e}")
        
        # Backblaze B2
        if destinations_config.get('backblaze_b2', {}).get('enabled', False):
            try:
                logger.info("Initializing Backblaze B2 manager")
                self.managers['backblaze_b2'] = RcloneManager(
                    config=self.config,
                    destination_key='backblaze_b2',
                    provider='b2'
                )
                logger.info("Backblaze B2 manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Backblaze B2 manager: {e}")
        
        # Scaleway (EU Provider)
        if destinations_config.get('eu_provider', {}).get('enabled', False):
            try:
                logger.info("Initializing Scaleway manager")
                self.managers['scaleway'] = RcloneManager(
                    config=self.config,
                    destination_key='eu_provider',
                    provider='s3'
                )
                logger.info("Scaleway manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Scaleway manager: {e}")
        
        if not self.managers:
            logger.warning("No storage destinations are enabled!")
    
    def get_available_destinations(self) -> List[str]:
        """
        Get list of available (initialized) destinations
        
        Returns:
            list: List of destination keys
        """
        return list(self.managers.keys())
    
    def get_manager(self, destination_key: str) -> Optional[RcloneManager]:
        """
        Get RcloneManager for a specific destination
        
        Args:
            destination_key: Destination key ('aws_s3', 'backblaze_b2', etc.)
            
        Returns:
            RcloneManager or None
        """
        return self.managers.get(destination_key)
    
    def upload_file(self, local_path: str, remote_path: str, 
                   destinations: List[str] = None) -> Dict:
        """
        Upload a file to one or more destinations
        
        Args:
            local_path: Local file path
            remote_path: Remote path (will be used for all destinations)
            destinations: List of destination keys (None = all available)
            
        Returns:
            dict: Upload results per destination
        """
        if destinations is None:
            destinations = self.get_available_destinations()
        
        results = {}
        
        for dest in destinations:
            manager = self.managers.get(dest)
            if not manager:
                logger.warning(f"Destination '{dest}' not available, skipping")
                results[dest] = {
                    'success': False,
                    'error': 'Destination not available or not enabled'
                }
                continue
            
            logger.info(f"Uploading {local_path} to {dest}")
            result = manager.upload_file(local_path, remote_path)
            results[dest] = result
            
            if result['success']:
                logger.info(f"Successfully uploaded to {dest}")
            else:
                logger.error(f"Failed to upload to {dest}: {result.get('error')}")
        
        # Determine overall success
        any_success = any(r.get('success', False) for r in results.values())
        all_success = all(r.get('success', False) for r in results.values())
        
        return {
            'success': any_success,
            'all_success': all_success,
            'destinations': results,
            'local_path': local_path,
            'remote_path': remote_path
        }
    
    def upload_directory(self, local_dir: str, remote_dir: str,
                        destinations: List[str] = None) -> Dict:
        """
        Upload a directory to one or more destinations
        
        Args:
            local_dir: Local directory path
            remote_dir: Remote directory path
            destinations: List of destination keys (None = all available)
            
        Returns:
            dict: Upload results per destination
        """
        if destinations is None:
            destinations = self.get_available_destinations()
        
        results = {}
        
        for dest in destinations:
            manager = self.managers.get(dest)
            if not manager:
                logger.warning(f"Destination '{dest}' not available, skipping")
                results[dest] = {
                    'success': False,
                    'error': 'Destination not available or not enabled'
                }
                continue
            
            logger.info(f"Uploading directory {local_dir} to {dest}")
            result = manager.upload_directory(local_dir, remote_dir)
            results[dest] = result
            
            if result['success']:
                logger.info(f"Successfully uploaded directory to {dest}")
            else:
                logger.error(f"Failed to upload directory to {dest}: {result.get('error')}")
        
        any_success = any(r.get('success', False) for r in results.values())
        all_success = all(r.get('success', False) for r in results.values())
        
        return {
            'success': any_success,
            'all_success': all_success,
            'destinations': results,
            'local_dir': local_dir,
            'remote_dir': remote_dir
        }
    
    def check_file_exists(self, remote_path: str, destination: str):
        """
        Check if a file exists at a specific destination
        
        Args:
            remote_path: Remote file path
            destination: Destination key
            
        Returns:
            tuple: (exists: bool, size: Optional[int])
        """
        manager = self.managers.get(destination)
        if not manager:
            logger.warning(f"Destination '{destination}' not available")
            return False, None
        
        return manager.check_file_exists(remote_path)
    
    def list_files(self, remote_path: str, destination: str) -> Dict:
        """
        List files at a destination
        
        Args:
            remote_path: Remote path to list
            destination: Destination key
            
        Returns:
            dict: List result with files
        """
        manager = self.managers.get(destination)
        if not manager:
            return {
                'success': False,
                'error': f"Destination '{destination}' not available"
            }
        
        return manager.list_files(remote_path)
    
    def get_destination_info(self) -> Dict:
        """
        Get information about all destinations
        
        Returns:
            dict: Information per destination
        """
        info = {}
        
        for dest_key, manager in self.managers.items():
            try:
                size_info = manager.get_bucket_size()
                info[dest_key] = {
                    'available': True,
                    'bucket': manager.bucket_name,
                    'remote_name': manager.remote_name,
                    'size_info': size_info
                }
            except Exception as e:
                info[dest_key] = {
                    'available': True,
                    'error': str(e)
                }
        
        return info


def create_storage_manager(config: Dict) -> StorageManager:
    """
    Factory function to create StorageManager instance
    
    Args:
        config: Configuration dictionary
        
    Returns:
        StorageManager instance
    """
    return StorageManager(config)
