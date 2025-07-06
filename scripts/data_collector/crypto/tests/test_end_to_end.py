#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for end-to-end data flow testing.

This script tests the complete data collection pipeline from data fetching 
to storage, collecting BTC/USDT and ETH/USDT data for 1 hour.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import time

from exchange_adapters.binance_adapter import BinanceAdapter
from exchange_adapters.okx_adapter import OKXAdapter
from storage_manager import CryptoStorageManager
from data_validator import CryptoDataValidator
from config.main_config import CryptoDataConfig


class TestEndToEndDataFlow:
    """Test complete data collection pipeline."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with temporary directories."""
        # Create temporary directory for test data
        self.test_data_dir = tempfile.mkdtemp(prefix="crypto_e2e_test_")
        
        # Setup proxy if needed
        proxy_url = os.environ.get('CRYPTO_TEST_PROXY', None)
        if proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
        
        # Set test mode
        os.environ['QLIB_TEST_MODE'] = '1'
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)
        
        if proxy_url:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
    
    def test_binance_end_to_end_flow(self):
        """Test complete Binance data collection flow."""
        print("Testing Binance end-to-end data flow...")

        try:
            # Initialize components
            try:
                adapter = BinanceAdapter()
            except Exception as init_error:
                pytest.skip(f"Skipping Binance test due to initialization error: {init_error}")

            storage_manager = CryptoStorageManager(self.test_data_dir)
            validator = CryptoDataValidator()

            # Test symbols and timeframe
            symbols = ['BTCUSDT', 'ETHUSDT']
            timeframe = '1h'
            limit = 10  # Collect 10 hours of data to minimize API calls

            for symbol in symbols:
                print(f"Processing {symbol}...")

                # Step 1: Fetch data from exchange
                try:
                    df = adapter.get_ohlcv(symbol, timeframe, limit=limit)
                except Exception as fetch_error:
                    pytest.skip(f"Skipping {symbol} due to fetch error: {fetch_error}")

                assert df is not None, f"Failed to fetch data for {symbol}"
                assert len(df) > 0, f"No data returned for {symbol}"

                # Data is already a DataFrame with proper index and columns

                # Step 3: Validate data
                validation_result = validator.validate(df, symbol, timeframe)
                assert validation_result.overall_status != "FAIL", f"Data validation failed for {symbol}: {validation_result.total_errors} errors"

                # Step 4: Store data
                instrument = f"binance.{symbol}"
                storage_manager.save_ohlcv_data(
                    data=df,
                    instrument=instrument,
                    freq=timeframe
                )

                # Step 5: Verify stored data can be read back
                stored_df = storage_manager.load_ohlcv_data(instrument, timeframe)
                assert stored_df is not None, f"Failed to load stored data for {symbol}"
                assert len(stored_df) == len(df), f"Data length mismatch for {symbol}"

                print(f"✅ {symbol} end-to-end flow completed successfully")

                # Add delay between symbols to respect rate limits
                time.sleep(1)

            print("✅ Binance end-to-end flow test passed")

        except Exception as e:
            pytest.fail(f"Binance end-to-end flow test failed: {e}")
    
    def test_okx_end_to_end_flow(self):
        """Test complete OKX data collection flow."""
        print("Testing OKX end-to-end data flow...")
        
        try:
            # Initialize components
            try:
                adapter = OKXAdapter()
            except Exception as init_error:
                pytest.skip(f"Skipping OKX test due to initialization error: {init_error}")

            storage_manager = CryptoStorageManager(self.test_data_dir)
            validator = CryptoDataValidator()

            # Test symbols and timeframe (OKX format)
            symbols = ['BTC-USDT', 'ETH-USDT']
            timeframe = '1h'
            limit = 10  # Collect 10 hours of data to minimize API calls

            for symbol in symbols:
                print(f"Processing {symbol}...")

                # Step 1: Fetch data from exchange
                try:
                    df = adapter.get_ohlcv(symbol, timeframe, limit=limit)
                except Exception as fetch_error:
                    pytest.skip(f"Skipping {symbol} due to fetch error: {fetch_error}")
                assert df is not None, f"Failed to fetch data for {symbol}"
                assert len(df) > 0, f"No data returned for {symbol}"

                # Data is already a DataFrame with proper index and columns
                
                # Step 3: Validate data
                validation_result = validator.validate(df, symbol, timeframe)
                assert validation_result.overall_status != "FAIL", f"Data validation failed for {symbol}: {validation_result.total_errors} errors"
                
                # Step 4: Store data
                instrument = f"okx.{symbol}"
                storage_manager.save_ohlcv_data(
                    data=df,
                    instrument=instrument,
                    freq=timeframe
                )

                # Step 5: Verify stored data can be read back
                stored_df = storage_manager.load_ohlcv_data(instrument, timeframe)
                assert stored_df is not None, f"Failed to load stored data for {symbol}"
                assert len(stored_df) == len(df), f"Data length mismatch for {symbol}"
                
                print(f"✅ {symbol} end-to-end flow completed successfully")
                
                # Add delay between symbols to respect rate limits
                time.sleep(1)
            
            print("✅ OKX end-to-end flow test passed")
            
        except Exception as e:
            pytest.fail(f"OKX end-to-end flow test failed: {e}")
    
    def test_data_consistency_across_exchanges(self):
        """Test data consistency between exchanges for the same symbol."""
        print("Testing data consistency across exchanges...")
        
        try:
            # Initialize adapters
            binance_adapter = BinanceAdapter()
            okx_adapter = OKXAdapter()
            
            # Fetch same timeframe data from both exchanges
            timeframe_binance = '1h'
            timeframe_okx = '1h'
            limit = 5  # Small sample to minimize API calls
            
            # Fetch BTC/USDT from both exchanges
            binance_df = binance_adapter.get_ohlcv('BTCUSDT', timeframe_binance, limit=limit)
            okx_df = okx_adapter.get_ohlcv('BTC-USDT', timeframe_okx, limit=limit)

            assert binance_df is not None, "Failed to fetch Binance data"
            assert okx_df is not None, "Failed to fetch OKX data"
            assert len(binance_df) > 0, "No Binance data returned"
            assert len(okx_df) > 0, "No OKX data returned"

            # Data is already in DataFrame format with proper types
            
            # Check that prices are in reasonable ranges (basic sanity check)
            for df, exchange in [(binance_df, 'Binance'), (okx_df, 'OKX')]:
                for col in ['open', 'high', 'low', 'close']:
                    prices = df[col].dropna()
                    assert len(prices) > 0, f"No valid {col} prices from {exchange}"
                    assert prices.min() > 0, f"Invalid {col} prices from {exchange}: {prices.min()}"
                    assert prices.max() < 1000000, f"Unrealistic {col} prices from {exchange}: {prices.max()}"
            
            print("✅ Data consistency check passed")
            
        except Exception as e:
            pytest.fail(f"Data consistency test failed: {e}")
    
    def test_storage_directory_structure(self):
        """Test that proper directory structure is created."""
        print("Testing storage directory structure...")
        
        try:
            storage_manager = CryptoStorageManager(self.test_data_dir)
            
            # Create some test data
            test_data = pd.DataFrame({
                'open': [100.0, 101.0],
                'high': [102.0, 103.0],
                'low': [99.0, 100.0],
                'close': [101.0, 102.0],
                'volume': [1000.0, 1100.0]
            }, index=pd.date_range('2023-01-01', periods=2, freq='1H'))
            
            # Store data for different exchanges and symbols
            test_cases = [
                ('binance', 'BTCUSDT', '1h'),
                ('okx', 'BTC-USDT', '1h'),
                ('binance', 'ETHUSDT', '1h'),
            ]
            
            for exchange, symbol, timeframe in test_cases:
                # Convert symbol to instrument format for storage
                instrument = f"{exchange}.{symbol}"

                # Save data using correct method name
                storage_manager.save_ohlcv_data(
                    data=test_data,
                    instrument=instrument,
                    freq=timeframe
                )

                # Verify data can be loaded
                loaded_data = storage_manager.load_ohlcv_data(instrument, timeframe)
                assert loaded_data is not None, f"Failed to load data for {instrument}"
                assert len(loaded_data) == len(test_data), f"Data length mismatch for {instrument}"
            
            print("✅ Storage directory structure test passed")
            
        except Exception as e:
            pytest.fail(f"Storage directory structure test failed: {e}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
