# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Incremental update module for cryptocurrency data collection.

This module provides comprehensive incremental update functionality including:
- State management and persistence
- Update strategies and planning
- Conflict resolution
- Progress tracking and recovery

Main Components:
- IncrementalUpdateManager: Main interface for incremental updates
- UpdateState classes: Data structures for tracking update state
- StateStorage: Persistence layer for update state
- UpdateStrategy: Strategies for determining when to update
- ConflictResolver: Handling data conflicts and overlaps
"""

from .manager import IncrementalUpdateManager, IncrementalUpdateError
from .update_state import (
    GlobalUpdateState,
    ExchangeUpdateState, 
    SymbolUpdateState,
    UpdateStatus
)
from .state_storage import (
    StateStorage,
    FileStateStorage,
    MemoryStateStorage,
    StateStorageError
)
from .update_strategy import (
    UpdateStrategy,
    TimeBasedStrategy,
    DataBasedStrategy,
    HybridStrategy,
    PriorityUpdatePlanner,
    UpdateDecision
)
from .conflict_resolver import (
    ConflictResolver,
    DefaultConflictResolver,
    ConflictDetector,
    ConflictResolutionStrategy,
    DataQualityMetrics,
    resolve_simple_overlap
)

__all__ = [
    # Main manager
    'IncrementalUpdateManager',
    'IncrementalUpdateError',
    
    # State management
    'GlobalUpdateState',
    'ExchangeUpdateState',
    'SymbolUpdateState',
    'UpdateStatus',
    
    # Storage
    'StateStorage',
    'FileStateStorage', 
    'MemoryStateStorage',
    'StateStorageError',
    
    # Update strategies
    'UpdateStrategy',
    'TimeBasedStrategy',
    'DataBasedStrategy',
    'HybridStrategy',
    'PriorityUpdatePlanner',
    'UpdateDecision',
    
    # Conflict resolution
    'ConflictResolver',
    'DefaultConflictResolver',
    'ConflictDetector',
    'ConflictResolutionStrategy',
    'DataQualityMetrics',
    'resolve_simple_overlap'
]


# Version information
__version__ = "1.0.0"
__author__ = "Qlib Crypto Data Collection Team"
__description__ = "Incremental update system for cryptocurrency data collection"


def create_default_manager(config, **kwargs):
    """
    Create a default incremental update manager with sensible defaults.
    
    Args:
        config: CryptoDataConfig instance
        **kwargs: Additional arguments for IncrementalUpdateManager
        
    Returns:
        IncrementalUpdateManager instance
    """
    # Import here to avoid circular imports
    from ..simple_error_log_collector import SimpleErrorLogCollector
    
    # Create default error log collector if not provided
    if 'error_log_collector' not in kwargs:
        incremental_config = config.incremental
        kwargs['error_log_collector'] = SimpleErrorLogCollector(
            max_retries=getattr(incremental_config, 'max_retries', 3),
            retry_delay=getattr(incremental_config, 'retry_delay', 1.0),
            enable_smart_logging=getattr(incremental_config, 'enable_smart_logging', True),
            error_cache_ttl=getattr(incremental_config, 'error_cache_ttl', 24 * 3600)
        )
    
    return IncrementalUpdateManager(config, **kwargs)


def create_file_storage(data_dir: str, **kwargs):
    """
    Create a file-based state storage.
    
    Args:
        data_dir: Base directory for data storage
        **kwargs: Additional arguments for FileStateStorage
        
    Returns:
        FileStateStorage instance
    """
    from pathlib import Path
    
    state_dir = Path(data_dir) / "incremental_state"
    return FileStateStorage(
        state_file=str(state_dir / "update_state.json"),
        backup_dir=str(state_dir / "backups"),
        **kwargs
    )


def create_time_based_strategy(update_intervals: dict = None, **kwargs):
    """
    Create a time-based update strategy with default intervals.
    
    Args:
        update_intervals: Dictionary mapping timeframes to update intervals in minutes
        **kwargs: Additional arguments for TimeBasedStrategy
        
    Returns:
        TimeBasedStrategy instance
    """
    if update_intervals is None:
        update_intervals = {
            '1m': 5,     # Update every 5 minutes
            '5m': 15,    # Update every 15 minutes  
            '15m': 30,   # Update every 30 minutes
            '30m': 60,   # Update every hour
            '1h': 120,   # Update every 2 hours
            '4h': 480,   # Update every 8 hours
            '1d': 1440,  # Update every day
            '1w': 10080  # Update every week
        }
    
    return TimeBasedStrategy(update_intervals=update_intervals, **kwargs)


def create_hybrid_strategy(time_weight: float = 0.7, data_weight: float = 0.3, **kwargs):
    """
    Create a hybrid update strategy combining time and data-based approaches.
    
    Args:
        time_weight: Weight for time-based decisions
        data_weight: Weight for data-based decisions
        **kwargs: Additional arguments for strategy components
        
    Returns:
        HybridStrategy instance
    """
    time_strategy = create_time_based_strategy(**kwargs)
    data_strategy = DataBasedStrategy(**kwargs)
    
    return HybridStrategy(
        time_strategy=time_strategy,
        data_strategy=data_strategy,
        time_weight=time_weight,
        data_weight=data_weight
    )


# Configuration helpers
DEFAULT_INCREMENTAL_CONFIG = {
    'max_concurrent_updates': 10,
    'max_backups': 10,
    'auto_backup': True,
    'max_age_hours': 24,
    'max_consecutive_failures': 3,
    'conflict_resolution': 'keep_latest',
    'update_intervals': {
        '1m': 5,
        '5m': 15,
        '15m': 30,
        '30m': 60,
        '1h': 120,
        '4h': 480,
        '1d': 1440,
        '1w': 10080
    }
}


def get_default_config():
    """Get default incremental update configuration."""
    return DEFAULT_INCREMENTAL_CONFIG.copy()


def validate_config(config: dict) -> bool:
    """
    Validate incremental update configuration.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    required_keys = ['max_concurrent_updates', 'update_intervals']
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    
    # Validate update intervals
    intervals = config['update_intervals']
    if not isinstance(intervals, dict):
        raise ValueError("update_intervals must be a dictionary")
    
    for timeframe, interval in intervals.items():
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError(f"Invalid update interval for {timeframe}: {interval}")
    
    # Validate conflict resolution strategy
    if 'conflict_resolution' in config:
        valid_strategies = [s.value for s in ConflictResolutionStrategy]
        if config['conflict_resolution'] not in valid_strategies:
            raise ValueError(f"Invalid conflict resolution strategy: {config['conflict_resolution']}")
    
    return True
