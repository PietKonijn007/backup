#!/usr/bin/env python3
"""
Fix OAuth Scopes for Google Photos
Deletes old token and forces re-authentication with Photos scope
"""
import os
import sys

print("=" * 60)
print("FIX OAUTH SCOPES FOR GOOGLE PHOTOS")
print("=" * 60)

# Check if token.pickle exists
token_file = 'token.pickle'

if os.path.exists(token_file):
    print(f"\n✓ Found existing token file: {token_file}")
    print("\nThe error you received:")
    print("  'Request had insufficient authentication scopes'")
    print("\nThis means your OAuth token doesn't include Google Photos permissions.")
    print("\nTo fix this, we need to delete the old token and re-authenticate.")
    
    response = input("\nDelete token.pickle and force re-authentication? (y/n): ")
    
    if response.lower() == 'y':
        try:
            os.remove(token_file)
            print(f"\n✅ Deleted {token_file}")
            print("\n" + "=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            print("\n1. Restart your Flask app:")
            print("   python app.py")
            print("\n2. Open in browser:")
            print("   http://localhost:8080/login")
            print("\n3. Click 'Login with Google'")
            print("\n4. IMPORTANT: Grant ALL permissions including Google Photos!")
            print("\n5. After login, try accessing /photos page again")
            print("\n6. The /api/photos/albums endpoint should now work")
            print("\n" + "=" * 60)
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error deleting token file: {e}")
            sys.exit(1)
    else:
        print("\n❌ Cancelled. Token file not deleted.")
        sys.exit(1)
else:
    print(f"\n✓ No token file found at: {token_file}")
    print("\nYou just need to authenticate:")
    print("\n1. Start your Flask app:")
    print("   python app.py")
    print("\n2. Open in browser:")
    print("   http://localhost:8080/login")
    print("\n3. Login with Google and grant ALL permissions")
    print("\n" + "=" * 60)
    sys.exit(0)
