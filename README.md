# Google Drive & Photos Backup Application

A robust backup solution that syncs Google Drive and Google Photos to AWS S3 and Scaleway (Europe) using a streaming architecture. Features a Bootstrap web dashboard for monitoring and control.

## Features

- 🔄 **Streaming Sync**: Downloads files one-by-one, uploads to both destinations, then deletes locally
- 📱 **Google Workspace Export**: Automatically converts Docs→.docx, Sheets→.xlsx, Slides→.pptx
- 🔁 **Retry Logic**: 5 attempts with exponential backoff for failed transfers
- 📊 **Web Dashboard**: Bootstrap-based UI with real-time progress monitoring
- 🔒 **Secure**: Session-based authentication, HTTPS support
- 💾 **Dual Redundancy**: Simultaneous backup to AWS S3 (us-east-1) and Scaleway (France)
- 📈 **Cost Optimized**: Streaming architecture (no 4TB local storage needed)

## Architecture

```
Google Drive/Photos → EC2 (100GB temp) → S3 + Scaleway
                            ↓
                      Flask Dashboard
```

## Cost Estimate (4TB backup)

- EC2 t3.small: $15/month
- EBS 100GB: $8/month  
- AWS S3 (4TB): $94/month
- Scaleway (4TB): $43/month
- **Total**: ~$161/month

## Prerequisites

- Python 3.11+
- rclone installed
- AWS account with S3 bucket
- Scaleway account with Object Storage
- Google Cloud Project with Drive & Photos APIs enabled

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd backup-app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Edit config.yaml for your needs
nano config.yaml
```

### 3. Setup Google OAuth

Follow the detailed guide: [Google OAuth Setup Guide](docs/GOOGLE_OAUTH_SETUP.md)

**Quick Steps:**
1. Create a Google Cloud Project
2. Enable Google Drive API and Google Photos Library API
3. Configure OAuth consent screen
4. Create OAuth 2.0 credentials (Web application)
5. Add credentials to `.env` file
6. Connect your Google account through the web dashboard

**After app is running:**
- Navigate to Settings page
- Click "Connect Google Account"
- Authorize the app with Google
- Test the connection

### 4. Configure rclone

```bash
# Configure S3 remote
rclone config

# Name: remote-s3
# Type: s3
# Provider: AWS
# Access Key ID: (from .env)
# Secret Access Key: (from .env)
# Region: us-east-1

# Configure Scaleway remote
# Name: remote-eu
# Type: s3
# Provider: Scaleway
# Access Key ID: (from .env)
# Secret Access Key: (from .env)
# Endpoint: s3.fr-par.scw.cloud
# Region: fr-par
```

### 5. Run Locally

```bash
# Development mode
export FLASK_ENV=development
python app.py

# Access dashboard at http://localhost:8080
# Default login: admin / (password from .env)
```

## Deployment to AWS EC2

### Automated Deployment

```bash
# Run the deployment script
./deploy.sh

# Script will:
# 1. Create EC2 instance in us-east-1
# 2. Configure security groups
# 3. Install dependencies
# 4. Set up systemd service
# 5. Start the application
```

### Manual Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## Project Structure

```
backup-app/
├── app.py                    # Main Flask application
├── config.yaml               # Application configuration
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create from .env.example)
├── src/
│   ├── sync_daemon.py        # Background sync daemon
│   ├── google_sync/          # Google API integrations
│   ├── storage/              # rclone and upload handlers
│   ├── database/             # SQLite models
│   ├── api/                  # REST API and authentication
│   └── utils/                # Logging, retry logic, etc.
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS, JavaScript, images
├── systemd/                  # systemd service files
└── tests/                    # Unit and integration tests
```

## Usage

### Dashboard Pages

- **Home** (`/`): Overview with sync status and metrics
- **Files** (`/files`): Browse backed-up files
- **Logs** (`/logs`): View live sync logs
- **Settings** (`/settings`): Configure sync options

### API Endpoints

- `GET /api/status` - Get sync status
- `POST /api/sync/start` - Start syncing
- `POST /api/sync/stop` - Stop syncing
- `POST /api/sync/force` - Force full sync
- `GET /api/logs/stream` - SSE stream of live logs

See [API.md](docs/API.md) for complete API documentation.

## Monitoring

### Check Status

```bash
# Via API
curl http://localhost:8080/api/status

# Via systemd (on EC2)
sudo systemctl status backup-daemon

# View logs
tail -f /var/log/backup-daemon/app.log
```

### Health Checks

```bash
# Application health
curl http://localhost:8080/api/health

# Disk space (important for 100GB cache)
df -h /sync
```

## Troubleshooting

### Common Issues

1. **OAuth errors**: Regenerate Google OAuth token
2. **rclone errors**: Check rclone config (`rclone config show`)
3. **Disk space**: Monitor `/sync` directory (100GB limit)
4. **Rate limits**: Google API has rate limits, daemon will auto-retry

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more help.

## Development

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

### Code Style

```bash
# Install formatters
pip install black flake8

# Format code
black src/ tests/

# Lint
flake8 src/ tests/
```

## Security

- All credentials stored in `.env` (never commit this file)
- Session-based authentication with secure cookies
- HTTPS recommended for production (use Let's Encrypt)
- IAM role support on EC2 (no AWS keys needed)

## License

MIT License - See LICENSE file

## Support

For issues and questions, please open a GitHub issue or refer to:
- [Setup Guide](docs/SETUP.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Documentation](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Roadmap

- [x] Phase 1: Core sync engine
- [x] Phase 2: Web dashboard
- [ ] Phase 3: Deployment automation
- [ ] Phase 4: Enhanced features (encryption, restore, etc.)

---

**Cost**: ~$161/month for 4TB backup with dual redundancy
**Status**: Beta - Ready for testing
