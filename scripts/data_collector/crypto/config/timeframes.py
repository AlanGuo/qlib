# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Timeframe configuration for cryptocurrency data collection.

This module defines the mapping between qlib-compatible timeframe names and 
exchange-specific timeframe formats. Only supports Binance and OKX exchanges.
"""

from typing import Dict, List


# Standard timeframe mapping (qlib compatible)
TIMEFRAME_MAPPING: Dict[str, str] = {
    # Minute timeframes
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    
    # Hour timeframes
    "1h": "1h",
    
    # Day/Week timeframes
    "1d": "1d",
    "1w": "1w",
    
    # Legacy support (deprecated)
    "day": "1d",
    "week": "1w",
}

# Exchange-specific timeframe mappings (qlib compatible)
EXCHANGE_TIMEFRAME_MAPPING: Dict[str, Dict[str, str]] = {
    "binance": {
        # Convert qlib format to Binance API format
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "1h": "1h",
        "1d": "1d",
        "1w": "1w",
        # Legacy support
        "day": "1d",
        "week": "1w",
    },
    "okx": {
        # Convert qlib format to OKX API format
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "1h": "1h",  # OKX uses lowercase 'h' for hours
        "1d": "1D",
        "1w": "1W",
        # Legacy support
        "day": "1D",
        "week": "1W",
    },
}

# Supported timeframes by category (qlib compatible)
SUPPORTED_TIMEFRAMES: Dict[str, List[str]] = {
    "minute": ["1min", "5min", "15min", "30min"],
    "hour": ["1h"],
    "daily": ["1d"],
    "weekly": ["1w"],
    "all": list(TIMEFRAME_MAPPING.keys()),
    "common": ["1min", "5min", "15min", "1h", "1d"],
    "trading": ["1min", "5min", "15min", "30min", "1h"],
    "analysis": ["1h", "1d", "1w"],
    "high_freq": ["1min", "5min"],
    "intraday": ["5min", "15min", "30min", "1h"],
    "long_term": ["1d", "1w"],
}

# Timeframe priorities for data collection (higher number = higher priority)
TIMEFRAME_PRIORITIES: Dict[str, int] = {
    "1d": 100,     # Highest priority - daily data
    "1h": 90,      # High priority - hourly data
    "1w": 85,      # Medium-high priority - weekly data
    "15min": 80,   # Medium-high priority
    "5min": 70,    # Medium priority
    "30min": 60,   # Medium-low priority
    "1min": 50,    # Lower priority
    "day": 100,    # Legacy support - same as 1d
}

def get_exchange_timeframe(exchange: str, standard_timeframe: str) -> str:
    """
    Convert standard qlib timeframe to exchange-specific format.
    
    Parameters
    ----------
    exchange : str
        Exchange identifier (binance or okx)
    standard_timeframe : str
        Standard qlib timeframe (e.g., "1h", "day")
        
    Returns
    -------
    str
        Exchange-specific timeframe format
    """
    exchange_mapping = EXCHANGE_TIMEFRAME_MAPPING.get(exchange.lower(), {})
    return exchange_mapping.get(standard_timeframe, standard_timeframe)

def get_standard_timeframe(exchange: str, exchange_timeframe: str) -> str:
    """
    Convert exchange-specific timeframe to standard qlib format.
    
    Parameters
    ----------
    exchange : str
        Exchange identifier (binance or okx)
    exchange_timeframe : str
        Exchange-specific timeframe
        
    Returns
    -------
    str
        Standard qlib timeframe format
    """
    exchange_mapping = EXCHANGE_TIMEFRAME_MAPPING.get(exchange.lower(), {})
    # Reverse lookup
    for standard, exchange_specific in exchange_mapping.items():
        if exchange_specific == exchange_timeframe:
            return standard
    return exchange_timeframe

def validate_timeframe(timeframe: str) -> bool:
    """
    Validate if timeframe is supported (accepts both standard and qlib formats).
    
    Parameters
    ----------
    timeframe : str
        Timeframe to validate
        
    Returns
    -------
    bool
        True if timeframe is supported
    """
    # Check if it's in standard mapping
    if timeframe in TIMEFRAME_MAPPING:
        return True
    
    # Check if it's a qlib format (reverse mapping)
    qlib_formats = set(convert_to_qlib_freq(tf) for tf in TIMEFRAME_MAPPING.keys())
    return timeframe in qlib_formats

def get_timeframe_seconds(timeframe: str) -> int:
    """
    Get timeframe duration in seconds.

    Parameters
    ----------
    timeframe : str
        Timeframe string

    Returns
    -------
    int
        Duration in seconds
    """
    timeframe_seconds = {
        "1min": 60,
        "5min": 300,
        "15min": 900,
        "30min": 1800,
        "1h": 3600,
        "1d": 86400,
        "1w": 604800,     # 7 * 86400
        "day": 86400,     # Legacy support
    }
    return timeframe_seconds.get(timeframe, 0)

def sort_timeframes_by_priority(timeframes: List[str]) -> List[str]:
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
    return sorted(timeframes, key=lambda tf: TIMEFRAME_PRIORITIES.get(tf, 0), reverse=True)

def get_supported_timeframes_for_exchange(exchange_id: str) -> List[str]:
    """
    Get list of supported timeframes for a specific exchange.

    Parameters
    ----------
    exchange_id : str
        Exchange identifier (binance or okx)

    Returns
    -------
    List[str]
        List of supported timeframes
    """
    exchange_mapping = EXCHANGE_TIMEFRAME_MAPPING.get(exchange_id.lower(), {})
    return list(exchange_mapping.keys())

def is_high_frequency_timeframe(timeframe: str) -> bool:
    """
    Check if a timeframe is considered high frequency (<= 5 minutes).

    Parameters
    ----------
    timeframe : str
        Timeframe string

    Returns
    -------
    bool
        True if high frequency timeframe
    """
    seconds = get_timeframe_seconds(timeframe)
    return seconds > 0 and seconds <= 300  # <= 5 minutes

def get_timeframe_category(timeframe: str) -> str:
    """
    Get the category of a timeframe.

    Parameters
    ----------
    timeframe : str
        Timeframe string

    Returns
    -------
    str
        Category name ('minute', 'hour', 'daily')
    """
    for category, timeframes in SUPPORTED_TIMEFRAMES.items():
        if category != "all" and timeframe in timeframes:
            return category
    return "unknown"

def get_optimal_batch_size(timeframe: str, max_candles: int = 1000) -> int:
    """
    Get optimal batch size for data collection based on timeframe.

    Parameters
    ----------
    timeframe : str
        Timeframe string
    max_candles : int, default 1000
        Maximum number of candles per request

    Returns
    -------
    int
        Optimal batch size
    """
    seconds = get_timeframe_seconds(timeframe)

    if seconds == 0:
        return max_candles

    # Adjust batch size based on timeframe
    if seconds <= 60:  # 1min
        return min(max_candles, 500)
    elif seconds <= 900:  # <= 15min
        return min(max_candles, 1000)
    elif seconds <= 3600:  # <= 1h
        return min(max_candles, 1500)
    elif seconds <= 86400:  # <= 1d
        return min(max_candles, 2000)
    else:  # 1w
        return min(max_candles, 3000)

def estimate_data_size(timeframe: str, days: int) -> int:
    """
    Estimate number of data points for a given timeframe and period.

    Parameters
    ----------
    timeframe : str
        Timeframe string
    days : int
        Number of days

    Returns
    -------
    int
        Estimated number of data points
    """
    seconds = get_timeframe_seconds(timeframe)
    if seconds == 0:
        return 0

    total_seconds = days * 86400
    return total_seconds // seconds

def get_timeframe_display_name(timeframe: str) -> str:
    """
    Get human-readable display name for timeframe.

    Parameters
    ----------
    timeframe : str
        Timeframe string

    Returns
    -------
    str
        Display name
    """
    display_names = {
        "1min": "1 Minute",
        "5min": "5 Minutes",
        "15min": "15 Minutes",
        "30min": "30 Minutes",
        "1h": "1 Hour",
        "1d": "1 Day",
        "1w": "1 Week",
        "day": "1 Day",  # Legacy support
    }
    return display_names.get(timeframe, timeframe)

def is_qlib_compatible_timeframe(timeframe: str) -> bool:
    """
    Check if a timeframe is compatible with qlib format.

    Parameters
    ----------
    timeframe : str
        Timeframe string

    Returns
    -------
    bool
        True if compatible with qlib
    """
    return timeframe in TIMEFRAME_MAPPING

def convert_to_qlib_freq(timeframe: str) -> str:
    """
    Convert timeframe to qlib frequency format.
    
    NOTE: This is the SINGLE authoritative function for qlib format conversion.
    All other modules should import and use this function.

    Parameters
    ----------
    timeframe : str
        Standard timeframe string

    Returns
    -------
    str
        Qlib frequency format (for qlib storage backend)
    """
    # For qlib compatibility, we map to qlib's internal frequency format
    # Based on qlib error: "freq should be like (n)month/mon, (n)week/w, (n)day/d, (n)minute/min"
    qlib_mapping = {
        "1min": "1min",     # qlib supports this format
        "5min": "5min",     # qlib supports this format  
        "15min": "15min",   # qlib supports this format
        "30min": "30min",   # qlib supports this format
        "1h": "60min",      # Convert to minutes for qlib compatibility
        "1d": "1d",         # qlib prefers this format for daily
        "1w": "1w",         # qlib prefers this format for weekly
        "day": "1d",        # Convert legacy to qlib format
        "week": "1w",       # Convert legacy to qlib format
    }
    return qlib_mapping.get(timeframe, timeframe)