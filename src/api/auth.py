"""
Authentication module
"""
import hashlib
from flask_login import UserMixin
from src.database.models import get_user_by_username

class User(UserMixin):
    def __init__(self, id, username):
        self.id = str(id)
        self.username = username
    
    @staticmethod
    def get(user_id):
        """Get user by ID"""
        from src.database.models import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(row[0], row[1])
        return None
    
    @staticmethod
    def authenticate(username, password):
        """Authenticate user with username and password"""
        row = get_user_by_username(username)
        if row:
            user_id, db_username, password_hash = row
            # Hash the provided password with SHA-512
            hashed_password = hashlib.sha512(password.encode()).hexdigest()
            
            if hashed_password == password_hash:
                return User(user_id, db_username)
        return None
    
    @staticmethod
    def hash_password(password):
        """Hash a password using SHA-512"""
        return hashlib.sha512(password.encode()).hexdigest()
