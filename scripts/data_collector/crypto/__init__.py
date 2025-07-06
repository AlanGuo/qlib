# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Crypto data collection module for Qlib.

This module provides a comprehensive cryptocurrency data collection system
that supports multiple exchanges, timeframes, and crypto-specific data fields.
"""

import sys
from pathlib import Path

# Setup path for imports - works from project root or crypto directory
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR))
sys.path.insert(0, str(CUR_DIR.parent.parent))

# Import with error handling
__all__ = []

try:
    from .collector import CryptoCollector
    __all__.append("CryptoCollector")
except ImportError:
    try:
        from collector import CryptoCollector
        __all__.append("CryptoCollector")
    except ImportError:
        pass

try:
    from .exchange_adapters import ExchangeAdapter
    __all__.append("ExchangeAdapter")
except ImportError:
    try:
        from exchange_adapters import ExchangeAdapter
        __all__.append("ExchangeAdapter")
    except ImportError:
        pass

try:
    from .universe_manager import UniverseManager
    __all__.append("UniverseManager")
except ImportError:
    try:
        from universe_manager import UniverseManager
        __all__.append("UniverseManager")
    except ImportError:
        pass

try:
    from .data_validator import CryptoDataValidator
    __all__.append("CryptoDataValidator")
except ImportError:
    try:
        from data_validator import CryptoDataValidator
        __all__.append("CryptoDataValidator")
    except ImportError:
        pass

try:
    from .storage_manager import CryptoStorageManager
    __all__.append("CryptoStorageManager")
except ImportError:
    try:
        from storage_manager import CryptoStorageManager
        __all__.append("CryptoStorageManager")
    except ImportError:
        pass

try:
    from .qlib_data_generator import QlibDataGenerator
    __all__.append("QlibDataGenerator")
except ImportError:
    try:
        from qlib_data_generator import QlibDataGenerator
        __all__.append("QlibDataGenerator")
    except ImportError:
        pass

# Version information
__version__ = "1.0.0"
__author__ = "Microsoft Corporation"
__license__ = "MIT"