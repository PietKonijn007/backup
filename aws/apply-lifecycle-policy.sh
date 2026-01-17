#!/bin/bash
# Apply S3 Lifecycle Policy to Existing Bucket
# This script applies cost-optimized lifecycle policies to your S3 backup bucket

set -e

echo "=== S3 Lifecycle Policy Application ==="
echo ""

# Configuration
REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET_NAME="${S3_BUCKET_NAME}"

if [ -z "$S3_BUCKET_NAME" ]; then
    echo "Error: S3_BUCKET_NAME environment variable not set"
    echo "Usage: S3_BUCKET_NAME=your-bucket-name ./aws/apply-lifecycle-policy.sh"
    exit 1
fi

echo "Configuration:"
echo "  Region: $REGION"
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

# Check if bucket exists
echo "Checking if bucket exists..."
if ! aws s3 ls "s3://$S3_BUCKET_NAME" --region $REGION &> /dev/null; then
    echo "Error: Bucket $S3_BUCKET_NAME does not exist or is not accessible"
    exit 1
fi

echo "Bucket found: $S3_BUCKET_NAME"
echo ""

# Show current lifecycle configuration (if any)
echo "Current lifecycle configuration:"
aws s3api get-bucket-lifecycle-configuration \
    --bucket $S3_BUCKET_NAME \
    --region $REGION 2>/dev/null || echo "No lifecycle configuration found"
echo ""

# Apply new lifecycle policy
echo "Applying new lifecycle policy..."
echo "  - Files will move to Glacier after 15 days of no access"
echo "  - Files will move to Deep Archive after 90 days"
echo "  - This applies to both current and non-current versions"
echo ""

read -p "Do you want to apply this lifecycle policy? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    aws s3api put-bucket-lifecycle-configuration \
        --bucket $S3_BUCKET_NAME \
        --lifecycle-configuration file://aws/s3-lifecycle-policy.json \
        --region $REGION
    
    echo "✓ Lifecycle policy applied successfully!"
    echo ""
    echo "Cost Impact:"
    echo "  - Standard storage: $0.023/GB/month"
    echo "  - Glacier storage: $0.004/GB/month (83% savings)"
    echo "  - Deep Archive: $0.00099/GB/month (96% savings)"
    echo ""
    echo "Files will automatically transition based on access patterns."
    echo "Retrieval from Glacier takes 1-5 minutes and costs $0.01/GB."
    echo ""
else
    echo "Lifecycle policy not applied."
fi

echo "=== Complete ==="