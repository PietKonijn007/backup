#!/usr/bin/env python3
"""
Diagnose Photos API Scope Issues
Check what scopes are actually in the token
"""
import os
import pickle
import sys

print("=" * 60)
print("DIAGNOSE PHOTOS API SCOPE")
print("=" * 60)

token_file = 'token.pickle'

if not os.path.exists(token_file):
    print(f"\n❌ No token file found: {token_file}")
    print("\nYou need to authenticate first:")
    print("  python app.py")
    print("  Then visit: http://localhost:8080/login")
    sys.exit(1)

try:
    with open(token_file, 'rb') as f:
        credentials = pickle.load(f)
    
    print("\n✓ Token file loaded successfully")
    print("\n" + "=" * 60)
    print("TOKEN INFORMATION")
    print("=" * 60)
    
    # Check if credentials have scopes attribute
    if hasattr(credentials, 'scopes'):
        scopes = credentials.scopes
        print(f"\nScopes in token: {len(scopes) if scopes else 0}")
        
        if scopes:
            print("\nActual scopes in your token:")
            for scope in scopes:
                print(f"  ✓ {scope}")
            
            # Check for Photos scope
            photos_scope = 'https://www.googleapis.com/auth/photoslibrary.readonly'
            if photos_scope in scopes:
                print(f"\n✅ Photos scope IS present in token")
                print("\nSince the scope is present, the issue is likely:")
                print("  1. Google Photos Library API not enabled in Cloud Console")
                print("  2. OAuth consent screen not published")
            else:
                print(f"\n❌ Photos scope NOT found in token")
                print("\nExpected scope:")
                print(f"  {photos_scope}")
                print("\nYou need to re-authenticate to get this scope.")
        else:
            print("\n⚠️  No scopes found in token (unusual)")
    else:
        print("\n⚠️  Token doesn't have scopes attribute")
        print("This might be an older token format")
    
    # Check token validity
    print("\n" + "=" * 60)
    print("TOKEN STATUS")
    print("=" * 60)
    
    if hasattr(credentials, 'valid'):
        if credentials.valid:
            print("\n✓ Token is VALID")
        else:
            print("\n⚠️  Token is INVALID or expired")
            
            if hasattr(credentials, 'expired') and credentials.expired:
                print("  - Token is expired")
                if hasattr(credentials, 'refresh_token') and credentials.refresh_token:
                    print("  - But has refresh token (will auto-refresh)")
                else:
                    print("  - No refresh token (need to re-authenticate)")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS TO FIX")
    print("=" * 60)
    
    print("\n1. ENABLE GOOGLE PHOTOS LIBRARY API:")
    print("   a. Go to: https://console.cloud.google.com/apis/library")
    print("   b. Search for: 'Google Photos Library API'")
    print("   c. Click 'ENABLE'")
    
    print("\n2. VERIFY OAUTH CONSENT SCREEN:")
    print("   a. Go to: https://console.cloud.google.com/apis/credentials/consent")
    print("   b. Check that Photos scope is listed")
    print("   c. If in 'Testing' mode, ensure your email is in test users")
    
    print("\n3. IF STILL DOESN'T WORK:")
    print("   Delete token and re-authenticate:")
    print("   rm token.pickle")
    print("   python app.py")
    print("   # Then login via web UI")
    
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"\n❌ Error reading token: {e}")
    print("\nThe token file might be corrupted.")
    print("Try deleting it and re-authenticating:")
    print("  rm token.pickle")
    print("  python app.py")
    sys.exit(1)
