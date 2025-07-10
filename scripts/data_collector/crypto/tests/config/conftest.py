# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Pytest configuration for crypto data collector tests.
"""

import sys
import os
import pytest
from pathlib import Path

# Add the crypto module directory to Python path for absolute imports
crypto_root = Path(__file__).parent.parent
if str(crypto_root) not in sys.path:
    sys.path.insert(0, str(crypto_root))

# Set environment variables for testing
os.environ["QLIB_TEST_MODE"] = "1"

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "live: mark test as requiring live exchange API calls"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "validation: mark test as data validation test"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers"""
    # Add markers to tests based on their names and modules
    for item in items:
        # Add live marker to live tests
        if "live" in item.module.__name__ or "live" in item.name:
            item.add_marker(pytest.mark.live)
        
        # Add slow marker to slow tests
        if "large_batch" in item.name or "integration" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Add validation marker to validation tests
        if "validation" in item.module.__name__ or "validate" in item.name:
            item.add_marker(pytest.mark.validation)

@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture"""
    return {
        "rate_limit_delay": 1.0,
        "max_retries": 3,
        "test_symbols": ["BTC/USDT", "ETH/USDT"],
        "test_timeframes": ["1h", "1d"],
        "test_exchanges": ["binance", "okx"]
    }
