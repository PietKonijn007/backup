#!/usr/bin/env python3
"""
Verify OAuth Project Configuration
Check if credentials.json matches the project with enabled APIs
"""
import json
import os
import sys

print("=" * 60)
print("VERIFY OAUTH PROJECT CONFIGURATION")
print("=" * 60)

# Check credentials.json
cred_file = 'credentials.json'

if not os.path.exists(cred_file):
    print(f"\n⚠️  No credentials.json found")
    print("This is created automatically from .env variables")
    
    # Check .env
    from dotenv import load_dotenv
    load_dotenv()
    
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    if client_id:
        # Extract project number from client ID
        # Format: 123456789-xxx.apps.googleusercontent.com
        project_num = client_id.split('-')[0] if '-' in client_id else 'unknown'
        print(f"\n✓ Client ID from .env: {client_id}")
        print(f"✓ Project number: {project_num}")
    else:
        print("\n❌ GOOGLE_CLIENT_ID not in .env")
        sys.exit(1)
else:
    try:
        with open(cred_file, 'r') as f:
            creds = json.load(f)
        
        client_id = creds.get('web', {}).get('client_id', 'unknown')
        project_num = client_id.split('-')[0] if '-' in client_id else 'unknown'
        
        print(f"\n✓ credentials.json found")
        print(f"✓ Client ID: {client_id}")
        print(f"✓ Project number: {project_num}")
    except Exception as e:
        print(f"\n❌ Error reading credentials.json: {e}")
        sys.exit(1)

print("\n" + "=" * 60)
print("CRITICAL CHECKS")
print("=" * 60)

print("\n1. OAUTH CONSENT SCREEN STATUS:")
print("   Go to: https://console.cloud.google.com/apis/credentials/consent")
print(f"   Make sure you're in project: {project_num}")
print("\n   Check these:")
print("   □ Publishing status: 'Testing' or 'In Production'")
print("   □ If 'Testing': Your email MUST be in 'Test users' list")
print("   □ Scopes section shows: '.../auth/photoslibrary.readonly'")

print("\n2. API ENABLED IN CORRECT PROJECT:")
print(f"   Go to: https://console.cloud.google.com/apis/library/photoslibrary.googleapis.com?project={project_num}")
print("   □ Should show 'API Enabled' with checkmark")
print("   □ If not enabled in this project, enable it")

print("\n3. CREDENTIALS MATCH PROJECT:")
print(f"   Go to: https://console.cloud.google.com/apis/credentials?project={project_num}")
print("   □ Find your OAuth 2.0 Client ID")
print(f"   □ Verify it matches: {client_id}")

print("\n" + "=" * 60)
print("MOST LIKELY FIX")
print("=" * 60)

print("\n🔥 IF YOUR APP IS IN 'TESTING' MODE:")
print("\n   1. Go to OAuth consent screen:")
print(f"      https://console.cloud.google.com/apis/credentials/consent?project={project_num}")
print("\n   2. Scroll to 'Test users' section")
print("\n   3. Click 'ADD USERS'")
print("\n   4. Add your Google account email")
print("\n   5. Click 'SAVE'")
print("\n   6. Delete your token: rm token.pickle")
print("\n   7. Restart app and re-login")

print("\n🔥 OR PUBLISH YOUR APP:")
print("\n   1. Go to OAuth consent screen")
print("   2. Click 'PUBLISH APP' button")
print("   3. Confirm publication")
print("   4. No need to verify (for personal use)")
print("   5. Re-login to app")

print("\n" + "=" * 60)
print("VERIFY THIS NOW")
print("=" * 60)

print(f"\nOpen this URL in your browser:")
print(f"https://console.cloud.google.com/apis/credentials/consent?project={project_num}")

print("\nLook for:")
print("  • Publishing status")
print("  • Test users list (if Testing)")
print("  • Scopes list (should include Photos)")

print("\n" + "=" * 60)
