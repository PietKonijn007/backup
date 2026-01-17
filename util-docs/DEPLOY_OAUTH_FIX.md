# Deploy OAuth Redirect URI Fix to EC2

## Your EC2 Instance Details
- **IP Address:** 100.48.101.102
- **User:** ubuntu
- **Key:** ~/.ssh/backup-app-key.pem
- **Domain:** backup.hofkensvermeulen.be
- **App Directory:** /opt/backup-app

## Quick Deploy Commands

### 1. Copy the fix script to your EC2 instance:
```bash
scp -i ~/.ssh/backup-app-key.pem fix_production_oauth.sh ubuntu@100.48.101.102:~/
```

### 2. SSH into your EC2 instance:
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102
```

### 3. Run the fix script:
```bash
bash fix_production_oauth.sh
```

## Alternative: Manual Fix (if script doesn't work)

If the script has issues, do it manually:

### 1. SSH into your EC2 instance:
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102
```

### 2. Go to your app directory:
```bash
cd /opt/backup-app
```

### 3. Backup current .env:
```bash
sudo cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
```

### 4. Add OAuth redirect URI to .env:
```bash
sudo nano .env
```

Add this line (or update if it exists):
```
OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback
```

Save and exit (Ctrl+X, Y, Enter)

### 5. Delete old token and credentials:
```bash
sudo rm -f /opt/backup-app/token.pickle
sudo rm -f /opt/backup-app/credentials.json
```

### 6. Restart the application:
```bash
sudo systemctl restart backup-daemon
```

### 7. Check status:
```bash
sudo systemctl status backup-daemon
```

## Verification

### Check if the redirect URI is configured:
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'grep OAUTH_REDIRECT_URI /opt/backup-app/.env'
```

Expected output:
```
OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback
```

### Check application logs:
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'sudo journalctl -u backup-daemon -n 50 --no-pager'
```

## Test OAuth Flow

1. Open browser to: **https://backup.hofkensvermeulen.be**
2. Login with admin credentials
3. Click "Connect Google Account" in Settings
4. Complete OAuth flow
5. **Verify it redirects to your domain** (not localhost)

## Troubleshooting

### If redirect still goes to localhost:

**Check 1: Is .env updated on the server?**
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'sudo cat /opt/backup-app/.env | grep OAUTH'
```

**Check 2: Did credentials.json regenerate?**
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'sudo cat /opt/backup-app/credentials.json'
```

Should show:
```json
"redirect_uris": ["https://backup.hofkensvermeulen.be/oauth2callback"]
```

**Check 3: Is service running?**
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'sudo systemctl status backup-daemon'
```

**Check 4: Restart service again:**
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'sudo systemctl restart backup-daemon'
```

### If you get "redirect_uri_mismatch" error:

This means Google Cloud Console doesn't have the production redirect URI yet. Make sure you:
1. ✅ Added `https://backup.hofkensvermeulen.be/oauth2callback` to Google Cloud Console
2. ✅ Clicked **SAVE** button
3. ⏳ Waited 5 minutes for changes to propagate

### If SSL/HTTPS issues:

Check if your SSL certificate is valid:
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'sudo certbot certificates'
```

Renew if needed:
```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'sudo certbot renew'
```

## All-in-One Deployment Command

Run this from your local machine to deploy everything at once:

```bash
scp -i ~/.ssh/backup-app-key.pem fix_production_oauth.sh ubuntu@100.48.101.102:~/ && \
ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102 'bash fix_production_oauth.sh'
```

## Summary

Your configuration should be:
- ✅ **Local .env:** `OAUTH_REDIRECT_URI=https://backup.hofkensvermeulen.be/oauth2callback`
- ✅ **Google Console:** `https://backup.hofkensvermeulen.be/oauth2callback` added and saved
- ⏳ **EC2 Server .env:** Needs to be updated (use commands above)
- ⏳ **EC2 Server restart:** Needs restart after .env update

Once all are done, OAuth will redirect correctly to your domain!

---

**Quick Reference:**
- SSH: `ssh -i ~/.ssh/backup-app-key.pem ubuntu@100.48.101.102`
- App Dir: `/opt/backup-app`
- Restart: `sudo systemctl restart backup-daemon`
- Logs: `sudo journalctl -u backup-daemon -f`
- Status: `sudo systemctl status backup-daemon`
