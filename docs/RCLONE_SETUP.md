# Rclone AWS S3 Integration Setup

Complete guide to set up rclone for backing up to AWS S3.

## Prerequisites

### 1. Install Rclone

**macOS:**
```bash
brew install rclone
```

**Linux:**
```bash
curl https://rclone.org/install.sh | sudo bash
```

**Verify installation:**
```bash
rclone version
```

### 2. AWS S3 Setup

You need:
- AWS Account
- S3 Bucket created
- IAM User with S3 access
- Access Key ID and Secret Access Key

#### Create S3 Bucket

1. Go to AWS Console → S3
2. Click "Create bucket"
3. Choose a unique name (e.g., `my-backup-bucket`)
4. Select region (e.g., `us-east-1`)
5. Leave other settings as default
6. Click "Create bucket"

#### Create IAM User

1. Go to AWS Console → IAM → Users
2. Click "Create user"
3. Username: `backup-user`
4. Attach policy: `AmazonS3FullAccess` (or create custom policy)
5. Create access key:
   - Go to Security credentials tab
   - Click "Create access key"
   - Choose "Application running outside AWS"
   - Save Access Key ID and Secret Access Key

## Configuration

### 1. Add AWS Credentials to .env

Edit your `.env` file:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

**Security:** Never commit `.env` to git!

### 2. Update config.yaml

Edit `config.yaml`:

```yaml
destinations:
  aws_s3:
    enabled: true
    bucket: my-backup-bucket
    region: us-east-1
    storage_class: INTELLIGENT_TIERING  # Options: STANDARD, INTELLIGENT_TIERING, GLACIER
```

### 3. Test Rclone Setup

Run the test script:

```bash
python test_rclone.py
```

Expected output:
```
============================================================
Rclone AWS S3 Integration Test
============================================================
✓ Configuration loaded

1. Checking AWS credentials...
✓ AWS_ACCESS_KEY_ID: AKIA...
✓ AWS_SECRET_ACCESS_KEY: ********************

2. Initializing rclone manager...
✓ Rclone manager initialized
  Remote name: aws-s3
  Bucket: my-backup-bucket
  Region: us-east-1

3. Testing S3 bucket access...
✓ Successfully accessed S3 bucket
  Files: 0
  Total size: 0.00 B

4. Testing file upload...
  Created test file: test_upload.txt
✓ File uploaded successfully
  Local: test_upload.txt
  Remote: aws-s3:my-backup-bucket/test/test_upload.txt
  Size: 45 B
  Cleaned up local test file

5. Testing file listing...
✓ Listed 1 files in test/ directory
  - test_upload.txt (45 bytes)

============================================================
✓ All tests passed! Rclone is configured correctly.
============================================================
```

## Usage Examples

### Upload a File

```python
from src.storage.rclone_manager import create_rclone_manager
import yaml

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Create manager
rclone = create_rclone_manager(config)

# Upload file
result = rclone.upload_file('path/to/file.txt', 'backups/file.txt')
print(result)
```

### Upload a Directory

```python
# Sync entire directory to S3
result = rclone.upload_directory('/path/to/folder', 'backups/my-folder')
print(f"Uploaded {result['stats']['transferred']} files")
```

### List Files in S3

```python
# List files in bucket
result = rclone.list_files()
for file in result['files']:
    print(f"{file['Name']} - {file['Size']} bytes")
```

### Check Storage Usage

```python
# Get bucket size
info = rclone.get_bucket_size()
print(f"Total: {info['size_formatted']}")
print(f"Files: {info['count']}")
```

## Storage Classes

AWS S3 offers different storage classes:

| Class | Use Case | Cost |
|-------|----------|------|
| **STANDARD** | Frequently accessed | $$$ |
| **INTELLIGENT_TIERING** | Automatic optimization (recommended) | $$ |
| **GLACIER** | Archive/long-term | $ |
| **DEEP_ARCHIVE** | Rarely accessed | ¢ |

**Recommendation:** Use `INTELLIGENT_TIERING` - automatically moves data between tiers based on access patterns.

## Features

### ✅ Implemented

- ✅ File upload with progress tracking
- ✅ Directory synchronization
- ✅ File listing and search
- ✅ Storage usage monitoring
- ✅ File deletion
- ✅ Existence checking
- ✅ Automatic retry logic
- ✅ Multi-threaded transfers (4 concurrent)
- ✅ Configurable storage classes

### 🔜 Future Enhancements

- [ ] Download from S3
- [ ] Encryption at rest
- [ ] Bandwidth limiting
- [ ] Progress callbacks for UI
- [ ] Incremental backups
- [ ] Lifecycle policies

## Troubleshooting

### Error: "rclone not found"

**Solution:** Install rclone (see Prerequisites)

### Error: "AccessDenied"

**Solution:** 
1. Check AWS credentials in `.env`
2. Verify IAM user has S3 permissions
3. Check bucket name is correct

### Error: "NoSuchBucket"

**Solution:** 
1. Verify bucket exists in AWS Console
2. Check bucket name in `config.yaml`
3. Ensure region matches

### Error: "SignatureDoesNotMatch"

**Solution:**
1. Verify AWS_SECRET_ACCESS_KEY is correct
2. Check for extra spaces in `.env`
3. Regenerate access keys if needed

### Slow Upload Speeds

**Solutions:**
1. Increase transfers: `--transfers 8`
2. Enable compression: `--s3-upload-concurrency 10`
3. Check network bandwidth
4. Consider AWS region proximity

## Best Practices

### 1. Security

- ✅ Never commit `.env` to version control
- ✅ Use IAM user, not root account
- ✅ Apply principle of least privilege
- ✅ Rotate access keys regularly
- ✅ Enable MFA on AWS account

### 2. Cost Optimization

- ✅ Use INTELLIGENT_TIERING storage class
- ✅ Set up lifecycle policies for old data
- ✅ Monitor S3 storage costs in AWS Console
- ✅ Delete old backups periodically

### 3. Performance

- ✅ Upload during off-peak hours
- ✅ Use multiple transfers for large datasets
- ✅ Compress data before upload if possible
- ✅ Choose nearest AWS region

### 4. Reliability

- ✅ Test restore procedures regularly
- ✅ Monitor backup logs
- ✅ Set up CloudWatch alarms
- ✅ Keep local copies temporarily

## Monitoring

### Check Rclone Logs

Logs are stored in: `logs/rclone.log`

```bash
tail -f logs/rclone.log
```

### AWS S3 Console

Monitor your backups:
1. AWS Console → S3 → Your Bucket
2. Check file counts and sizes
3. Review access logs
4. Set up CloudWatch metrics

## Next Steps

1. ✅ Test rclone setup with `python test_rclone.py`
2. ✅ Verify test file appears in S3 Console
3. ✅ Configure backup sources in `config.yaml`
4. ✅ Run initial backup
5. ✅ Set up monitoring and alerts

---

**Need Help?**
- Rclone Docs: https://rclone.org/docs/
- AWS S3 Guide: https://docs.aws.amazon.com/s3/
- Issue Tracker: Report bugs in your project
