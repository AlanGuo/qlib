# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
State storage interfaces and implementations for incremental updates.

This module provides interfaces and implementations for persisting and
retrieving update state information.
"""

import json
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
import os
import shutil
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from .update_state import GlobalUpdateState


class StateStorageError(Exception):
    """Base exception for state storage errors."""
    pass


class StateStorage(ABC):
    """Abstract base class for state storage."""
    
    @abstractmethod
    def save_state(self, state: GlobalUpdateState) -> None:
        """Save the global update state."""
        pass
    
    @abstractmethod
    def load_state(self) -> Optional[GlobalUpdateState]:
        """Load the global update state."""
        pass
    
    @abstractmethod
    def backup_state(self, backup_id: Optional[str] = None) -> str:
        """Create a backup of the current state."""
        pass
    
    @abstractmethod
    def restore_state(self, backup_id: str) -> GlobalUpdateState:
        """Restore state from a backup."""
        pass
    
    @abstractmethod
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        pass
    
    @abstractmethod
    def delete_backup(self, backup_id: str) -> None:
        """Delete a backup."""
        pass


class FileStateStorage(StateStorage):
    """File-based state storage implementation."""
    
    def __init__(self, 
                 state_file: str = "update_state.json",
                 backup_dir: str = "backups",
                 max_backups: int = 10,
                 auto_backup: bool = True):
        """
        Initialize file state storage.
        
        Args:
            state_file: Path to the main state file
            backup_dir: Directory for backup files
            max_backups: Maximum number of backups to keep
            auto_backup: Whether to automatically create backups
        """
        self.state_file = Path(state_file)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        self.auto_backup = auto_backup
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        
        # Create directories if they don't exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, state: GlobalUpdateState) -> None:
        """Save the global update state."""
        with self._lock:
            try:
                # Create backup if auto_backup is enabled
                if self.auto_backup and self.state_file.exists():
                    self._create_auto_backup()
                
                # Update timestamp
                state.update_timestamp()
                
                # Write to temporary file first (atomic write)
                temp_file = self.state_file.with_suffix('.tmp')
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
                
                # Atomic rename
                temp_file.replace(self.state_file)
                
                self.logger.debug(f"State saved to {self.state_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to save state: {str(e)}")
                raise StateStorageError(f"Failed to save state: {str(e)}")
    
    def load_state(self) -> Optional[GlobalUpdateState]:
        """Load the global update state."""
        with self._lock:
            try:
                if not self.state_file.exists():
                    self.logger.info("State file does not exist, returning None")
                    return None
                
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                state = GlobalUpdateState.from_dict(data)
                self.logger.debug(f"State loaded from {self.state_file}")
                return state
                
            except Exception as e:
                self.logger.error(f"Failed to load state: {str(e)}")
                # Try to restore from latest backup
                backups = self.list_backups()
                if backups:
                    self.logger.info("Attempting to restore from latest backup")
                    try:
                        return self.restore_state(backups[0]['id'])
                    except Exception as restore_error:
                        self.logger.error(f"Failed to restore from backup: {str(restore_error)}")
                
                raise StateStorageError(f"Failed to load state: {str(e)}")
    
    def backup_state(self, backup_id: Optional[str] = None) -> str:
        """Create a backup of the current state."""
        with self._lock:
            try:
                if not self.state_file.exists():
                    raise StateStorageError("No state file to backup")
                
                if backup_id is None:
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    backup_id = f"backup_{timestamp}"
                
                backup_file = self.backup_dir / f"{backup_id}.json"
                
                # Copy current state file to backup
                shutil.copy2(self.state_file, backup_file)
                
                # Clean up old backups
                self._cleanup_old_backups()
                
                self.logger.info(f"State backed up to {backup_file}")
                return backup_id
                
            except Exception as e:
                self.logger.error(f"Failed to create backup: {str(e)}")
                raise StateStorageError(f"Failed to create backup: {str(e)}")
    
    def restore_state(self, backup_id: str) -> GlobalUpdateState:
        """Restore state from a backup."""
        with self._lock:
            try:
                backup_file = self.backup_dir / f"{backup_id}.json"
                
                if not backup_file.exists():
                    raise StateStorageError(f"Backup {backup_id} not found")
                
                # Load backup data
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                state = GlobalUpdateState.from_dict(data)
                
                # Save as current state
                self.save_state(state)
                
                self.logger.info(f"State restored from backup {backup_id}")
                return state
                
            except Exception as e:
                self.logger.error(f"Failed to restore state: {str(e)}")
                raise StateStorageError(f"Failed to restore state: {str(e)}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        try:
            backups = []
            
            for backup_file in self.backup_dir.glob("*.json"):
                stat = backup_file.stat()
                backups.append({
                    'id': backup_file.stem,
                    'file': str(backup_file),
                    'created_at': datetime.fromtimestamp(stat.st_ctime, timezone.utc),
                    'size': stat.st_size
                })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {str(e)}")
            return []
    
    def delete_backup(self, backup_id: str) -> None:
        """Delete a backup."""
        try:
            backup_file = self.backup_dir / f"{backup_id}.json"
            
            if backup_file.exists():
                backup_file.unlink()
                self.logger.info(f"Backup {backup_id} deleted")
            else:
                raise StateStorageError(f"Backup {backup_id} not found")
                
        except Exception as e:
            self.logger.error(f"Failed to delete backup: {str(e)}")
            raise StateStorageError(f"Failed to delete backup: {str(e)}")
    
    def _create_auto_backup(self) -> None:
        """Create an automatic backup."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_id = f"auto_{timestamp}"
            self.backup_state(backup_id)
        except Exception as e:
            self.logger.warning(f"Failed to create auto backup: {str(e)}")
    
    def _cleanup_old_backups(self) -> None:
        """Clean up old backups to maintain max_backups limit."""
        try:
            backups = self.list_backups()
            
            # Keep only max_backups
            if len(backups) > self.max_backups:
                for backup in backups[self.max_backups:]:
                    try:
                        self.delete_backup(backup['id'])
                    except Exception as e:
                        self.logger.warning(f"Failed to delete old backup {backup['id']}: {str(e)}")
                        
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups: {str(e)}")
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get information about the state storage."""
        info = {
            'state_file': str(self.state_file),
            'backup_dir': str(self.backup_dir),
            'max_backups': self.max_backups,
            'auto_backup': self.auto_backup,
            'state_file_exists': self.state_file.exists(),
            'backup_count': len(self.list_backups())
        }
        
        if self.state_file.exists():
            stat = self.state_file.stat()
            info.update({
                'state_file_size': stat.st_size,
                'state_file_modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            })
        
        return info


class MemoryStateStorage(StateStorage):
    """In-memory state storage for testing."""
    
    def __init__(self):
        """Initialize memory state storage."""
        self._state: Optional[GlobalUpdateState] = None
        self._backups: Dict[str, GlobalUpdateState] = {}
        self.logger = logging.getLogger(__name__)
    
    def save_state(self, state: GlobalUpdateState) -> None:
        """Save the global update state."""
        state.update_timestamp()
        # Deep copy to avoid reference issues
        self._state = GlobalUpdateState.from_dict(state.to_dict())
        self.logger.debug("State saved to memory")
    
    def load_state(self) -> Optional[GlobalUpdateState]:
        """Load the global update state."""
        if self._state is None:
            return None
        # Deep copy to avoid reference issues
        return GlobalUpdateState.from_dict(self._state.to_dict())
    
    def backup_state(self, backup_id: Optional[str] = None) -> str:
        """Create a backup of the current state."""
        if self._state is None:
            raise StateStorageError("No state to backup")
        
        if backup_id is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_id = f"backup_{timestamp}"
        
        # Deep copy to avoid reference issues
        self._backups[backup_id] = GlobalUpdateState.from_dict(self._state.to_dict())
        self.logger.debug(f"State backed up with ID {backup_id}")
        return backup_id
    
    def restore_state(self, backup_id: str) -> GlobalUpdateState:
        """Restore state from a backup."""
        if backup_id not in self._backups:
            raise StateStorageError(f"Backup {backup_id} not found")
        
        # Deep copy to avoid reference issues
        state = GlobalUpdateState.from_dict(self._backups[backup_id].to_dict())
        self.save_state(state)
        self.logger.debug(f"State restored from backup {backup_id}")
        return state
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        for backup_id, state in self._backups.items():
            backups.append({
                'id': backup_id,
                'created_at': state.created_at,
                'size': len(json.dumps(state.to_dict()))
            })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups
    
    def delete_backup(self, backup_id: str) -> None:
        """Delete a backup."""
        if backup_id not in self._backups:
            raise StateStorageError(f"Backup {backup_id} not found")
        
        del self._backups[backup_id]
        self.logger.debug(f"Backup {backup_id} deleted")
