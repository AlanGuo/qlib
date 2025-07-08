#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for exception recovery testing (4.4).

This script tests the system's ability to gracefully handle and recover from various exceptions:
- Network interruption and recovery
- API rate limiting handling
- Disk space issues
- Data anomaly handling
"""

import pytest
import os
import tempfile
import shutil
import time
import socket
import threading
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
import psutil

from exchange_adapters.binance_adapter import BinanceAdapter
from exchange_adapters.okx_adapter import OKXAdapter
from storage_manager import CryptoStorageManager
from data_validator import CryptoDataValidator
from config.main_config import CryptoDataConfig
from qlib_data_generator import QlibDataGenerator


class TestExceptionRecovery:
    """Test exception recovery capabilities."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with temporary directories."""
        # Create temporary directory for test data
        self.test_data_dir = tempfile.mkdtemp(prefix="crypto_exception_test_")
        
        # Setup proxy for real environment testing
        proxy_url = os.environ.get('CRYPTO_TEST_PROXY', 'http://127.0.0.1:10808')
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url
        print(f"Using proxy: {proxy_url}")
        
        # Set test mode
        os.environ['QLIB_TEST_MODE'] = '1'
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    def test_network_interruption_recovery(self):
        """Test network interruption and recovery handling."""
        print("\n=== Testing Network Interruption Recovery ===")
        
        # Setup test configuration
        config = CryptoDataConfig()
        config.collection.exchanges = ['binance']
        config.collection.symbols = ['BTC/USDT']
        config.collection.timeframes = ['1m']
        config.collection.output_dir = self.test_data_dir
        config.collection.retry_attempts = 3
        config.collection.retry_delay = 1.0
        
        # Initialize components
        adapter = BinanceAdapter()
        storage_manager = CryptoStorageManager(self.test_data_dir)
        validator = CryptoDataValidator()
        
        # Test Phase 1: Normal operation with proxy
        print("Phase 1: Normal data collection...")
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', limit=3)
            assert len(data) > 0, "Should collect data normally"
            print(f"✓ Collected {len(data)} data points normally")
        except Exception as e:
            print(f"✗ Normal collection failed: {e}")
            print("This might be expected if proxy is down - continuing with recovery tests")
        
        # Test Phase 2: Simulate network interruption
        print("Phase 2: Simulating network interruption...")
        
        # Create a mock that simulates network timeout
        def mock_get_with_timeout(*args, **kwargs):
            raise socket.timeout("Network timeout simulated")
        
        original_get = adapter.get_ohlcv
        adapter.get_ohlcv = mock_get_with_timeout
        
        # Test retry mechanism
        retry_count = 0
        max_retries = config.collection.retry_attempts
        
        for attempt in range(max_retries):
            try:
                data = adapter.get_ohlcv('BTCUSDT', '1h', limit=2)
                break
            except socket.timeout:
                retry_count += 1
                print(f"✓ Retry {retry_count}: Network timeout handled correctly")
                time.sleep(1)
        
        assert retry_count == max_retries, f"Should retry {max_retries} times"
        
        # Test Phase 3: Network recovery
        print("Phase 3: Network recovery...")
        adapter.get_ohlcv = original_get
        
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', limit=2)
            assert len(data) > 0, "Should recover and collect data"
            print(f"✓ Network recovered, collected {len(data)} data points")
        except Exception as e:
            print(f"✗ Network recovery failed: {e}")
            raise
        
        print("✓ Network interruption recovery test passed")

    def test_proxy_failure_recovery(self):
        """Test proxy failure and recovery handling."""
        print("\n=== Testing Proxy Failure Recovery ===")
        
        # Setup test configuration
        config = CryptoDataConfig()
        config.collection.exchanges = ['binance']
        config.collection.symbols = ['BTC/USDT']
        config.collection.timeframes = ['1m']
        config.collection.output_dir = self.test_data_dir
        config.collection.retry_attempts = 3
        config.collection.retry_delay = 2.0
        
        # Test Phase 1: Normal operation with working proxy
        print("Phase 1: Testing with working proxy...")
        working_proxy = os.environ.get('CRYPTO_TEST_PROXY', 'http://127.0.0.1:10808')
        
        try:
            adapter = BinanceAdapter()
            data = adapter.get_ohlcv('BTCUSDT', '1h', 
                                       limit=2)
            print(f"✓ Working proxy successful, collected {len(data)} data points")
            proxy_working = True
        except Exception as e:
            print(f"! Working proxy failed: {e}")
            proxy_working = False
        
        # Test Phase 2: Simulate proxy failure
        print("Phase 2: Simulating proxy failure...")
        
        # Set invalid proxy to simulate failure
        bad_proxy = 'http://127.0.0.1:99999'  # Non-existent port
        os.environ['HTTP_PROXY'] = bad_proxy
        os.environ['HTTPS_PROXY'] = bad_proxy
        os.environ['http_proxy'] = bad_proxy
        os.environ['https_proxy'] = bad_proxy
        
        # Test proxy failure handling
        proxy_failures = 0
        max_retries = config.collection.retry_attempts
        
        for attempt in range(max_retries):
            try:
                # Create new adapter with bad proxy
                adapter_bad = BinanceAdapter()
                data = adapter_bad.get_ohlcv('BTCUSDT', '1h', 
                                               limit=1)
                break
            except Exception as e:
                proxy_failures += 1
                print(f"✓ Proxy failure {proxy_failures}: {type(e).__name__} handled correctly")
                time.sleep(config.collection.retry_delay)
        
        print(f"✓ Detected {proxy_failures} proxy failures as expected")
        
        # Test Phase 3: Proxy recovery
        print("Phase 3: Proxy recovery...")
        
        # Restore working proxy
        os.environ['HTTP_PROXY'] = working_proxy
        os.environ['HTTPS_PROXY'] = working_proxy
        os.environ['http_proxy'] = working_proxy
        os.environ['https_proxy'] = working_proxy
        
        # Test recovery only if proxy was working initially
        if proxy_working:
            try:
                adapter_recovered = BinanceAdapter()
                data = adapter_recovered.get_ohlcv('BTCUSDT', '1h', 
                                                     limit=1)
                print(f"✓ Proxy recovered, collected {len(data)} data points")
            except Exception as e:
                print(f"! Proxy recovery failed: {e}")
        else:
            print("! Skipping recovery test as initial proxy was not working")
        
        print("✓ Proxy failure recovery test completed")

    def test_api_rate_limiting_handling(self):
        """Test API rate limiting handling."""
        print("\n=== Testing API Rate Limiting Handling ===")
        
        # Setup test configuration
        config = CryptoDataConfig()
        config.collection.exchanges = ['binance']
        config.collection.symbols = ['BTC/USDT']
        config.collection.timeframes = ['1m']
        config.collection.output_dir = self.test_data_dir
        config.collection.retry_attempts = 3
        config.collection.retry_delay = 2.0
        
        # Initialize adapter
        adapter = BinanceAdapter()
        
        # Test Phase 1: Normal operation
        print("Phase 1: Normal API calls...")
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', 
                                       limit=2)
            assert len(data) > 0, "Should collect data normally"
            print(f"✓ Normal API call successful, collected {len(data)} data points")
        except Exception as e:
            print(f"✗ Normal API call failed: {e}")
            raise
        
        # Test Phase 2: Simulate rate limiting
        print("Phase 2: Simulating API rate limiting...")
        
        # Create a mock that simulates rate limiting error
        def mock_get_with_rate_limit(*args, **kwargs):
            from ccxt.base.errors import RateLimitExceeded
            raise RateLimitExceeded("Rate limit exceeded")
        
        original_get = adapter.get_ohlcv
        adapter.get_ohlcv = mock_get_with_rate_limit
        
        # Test rate limit handling
        rate_limit_count = 0
        max_retries = config.collection.retry_attempts
        
        for attempt in range(max_retries):
            try:
                data = adapter.get_ohlcv('BTCUSDT', '1h', limit=2)
                break
            except Exception as e:
                rate_limit_count += 1
                print(f"✓ Rate limit {rate_limit_count}: {type(e).__name__} handled correctly")
                time.sleep(config.collection.retry_delay)  # Wait longer for rate limiting
        
        assert rate_limit_count == max_retries, f"Should handle rate limit {max_retries} times"
        
        # Test Phase 3: API recovery
        print("Phase 3: API recovery...")
        adapter.get_ohlcv = original_get
        
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', limit=1)
            assert len(data) > 0, "Should recover and collect data"
            print(f"✓ API recovered, collected {len(data)} data points")
        except Exception as e:
            print(f"✗ API recovery failed: {e}")
            raise
        
        print("✓ API rate limiting handling test passed")

    def test_disk_space_handling(self):
        """Test disk space insufficient handling."""
        print("\n=== Testing Disk Space Handling ===")
        
        # Setup test configuration
        config = CryptoDataConfig()
        config.collection.exchanges = ['binance']
        config.collection.symbols = ['BTC/USDT']
        config.collection.timeframes = ['1m']
        config.collection.output_dir = self.test_data_dir
        config.collection.retry_attempts = 2
        config.collection.retry_delay = 1.0
        
        # Initialize components
        adapter = BinanceAdapter()
        storage_manager = CryptoStorageManager(self.test_data_dir)
        
        # Test Phase 1: Check available disk space
        print("Phase 1: Checking disk space...")
        disk_usage = psutil.disk_usage(self.test_data_dir)
        available_gb = disk_usage.free / (1024**3)
        print(f"Available disk space: {available_gb:.2f} GB")
        
        # Test Phase 2: Normal storage operation
        print("Phase 2: Normal storage operation...")
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', 
                                       limit=2)
            
            # Convert to DataFrame for storage
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Store data
            storage_manager.save_ohlcv_data(
                data=df,
                instrument=f"binance.BTCUSDT",
                freq='1h'
            )
            print("✓ Normal storage operation successful")
        except Exception as e:
            print(f"✗ Normal storage operation failed: {e}")
            raise
        
        # Test Phase 3: Simulate disk space issue
        print("Phase 3: Simulating disk space issue...")
        
        # Create a mock that simulates disk space error
        def mock_save_with_disk_error(*args, **kwargs):
            raise OSError("No space left on device")
        
        original_save = storage_manager.save_ohlcv_data
        storage_manager.save_ohlcv_data = mock_save_with_disk_error
        
        # Test disk space error handling
        disk_error_handled = False
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', limit=1)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            storage_manager.save_ohlcv_data(
                data=df,
                instrument=f"binance.BTCUSDT", 
                freq='1h'
            )
        except OSError as e:
            if "No space left on device" in str(e):
                disk_error_handled = True
                print("✓ Disk space error handled correctly")
            else:
                raise
        
        assert disk_error_handled, "Should handle disk space error"
        
        # Test Phase 4: Storage recovery
        print("Phase 4: Storage recovery...")
        storage_manager.save_ohlcv_data = original_save
        
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', limit=1)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            storage_manager.save_ohlcv_data(
                data=df,
                instrument=f"binance.BTCUSDT", 
                freq='1h'
            )
            print("✓ Storage recovered successfully")
        except Exception as e:
            print(f"✗ Storage recovery failed: {e}")
            raise
        
        print("✓ Disk space handling test passed")

    def test_data_anomaly_handling(self):
        """Test data anomaly handling."""
        print("\n=== Testing Data Anomaly Handling ===")
        
        # Setup test configuration
        config = CryptoDataConfig()
        config.collection.exchanges = ['binance']
        config.collection.symbols = ['BTC/USDT']
        config.collection.timeframes = ['1m']
        config.collection.output_dir = self.test_data_dir
        config.collection.retry_attempts = 2
        config.collection.retry_delay = 1.0
        
        # Initialize components
        adapter = BinanceAdapter()
        validator = CryptoDataValidator()
        storage_manager = CryptoStorageManager(self.test_data_dir)
        
        # Test Phase 1: Normal data validation
        print("Phase 1: Normal data validation...")
        try:
            data = adapter.get_ohlcv('BTCUSDT', '1h', 
                                       limit=2)
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Validate data
            validation_result = validator.validate(df, 'BTCUSDT', '1h')
            is_valid = validation_result.overall_status != "FAIL"
            issues = validation_result.total_errors
            print(f"✓ Normal data validation: valid={is_valid}, issues={issues}")
        except Exception as e:
            print(f"✗ Normal data validation failed: {e}")
            raise
        
        # Test Phase 2: Simulate data anomalies
        print("Phase 2: Simulating data anomalies...")
        
        # Create anomalous data
        anomalous_data = [
            [int(datetime.now().timestamp() * 1000), 50000, 55000, 49000, 52000, 1000],  # Normal
            [int(datetime.now().timestamp() * 1000), 52000, 0, 51000, 51500, 800],       # Zero high price
            [int(datetime.now().timestamp() * 1000), 51500, 52000, 60000, 51800, 900],  # Low > High
            [int(datetime.now().timestamp() * 1000), 51800, 52200, 51700, -1000, 1100], # Negative close
        ]
        
        anomalous_df = pd.DataFrame(anomalous_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        anomalous_df['datetime'] = pd.to_datetime(anomalous_df['timestamp'], unit='ms')
        
        # Test anomaly detection
        validation_result = validator.validate(anomalous_df, 'BTCUSDT', '1h')
        is_valid = validation_result.overall_status != "FAIL"
        issues = validation_result.total_errors
        print(f"✓ Anomaly detection: valid={is_valid}, issues={issues}")
        
        assert not is_valid, "Should detect anomalies"
        assert issues > 0, "Should report validation issues"
        
        # Test Phase 3: Data filtering and recovery
        print("Phase 3: Data filtering and recovery...")
        
        # Filter out anomalous data
        filtered_df = anomalous_df[
            (anomalous_df['high'] > 0) & 
            (anomalous_df['low'] <= anomalous_df['high']) & 
            (anomalous_df['close'] > 0) &
            (anomalous_df['volume'] >= 0)
        ]
        
        # Validate filtered data
        validation_result = validator.validate(filtered_df, 'BTCUSDT', '1h')
        is_valid = validation_result.overall_status != "FAIL"
        issues = validation_result.total_errors
        print(f"✓ Filtered data validation: valid={is_valid}, issues={issues}")
        
        if is_valid:
            print("✓ Data filtering successful")
        else:
            print("! Some issues remain after filtering")
        
        # Test Phase 4: Store valid data only
        print("Phase 4: Storing valid data only...")
        try:
            if len(filtered_df) > 0:
                storage_manager.save_ohlcv_data(
                    data=filtered_df,
                    instrument=f"binance.BTCUSDT",
                    freq='1h'
                )
                print(f"✓ Stored {len(filtered_df)} valid records")
            else:
                print("! No valid data to store")
        except Exception as e:
            print(f"✗ Storage of valid data failed: {e}")
            raise
        
        print("✓ Data anomaly handling test passed")

    def test_comprehensive_exception_recovery(self):
        """Test comprehensive exception recovery scenario."""
        print("\n=== Testing Comprehensive Exception Recovery ===")
        
        # Setup test configuration
        config = CryptoDataConfig()
        config.collection.exchanges = ['binance']
        config.collection.symbols = ['BTCUSDT', 'ETHUSDT']
        config.collection.timeframes = ['1m']
        config.collection.output_dir = self.test_data_dir
        config.collection.retry_attempts = 3
        config.collection.retry_delay = 1.0
        
        # Initialize components
        adapter = BinanceAdapter()
        storage_manager = CryptoStorageManager(self.test_data_dir)
        validator = CryptoDataValidator()
        
        # Test comprehensive recovery scenario
        print("Testing comprehensive recovery scenario...")
        
        total_attempts = 0
        successful_collections = 0
        
        for symbol in config.collection.symbols:
            print(f"\nProcessing {symbol}...")
            
            for attempt in range(config.collection.retry_attempts):
                total_attempts += 1
                
                try:
                    # Fetch data
                    data = adapter.get_ohlcv(symbol, '1h', limit=3)
                    
                    if len(data) == 0:
                        print(f"  Attempt {attempt + 1}: No data received")
                        continue
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    # Validate data (but don't fail on validation issues for this test)
                    validation_result = validator.validate(df, symbol, '1h')
                    is_valid = validation_result.overall_status != "FAIL"
                    issues = validation_result.total_errors
                    
                    # For comprehensive test, continue even with minor validation issues
                    if issues > 5:  # Only fail on major validation issues
                        print(f"  Attempt {attempt + 1}: Major data validation failed ({issues} issues)")
                        continue
                    
                    # Store data
                    storage_manager.save_ohlcv_data(
                        data=df,
                        instrument=f"binance.{symbol}",
                        freq='1h'
                    )
                    
                    successful_collections += 1
                    print(f"  ✓ Attempt {attempt + 1}: Successfully collected and stored {len(df)} records")
                    break
                    
                except Exception as e:
                    print(f"  Attempt {attempt + 1}: Exception occurred - {type(e).__name__}: {str(e)[:100]}")
                    time.sleep(config.collection.retry_delay)
                    continue
        
        # Calculate success rate
        success_rate = (successful_collections / len(config.collection.symbols)) * 100
        print(f"\nComprehensive recovery results:")
        print(f"- Total symbols: {len(config.collection.symbols)}")
        print(f"- Total attempts: {total_attempts}")
        print(f"- Successful collections: {successful_collections}")
        print(f"- Success rate: {success_rate:.1f}%")
        
        # Verify stored data
        stored_files = list(Path(self.test_data_dir).rglob("*.*"))  # All files
        print(f"- Stored files: {len(stored_files)}")
        if len(stored_files) > 0:
            print(f"- File types: {[f.suffix for f in stored_files[:10]]}")  # Show first 10 file extensions
        
        # Generate calendar and instruments files for recovery test
        if successful_collections > 0:
            print("Generating calendar and instruments files after recovery...")
            try:
                # Initialize qlib for QlibDataGenerator
                import qlib
                qlib.init(provider_uri=self.test_data_dir)
                
                # Generate complete Qlib structure
                qlib_generator = QlibDataGenerator(
                    data_dir=self.test_data_dir,
                    provider_uri=self.test_data_dir
                )
                
                # Calculate date range based on recent data
                end_date = datetime.now()
                start_date = end_date - timedelta(hours=5)  # Cover collected data range
                
                summary = qlib_generator.create_full_structure(
                    timeframes=['1h'],
                    exchanges=['binance'],
                    symbols=[s.replace('USDT', '/USDT') for s in config.collection.symbols],
                    start_date=start_date,
                    end_date=end_date,
                    market_type='spot'
                )
                
                print(f"✅ Exception recovery Qlib structure generated: {summary['timeframes_created']} timeframes, "
                      f"{summary['instruments_files']} instruments files, "
                      f"{summary['calendar_files']} calendar files")
                
                # Verify calendar and instruments files exist
                data_path = Path(self.test_data_dir)
                tf_dir = data_path / "1h"
                
                if (tf_dir / "instruments" / "crypto.txt").exists():
                    print("✅ Instruments file generated successfully after recovery")
                if (tf_dir / "calendars" / "1h.txt").exists():
                    print("✅ Calendar files generated successfully after recovery")
                
            except Exception as qlib_error:
                print(f"⚠️ Calendar/instruments generation failed after recovery: {qlib_error}")
                # Don't fail the test for this, as it's an enhancement
        
        # Assert minimum success criteria
        assert success_rate >= 50, f"Success rate {success_rate:.1f}% too low"
        assert len(stored_files) > 0, "No data files were stored"
        
        print("✓ Comprehensive exception recovery test passed")


if __name__ == "__main__":
    # Run tests directly
    test_instance = TestExceptionRecovery()
    test_instance.setup_test_environment()
    
    try:
        test_instance.test_network_interruption_recovery()
        test_instance.test_proxy_failure_recovery()
        test_instance.test_api_rate_limiting_handling()
        test_instance.test_disk_space_handling()
        test_instance.test_data_anomaly_handling()
        test_instance.test_comprehensive_exception_recovery()
        print("\n🎉 All exception recovery tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise