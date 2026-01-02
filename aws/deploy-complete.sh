#!/bin/bash
# Complete AWS Deployment Script for Backup Application
# This script creates all necessary AWS resources and deploys the application

set -e

echo "=== Backup App Complete AWS Deployment ==="
echo ""

# Configuration
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.small}"
KEY_NAME="${KEY_NAME:-backup-app-key}"
SECURITY_GROUP="backup-app-sg"
IAM_ROLE_NAME="backup-app-role"
INSTANCE_PROFILE_NAME="backup-app-profile"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-backup-app-storage-$(date +%s)}"

echo "Configuration:"
echo "  Region: $REGION"
echo "  Instance Type: $INSTANCE_TYPE"
echo "  Key Name: $KEY_NAME"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    echo "Install it with: pip install awscli"
    exit 1
fi

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Using AWS Account: $ACCOUNT_ID"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "You'll need to configure environment variables manually or via Parameter Store"
    echo ""
fi

# Step 1: Create S3 Bucket
echo "Step 1: Creating S3 bucket for backups..."
if aws s3 ls "s3://$S3_BUCKET_NAME" 2>/dev/null; then
    echo "Bucket $S3_BUCKET_NAME already exists"
else
    aws s3 mb "s3://$S3_BUCKET_NAME" --region $REGION
    echo "Bucket created: $S3_BUCKET_NAME"
fi

# Enable versioning and encryption
aws s3api put-bucket-versioning \
    --bucket $S3_BUCKET_NAME \
    --versioning-configuration Status=Enabled \
    --region $REGION || true

aws s3api put-bucket-encryption \
    --bucket $S3_BUCKET_NAME \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
    --region $REGION || true

echo "S3 bucket configured with versioning and encryption"
echo ""

# Step 2: Store environment variables in Parameter Store
echo "Step 2: Storing configuration in Parameter Store..."
if [ -f ".env" ]; then
    read -p "Do you want to upload .env to Parameter Store? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        aws ssm put-parameter \
            --name "/backup-app/env" \
            --type "SecureString" \
            --value "$(cat .env)" \
            --region $REGION \
            --overwrite 2>/dev/null || \
        aws ssm put-parameter \
            --name "/backup-app/env" \
            --type "SecureString" \
            --value "$(cat .env)" \
            --region $REGION
        echo "Environment variables stored in Parameter Store"
    fi
fi
echo ""

# Step 3: Create IAM Role
echo "Step 3: Creating IAM role and instance profile..."

# Create IAM role
aws iam create-role \
    --role-name $IAM_ROLE_NAME \
    --assume-role-policy-document file://aws/iam-trust-policy.json \
    --region $REGION 2>/dev/null || echo "IAM role may already exist"

# Attach policy
aws iam put-role-policy \
    --role-name $IAM_ROLE_NAME \
    --policy-name backup-app-policy \
    --policy-document file://aws/iam-policy.json \
    --region $REGION

# Create instance profile
aws iam create-instance-profile \
    --instance-profile-name $INSTANCE_PROFILE_NAME \
    --region $REGION 2>/dev/null || echo "Instance profile may already exist"

# Attach role to instance profile
aws iam add-role-to-instance-profile \
    --instance-profile-name $INSTANCE_PROFILE_NAME \
    --role-name $IAM_ROLE_NAME \
    --region $REGION 2>/dev/null || true

echo "IAM role and instance profile configured"
echo ""

# Wait for instance profile to be ready
echo "Waiting for instance profile to propagate..."
sleep 10

# Step 4: Create Security Group
echo "Step 4: Creating security group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name $SECURITY_GROUP \
    --description "Security group for backup app" \
    --region $REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
        --group-names $SECURITY_GROUP \
        --region $REGION \
        --query 'SecurityGroups[0].GroupId' \
        --output text)

echo "Security Group ID: $SG_ID"

# Add ingress rules
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 22 --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 80 --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 443 --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true

echo "Security group configured (ports 22, 80, 443)"
echo ""

# Step 5: Check for existing key pair
echo "Step 5: Checking EC2 key pair..."
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION &>/dev/null; then
    echo "Error: Key pair '$KEY_NAME' not found"
    echo ""
    echo "Create a key pair with:"
    echo "  aws ec2 create-key-pair --key-name $KEY_NAME --region $REGION --query 'KeyMaterial' --output text > ~/.ssh/$KEY_NAME.pem"
    echo "  chmod 400 ~/.ssh/$KEY_NAME.pem"
    echo ""
    read -p "Press enter to continue after creating the key pair, or Ctrl+C to exit..."
fi
echo "Key pair found: $KEY_NAME"
echo ""

# Step 6: Get latest Ubuntu AMI
echo "Step 6: Finding latest Ubuntu 22.04 AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text \
    --region $REGION)

echo "Using AMI: $AMI_ID"
echo ""

# Step 7: Launch EC2 instance
echo "Step 7: Launching EC2 instance..."
echo "This will take several minutes as the instance sets up..."
echo ""

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --iam-instance-profile "Name=$INSTANCE_PROFILE_NAME" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=backup-app},{Key=Application,Value=backup-app}]" \
    --user-data file://aws/user-data.sh \
    --region $REGION \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Instance launched: $INSTANCE_ID"
echo "Waiting for instance to be running..."

aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $REGION)

PUBLIC_DNS=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicDnsName' \
    --output text \
    --region $REGION)

echo ""
echo "==================================="
echo "=== Deployment In Progress ==="
echo "==================================="
echo ""
echo "Instance Details:"
echo "  Instance ID: $INSTANCE_ID"
echo "  Public IP: $PUBLIC_IP"
echo "  Public DNS: $PUBLIC_DNS"
echo "  Region: $REGION"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo ""
echo "The instance is now running and installing the application."
echo "This process takes approximately 5-10 minutes."
echo ""
echo "To monitor the installation progress:"
echo "  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo "  tail -f /var/log/user-data.log"
echo ""
echo "Once complete, access the application at:"
echo "  http://$PUBLIC_IP"
echo ""
echo "Check service status:"
echo "  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP 'sudo systemctl status backup-daemon'"
echo ""
echo "View application logs:"
echo "  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP 'sudo journalctl -u backup-daemon -f'"
echo ""
echo "To connect via SSH:"
echo "  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo ""
echo "==================================="
echo ""

# Save deployment info
cat > deployment-info.txt << EOF
Backup App Deployment Information
Generated: $(date)

Instance ID: $INSTANCE_ID
Public IP: $PUBLIC_IP
Public DNS: $PUBLIC_DNS
Region: $REGION
S3 Bucket: $S3_BUCKET_NAME
Security Group: $SG_ID
IAM Role: $IAM_ROLE_NAME
Instance Profile: $INSTANCE_PROFILE_NAME

Application URL: http://$PUBLIC_IP
SSH Command: ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP

Monitor Installation:
  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/user-data.log'

Check Status:
  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP 'sudo systemctl status backup-daemon'

View Logs:
  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP 'sudo journalctl -u backup-daemon -f'
EOF

echo "Deployment information saved to: deployment-info.txt"
echo ""
echo "Waiting 2 minutes before checking if the application is ready..."
sleep 120

echo "Checking application status..."
if curl -s -o /dev/null -w "%{http_code}" "http://$PUBLIC_IP" | grep -q "200\|302"; then
    echo "✓ Application is responding!"
else
    echo "⚠ Application not yet ready. Check logs with:"
    echo "  ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP 'sudo journalctl -u backup-daemon -f'"
fi

echo ""
echo "=== Deployment Complete ==="
