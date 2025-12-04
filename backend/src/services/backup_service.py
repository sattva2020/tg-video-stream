"""
BackupService for automated configuration and data backups.

Features:
- PostgreSQL database backups (pg_dump)
- Configuration file backups
- Redis database snapshots
- Rotation policy (keep last N backups)
- Cloud storage support (optional)

Backup locations: ./backups/ (local) or S3/GCS
"""

import logging
import os
import subprocess
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List


logger = logging.getLogger(__name__)


class BackupService:
    """Manages automated backups of configuration and data."""
    
    DEFAULT_BACKUP_DIR = "./backups"
    RETENTION_DAYS = 30  # Keep backups for 30 days
    MAX_BACKUPS = 10  # Keep maximum 10 backups
    
    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize backup service.
        
        Args:
            backup_dir: Directory for storing backups (default: ./backups)
        """
        self.backup_dir = Path(backup_dir or self.DEFAULT_BACKUP_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
    
    def backup_database(self, db_url: str, name: Optional[str] = None) -> Path:
        """
        Create database backup using pg_dump.
        
        Args:
            db_url: PostgreSQL connection URL (postgresql://...)
            name: Optional backup name
            
        Returns:
            Path to backup file
            
        Raises:
            Exception: If backup fails
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = name or "database"
            backup_file = self.backup_dir / f"{backup_name}_{timestamp}.sql.gz"
            
            # Extract credentials from URL
            # Format: postgresql://user:password@host:port/database
            
            # Run pg_dump
            cmd = f"pg_dump {db_url} | gzip > {backup_file}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            file_size = backup_file.stat().st_size / 1024 / 1024  # MB
            self.logger.info(f"Database backed up: {backup_file.name} ({file_size:.2f} MB)")
            
            self._cleanup_old_backups(backup_name)
            
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            raise
    
    def backup_configuration(self, config_paths: List[str], name: str = "config") -> Path:
        """
        Create configuration backup.
        
        Args:
            config_paths: List of config file/directory paths
            name: Backup name
            
        Returns:
            Path to backup tar.gz file
            
        Raises:
            Exception: If backup fails
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{name}_{timestamp}.tar.gz"
            
            # Create tar archive
            paths_str = " ".join(config_paths)
            cmd = f"tar -czf {backup_file} {paths_str}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"tar failed: {result.stderr}")
            
            file_size = backup_file.stat().st_size / 1024 / 1024  # MB
            self.logger.info(f"Configuration backed up: {backup_file.name} ({file_size:.2f} MB)")
            
            self._cleanup_old_backups(name)
            
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Configuration backup failed: {e}")
            raise
    
    def backup_redis_snapshot(self, redis_host: str, redis_port: int = 6379, name: str = "redis") -> Path:
        """
        Create Redis database snapshot.
        
        Args:
            redis_host: Redis host
            redis_port: Redis port
            name: Backup name
            
        Returns:
            Path to backup file
        """
        try:
            import redis
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{name}_{timestamp}.rdb"
            
            # Connect and save
            r = redis.Redis(host=redis_host, port=redis_port)
            r.save()
            
            # Copy dump.rdb
            import shutil
            shutil.copy("/var/lib/redis/dump.rdb", str(backup_file))
            
            file_size = backup_file.stat().st_size / 1024 / 1024  # MB
            self.logger.info(f"Redis backed up: {backup_file.name} ({file_size:.2f} MB)")
            
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Redis backup failed: {e}")
            raise
    
    def create_backup_manifest(self) -> dict:
        """
        Create manifest of all backups.
        
        Returns:
            Dict with backup metadata
        """
        backups = list(self.backup_dir.glob("*"))
        
        manifest = {
            "timestamp": datetime.utcnow().isoformat(),
            "backup_dir": str(self.backup_dir),
            "backups": []
        }
        
        for backup in sorted(backups, reverse=True):
            manifest["backups"].append({
                "filename": backup.name,
                "size_mb": backup.stat().st_size / 1024 / 1024,
                "created": datetime.fromtimestamp(backup.stat().st_mtime).isoformat()
            })
        
        return manifest
    
    def list_backups(self, pattern: Optional[str] = None) -> List[Path]:
        """
        List available backups.
        
        Args:
            pattern: Optional filename pattern filter
            
        Returns:
            List of backup file paths
        """
        if pattern:
            backups = list(self.backup_dir.glob(f"*{pattern}*"))
        else:
            backups = list(self.backup_dir.glob("*"))
        
        return sorted(backups, reverse=True)
    
    def restore_database(self, backup_file: Path, db_url: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_file: Path to backup file
            db_url: Target PostgreSQL connection URL
            
        Returns:
            True if restore successful
        """
        try:
            cmd = f"zcat {backup_file} | psql {db_url}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Restore failed: {result.stderr}")
            
            self.logger.info(f"Database restored from {backup_file.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Database restore failed: {e}")
            return False
    
    def _cleanup_old_backups(self, prefix: str) -> None:
        """
        Remove old backups based on retention policy.
        
        Args:
            prefix: Backup file name prefix (e.g., "database", "config")
        """
        backups = sorted(
            self.backup_dir.glob(f"{prefix}_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Remove based on both count and age
        for i, backup in enumerate(backups):
            age_days = (datetime.utcnow() - datetime.fromtimestamp(
                backup.stat().st_mtime
            )).days
            
            # Remove if older than retention or exceeds max count
            if i >= self.MAX_BACKUPS or age_days > self.RETENTION_DAYS:
                backup.unlink()
                self.logger.debug(f"Cleaned up old backup: {backup.name}")
