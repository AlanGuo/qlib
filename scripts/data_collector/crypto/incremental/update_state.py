# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Update state management for incremental data collection.

This module defines data structures for tracking the state of incremental
data collection across exchanges, symbols, and timeframes.
"""

from dataclasses import dataclass, field, asdict
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json


class UpdateStatus(Enum):
    """Update status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class SymbolUpdateState:
    """State for a single symbol's data collection."""
    
    symbol: str
    exchange: str
    timeframe: str
    last_update_time: Optional[datetime] = None
    last_data_timestamp: Optional[datetime] = None
    update_count: int = 0
    status: UpdateStatus = UpdateStatus.NOT_STARTED
    error_info: Optional[str] = None
    data_points_collected: int = 0
    last_successful_update: Optional[datetime] = None
    consecutive_failures: int = 0
    next_scheduled_update: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, UpdateStatus):
                data[key] = value.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymbolUpdateState':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        datetime_fields = [
            'last_update_time', 'last_data_timestamp', 
            'last_successful_update', 'next_scheduled_update'
        ]
        
        for field_name in datetime_fields:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        # Convert status string to enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = UpdateStatus(data['status'])
        
        return cls(**data)
    
    def mark_update_start(self):
        """Mark the start of an update."""
        self.status = UpdateStatus.IN_PROGRESS
        self.last_update_time = datetime.now(timezone.utc)
    
    def mark_update_success(self, data_timestamp: Optional[datetime] = None, 
                          data_points: int = 0):
        """Mark successful update."""
        now = datetime.now(timezone.utc)
        self.status = UpdateStatus.SUCCESS
        self.last_successful_update = now
        self.consecutive_failures = 0
        self.update_count += 1
        self.error_info = None
        
        if data_timestamp:
            self.last_data_timestamp = data_timestamp
        
        if data_points > 0:
            self.data_points_collected += data_points
    
    def mark_update_failure(self, error_info: str):
        """Mark failed update."""
        self.status = UpdateStatus.FAILED
        self.consecutive_failures += 1
        self.error_info = error_info
    
    def should_retry(self, max_consecutive_failures: int = 3) -> bool:
        """Check if update should be retried."""
        return (self.status == UpdateStatus.FAILED and 
                self.consecutive_failures < max_consecutive_failures)
    
    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if data is stale."""
        if not self.last_successful_update:
            return True
        
        age = datetime.now(timezone.utc) - self.last_successful_update
        return age.total_seconds() > (max_age_hours * 3600)


@dataclass
class ExchangeUpdateState:
    """State for an exchange's data collection."""
    
    exchange: str
    symbols: Dict[str, Dict[str, SymbolUpdateState]] = field(default_factory=dict)
    last_full_update: Optional[datetime] = None
    update_frequency_minutes: int = 60
    enabled: bool = True
    total_symbols: int = 0
    successful_symbols: int = 0
    failed_symbols: int = 0
    last_universe_update: Optional[datetime] = None
    
    def get_symbol_state(self, symbol: str, timeframe: str) -> SymbolUpdateState:
        """Get or create symbol state."""
        if symbol not in self.symbols:
            self.symbols[symbol] = {}
        
        if timeframe not in self.symbols[symbol]:
            self.symbols[symbol][timeframe] = SymbolUpdateState(
                symbol=symbol,
                exchange=self.exchange,
                timeframe=timeframe
            )
        
        return self.symbols[symbol][timeframe]
    
    def get_all_symbol_states(self) -> List[SymbolUpdateState]:
        """Get all symbol states."""
        states = []
        for symbol_dict in self.symbols.values():
            for state in symbol_dict.values():
                states.append(state)
        return states
    
    def get_stale_symbols(self, max_age_hours: int = 24) -> List[SymbolUpdateState]:
        """Get symbols with stale data."""
        return [state for state in self.get_all_symbol_states() 
                if state.is_stale(max_age_hours)]
    
    def get_failed_symbols(self) -> List[SymbolUpdateState]:
        """Get symbols with failed updates."""
        return [state for state in self.get_all_symbol_states() 
                if state.status == UpdateStatus.FAILED]
    
    def update_statistics(self):
        """Update exchange statistics."""
        all_states = self.get_all_symbol_states()
        self.total_symbols = len(all_states)
        self.successful_symbols = len([s for s in all_states 
                                     if s.status == UpdateStatus.SUCCESS])
        self.failed_symbols = len([s for s in all_states 
                                 if s.status == UpdateStatus.FAILED])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            'exchange': self.exchange,
            'last_full_update': self.last_full_update.isoformat() if self.last_full_update else None,
            'update_frequency_minutes': self.update_frequency_minutes,
            'enabled': self.enabled,
            'total_symbols': self.total_symbols,
            'successful_symbols': self.successful_symbols,
            'failed_symbols': self.failed_symbols,
            'last_universe_update': self.last_universe_update.isoformat() if self.last_universe_update else None,
            'symbols': {}
        }
        
        # Convert symbol states
        for symbol, timeframe_dict in self.symbols.items():
            data['symbols'][symbol] = {}
            for timeframe, state in timeframe_dict.items():
                data['symbols'][symbol][timeframe] = state.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExchangeUpdateState':
        """Create from dictionary."""
        # Convert datetime fields
        if data.get('last_full_update'):
            data['last_full_update'] = datetime.fromisoformat(data['last_full_update'])
        
        if data.get('last_universe_update'):
            data['last_universe_update'] = datetime.fromisoformat(data['last_universe_update'])
        
        # Convert symbol states
        symbols = {}
        if 'symbols' in data:
            for symbol, timeframe_dict in data['symbols'].items():
                symbols[symbol] = {}
                for timeframe, state_data in timeframe_dict.items():
                    symbols[symbol][timeframe] = SymbolUpdateState.from_dict(state_data)
        
        # Remove symbols from data and create instance
        symbols_data = data.pop('symbols', {})
        instance = cls(**data)
        instance.symbols = symbols
        
        return instance


