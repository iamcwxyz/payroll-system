"""
Backup and Disaster Recovery System
Provides automated database backup and recovery capabilities
"""

import sqlite3
import os
import shutil
import gzip
import json
from datetime import datetime, timedelta
from database import get_db_connection, log_security_event
import threading
import time

class BackupManager:
    """Manages database backups and recovery operations"""
    
    def __init__(self, backup_dir="backups"):
        self.backup_dir = backup_dir
        self.db_name = "payroll_system.db"
        self.max_backups = 30  # Keep 30 days of backups
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_full_backup(self, compress=True):
        """Create a complete database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"payroll_backup_{timestamp}"
            
            if compress:
                backup_path = os.path.join(self.backup_dir, f"{backup_filename}.gz")
            else:
                backup_path = os.path.join(self.backup_dir, f"{backup_filename}.db")
            
            # Create backup
            if compress:
                with gzip.open(backup_path, 'wb') as gz_file:
                    with open(self.db_name, 'rb') as db_file:
                        shutil.copyfileobj(db_file, gz_file)
            else:
                shutil.copy2(self.db_name, backup_path)
            
            # Create metadata file
            metadata = {
                'backup_time': datetime.now().isoformat(),
                'backup_type': 'full',
                'compressed': compress,
                'file_size': os.path.getsize(backup_path),
                'database_version': self.get_database_version()
            }
            
            metadata_path = os.path.join(self.backup_dir, f"{backup_filename}.json")
            with open(metadata_path, 'w') as meta_file:
                json.dump(metadata, meta_file, indent=2)
            
            # Log backup creation
            log_security_event('BACKUP_CREATED', None, 'system', f"Full backup created: {backup_filename}")
            
            # Clean old backups
            self.cleanup_old_backups()
            
            return True, backup_path
            
        except Exception as e:
            log_security_event('BACKUP_FAILED', None, 'system', f"Backup failed: {str(e)}")
            return False, str(e)
    
    def restore_backup(self, backup_path, user_id=None):
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                return False, "Backup file not found"
            
            # Create a backup of current database before restore
            current_backup_path = f"{self.db_name}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_name, current_backup_path)
            
            # Restore from backup
            if backup_path.endswith('.gz'):
                with gzip.open(backup_path, 'rb') as gz_file:
                    with open(self.db_name, 'wb') as db_file:
                        shutil.copyfileobj(gz_file, db_file)
            else:
                shutil.copy2(backup_path, self.db_name)
            
            # Log restore operation
            log_security_event('DATABASE_RESTORED', user_id, 'system', 
                             f"Database restored from: {os.path.basename(backup_path)}")
            
            return True, "Database restored successfully"
            
        except Exception as e:
            # Try to restore the pre-restore backup if restoration failed
            if 'current_backup_path' in locals() and os.path.exists(current_backup_path):
                shutil.copy2(current_backup_path, self.db_name)
            
            log_security_event('RESTORE_FAILED', user_id, 'system', f"Restore failed: {str(e)}")
            return False, str(e)
    
    def get_database_version(self):
        """Get database schema version"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version")
            version = cursor.fetchone()[0]
            conn.close()
            return version
        except:
            return 0
    
    def list_backups(self):
        """List available backups with metadata"""
        backups = []
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.json'):
                metadata_path = os.path.join(self.backup_dir, filename)
                try:
                    with open(metadata_path, 'r') as meta_file:
                        metadata = json.load(meta_file)
                    
                    backup_name = filename.replace('.json', '')
                    backup_file = f"{backup_name}.gz" if metadata.get('compressed') else f"{backup_name}.db"
                    backup_path = os.path.join(self.backup_dir, backup_file)
                    
                    if os.path.exists(backup_path):
                        metadata['backup_name'] = backup_name
                        metadata['backup_path'] = backup_path
                        backups.append(metadata)
                        
                except Exception:
                    continue
        
        # Sort by backup time, newest first
        backups.sort(key=lambda x: x['backup_time'], reverse=True)
        return backups
    
    def cleanup_old_backups(self):
        """Remove old backups to maintain storage limits"""
        try:
            backups = self.list_backups()
            
            if len(backups) > self.max_backups:
                # Remove oldest backups
                backups_to_remove = backups[self.max_backups:]
                
                for backup in backups_to_remove:
                    backup_name = backup['backup_name']
                    
                    # Remove backup file
                    backup_file = f"{backup_name}.gz" if backup.get('compressed') else f"{backup_name}.db"
                    backup_path = os.path.join(self.backup_dir, backup_file)
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    
                    # Remove metadata file
                    metadata_path = os.path.join(self.backup_dir, f"{backup_name}.json")
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                
                log_security_event('BACKUP_CLEANUP', None, 'system', 
                                 f"Cleaned up {len(backups_to_remove)} old backups")
                
        except Exception as e:
            log_security_event('BACKUP_CLEANUP_FAILED', None, 'system', f"Cleanup failed: {str(e)}")
    
    def verify_backup_integrity(self, backup_path):
        """Verify backup file integrity"""
        try:
            if backup_path.endswith('.gz'):
                # Test gzip file integrity
                with gzip.open(backup_path, 'rb') as gz_file:
                    # Try to read the file
                    gz_file.read(1024)
            else:
                # Test SQLite database integrity
                conn = sqlite3.connect(backup_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()
                
                if result[0] != 'ok':
                    return False, f"Database integrity check failed: {result[0]}"
            
            return True, "Backup integrity verified"
            
        except Exception as e:
            return False, f"Integrity check failed: {str(e)}"

class AutoBackupScheduler:
    """Automated backup scheduling system"""
    
    def __init__(self, backup_manager):
        self.backup_manager = backup_manager
        self.running = False
        self.thread = None
    
    def start_scheduler(self, interval_hours=24):
        """Start automated backup scheduling"""
        if self.running:
            return
        
        self.running = True
        self.interval_hours = interval_hours
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        log_security_event('AUTO_BACKUP_STARTED', None, 'system', 
                         f"Automated backup started (every {interval_hours} hours)")
    
    def stop_scheduler(self):
        """Stop automated backup scheduling"""
        self.running = False
        if self.thread:
            self.thread.join()
        
        log_security_event('AUTO_BACKUP_STOPPED', None, 'system', "Automated backup stopped")
    
    def _run_scheduler(self):
        """Background scheduler loop"""
        while self.running:
            try:
                # Create backup
                success, result = self.backup_manager.create_full_backup(compress=True)
                
                if success:
                    log_security_event('AUTO_BACKUP_SUCCESS', None, 'system', 
                                     f"Automated backup completed: {result}")
                else:
                    log_security_event('AUTO_BACKUP_FAILED', None, 'system', 
                                     f"Automated backup failed: {result}")
                
                # Wait for next backup
                time.sleep(self.interval_hours * 3600)
                
            except Exception as e:
                log_security_event('AUTO_BACKUP_ERROR', None, 'system', 
                                 f"Automated backup error: {str(e)}")
                time.sleep(3600)  # Wait 1 hour before retry

# Global backup manager instance
backup_manager = BackupManager()
auto_scheduler = AutoBackupScheduler(backup_manager)

# Start automated backups (daily)
auto_scheduler.start_scheduler(interval_hours=24)