# Google OAuth 2.0 Setup Guide

This guide will walk you through setting up Google OAuth 2.0 for your backup application.

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com/)

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "Backup App")
5. Click "Create"

## Step 2: Enable Required APIs

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for and enable the following APIs:
   - **Google Drive API**
   - **Google Photos Library API**
   - **Google OAuth2 API** (usually enabled by default)

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** user type (or Internal if you have a Google Workspace)
3. Click **Create**
4. Fill in the required fields:
   - **App name**: Your app name (e.g., "Backup App")
   - **User support email**: Your email
   - **Developer contact email**: Your email
5. Click **Save and Continue**
6. On the **Scopes** page, click **Add or Remove Scopes**
7. Add the following scopes:
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/photoslibrary.readonly`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
8. Click **Update** and then **Save and Continue**
9. On the **Test users** page (for External apps), add your Google account email
10. Click **Save and Continue**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Select **Web application** as the application type
4. Enter a name (e.g., "Backup App Web Client")
5. Under **Authorized redirect URIs**, add:
   - `http://localhost:8080/oauth2callback` (for local development)
   - If deploying to production, add: `https://your-domain.com/oauth2callback`
6. Click **Create**
7. A dialog will appear with your **Client ID** and **Client Secret**
8. **IMPORTANT**: Copy these values - you'll need them in the next step

## Step 5: Configure Environment Variables

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your credentials:
   ```bash
   # Google OAuth Credentials
   GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret-here
   
   # Flask Configuration
   FLASK_ENV=development
   API_SECRET_KEY=your-random-secret-key-here
   
   # Admin User
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your-secure-password
   ```

3. **Generate a secure API secret key**:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

## Step 6: Initialize the Application

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize the database and create admin user:
   ```bash
   python init_user.py
   ```

3. Start the application:
   ```bash
   python app.py
   ```

4. Open your browser and go to: `http://localhost:8080`

## Step 7: Connect Your Google Account

1. Log in with the admin credentials you set in `.env`
2. Navigate to **Settings** in the sidebar
3. Click **Connect Google Account**
4. You'll be redirected to Google's consent screen
5. Review the permissions and click **Allow**
6. You'll be redirected back to the app with a success message
7. Click **Test Connection** to verify everything is working

## Troubleshooting

### Error: "Access blocked: This app's request is invalid"

**Solution**: Make sure you've:
- Enabled the Google Drive API and Google Photos Library API
- Configured the OAuth consent screen properly
- Added the correct redirect URI in the credentials

### Error: "redirect_uri_mismatch"

**Solution**: The redirect URI in your Google Cloud credentials must exactly match the one used by the app. For local development, it should be:
```
http://localhost:8080/oauth2callback
```

### Error: "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"

**Solution**: Make sure you've:
- Created a `.env` file (not just `.env.example`)
- Added your Google OAuth credentials to the `.env` file
- Restarted the application after updating `.env`

### Token Expired or Invalid

**Solution**: The app automatically refreshes expired tokens. If you encounter persistent issues:
1. Go to Settings
2. Click "Disconnect"
3. Click "Connect Google Account" again to re-authenticate

## Security Notes

- **Never commit** your `.env` file to version control (it's in `.gitignore`)
- **Never share** your Client Secret publicly
- The OAuth tokens are stored in `token.pickle` - keep this file secure
- In production, use HTTPS and update the redirect URI accordingly
- Consider using IAM roles on EC2 instead of hardcoding AWS credentials

## File Locations

- **OAuth tokens**: `token.pickle` (automatically created after authentication)
- **Temporary credentials file**: `credentials.json` (automatically created from `.env`)
- **Database**: `sync_state.db`
- **Logs**: Check the configured log path in `config.yaml`

## Next Steps

After successfully connecting your Google account:

1. The app can now access your Google Drive and Google Photos (read-only)
2. Proceed to implement the sync logic for downloading files
3. Configure rclone for uploading to S3/Scaleway
4. Test the full backup pipeline

## API Rate Limits

Be aware of Google API quotas:
- **Google Drive API**: 20,000 queries per 100 seconds per user
- **Google Photos Library API**: 10,000 queries per day per user

The app implements retry logic with exponential backoff to handle rate limiting gracefully.

## Support

For issues or questions:
1. Check the application logs in the configured log directory
2. Review the Flask debug output in the terminal
3. Verify API quotas in Google Cloud Console