@dataclass
class GlobalUpdateState:
    """Global state for all data collection."""
    
    exchanges: Dict[str, ExchangeUpdateState] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"
    total_updates: int = 0
    last_backup_time: Optional[datetime] = None
    
    def get_exchange_state(self, exchange: str) -> ExchangeUpdateState:
        """Get or create exchange state."""
        if exchange not in self.exchanges:
            self.exchanges[exchange] = ExchangeUpdateState(exchange=exchange)
        return self.exchanges[exchange]
    
    def update_timestamp(self):
        """Update the last updated timestamp."""
        self.updated_at = datetime.now(timezone.utc)
        self.total_updates += 1
    
    def get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        total_symbols = 0
        successful_symbols = 0
        failed_symbols = 0
        
        for exchange_state in self.exchanges.values():
            exchange_state.update_statistics()
            total_symbols += exchange_state.total_symbols
            successful_symbols += exchange_state.successful_symbols
            failed_symbols += exchange_state.failed_symbols
        
        return {
            'total_exchanges': len(self.exchanges),
            'enabled_exchanges': len([e for e in self.exchanges.values() if e.enabled]),
            'total_symbols': total_symbols,
            'successful_symbols': successful_symbols,
            'failed_symbols': failed_symbols,
            'success_rate': successful_symbols / total_symbols if total_symbols > 0 else 0,
            'total_updates': self.total_updates,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'exchanges': {name: state.to_dict() for name, state in self.exchanges.items()},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'version': self.version,
            'total_updates': self.total_updates,
            'last_backup_time': self.last_backup_time.isoformat() if self.last_backup_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalUpdateState':
        """Create from dictionary."""
        # Convert datetime fields
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        if data.get('last_backup_time'):
            data['last_backup_time'] = datetime.fromisoformat(data['last_backup_time'])
        
        # Convert exchange states
        exchanges = {}
        if 'exchanges' in data:
            for exchange_name, exchange_data in data['exchanges'].items():
                exchanges[exchange_name] = ExchangeUpdateState.from_dict(exchange_data)
        
        # Remove exchanges from data and create instance
        exchanges_data = data.pop('exchanges', {})
        instance = cls(**data)
        instance.exchanges = exchanges
        
        return instance
