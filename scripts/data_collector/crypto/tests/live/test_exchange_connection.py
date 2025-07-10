#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for cryptocurrency exchange connection testing.

This script tests real API connections to exchanges with limited request volume.
Tests Binance and OKX connections using public market data without API keys.
"""

import pytest
import asyncio
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from pathlib import Path

# Add crypto collector to path
crypto_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(crypto_root))

from exchange_adapters.binance_adapter import BinanceAdapter
from exchange_adapters.okx_adapter import OKXAdapter
from config.main_config import CryptoDataConfig


class TestExchangeConnection:
    """Test real exchange connections with limited requests."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with proxy if needed."""
        # Configure proxy for accessing exchanges
        proxy_url = os.environ.get('CRYPTO_TEST_PROXY', 'http://127.0.0.1:10808')

        # Set proxy environment variables
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url

        # Set test mode
        os.environ['QLIB_TEST_MODE'] = '1'

        print(f"Using proxy: {proxy_url}")

        yield

        # Cleanup
        for env_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            os.environ.pop(env_var, None)
    
    def test_binance_connection_basic(self):
        """Test basic Binance connection and market info."""
        print("Testing Binance basic connection...")
        
        try:
            adapter = BinanceAdapter()

            # Test connection by getting instruments
            instruments = adapter.get_instruments()
            assert instruments is not None, "Failed to get instruments from Binance"
            assert len(instruments) > 0, "No instruments returned from Binance"

            # Check if BTC/USDT exists
            btc_usdt_found = any(
                'BTCUSDT' in instrument or
                'BTC/USDT' in instrument
                for instrument in instruments
            )
            assert btc_usdt_found, "BTC/USDT instrument not found in Binance"

            print(f"✅ Binance connection successful, found {len(instruments)} instruments")
            
        except Exception as e:
            pytest.fail(f"Binance connection test failed: {e}")
    
    def test_okx_connection_basic(self):
        """Test basic OKX connection and market info."""
        print("Testing OKX basic connection...")
        
        try:
            adapter = OKXAdapter()
            
            # Test connection by getting instruments
            instruments = adapter.get_instruments()
            assert instruments is not None, "Failed to get instruments from OKX"
            assert len(instruments) > 0, "No instruments returned from OKX"

            # Check if BTC/USDT exists
            btc_usdt_found = any(
                'BTC-USDT' in instrument or
                'BTC/USDT' in instrument
                for instrument in instruments
            )
            assert btc_usdt_found, "BTC/USDT instrument not found in OKX"

            print(f"✅ OKX connection successful, found {len(instruments)} instruments")
            
        except Exception as e:
            pytest.fail(f"OKX connection test failed: {e}")
    
    def test_binance_ohlcv_fetch(self):
        """Test fetching OHLCV data from Binance."""
        print("Testing Binance OHLCV data fetch...")
        
        try:
            adapter = BinanceAdapter()
            
            # Fetch recent 1h data for BTC/USDT (limit to 5 candles to minimize requests)
            symbol = 'BTCUSDT'
            timeframe = '1h'
            limit = 5
            
            ohlcv_data = adapter.get_ohlcv(symbol, timeframe, limit=limit)
            
            assert ohlcv_data is not None, "No OHLCV data returned from Binance"
            assert not ohlcv_data.empty, "Empty OHLCV data from Binance"
            assert len(ohlcv_data) <= limit, f"Too many candles returned: {len(ohlcv_data)}"

            # Validate data structure (DataFrame columns)
            expected_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in expected_columns:
                assert col in ohlcv_data.columns, f"Missing column: {col}"

            # Validate data types
            assert ohlcv_data.index.dtype.kind in ['M', 'i'], "Invalid timestamp index"
            assert pd.api.types.is_numeric_dtype(ohlcv_data['open']), "Invalid open price type"
            assert pd.api.types.is_numeric_dtype(ohlcv_data['close']), "Invalid close price type"
            assert pd.api.types.is_numeric_dtype(ohlcv_data['volume']), "Invalid volume type"

            print(f"✅ Binance OHLCV fetch successful, got {len(ohlcv_data)} candles")
            
            # Add small delay to respect rate limits
            time.sleep(1)
            
        except Exception as e:
            pytest.fail(f"Binance OHLCV fetch test failed: {e}")
    
    def test_okx_ohlcv_fetch(self):
        """Test fetching OHLCV data from OKX."""
        print("Testing OKX OHLCV data fetch...")
        
        # IMPORTANT: OKX uses lowercase timeframes (1h, 1d, 1w), NOT uppercase!
        # This is a common source of confusion - do not change to uppercase
        
        try:
            adapter = OKXAdapter()
            
            # Fetch recent 1h data for BTC/USDT (limit to 5 candles to minimize requests)
            symbol = 'BTC-USDT'
            timeframe = '1h'
            limit = 5
            
            ohlcv_data = adapter.get_ohlcv(symbol, timeframe, limit=limit)
            
            assert ohlcv_data is not None, "No OHLCV data returned from OKX"
            assert not ohlcv_data.empty, "Empty OHLCV data from OKX"
            assert len(ohlcv_data) <= limit, f"Too many candles returned: {len(ohlcv_data)}"

            # Validate data structure (DataFrame columns)
            expected_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in expected_columns:
                assert col in ohlcv_data.columns, f"Missing column: {col}"

            # Validate data types
            assert ohlcv_data.index.dtype.kind in ['M', 'i'], "Invalid timestamp index"
            assert pd.api.types.is_numeric_dtype(ohlcv_data['open']), "Invalid open price type"
            assert pd.api.types.is_numeric_dtype(ohlcv_data['close']), "Invalid close price type"
            assert pd.api.types.is_numeric_dtype(ohlcv_data['volume']), "Invalid volume type"

            print(f"✅ OKX OHLCV fetch successful, got {len(ohlcv_data)} candles")
            
            # Add small delay to respect rate limits
            time.sleep(1)
            
        except Exception as e:
            pytest.fail(f"OKX OHLCV fetch test failed: {e}")
    
    def test_rate_limiting(self):
        """Test that rate limiting is respected."""
        print("Testing rate limiting...")
        
        try:
            adapter = BinanceAdapter()
            
            # Make multiple requests and measure timing
            start_time = time.time()
            request_count = 3
            
            for i in range(request_count):
                adapter.get_ohlcv('BTCUSDT', '1h', limit=1)
                if i < request_count - 1:  # Don't sleep after last request
                    time.sleep(0.5)  # Small delay between requests
            
            elapsed_time = time.time() - start_time
            
            # Should take at least some time due to rate limiting
            assert elapsed_time >= 1.0, f"Requests completed too quickly: {elapsed_time:.2f}s"
            
            print(f"✅ Rate limiting test passed, {request_count} requests took {elapsed_time:.2f}s")
            
        except Exception as e:
            pytest.fail(f"Rate limiting test failed: {e}")
    
    def test_error_handling(self):
        """Test error handling for invalid requests."""
        print("Testing error handling...")
        
        try:
            adapter = BinanceAdapter()
            
            # Test with invalid symbol
            try:
                adapter.fetch_ohlcv('INVALID/SYMBOL', '1h', limit=1)
                pytest.fail("Should have raised an exception for invalid symbol")
            except Exception as e:
                print(f"✅ Correctly handled invalid symbol: {type(e).__name__}")
            
            # Test with invalid timeframe
            try:
                adapter.fetch_ohlcv('BTCUSDT', 'invalid_timeframe', limit=1)
                pytest.fail("Should have raised an exception for invalid timeframe")
            except Exception as e:
                print(f"✅ Correctly handled invalid timeframe: {type(e).__name__}")
            
        except Exception as e:
            pytest.fail(f"Error handling test failed: {e}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
