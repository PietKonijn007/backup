#!/usr/bin/env python3
"""
Cost Optimization Tools
CLI utilities for managing S3 lifecycle policies and monitoring deduplication savings
"""
import argparse
import os
import sys
import subprocess
from src.utils.deduplication_monitor import dedup_monitor


def apply_s3_lifecycle_policy(bucket_name: str, region: str = 'us-east-1'):
    """Apply S3 lifecycle policy for cost optimization"""
    print(f"Applying S3 lifecycle policy to bucket: {bucket_name}")
    print(f"Region: {region}")
    print()
    
    # Check if AWS CLI is available
    try:
        subprocess.run(['aws', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: AWS CLI not found. Please install it first.")
        return False
    
    # Check if lifecycle policy file exists
    policy_file = 'aws/s3-lifecycle-policy.json'
    if not os.path.exists(policy_file):
        print(f"Error: Lifecycle policy file not found: {policy_file}")
        return False
    
    try:
        # Apply lifecycle policy
        cmd = [
            'aws', 's3api', 'put-bucket-lifecycle-configuration',
            '--bucket', bucket_name,
            '--lifecycle-configuration', f'file://{policy_file}',
            '--region', region
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Lifecycle policy applied successfully!")
            print()
            print("Policy Details:")
            print("  - Files move to Glacier after 15 days of no access")
            print("  - Files move to Deep Archive after 90 days")
            print("  - Applies to both current and non-current versions")
            print()
            print("Expected Cost Savings:")
            print("  - Standard storage: $0.023/GB/month")
            print("  - Glacier storage: $0.004/GB/month (83% savings)")
            print("  - Deep Archive: $0.00099/GB/month (96% savings)")
            print()
            return True
        else:
            print(f"Error applying lifecycle policy: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def show_deduplication_stats(days: int = 30):
    """Show deduplication statistics and savings"""
    print(f"Deduplication Statistics (Last {days} days)")
    print("=" * 50)
    
    try:
        dedup_monitor.print_savings_report(days)
        return True
    except Exception as e:
        print(f"Error loading deduplication stats: {e}")
        return False


def estimate_cost_savings(storage_gb: float):
    """Estimate potential cost savings from optimizations"""
    print(f"Cost Savings Estimation for {storage_gb:.1f} GB")
    print("=" * 50)
    
    # Current costs (monthly)
    s3_standard_cost = storage_gb * 0.023
    b2_cost = storage_gb * 0.005
    
    print(f"Current Storage Costs (monthly):")
    print(f"  AWS S3 Standard: ${s3_standard_cost:.2f}")
    print(f"  Backblaze B2: ${b2_cost:.2f}")
    print()
    
    # Lifecycle policy savings (assuming 70% of data moves to Glacier after 15 days)
    glacier_percentage = 0.7
    standard_remaining = storage_gb * (1 - glacier_percentage)
    glacier_storage = storage_gb * glacier_percentage
    
    s3_with_lifecycle = (standard_remaining * 0.023) + (glacier_storage * 0.004)
    lifecycle_savings = s3_standard_cost - s3_with_lifecycle
    
    print(f"With S3 Lifecycle Policy (70% to Glacier after 15 days):")
    print(f"  S3 Standard ({100*(1-glacier_percentage):.0f}%): ${standard_remaining * 0.023:.2f}")
    print(f"  S3 Glacier ({100*glacier_percentage:.0f}%): ${glacier_storage * 0.004:.2f}")
    print(f"  Total S3 cost: ${s3_with_lifecycle:.2f}")
    print(f"  Monthly savings: ${lifecycle_savings:.2f} ({lifecycle_savings/s3_standard_cost*100:.1f}%)")
    print()
    
    # B2 as primary savings
    b2_primary_savings = s3_standard_cost - b2_cost
    print(f"Using Backblaze B2 as Primary:")
    print(f"  B2 cost: ${b2_cost:.2f}")
    print(f"  Monthly savings vs S3: ${b2_primary_savings:.2f} ({b2_primary_savings/s3_standard_cost*100:.1f}%)")
    print()
    
    # Combined savings
    combined_monthly = lifecycle_savings + b2_primary_savings
    combined_annual = combined_monthly * 12
    
    print(f"Combined Optimizations:")
    print(f"  Monthly savings: ${combined_monthly:.2f}")
    print(f"  Annual savings: ${combined_annual:.2f}")
    print(f"  Total reduction: {combined_monthly/(s3_standard_cost + b2_cost)*100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Cost Optimization Tools for Backup Application')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # S3 Lifecycle Policy command
    lifecycle_parser = subparsers.add_parser('lifecycle', help='Apply S3 lifecycle policy')
    lifecycle_parser.add_argument('bucket', help='S3 bucket name')
    lifecycle_parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    # Deduplication stats command
    dedup_parser = subparsers.add_parser('dedup-stats', help='Show deduplication statistics')
    dedup_parser.add_argument('--days', type=int, default=30, help='Number of days to include (default: 30)')
    
    # Cost estimation command
    cost_parser = subparsers.add_parser('estimate-savings', help='Estimate cost savings')
    cost_parser.add_argument('storage_gb', type=float, help='Storage size in GB')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'lifecycle':
        success = apply_s3_lifecycle_policy(args.bucket, args.region)
        sys.exit(0 if success else 1)
    
    elif args.command == 'dedup-stats':
        success = show_deduplication_stats(args.days)
        sys.exit(0 if success else 1)
    
    elif args.command == 'estimate-savings':
        estimate_cost_savings(args.storage_gb)
        sys.exit(0)


if __name__ == '__main__':
    main()