#!/usr/bin/env python3
"""
Test OAuth credentials before using in the app
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_credentials():
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    print("=" * 60)
    print("GOOGLE OAUTH CREDENTIALS TEST")
    print("=" * 60)
    
    print(f"\n✓ Client ID found: {client_id[:20]}..." if client_id else "✗ Client ID missing!")
    print(f"✓ Client Secret found: {client_secret[:10]}..." if client_secret else "✗ Client Secret missing!")
    
    print("\n" + "=" * 60)
    print("COMMON ISSUES CHECKLIST")
    print("=" * 60)
    
    issues = []
    
    # Check Client ID format
    if client_id:
        if not client_id.endswith('.apps.googleusercontent.com'):
            issues.append("⚠️  Client ID should end with '.apps.googleusercontent.com'")
        if not client_id.split('-')[0].isdigit():
            issues.append("⚠️  Client ID should start with numbers (e.g., '123456789-xxx.apps.googleusercontent.com')")
    else:
        issues.append("✗ GOOGLE_CLIENT_ID is not set in .env file")
    
    # Check Client Secret format
    if client_secret:
        if not client_secret.startswith('GOCSPX-'):
            issues.append("⚠️  Client Secret should start with 'GOCSPX-'")
    else:
        issues.append("✗ GOOGLE_CLIENT_SECRET is not set in .env file")
    
    if issues:
        print("\n❌ PROBLEMS FOUND:")
        for issue in issues:
            print(f"   {issue}")
        
        print("\n" + "=" * 60)
        print("HOW TO FIX:")
        print("=" * 60)
        print("""
1. Go to Google Cloud Console:
   https://console.cloud.google.com/apis/credentials

2. Make sure you have created OAuth 2.0 Client ID of type "Web application"
   (NOT Desktop, iOS, Android, or other types)

3. Under "Authorized redirect URIs", add EXACTLY:
   http://localhost:8080/oauth2callback
   
4. Click the download icon (⬇) to download JSON credentials

5. Open the downloaded JSON file and copy:
   - "client_id" → GOOGLE_CLIENT_ID in .env
   - "client_secret" → GOOGLE_CLIENT_SECRET in .env

6. The Client ID should look like:
   123456789-abc123def456.apps.googleusercontent.com
   
7. The Client Secret should look like:
   GOCSPX-XxXxXxXxXxXxXxXxXxXx

8. Make sure these APIs are enabled:
   - Google Drive API
   - Google Photos Library API
   
9. Make sure OAuth consent screen is configured
        """)
    else:
        print("\n✅ Credentials format looks correct!")
        print("\nIf you're still getting errors, verify in Google Cloud Console that:")
        print("   1. Redirect URI is: http://localhost:8080/oauth2callback")
        print("   2. Application type is: Web application")
        print("   3. APIs are enabled: Google Drive API & Google Photos Library API")
        print("   4. OAuth consent screen is configured")

if __name__ == '__main__':
    test_credentials()
