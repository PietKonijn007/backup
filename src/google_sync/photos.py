"""
Google Photos API Integration
Handles listing, downloading, and syncing photos/videos from Google Photos
"""
import os
import io
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Generator
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.utils.logger import setup_logger

logger = setup_logger('google-photos')


class GooglePhotosManager:
    """Manages Google Photos operations"""
    
    def __init__(self, credentials):
        """
        Initialize Photos manager
        
        Args:
            credentials: Google OAuth credentials
        """
        self.credentials = credentials
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Photos API service"""
        try:
            # Photos API requires static_discovery=False
            self.service = build('photoslibrary', 'v1', 
                               credentials=self.credentials, 
                               static_discovery=False)
            logger.info("Google Photos API service initialized")
        except Exception as e:
            logger.error(f"Error initializing Photos service: {e}")
            raise
    
    def list_media_items(self, page_size: int = 100, page_token: Optional[str] = None,
                        album_id: Optional[str] = None) -> Dict:
        """
        List media items from Google Photos
        
        Args:
            page_size: Number of items per page (max 100)
            page_token: Token for pagination
            album_id: Optional album ID to list items from
            
        Returns:
            dict: Media items with metadata and next page token
        """
        try:
            if album_id:
                # List items from specific album
                body = {
                    'albumId': album_id,
                    'pageSize': min(page_size, 100)
                }
                if page_token:
                    body['pageToken'] = page_token
                
                results = self.service.mediaItems().search(body=body).execute()
            else:
                # List all media items
                results = self.service.mediaItems().list(
                    pageSize=min(page_size, 100),
                    pageToken=page_token
                ).execute()
            
            media_items = results.get('mediaItems', [])
            next_page_token = results.get('nextPageToken')
            
            # Enhance metadata
            enhanced_items = []
            for item in media_items:
                enhanced_item = self._enhance_media_metadata(item)
                enhanced_items.append(enhanced_item)
            
            logger.info(f"Listed {len(enhanced_items)} media items from Photos")
            
            return {
                'items': enhanced_items,
                'next_page_token': next_page_token,
                'total_count': len(enhanced_items)
            }
        
        except HttpError as e:
            logger.error(f"Error listing media items: {e}")
            raise
    
    def list_all_media_items(self, album_id: Optional[str] = None) -> List[Dict]:
        """
        List all media items (handles pagination automatically)
        
        Args:
            album_id: Optional album ID to list items from
            
        Returns:
            list: All media items
        """
        all_items = []
        page_token = None
        
        while True:
            result = self.list_media_items(page_size=100, page_token=page_token, album_id=album_id)
            all_items.extend(result['items'])
            
            page_token = result.get('next_page_token')
            if not page_token:
                break
        
        logger.info(f"Retrieved total of {len(all_items)} media items from Photos")
        return all_items
    
    def list_albums(self, page_size: int = 50, page_token: Optional[str] = None) -> Dict:
        """
        List albums from Google Photos
        
        Args:
            page_size: Number of albums per page (max 50)
            page_token: Token for pagination
            
        Returns:
            dict: Albums with metadata and next page token
        """
        try:
            results = self.service.albums().list(
                pageSize=min(page_size, 50),
                pageToken=page_token
            ).execute()
            
            albums = results.get('albums', [])
            next_page_token = results.get('nextPageToken')
            
            # Enhance album metadata
            enhanced_albums = []
            for album in albums:
                enhanced_album = {
                    'id': album.get('id'),
                    'title': album.get('title'),
                    'product_url': album.get('productUrl'),
                    'cover_photo_url': album.get('coverPhotoBaseUrl'),
                    'media_items_count': int(album.get('mediaItemsCount', 0)),
                    'is_writable': album.get('isWriteable', False)
                }
                enhanced_albums.append(enhanced_album)
            
            logger.info(f"Listed {len(enhanced_albums)} albums from Photos")
            
            return {
                'albums': enhanced_albums,
                'next_page_token': next_page_token,
                'total_count': len(enhanced_albums)
            }
        
        except HttpError as e:
            logger.error(f"Error listing albums: {e}")
            raise
    
    def get_media_item(self, media_item_id: str) -> Dict:
        """
        Get metadata for a specific media item
        
        Args:
            media_item_id: Google Photos media item ID
            
        Returns:
            dict: Media item metadata
        """
        try:
            item = self.service.mediaItems().get(mediaItemId=media_item_id).execute()
            return self._enhance_media_metadata(item)
        
        except HttpError as e:
            logger.error(f"Error getting media item {media_item_id}: {e}")
            raise
    
    def download_media_item(self, media_item_id: str, destination_path: str,
                           file_name: Optional[str] = None) -> Dict:
        """
        Download a media item from Google Photos
        
        Args:
            media_item_id: Google Photos media item ID
            destination_path: Local directory to save file
            file_name: Optional custom file name
            
        Returns:
            dict: Download result with file path and size
        """
        try:
            # Get media item metadata
            item = self.get_media_item(media_item_id)
            
            # Determine filename
            if not file_name:
                file_name = item['filename']
            
            # Create destination directory
            Path(destination_path).mkdir(parents=True, exist_ok=True)
            
            # Build download URL
            base_url = item['base_url']
            
            # Add download parameters based on media type
            if item['is_video']:
                download_url = f"{base_url}=dv"  # Download video
            else:
                # Download image at original quality
                download_url = f"{base_url}=d"
            
            # Download file
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Save file
            file_path = os.path.join(destination_path, file_name)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            logger.info(f"Downloaded media item {file_name} ({self._format_size(file_size)})")
            
            return {
                'success': True,
                'file_path': file_path,
                'file_name': file_name,
                'size': file_size,
                'size_formatted': self._format_size(file_size),
                'media_type': 'video' if item['is_video'] else 'photo'
            }
        
        except Exception as e:
            logger.error(f"Error downloading media item {media_item_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_album(self, album_id: str, destination_path: str) -> Generator[Dict, None, None]:
        """
        Download all media items from an album
        
        Args:
            album_id: Google Photos album ID
            destination_path: Local directory to save files
            
        Yields:
            dict: Download result for each media item
        """
        try:
            # List all items in album
            items = self.list_all_media_items(album_id=album_id)
            
            for item in items:
                result = self.download_media_item(
                    item['id'],
                    destination_path,
                    item['filename']
                )
                yield result
        
        except Exception as e:
            logger.error(f"Error downloading album {album_id}: {e}")
            yield {
                'success': False,
                'error': str(e)
            }
    
    def search_media_items(self, filters: Dict, page_size: int = 100) -> List[Dict]:
        """
        Search for media items with filters
        
        Args:
            filters: Search filters (date, content category, etc.)
            page_size: Number of items per page
            
        Returns:
            list: Matching media items
        """
        try:
            body = {
                'pageSize': min(page_size, 100),
                'filters': filters
            }
            
            results = self.service.mediaItems().search(body=body).execute()
            media_items = results.get('mediaItems', [])
            
            enhanced_items = []
            for item in media_items:
                enhanced_item = self._enhance_media_metadata(item)
                enhanced_items.append(enhanced_item)
            
            logger.info(f"Found {len(enhanced_items)} media items matching filters")
            return enhanced_items
        
        except HttpError as e:
            logger.error(f"Error searching media items: {e}")
            raise
    
    def get_recent_media(self, days: int = 7, max_results: int = 50) -> List[Dict]:
        """
        Get recently added media items
        
        Args:
            days: Number of days to look back
            max_results: Maximum number of results
            
        Returns:
            list: Recently added media items
        """
        try:
            from datetime import timedelta
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Build date filter
            filters = {
                'dateFilter': {
                    'ranges': [{
                        'startDate': {
                            'year': start_date.year,
                            'month': start_date.month,
                            'day': start_date.day
                        },
                        'endDate': {
                            'year': end_date.year,
                            'month': end_date.month,
                            'day': end_date.day
                        }
                    }]
                }
            }
            
            items = self.search_media_items(filters, page_size=max_results)
            logger.info(f"Found {len(items)} media items from last {days} days")
            return items
        
        except Exception as e:
            logger.error(f"Error getting recent media: {e}")
            raise
    
    def get_photos_by_category(self, category: str, max_results: int = 50) -> List[Dict]:
        """
        Get photos by content category
        
        Categories: NONE, LANDSCAPES, RECEIPTS, CITYSCAPES, LANDMARKS, 
                   SELFIES, PEOPLE, PETS, WEDDINGS, BIRTHDAYS, DOCUMENTS,
                   TRAVEL, ANIMALS, FOOD, SPORT, NIGHT, PERFORMANCES, 
                   WHITEBOARDS, SCREENSHOTS, UTILITY, ARTS, CRAFTS, FASHION, 
                   HOUSES, GARDENS, FLOWERS, HOLIDAYS
        
        Args:
            category: Content category
            max_results: Maximum number of results
            
        Returns:
            list: Media items in category
        """
        try:
            filters = {
                'contentFilter': {
                    'includedContentCategories': [category.upper()]
                }
            }
            
            items = self.search_media_items(filters, page_size=max_results)
            logger.info(f"Found {len(items)} media items in category {category}")
            return items
        
        except Exception as e:
            logger.error(f"Error getting photos by category: {e}")
            raise
    
    def _enhance_media_metadata(self, item: Dict) -> Dict:
        """
        Enhance media item metadata with additional information
        
        Args:
            item: Raw media item from API
            
        Returns:
            dict: Enhanced media item metadata
        """
        media_metadata = item.get('mediaMetadata', {})
        
        # Determine media type
        is_video = 'video' in media_metadata
        is_photo = 'photo' in media_metadata
        
        # Get dimensions
        width = int(media_metadata.get('width', 0))
        height = int(media_metadata.get('height', 0))
        
        # Get creation time
        creation_time = media_metadata.get('creationTime', '')
        
        # Build enhanced metadata
        enhanced = {
            'id': item.get('id'),
            'filename': item.get('filename'),
            'base_url': item.get('baseUrl'),
            'product_url': item.get('productUrl'),
            'mime_type': item.get('mimeType', ''),
            'is_video': is_video,
            'is_photo': is_photo,
            'media_type': 'video' if is_video else 'photo',
            'width': width,
            'height': height,
            'resolution': f"{width}x{height}" if width and height else 'Unknown',
            'creation_time': creation_time,
            'description': item.get('description', ''),
        }
        
        # Add video-specific metadata
        if is_video:
            video_metadata = media_metadata.get('video', {})
            enhanced['duration_seconds'] = float(video_metadata.get('fps', 0))
            enhanced['video_codec'] = video_metadata.get('cameraMake', 'Unknown')
        
        # Add photo-specific metadata
        if is_photo:
            photo_metadata = media_metadata.get('photo', {})
            enhanced['camera_make'] = photo_metadata.get('cameraMake', '')
            enhanced['camera_model'] = photo_metadata.get('cameraModel', '')
            enhanced['focal_length'] = photo_metadata.get('focalLength', 0)
            enhanced['aperture'] = photo_metadata.get('apertureFNumber', 0)
            enhanced['iso'] = photo_metadata.get('isoEquivalent', 0)
        
        return enhanced
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def create_photos_manager(credentials):
    """
    Factory function to create PhotosManager instance
    
    Args:
        credentials: Google OAuth credentials
        
    Returns:
        GooglePhotosManager instance
    """
    return GooglePhotosManager(credentials)
