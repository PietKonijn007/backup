"""
Real-time bucket inspection for AWS S3 and Backblaze B2
"""
import yaml
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger('bucket-inspector')


def load_config():
    """Load configuration from yaml file"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config.yaml not found")
        return {}


def get_aws_s3_stats():
    """Get real-time statistics from AWS S3 bucket"""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        config = load_config()
        aws_config = config.get('destinations', {}).get('aws_s3', {})
        
        if not aws_config.get('enabled', False):
            return {'enabled': False, 'error': 'AWS S3 not enabled in config'}
        
        bucket_name = aws_config.get('bucket')
        if not bucket_name:
            return {'enabled': False, 'error': 'AWS S3 bucket not configured'}
        
        # Create S3 client
        s3_client = boto3.client('s3')
        
        # Get bucket statistics
        total_files = 0
        total_size = 0
        files_by_status = {'synced': 0, 'pending': 0, 'failed': 0}
        
        # List all objects in bucket
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    total_files += 1
                    total_size += obj['Size']
                    # All files in bucket are considered 'synced'
                    files_by_status['synced'] += 1
        
        return {
            'enabled': True,
            'bucket': bucket_name,
            'total_files': total_files,
            'total_size': total_size,
            'total_size_formatted': format_bytes(total_size),
            'synced': files_by_status['synced'],
            'pending': 0,  # Files in bucket are synced, pending would be in queue
            'failed': 0,   # Would need to check sync logs for failures
            'last_checked': datetime.now().isoformat()
        }
        
    except ImportError:
        return {'enabled': False, 'error': 'boto3 not installed'}
    except NoCredentialsError:
        return {'enabled': False, 'error': 'AWS credentials not configured'}
    except ClientError as e:
        return {'enabled': False, 'error': f'AWS S3 error: {str(e)}'}
    except Exception as e:
        logger.error(f"Error getting AWS S3 stats: {e}")
        return {'enabled': False, 'error': f'Unexpected error: {str(e)}'}


def get_backblaze_b2_stats():
    """Get real-time statistics from Backblaze B2 bucket"""
    try:
        import os
        from b2sdk.v2 import InMemoryAccountInfo, B2Api
        from b2sdk.v2.exception import B2Error
        
        config = load_config()
        b2_config = config.get('destinations', {}).get('backblaze_b2', {})
        
        if not b2_config.get('enabled', False):
            return {'enabled': False, 'error': 'Backblaze B2 not enabled in config'}
        
        # Try to get credentials from config first, then environment variables
        app_key_id = b2_config.get('application_key_id') or os.getenv('B2_APPLICATION_KEY_ID')
        app_key = b2_config.get('application_key') or os.getenv('B2_APPLICATION_KEY')
        bucket_name = b2_config.get('bucket')
        
        if not all([app_key_id, app_key, bucket_name]):
            missing = []
            if not app_key_id: missing.append('application_key_id (config or B2_APPLICATION_KEY_ID env)')
            if not app_key: missing.append('application_key (config or B2_APPLICATION_KEY env)')
            if not bucket_name: missing.append('bucket')
            return {'enabled': False, 'error': f'Backblaze B2 credentials missing: {", ".join(missing)}'}
        
        # Create B2 API
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", app_key_id, app_key)
        
        # Get bucket
        bucket = b2_api.get_bucket_by_name(bucket_name)
        
        # Get bucket statistics
        total_files = 0
        total_size = 0
        files_by_status = {'synced': 0, 'pending': 0, 'failed': 0}
        
        # List all files
        for file_version, folder_to_list in bucket.ls(recursive=True):
            if file_version:
                total_files += 1
                total_size += file_version.size
                # All files in bucket are considered 'synced'
                files_by_status['synced'] += 1
        
        return {
            'enabled': True,
            'bucket': bucket_name,
            'total_files': total_files,
            'total_size': total_size,
            'total_size_formatted': format_bytes(total_size),
            'synced': files_by_status['synced'],
            'pending': 0,  # Files in bucket are synced, pending would be in queue
            'failed': 0,   # Would need to check sync logs for failures
            'last_checked': datetime.now().isoformat()
        }
        
    except ImportError as e:
        return {'enabled': False, 'error': f'b2sdk import error: {str(e)} - run: pip install b2sdk'}
    except Exception as e:
        # Catch B2Error and other exceptions
        logger.error(f"Error getting Backblaze B2 stats: {e}")
        if 'B2Error' in str(type(e)) or 'b2sdk' in str(e).lower():
            return {'enabled': False, 'error': f'Backblaze B2 error: {str(e)}'}
        return {'enabled': False, 'error': f'Unexpected error: {str(e)}'}


def get_pending_and_failed_from_database():
    """Get pending and failed files from database (these aren't in buckets yet)"""
    try:
        from src.database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get pending files by destination
        cursor.execute('''
            SELECT destination, COUNT(*) as count
            FROM file_destinations 
            WHERE sync_status = 'pending' AND file_id NOT LIKE 'test-%'
            GROUP BY destination
        ''')
        pending_results = cursor.fetchall()
        
        # Get failed files by destination
        cursor.execute('''
            SELECT destination, COUNT(*) as count
            FROM file_destinations 
            WHERE sync_status = 'failed' AND file_id NOT LIKE 'test-%'
            GROUP BY destination
        ''')
        failed_results = cursor.fetchall()
        
        conn.close()
        
        # Process results
        pending_by_dest = {row[1]: row[0] for row in pending_results}
        failed_by_dest = {row[1]: row[0] for row in failed_results}
        
        return {
            'aws_s3': {
                'pending': pending_by_dest.get('aws_s3', 0),
                'failed': failed_by_dest.get('aws_s3', 0)
            },
            'backblaze_b2': {
                'pending': pending_by_dest.get('backblaze_b2', 0),
                'failed': failed_by_dest.get('backblaze_b2', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting pending/failed from database: {e}")
        return {
            'aws_s3': {'pending': 0, 'failed': 0},
            'backblaze_b2': {'pending': 0, 'failed': 0}
        }


def get_real_time_sync_statistics():
    """Get comprehensive real-time sync statistics from actual buckets and database"""
    logger.info("Getting real-time sync statistics from buckets...")
    
    # Get bucket statistics
    aws_stats = get_aws_s3_stats()
    b2_stats = get_backblaze_b2_stats()
    
    # Get pending/failed from database
    db_stats = get_pending_and_failed_from_database()
    
    # Combine statistics
    result = {
        'aws_synced': aws_stats.get('synced', 0) if aws_stats.get('enabled') else 0,
        'aws_pending': db_stats['aws_s3']['pending'],
        'aws_failed': db_stats['aws_s3']['failed'],
        'aws_size_formatted': aws_stats.get('total_size_formatted', '0 B') if aws_stats.get('enabled') else '0 B',
        'aws_file_count': aws_stats.get('total_files', 0) if aws_stats.get('enabled') else 0,
        'aws_enabled': aws_stats.get('enabled', False),
        'aws_error': aws_stats.get('error') if not aws_stats.get('enabled') else None,
        
        'b2_synced': b2_stats.get('synced', 0) if b2_stats.get('enabled') else 0,
        'b2_pending': db_stats['backblaze_b2']['pending'],
        'b2_failed': db_stats['backblaze_b2']['failed'],
        'b2_size_formatted': b2_stats.get('total_size_formatted', '0 B') if b2_stats.get('enabled') else '0 B',
        'b2_file_count': b2_stats.get('total_files', 0) if b2_stats.get('enabled') else 0,
        'b2_enabled': b2_stats.get('enabled', False),
        'b2_error': b2_stats.get('error') if not b2_stats.get('enabled') else None,
        
        'total_failed': db_stats['aws_s3']['failed'] + db_stats['backblaze_b2']['failed'],
        'total_size_formatted': format_bytes(
            (aws_stats.get('total_size', 0) if aws_stats.get('enabled') else 0) +
            (b2_stats.get('total_size', 0) if b2_stats.get('enabled') else 0)
        ),
        'total_file_count': (
            (aws_stats.get('total_files', 0) if aws_stats.get('enabled') else 0) +
            (b2_stats.get('total_files', 0) if b2_stats.get('enabled') else 0)
        ),
        'last_updated': datetime.now().isoformat()
    }
    
    logger.info(f"Real-time stats: AWS {result['aws_synced']} synced, B2 {result['b2_synced']} synced, {result['total_failed']} failed")
    
    return result


def format_bytes(bytes_value):
    """Format bytes into human readable format"""
    if bytes_value == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def get_failed_files_from_database():
    """Get detailed failed files information from database"""
    try:
        from src.database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fd.file_id, f.name, fd.destination, fd.error_message, fd.updated_at
            FROM file_destinations fd
            LEFT JOIN files f ON fd.file_id = f.file_id
            WHERE fd.sync_status = 'failed' AND fd.file_id NOT LIKE 'test-%'
            ORDER BY fd.updated_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        failed_files = []
        for row in rows:
            failed_files.append({
                'file_id': row[0],
                'name': row[1] or 'Unknown file',
                'destination': row[2],
                'error_message': row[3],
                'last_attempt': row[4]
            })
        
        return failed_files
        
    except Exception as e:
        logger.error(f"Error getting failed files: {e}")
        return []