#!/usr/bin/env python3
"""
Fix Expired Google OAuth Token
This script will help you resolve the 'invalid_grant' error by:
1. Removing the expired token
2. Guiding you through re-authentication
"""

import os
import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("Google OAuth Token Fix Tool")
    print("=" * 60)
    print()
    
    # Check for token.pickle
    token_file = 'token.pickle'
    if os.path.exists(token_file):
        print(f"✓ Found expired token file: {token_file}")
        
        # Ask for confirmation
        response = input("\nDelete expired token file? (yes/no): ").lower().strip()
        
        if response in ['yes', 'y']:
            try:
                os.remove(token_file)
                print(f"✓ Deleted {token_file}")
            except Exception as e:
                print(f"✗ Error deleting token file: {e}")
                sys.exit(1)
        else:
            print("Cancelled. Token file not deleted.")
            sys.exit(0)
    else:
        print(f"✓ No token.pickle file found (already cleaned)")
    
    print()
    print("=" * 60)
    print("Next Steps to Re-authenticate:")
    print("=" * 60)
    print()
    print("Option 1: Re-authenticate through the web app")
    print("-" * 60)
    print("1. Start your Flask app:")
    print("   python3 app.py")
    print()
    print("2. Open your browser and go to:")
    print("   http://localhost:8080")
    print()
    print("3. Log in and click 'Connect Google Account'")
    print()
    print("4. Follow the OAuth flow to re-authenticate")
    print()
    print()
    print("Option 2: Test OAuth directly")
    print("-" * 60)
    print("Run the test script:")
    print("   python3 test_oauth_credentials.py")
    print()
    print()
    print("=" * 60)
    print("Important Notes:")
    print("=" * 60)
    print()
    print("• The GOOGLE_REFRESH_TOKEN in .env is not being used")
    print("  (it says 'your-refresh-token-here')")
    print()
    print("• Your OAuth credentials are valid:")
    print("  Client ID: 177383053794-jagi4bmvspng61dpvrq3umef303qruok...")
    print()
    print("• Make sure your OAuth consent screen includes:")
    print("  - drive.readonly scope")
    print("  - userinfo.email scope")
    print("  - userinfo.profile scope")
    print()
    print("• The old token included the deprecated Photos API scope")
    print("  The new token will not include this (Photos API deprecated)")
    print()

if __name__ == '__main__':
    main()
