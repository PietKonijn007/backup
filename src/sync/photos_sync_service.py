"""
Photos Sync Service - DEPRECATED
⚠️ THIS MODULE IS NO LONGER FUNCTIONAL ⚠️

Google deprecated the Photos Library API on March 31, 2025.
The new Photos Picker API does not support automated backup use cases.

For alternative solutions, see: GOOGLE_PHOTOS_API_DEPRECATION.md

This file is kept for reference only.
"""
import os
import tempfile
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from src.google_sync.photos import create_photos_manager
from src.storage.rclone_manager import create_rclone_manager
from src.utils.logger import setup_logger

logger = setup_logger('photos-sync-service')


class PhotosSyncService:
    """Manages syncing photos from Google Photos to AWS S3"""
    
    def __init__(self, config, google_credentials):
        """
        Initialize photos sync service
        
        Args:
            config: Configuration dictionary
            google_credentials: Google OAuth credentials
        """
        self.config = config
        self.photos_manager = create_photos_manager(google_credentials)
        self.rclone_manager = create_rclone_manager(config)
        self.temp_dir = config.get('sync', {}).get('temp_dir', '/tmp/backup-sync')
        
        # Create temp directory
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Photos sync service initialized with temp dir: {self.temp_dir}")
    
    def sync_media_item(self, media_id: str, remote_path: str = None) -> Dict:
        """
        Sync a single media item from Google Photos to S3
        
        Args:
            media_id: Google Photos media item ID
            remote_path: Optional S3 path (if None, organizes by date)
            
        Returns:
            dict: Sync result
        """
        try:
            logger.info(f"Starting sync for media item ID: {media_id}")
            
            # Get media item metadata
            metadata = self.photos_manager.get_media_item(media_id)
            filename = metadata['filename']
            
            logger.info(f"Syncing media: {filename}")
            
            # Download from Google Photos
            logger.info(f"Downloading from Google Photos...")
            download_result = self.photos_manager.download_media_item(media_id, self.temp_dir)
            
            if not download_result['success']:
                return {
                    'success': False,
                    'error': f"Download failed: {download_result.get('error')}",
                    'filename': filename
                }
            
            local_path = download_result['file_path']
            
            # Determine S3 path
            if remote_path is None:
                # Organize by date: google-photos/YYYY/MM/DD/filename
                remote_path = self._build_date_organized_path(metadata, filename)
                logger.info(f"Using date-organized path: {remote_path}")
            
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
                logger.info(f"Successfully synced {filename} to S3")
                return {
                    'success': True,
                    'filename': filename,
                    'media_id': media_id,
                    'size': upload_result['size'],
                    'size_formatted': upload_result['size_formatted'],
                    'remote_path': upload_result['remote_path'],
                    'media_type': metadata['media_type'],
                    'creation_time': metadata['creation_time']
                }
            else:
                return {
                    'success': False,
                    'error': f"Upload failed: {upload_result.get('error')}",
                    'filename': filename
                }
                
        except Exception as e:
            logger.error(f"Error syncing media item {media_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'media_id': media_id
            }
    
    def sync_multiple_media(self, media_ids: List[str]) -> Dict:
        """
        Sync multiple media items from Google Photos to S3
        
        Args:
            media_ids: List of Google Photos media item IDs
            
        Returns:
            dict: Sync results with statistics
        """
        logger.info(f"Starting batch sync for {len(media_ids)} media items")
        
        results = []
        success_count = 0
        error_count = 0
        total_size = 0
        
        for i, media_id in enumerate(media_ids, 1):
            logger.info(f"Processing media {i}/{len(media_ids)}")
            result = self.sync_media_item(media_id)
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
                'total': len(media_ids),
                'success': success_count,
                'failed': error_count,
                'total_size': total_size,
                'total_size_formatted': self._format_size(total_size)
            }
        }
    
    def sync_album(self, album_id: str, remote_base_path: str = None) -> Dict:
        """
        Sync an entire album from Google Photos to S3
        
        Args:
            album_id: Google Photos album ID
            remote_base_path: Base path in S3 (optional, defaults to date organization)
            
        Returns:
            dict: Sync results
        """
        try:
            logger.info(f"Starting album sync for album ID: {album_id}")
            
            # Get all media items in album
            logger.info(f"Fetching all media items from album...")
            media_items = self.photos_manager.list_all_media_items(album_id=album_id)
            
            if not media_items:
                logger.warning(f"No media items found in album {album_id}")
                return {
                    'success': False,
                    'error': 'No media items found in album'
                }
            
            logger.info(f"Found {len(media_items)} media items in album")
            
            # Sync each media item
            results = []
            success_count = 0
            total_size = 0
            
            for i, item in enumerate(media_items, 1):
                logger.info(f"Processing media {i}/{len(media_items)}: {item['filename']}")
                
                # Build custom path if remote_base_path specified
                if remote_base_path:
                    custom_path = f"{remote_base_path}/{item['filename']}"
                else:
                    custom_path = None  # Will use date organization
                
                result = self.sync_media_item(item['id'], remote_path=custom_path)
                results.append(result)
                
                if result['success']:
                    success_count += 1
                    total_size += result.get('size', 0)
            
            logger.info(f"Album sync complete: {success_count}/{len(media_items)} items synced")
            
            return {
                'success': True,
                'album_id': album_id,
                'results': results,
                'statistics': {
                    'total': len(media_items),
                    'success': success_count,
                    'failed': len(media_items) - success_count,
                    'total_size': total_size,
                    'total_size_formatted': self._format_size(total_size)
                }
            }
            
        except Exception as e:
            logger.error(f"Error syncing album {album_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'album_id': album_id
            }
    
    def sync_recent_media(self, days: int = 7, max_results: int = 100) -> Dict:
        """
        Sync recently added media items from Google Photos to S3
        
        Args:
            days: Number of days to look back
            max_results: Maximum number of media items to sync
            
        Returns:
            dict: Sync results
        """
        try:
            logger.info(f"Starting sync for recent media (last {days} days, max {max_results} items)")
            
            # Get recent media items
            recent_items = self.photos_manager.get_recent_media(days=days, max_results=max_results)
            
            if not recent_items:
                logger.warning(f"No recent media items found")
                return {
                    'success': False,
                    'error': 'No recent media items found'
                }
            
            logger.info(f"Found {len(recent_items)} recent media items")
            
            # Sync each item
            media_ids = [item['id'] for item in recent_items]
            return self.sync_multiple_media(media_ids)
            
        except Exception as e:
            logger.error(f"Error syncing recent media: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_all_photos(self, batch_size: int = 100) -> Dict:
        """
        Sync all photos from Google Photos library to S3
        
        Args:
            batch_size: Number of photos to process in each batch
            
        Returns:
            dict: Sync results
        """
        try:
            logger.info(f"Starting sync for ALL photos in Google Photos library")
            
            # Get all media items (handles pagination automatically)
            all_items = self.photos_manager.list_all_media_items()
            
            if not all_items:
                logger.warning("No media items found in Google Photos library")
                return {
                    'success': False,
                    'error': 'No media items found'
                }
            
            logger.info(f"Found {len(all_items)} total media items in library")
            
            # Sync all items
            media_ids = [item['id'] for item in all_items]
            
            # Process in batches for better progress tracking
            results = []
            success_count = 0
            total_size = 0
            
            for i in range(0, len(media_ids), batch_size):
                batch = media_ids[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(media_ids) + batch_size - 1) // batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
                
                batch_result = self.sync_multiple_media(batch)
                results.extend(batch_result['results'])
                success_count += batch_result['statistics']['success']
                total_size += batch_result['statistics']['total_size']
            
            logger.info(f"All photos sync complete: {success_count}/{len(all_items)} items synced")
            
            return {
                'success': True,
                'results': results,
                'statistics': {
                    'total': len(all_items),
                    'success': success_count,
                    'failed': len(all_items) - success_count,
                    'total_size': total_size,
                    'total_size_formatted': self._format_size(total_size)
                }
            }
            
        except Exception as e:
            logger.error(f"Error syncing all photos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_date_organized_path(self, metadata: Dict, filename: str) -> str:
        """
        Build date-organized path for S3: google-photos/YYYY/MM/DD/filename
        
        Args:
            metadata: Media item metadata
            filename: Original filename
            
        Returns:
            str: Organized S3 path
        """
        try:
            # Parse creation time (ISO format: 2024-01-15T10:30:00Z)
            creation_time = metadata.get('creation_time', '')
            
            if creation_time:
                # Parse ISO format
                dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                year = dt.strftime('%Y')
                month = dt.strftime('%m')
                day = dt.strftime('%d')
                
                return f"google-photos/{year}/{month}/{day}/{filename}"
            else:
                # Fallback to unsorted if no creation time
                return f"google-photos/unsorted/{filename}"
                
        except Exception as e:
            logger.warning(f"Error parsing creation time, using unsorted: {e}")
            return f"google-photos/unsorted/{filename}"
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def create_photos_sync_service(config: Dict, google_credentials):
    """
    Factory function to create PhotosSyncService instance
    
    Args:
        config: Configuration dictionary
        google_credentials: Google OAuth credentials
        
    Returns:
        PhotosSyncService instance
    """
    return PhotosSyncService(config, google_credentials)
