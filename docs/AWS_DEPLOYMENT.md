# AWS Deployment Guide

This guide covers deploying the Backup Application to AWS EC2 with complete automation.

## Overview

The deployment creates:
- EC2 instance (t3.small with 100GB storage)
- S3 bucket for backups
- IAM role with appropriate permissions
- Security groups for network access
- Nginx reverse proxy
- Systemd services for application management

## Prerequisites

### 1. AWS Account Setup

- Active AWS account
- AWS CLI installed and configured:
  ```bash
  aws configure
  ```
  You'll need:
  - AWS Access Key ID
  - AWS Secret Access Key
  - Default region (us-east-1 recommended)

### 2. EC2 Key Pair

Create an EC2 key pair for SSH access:

```bash
aws ec2 create-key-pair \
  --key-name backup-app-key \
  --region us-east-1 \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/backup-app-key.pem

chmod 400 ~/.ssh/backup-app-key.pem
```

Or use a different key name by setting the `KEY_NAME` environment variable.

### 3. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   nano .env
   ```

   Required values:
   - `GOOGLE_CLIENT_ID` - From Google Cloud Console
   - `GOOGLE_CLIENT_SECRET` - From Google Cloud Console
   - `EU_PROVIDER_ACCESS_KEY` - Scaleway access key
   - `EU_PROVIDER_SECRET_KEY` - Scaleway secret key
   - `ADMIN_PASSWORD` - Strong password for admin user
   - `API_SECRET_KEY` - Random secret key (generate with `openssl rand -hex 32`)

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

The complete deployment script handles everything automatically:

```bash
# Make script executable
chmod +x aws/deploy-complete.sh

# Run deployment
./aws/deploy-complete.sh
```

**What it does:**
1. Creates S3 bucket for backups
2. Stores environment variables in AWS Parameter Store (optional)
3. Creates IAM role and instance profile
4. Sets up security groups
5. Launches EC2 instance with User Data script
6. Installs and configures all services automatically

**Environment Variables:**

Customize deployment with environment variables:

```bash
# Optional: customize deployment
export AWS_REGION=us-east-1
export INSTANCE_TYPE=t3.small
export KEY_NAME=backup-app-key
export S3_BUCKET_NAME=my-backup-bucket

# Run deployment
./aws/deploy-complete.sh
```

### Method 2: Manual Deployment

If you prefer step-by-step control:

#### Step 1: Create S3 Bucket

```bash
aws s3 mb s3://my-backup-bucket --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-backup-bucket \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket my-backup-bucket \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

#### Step 2: Store Configuration (Optional)

Store your .env file in Parameter Store for automatic retrieval:

```bash
aws ssm put-parameter \
  --name "/backup-app/env" \
  --type "SecureString" \
  --value "$(cat .env)" \
  --region us-east-1
```

#### Step 3: Create IAM Resources

```bash
# Create IAM role
aws iam create-role \
  --role-name backup-app-role \
  --assume-role-policy-document file://aws/iam-trust-policy.json

# Attach policy
aws iam put-role-policy \
  --role-name backup-app-role \
  --policy-name backup-app-policy \
  --policy-document file://aws/iam-policy.json

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name backup-app-profile

# Attach role to profile
aws iam add-role-to-instance-profile \
  --instance-profile-name backup-app-profile \
  --role-name backup-app-role
```

#### Step 4: Create Security Group

```bash
# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name backup-app-sg \
  --description "Security group for backup app" \
  --region us-east-1 \
  --query 'GroupId' \
  --output text)

# Allow SSH
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

# Allow HTTP
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

# Allow HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

#### Step 5: Launch EC2 Instance

```bash
# Get latest Ubuntu 22.04 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text \
  --region us-east-1)

# Launch instance
aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.small \
  --key-name backup-app-key \
  --security-group-ids $SG_ID \
  --iam-instance-profile "Name=backup-app-profile" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=backup-app}]' \
  --user-data file://aws/user-data.sh \
  --region us-east-1
```

## Post-Deployment

### 1. Monitor Installation Progress

The User Data script takes 5-10 minutes to complete. Monitor progress:

```bash
# SSH into instance
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP>

# Watch installation log
tail -f /var/log/user-data.log
```

### 2. Verify Services

Check that all services are running:

```bash
# Check backup daemon
sudo systemctl status backup-daemon

# Check Nginx
sudo systemctl status nginx

# View application logs
sudo journalctl -u backup-daemon -f
```

### 3. Access Application

Open your browser to:
```
http://<PUBLIC_IP>
```

Login with:
- Username: `admin` (or value from .env)
- Password: (from .env `ADMIN_PASSWORD`)

### 4. Configure Google OAuth

1. Go to Settings page in the web dashboard
2. Click "Connect Google Account"
3. Authorize the application
4. Test the connection

See [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md) for detailed OAuth configuration.

### 5. Configure rclone

If you didn't use Parameter Store, manually configure rclone:

```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP>
sudo su - backupapp
rclone config
```

## Security Best Practices

### 1. Enable HTTPS with Let's Encrypt

```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP>

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Certificate auto-renewal is already configured
```

### 2. Restrict Security Group

Update security group to allow SSH only from your IP:

```bash
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 22 --cidr YOUR_IP/32
```

### 3. Use IAM Roles (Already Configured)

The deployment uses IAM roles instead of storing AWS credentials on the instance.

### 4. Regular Updates

```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP>
sudo apt update && sudo apt upgrade -y
sudo systemctl restart backup-daemon
```

## Monitoring

### Check Disk Space

The instance has 100GB for temporary file storage:

```bash
df -h /sync
```

### View Logs

```bash
# Application logs
sudo journalctl -u backup-daemon -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# User data script logs
tail -f /var/log/user-data.log
```

### CloudWatch Integration

The IAM role allows sending metrics to CloudWatch. To enable:

```python
# Add to your application code
import boto3
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='BackupApp',
    MetricData=[
        {
            'MetricName': 'FilesBackedUp',
            'Value': count,
            'Unit': 'Count'
        }
    ]
)
```

## Troubleshooting

### Application Won't Start

```bash
# Check service status
sudo systemctl status backup-daemon

