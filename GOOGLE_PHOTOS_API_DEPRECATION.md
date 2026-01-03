# 🚨 CRITICAL: Google Photos API Deprecation (March 31, 2025)

## Root Cause Identified

The 403 "insufficient scopes" error is **NOT a bug in our code** - Google **deprecated the entire Photos Library API** on March 31, 2025.

## What Happened

### Deprecated (No Longer Works)
```
❌ https://www.googleapis.com/auth/photoslibrary.readonly
❌ https://www.googleapis.com/auth/photoslibrary
❌ https://www.googleapis.com/auth/photoslibrary.sharing
```

These scopes **still appear valid** in tokens but Google's API now rejects them with 403 errors.

### New Scope
```
✅ https://www.googleapis.com/auth/photospicker.mediaitems.readonly
```

**BUT:** This is for a **completely different API** with severe limitations.

## Code Updated

I've updated `src/google_sync/oauth.py` with the new scope:

```python
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/photospicker.mediaitems.readonly',  # NEW
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
```

## ⚠️ CRITICAL LIMITATIONS

### Photos Library API (OLD - What We Built For)
- ✅ List all albums
- ✅ List all media items
- ✅ Download photos/videos at original quality
- ✅ Access full library programmatically
- ✅ Automated backup possible
- **Status:** DEPRECATED - No longer works

### Photos Picker API (NEW - Severe Restrictions)
- ❌ **No programmatic access** - requires user interaction
- ❌ Cannot list albums automatically
- ❌ Cannot list all photos automatically
- ❌ **User must manually select** photos each time
- ❌ No automated backup possible
- ⚠️ Designed for "user picks photos in UI" scenarios only

## Impact on Your Backup Solution

### What's Broken
1. **Automated album sync** - Not possible with Picker API
2. **List albums endpoint** - Requires user interaction now
3. **Bulk backup** - Cannot be automated
4. **All photos sync** - Not supported

### What Still Works
1. **Google Drive backup** - Unaffected (different API)
2. **Manual file selection** - If user picks photos

## Alternative Solutions

### Option 1: Google Takeout (Recommended)
**Use Case:** Periodic full backups

**Process:**
1. User goes to https://takeout.google.com/
2. Select "Google Photos"
3. Choose export format and delivery
4. Download archive manually or via API
5. Upload to S3

**Pros:**
- Gets ALL photos
- Original quality
- Works around API restrictions

**Cons:**
- Manual process (can be partially automated)
- Not real-time
- Large downloads

### Option 2: Third-Party Services
Some services still have legacy API access, but Google is actively revoking these.

### Option 3: Wait for Google's Solution
Google may introduce a new API for programmatic access, but no timeline announced.

### Option 4: Desktop Client Approach
- Install Google Photos desktop client
- Sync photos locally
- Upload local folder to S3 (our rclone integration already does this)

**Pros:**
- Fully automated
- Works with current code
- Real-time sync possible

**Cons:**
- Requires always-on computer with Photos desktop app
- Uses local disk space

## Recommended Next Steps

### Immediate (Test New Scope)
Even though Picker API is limited, test if it works at all:

```bash
# 1. Delete old token
rm token.pickle

# 2. Update OAuth consent screen in Cloud Console
# Add new scope: photospicker.mediaitems.readonly

# 3. Restart app
python app.py

# 4. Re-authenticate
# Visit: http://localhost:8080/login

# 5. Test (will likely still fail due to API differences)
python test_photos_api.py
```

### Short-term (Implement Takeout)
1. Create Google Takeout integration
2. Schedule periodic exports
3. Automate download and S3 upload
4. Update UI to reflect new workflow

### Long-term (Monitor Google)
1. Watch for new Photos API announcements
2. Consider desktop client + local sync approach
3. Evaluate third-party backup services

## Why This Was Confusing

1. **Token still shows scope** - The deprecated scope appears in tokens
2. **Google's error message** - Says "insufficient scopes" (misleading)
3. **Drive API works** - Different scope, not affected
4. **Recent change** - March 31, 2025 (very recent deprecation)
5. **Documentation lag** - Many tutorials still reference old API

## API Comparison

| Feature | Photos Library API (OLD) | Photos Picker API (NEW) |
|---------|-------------------------|------------------------|
| List albums programmatically | ✅ Yes | ❌ No (user interaction) |
| List all photos | ✅ Yes | ❌ No |
| Download at original quality | ✅ Yes | ⚠️ Limited |
| Automated backup | ✅ Yes | ❌ No |
| Batch operations | ✅ Yes | ❌ No |
| User interaction required | ❌ No | ✅ Yes (every time) |

## Code Impact

### Will Still Work
- ✅ OAuth flow
- ✅ Token generation
- ✅ Scope in token

### Will Not Work
- ❌ `photos_manager.list_albums()`
- ❌ `photos_manager.list_media_items()`
- ❌ Automated sync
- ❌ All routes in `/api/photos/*`

### Needs Rewrite
- Entire Photos integration
- Cannot use `photoslibrary` API
- Would need Picker API implementation (very different)
- Or switch to Google Takeout approach

## Official References

- **Deprecation Notice:** https://developers.google.com/photos/support/updates
- **Picker API Docs:** https://developers.google.com/photos/picker/guides
- **Migration Guide:** (If Google provides one)

## Decision Point

You need to decide on approach:

1. **Abandon Photos API** - Remove Photos features, focus on Drive only
2. **Implement Takeout** - Periodic manual/semi-automated backups
3. **Desktop + Local Sync** - Use Google Photos desktop client
4. **Wait** - Hope Google releases new programmatic API

The Photos Picker API is fundamentally incompatible with automated backup use cases.

## Status

- [x] Root cause identified (API deprecation)
- [x] Code updated with new scope
- [ ] Test new scope (likely won't solve the problem)
- [ ] Choose alternative approach
- [ ] Implement chosen solution

---

**Bottom Line:** Your code was perfect. Google deprecated the API your solution was built on. The new API doesn't support automated backups. You need a different approach (Google Takeout recommended).
