# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Timeframe Manager for Cryptocurrency Data Collection.

This module provides advanced timeframe management functionality including
validation, conversion, optimization, and exchange-specific handling.
"""

from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from config.timeframes import (
    TIMEFRAME_MAPPING,
    EXCHANGE_TIMEFRAME_MAPPING,
    SUPPORTED_TIMEFRAMES,
    TIMEFRAME_PRIORITIES,
    get_timeframe_seconds,
    get_supported_timeframes_for_exchange,
    is_high_frequency_timeframe,
    get_timeframe_category,
    get_optimal_batch_size,
    estimate_data_size,
    get_timeframe_display_name
)

logger = logging.getLogger(__name__)


@dataclass
class TimeframeInfo:
    """Information about a timeframe."""
    timeframe: str
    seconds: int
    category: str
    priority: int
    display_name: str
    is_high_freq: bool
    optimal_batch_size: int


class TimeframeManager:
    """
    Advanced timeframe management for cryptocurrency data collection.
    
    This class provides comprehensive timeframe handling including:
    - Validation and conversion
    - Exchange-specific mapping
    - Optimization recommendations
    - Data size estimation
    """
    
    def __init__(self):
        """Initialize the timeframe manager."""
        self._cache: Dict[str, TimeframeInfo] = {}
        self._exchange_cache: Dict[str, Set[str]] = {}
        
    def get_timeframe_info(self, timeframe: str) -> Optional[TimeframeInfo]:
        """
        Get comprehensive information about a timeframe.
        
        Parameters
        ----------
        timeframe : str
            Timeframe string
            
        Returns
        -------
        Optional[TimeframeInfo]
            Timeframe information or None if invalid
        """
        if timeframe in self._cache:
            return self._cache[timeframe]
            
        if timeframe not in TIMEFRAME_MAPPING:
            return None
            
        info = TimeframeInfo(
            timeframe=timeframe,
            seconds=get_timeframe_seconds(timeframe),
            category=get_timeframe_category(timeframe),
            priority=TIMEFRAME_PRIORITIES.get(timeframe, 0),
            display_name=get_timeframe_display_name(timeframe),
            is_high_freq=is_high_frequency_timeframe(timeframe),
            optimal_batch_size=get_optimal_batch_size(timeframe)
        )
        
        self._cache[timeframe] = info
        return info
    
    def validate_timeframe(self, timeframe: str) -> bool:
        """
        Validate if a timeframe is supported.
        
        Parameters
        ----------
        timeframe : str
            Timeframe to validate
            
        Returns
        -------
        bool
            True if timeframe is supported
        """
        return timeframe in TIMEFRAME_MAPPING
    
    def validate_timeframe_for_exchange(self, timeframe: str, exchange_id: str) -> bool:
        """
        Validate if a timeframe is supported by a specific exchange.
        
        Parameters
        ----------
        timeframe : str
            Timeframe to validate
        exchange_id : str
            Exchange identifier
            
        Returns
        -------
        bool
            True if timeframe is supported by the exchange
        """
        supported = self.get_supported_timeframes_for_exchange(exchange_id)
        return timeframe in supported
    
    def get_supported_timeframes_for_exchange(self, exchange_id: str) -> Set[str]:
        """
        Get supported timeframes for an exchange (cached).
        
        Parameters
        ----------
        exchange_id : str
            Exchange identifier
            
        Returns
        -------
        Set[str]
            Set of supported timeframes
        """
        if exchange_id not in self._exchange_cache:
            timeframes = get_supported_timeframes_for_exchange(exchange_id)
            self._exchange_cache[exchange_id] = set(timeframes)
        
        return self._exchange_cache[exchange_id]
    
    def convert_timeframe_for_exchange(self, timeframe: str, exchange_id: str) -> Optional[str]:
        """
        Convert standard timeframe to exchange-specific format.
        
        Parameters
        ----------
        timeframe : str
            Standard timeframe
        exchange_id : str
            Exchange identifier
            
        Returns
        -------
        Optional[str]
            Exchange-specific timeframe or None if not supported
        """
        exchange_mapping = EXCHANGE_TIMEFRAME_MAPPING.get(exchange_id.lower(), {})
        return exchange_mapping.get(timeframe)
    
    def get_compatible_timeframes(self, 
                                 exchanges: List[str], 
                                 categories: Optional[List[str]] = None) -> List[str]:
        """
        Get timeframes compatible with all specified exchanges.
        
        Parameters
        ----------
        exchanges : List[str]
            List of exchange identifiers
        categories : Optional[List[str]]
            Filter by timeframe categories
            
        Returns
        -------
        List[str]
            List of compatible timeframes
        """
        if not exchanges:
            return []
        
        # Get intersection of supported timeframes
        compatible = self.get_supported_timeframes_for_exchange(exchanges[0])
        for exchange_id in exchanges[1:]:
            exchange_timeframes = self.get_supported_timeframes_for_exchange(exchange_id)
            compatible = compatible.intersection(exchange_timeframes)
        
        # Filter by categories if specified
        if categories:
            category_timeframes = set()
            for category in categories:
                if category in SUPPORTED_TIMEFRAMES:
                    category_timeframes.update(SUPPORTED_TIMEFRAMES[category])
            compatible = compatible.intersection(category_timeframes)
        
        # Sort by priority
        return sorted(list(compatible), 
                     key=lambda tf: TIMEFRAME_PRIORITIES.get(tf, 0), 
                     reverse=True)
    
    def recommend_timeframes_for_strategy(self, 
                                        strategy_type: str,
                                        exchanges: List[str]) -> List[str]:
        """
        Recommend optimal timeframes for a trading strategy.
        
        Parameters
        ----------
        strategy_type : str
            Strategy type ('scalping', 'intraday', 'swing', 'position')
        exchanges : List[str]
            Target exchanges
            
        Returns
        -------
        List[str]
            Recommended timeframes
        """
        strategy_mappings = {
            'scalping': ['scalping', 'high_freq'],
            'intraday': ['intraday', 'trading'],
            'swing': ['trading', 'analysis'],
            'position': ['analysis', 'daily_plus'],
            'arbitrage': ['ultra_short', 'high_freq'],
            'market_making': ['ultra_short', 'minute'],
        }
        
        categories = strategy_mappings.get(strategy_type, ['common'])
        return self.get_compatible_timeframes(exchanges, categories)
    
    def estimate_collection_time(self, 
                               timeframes: List[str],
                               symbols: List[str],
                               days: int,
                               exchanges: List[str]) -> Dict[str, float]:
        """
        Estimate data collection time for given parameters.
        
        Parameters
        ----------
        timeframes : List[str]
            List of timeframes
        symbols : List[str]
            List of symbols
        days : int
            Number of days of historical data
        exchanges : List[str]
            List of exchanges
            
        Returns
        -------
        Dict[str, float]
            Estimation results (total_requests, estimated_minutes, etc.)
        """
        total_requests = 0
        total_data_points = 0
        
        for timeframe in timeframes:
            data_points_per_symbol = estimate_data_size(timeframe, days)
            batch_size = get_optimal_batch_size(timeframe)
            
            requests_per_symbol = max(1, data_points_per_symbol // batch_size)
            
            # Multiply by symbols and exchanges
            total_requests += requests_per_symbol * len(symbols) * len(exchanges)
            total_data_points += data_points_per_symbol * len(symbols) * len(exchanges)
        
        # Estimate time based on rate limits (conservative estimate)
        avg_rate_limit = 0.15  # seconds per request
        estimated_seconds = total_requests * avg_rate_limit
        estimated_minutes = estimated_seconds / 60
        
        return {
            'total_requests': total_requests,
            'total_data_points': total_data_points,
            'estimated_seconds': estimated_seconds,
            'estimated_minutes': estimated_minutes,
            'estimated_hours': estimated_minutes / 60,
        }
    
    def optimize_timeframe_collection_order(self, 
                                          timeframes: List[str],
                                          prioritize_high_freq: bool = False) -> List[str]:
        """
        Optimize the order of timeframe collection.
        
        Parameters
        ----------
        timeframes : List[str]
            List of timeframes to optimize
        prioritize_high_freq : bool, default False
            Whether to prioritize high frequency data
            
        Returns
        -------
        List[str]
            Optimized timeframe order
        """
        if prioritize_high_freq:
            # Sort by frequency (high freq first), then by priority
            return sorted(timeframes, 
                         key=lambda tf: (
                             -get_timeframe_seconds(tf),  # Negative for ascending order
                             -TIMEFRAME_PRIORITIES.get(tf, 0)
                         ))
        else:
            # Sort by priority (high priority first)
            return sorted(timeframes, 
                         key=lambda tf: TIMEFRAME_PRIORITIES.get(tf, 0), 
                         reverse=True)
    
    def get_timeframe_statistics(self) -> Dict[str, any]:
        """
        Get statistics about available timeframes.
        
        Returns
        -------
        Dict[str, any]
            Statistics about timeframes
        """
        all_timeframes = list(TIMEFRAME_MAPPING.keys())
        
        stats = {
            'total_timeframes': len(all_timeframes),
            'by_category': {},
            'by_exchange': {},
            'high_frequency_count': 0,
            'priority_distribution': {},
        }
        
        # Count by category
        for category, timeframes in SUPPORTED_TIMEFRAMES.items():
            if category != 'all':
                stats['by_category'][category] = len(timeframes)
        
        # Count by exchange
        for exchange_id in EXCHANGE_TIMEFRAME_MAPPING.keys():
            supported = self.get_supported_timeframes_for_exchange(exchange_id)
            stats['by_exchange'][exchange_id] = len(supported)
        
        # Count high frequency
        stats['high_frequency_count'] = sum(
            1 for tf in all_timeframes if is_high_frequency_timeframe(tf)
        )
        
        # Priority distribution
        for tf in all_timeframes:
            priority = TIMEFRAME_PRIORITIES.get(tf, 0)
            priority_range = f"{priority//10*10}-{priority//10*10+9}"
            stats['priority_distribution'][priority_range] = \
                stats['priority_distribution'].get(priority_range, 0) + 1
        
        return stats


# Global instance
timeframe_manager = TimeframeManager()
