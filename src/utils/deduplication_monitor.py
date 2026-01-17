"""
Deduplication Monitoring Utility
Tracks and reports on deduplication savings across all sync operations
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from src.utils.logger import setup_logger

logger = setup_logger('deduplication-monitor')


class DeduplicationMonitor:
    """Monitors and tracks deduplication savings"""
    
    def __init__(self, stats_file: str = 'deduplication_stats.json'):
        """
        Initialize deduplication monitor
        
        Args:
            stats_file: Path to JSON file for storing statistics
        """
        self.stats_file = stats_file
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load existing statistics from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load deduplication stats: {e}")
        
        return {
            'total_files_checked': 0,
            'total_files_skipped': 0,
            'total_bytes_saved': 0,
            'daily_stats': {},
            'destination_stats': {},
            'last_updated': None
        }
    
    def _save_stats(self):
        """Save statistics to file"""
        try:
            self.stats['last_updated'] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save deduplication stats: {e}")
    
    def record_deduplication(self, file_name: str, file_size: int, destinations: List[str]):
        """
        Record a deduplication event
        
        Args:
            file_name: Name of the file that was deduplicated
            file_size: Size of the file in bytes
            destinations: List of destinations where file was skipped
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Update overall stats
        self.stats['total_files_checked'] += 1
        self.stats['total_files_skipped'] += 1
        self.stats['total_bytes_saved'] += file_size
        
        # Update daily stats
        if today not in self.stats['daily_stats']:
            self.stats['daily_stats'][today] = {
                'files_checked': 0,
                'files_skipped': 0,
                'bytes_saved': 0
            }
        
        daily = self.stats['daily_stats'][today]
        daily['files_checked'] += 1
        daily['files_skipped'] += 1
        daily['bytes_saved'] += file_size
        
        # Update per-destination stats
        for dest in destinations:
            if dest not in self.stats['destination_stats']:
                self.stats['destination_stats'][dest] = {
                    'files_skipped': 0,
                    'bytes_saved': 0
                }
            
            dest_stats = self.stats['destination_stats'][dest]
            dest_stats['files_skipped'] += 1
            dest_stats['bytes_saved'] += file_size
        
        logger.debug(f"Recorded deduplication: {file_name} ({self._format_size(file_size)}) for {destinations}")
        self._save_stats()
    
    def record_file_check(self, file_name: str, file_size: int, was_skipped: bool, destinations: List[str]):
        """
        Record any file check (whether skipped or uploaded)
        
        Args:
            file_name: Name of the file
            file_size: Size of the file in bytes
            was_skipped: Whether the file was skipped due to deduplication
            destinations: List of destinations
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Update overall stats
        self.stats['total_files_checked'] += 1
        
        # Update daily stats
        if today not in self.stats['daily_stats']:
            self.stats['daily_stats'][today] = {
                'files_checked': 0,
                'files_skipped': 0,
                'bytes_saved': 0
            }
        
        daily = self.stats['daily_stats'][today]
        daily['files_checked'] += 1
        
        if was_skipped:
            self.record_deduplication(file_name, file_size, destinations)
    
    def get_savings_report(self, days: int = 30) -> Dict:
        """
        Get deduplication savings report
        
        Args:
            days: Number of days to include in report
            
        Returns:
            dict: Savings report with statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Calculate recent stats
        recent_files_checked = 0
        recent_files_skipped = 0
        recent_bytes_saved = 0
        
        for date_str, daily_stats in self.stats['daily_stats'].items():
            if date_str >= cutoff_str:
                recent_files_checked += daily_stats['files_checked']
                recent_files_skipped += daily_stats['files_skipped']
                recent_bytes_saved += daily_stats['bytes_saved']
        
        # Calculate deduplication rate
        total_dedup_rate = (self.stats['total_files_skipped'] / max(self.stats['total_files_checked'], 1)) * 100
        recent_dedup_rate = (recent_files_skipped / max(recent_files_checked, 1)) * 100
        
        return {
            'period_days': days,
            'total_stats': {
                'files_checked': self.stats['total_files_checked'],
                'files_skipped': self.stats['total_files_skipped'],
                'bytes_saved': self.stats['total_bytes_saved'],
                'bytes_saved_formatted': self._format_size(self.stats['total_bytes_saved']),
                'deduplication_rate': round(total_dedup_rate, 2)
            },
            'recent_stats': {
                'files_checked': recent_files_checked,
                'files_skipped': recent_files_skipped,
                'bytes_saved': recent_bytes_saved,
                'bytes_saved_formatted': self._format_size(recent_bytes_saved),
                'deduplication_rate': round(recent_dedup_rate, 2)
            },
            'destination_breakdown': {
                dest: {
                    'files_skipped': stats['files_skipped'],
                    'bytes_saved': stats['bytes_saved'],
                    'bytes_saved_formatted': self._format_size(stats['bytes_saved'])
                }
                for dest, stats in self.stats['destination_stats'].items()
            },
            'estimated_cost_savings': self._calculate_cost_savings(self.stats['total_bytes_saved'])
        }
    
    def _calculate_cost_savings(self, bytes_saved: int) -> Dict:
        """
        Calculate estimated cost savings from deduplication
        
        Args:
            bytes_saved: Total bytes saved through deduplication
            
        Returns:
            dict: Cost savings breakdown by provider
        """
        gb_saved = bytes_saved / (1024 ** 3)  # Convert to GB
        
        # Cost per GB per month for different providers
        costs = {
            'aws_s3_standard': 0.023,
            'aws_s3_ia': 0.0125,
            'backblaze_b2': 0.005,
            'scaleway': 0.01
        }
        
        savings = {}
        for provider, cost_per_gb in costs.items():
            monthly_savings = gb_saved * cost_per_gb
            annual_savings = monthly_savings * 12
            savings[provider] = {
                'monthly_savings': round(monthly_savings, 2),
                'annual_savings': round(annual_savings, 2)
            }
        
        return savings
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def print_savings_report(self, days: int = 30):
        """Print a formatted savings report to console"""
        report = self.get_savings_report(days)
        
        print("\n" + "="*60)
        print("DEDUPLICATION SAVINGS REPORT")
        print("="*60)
        
        print(f"\nPeriod: Last {days} days")
        print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\nTOTAL STATISTICS (All Time):")
        total = report['total_stats']
        print(f"  Files checked: {total['files_checked']:,}")
        print(f"  Files skipped: {total['files_skipped']:,}")
        print(f"  Bytes saved: {total['bytes_saved_formatted']}")
        print(f"  Deduplication rate: {total['deduplication_rate']}%")
        
        print(f"\nRECENT STATISTICS (Last {days} days):")
        recent = report['recent_stats']
        print(f"  Files checked: {recent['files_checked']:,}")
        print(f"  Files skipped: {recent['files_skipped']:,}")
        print(f"  Bytes saved: {recent['bytes_saved_formatted']}")
        print(f"  Deduplication rate: {recent['deduplication_rate']}%")
        
        print(f"\nDESTINATION BREAKDOWN:")
        for dest, stats in report['destination_breakdown'].items():
            print(f"  {dest}:")
            print(f"    Files skipped: {stats['files_skipped']:,}")
            print(f"    Bytes saved: {stats['bytes_saved_formatted']}")
        
        print(f"\nESTIMATED MONTHLY COST SAVINGS:")
        for provider, savings in report['estimated_cost_savings'].items():
            if savings['monthly_savings'] > 0:
                print(f"  {provider}: ${savings['monthly_savings']:.2f}/month (${savings['annual_savings']:.2f}/year)")
        
        print("="*60)


# Global instance for easy access
dedup_monitor = DeduplicationMonitor()