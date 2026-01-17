"""
Database Logger - Writes logs to SQLite database
"""
import logging
import sqlite3
from datetime import datetime
from src.database.models import get_db


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes to database"""
    
    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)
        
    def emit(self, record):
        """Write log record to database"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Format the log message
            message = self.format(record)
            
            # Get additional details if available
            details = None
            if hasattr(record, 'exc_info') and record.exc_info:
                details = self.formatException(record.exc_info)
            
            cursor.execute('''
                INSERT INTO logs (timestamp, level, source, message, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.fromtimestamp(record.created).isoformat(),
                record.levelname,
                record.name,
                message,
                details
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"Database logging error: {e}")


def setup_database_logging():
    """Set up database logging for the application"""
    # Get root logger
    root_logger = logging.getLogger()
    
    # Create database handler
    db_handler = DatabaseLogHandler()
    
    # Set format
    formatter = logging.Formatter('%(message)s')
    db_handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger.addHandler(db_handler)
    
    return db_handler


def log_sync_event(file_id, action, status, message=None):
    """Log a sync-specific event"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO logs (timestamp, level, source, message)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            'INFO' if status == 'success' else 'ERROR',
            'sync',
            f"{action}: {file_id} - {status}" + (f" - {message}" if message else "")
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error logging sync event: {e}")


def log_daemon_event(action, status, message=None):
    """Log a daemon-specific event"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO logs (timestamp, level, source, message)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            'INFO',
            'daemon',
            f"Daemon {action}: {status}" + (f" - {message}" if message else "")
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error logging daemon event: {e}")


def cleanup_old_logs(days=30):
    """Clean up logs older than specified days"""
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM logs 
            WHERE timestamp < ?
        ''', (cutoff_date.isoformat(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            log_daemon_event('cleanup', 'success', f"Deleted {deleted_count} old log entries")
        
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up logs: {e}")
        return 0