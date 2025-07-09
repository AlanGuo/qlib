# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Timeframe Manager for Cryptocurrency Data Collection.

This module provides simple timeframe management functionality following
the existing Qlib project patterns used in other data collectors.
"""

from typing import Dict, List, Optional, Set
import logging

from config.timeframes import (
    TIMEFRAME_MAPPING,
    EXCHANGE_TIMEFRAME_MAPPING,
    SUPPORTED_TIMEFRAMES,
    TIMEFRAME_PRIORITIES,
    validate_timeframe,
    get_exchange_timeframe,
    get_supported_timeframes_for_exchange,
    get_timeframe_seconds,
    sort_timeframes_by_priority
)

logger = logging.getLogger(__name__)


class TimeframeManager:
    """
    Simple timeframe management for cryptocurrency data collection.
    
    This class provides core timeframe handling functionality similar to
    other data collectors in the Qlib project.
    """
    
    def __init__(self):
        """Initialize the timeframe manager."""
        self._validated_cache: Set[str] = set()
        
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
        if timeframe in self._validated_cache:
            return True
            
        is_valid = validate_timeframe(timeframe)
        if is_valid:
            self._validated_cache.add(timeframe)
        return is_valid
    
    def validate_timeframes(self, timeframes: List[str]) -> List[str]:
        """
        Validate a list of timeframes and return only valid ones.
        
        Parameters
        ----------
        timeframes : List[str]
            List of timeframes to validate
            
        Returns
        -------
        List[str]
            List of valid timeframes
        """
        valid_timeframes = []
        for timeframe in timeframes:
            if self.validate_timeframe(timeframe):
                valid_timeframes.append(timeframe)
            else:
                logger.warning(f"Timeframe '{timeframe}' is not supported")
        return valid_timeframes
    
    def get_exchange_timeframe(self, exchange: str, timeframe: str) -> Optional[str]:
        """
        Convert standard timeframe to exchange-specific format.
        
        Parameters
        ----------
        exchange : str
            Exchange identifier (binance or okx)
        timeframe : str
            Standard timeframe
            
        Returns
        -------
        Optional[str]
            Exchange-specific timeframe or None if not supported
        """
        if not self.validate_timeframe(timeframe):
            return None
            
        return get_exchange_timeframe(exchange, timeframe)
    
    def get_supported_timeframes_for_exchange(self, exchange: str) -> List[str]:
        """
        Get supported timeframes for an exchange.
        
        Parameters
        ----------
        exchange : str
            Exchange identifier
            
        Returns
        -------
        List[str]
            List of supported timeframes
        """
        return get_supported_timeframes_for_exchange(exchange)
    
    def get_common_timeframes(self, exchanges: List[str]) -> List[str]:
        """
        Get timeframes supported by all specified exchanges.
        
        Parameters
        ----------
        exchanges : List[str]
            List of exchange identifiers
            
        Returns
        -------
        List[str]
            List of common timeframes sorted by priority
        """
        if not exchanges:
            return []
        
        # Get intersection of supported timeframes
        common = set(self.get_supported_timeframes_for_exchange(exchanges[0]))
        for exchange in exchanges[1:]:
            exchange_timeframes = set(self.get_supported_timeframes_for_exchange(exchange))
            common = common.intersection(exchange_timeframes)
        
        # Sort by priority
        return sort_timeframes_by_priority(list(common))
    
    def get_timeframes_by_category(self, category: str) -> List[str]:
        """
        Get timeframes by category.
        
        Parameters
        ----------
        category : str
            Category name (minute, hour, daily, weekly, all, common)
            
        Returns
        -------
        List[str]
            List of timeframes in the category
        """
        return SUPPORTED_TIMEFRAMES.get(category, [])
    
    def sort_timeframes_by_priority(self, timeframes: List[str]) -> List[str]:
        """
        Sort timeframes by collection priority.
        
        Parameters
        ----------
        timeframes : List[str]
            List of timeframes to sort
            
        Returns
        -------
        List[str]
            Sorted timeframes (highest priority first)
        """
        return sort_timeframes_by_priority(timeframes)
    
    def get_timeframe_info(self, timeframe: str) -> Dict[str, any]:
        """
        Get basic information about a timeframe.
        
        Parameters
        ----------
        timeframe : str
            Timeframe string
            
        Returns
        -------
        Dict[str, any]
            Basic timeframe information
        """
        if not self.validate_timeframe(timeframe):
            return {}
            
        return {
            'timeframe': timeframe,
            'seconds': get_timeframe_seconds(timeframe),
            'priority': TIMEFRAME_PRIORITIES.get(timeframe, 0),
            'is_valid': True
        }


# Global instance
timeframe_manager = TimeframeManager()