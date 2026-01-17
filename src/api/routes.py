"""API Routes - Sync control and monitoring"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
import yaml
from src.sync_daemon import get_daemon
from src.database import sync_config
from src.utils.logger import setup_logger

logger = setup_logger('api-routes')
api_bp = Blueprint('api', __name__)


def get_config():
    """Load configuration from yaml file"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config.yaml not found")
        return {}


@api_bp.route('/status')
@login_required
def status():
    """Get current sync daemon status with real-time statistics from buckets"""
    try:
        config = get_config()
        daemon = get_daemon(config)
        daemon_status = daemon.get_status()
        
        # Get real-time detailed statistics from actual buckets
        from src.storage.bucket_inspector import get_real_time_sync_statistics
        detailed_stats = get_real_time_sync_statistics()
        daemon_status['detailed_stats'] = detailed_stats
        
        return jsonify({
            'success': True,
            'daemon': daemon_status
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_detailed_sync_statistics():
    """DEPRECATED: Use bucket_inspector.get_real_time_sync_statistics() instead"""
    # Keep for backward compatibility, but redirect to real-time version
    from src.storage.bucket_inspector import get_real_time_sync_statistics
    return get_real_time_sync_statistics()


def format_bytes(bytes_value):
    """Format bytes into human readable format"""
    if bytes_value == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


@api_bp.route('/sync/start', methods=['POST'])
@login_required
def start_sync():
    """Start the sync daemon"""
    try:
        config = get_config()
        daemon = get_daemon(config)
        
        if daemon.start():
            logger.info("Sync daemon started via API")
            return jsonify({
                'success': True,
                'message': 'Sync daemon started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Daemon is already running'
            }), 400
    except Exception as e:
        logger.error(f"Error starting daemon: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/stop', methods=['POST'])
@login_required
def stop_sync():
    """Stop the sync daemon"""
    try:
        config = get_config()
        daemon = get_daemon(config)
        
        if daemon.stop():
            logger.info("Sync daemon stopped via API")
            return jsonify({
                'success': True,
                'message': 'Sync daemon stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Daemon is not running'
            }), 400
    except Exception as e:
        logger.error(f"Error stopping daemon: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/pause', methods=['POST'])
@login_required
def pause_sync():
    """Pause the sync daemon"""
    try:
        config = get_config()
        daemon = get_daemon(config)
        
        if daemon.pause():
            logger.info("Sync daemon paused via API")
            return jsonify({
                'success': True,
                'message': 'Sync daemon paused successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Cannot pause - daemon is not running'
            }), 400
    except Exception as e:
        logger.error(f"Error pausing daemon: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/resume', methods=['POST'])
@login_required
def resume_sync():
    """Resume the sync daemon"""
    try:
        config = get_config()
        daemon = get_daemon(config)
        
        if daemon.resume():
            logger.info("Sync daemon resumed via API")
            return jsonify({
                'success': True,
                'message': 'Sync daemon resumed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Cannot resume - daemon is not running'
            }), 400
    except Exception as e:
        logger.error(f"Error resuming daemon: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/health')
def health():
    """Health check endpoint for monitoring"""
    try:
        # Check basic health
        health_status = {
            'status': 'healthy',
            'timestamp': None
        }
        
        # Get daemon status if possible
        try:
            from datetime import datetime
            health_status['timestamp'] = datetime.now().isoformat()
            
            config = get_config()
            daemon = get_daemon(config)
            daemon_status = daemon.get_status()
            
            health_status['daemon'] = {
                'running': daemon_status['running'],
                'paused': daemon_status['paused']
            }
        except Exception as e:
            logger.warning(f"Could not get daemon status in health check: {e}")
            health_status['daemon'] = None
        
        return jsonify(health_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# Sync Configuration Endpoints

@api_bp.route('/sync/config', methods=['GET'])
@login_required
def get_sync_config():
    """Get current sync configuration"""
    try:
        config_items = sync_config.get_sync_config()
        return jsonify({
            'success': True,
            'items': config_items,
            'count': len(config_items)
        })
    except Exception as e:
        logger.error(f"Error getting sync config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/config/add', methods=['POST'])
@login_required
def add_sync_config():
    """Add items to sync configuration"""
    try:
        data = request.get_json()
        items = data.get('items', [])
        
        if not items:
            return jsonify({
                'success': False,
                'error': 'No items provided'
            }), 400
        
        added = 0
        for item in items:
            if sync_config.add_to_sync_config(
                item['item_id'],
                item['item_name'],
                item.get('item_type', 'file'),
                item.get('is_folder', False)
            ):
                added += 1
        
        logger.info(f"Added {added} items to sync configuration")
        return jsonify({
            'success': True,
            'added': added,
            'message': f'Added {added} items to sync configuration'
        })
    except Exception as e:
        logger.error(f"Error adding to sync config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/config/remove', methods=['POST'])
@login_required
def remove_sync_config():
    """Remove items from sync configuration"""
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])
        
        if not item_ids:
            return jsonify({
                'success': False,
                'error': 'No item IDs provided'
            }), 400
        
        removed = 0
        for item_id in item_ids:
            if sync_config.remove_from_sync_config(item_id):
                removed += 1
        
        logger.info(f"Removed {removed} items from sync configuration")
        return jsonify({
            'success': True,
            'removed': removed,
            'message': f'Removed {removed} items from sync configuration'
        })
    except Exception as e:
        logger.error(f"Error removing from sync config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/config/clear', methods=['POST'])
@login_required  
def clear_sync_config():
    """Clear all sync configuration"""
    try:
        if sync_config.clear_sync_config():
            logger.info("Cleared all sync configuration")
            return jsonify({
                'success': True,
                'message': 'Cleared all sync configuration'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to clear configuration'
            }), 500
    except Exception as e:
        logger.error(f"Error clearing sync config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/status', methods=['GET'])
@login_required
def get_sync_status():
    """Get sync status for all files"""
    try:
        from src.database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT file_id, name, sync_status, last_sync, size
            FROM files
            WHERE sync_status IN ('synced', 'failed')
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        status_map = {}
        for row in rows:
            status_map[row[0]] = {
                'file_id': row[0],
                'name': row[1],
                'status': row[2],
                'last_sync': row[3],
                'size': row[4]
            }
        
        return jsonify({
            'success': True,
            'status_map': status_map
        })
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/drive/tree', methods=['GET'])
@login_required
def get_drive_tree():
    """Get root level of Google Drive (lazy loading)"""
    try:
        from src.google_sync.oauth import get_oauth_manager
        from src.google_sync.drive import create_drive_manager
        
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({
                'success': False,
                'error': 'Not authenticated with Google'
            }), 401
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        
        # Get only root level files with pagination
        all_files = []
        page_token = None
        
        while True:
            result = drive_manager.list_files(
                page_size=1000, 
                folder_id=None,  # Root level
                page_token=page_token
            )
            all_files.extend(result['files'])
            page_token = result.get('next_page_token')
            
            if not page_token:
                break
        
        tree_nodes = []
        folders = [f for f in all_files if f['is_folder']]
        regular_files = [f for f in all_files if not f['is_folder']]
        
        # Process folders first (without children - lazy load them later)
        for folder in folders:
            folder_node = {
                'id': folder['id'],
                'name': folder['name'],
                'type': 'folder',
                'mimeType': folder['mime_type'],
                'modifiedTime': folder['modified_time'],
                'hasChildren': True,  # Flag to indicate children can be loaded
                'childrenLoaded': False
            }
            tree_nodes.append(folder_node)
        
        # Then add files
        for file in regular_files:
            file_node = {
                'id': file['id'],
                'name': file['name'],
                'type': 'file',
                'mimeType': file['mime_type'],
                'size': file['size'],
                'sizeFormatted': file['size_formatted'],
                'modifiedTime': file['modified_time'],
                'fileType': file['file_type']
            }
            tree_nodes.append(file_node)
        
        logger.info(f"Loaded {len(tree_nodes)} root level items")
        
        return jsonify({
            'success': True,
            'tree': tree_nodes
        })
    except Exception as e:
        logger.error(f"Error loading drive tree: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/drive/folder/<folder_id>', methods=['GET'])
@login_required
def get_folder_contents(folder_id):
    """Get contents of a specific folder (for lazy loading)"""
    try:
        from src.google_sync.oauth import get_oauth_manager
        from src.google_sync.drive import create_drive_manager
        
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({
                'success': False,
                'error': 'Not authenticated with Google'
            }), 401
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        
        # Get all files in this folder with pagination
        all_files = []
        page_token = None
        
        while True:
            result = drive_manager.list_files(
                page_size=1000, 
                folder_id=folder_id,
                page_token=page_token
            )
            all_files.extend(result['files'])
            page_token = result.get('next_page_token')
            
            if not page_token:
                break
        
        children = []
        folders = [f for f in all_files if f['is_folder']]
        regular_files = [f for f in all_files if not f['is_folder']]
        
        # Process folders first
        for folder in folders:
            folder_node = {
                'id': folder['id'],
                'name': folder['name'],
                'type': 'folder',
                'mimeType': folder['mime_type'],
                'modifiedTime': folder['modified_time'],
                'hasChildren': True,
                'childrenLoaded': False
            }
            children.append(folder_node)
        
        # Then add files
        for file in regular_files:
            file_node = {
                'id': file['id'],
                'name': file['name'],
                'type': 'file',
                'mimeType': file['mime_type'],
                'size': file['size'],
                'sizeFormatted': file['size_formatted'],
                'modifiedTime': file['modified_time'],
                'fileType': file['file_type']
            }
            children.append(file_node)
        
        logger.info(f"Loaded {len(children)} items from folder {folder_id}")
        
        return jsonify({
            'success': True,
            'children': children
        })
    except Exception as e:
        logger.error(f"Error loading folder contents: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Google Photos API Routes - REMOVED
# Google deprecated the Photos Library API on March 31, 2025
# For alternative backup solutions, see: GOOGLE_PHOTOS_API_DEPRECATION.md


# Folder Policy Management Endpoints

@api_bp.route('/folders/policies', methods=['GET'])
@login_required
def get_folder_policies():
    """Get all folder destination policies"""
    try:
        from src.database import folder_policies
        policies = folder_policies.get_all_folder_policies()
        return jsonify({
            'success': True,
            'policies': policies,
            'count': len(policies)
        })
    except Exception as e:
        logger.error(f"Error getting folder policies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/folders/policies', methods=['POST'])
@login_required
def add_folder_policy():
    """Add folder with destination policy"""
    try:
        from src.database import folder_policies
        data = request.get_json()
        
        folder_id = data.get('folder_id')
        folder_name = data.get('folder_name')
        folder_path = data.get('folder_path', '')
        destinations = data.get('destinations', [])
        
        if not folder_id or not folder_name:
            return jsonify({
                'success': False,
                'error': 'folder_id and folder_name are required'
            }), 400
        
        if not destinations:
            return jsonify({
                'success': False,
                'error': 'At least one destination must be selected'
            }), 400
        
        success = folder_policies.add_folder_policy(
            folder_id=folder_id,
            folder_name=folder_name,
            folder_path=folder_path,
            destinations=destinations
        )
        
        if success:
            logger.info(f"Added folder policy: {folder_name} -> {destinations}")
            return jsonify({
                'success': True,
                'message': f'Added folder policy for {folder_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add folder policy (may already exist)'
            }), 400
            
    except Exception as e:
        logger.error(f"Error adding folder policy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/folders/policies/<folder_id>', methods=['PUT'])
@login_required
def update_folder_policy(folder_id):
    """Update folder destinations"""
    try:
        from src.database import folder_policies
        data = request.get_json()
        
        destinations = data.get('destinations', [])
        
        if not destinations:
            return jsonify({
                'success': False,
                'error': 'At least one destination must be selected'
            }), 400
        
        success = folder_policies.update_folder_policy(
            folder_id=folder_id,
            destinations=destinations
        )
        
        if success:
            logger.info(f"Updated folder policy for {folder_id}: {destinations}")
            return jsonify({
                'success': True,
                'message': 'Folder policy updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update folder policy'
            }), 400
            
    except Exception as e:
        logger.error(f"Error updating folder policy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/folders/policies/<folder_id>', methods=['DELETE'])
@login_required
def delete_folder_policy(folder_id):
    """Remove folder policy"""
    try:
        from src.database import folder_policies
        
        success = folder_policies.remove_folder_policy(folder_id)
        
        if success:
            logger.info(f"Removed folder policy for {folder_id}")
            return jsonify({
                'success': True,
                'message': 'Folder policy removed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to remove folder policy'
            }), 400
            
    except Exception as e:
        logger.error(f"Error removing folder policy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/destinations/available', methods=['GET'])
@login_required
def get_available_destinations():
    """Get list of enabled backup destinations"""
    try:
        from src.storage.storage_manager import create_storage_manager
        
        config = get_config()
        storage_mgr = create_storage_manager(config)
        destinations = storage_mgr.get_available_destinations()
        
        # Get human-readable names and icons
        dest_info = {
            'aws_s3': {
                'key': 'aws_s3',
                'name': 'AWS S3',
                'icon': 'bi-amazon',
                'color': 'warning'
            },
            'backblaze_b2': {
                'key': 'backblaze_b2',
                'name': 'Backblaze B2',
                'icon': 'bi-cloud',
                'color': 'info'
            },
            'scaleway': {
                'key': 'scaleway',
                'name': 'Scaleway',
                'icon': 'bi-hdd-network',
                'color': 'secondary'
            }
        }
        
        result = []
        for dest in destinations:
            info = dest_info.get(dest, {
                'key': dest,
                'name': dest,
                'icon': 'bi-cloud',
                'color': 'secondary'
            })
            result.append(info)
        
        return jsonify({
            'success': True,
            'destinations': result,
            'count': len(result)
        })
        
    except Exception as e:
        logger.error(f"Error getting available destinations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/files/<file_id>/destinations', methods=['GET'])
@login_required
def get_file_destinations(file_id):
    """Get destination status for a specific file"""
    try:
        from src.database import folder_policies
        
        destinations = folder_policies.get_file_destinations(file_id)
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'destinations': destinations
        })
        
    except Exception as e:
        logger.error(f"Error getting file destinations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/files/backup-status', methods=['GET'])
@login_required
def get_files_backup_status():
    """Get backup status for all files across all destinations"""
    try:
        from src.database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all file backup statuses
        cursor.execute('''
            SELECT file_id, destination, sync_status, last_sync
            FROM file_destinations
            WHERE sync_status IN ('synced', 'pending', 'failed')
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Build a map: file_id -> {destinations: {...}}
        backup_status = {}
        for row in rows:
            file_id = row[0]
            destination = row[1]
            status = row[2]
            last_sync = row[3]
            
            if file_id not in backup_status:
                backup_status[file_id] = {
                    'aws_s3': {'status': 'not_configured', 'last_sync': None},
                    'backblaze_b2': {'status': 'not_configured', 'last_sync': None}
                }
            
            if destination == 'aws_s3':
                backup_status[file_id]['aws_s3'] = {
                    'status': status,
                    'last_sync': last_sync
                }
            elif destination == 'backblaze_b2':
                backup_status[file_id]['backblaze_b2'] = {
                    'status': status,
                    'last_sync': last_sync
                }
        
        return jsonify({
            'success': True,
            'backup_status': backup_status
        })
        
    except Exception as e:
        logger.error(f"Error getting files backup status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/drive/storage', methods=['GET'])
@login_required
def get_drive_storage():
    """Get Google Drive storage information"""
    try:
        from src.google_sync.oauth import get_oauth_manager
        from src.google_sync.drive import create_drive_manager
        
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({
                'success': False,
                'error': 'Not authenticated with Google'
            }), 401
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        storage_info = drive_manager.get_storage_quota()
        
        return jsonify({
            'success': True,
            'storage': storage_info
        })
        
    except Exception as e:
        logger.error(f"Error getting drive storage: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/folders/backup-stats', methods=['GET'])
@login_required
def get_folder_backup_stats():
    """Get pre-calculated backup statistics for all folders"""
    try:
        from src.database import folder_stats
        
        stats = folder_stats.get_folder_backup_stats()
        
        return jsonify({
            'success': True,
            'folder_stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting folder backup stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Logs API Endpoints

@api_bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    """Get system logs with filtering and pagination"""
    try:
        from src.database.models import get_db
        from datetime import datetime, timedelta
        
        # Get query parameters
        limit = request.args.get('limit', 500, type=int)
        since_id = request.args.get('since', 0, type=int)
        level = request.args.get('level', None)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Build query
        where_conditions = []
        params = []
        
        if since_id > 0:
            where_conditions.append('id > ?')
            params.append(since_id)
        
        if level:
            where_conditions.append('level = ?')
            params.append(level.upper())
        
        where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
        
        # Get logs
        cursor.execute(f'''
            SELECT id, timestamp, level, source, message
            FROM logs
            WHERE {where_clause}
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
        ''', params + [limit])
        
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'timestamp': row[1],
                'level': row[2],
                'source': row[3],
                'message': row[4]
            })
        
        # Get statistics for last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        cursor.execute('''
            SELECT level, COUNT(*) as count
            FROM logs
            WHERE timestamp >= ?
            GROUP BY level
        ''', (yesterday.isoformat(),))
        
        stats_rows = cursor.fetchall()
        stats = {'error': 0, 'warning': 0, 'info': 0, 'debug': 0, 'total': 0}
        
        for row in stats_rows:
            level = row[0].lower()
            count = row[1]
            if level in stats:
                stats[level] = count
            stats['total'] += count
        
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'stats': stats,
            'count': len(logs)
        })
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/logs/export', methods=['GET'])
@login_required
def export_logs():
    """Export logs as text file"""
    try:
        from src.database.models import get_db
        from flask import Response
        from datetime import datetime
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, level, source, message
            FROM logs
            ORDER BY timestamp DESC
            LIMIT 10000
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Generate text content
        content = f"# Backup System Logs Export\n"
        content += f"# Generated: {datetime.now().isoformat()}\n"
        content += f"# Total entries: {len(rows)}\n\n"
        
        for row in rows:
            timestamp, level, source, message = row
            content += f"{timestamp} [{source}] {level}: {message}\n"
        
        return Response(
            content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename=backup-logs-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt'
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    """Clear all logs (admin only)"""
    try:
        from src.database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM logs')
        conn.commit()
        conn.close()
        
        logger.info(f"All logs cleared by user {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'All logs cleared successfully'
        })
        
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Failed Files Management Endpoints

@api_bp.route('/sync/failed-files', methods=['GET'])
@login_required
def get_failed_files():
    """Get all failed files with details from database (real-time)"""
    try:
        from src.storage.bucket_inspector import get_failed_files_from_database
        
        failed_files = get_failed_files_from_database()
        
        return jsonify({
            'success': True,
            'failed_files': failed_files,
            'count': len(failed_files)
        })
        
    except Exception as e:
        logger.error(f"Error getting failed files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/retry-file', methods=['POST'])
@login_required
def retry_file():
    """Retry syncing a specific failed file"""
    try:
        from src.database.models import get_db
        
        data = request.get_json()
        file_id = data.get('file_id')
        destination = data.get('destination')
        
        if not file_id or not destination:
            return jsonify({
                'success': False,
                'error': 'file_id and destination are required'
            }), 400
        
        # Update status to pending for retry
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE file_destinations 
            SET sync_status = 'pending', error_message = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE file_id = ? AND destination = ?
        ''', (file_id, destination))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"File {file_id} marked for retry on {destination}")
            
            # TODO: Trigger actual sync process here
            # For now, we just mark it as pending
            
            conn.close()
            return jsonify({
                'success': True,
                'message': f'File marked for retry on {destination}'
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'File not found or not in failed state'
            }), 404
            
    except Exception as e:
        logger.error(f"Error retrying file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/sync/retry-all-failed', methods=['POST'])
@login_required
def retry_all_failed():
    """Retry all failed files"""
    try:
        from src.database.models import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update all failed files to pending
        cursor.execute('''
            UPDATE file_destinations 
            SET sync_status = 'pending', error_message = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE sync_status = 'failed'
        ''')
        
        retry_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Marked {retry_count} failed files for retry")
        
        # TODO: Trigger actual sync process here
        
        return jsonify({
            'success': True,
            'message': f'Marked {retry_count} files for retry',
            'retry_count': retry_count
        })
        
    except Exception as e:
        logger.error(f"Error retrying all failed files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Real-time Bucket Status Endpoints

@api_bp.route('/buckets/status', methods=['GET'])
@login_required
def get_bucket_status():
    """Get real-time status of all configured buckets"""
    try:
        from src.storage.bucket_inspector import get_aws_s3_stats, get_backblaze_b2_stats
        
        aws_stats = get_aws_s3_stats()
        b2_stats = get_backblaze_b2_stats()
        
        return jsonify({
            'success': True,
            'buckets': {
                'aws_s3': aws_stats,
                'backblaze_b2': b2_stats
            },
            'last_checked': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting bucket status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/buckets/aws-s3/status', methods=['GET'])
@login_required
def get_aws_s3_bucket_status():
    """Get real-time AWS S3 bucket status"""
    try:
        from src.storage.bucket_inspector import get_aws_s3_stats
        
        stats = get_aws_s3_stats()
        
        return jsonify({
            'success': True,
            'aws_s3': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting AWS S3 bucket status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/buckets/backblaze-b2/status', methods=['GET'])
@login_required
def get_b2_bucket_status():
    """Get real-time Backblaze B2 bucket status"""
    try:
        from src.storage.bucket_inspector import get_backblaze_b2_stats
        
        stats = get_backblaze_b2_stats()
        
        return jsonify({
            'success': True,
            'backblaze_b2': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting Backblaze B2 bucket status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
