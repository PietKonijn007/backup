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
