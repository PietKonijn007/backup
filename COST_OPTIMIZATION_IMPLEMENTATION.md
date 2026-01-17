# Cost Optimization Implementation

This document describes the implemented cost optimization features for the backup application, focusing on S3 lifecycle policies and enhanced deduplication.

## 🎯 **Implemented Optimizations**

### **1. S3 Lifecycle Policies (Save $20-30/month)**

**What it does:**
- Automatically moves files to cheaper storage classes based on access patterns
- Files move to Glacier after 15 days of no access (83% cost reduction)
- Files move to Deep Archive after 90 days (96% cost reduction)

**Files created:**
- `aws/s3-lifecycle-policy.json` - Lifecycle policy configuration
- `aws/apply-lifecycle-policy.sh` - Standalone script to apply policy to existing buckets

**Cost Impact:**
- Standard S3: $0.023/GB/month
- Glacier: $0.004/GB/month (83% savings)
- Deep Archive: $0.00099/GB/month (96% savings)
- **Estimated savings: $20-30/month for 4TB**

### **2. Enhanced Deduplication (Save $10-15/month)**

**What it does:**
- Prevents uploading files that already exist with the same size
- Works across all destinations (AWS S3, Backblaze B2, Scaleway)
- Tracks and reports deduplication savings
- Reduces bandwidth, API calls, and storage costs

**Files created/modified:**
- `src/sync/sync_service.py` - Enhanced deduplication logic with detailed logging
- `src/utils/deduplication_monitor.py` - New monitoring and reporting system
- `cost_optimization_tools.py` - CLI tools for managing optimizations

**Features:**
- Per-destination size checking
- Detailed logging of deduplication decisions
- Statistics tracking and reporting
- Cost savings estimation

## 📊 **Usage Instructions**

### **Apply S3 Lifecycle Policy**

For new deployments (automatic):
```bash
# Lifecycle policy is automatically applied during deployment
./aws/deploy-complete.sh
```

For existing buckets:
```bash
# Method 1: Use standalone script
S3_BUCKET_NAME=your-bucket-name ./aws/apply-lifecycle-policy.sh

# Method 2: Use CLI tool
python cost_optimization_tools.py lifecycle your-bucket-name

# Method 3: Manual AWS CLI
aws s3api put-bucket-lifecycle-configuration \
  --bucket your-bucket-name \
  --lifecycle-configuration file://aws/s3-lifecycle-policy.json \
  --region us-east-1
```

### **Monitor Deduplication Savings**

```bash
# Show deduplication stats for last 30 days
python cost_optimization_tools.py dedup-stats

# Show stats for last 7 days
python cost_optimization_tools.py dedup-stats --days 7

# Estimate cost savings for your storage size
python cost_optimization_tools.py estimate-savings 4000  # for 4TB
```

### **Check Deduplication in Logs**

Look for these log messages during sync operations:
```
INFO: DEDUPLICATION: Skipping upload - file already exists in all destinations with same size: document.pdf
INFO: Deduplication saved: 15.2 MB for document.pdf
INFO: Batch sync complete: 45 uploaded, 123 skipped (deduplication), 2 failed
INFO: Deduplication savings: 2.3 GB (123 files)
```

## 🔧 **Technical Details**

### **S3 Lifecycle Policy Configuration**

```json
{
  "Rules": [
    {
      "ID": "BackupArchivalPolicy",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 15,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 90,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ]
    }
  ]
}
```

### **Enhanced Deduplication Logic**

1. **File Metadata Check**: Gets file size and modification time from Google Drive
2. **Per-Destination Verification**: Checks each destination (S3, B2, Scaleway) separately
3. **Size Comparison**: Compares local file size with remote file size
4. **Skip Decision**: Skips upload only if file exists in ALL destinations with exact size match
5. **Statistics Recording**: Tracks savings for reporting and cost analysis

### **Deduplication Monitor Features**

- **Real-time Tracking**: Records every deduplication event
- **Daily Statistics**: Breaks down savings by day
- **Per-Destination Stats**: Shows savings per storage provider
- **Cost Estimation**: Calculates monetary savings based on provider pricing
- **Persistent Storage**: Saves statistics to `deduplication_stats.json`

