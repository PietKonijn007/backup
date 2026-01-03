"""
Google OAuth 2.0 Implementation
Handles authentication, token storage, and refresh
"""
import os
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from src.utils.logger import setup_logger

logger = setup_logger('google-oauth')

# OAuth 2.0 scopes needed for Drive
# NOTE: Google Photos removed due to API deprecation (March 31, 2025)
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

TOKEN_FILE = 'token.pickle'
CREDENTIALS_FILE = 'credentials.json'


class GoogleOAuthManager:
    """Manages Google OAuth 2.0 authentication and token lifecycle"""
    
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        """
        Initialize OAuth manager
        
        Args:
            client_id: Google OAuth client ID (from .env or Google Console)
            client_secret: Google OAuth client secret
            redirect_uri: OAuth callback URL (from .env OAUTH_REDIRECT_URI or defaults to localhost)
        """
        self.client_id = client_id or os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = redirect_uri or os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8080/oauth2callback')
        self.credentials = None
        
        # Load existing credentials if available
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from pickle file"""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'rb') as token:
                    self.credentials = pickle.load(token)
                logger.info("Loaded existing Google credentials")
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
                self.credentials = None
    
    def _save_credentials(self):
        """Save credentials to pickle file"""
        try:
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(self.credentials, token)
            logger.info("Saved Google credentials")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
    
    def is_authenticated(self):
        """Check if user is authenticated with valid credentials"""
        if not self.credentials:
            return False
        
        if not self.credentials.valid:
            if self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    logger.info("Refreshed Google credentials")
                    return True
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    return False
            return False
        
        return True
    
    def get_authorization_url(self):
        """
        Generate authorization URL for OAuth flow
        
        Returns:
            tuple: (authorization_url, state)
        """
        # Create credentials.json on the fly if not exists
        if not os.path.exists(CREDENTIALS_FILE):
            self._create_credentials_file()
        
        try:
            flow = Flow.from_client_secrets_file(
                CREDENTIALS_FILE,
                scopes=SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent screen to get refresh token
            )
            
            logger.info("Generated authorization URL")
            return authorization_url, state
        
        except Exception as e:
            logger.error(f"Error generating authorization URL: {e}")
            raise
    
    def _create_credentials_file(self):
        """Create credentials.json from environment variables"""
        import json
        
        if not self.client_id or not self.client_secret:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env")
        
        credentials_data = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uris": [self.redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials_data, f)
        
        logger.info("Created credentials.json from environment variables")
    
    def handle_callback(self, authorization_response, state):
        """
        Handle OAuth callback and exchange code for credentials
        
        Args:
            authorization_response: Full callback URL with code
            state: State parameter for CSRF protection
            
        Returns:
            bool: True if successful
        """
        try:
            # Disable strict scope checking - Google may add 'openid' and reorder scopes
            import os
            os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
            
            flow = Flow.from_client_secrets_file(
                CREDENTIALS_FILE,
                scopes=SCOPES,
                state=state,
                redirect_uri=self.redirect_uri
            )
            
            flow.fetch_token(authorization_response=authorization_response)
            self.credentials = flow.credentials
            self._save_credentials()
            
            logger.info("Successfully authenticated with Google")
            return True
        
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            return False
    
    def revoke_credentials(self):
        """Revoke and delete stored credentials"""
        if self.credentials:
            try:
                # Revoke the token
                import requests
                requests.post('https://oauth2.googleapis.com/revoke',
                    params={'token': self.credentials.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'})
                logger.info("Revoked Google credentials")
            except Exception as e:
                logger.warning(f"Error revoking credentials: {e}")
        
        # Delete token file
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            logger.info("Deleted token file")
        
        self.credentials = None
    
    def get_credentials(self):
        """
        Get valid credentials, refreshing if necessary
        
        Returns:
            Credentials object or None
        """
        if self.is_authenticated():
            return self.credentials
        return None
    
    def get_user_info(self):
        """
        Get authenticated user's information
        
        Returns:
            dict: User info (email, name, etc.)
        """
        if not self.is_authenticated():
            return None
        
        try:
            service = build('oauth2', 'v2', credentials=self.credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'verified_email': user_info.get('verified_email')
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def test_connection(self):
        """
        Test the connection to Google APIs
        
        Returns:
            dict: Status information
        """
        if not self.is_authenticated():
            return {'success': False, 'error': 'Not authenticated'}
        
        results = {}
        
        # Test Drive API
        try:
            drive_service = build('drive', 'v3', credentials=self.credentials)
            about = drive_service.about().get(fields="user,storageQuota").execute()
            results['drive'] = {
                'success': True,
                'user': about.get('user', {}).get('emailAddress'),
                'storage_used': about.get('storageQuota', {}).get('usage', 0),
                'storage_limit': about.get('storageQuota', {}).get('limit', 0)
            }
        except Exception as e:
            results['drive'] = {'success': False, 'error': str(e)}
        
        # Test Photos API
        try:
            photos_service = build('photoslibrary', 'v1', credentials=self.credentials, static_discovery=False)
            # Just test if we can access the API
            results['photos'] = {'success': True}
        except Exception as e:
            results['photos'] = {'success': False, 'error': str(e)}
        
        return results


# Singleton instance
_oauth_manager = None

def get_oauth_manager():
    """Get or create OAuth manager singleton"""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = GoogleOAuthManager()
    return _oauth_manager
