#!/bin/bash
# Deployment script for AWS EC2

set -e

echo "=== Backup App Deployment Script ==="
echo ""
echo "This script will deploy the backup app to AWS EC2"
echo ""

# Configuration
REGION="us-east-1"
INSTANCE_TYPE="t3.small"
KEY_NAME="${KEY_NAME:-backup-app-key}"
SECURITY_GROUP="backup-app-sg"

echo "Configuration:"
echo "  Region: $REGION"
echo "  Instance Type: $INSTANCE_TYPE"
echo "  Key Name: $KEY_NAME"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    echo "Install it with: pip install awscli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

echo "Step 1: Creating security group..."
aws ec2 create-security-group \
    --group-name $SECURITY_GROUP \
    --description "Security group for backup app" \
    --region $REGION || echo "Security group may already exist"

# Allow SSH
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp --port 22 --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true

# Allow HTTP
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp --port 80 --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true

# Allow HTTPS
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp --port 443 --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true

# Allow custom port 8080
aws ec2 authorize-security-group-ingress \
    --group-name $SECURITY_GROUP \
    --protocol tcp --port 8080 --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || true

echo "Security group configured"

echo ""
echo "Step 2: Get latest Ubuntu AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text \
    --region $REGION)

echo "Using AMI: $AMI_ID"

echo ""
echo "Step 3: Launch EC2 instance..."
echo "Note: Make sure you have created an EC2 key pair named '$KEY_NAME'"
echo ""

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-groups $SECURITY_GROUP \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}}]' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=backup-app}]' \
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

echo "Instance is running at: $PUBLIC_IP"
echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. SSH into the instance: ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo "2. Clone the repository"
echo "3. Run setup-instance.sh"
echo "4. Configure .env with your credentials"
echo "5. Start the application"
echo ""
echo "Access the dashboard at: http://$PUBLIC_IP:8080"
echo ""