## 📈 **Expected Savings**

### **For 4TB Backup:**

| Optimization | Monthly Savings | Implementation |
|-------------|----------------|----------------|
| S3 Lifecycle (70% to Glacier) | $25 | ✅ Implemented |
| Enhanced Deduplication | $10-15 | ✅ Implemented |
| **Total Immediate Savings** | **$35-40** | **Ready to use** |

### **Annual Impact:**
- **Monthly**: $35-40 saved
- **Annual**: $420-480 saved
- **Percentage**: 25-30% cost reduction

## 🚀 **Activation Steps**

### **For New Deployments:**
1. Run `./aws/deploy-complete.sh` - lifecycle policy applied automatically
2. Deduplication is active by default
3. Monitor savings with `python cost_optimization_tools.py dedup-stats`

### **For Existing Deployments:**
1. **Apply Lifecycle Policy:**
   ```bash
   S3_BUCKET_NAME=your-bucket-name ./aws/apply-lifecycle-policy.sh
   ```

2. **Update Application Code:**
   ```bash
   git pull  # Get latest changes
   sudo systemctl restart backup-daemon  # Restart with new deduplication
   ```

3. **Verify Deduplication:**
   ```bash
   # Check logs for deduplication messages
   sudo journalctl -u backup-daemon -f | grep DEDUPLICATION
   ```

## 📋 **Monitoring and Verification**

### **S3 Lifecycle Policy Status:**
```bash
# Check if policy is applied
aws s3api get-bucket-lifecycle-configuration --bucket your-bucket-name

# Monitor storage class transitions in S3 Console
# AWS Console > S3 > Bucket > Metrics > Storage class analysis
```

### **Deduplication Effectiveness:**
```bash
# Daily monitoring
python cost_optimization_tools.py dedup-stats --days 1

# Weekly summary
python cost_optimization_tools.py dedup-stats --days 7

# Check deduplication stats file
cat deduplication_stats.json | jq '.total_bytes_saved'
```

### **Application Logs:**
```bash
# Real-time deduplication monitoring
sudo journalctl -u backup-daemon -f | grep -E "(DEDUPLICATION|skipped|saved)"

# Daily summary in logs
sudo journalctl -u backup-daemon --since "1 day ago" | grep "Deduplication savings"
```

## ⚠️ **Important Notes**

### **S3 Lifecycle Policy:**
- Files in Glacier take 1-5 minutes to retrieve (costs $0.01/GB)
- Deep Archive takes 12 hours to retrieve (costs $0.02/GB)
- Consider access patterns when setting transition days
- Policy applies to all files in the bucket

### **Deduplication:**
- Only skips files with exact size match
- Does not compare file content/checksums (for performance)
- Works across all configured destinations
- Statistics are stored locally in `deduplication_stats.json`

### **Cost Calculations:**
- Based on current AWS/B2 pricing (January 2025)
- Actual savings depend on access patterns and file types
- Monitor actual costs in AWS/B2 billing dashboards

## 🔄 **Next Steps**

After implementing these optimizations, consider:

1. **Monitor for 30 days** to measure actual savings
2. **Adjust lifecycle policy** based on access patterns
3. **Consider Reserved Instances** for additional EC2 savings
4. **Implement compression** for document files
5. **Add cost alerting** for budget monitoring

## 📞 **Troubleshooting**

### **Lifecycle Policy Issues:**
```bash
# Check policy syntax
aws s3api get-bucket-lifecycle-configuration --bucket your-bucket-name

# Verify permissions
aws iam get-role-policy --role-name backup-app-role --policy-name backup-app-policy
```

### **Deduplication Not Working:**
```bash
# Check if monitor is recording events
cat deduplication_stats.json

# Verify sync service is using new code
sudo systemctl status backup-daemon
sudo journalctl -u backup-daemon --since "1 hour ago" | grep dedup
```

### **Cost Tracking:**
```bash
# AWS costs
aws ce get-cost-and-usage --time-period Start=2025-01-01,End=2025-01-31 --granularity MONTHLY --metrics BlendedCost

# B2 costs - check Backblaze dashboard
# Scaleway costs - check Scaleway console
```