# View detailed logs
sudo journalctl -u backup-daemon -n 100 --no-pager

# Check if Python environment is correct
sudo su - backupapp
cd /opt/backup-app
source venv/bin/activate
python app.py
```

### Can't Connect to Application

```bash
# Check if Nginx is running
sudo systemctl status nginx

# Test local connection
curl http://localhost:8080

# Check security group allows port 80
aws ec2 describe-security-groups --group-ids <SG_ID>
```

### User Data Script Failed

```bash
# View full user data log
cat /var/log/user-data.log

# Re-run specific steps manually
sudo -u backupapp /opt/backup-app/venv/bin/pip install -r /opt/backup-app/requirements.txt
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up sync directory
sudo rm -rf /sync/*

# Consider resizing EBS volume
aws ec2 modify-volume --volume-id <VOLUME_ID> --size 200
```

## Updating the Application

### Pull Latest Code

```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP>
sudo su - backupapp
cd /opt/backup-app
git pull
source venv/bin/activate
pip install -r requirements.txt
exit
sudo systemctl restart backup-daemon
```

### Blue-Green Deployment

For zero-downtime updates:

1. Launch new instance with updated code
2. Test new instance
3. Update DNS/Load Balancer to point to new instance
4. Terminate old instance

## Cost Optimization

### Current Costs (Estimated)

- EC2 t3.small: ~$15/month
- EBS 100GB gp3: ~$8/month
- S3 storage (4TB): ~$94/month
- Data transfer: Variable

**Total: ~$117/month + data transfer**

### Optimization Tips

1. **Use S3 Lifecycle Policies:**
   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket my-backup-bucket \
     --lifecycle-configuration file://lifecycle.json
   ```

2. **Use S3 Intelligent-Tiering:**
   Automatically moves data to cheaper storage tiers

3. **Reserved Instances:**
   Save ~40% with 1-year commitment

4. **Spot Instances:**
   Use for non-critical workloads (not recommended for backup)

## Scaling

### Increase Storage

```bash
# Resize EBS volume
aws ec2 modify-volume --volume-id <VOLUME_ID> --size 200

# On instance, expand filesystem
sudo growpart /dev/xvda 1
sudo resize2fs /dev/xvda1
```

### Upgrade Instance Type

```bash
# Stop instance
aws ec2 stop-instances --instance-ids <INSTANCE_ID>

# Change instance type
aws ec2 modify-instance-attribute \
  --instance-id <INSTANCE_ID> \
  --instance-type t3.medium

# Start instance
aws ec2 start-instances --instance-ids <INSTANCE_ID>
```

## Backup and Disaster Recovery

### Backup EC2 Configuration

```bash
# Create AMI
aws ec2 create-image \
  --instance-id <INSTANCE_ID> \
  --name "backup-app-$(date +%Y%m%d)" \
  --description "Backup app snapshot"
```

### Backup Database

```bash
# Database is SQLite, backup file
scp -i ~/.ssh/backup-app-key.pem \
  ubuntu@<PUBLIC_IP>:/opt/backup-app/sync_state.db \
  ./sync_state.db.backup
```

### S3 Versioning

Already enabled - previous versions are retained automatically.

## Cleanup

To remove all AWS resources:

```bash
# Terminate instance
aws ec2 terminate-instances --instance-ids <INSTANCE_ID>

# Delete security group (after instance terminates)
aws ec2 delete-security-group --group-id <SG_ID>

# Delete IAM resources
aws iam remove-role-from-instance-profile \
  --instance-profile-name backup-app-profile \
  --role-name backup-app-role

aws iam delete-instance-profile --instance-profile-name backup-app-profile

aws iam delete-role-policy \
  --role-name backup-app-role \
  --policy-name backup-app-policy

aws iam delete-role --role-name backup-app-role

# Delete S3 bucket (caution: deletes all backups!)
aws s3 rb s3://my-backup-bucket --force

# Delete Parameter Store parameters
aws ssm delete-parameter --name "/backup-app/env"
```

## Support

For issues:
- Check logs: `sudo journalctl -u backup-daemon -f`
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Open GitHub issue

## Next Steps

After deployment:
1. ✅ Configure Google OAuth (Settings page)
2. ✅ Configure rclone remotes
3. ✅ Start first sync
4. ✅ Monitor progress on Dashboard
5. ✅ Set up CloudWatch alarms (optional)
6. ✅ Configure HTTPS with Let's Encrypt
7. ✅ Set up automated backups of the database
