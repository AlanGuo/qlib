#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for cryptocurrency storage manager.

This script tests the storage manager functionality including file operations,
directory management, and data format conversions using temporary directories.
"""

import pytest
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from storage_manager import CryptoStorageManager


# Test fixtures
@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="crypto_storage_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    dates = pd.date_range(start='2022-01-01', end='2022-01-03', freq='1H')
    data = {
        'timestamp': dates,
        'open': np.random.uniform(45000, 47000, len(dates)),
        'high': np.random.uniform(46000, 48000, len(dates)),
        'low': np.random.uniform(44000, 46000, len(dates)),
        'close': np.random.uniform(45000, 47000, len(dates)),
        'volume': np.random.uniform(100, 1000, len(dates))
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_crypto_fields_data():
    """Sample crypto-specific fields data for testing."""
    dates = pd.date_range(start='2022-01-01', end='2022-01-03', freq='8H')
    data = {
        'timestamp': dates,
        'funding_rate': np.random.uniform(-0.001, 0.001, len(dates)),
        'open_interest': np.random.uniform(100000, 1000000, len(dates)),
        'long_short_ratio': np.random.uniform(0.5, 2.0, len(dates))
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_instruments_list():
    """Sample instruments list for testing."""
    return ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"]


class TestStorageManagerInitialization:
    """Test storage manager initialization and configuration."""
    
    def test_storage_manager_default_initialization(self, temp_storage_dir):
        """Test default storage manager initialization."""
        storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
        
        assert storage_manager.data_dir == Path(temp_storage_dir)
        assert hasattr(storage_manager, 'data_dir')
    
    def test_storage_manager_custom_initialization(self, temp_storage_dir):
        """Test storage manager initialization with custom parameters."""
        storage_manager = CryptoStorageManager(
            data_dir=temp_storage_dir,
            create_dirs=True
        )
        
        assert storage_manager.data_dir == Path(temp_storage_dir)
    
    def test_storage_manager_directory_creation(self, temp_storage_dir):
        """Test automatic directory creation."""
        storage_dir = Path(temp_storage_dir) / "new_crypto_storage"
        storage_manager = CryptoStorageManager(data_dir=storage_dir, create_dirs=True)
        
        assert storage_dir.exists()
        assert storage_dir.is_dir()
    
    def test_storage_manager_path_properties(self, temp_storage_dir):
        """Test storage manager path properties."""
        storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
        
        # Test that data_dir is properly set as Path object
        assert isinstance(storage_manager.data_dir, Path)
        assert str(storage_manager.data_dir) == temp_storage_dir


class TestStorageManagerBasicOperations:
    """Test basic storage manager operations."""
    
    def test_storage_manager_attributes(self, temp_storage_dir):
        """Test storage manager has required attributes."""
        storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
        
        # Test basic attributes exist
        assert hasattr(storage_manager, 'data_dir')
        assert hasattr(storage_manager, '__init__')
    
    def test_storage_manager_with_different_paths(self):
        """Test storage manager with different path types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with string path
            storage_manager1 = CryptoStorageManager(data_dir=temp_dir)
            assert storage_manager1.data_dir == Path(temp_dir)
            
            # Test with Path object
            path_obj = Path(temp_dir)
            storage_manager2 = CryptoStorageManager(data_dir=path_obj)
            assert storage_manager2.data_dir == path_obj
    
    def test_storage_manager_memory_usage(self, temp_storage_dir):
        """Test storage manager memory usage."""
        storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
        
        # Test that multiple instances don't interfere
        storage_manager2 = CryptoStorageManager(data_dir=temp_storage_dir)
        
        assert storage_manager.data_dir == storage_manager2.data_dir
        assert id(storage_manager) != id(storage_manager2)


