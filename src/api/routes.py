"""API Routes - Sync control and monitoring"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
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
    """Get current sync daemon status"""
    try:
        config = get_config()
        daemon = get_daemon(config)
        daemon_status = daemon.get_status()
        
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
