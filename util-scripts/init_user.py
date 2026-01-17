#!/usr/bin/env python3
"""
Initialize user in database with hashed password
"""
import os
from dotenv import load_dotenv
from src.database.models import init_db, create_user
from src.api.auth import User

# Load environment variables
load_dotenv()

def main():
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Get credentials from environment variables
    username = os.getenv('ADMIN_USERNAME', 'admin')
    password = os.getenv('ADMIN_PASSWORD', 'change-this-password')
    
    if password == 'change-this-password':
        print("⚠️  WARNING: Using default password!")
        print("⚠️  Please set ADMIN_PASSWORD in your .env file")
    
    # Hash the password with SHA-512
    password_hash = User.hash_password(password)
    
    print(f"Creating user '{username}'...")
    print(f"Password hash (SHA-512): {password_hash[:32]}...")
    
    user_id = create_user(username, password_hash)
    
    if user_id:
        print(f"✓ User '{username}' created successfully with ID: {user_id}")
        print(f"  Username: {username}")
        print(f"  Password: {'[hidden - from .env]' if password != 'change-this-password' else password}")
        print(f"\nYou can now login at http://localhost:8080")
    else:
        print(f"✗ User '{username}' already exists or error occurred")

if __name__ == '__main__':
    main()
