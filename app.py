"""
Backup Application - Main Flask Application
Syncs Google Drive and Photos to AWS S3 and Scaleway
"""
import os
import threading
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import yaml

from src.api.auth import User
from src.api.routes import api_bp
from src.sync_daemon import get_daemon
from src.utils.logger import setup_logger
from src.database.models import init_db
from src.google_sync.oauth import get_oauth_manager
from src.google_sync.drive import create_drive_manager
from src.google_sync.photos import create_photos_manager
from src.sync.sync_service import create_sync_service

# Load environment variables
load_dotenv()

# Allow OAuth over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('API_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize logger
logger = setup_logger('backup-app')

# Initialize database
init_db()

# Set up database logging
from src.utils.db_logger import setup_database_logging
setup_database_logging()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Load configuration
try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    logger.info("Configuration loaded successfully")
except FileNotFoundError:
    logger.error("config.yaml not found")
    config = {}

# Sync daemon - will be initialized on startup
sync_daemon = None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Register blueprints
app.register_blueprint(api_bp, url_prefix='/api')

# Routes
@app.route('/')
@login_required
def index():
    """Dashboard home page"""
    return render_template('dashboard.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.authenticate(username, password)
        if user:
            login_user(user, remember=request.form.get('remember', False))
            logger.info(f"User {username} logged in successfully")
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            logger.warning(f"Failed login attempt for user: {username}")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout current user"""
    logger.info(f"User {current_user.username} logged out")
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/files')
@login_required
def files():
    """File browser page"""
    return render_template('files.html', user=current_user)

@app.route('/photos')
@login_required
def photos():
    """Photos browser page"""
    return render_template('photos.html', user=current_user)

@app.route('/logs')
@login_required
def logs():
    """Log viewer page"""
    return render_template('logs.html', user=current_user)

@app.route('/settings')
@login_required
def settings():
    """Settings page"""
    oauth_manager = get_oauth_manager()
    google_connected = oauth_manager.is_authenticated()
    google_user = oauth_manager.get_user_info() if google_connected else None
    
    return render_template('settings.html', 
                         user=current_user, 
                         config=config,
                         google_connected=google_connected,
                         google_user=google_user)

@app.route('/sync-help')
@login_required
def sync_help():
    """Sync help page"""
    return render_template('sync_help.html', user=current_user)

# Google OAuth Routes
@app.route('/google/authorize')
@login_required
def google_authorize():
    """Initiate Google OAuth flow"""
    try:
        oauth_manager = get_oauth_manager()
        authorization_url, state = oauth_manager.get_authorization_url()
        
        # Store state in session for CSRF protection
        from flask import session
        session['oauth_state'] = state
        
        logger.info(f"User {current_user.username} initiated Google OAuth")
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error initiating OAuth: {e}")
        flash('Error connecting to Google. Please check your OAuth credentials.', 'danger')
        return redirect(url_for('settings'))

@app.route('/oauth2callback')
@login_required
def oauth2callback():
    """Handle Google OAuth callback"""
    try:
        from flask import session
        state = session.get('oauth_state')
        
        if not state:
            logger.error("OAuth state not found in session")
            flash('Invalid OAuth state. Please try connecting again.', 'danger')
            return redirect(url_for('settings'))
        
        # Get the full callback URL
        authorization_response = request.url
        logger.info(f"OAuth callback URL: {authorization_response[:100]}...")
        
        oauth_manager = get_oauth_manager()
        if oauth_manager.handle_callback(authorization_response, state):
            # Get user info
            user_info = oauth_manager.get_user_info()
            if user_info:
                flash(f'Successfully connected to Google as {user_info["email"]}', 'success')
                logger.info(f"User {current_user.username} connected Google account: {user_info['email']}")
            else:
                flash('Successfully connected to Google', 'success')
                logger.info(f"User {current_user.username} connected to Google (no user info)")
        else:
            logger.error("OAuth callback handler returned False")
            flash('Failed to connect to Google. Check the logs for details.', 'danger')
        
        # Clear state from session
        session.pop('oauth_state', None)
        
    except Exception as e:
        import traceback
        logger.error(f"Error handling OAuth callback: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'Error completing Google authentication: {str(e)}', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/google/disconnect')
@login_required
def google_disconnect():
    """Disconnect Google account"""
    try:
        oauth_manager = get_oauth_manager()
        oauth_manager.revoke_credentials()
        flash('Successfully disconnected from Google', 'info')
        logger.info(f"User {current_user.username} disconnected Google account")
    except Exception as e:
        logger.error(f"Error disconnecting Google: {e}")
        flash('Error disconnecting from Google', 'danger')
    
    return redirect(url_for('settings'))

@app.route('/google/test')
@login_required
def google_test():
    """Test Google API connection"""
    try:
        oauth_manager = get_oauth_manager()
        results = oauth_manager.test_connection()
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error testing Google connection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Google Drive API Routes
@app.route('/api/drive/files')
@login_required
def drive_list_files():
    """List files from Google Drive"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        # Get query parameters
        page_size = request.args.get('page_size', 50, type=int)
        page_token = request.args.get('page_token', None)
        folder_id = request.args.get('folder_id', None)
        
        # Create Drive manager
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        
        # List files
        result = drive_manager.list_files(
            page_size=page_size,
            page_token=page_token,
            folder_id=folder_id
        )
        
        return jsonify({
            'success': True,
            'files': result['files'],
            'next_page_token': result.get('next_page_token'),
            'total_count': result['total_count']
        })
    
    except Exception as e:
        logger.error(f"Error listing Drive files: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/drive/storage')
@login_required
def drive_storage_info():
    """Get Drive storage information"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        storage_info = drive_manager.get_storage_info()
        
        return jsonify({
            'success': True,
            'storage': storage_info
        })
    
    except Exception as e:
        logger.error(f"Error getting Drive storage info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/drive/search')
@login_required
def drive_search():
    """Search files in Drive"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        query = request.args.get('q', '')
        max_results = request.args.get('max_results', 50, type=int)
        
        if not query:
            return jsonify({'success': False, 'error': 'Search query required'}), 400
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        files = drive_manager.search_files(query, max_results)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_count': len(files)
        })
    
    except Exception as e:
        logger.error(f"Error searching Drive files: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/drive/recent')
@login_required
def drive_recent_files():
    """Get recently modified files"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        days = request.args.get('days', 7, type=int)
        max_results = request.args.get('max_results', 50, type=int)
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        files = drive_manager.get_recent_files(days, max_results)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_count': len(files)
        })
    
    except Exception as e:
        logger.error(f"Error getting recent Drive files: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/drive/download/<file_id>')
@login_required
def drive_download_file(file_id):
    """Download a file from Drive"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        # Get download destination from config or use default
        download_path = config.get('download', {}).get('temp_dir', '/tmp/backup-downloads')
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        result = drive_manager.download_file(file_id, download_path)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/drive/file/<file_id>')
@login_required
def drive_file_metadata(file_id):
    """Get metadata for a specific file"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        drive_manager = create_drive_manager(oauth_manager.get_credentials())
        metadata = drive_manager.get_file_metadata(file_id)
        
        return jsonify({
            'success': True,
            'file': metadata
        })
    
    except Exception as e:
        logger.error(f"Error getting file metadata for {file_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Google Photos API Routes
@app.route('/api/photos/media')
@login_required
def photos_list_media():
    """List media items from Google Photos"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        # Get query parameters
        page_size = request.args.get('page_size', 50, type=int)
        page_token = request.args.get('page_token', None)
        album_id = request.args.get('album_id', None)
        
        # Create Photos manager
        photos_manager = create_photos_manager(oauth_manager.get_credentials())
        
        # List media items
        result = photos_manager.list_media_items(
            page_size=page_size,
            page_token=page_token,
            album_id=album_id
        )
        
        return jsonify({
            'success': True,
            'items': result['items'],
            'next_page_token': result.get('next_page_token'),
            'total_count': result['total_count']
        })
    
    except Exception as e:
        logger.error(f"Error listing Photos media: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photos/albums')
@login_required
def photos_list_albums():
    """List albums from Google Photos"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        page_size = request.args.get('page_size', 50, type=int)
        page_token = request.args.get('page_token', None)
        
        photos_manager = create_photos_manager(oauth_manager.get_credentials())
        result = photos_manager.list_albums(page_size=page_size, page_token=page_token)
        
        return jsonify({
            'success': True,
            'albums': result['albums'],
            'next_page_token': result.get('next_page_token'),
            'total_count': result['total_count']
        })
    
    except Exception as e:
        logger.error(f"Error listing Photos albums: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photos/recent')
@login_required
def photos_recent_media():
    """Get recently added photos"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        days = request.args.get('days', 7, type=int)
        max_results = request.args.get('max_results', 50, type=int)
        
        photos_manager = create_photos_manager(oauth_manager.get_credentials())
        items = photos_manager.get_recent_media(days, max_results)
        
        return jsonify({
            'success': True,
            'items': items,
            'total_count': len(items)
        })
    
    except Exception as e:
        logger.error(f"Error getting recent Photos media: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photos/category/<category>')
@login_required
def photos_by_category(category):
    """Get photos by category"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        max_results = request.args.get('max_results', 50, type=int)
        
        photos_manager = create_photos_manager(oauth_manager.get_credentials())
        items = photos_manager.get_photos_by_category(category, max_results)
        
        return jsonify({
            'success': True,
            'items': items,
            'total_count': len(items)
        })
    
    except Exception as e:
        logger.error(f"Error getting Photos by category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photos/download/<media_item_id>')
@login_required
def photos_download_media(media_item_id):
    """Download a media item from Photos"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        # Get download destination from config or use default
        download_path = config.get('download', {}).get('temp_dir', '/tmp/backup-downloads')
        
        photos_manager = create_photos_manager(oauth_manager.get_credentials())
        result = photos_manager.download_media_item(media_item_id, download_path)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error downloading media item {media_item_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/photos/media/<media_item_id>')
@login_required
def photos_media_metadata(media_item_id):
    """Get metadata for a specific media item"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        photos_manager = create_photos_manager(oauth_manager.get_credentials())
        metadata = photos_manager.get_media_item(media_item_id)
        
        return jsonify({
            'success': True,
            'item': metadata
        })
    
    except Exception as e:
        logger.error(f"Error getting media metadata for {media_item_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Sync API Routes
@app.route('/api/sync/file', methods=['POST'])
@login_required
def sync_file():
    """Sync a single file from Google Drive to S3"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'success': False, 'error': 'file_id required'}), 400
        
        # Create sync service
        sync_service = create_sync_service(config, oauth_manager.get_credentials())
        
        # Sync the file
        result = sync_service.sync_file(file_id)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error syncing file: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sync/files', methods=['POST'])
@login_required
def sync_files():
    """Sync multiple files from Google Drive to S3"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        data = request.get_json()
        file_ids = data.get('file_ids', [])
        
        if not file_ids:
            return jsonify({'success': False, 'error': 'file_ids required'}), 400
        
        # Create sync service
        sync_service = create_sync_service(config, oauth_manager.get_credentials())
        
        # Sync files
        result = sync_service.sync_multiple_files(file_ids)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error syncing files: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sync/folder', methods=['POST'])
@login_required
def sync_folder():
    """Sync a folder from Google Drive to S3"""
    try:
        oauth_manager = get_oauth_manager()
        if not oauth_manager.is_authenticated():
            return jsonify({'success': False, 'error': 'Not authenticated with Google'}), 401
        
        data = request.get_json()
        folder_id = data.get('folder_id')
        
        if not folder_id:
            return jsonify({'success': False, 'error': 'folder_id required'}), 400
        
        # Create sync service
        sync_service = create_sync_service(config, oauth_manager.get_credentials())
        
        # Sync folder
        result = sync_service.sync_folder(folder_id)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error syncing folder: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

def init_sync_daemon():
    """Initialize and optionally auto-start the sync daemon"""
    global sync_daemon
    try:
        sync_daemon = get_daemon(config)
        
        # Check if auto-start is enabled in config
        auto_start = config.get('sync', {}).get('auto_start', True)
        
        if auto_start:
            if sync_daemon.start():
                logger.info("Sync daemon auto-started successfully")
            else:
                logger.warning("Sync daemon auto-start failed - may already be running")
        else:
            logger.info("Sync daemon initialized but not auto-started (auto_start=False in config)")
            
    except Exception as e:
        logger.error(f"Error initializing sync daemon: {e}", exc_info=True)

if __name__ == '__main__':
    # Initialize sync daemon
    init_sync_daemon()
    
    # Get configuration from environment or config file
    host = config.get('daemon', {}).get('api_host', '0.0.0.0')
    port = config.get('daemon', {}).get('api_port', 8080)
    # Disable debug mode to prevent duplicate daemon processes
    debug = False
    
    logger.info(f"Starting Flask application on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
