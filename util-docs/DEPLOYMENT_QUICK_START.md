# Quick Start: Deploy to AWS

## Prerequisites Checklist

Before deploying, ensure you have:

- [x] AWS CLI installed and configured (`aws configure`)
- [ ] EC2 key pair created (or will create during deployment)
- [ ] `.env` file configured with all credentials
- [ ] AWS account with sufficient permissions

## Deploy in 3 Steps

### Step 1: Create EC2 Key Pair (if you don't have one)

```bash
aws ec2 create-key-pair \
  --key-name backup-app-key \
  --region us-east-1 \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/backup-app-key.pem

chmod 400 ~/.ssh/backup-app-key.pem
```

### Step 2: Configure Environment Variables

Ensure your `.env` file has all required values:

```bash
# Check .env file exists and has required values
cat .env | grep -E "GOOGLE_CLIENT_ID|EU_PROVIDER_ACCESS_KEY|ADMIN_PASSWORD"
```

### Step 3: Run Deployment

```bash
./aws/deploy-complete.sh
```

**Optional:** Customize deployment parameters:

```bash
# Custom configuration
export AWS_REGION=us-east-1
export INSTANCE_TYPE=t3.small
export KEY_NAME=backup-app-key
export S3_BUCKET_NAME=my-custom-bucket-name

# Run deployment
./aws/deploy-complete.sh
```

## What Happens During Deployment

The script will:

1. ✅ Create S3 bucket with encryption and versioning
2. ✅ Store environment variables in AWS Parameter Store (optional)
3. ✅ Create IAM role with appropriate permissions
4. ✅ Set up security groups (ports 22, 80, 443)
5. ✅ Launch EC2 instance (t3.small, 100GB storage)
6. ✅ Install all dependencies automatically via User Data script
7. ✅ Configure Nginx reverse proxy
8. ✅ Start application as systemd service

**Estimated time:** 5-10 minutes

## Post-Deployment

After deployment completes, you'll see:

```
Instance ID: i-xxxxxxxxxxxxx
Public IP: x.x.x.x
Application URL: http://x.x.x.x
```

### Access Your Application

1. Open browser to: `http://<PUBLIC_IP>`
2. Login with credentials from `.env` file
3. Go to Settings → Connect Google Account
4. Start your first sync!

### Monitor Installation Progress

```bash
# SSH into instance
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP>

# Watch installation log
tail -f /var/log/user-data.log
```

### Check Application Status

```bash
# Via SSH
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP> 'sudo systemctl status backup-daemon'

# View logs
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP> 'sudo journalctl -u backup-daemon -f'
```

## Troubleshooting

### Deployment Script Fails

**Error: AWS credentials not configured**
```bash
aws configure
```

**Error: Key pair not found**
```bash
# Create key pair first (see Step 1 above)
aws ec2 create-key-pair --key-name backup-app-key --region us-east-1 --query 'KeyMaterial' --output text > ~/.ssh/backup-app-key.pem
chmod 400 ~/.ssh/backup-app-key.pem
```

**Error: .env file not found**
```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

### Application Won't Start

```bash
# Check user data log for errors
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP> 'cat /var/log/user-data.log'

# Check service status
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP> 'sudo systemctl status backup-daemon'

# View detailed logs
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP> 'sudo journalctl -u backup-daemon -n 100 --no-pager'
```

### Can't Access Application

1. Wait 5-10 minutes for installation to complete
2. Check security group allows port 80
3. Try accessing from different browser/network
4. Check if app is running: `curl http://<PUBLIC_IP>`

## Cost Estimate

| Resource | Cost |
|----------|------|
| EC2 t3.small | ~$15/month |
| EBS 100GB gp3 | ~$8/month |
| S3 storage (4TB) | ~$94/month |
| **Total** | **~$117/month** |

+ Data transfer costs (variable)

## Next Steps

After successful deployment:

1. ✅ **Configure Google OAuth** - Settings page
2. ✅ **Test connection** - Use "Connect Google Account" button
3. ✅ **Configure sync items** - Add Drive folders/albums
4. ✅ **Start first sync** - Monitor on Dashboard
5. 🔒 **Enable HTTPS** - Use Let's Encrypt (optional but recommended)
6. 🔒 **Restrict SSH access** - Update security group to your IP only

## Enable HTTPS (Recommended)

After deployment, secure your application with HTTPS:

```bash
ssh -i ~/.ssh/backup-app-key.pem ubuntu@<PUBLIC_IP>

# Point a domain to your IP address first
# Then run:
sudo certbot --nginx -d your-domain.com

# Certificate auto-renewal is already configured
```

## Cleanup / Destroy Resources

To remove all AWS resources and stop billing:

```bash
# Get instance ID from deployment-info.txt
INSTANCE_ID=<your-instance-id>
S3_BUCKET=<your-bucket-name>
SG_ID=<your-security-group-id>

# Terminate instance
aws ec2 terminate-instances --instance-ids $INSTANCE_ID

# Wait for termination
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID

# Delete security group
aws ec2 delete-security-group --group-id $SG_ID

# Delete IAM resources
aws iam remove-role-from-instance-profile \
  --instance-profile-name backup-app-profile \
  --role-name backup-app-role

aws iam delete-instance-profile --instance-profile-name backup-app-profile
aws iam delete-role-policy --role-name backup-app-role --policy-name backup-app-policy
aws iam delete-role --role-name backup-app-role

# Delete S3 bucket (WARNING: Deletes all backups!)
aws s3 rb s3://$S3_BUCKET --force

# Delete Parameter Store
aws ssm delete-parameter --name "/backup-app/env"
```

## Support

- 📖 Full Documentation: [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md)
- 🔧 Troubleshooting: Check application logs
- 💬 Issues: Open GitHub issue

## Ready to Deploy?

```bash
./aws/deploy-complete.sh
```

🚀 Your backup application will be live on AWS in ~10 minutes!
