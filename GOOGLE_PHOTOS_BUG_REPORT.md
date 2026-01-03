# Google Photos Library API - 403 Scope Error Bug Report

## Issue Summary
Google Photos Library API consistently returns 403 "Request had insufficient authentication scopes" error despite OAuth token containing the required scope and all configuration being verified as correct.

## Error Details

**Error Message:**
```
HttpError 403 when requesting https://photoslibrary.googleapis.com/v1/albums?pageSize=50&alt=json 
returned "Request had insufficient authentication scopes.". 
Details: "Request had insufficient authentication scopes."
```

**API Endpoint:** `https://photoslibrary.googleapis.com/v1/albums`
**Method:** GET
**Expected Behavior:** Return list of user's Google Photos albums
**Actual Behavior:** 403 error claiming insufficient scopes

## Environment

**Application Details:**
- Language: Python 3.13
- OAuth Library: `google-auth-oauthlib` 
- API Client: `google-api-python-client`
- Using: `build('photoslibrary', 'v1', credentials=credentials, static_discovery=False)`

**Google Cloud Project:**
- Project ID: 177383053794
- Client ID: `177383053794-jagi4bmvspng61dpvrq3umef303qruok.apps.googleusercontent.com`
- OAuth Consent Screen: Testing mode
- Test User: hofkensjurgen@gmail.com (added and verified)

## Configuration Verification

### ✅ OAuth Scopes Requested
Code requests these scopes in `src/google_sync/oauth.py`:
```python
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/photoslibrary.readonly',  # ← Required scope
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
```

### ✅ Token Contains Correct Scopes
Verified via token inspection (`token.pickle`):
```
✓ https://www.googleapis.com/auth/drive.readonly
✓ https://www.googleapis.com/auth/photoslibrary.readonly  ← PRESENT
✓ https://www.googleapis.com/auth/userinfo.email
✓ https://www.googleapis.com/auth/userinfo.profile
```

### ✅ OAuth Callback Confirms Scope Granted
OAuth callback URL includes all scopes:
```
scope=email%20profile%20
https://www.googleapis.com/auth/drive.readonly%20
https://www.googleapis.com/auth/photoslibrary.readonly%20  ← GRANTED
https://www.googleapis.com/auth/userinfo.profile%20
https://www.googleapis.com/auth/userinfo.email%20
openid&authuser=0&prompt=consent
```

### ✅ APIs Enabled in Cloud Console
Both APIs show as "Enabled" in Cloud Console:
- Google Photos Library API: **Enabled** ✓
- Google Photos Picker API: **Enabled** ✓

### ✅ OAuth Consent Screen Configured
Verified at: `https://console.cloud.google.com/apis/credentials/consent?project=177383053794`
- Publishing Status: **Testing**
- Test User: **hofkensjurgen@gmail.com** (added) ✓
- Scopes: **`.../auth/photoslibrary.readonly`** (listed) ✓

### ✅ Token Fresh and Valid
- Token deleted and regenerated multiple times
- OAuth flow completed successfully each time
- Token shows as `valid: True`
- Latest authentication: 2026-01-03 16:50:45

## What We've Tried

1. ✅ Enabled Google Photos Library API in Cloud Console
2. ✅ Added Photos scope to OAuth SCOPES array
3. ✅ Added user email to Test Users list
4. ✅ Deleted `token.pickle` and re-authenticated (3+ times)
5. ✅ Verified scope in OAuth callback URL
6. ✅ Verified scope in stored token
7. ✅ Used `static_discovery=False` for Photos API
8. ✅ Verified project ID matches across all configurations
9. ✅ Confirmed API is enabled in the correct project

## Code That Fails

**Python code making the API call:**
```python
from googleapiclient.discovery import build

# credentials object has photoslibrary.readonly scope (verified)
photos_service = build('photoslibrary', 'v1', 
                      credentials=credentials, 
                      static_discovery=False)

# This call fails with 403 scope error
results = photos_service.albums().list(pageSize=50).execute()
```

**Error Stack Trace:**
```python
File "/src/google_sync/photos.py", line 135, in list_albums
    ).execute()
File "/venv/lib/python3.13/site-packages/googleapiclient/http.py", line 938, in execute
    raise HttpError(resp, content, uri=self.uri)
googleapiclient.errors.HttpError: <HttpError 403 when requesting 
https://photoslibrary.googleapis.com/v1/albums?pageSize=50&alt=json 
returned "Request had insufficient authentication scopes.". 
Details: "Request had insufficient authentication scopes.">
```

## Comparison: Working vs Not Working

**Google Drive API** (Same OAuth flow, WORKS):
```python
drive_service = build('drive', 'v3', credentials=credentials)
results = drive_service.files().list(pageSize=10).execute()  # ✅ WORKS
```

**Google Photos API** (Same credentials, FAILS):
```python
photos_service = build('photoslibrary', 'v1', credentials=credentials, static_discovery=False)
results = photos_service.albums().list(pageSize=50).execute()  # ❌ 403 ERROR
```

**Both APIs:**
- Use same OAuth credentials object
- Use same token with same scopes
- Both scopes are in the token
- Both APIs are enabled
- Drive works, Photos doesn't

## Diagnostic Evidence

**Token Scopes Inspection:**
```bash
$ python diagnose_photos_scope.py
Scopes in token: 4
Actual scopes in your token:
  ✓ https://www.googleapis.com/auth/drive.readonly
  ✓ https://www.googleapis.com/auth/photoslibrary.readonly  ← PRESENT
  ✓ https://www.googleapis.com/auth/userinfo.email
  ✓ https://www.googleapis.com/auth/userinfo.profile

✅ Photos scope IS present in token
✓ Token is VALID
```

**OAuth Flow Logs:**
```
2026-01-03 16:50:45 - google-oauth - INFO - Saved Google credentials
2026-01-03 16:50:45 - google-oauth - INFO - Successfully authenticated with Google
2026-01-03 16:50:45 - backup-app - INFO - User hofkens connected Google account: hofkensjurgen@gmail.com

Callback URL scope parameter:
scope=... https://www.googleapis.com/auth/photoslibrary.readonly ...
```

## Questions

1. **Is there an additional configuration step** for Photos API that's not documented?
2. **Does Testing mode have restrictions** on Photos API that don't apply to Drive API?
3. **Is there a delay** between adding a scope to consent screen and it being recognized by the API?
4. **Are there hidden quota/permission requirements** for Photos API in testing mode?
5. **Could this be a project-level permission issue** not visible in the console?

## Expected Resolution

Either:
1. **Documentation:** Identify missing configuration step for Photos API in Testing mode
2. **Bug Fix:** Address why 403 occurs when scope is provably present in token
3. **Guidance:** Provide specific troubleshooting for this scenario

## Supporting Files

All configuration files and diagnostic scripts available at:
- OAuth configuration: `src/google_sync/oauth.py`
- Photos API client: `src/google_sync/photos.py`
- Diagnostic script: `diagnose_photos_scope.py`
- Verification script: `verify_oauth_project.py`

## Contact

Project: Backup Application
Email: hofkensjurgen@gmail.com
Date: 2026-01-03
