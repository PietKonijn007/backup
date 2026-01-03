"""
Rclone Integration for AWS S3
Handles file uploads and management using rclone
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.utils.logger import setup_logger

logger = setup_logger('rclone')


class RcloneManager:
    """Manages rclone operations for AWS S3"""
    
    def __init__(self, config: Dict):
        """
        Initialize rclone manager
        
        Args:
            config: Configuration dictionary with AWS S3 settings
        """
        self.config = config
        self.aws_config = config.get('destinations', {}).get('aws_s3', {})
        self.remote_name = 'aws-s3'
        self._ensure_rclone_installed()
        self._configure_remote()
    
    def _ensure_rclone_installed(self):
        """Check if rclone is installed"""
        try:
            result = subprocess.run(['rclone', 'version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                logger.info(f"Rclone found: {version}")
            else:
                raise FileNotFoundError("Rclone not properly installed")
        except FileNotFoundError:
            logger.error("Rclone not found. Please install: https://rclone.org/install/")
            raise
        except Exception as e:
            logger.error(f"Error checking rclone: {e}")
            raise
    
    def _configure_remote(self):
        """Configure rclone remote for AWS S3"""
        try:
            # Check if remote already exists
            result = subprocess.run(['rclone', 'listremotes'], 
                                  capture_output=True, 
                                  text=True,
                                  timeout=10)
            
            remotes = result.stdout.strip().split('\n')
            if f'{self.remote_name}:' in remotes:
                logger.info(f"Rclone remote '{self.remote_name}' already configured")
                return
            
            # Create remote configuration
            logger.info(f"Configuring rclone remote '{self.remote_name}' for AWS S3")
            
            # Build rclone config command
            config_commands = [
                f"rclone config create {self.remote_name} s3",
                f"provider=AWS",
                f"access_key_id={os.getenv('AWS_ACCESS_KEY_ID', '')}",
                f"secret_access_key={os.getenv('AWS_SECRET_ACCESS_KEY', '')}",
                f"region={self.aws_config.get('region', 'us-east-1')}",
                f"storage_class={self.aws_config.get('storage_class', 'INTELLIGENT_TIERING')}"
            ]
            
            # Use environment variables for AWS credentials
            env = os.environ.copy()
            
            # Create config using rclone's config create command
            cmd = [
                'rclone', 'config', 'create', self.remote_name, 's3',
                'provider', 'AWS',
                'access_key_id', env.get('AWS_ACCESS_KEY_ID', ''),
                'secret_access_key', env.get('AWS_SECRET_ACCESS_KEY', ''),
                'region', self.aws_config.get('region', 'us-east-1'),
                'storage_class', self.aws_config.get('storage_class', 'INTELLIGENT_TIERING')
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Successfully configured rclone remote '{self.remote_name}'")
            else:
                logger.warning(f"Remote configuration output: {result.stderr}")
                # Remote might already exist or config might be manual
                
        except Exception as e:
            logger.error(f"Error configuring rclone remote: {e}")
            raise
    
    def upload_file(self, local_path: str, remote_path: str = None) -> Dict:
        """
        Upload a file to AWS S3
        
        Args:
            local_path: Local file path
            remote_path: Remote path in S3 (optional, uses local filename if not provided)
            
        Returns:
            dict: Upload result with success status and details
        """
        try:
            if not os.path.exists(local_path):
                return {'success': False, 'error': f'File not found: {local_path}'}
            
            # Determine remote path
            if remote_path is None:
                remote_path = Path(local_path).name
            
            # Build S3 path
            bucket = self.aws_config.get('bucket', 'my-backup-bucket')
            s3_path = f"{self.remote_name}:{bucket}/{remote_path}"
            
            # Get file size for progress
            file_size = os.path.getsize(local_path)
            
            logger.info(f"Uploading {local_path} ({self._format_size(file_size)}) to {s3_path}")
            
            # Upload with rclone copy (with progress and stats)
            cmd = [
                'rclone', 'copy',
                local_path,
                s3_path,
                '--progress',
                '--stats', '5s',
                '--transfers', '4',
                '--checkers', '8',
                '--s3-storage-class', self.aws_config.get('storage_class', 'INTELLIGENT_TIERING')
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                logger.info(f"Successfully uploaded {local_path} to S3")
                return {
                    'success': True,
                    'local_path': local_path,
                    'remote_path': s3_path,
                    'size': file_size,
                    'size_formatted': self._format_size(file_size)
                }
            else:
                error_msg = result.stderr or 'Unknown error'
                logger.error(f"Upload failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'local_path': local_path
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"Upload timed out for {local_path}")
            return {'success': False, 'error': 'Upload timeout', 'local_path': local_path}
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {'success': False, 'error': str(e), 'local_path': local_path}
    
    def upload_directory(self, local_dir: str, remote_dir: str = None) -> Dict:
        """
        Upload a directory to AWS S3
        
        Args:
            local_dir: Local directory path
            remote_dir: Remote directory path in S3 (optional)
            
        Returns:
            dict: Upload result with success status and statistics
        """
        try:
            if not os.path.exists(local_dir):
                return {'success': False, 'error': f'Directory not found: {local_dir}'}
            
            # Determine remote path
            if remote_dir is None:
                remote_dir = Path(local_dir).name
            
            # Build S3 path
            bucket = self.aws_config.get('bucket', 'my-backup-bucket')
            s3_path = f"{self.remote_name}:{bucket}/{remote_dir}"
            
            logger.info(f"Uploading directory {local_dir} to {s3_path}")
            
            # Sync with rclone (more efficient for directories)
            cmd = [
                'rclone', 'sync',
                local_dir,
                s3_path,
                '--progress',
                '--stats', '10s',
                '--transfers', '4',
                '--checkers', '8',
                '--s3-storage-class', self.aws_config.get('storage_class', 'INTELLIGENT_TIERING'),
                '--create-empty-src-dirs'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
            
            if result.returncode == 0:
                # Parse stats from output
                stats = self._parse_rclone_stats(result.stderr)
                logger.info(f"Successfully synced {local_dir} to S3: {stats}")
                
                return {
                    'success': True,
                    'local_dir': local_dir,
                    'remote_dir': s3_path,
                    'stats': stats
                }
            else:
                error_msg = result.stderr or 'Unknown error'
                logger.error(f"Directory sync failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'local_dir': local_dir
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"Directory sync timed out for {local_dir}")
            return {'success': False, 'error': 'Sync timeout', 'local_dir': local_dir}
        except Exception as e:
            logger.error(f"Error syncing directory: {e}")
            return {'success': False, 'error': str(e), 'local_dir': local_dir}
    
    def list_files(self, remote_path: str = '') -> Dict:
        """
        List files in S3 bucket
        
        Args:
            remote_path: Remote path to list (optional)
            
        Returns:
            dict: List result with files
        """
        try:
            bucket = self.aws_config.get('bucket', 'my-backup-bucket')
            s3_path = f"{self.remote_name}:{bucket}/{remote_path}"
            
            cmd = ['rclone', 'lsjson', s3_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                files = json.loads(result.stdout)
                logger.info(f"Listed {len(files)} files from {s3_path}")
                return {
                    'success': True,
                    'files': files,
                    'count': len(files)
                }
            else:
                error_msg = result.stderr or 'Unknown error'
                logger.error(f"List files failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_file_exists(self, remote_path: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a file exists in S3 and get its size
        
        Args:
            remote_path: Remote file path
            
        Returns:
            tuple: (exists: bool, size: Optional[int]) - True if file exists, and its size in bytes
        """
        try:
            bucket = self.aws_config.get('bucket', 'my-backup-bucket')
            s3_path = f"{self.remote_name}:{bucket}/{remote_path}"
            
            # Use lsjson to get file details including size
            cmd = ['rclone', 'lsjson', s3_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    files = json.loads(result.stdout)
                    if files and len(files) > 0:
                        # File exists, return True and its size
                        size = files[0].get('Size', 0)
                        logger.debug(f"File exists in S3: {remote_path} (size: {self._format_size(size)})")
                        return True, size
                except json.JSONDecodeError:
                    pass
            
            return False, None
                
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False, None
    
    def get_bucket_size(self) -> Dict:
        """
        Get total size of files in S3 bucket
        
        Returns:
            dict: Size information
        """
        try:
            bucket = self.aws_config.get('bucket', 'my-backup-bucket')
            s3_path = f"{self.remote_name}:{bucket}"
            
            cmd = ['rclone', 'size', s3_path, '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    'success': True,
                    'count': data.get('count', 0),
                    'bytes': data.get('bytes', 0),
                    'size_formatted': self._format_size(data.get('bytes', 0))
                }
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            logger.error(f"Error getting bucket size: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_file(self, remote_path: str) -> Dict:
        """
        Delete a file from S3
        
        Args:
            remote_path: Remote file path
            
        Returns:
            dict: Deletion result
        """
        try:
            bucket = self.aws_config.get('bucket', 'my-backup-bucket')
            s3_path = f"{self.remote_name}:{bucket}/{remote_path}"
            
            logger.info(f"Deleting {s3_path}")
            
            cmd = ['rclone', 'deletefile', s3_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"Successfully deleted {s3_path}")
                return {'success': True, 'remote_path': s3_path}
            else:
                error_msg = result.stderr or 'Unknown error'
                logger.error(f"Delete failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    @staticmethod
    def _parse_rclone_stats(output: str) -> Dict:
        """Parse statistics from rclone output"""
        stats = {
            'transferred': 0,
            'errors': 0,
            'checks': 0
        }
        
        try:
            for line in output.split('\n'):
                if 'Transferred:' in line:
                    # Extract transferred count
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'Transferred:' and i + 1 < len(parts):
                            try:
                                stats['transferred'] = int(parts[i + 1].split('/')[0])
                            except:
                                pass
                elif 'Errors:' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'Errors:' and i + 1 < len(parts):
                            try:
                                stats['errors'] = int(parts[i + 1])
                            except:
                                pass
                elif 'Checks:' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'Checks:' and i + 1 < len(parts):
                            try:
                                stats['checks'] = int(parts[i + 1].split('/')[0])
                            except:
                                pass
        except Exception as e:
            logger.warning(f"Error parsing rclone stats: {e}")
        
        return stats


def create_rclone_manager(config: Dict) -> RcloneManager:
    """
    Factory function to create RcloneManager instance
    
    Args:
        config: Configuration dictionary
        
    Returns:
        RcloneManager instance
    """
    return RcloneManager(config)
