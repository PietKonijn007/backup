# Fix OAuth Redirect URI for Production Server

## Problem
Google OAuth was redirecting to `http://localhost:8080/oauth2callback` instead of your production domain `https://backup.hofkensvermeulen.be/oauth2callback`.

## What I Fixed

✓ **Updated `.env` file** - Added production redirect URI:
```bash
OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback
```

✓ **Deleted old `credentials.json`** - Will be regenerated with correct URI

## Required: Update Google Cloud Console

You MUST add the production redirect URI to your Google OAuth configuration:

### Step 1: Go to Google Cloud Console

1. Visit: https://console.cloud.google.com/apis/credentials
2. Find your OAuth 2.0 Client ID: `177383053794-jagi4bmvspng61dpvrq3umef303qruok...`
3. Click on it to edit

### Step 2: Add Production Redirect URI

In the "Authorized redirect URIs" section, you should have:

**Required URIs:**
- ✅ `https://backup.hofkensvermeulen.be/oauth2callback` (production)
- ✅ `http://localhost:8080/oauth2callback` (local development - optional)

**Important:** Make sure you're using `https://` (not `http://`) for the production URL!

### Step 3: Save Changes

Click **"Save"** at the bottom of the page.

## Testing the Fix

### On Your Production Server

1. **SSH into your production server** (backup.hofkensvermeulen.be)

2. **Update the .env file on the server:**
```bash
cd /path/to/your/app
nano .env
```

Add this line:
```
OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback
```

3. **Delete old token and credentials files:**
```bash
rm -f token.pickle credentials.json
```

4. **Restart your application:**
```bash
# If using systemd:
sudo systemctl restart backup-daemon

# Or if running manually:
python3 app.py
```

5. **Test OAuth flow:**
   - Go to: https://backup.hofkensvermeulen.be
   - Login with admin credentials
   - Click "Connect Google Account"
   - Complete OAuth flow
   - Should now redirect correctly to your domain!

## Common Issues

### Issue 1: "Redirect URI mismatch" error
**Solution:** Double-check that the URI in Google Cloud Console exactly matches:
```
https://backup.hofkensvermeulen.be/oauth2callback
```
- No trailing slash
- Use `https://` not `http://`
- Exact domain spelling

### Issue 2: Still redirecting to localhost
**Solution:** 
1. Make sure `.env` has `OAUTH_REDIRECT_URI` set on the production server
2. Delete `credentials.json` and `token.pickle` 
3. Restart the app to force regeneration

### Issue 3: Certificate/SSL errors
**Solution:** Ensure your domain has a valid SSL certificate. If using Let's Encrypt:
```bash
sudo certbot renew
```

## For Local Development

If you want to test locally, you can temporarily change `.env`:
```bash
OAUTH_REDIRECT_URI=http://localhost:8080/oauth2callback
```

Then make sure this URI is also in your Google Cloud Console redirect URIs list.

## Deployment Checklist

When deploying changes:

- [ ] Updated `.env` on production server with production redirect URI
- [ ] Added production redirect URI to Google Cloud Console
- [ ] Deleted old `token.pickle` on production server
- [ ] Deleted old `credentials.json` on production server  
- [ ] Restarted application
- [ ] Tested OAuth flow on production domain
- [ ] Verified successful authentication

## Environment-Specific Configuration

You can set different redirect URIs for different environments:

**Production (.env on server):**
```bash
OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback
```

**Local Development (.env on laptop):**
```bash
OAUTH_REDIRECT_URI=http://localhost:8080/oauth2callback
```

**Important:** Never commit your `.env` file to git (it's in `.gitignore`)

## Verification

After completing the steps above, verify it works:

```bash
# On production server
python3 -c "from src.google_sync.oauth import get_oauth_manager; 
manager = get_oauth_manager(); 
print('Redirect URI:', manager.redirect_uri);
print('Authenticated:', manager.is_authenticated())"
```

Expected output:
```
Redirect URI: https://backup.hofkensvermeulen.be/oauth2callback
Authenticated: True
```

## Need Help?

If you still have issues:

1. Check application logs: `tail -f /var/log/backup-daemon/app.log`
2. Verify environment variables: `python3 -c "import os; print(os.getenv('OAUTH_REDIRECT_URI'))"`
3. Test OAuth manually: `python3 test_oauth_credentials.py`

---

**Status:** Configuration updated on local machine ✓  
**Next Action:** Update Google Cloud Console + Deploy to production server  
**Date:** January 11, 2026
