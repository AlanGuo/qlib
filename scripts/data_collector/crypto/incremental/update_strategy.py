# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Update strategies for incremental data collection.

This module defines strategies for determining when and how to update
cryptocurrency data based on various criteria.
"""

from abc import ABC, abstractmethod
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import logging

from .update_state import SymbolUpdateState, UpdateStatus


@dataclass
class UpdateDecision:
    """Decision about whether to update a symbol."""
    
    should_update: bool
    reason: str
    priority: int = 0  # Higher priority = update first
    estimated_data_points: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class UpdateStrategy(ABC):
    """Abstract base class for update strategies."""
    
    def __init__(self, name: str):
        """Initialize update strategy."""
        self.name = name
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def should_update(self, symbol_state: SymbolUpdateState, 
                     current_time: Optional[datetime] = None) -> UpdateDecision:
        """Determine if a symbol should be updated."""
        pass
    
    @abstractmethod
    def get_update_timeframe(self, symbol_state: SymbolUpdateState,
                           current_time: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get the time range for data collection."""
        pass


class TimeBasedStrategy(UpdateStrategy):
    """Time-based update strategy."""
    
    def __init__(self, 
                 update_intervals: Dict[str, int],  # timeframe -> minutes
                 max_age_hours: int = 24,
                 force_update_after_failures: int = 3):
        """
        Initialize time-based strategy.
        
        Args:
            update_intervals: Update intervals in minutes for each timeframe
            max_age_hours: Maximum age before forcing update
            force_update_after_failures: Force update after this many failures
        """
        super().__init__("time_based")
        self.update_intervals = update_intervals
        self.max_age_hours = max_age_hours
        self.force_update_after_failures = force_update_after_failures
    
    def should_update(self, symbol_state: SymbolUpdateState, 
                     current_time: Optional[datetime] = None) -> UpdateDecision:
        """Determine if a symbol should be updated based on time."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Get update interval for this timeframe
        interval_minutes = self.update_intervals.get(symbol_state.timeframe, 60)
        interval = timedelta(minutes=interval_minutes)
        
        # Check if never updated
        if symbol_state.last_successful_update is None:
            return UpdateDecision(
                should_update=True,
                reason="Never updated",
                priority=100,
                estimated_data_points=self._estimate_data_points(symbol_state, current_time)
            )
        
        # Check if data is too old
        age = current_time - symbol_state.last_successful_update
        if age.total_seconds() > (self.max_age_hours * 3600):
            return UpdateDecision(
                should_update=True,
                reason=f"Data too old ({age.total_seconds() / 3600:.1f} hours)",
                priority=90,
                estimated_data_points=self._estimate_data_points(symbol_state, current_time)
            )
        
        # Check if enough time has passed since last update
        if age >= interval:
            return UpdateDecision(
                should_update=True,
                reason=f"Update interval reached ({age.total_seconds() / 60:.1f} minutes)",
                priority=50,
                estimated_data_points=self._estimate_data_points(symbol_state, current_time)
            )
        
        # Check if we should force update after failures
        if (symbol_state.consecutive_failures >= self.force_update_after_failures and
            age >= timedelta(minutes=30)):  # Wait at least 30 minutes between retries
            return UpdateDecision(
                should_update=True,
                reason=f"Force update after {symbol_state.consecutive_failures} failures",
                priority=80,
                estimated_data_points=self._estimate_data_points(symbol_state, current_time)
            )
        
        # No update needed
        next_update = symbol_state.last_successful_update + interval
        time_until_next = next_update - current_time
        return UpdateDecision(
            should_update=False,
            reason=f"Next update in {time_until_next.total_seconds() / 60:.1f} minutes"
        )
    
    def get_update_timeframe(self, symbol_state: SymbolUpdateState,
                           current_time: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get the time range for data collection."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Start from last data timestamp or a reasonable default
        if symbol_state.last_data_timestamp:
            start_time = symbol_state.last_data_timestamp
        else:
            # Default to 30 days ago for new symbols
            start_time = current_time - timedelta(days=30)
        
        # End at current time
        end_time = current_time
        
        return start_time, end_time
    
    def _estimate_data_points(self, symbol_state: SymbolUpdateState, 
                            current_time: datetime) -> int:
        """Estimate number of data points to collect."""
        start_time, end_time = self.get_update_timeframe(symbol_state, current_time)
        
        if not start_time or not end_time:
            return 0
        
        duration = end_time - start_time
        
        # Estimate based on timeframe
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440, '1w': 10080
        }
        
        minutes = timeframe_minutes.get(symbol_state.timeframe, 60)
        return int(duration.total_seconds() / (minutes * 60))


class DataBasedStrategy(UpdateStrategy):
    """Data-based update strategy that checks for new data availability."""
    
    def __init__(self, 
                 min_update_interval_minutes: int = 5,
                 check_remote_timestamp: bool = True):
        """
        Initialize data-based strategy.
        
        Args:
            min_update_interval_minutes: Minimum time between updates
            check_remote_timestamp: Whether to check remote data timestamps
        """
        super().__init__("data_based")
        self.min_update_interval = timedelta(minutes=min_update_interval_minutes)
        self.check_remote_timestamp = check_remote_timestamp
    
    def should_update(self, symbol_state: SymbolUpdateState, 
                     current_time: Optional[datetime] = None) -> UpdateDecision:
        """Determine if a symbol should be updated based on data availability."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Check minimum interval
        if (symbol_state.last_update_time and 
            current_time - symbol_state.last_update_time < self.min_update_interval):
            return UpdateDecision(
                should_update=False,
                reason="Minimum update interval not reached"
            )
        
        # Always update if never updated
        if symbol_state.last_data_timestamp is None:
            return UpdateDecision(
                should_update=True,
                reason="No data available",
                priority=100
            )
        
        # Check if we're in a failed state and should retry
        if symbol_state.status == UpdateStatus.FAILED:
            return UpdateDecision(
                should_update=True,
                reason="Retry after failure",
                priority=70
            )
        
        # For now, assume new data is available
        # In a real implementation, this would check with the exchange
        return UpdateDecision(
            should_update=True,
            reason="New data potentially available",
            priority=30
        )
    
    def get_update_timeframe(self, symbol_state: SymbolUpdateState,
                           current_time: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get the time range for data collection."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Start from last data timestamp
        if symbol_state.last_data_timestamp:
            start_time = symbol_state.last_data_timestamp
        else:
            # Default to 7 days ago for new symbols
            start_time = current_time - timedelta(days=7)
        
        end_time = current_time
        return start_time, end_time


class HybridStrategy(UpdateStrategy):
    """Hybrid strategy combining time-based and data-based approaches."""
    
    def __init__(self, 
                 time_strategy: TimeBasedStrategy,
                 data_strategy: DataBasedStrategy,
                 time_weight: float = 0.7,
                 data_weight: float = 0.3):
        """
        Initialize hybrid strategy.
        
        Args:
            time_strategy: Time-based strategy
            data_strategy: Data-based strategy
            time_weight: Weight for time-based decision
            data_weight: Weight for data-based decision
        """
        super().__init__("hybrid")
        self.time_strategy = time_strategy
        self.data_strategy = data_strategy
        self.time_weight = time_weight
        self.data_weight = data_weight
    
    def should_update(self, symbol_state: SymbolUpdateState, 
                     current_time: Optional[datetime] = None) -> UpdateDecision:
        """Determine if a symbol should be updated using hybrid approach."""
        time_decision = self.time_strategy.should_update(symbol_state, current_time)
        data_decision = self.data_strategy.should_update(symbol_state, current_time)
        
        # Combine decisions
        if time_decision.should_update and data_decision.should_update:
            # Both strategies agree - high priority
            return UpdateDecision(
                should_update=True,
                reason=f"Both strategies agree: {time_decision.reason} & {data_decision.reason}",
                priority=max(time_decision.priority, data_decision.priority) + 10,
                estimated_data_points=time_decision.estimated_data_points
            )
        elif time_decision.should_update:
            # Only time strategy says update
            weighted_priority = int(time_decision.priority * self.time_weight)
            return UpdateDecision(
                should_update=weighted_priority > 30,  # Threshold
                reason=f"Time-based: {time_decision.reason}",
                priority=weighted_priority,
                estimated_data_points=time_decision.estimated_data_points
            )
        elif data_decision.should_update:
            # Only data strategy says update
            weighted_priority = int(data_decision.priority * self.data_weight)
            return UpdateDecision(
                should_update=weighted_priority > 30,  # Threshold
                reason=f"Data-based: {data_decision.reason}",
                priority=weighted_priority,
                estimated_data_points=data_decision.estimated_data_points
            )
        else:
            # Neither strategy says update
            return UpdateDecision(
                should_update=False,
                reason="Neither strategy recommends update"
            )
    
    def get_update_timeframe(self, symbol_state: SymbolUpdateState,
                           current_time: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get the time range for data collection."""
        # Use time strategy's timeframe as it's usually more comprehensive
        return self.time_strategy.get_update_timeframe(symbol_state, current_time)


class PriorityUpdatePlanner:
    """Plans updates based on priority and resource constraints."""
    
    def __init__(self, max_concurrent_updates: int = 10):
        """
        Initialize update planner.
        
        Args:
            max_concurrent_updates: Maximum number of concurrent updates
        """
        self.max_concurrent_updates = max_concurrent_updates
        self.logger = logging.getLogger(__name__)
    
    def plan_updates(self, 
                    symbol_states: List[SymbolUpdateState],
                    strategy: UpdateStrategy,
                    current_time: Optional[datetime] = None) -> List[tuple[SymbolUpdateState, UpdateDecision]]:
        """
        Plan updates for a list of symbol states.
        
        Returns:
            List of (symbol_state, update_decision) tuples sorted by priority
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Get update decisions for all symbols
        update_plans = []
        for symbol_state in symbol_states:
            decision = strategy.should_update(symbol_state, current_time)
            if decision.should_update:
                update_plans.append((symbol_state, decision))
        
        # Sort by priority (highest first)
        update_plans.sort(key=lambda x: x[1].priority, reverse=True)
        
        # Limit to max concurrent updates
        if len(update_plans) > self.max_concurrent_updates:
            self.logger.info(f"Limiting updates to {self.max_concurrent_updates} out of {len(update_plans)} candidates")
            update_plans = update_plans[:self.max_concurrent_updates]
        
        return update_plans
    
    def get_update_statistics(self, 
                            symbol_states: List[SymbolUpdateState],
                            strategy: UpdateStrategy,
                            current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get statistics about pending updates."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        total_symbols = len(symbol_states)
        needs_update = 0
        high_priority = 0
        estimated_data_points = 0
        
        for symbol_state in symbol_states:
            decision = strategy.should_update(symbol_state, current_time)
            if decision.should_update:
                needs_update += 1
                estimated_data_points += decision.estimated_data_points
                if decision.priority >= 70:
                    high_priority += 1
        
        return {
            'total_symbols': total_symbols,
            'needs_update': needs_update,
            'high_priority_updates': high_priority,
            'estimated_data_points': estimated_data_points,
            'update_percentage': (needs_update / total_symbols * 100) if total_symbols > 0 else 0
        }
