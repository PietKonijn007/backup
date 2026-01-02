"""
Google Drive API Integration
Handles listing, downloading, and syncing files from Google Drive
"""
import os
import io
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Generator
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from src.utils.logger import setup_logger

logger = setup_logger('google-drive')


class GoogleDriveManager:
    """Manages Google Drive operations"""
    
    # File type categories
    DOCUMENT_TYPES = {
        'application/vnd.google-apps.document': '.docx',
        'application/vnd.google-apps.spreadsheet': '.xlsx',
        'application/vnd.google-apps.presentation': '.pptx',
        'application/vnd.google-apps.drawing': '.png',
        'application/vnd.google-apps.script': '.json',
        'application/vnd.google-apps.form': '.zip'
    }
    
    # Export MIME types for Google Workspace files
    EXPORT_MIME_TYPES = {
        'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.google-apps.drawing': 'image/png',
        'application/vnd.google-apps.script': 'application/vnd.google-apps.script+json',
        'application/vnd.google-apps.form': 'application/zip'
    }
    
    def __init__(self, credentials):
        """
        Initialize Drive manager
        
        Args:
            credentials: Google OAuth credentials
        """
        self.credentials = credentials
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service"""
        try:
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Google Drive API service initialized")
        except Exception as e:
            logger.error(f"Error initializing Drive service: {e}")
            raise
    
    def get_storage_info(self) -> Dict:
        """
        Get Drive storage information
        
        Returns:
            dict: Storage quota information
        """
        try:
            about = self.service.about().get(fields="storageQuota,user").execute()
            quota = about.get('storageQuota', {})
            
            usage = int(quota.get('usage', 0))
            limit = int(quota.get('limit', 0))
            
            return {
                'usage': usage,
                'limit': limit,
                'usage_formatted': self._format_size(usage),
                'limit_formatted': self._format_size(limit),
                'percentage': round((usage / limit * 100), 2) if limit > 0 else 0,
                'user': about.get('user', {})
            }
        except HttpError as e:
            logger.error(f"Error getting storage info: {e}")
            raise
    
    def list_files(self, page_size: int = 100, page_token: Optional[str] = None, 
                   folder_id: Optional[str] = None, query: Optional[str] = None) -> Dict:
        """
        List files from Google Drive
        
        Args:
            page_size: Number of files per page (max 1000)
            page_token: Token for pagination
            folder_id: Optional folder ID to list files from (None = root of My Drive)
            query: Optional custom query string
            
        Returns:
            dict: Files list with metadata and next page token
        """
        try:
            # Build query
            if query:
                q = query
            elif folder_id:
                q = f"'{folder_id}' in parents and trashed=false"
            else:
                # When folder_id is None, get root-level files in My Drive
                q = "'root' in parents and trashed=false"
            
            # Request files with metadata
            fields = (
                "nextPageToken, files(id, name, mimeType, size, createdTime, "
                "modifiedTime, owners, shared, webViewLink, iconLink, thumbnailLink, "
                "parents, starred, trashed)"
            )
            
            results = self.service.files().list(
                q=q,
                pageSize=min(page_size, 1000),
                pageToken=page_token,
                fields=fields,
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            next_page_token = results.get('nextPageToken')
            
            # Enhance file metadata
            enhanced_files = []
            for file in files:
                enhanced_file = self._enhance_file_metadata(file)
                enhanced_files.append(enhanced_file)
            
            logger.info(f"Listed {len(enhanced_files)} files from Drive")
            
            return {
                'files': enhanced_files,
                'next_page_token': next_page_token,
                'total_count': len(enhanced_files)
            }
        
        except HttpError as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    def list_all_files(self, folder_id: Optional[str] = None) -> List[Dict]:
        """
        List all files from Google Drive (handles pagination automatically)
        
        Args:
            folder_id: Optional folder ID to list files from
            
        Returns:
            list: All files
        """
        all_files = []
        page_token = None
        
        while True:
            result = self.list_files(page_size=1000, page_token=page_token, folder_id=folder_id)
            all_files.extend(result['files'])
            
            page_token = result.get('next_page_token')
            if not page_token:
                break
        
        logger.info(f"Retrieved total of {len(all_files)} files from Drive")
        return all_files
    
    def get_file_metadata(self, file_id: str) -> Dict:
        """
        Get detailed metadata for a specific file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            dict: File metadata
        """
        try:
            fields = (
                "id, name, mimeType, size, createdTime, modifiedTime, "
                "owners, shared, webViewLink, iconLink, thumbnailLink, "
                "parents, starred, trashed, description, version, "
                "permissions, capabilities"
            )
            
            file = self.service.files().get(
                fileId=file_id,
                fields=fields
            ).execute()
            
            return self._enhance_file_metadata(file)
        
        except HttpError as e:
            logger.error(f"Error getting file metadata for {file_id}: {e}")
            raise
    
    def download_file(self, file_id: str, destination_path: str, 
                     file_name: Optional[str] = None, mime_type: Optional[str] = None) -> Dict:
        """
        Download a file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            destination_path: Local directory to save file
            file_name: Optional custom file name
            mime_type: File MIME type (needed for Google Workspace files)
            
        Returns:
            dict: Download result with file path and size
        """
        try:
            # Get file metadata if not provided
            if not file_name or not mime_type:
                metadata = self.get_file_metadata(file_id)
                file_name = file_name or metadata['name']
                mime_type = mime_type or metadata['mime_type']
            
            # Create destination directory
            Path(destination_path).mkdir(parents=True, exist_ok=True)
            
            # Check if it's a Google Workspace file that needs export
            is_google_doc = mime_type in self.EXPORT_MIME_TYPES
            
            if is_google_doc:
                # Export Google Workspace file
                export_mime_type = self.EXPORT_MIME_TYPES[mime_type]
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType=export_mime_type
                )
                
                # Add proper extension if not present
                if mime_type in self.DOCUMENT_TYPES:
                    extension = self.DOCUMENT_TYPES[mime_type]
                    if not file_name.endswith(extension):
                        file_name += extension
            else:
                # Download regular file
                request = self.service.files().get_media(fileId=file_id)
            
            # Build full path
            file_path = os.path.join(destination_path, file_name)
            
            # Download file with progress tracking
            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            progress = 0
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Download progress: {progress}%")
            
            fh.close()
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            logger.info(f"Downloaded file {file_name} ({self._format_size(file_size)})")
            
            return {
                'success': True,
                'file_path': file_path,
                'file_name': file_name,
                'size': file_size,
                'size_formatted': self._format_size(file_size)
            }
        
        except HttpError as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error downloading file {file_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_folder(self, folder_id: str, destination_path: str, 
                       recursive: bool = True) -> Generator[Dict, None, None]:
        """
        Download all files from a folder
        
        Args:
            folder_id: Google Drive folder ID
            destination_path: Local directory to save files
            recursive: Whether to download subfolders
            
        Yields:
            dict: Download result for each file
        """
        try:
            # List all files in folder
            files = self.list_all_files(folder_id=folder_id)
            
            for file in files:
                if file['mime_type'] == 'application/vnd.google-apps.folder':
                    if recursive:
                        # Create subfolder
                        subfolder_path = os.path.join(destination_path, file['name'])
                        Path(subfolder_path).mkdir(parents=True, exist_ok=True)
                        
                        # Download folder contents recursively
                        yield from self.download_folder(
                            file['id'],
                            subfolder_path,
                            recursive=True
                        )
                else:
                    # Download file
                    result = self.download_file(
                        file['id'],
                        destination_path,
                        file['name'],
                        file['mime_type']
                    )
                    yield result
        
        except Exception as e:
            logger.error(f"Error downloading folder {folder_id}: {e}")
            yield {
                'success': False,
                'error': str(e)
            }
    
    def search_files(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search for files in Drive
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            list: Matching files
        """
        try:
            # Build search query
            search_query = f"name contains '{query}' and trashed=false"
            
            result = self.list_files(
                page_size=max_results,
                query=search_query
            )
            
            logger.info(f"Found {len(result['files'])} files matching '{query}'")
            return result['files']
        
        except HttpError as e:
            logger.error(f"Error searching files: {e}")
            raise
    
    def get_recent_files(self, days: int = 7, max_results: int = 50) -> List[Dict]:
        """
        Get recently modified files
        
        Args:
            days: Number of days to look back
            max_results: Maximum number of results
            
        Returns:
            list: Recently modified files
        """
        try:
            from datetime import timedelta
            
            # Calculate date threshold
            threshold = datetime.utcnow() - timedelta(days=days)
            threshold_str = threshold.strftime('%Y-%m-%dT%H:%M:%S')
            
            query = f"modifiedTime > '{threshold_str}' and trashed=false"
            
            result = self.list_files(
                page_size=max_results,
                query=query
            )
            
            logger.info(f"Found {len(result['files'])} files modified in last {days} days")
            return result['files']
        
        except HttpError as e:
            logger.error(f"Error getting recent files: {e}")
            raise
    
    def _enhance_file_metadata(self, file: Dict) -> Dict:
        """
        Enhance file metadata with additional information
        
        Args:
            file: Raw file metadata from API
            
        Returns:
            dict: Enhanced file metadata
        """
        mime_type = file.get('mimeType', '')
        size = int(file.get('size', 0))
        
        # Determine file type
        is_folder = mime_type == 'application/vnd.google-apps.folder'
        is_google_doc = mime_type.startswith('application/vnd.google-apps.')
        
        enhanced = {
            'id': file.get('id'),
            'name': file.get('name'),
            'mime_type': mime_type,
            'size': size,
            'size_formatted': self._format_size(size) if size > 0 else 'N/A',
            'created_time': file.get('createdTime'),
            'modified_time': file.get('modifiedTime'),
            'web_view_link': file.get('webViewLink'),
            'icon_link': file.get('iconLink'),
            'thumbnail_link': file.get('thumbnailLink'),
            'parents': file.get('parents', []),
            'owners': file.get('owners', []),
            'shared': file.get('shared', False),
            'starred': file.get('starred', False),
            'trashed': file.get('trashed', False),
            'is_folder': is_folder,
            'is_google_doc': is_google_doc,
            'file_type': self._get_file_type(mime_type),
            'downloadable': not is_folder
        }
        
        return enhanced
    
    def _get_file_type(self, mime_type: str) -> str:
        """Get human-readable file type"""
        type_map = {
            'application/vnd.google-apps.folder': 'Folder',
            'application/vnd.google-apps.document': 'Google Doc',
            'application/vnd.google-apps.spreadsheet': 'Google Sheet',
            'application/vnd.google-apps.presentation': 'Google Slides',
            'application/vnd.google-apps.form': 'Google Form',
            'application/vnd.google-apps.drawing': 'Google Drawing',
            'application/pdf': 'PDF',
            'image/jpeg': 'JPEG Image',
            'image/png': 'PNG Image',
            'video/mp4': 'MP4 Video',
            'text/plain': 'Text File',
        }
        
        return type_map.get(mime_type, mime_type.split('/')[-1].upper())
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"


def create_drive_manager(credentials):
    """
    Factory function to create DriveManager instance
    
    Args:
        credentials: Google OAuth credentials
        
    Returns:
        GoogleDriveManager instance
    """
    return GoogleDriveManager(credentials)
