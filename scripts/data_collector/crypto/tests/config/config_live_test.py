#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Configuration for live incremental update tests.

This module provides configuration settings specifically for live testing
of the crypto data collector incremental update functionality.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import timedelta

@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    http_proxy: str = "http://127.0.0.1:10808"
    https_proxy: str = "http://127.0.0.1:10808"
    all_proxy: str = "socks5://127.0.0.1:10808"
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert to environment variable dictionary."""
        return {
            'http_proxy': self.http_proxy,
            'https_proxy': self.https_proxy,
            'all_proxy': self.all_proxy,
            'HTTP_PROXY': self.http_proxy,
            'HTTPS_PROXY': self.https_proxy,
            'ALL_PROXY': self.all_proxy
        }

@dataclass
class LiveTestConfig:
    """Configuration for live testing."""
    # Test parameters
    test_exchange: str = "binance"
    test_symbol: str = "BTCUSDT"
    test_timeframe: str = "1h"
    test_limit: int = 100
    
    # Test timeouts
    network_timeout: int = 30
    api_timeout: int = 60
    test_timeout: int = 300
    
    # Test data parameters
    lookback_hours: int = 24
    incremental_delay_seconds: int = 5
    
    # Validation parameters
    min_data_points: int = 10
    max_price_deviation: float = 0.1  # 10% price deviation threshold
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: int = 2
    
    # Proxy configuration
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    
    # Test exchanges to validate
    supported_exchanges: List[str] = field(default_factory=lambda: ["binance", "okx"])
    
    # Test symbols for different exchanges
    test_symbols: Dict[str, List[str]] = field(default_factory=lambda: {
        "binance": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
        "okx": ["BTC-USDT", "ETH-USDT", "ADA-USDT"]
    })
    
    # Test timeframes
    test_timeframes: List[str] = field(default_factory=lambda: ["1h", "4h", "1d"])
    
    def get_test_cases(self) -> List[Dict[str, str]]:
        """Get all test case combinations."""
        test_cases = []
        
        for exchange in self.supported_exchanges:
            symbols = self.test_symbols.get(exchange, [self.test_symbol])
            for symbol in symbols[:2]:  # Limit to 2 symbols per exchange
                for timeframe in self.test_timeframes[:2]:  # Limit to 2 timeframes
                    test_cases.append({
                        'exchange': exchange,
                        'symbol': symbol,
                        'timeframe': timeframe
                    })
        
        return test_cases

# Global configuration instance
LIVE_TEST_CONFIG = LiveTestConfig()

def setup_test_environment():
    """Set up the test environment with proper configuration."""
    # Set proxy environment variables
    for key, value in LIVE_TEST_CONFIG.proxy.to_env_dict().items():
        os.environ[key] = value
    
    # Set test-specific environment variables
    os.environ['CRYPTO_TEST_MODE'] = 'live'
    os.environ['CRYPTO_TEST_EXCHANGE'] = LIVE_TEST_CONFIG.test_exchange
    os.environ['CRYPTO_TEST_SYMBOL'] = LIVE_TEST_CONFIG.test_symbol
    os.environ['CRYPTO_TEST_TIMEFRAME'] = LIVE_TEST_CONFIG.test_timeframe
    
    return LIVE_TEST_CONFIG

def validate_test_environment() -> bool:
    """Validate that the test environment is properly configured."""
    required_vars = ['http_proxy', 'https_proxy']
    
    for var in required_vars:
        if var not in os.environ:
            print(f"Warning: {var} not set in environment")
            return False
    
    return True

# Test markers for pytest
PYTEST_MARKERS = {
    'live': 'Tests that require live exchange API connections',
    'slow': 'Tests that take a long time to execute',
    'incremental': 'Tests for incremental update functionality',
    'network': 'Tests that require network connectivity',
    'proxy': 'Tests that require proxy configuration'
}