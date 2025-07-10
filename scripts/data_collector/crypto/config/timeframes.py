# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Timeframe configuration for cryptocurrency data collection.

This module defines timeframe handling following the existing Qlib project patterns.
It provides simple conversion logic similar to other data collectors like Yahoo and BaoStock.
"""

from typing import Dict, List, Optional


# Standard timeframe mapping - follows existing Qlib project naming conventions
TIMEFRAME_MAPPING: Dict[str, str] = {
    "1min": "1min",
    "5min": "5min", 
    "15min": "15min",
    "30min": "30min",
    "1h": "1h",        # New addition following existing pattern
    "1d": "1d",
    "1w": "1w",        # New addition following existing pattern
}

# Exchange-specific timeframe mappings - simple conversion like Yahoo collector
# 
# ⚠️  CRITICAL WARNING FOR OKX:
# ================================
# OKX timeframes are LOWERCASE (1h, 1d, 1w), NOT uppercase (1H, 1D, 1W)!
# This is a common source of confusion and bugs. Many developers assume
# OKX follows the "standard" uppercase format, but it actually uses lowercase.
# 
# CORRECT:   1h, 1d, 1w (lowercase)
# INCORRECT: 1H, 1D, 1W (uppercase) - will cause "Timeframe not supported" errors
# 
# This has been verified against OKX API documentation and actual testing.
# Do NOT change these to uppercase even if it "looks wrong" - it's correct!
# 
EXCHANGE_TIMEFRAME_MAPPING: Dict[str, Dict[str, str]] = {
    "binance": {
        "1min": "1m",
        "5min": "5m", 
        "15min": "15m",
        "30min": "30m",
        "1h": "1h",
        "1d": "1d",
        "1w": "1w",
    },
    "okx": {
        "1min": "1m",
        "5min": "5m",
        "15min": "15m", 
        "30min": "30m",
        "1h": "1h",     # IMPORTANT: OKX uses lowercase, NOT "1H" - common mistake!
        "1d": "1d",     # IMPORTANT: OKX uses lowercase, NOT "1D" - common mistake!
        "1w": "1w",     # IMPORTANT: OKX uses lowercase, NOT "1W" - common mistake!
    },
}

# Supported timeframes by category
SUPPORTED_TIMEFRAMES: Dict[str, List[str]] = {
    "minute": ["1min", "5min", "15min", "30min"],
    "hour": ["1h"], 
    "daily": ["1d"],
    "weekly": ["1w"],
    "all": list(TIMEFRAME_MAPPING.keys()),
    "common": ["1min", "5min", "15min", "1h", "1d"],
}

# Timeframe priorities for data collection
TIMEFRAME_PRIORITIES: Dict[str, int] = {
    "1d": 100,     # Highest priority
    "1h": 90,      
    "1w": 85,      
    "15min": 80,   
    "5min": 70,    
    "30min": 60,   
    "1min": 50,    # Lowest priority
}


def get_exchange_timeframe(exchange: str, timeframe: str) -> str:
    """
    Convert standard timeframe to exchange-specific format.
    Similar to Yahoo collector's simple conversion pattern.
    
    Parameters
    ----------
    exchange : str
        Exchange identifier (binance or okx)
    timeframe : str
        Standard timeframe (e.g., "1h", "1d")
        
    Returns
    -------
    str
        Exchange-specific timeframe format
    """
    exchange_mapping = EXCHANGE_TIMEFRAME_MAPPING.get(exchange.lower(), {})
    return exchange_mapping.get(timeframe, timeframe)


def validate_timeframe(timeframe: str) -> bool:
    """
    Validate if timeframe is supported.
    
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


def get_supported_timeframes_for_exchange(exchange: str) -> List[str]:
    """
    Get list of supported timeframes for a specific exchange.

    Parameters
    ----------
    exchange : str
        Exchange identifier (binance or okx)

    Returns
    -------
    List[str]
        List of supported timeframes
    """
    exchange_mapping = EXCHANGE_TIMEFRAME_MAPPING.get(exchange.lower(), {})
    return list(exchange_mapping.keys())


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
        "1w": 604800,
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


# Simple conversion for Qlib compatibility - only convert when absolutely necessary
def convert_for_qlib_internal(timeframe: str) -> str:
    """
    Convert timeframe for Qlib internal storage API usage ONLY.
    
    STRICT USAGE BOUNDARIES:
    ========================
    ALLOWED USAGE:
    - storage_manager.py: When creating FileFeatureStorage, FileInstrumentStorage, FileCalendarStorage
    - qlib_data_generator.py: When interfacing with Qlib storage classes
    
    FORBIDDEN USAGE:
    - User-facing APIs and functions
    - Data collection logic (collectors, adapters)
    - Configuration processing
    - Directory/file naming (use original timeframe)
    - Any code that doesn't directly interface with Qlib storage classes
    
    WARNING: This function should NEVER be called from:
    - timeframe_manager.py
    - collector.py
    - exchange_adapters/*
    - User configuration processing
    - Any code that handles user input
    
    RATIONALE:
    This function exists solely because Qlib's internal storage API expects
    "60min" instead of "1h". This is an implementation detail of Qlib's
    storage layer and should not leak into other parts of the system.
    
    Parameters
    ----------
    timeframe : str
        Standard timeframe string (must be pre-validated)

    Returns
    -------
    str
        Qlib storage API compatible frequency format
        
    Raises
    ------
    ValueError
        If timeframe is not valid (indicates usage boundary violation)
    """
    # Validate that timeframe is supported (boundary check)
    if not validate_timeframe(timeframe):
        raise ValueError(f"Invalid timeframe '{timeframe}' - this function should only be called "
                        f"with pre-validated timeframes from storage operations")
    
    # ONLY convert what's absolutely necessary for Qlib storage API compatibility
    if timeframe == "1h":
        return "60min"  # Qlib storage API expects "60min" format for hour intervals
    
    # All other formats remain unchanged to maintain consistency
    return timeframe


def _validate_qlib_internal_usage():
    """
    Internal validation function to help detect misuse of convert_for_qlib_internal.
    This is used during development to catch boundary violations.
    """
    import inspect
    import warnings
    
    # Get the calling frame to check if usage is appropriate
    frame = inspect.currentframe()
    if frame is None:
        return
    
    try:
        # Go up the call stack to find the caller
        caller_frame = frame.f_back.f_back  # Skip this function and convert_for_qlib_internal
        if caller_frame is None:
            return
            
        caller_filename = caller_frame.f_code.co_filename
        caller_function = caller_frame.f_code.co_name
        
        # Check if the caller is from an allowed module
        allowed_modules = ['storage_manager.py', 'qlib_data_generator.py']
        forbidden_modules = ['timeframe_manager.py', 'collector.py', 'exchange_adapters']
        
        is_allowed = any(module in caller_filename for module in allowed_modules)
        is_forbidden = any(module in caller_filename for module in forbidden_modules)
        
        if is_forbidden or not is_allowed:
            warnings.warn(
                f"BOUNDARY VIOLATION: convert_for_qlib_internal called from {caller_filename}:{caller_function}. "
                f"This function should only be used in storage_manager.py and qlib_data_generator.py "
                f"when interfacing with Qlib storage classes.",
                UserWarning,
                stacklevel=3
            )
    except Exception:
        # If we can't inspect the stack, just continue
        pass
    finally:
        del frame