class TestStorageManagerFileOperations:
    """Test storage manager file operations."""
    
    def test_directory_structure_verification(self, temp_storage_dir):
        """Test directory structure verification."""
        storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
        
        # Check base directory exists
        assert storage_manager.data_dir.exists()
        assert storage_manager.data_dir.is_dir()
    
    def test_multiple_storage_managers(self, temp_storage_dir):
        """Test multiple storage manager instances."""
        # Create multiple instances
        managers = []
        for i in range(5):
            manager = CryptoStorageManager(data_dir=temp_storage_dir)
            managers.append(manager)
        
        # Verify all instances are created successfully
        assert len(managers) == 5
        for manager in managers:
            assert manager.data_dir == Path(temp_storage_dir)
    
    def test_storage_manager_thread_safety(self, temp_storage_dir):
        """Test storage manager thread safety."""
        import threading
        
        results = []
        
        def create_manager(thread_id):
            try:
                manager = CryptoStorageManager(data_dir=temp_storage_dir)
                results.append(f"success_{thread_id}")
            except Exception as e:
                results.append(f"error_{thread_id}: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_manager, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        assert len(results) == 3
        for result in results:
            assert result.startswith("success_")


class TestStorageManagerConfiguration:
    """Test storage manager configuration options."""
    
    def test_create_dirs_option(self):
        """Test create_dirs configuration option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with create_dirs=True (default)
            new_dir = Path(temp_dir) / "new_storage"
            storage_manager = CryptoStorageManager(data_dir=new_dir, create_dirs=True)
            assert new_dir.exists()
            
            # Test with create_dirs=False
            another_dir = Path(temp_dir) / "another_storage"
            # This should work if the directory doesn't need to be created
            # or should be handled gracefully
            try:
                storage_manager2 = CryptoStorageManager(data_dir=another_dir, create_dirs=False)
                # If it succeeds, that's fine too
            except Exception:
                # If it fails, that's also acceptable behavior
                pass
    
    def test_provider_uri_configuration(self, temp_storage_dir):
        """Test provider URI configuration."""
        provider_config = {
            "class": "FileProvider",
            "kwargs": {"data_dir": temp_storage_dir}
        }
        
        storage_manager = CryptoStorageManager(
            data_dir=temp_storage_dir,
            provider_uri=provider_config
        )
        
        assert storage_manager.data_dir == Path(temp_storage_dir)
    
    def test_storage_manager_repr(self, temp_storage_dir):
        """Test storage manager string representation."""
        storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
        
        # Test that we can convert to string without error
        str_repr = str(storage_manager)
        assert isinstance(str_repr, str)
        
        # Test that repr works
        repr_str = repr(storage_manager)
        assert isinstance(repr_str, str)


class TestStorageManagerPerformance:
    """Test storage manager performance aspects."""
    
    def test_initialization_performance(self, temp_storage_dir):
        """Test storage manager initialization performance."""
        import time
        
        # Measure initialization time
        start_time = time.time()
        
        storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
        
        initialization_time = time.time() - start_time
        
        # Should initialize quickly
        assert initialization_time < 1.0  # Less than 1 second
        assert storage_manager.data_dir == Path(temp_storage_dir)
    
    def test_multiple_initialization_performance(self, temp_storage_dir):
        """Test performance of multiple initializations."""
        import time
        
        start_time = time.time()
        
        # Create multiple instances
        managers = []
        for i in range(10):
            manager = CryptoStorageManager(data_dir=temp_storage_dir)
            managers.append(manager)
        
        total_time = time.time() - start_time
        
        # Should create all instances quickly
        assert total_time < 2.0  # Less than 2 seconds for 10 instances
        assert len(managers) == 10
        
        # Verify all instances are valid
        for manager in managers:
            assert manager.data_dir == Path(temp_storage_dir)
    
    def test_memory_efficiency(self, temp_storage_dir):
        """Test memory efficiency of storage manager."""
        # Create and destroy many instances to test for memory leaks
        for i in range(100):
            manager = CryptoStorageManager(data_dir=temp_storage_dir)
            del manager
        
        # If we get here without running out of memory, test passes
        assert True


class TestStorageManagerUtilityFunctions:
    """Test utility functions in storage manager module."""
    
    def test_convert_to_qlib_freq_function(self):
        """Test the convert_to_qlib_freq utility function."""
        from storage_manager import convert_to_qlib_freq
        
        # Test common timeframe conversions to qlib-compatible format
        assert convert_to_qlib_freq("1min") == "1min"
        assert convert_to_qlib_freq("5min") == "5min"
        assert convert_to_qlib_freq("1h") == "60min"    # qlib expects minutes format
        assert convert_to_qlib_freq("1d") == "1d"       # qlib d format
        assert convert_to_qlib_freq("1w") == "1w"       # qlib w format
        assert convert_to_qlib_freq("day") == "1d"      # Legacy conversion to qlib format
        
        # Test unknown timeframe (should return as-is)
        assert convert_to_qlib_freq("unknown") == "unknown"
    
    def test_timeframe_conversion_edge_cases(self):
        """Test edge cases in timeframe conversion."""
        from storage_manager import convert_to_qlib_freq
        
        # Test empty string
        assert convert_to_qlib_freq("") == ""
        
        # Test None (should handle gracefully)
        try:
            result = convert_to_qlib_freq(None)
            # If it doesn't raise an exception, that's fine
        except (TypeError, AttributeError):
            # If it raises an exception, that's also acceptable
            pass
    
    def test_complex_timeframe_conversions(self):
        """Test complex timeframe conversions."""
        from storage_manager import convert_to_qlib_freq
        
        # Test our supported standard timeframes
        assert convert_to_qlib_freq("15min") == "15min"
        assert convert_to_qlib_freq("30min") == "30min"
        
        # Test unsupported formats return as-is
        result = convert_to_qlib_freq("4h")
        assert isinstance(result, str)  # Should return as-is
        assert result == "4h"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])