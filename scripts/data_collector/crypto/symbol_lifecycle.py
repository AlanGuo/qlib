# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Symbol lifecycle management for cryptocurrency data collection.

This module provides comprehensive symbol lifecycle tracking including:
- Symbol status monitoring (active, suspended, delisted)
- Delisting detection and handling
- Symbol availability tracking
- Historical status records
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
from threading import Lock
import time

try:
    import ccxt
except ImportError:
    logging.error("ccxt library is required. Install with: pip install ccxt")
    raise

logger = logging.getLogger(__name__)


class SymbolStatus(Enum):
    """Symbol lifecycle status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
    UNKNOWN = "unknown"


@dataclass
class SymbolStatusRecord:
    """Record of symbol status at a specific time."""
    symbol: str
    status: SymbolStatus
    timestamp: datetime
    reason: Optional[str] = None
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymbolStatusRecord':
        """Create from dictionary."""
        data = data.copy()
        data['status'] = SymbolStatus(data['status'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class SymbolAvailabilityWindow:
    """Represents a time window when a symbol was available for trading."""
    symbol: str
    start_time: datetime
    end_time: Optional[datetime] = None
    exchange: Optional[str] = None
    market_type: Optional[str] = None
    reason_ended: Optional[str] = None

    def is_active(self) -> bool:
        """Check if symbol is currently active."""
        return self.end_time is None

    def contains_time(self, timestamp: datetime) -> bool:
        """Check if timestamp falls within this availability window."""
        if timestamp < self.start_time:
            return False
        if self.end_time is not None and timestamp > self.end_time:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymbolAvailabilityWindow':
        """Create from dictionary."""
        data = data.copy()
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)


class SymbolLifecycleManager:
    """
    Manages symbol lifecycle tracking and delisting detection.
    
    Features:
    - Real-time symbol status monitoring
    - Delisting detection through multiple methods
    - Symbol availability window tracking
    - Persistent storage of lifecycle data
    - Multi-exchange support
    """
    
    def __init__(self, 
                 storage_dir: str = "./symbol_lifecycle",
                 cache_ttl: int = 3600,
                 enable_persistence: bool = True):
        """
        Initialize symbol lifecycle manager.
        
        Parameters
        ----------
        storage_dir : str
            Directory to store lifecycle data
        cache_ttl : int
            Cache TTL in seconds
        enable_persistence : bool
            Enable persistent storage
        """
        self.storage_dir = Path(storage_dir)
        self.cache_ttl = cache_ttl
        self.enable_persistence = enable_persistence
        
        # Thread-safe data structures
        self._lock = Lock()
        self._status_cache: Dict[str, SymbolStatusRecord] = {}
        self._availability_windows: Dict[str, List[SymbolAvailabilityWindow]] = {}
        self._status_history: Dict[str, List[SymbolStatusRecord]] = {}
        
        # Initialize storage
        if self.enable_persistence:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_from_storage()
    
    def get_symbol_status(self, 
                         symbol: str, 
                         exchange: str,
                         market_type: str = "spot",
                         force_refresh: bool = False) -> SymbolStatusRecord:
        """
        Get current status of a symbol.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        market_type : str
            Market type
        force_refresh : bool
            Force refresh from exchange
            
        Returns
        -------
        SymbolStatusRecord
            Current symbol status
        """
        cache_key = f"{exchange}_{market_type}_{symbol}"
        
        with self._lock:
            # Check cache first
            if not force_refresh and cache_key in self._status_cache:
                cached_record = self._status_cache[cache_key]
                if (datetime.now() - cached_record.timestamp).total_seconds() < self.cache_ttl:
                    return cached_record
            
            # Fetch fresh status from exchange
            try:
                status_record = self._fetch_symbol_status(symbol, exchange, market_type)
                
                # Update cache
                self._status_cache[cache_key] = status_record
                
                # Update history
                if cache_key not in self._status_history:
                    self._status_history[cache_key] = []
                self._status_history[cache_key].append(status_record)
                
                # Update availability windows
                self._update_availability_windows(status_record)
                
                # Persist changes
                if self.enable_persistence:
                    self._save_to_storage()
                
                return status_record
                
            except Exception as e:
                logger.error(f"Failed to fetch symbol status for {symbol}: {e}")
                
                # Return last known status or unknown
                if cache_key in self._status_cache:
                    return self._status_cache[cache_key]
                
                return SymbolStatusRecord(
                    symbol=symbol,
                    status=SymbolStatus.UNKNOWN,
                    timestamp=datetime.now(),
                    reason=f"Failed to fetch status: {e}",
                    exchange=exchange,
                    market_type=market_type
                )
    
    def _fetch_symbol_status(self, 
                           symbol: str, 
                           exchange: str, 
                           market_type: str) -> SymbolStatusRecord:
        """
        Fetch symbol status from exchange.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        market_type : str
            Market type
            
        Returns
        -------
        SymbolStatusRecord
            Symbol status record
        """
        # Initialize exchange adapter
        exchange_class = getattr(ccxt, exchange.lower())
        exchange_instance = exchange_class()
        
        try:
            # Load markets
            markets = exchange_instance.load_markets()
            
            if symbol not in markets:
                return SymbolStatusRecord(
                    symbol=symbol,
                    status=SymbolStatus.DELISTED,
                    timestamp=datetime.now(),
                    reason="Symbol not found in markets",
                    exchange=exchange,
                    market_type=market_type
                )
            
            market = markets[symbol]
            
            # Check if market is active
            if not market.get('active', True):
                return SymbolStatusRecord(
                    symbol=symbol,
                    status=SymbolStatus.SUSPENDED,
                    timestamp=datetime.now(),
                    reason="Market marked as inactive",
                    exchange=exchange,
                    market_type=market_type,
                    metadata={"market_info": market}
                )
            
            # Additional checks for specific market types
            if market_type == "spot" and not market.get('spot', False):
                return SymbolStatusRecord(
                    symbol=symbol,
                    status=SymbolStatus.DELISTED,
                    timestamp=datetime.now(),
                    reason=f"Not available for {market_type} trading",
                    exchange=exchange,
                    market_type=market_type
                )
            
            # Try to fetch recent ticker to confirm symbol is actively trading
            try:
                ticker = exchange_instance.fetch_ticker(symbol)
                if ticker and ticker.get('timestamp'):
                    # Check if ticker is recent (within last 24 hours)
                    ticker_time = datetime.fromtimestamp(ticker['timestamp'] / 1000)
                    if (datetime.now() - ticker_time).total_seconds() > 86400:  # 24 hours
                        return SymbolStatusRecord(
                            symbol=symbol,
                            status=SymbolStatus.SUSPENDED,
                            timestamp=datetime.now(),
                            reason="No recent trading activity",
                            exchange=exchange,
                            market_type=market_type,
                            metadata={"last_ticker_time": ticker_time.isoformat()}
                        )
            except Exception as e:
                logger.warning(f"Could not fetch ticker for {symbol}: {e}")
                # Continue with ACTIVE status if market info looks good
            
            # Symbol appears to be active
            return SymbolStatusRecord(
                symbol=symbol,
                status=SymbolStatus.ACTIVE,
                timestamp=datetime.now(),
                reason="Symbol is active and trading",
                exchange=exchange,
                market_type=market_type,
                metadata={"market_info": market}
            )
            
        except Exception as e:
            logger.error(f"Error fetching symbol status for {symbol}: {e}")
            raise
    
    def _update_availability_windows(self, status_record: SymbolStatusRecord):
        """Update availability windows based on status change."""
        key = f"{status_record.exchange}_{status_record.market_type}_{status_record.symbol}"
        
        if key not in self._availability_windows:
            self._availability_windows[key] = []
        
        windows = self._availability_windows[key]
        
        # If symbol became active, start a new window
        if status_record.status == SymbolStatus.ACTIVE:
            # Check if there's already an active window
            active_window = None
            for window in windows:
                if window.is_active():
                    active_window = window
                    break
            
            if not active_window:
                # Create new availability window
                new_window = SymbolAvailabilityWindow(
                    symbol=status_record.symbol,
                    start_time=status_record.timestamp,
                    exchange=status_record.exchange,
                    market_type=status_record.market_type
                )
                windows.append(new_window)
        
        # If symbol became suspended or delisted, end the current window
        elif status_record.status in [SymbolStatus.SUSPENDED, SymbolStatus.DELISTED]:
            # Find and close the active window
            for window in windows:
                if window.is_active():
                    window.end_time = status_record.timestamp
                    window.reason_ended = status_record.reason
                    break
    
    def get_symbol_availability_windows(self, 
                                      symbol: str, 
                                      exchange: str,
                                      market_type: str = "spot") -> List[SymbolAvailabilityWindow]:
        """
        Get availability windows for a symbol.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        market_type : str
            Market type
            
        Returns
        -------
        List[SymbolAvailabilityWindow]
            List of availability windows
        """
        key = f"{exchange}_{market_type}_{symbol}"
        with self._lock:
            return self._availability_windows.get(key, []).copy()
    
    def is_symbol_available_at_time(self, 
                                  symbol: str, 
                                  exchange: str,
                                  timestamp: datetime,
                                  market_type: str = "spot") -> bool:
        """
        Check if symbol was available at a specific time.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        timestamp : datetime
            Time to check
        market_type : str
            Market type
            
        Returns
        -------
        bool
            True if symbol was available
        """
        windows = self.get_symbol_availability_windows(symbol, exchange, market_type)
        
        for window in windows:
            if window.contains_time(timestamp):
                return True
        
        return False
    
    def get_collection_time_windows(self, 
                                  symbol: str, 
                                  exchange: str,
                                  start_time: datetime, 
                                  end_time: datetime,
                                  market_type: str = "spot") -> List[Tuple[datetime, datetime]]:
        """
        Get time windows when symbol was available within a date range.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        start_time : datetime
            Start time
        end_time : datetime
            End time
        market_type : str
            Market type
            
        Returns
        -------
        List[Tuple[datetime, datetime]]
            List of (start, end) time windows when symbol was available
        """
        windows = self.get_symbol_availability_windows(symbol, exchange, market_type)
        collection_windows = []
        
        for window in windows:
            # Calculate intersection with requested time range
            window_start = max(window.start_time, start_time)
            window_end = min(window.end_time or datetime.now(), end_time)
            
            if window_start < window_end:
                collection_windows.append((window_start, window_end))
        
        return collection_windows
    
    def detect_delisting_event(self, 
                             symbol: str, 
                             exchange: str,
                             market_type: str = "spot") -> Optional[datetime]:
        """
        Detect when a symbol was delisted.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        market_type : str
            Market type
            
        Returns
        -------
        Optional[datetime]
            Delisting timestamp if found, None otherwise
        """
        key = f"{exchange}_{market_type}_{symbol}"
        
        with self._lock:
            if key in self._status_history:
                for record in reversed(self._status_history[key]):
                    if record.status == SymbolStatus.DELISTED:
                        return record.timestamp
        
        return None
    
    def get_symbol_status_history(self, 
                                symbol: str, 
                                exchange: str,
                                market_type: str = "spot") -> List[SymbolStatusRecord]:
        """
        Get status history for a symbol.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        market_type : str
            Market type
            
        Returns
        -------
        List[SymbolStatusRecord]
            List of status records
        """
        key = f"{exchange}_{market_type}_{symbol}"
        with self._lock:
            return self._status_history.get(key, []).copy()
    
    def mark_symbol_delisted(self, 
                           symbol: str, 
                           exchange: str,
                           delisting_time: datetime,
                           reason: str = "Manual delisting",
                           market_type: str = "spot"):
        """
        Manually mark a symbol as delisted.
        
        Parameters
        ----------
        symbol : str
            Trading symbol
        exchange : str
            Exchange name
        delisting_time : datetime
            Delisting timestamp
        reason : str
            Reason for delisting
        market_type : str
            Market type
        """
        record = SymbolStatusRecord(
            symbol=symbol,
            status=SymbolStatus.DELISTED,
            timestamp=delisting_time,
            reason=reason,
            exchange=exchange,
            market_type=market_type
        )
        
        key = f"{exchange}_{market_type}_{symbol}"
        
        with self._lock:
            # Update cache
            self._status_cache[key] = record
            
            # Update history
            if key not in self._status_history:
                self._status_history[key] = []
            self._status_history[key].append(record)
            
            # Update availability windows
            self._update_availability_windows(record)
            
            # Persist changes
            if self.enable_persistence:
                self._save_to_storage()
    
    def _save_to_storage(self):
        """Save lifecycle data to storage."""
        try:
            # Save status cache
            cache_file = self.storage_dir / "status_cache.json"
            cache_data = {k: v.to_dict() for k, v in self._status_cache.items()}
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            # Save status history
            history_file = self.storage_dir / "status_history.json"
            history_data = {k: [r.to_dict() for r in v] for k, v in self._status_history.items()}
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            # Save availability windows
            windows_file = self.storage_dir / "availability_windows.json"
            windows_data = {k: [w.to_dict() for w in v] for k, v in self._availability_windows.items()}
            with open(windows_file, 'w') as f:
                json.dump(windows_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save lifecycle data: {e}")
    
    def _load_from_storage(self):
        """Load lifecycle data from storage."""
        try:
            # Load status cache
            cache_file = self.storage_dir / "status_cache.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self._status_cache = {k: SymbolStatusRecord.from_dict(v) for k, v in cache_data.items()}
            
            # Load status history
            history_file = self.storage_dir / "status_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                    self._status_history = {k: [SymbolStatusRecord.from_dict(r) for r in v] for k, v in history_data.items()}
            
            # Load availability windows
            windows_file = self.storage_dir / "availability_windows.json"
            if windows_file.exists():
                with open(windows_file, 'r') as f:
                    windows_data = json.load(f)
                    self._availability_windows = {k: [SymbolAvailabilityWindow.from_dict(w) for w in v] for k, v in windows_data.items()}
            
        except Exception as e:
            logger.error(f"Failed to load lifecycle data: {e}")
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up old lifecycle data.
        
        Parameters
        ----------
        days_to_keep : int
            Number of days to keep data
        """
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        
        with self._lock:
            # Clean up status history
            for key in list(self._status_history.keys()):
                self._status_history[key] = [
                    record for record in self._status_history[key] 
                    if record.timestamp > cutoff_time
                ]
                
                # Remove empty entries
                if not self._status_history[key]:
                    del self._status_history[key]
            
            # Clean up cache for old entries
            for key in list(self._status_cache.keys()):
                if self._status_cache[key].timestamp < cutoff_time:
                    del self._status_cache[key]
            
            # Save changes
            if self.enable_persistence:
                self._save_to_storage()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get lifecycle manager statistics.
        
        Returns
        -------
        Dict[str, Any]
            Statistics dictionary
        """
        with self._lock:
            total_symbols = len(self._status_cache)
            active_symbols = sum(1 for r in self._status_cache.values() if r.status == SymbolStatus.ACTIVE)
            suspended_symbols = sum(1 for r in self._status_cache.values() if r.status == SymbolStatus.SUSPENDED)
            delisted_symbols = sum(1 for r in self._status_cache.values() if r.status == SymbolStatus.DELISTED)
            
            total_windows = sum(len(windows) for windows in self._availability_windows.values())
            active_windows = sum(1 for windows in self._availability_windows.values() 
                               for window in windows if window.is_active())
            
            return {
                "total_symbols": total_symbols,
                "active_symbols": active_symbols,
                "suspended_symbols": suspended_symbols,
                "delisted_symbols": delisted_symbols,
                "total_availability_windows": total_windows,
                "active_availability_windows": active_windows,
                "cache_size": len(self._status_cache),
                "history_entries": sum(len(history) for history in self._status_history.values())
            }