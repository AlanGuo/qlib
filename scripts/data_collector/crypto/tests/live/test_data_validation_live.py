"""
Live Data Validation Test Suite for Crypto Data Collector

This test suite validates the data collection system using actual exchange APIs.
It ensures real-world data integrity, API compatibility, and proper handling of
live market conditions.

WARNING: These tests make actual API calls to exchanges and may be rate-limited.
Use with caution and ensure you have proper API credentials if required.

Test Coverage:
- All supported exchanges (Binance, OKX, future Bybit)
- All supported timeframes (1min, 5min, 15min, 30min, 1h, 4h, 1d)
- Core trading pairs (BTC/USDT, ETH/USDT, BNB/USDT, TRX/USDT, DOGE/USDT)
- Real data structure validation
- Live batch size scenarios
- Rate limiting and error handling
"""

import pytest
import os
import sys
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import ccxt
from unittest.mock import patch

# Add crypto collector to path
crypto_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(crypto_root))

from exchange_adapters.binance_adapter import BinanceAdapter
from exchange_adapters.okx_adapter import OKXAdapter
from crypto_field_collector import CryptoFieldCollector
from config.exchanges import EXCHANGE_CONFIGS
from config.timeframes import TIMEFRAME_MAPPING, get_exchange_timeframe
from cli import CLI


class SimpleDataValidationHelper:
    """Simple data validation helper for live tests"""
    
    def validate_ohlcv_data(self, data: List[List]) -> Dict[str, Any]:
        """Basic OHLCV data validation"""
        if not data:
            return {"valid": False, "errors": ["No data provided"]}
        
        errors = []
        
        for i, row in enumerate(data):
            if len(row) != 6:  # timestamp, open, high, low, close, volume
                errors.append(f"Row {i}: Expected 6 columns, got {len(row)}")
                continue
            
            # Check data types and values
            try:
                timestamp, open_price, high, low, close, volume = row
                
                # Validate numeric values
                if not all(isinstance(x, (int, float)) for x in [open_price, high, low, close, volume]):
                    errors.append(f"Row {i}: Non-numeric values found")
                    continue
                
                # Validate price relationships
                if not (low <= open_price <= high and low <= close <= high):
                    errors.append(f"Row {i}: Invalid OHLC relationships")
                
                # Validate volume
                if volume < 0:
                    errors.append(f"Row {i}: Negative volume")
                    
            except (ValueError, TypeError) as e:
                errors.append(f"Row {i}: Data validation error: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "total_rows": len(data),
            "error_count": len(errors)
        }


# Test Parameters
EXCHANGES = ["binance", "okx"]
TIMEFRAMES = ["1min", "5min", "15min", "30min", "1h", "4h", "1d"]
CORE_SYMBOLS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "TRX/USDT", "DOGE/USDT"]
MARKET_TYPES = ["spot", "futures", "perpetual"]

# Rate limiting configuration
RATE_LIMIT_DELAY = 1.0  # Seconds between API calls
MAX_RETRIES = 3


class LiveDataValidator:
    """Validator for live exchange data"""
    
    def __init__(self):
        self.data_helper = SimpleDataValidationHelper()
        self.last_request_time = {}
    
    def enforce_rate_limit(self, exchange: str):
        """Enforce rate limiting between API calls"""
        now = time.time()
        if exchange in self.last_request_time:
            elapsed = now - self.last_request_time[exchange]
            if elapsed < RATE_LIMIT_DELAY:
                time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time[exchange] = time.time()
    
    def validate_live_data(self, data: pd.DataFrame, exchange: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Validate live data with additional real-world checks"""
        
        # Convert DataFrame to list format for base validation
        if isinstance(data, pd.DataFrame):
            data_list = []
            for idx, row in data.iterrows():
                # Convert timestamp to milliseconds
                timestamp_ms = int(idx.timestamp() * 1000)
                data_list.append([timestamp_ms, row['open'], row['high'], row['low'], row['close'], row['volume']])
        else:
            data_list = data
        
        # Use base validation first
        result = self.data_helper.validate_ohlcv_data(data_list)
        
        if not result["valid"]:
            return result
        
        # Add warnings list if not exists
        if "warnings" not in result:
            result["warnings"] = []
        
        # Additional live data validations
        if len(data) > 0:
            # Check if timestamps are recent (within last few days for short timeframes)
            latest_timestamp = data.index[-1].timestamp()
            latest_time = datetime.fromtimestamp(latest_timestamp)
            now = datetime.now()
            
            # For short timeframes, data should be very recent
            if timeframe in ["1min", "5min", "15min"]:
                max_age = timedelta(hours=1)
            else:
                max_age = timedelta(days=1)
            
            if now - latest_time > max_age:
                result["warnings"].append(f"Data seems stale: latest timestamp {latest_time}")
            
            # Check for realistic price ranges
            prices = []
            for col in ['open', 'high', 'low', 'close']:
                prices.extend(data[col].tolist())
            
            min_price = min(prices)
            max_price = max(prices)
            
            # Basic sanity checks for major pairs
            if "BTC" in symbol and "USDT" in symbol:
                if min_price < 10000 or max_price > 100000:
                    result["warnings"].append(f"BTC/USDT price out of expected range: {min_price}-{max_price}")
            elif "ETH" in symbol and "USDT" in symbol:
                if min_price < 1000 or max_price > 10000:
                    result["warnings"].append(f"ETH/USDT price out of expected range: {min_price}-{max_price}")
        
        return result
    
    def test_exchange_connectivity(self, exchange: str) -> Dict[str, Any]:
        """Test basic connectivity to exchange"""
        result = {
            "connected": False,
            "error": None,
            "exchange_info": {}
        }
        
        try:
            self.enforce_rate_limit(exchange)
            
            # Configure proxy settings from environment variables
            proxy_config = {}
            if os.getenv('https_proxy') or os.getenv('HTTPS_PROXY'):
                proxy_url = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
                proxy_config['proxies'] = {
                    'http': proxy_url,
                    'https': proxy_url
                }
            
            if exchange == "binance":
                client = ccxt.binance(proxy_config)
            elif exchange == "okx":
                client = ccxt.okx(proxy_config)
            else:
                result["error"] = f"Unsupported exchange: {exchange}"
                return result
            
            # Test basic API call
            markets = client.load_markets()
            result["connected"] = True
            result["exchange_info"] = {
                "total_markets": len(markets),
                "exchange_id": client.id,
                "has_ohlcv": client.has.get("fetchOHLCV", False)
            }
            
        except Exception as e:
            result["error"] = str(e)
        
        return result


@pytest.fixture
def live_validator():
    """Live data validator instance"""
    return LiveDataValidator()


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.mark.live
class TestLiveDataValidation:
    """Main test class for live data validation"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Add delay between tests to avoid rate limiting
        time.sleep(1)
    
    @pytest.mark.parametrize("exchange", EXCHANGES)
    def test_exchange_connectivity(self, exchange, live_validator):
        """Test basic connectivity to each exchange"""
        result = live_validator.test_exchange_connectivity(exchange)
        
        if not result["connected"]:
            pytest.skip(f"Cannot connect to {exchange}: {result['error']}")
        
        assert result["connected"], f"Failed to connect to {exchange}: {result['error']}"
        assert result["exchange_info"]["has_ohlcv"], f"{exchange} doesn't support OHLCV data"
        assert result["exchange_info"]["total_markets"] > 0, f"No markets found on {exchange}"
    
    @pytest.mark.parametrize("exchange,symbol", [
        (exchange, symbol)
        for exchange in EXCHANGES
        for symbol in CORE_SYMBOLS[:2]  # Test subset to avoid rate limits
    ])
    def test_symbol_availability(self, exchange, symbol, live_validator):
        """Test if core symbols are available on each exchange"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity(exchange)
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to {exchange}: {connectivity['error']}")
        
        try:
            live_validator.enforce_rate_limit(exchange)
            
            if exchange == "binance":
                adapter = BinanceAdapter()
            elif exchange == "okx":
                adapter = OKXAdapter()
            else:
                pytest.skip(f"Unsupported exchange: {exchange}")
            
            # Test if symbol is available
            instruments = adapter.get_instruments()
            available_symbols = instruments  # get_instruments already returns a list of symbols
            
            assert symbol in available_symbols, f"Symbol {symbol} not available on {exchange}"
            
        except Exception as e:
            pytest.fail(f"Failed to check symbol availability: {e}")
    
    @pytest.mark.parametrize("exchange,timeframe,symbol", [
        (exchange, timeframe, symbol)
        for exchange in EXCHANGES
        for timeframe in ["1h", "1d"]  # Test longer timeframes to avoid rate limits
        for symbol in CORE_SYMBOLS[:1]  # Test one symbol per combination
    ])
    def test_small_batch_live_data(self, exchange, timeframe, symbol, live_validator):
        """Test small batch live data collection"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity(exchange)
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to {exchange}: {connectivity['error']}")
        
        try:
            live_validator.enforce_rate_limit(exchange)
            
            if exchange == "binance":
                adapter = BinanceAdapter()
            elif exchange == "okx":
                adapter = OKXAdapter()
            else:
                pytest.skip(f"Unsupported exchange: {exchange}")
            
            # Setup time range for small batch
            end_time = datetime.now()
            if timeframe == "1h":
                start_time = end_time - timedelta(hours=5)  # Small batch
            else:  # 1d
                start_time = end_time - timedelta(days=3)
            
            # Collect data
            data = adapter.get_ohlcv(symbol, timeframe, start_time, end_time)
            
            # Validate data
            assert len(data) > 0, f"No data returned for {exchange}:{symbol}:{timeframe}"
            
            validation_result = live_validator.validate_live_data(data, exchange, symbol, timeframe)
            assert validation_result["valid"], f"Invalid live data: {validation_result['errors']}"
            
            # Log warnings if any
            if validation_result["warnings"]:
                print(f"Warnings for {exchange}:{symbol}:{timeframe}: {validation_result['warnings']}")
                
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.parametrize("exchange,timeframe,symbol", [
        (exchange, timeframe, symbol)
        for exchange in EXCHANGES
        for timeframe in ["1d"]  # Only test daily for large batches
        for symbol in CORE_SYMBOLS[:1]
    ])
    def test_large_batch_live_data(self, exchange, timeframe, symbol, live_validator):
        """Test large batch live data collection"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity(exchange)
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to {exchange}: {connectivity['error']}")
        
        try:
            live_validator.enforce_rate_limit(exchange)
            
            if exchange == "binance":
                adapter = BinanceAdapter()
            elif exchange == "okx":
                adapter = OKXAdapter()
            else:
                pytest.skip(f"Unsupported exchange: {exchange}")
            
            max_candles = EXCHANGE_CONFIGS[exchange].max_candles_per_request
            
            # Setup time range for large batch
            end_time = datetime.now()
            start_time = end_time - timedelta(days=max_candles + 50)  # Force multiple requests
            
            # Collect data
            data = adapter.get_ohlcv(symbol, timeframe, start_time, end_time)
            
            # Validate data
            assert len(data) >= max_candles * 0.9, f"Expected large batch (>={max_candles * 0.9}), got {len(data)} records"
            
            validation_result = live_validator.validate_live_data(data, exchange, symbol, timeframe)
            assert validation_result["valid"], f"Invalid live data: {validation_result['errors']}"
            
            # Check for pagination handling - timestamps should be sorted
            timestamps = data.index.tolist()
            assert len(set(timestamps)) == len(timestamps), "Duplicate timestamps found"
            assert timestamps == sorted(timestamps), "Timestamps not in order"
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.parametrize("exchange,timeframe,symbol", [
        (exchange, timeframe, symbol)
        for exchange in EXCHANGES
        for timeframe in ["1d"]
        for symbol in CORE_SYMBOLS[:1]
    ])
    def test_boundary_batch_live_data(self, exchange, timeframe, symbol, live_validator):
        """Test boundary batch live data collection"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity(exchange)
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to {exchange}: {connectivity['error']}")
        
        try:
            live_validator.enforce_rate_limit(exchange)
            
            if exchange == "binance":
                adapter = BinanceAdapter()
            elif exchange == "okx":
                adapter = OKXAdapter()
            else:
                pytest.skip(f"Unsupported exchange: {exchange}")
            
            max_candles = EXCHANGE_CONFIGS[exchange].max_candles_per_request
            
            # Setup time range for boundary batch
            end_time = datetime.now()
            start_time = end_time - timedelta(days=max_candles)
            
            # Collect data
            data = adapter.get_ohlcv(symbol, timeframe, start_time, end_time)
            
            # Validate data
            assert len(data) > 0, f"No data returned for boundary test"
            
            validation_result = live_validator.validate_live_data(data, exchange, symbol, timeframe)
            assert validation_result["valid"], f"Invalid live data: {validation_result['errors']}"
            
            # Check that we get close to max_candles (allowing for weekends, etc.)
            assert len(data) >= max_candles * 0.7, f"Expected ~{max_candles} records, got {len(data)}"
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.parametrize("exchange,timeframe", [
        (exchange, timeframe)
        for exchange in EXCHANGES
        for timeframe in ["1min", "5min", "1h", "1d"]
    ])
    def test_timeframe_data_consistency(self, exchange, timeframe, live_validator):
        """Test data consistency across different timeframes"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity(exchange)
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to {exchange}: {connectivity['error']}")
        
        try:
            live_validator.enforce_rate_limit(exchange)
            
            if exchange == "binance":
                adapter = BinanceAdapter()
            elif exchange == "okx":
                adapter = OKXAdapter()
            else:
                pytest.skip(f"Unsupported exchange: {exchange}")
            
            symbol = "BTC/USDT"  # Use stable symbol
            
            # Setup time range based on timeframe
            end_time = datetime.now()
            if timeframe == "1min":
                start_time = end_time - timedelta(minutes=60)
            elif timeframe == "5min":
                start_time = end_time - timedelta(minutes=300)
            elif timeframe == "1h":
                start_time = end_time - timedelta(hours=24)
            else:  # 1d
                start_time = end_time - timedelta(days=7)
            
            # Collect data
            data = adapter.get_ohlcv(symbol, timeframe, start_time, end_time)
            
            # Validate data
            assert len(data) > 0, f"No data returned for {exchange}:{timeframe}"
            
            validation_result = live_validator.validate_live_data(data, exchange, symbol, timeframe)
            assert validation_result["valid"], f"Invalid live data: {validation_result['errors']}"
            
            # Check timeframe-specific consistency
            if len(data) > 1:
                timestamps = [int(ts.timestamp() * 1000) for ts in data.index]  # Convert to milliseconds
                intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                
                # Expected interval in milliseconds
                expected_intervals = {
                    "1min": 60000,
                    "5min": 300000,
                    "1h": 3600000,
                    "1d": 86400000
                }
                
                expected_interval = expected_intervals.get(timeframe)
                if expected_interval:
                    # Allow some tolerance for irregular intervals
                    tolerance = expected_interval * 0.1
                    irregular_count = sum(1 for i in intervals if abs(i - expected_interval) > tolerance)
                    
                    # Should have mostly regular intervals
                    assert irregular_count < len(intervals) * 0.3, f"Too many irregular intervals in {timeframe} data"
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.parametrize("exchange", EXCHANGES)
    def test_rate_limiting_compliance(self, exchange, live_validator):
        """Test rate limiting compliance"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity(exchange)
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to {exchange}: {connectivity['error']}")
        
        try:
            if exchange == "binance":
                adapter = BinanceAdapter()
            elif exchange == "okx":
                adapter = OKXAdapter()
            else:
                pytest.skip(f"Unsupported exchange: {exchange}")
            
            symbol = "BTC/USDT"
            timeframe = "1h"
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=5)
            
            # Make multiple requests and measure timing
            request_times = []
            for i in range(3):  # Make 3 requests
                start = time.time()
                data = adapter.get_ohlcv(symbol, timeframe, start_time, end_time)
                end = time.time()
                
                assert len(data) > 0, f"No data returned in request {i+1}"
                request_times.append(end - start)
                
                # Ensure we don't overwhelm the API
                if i < 2:  # Don't sleep after last request
                    time.sleep(RATE_LIMIT_DELAY)
            
            # All requests should complete successfully
            assert len(request_times) == 3, "Not all requests completed"
            
            # Check that rate limiting is working (requests shouldn't be too fast)
            config = EXCHANGE_CONFIGS[exchange]
            min_interval = config.rate_limit
            
            # At least one request should take longer than the minimum
            assert any(t >= min_interval for t in request_times), "Rate limiting not working properly"
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    def test_error_handling_resilience(self, live_validator):
        """Test error handling and resilience"""
        # Test with invalid symbol
        try:
            adapter = BinanceAdapter()
            invalid_symbol = "INVALID/PAIR"
            
            # This should either return empty data or raise a known exception
            try:
                data = adapter.get_ohlcv(invalid_symbol, "1h", datetime.now() - timedelta(hours=1), datetime.now())
                # If it returns data, it should be empty
                assert len(data) == 0, "Invalid symbol should return empty data"
            except (ccxt.BaseError, ValueError, KeyError):
                # These are expected exceptions for invalid symbols
                pass
            
        except Exception as e:
            pytest.fail(f"Unexpected error handling behavior: {e}")
    
    @pytest.mark.slow
    def test_full_integration_workflow(self, temp_data_dir, live_validator):
        """Test full integration workflow with live data"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity("binance")
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to binance: {connectivity['error']}")
        
        try:
            # Create a simple config for testing
            config = {
                "exchange": "binance",
                "market_type": "spot",
                "symbols": ["BTC/USDT"],
                "timeframes": ["1h"],
                "start_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "output_dir": str(temp_data_dir)
            }
            
            # Initialize CLI and collector
            cli = CLI()
            
            # Run collection
            live_validator.enforce_rate_limit("binance")
            
            # This is a simplified test - in real usage, you'd use the CLI
            adapter = BinanceAdapter()
            collector = CryptoFieldCollector(adapter)
            
            # Collect data for BTC/USDT
            ticker_data = collector.collect_ticker_fields("BTC/USDT")
            
            # Check that we got some data
            assert isinstance(ticker_data, dict), "Data collection should return a dictionary"
            assert len(ticker_data) > 0, "Should have collected some ticker data"
            
            # Basic check that collector is working
            assert collector.exchange_id == "binance"
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")


class TestLiveDataQuality:
    """Test live data quality and market conditions"""
    
    @pytest.mark.live
    def test_market_hours_detection(self, live_validator):
        """Test detection of market hours and data availability"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity("binance")
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to binance: {connectivity['error']}")
        
        try:
            live_validator.enforce_rate_limit("binance")
            
            adapter = BinanceAdapter()
            symbol = "BTC/USDT"
            timeframe = "1h"
            
            # Crypto markets are 24/7, so we should always get recent data
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=3)
            
            data = adapter.get_ohlcv(symbol, timeframe, start_time, end_time)
            
            assert len(data) > 0, "Should have data for 24/7 crypto markets"
            
            # Check that the latest data is very recent
            latest_timestamp = data.index[-1].timestamp()
            latest_time = datetime.fromtimestamp(latest_timestamp)
            time_diff = (datetime.now() - latest_time).total_seconds()
            
            # Should be within 2 hours for hourly data
            assert time_diff < 7200, f"Data is too old: {time_diff} seconds"
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    @pytest.mark.live
    def test_data_freshness(self, live_validator):
        """Test data freshness for different timeframes"""
        # Test connectivity first
        connectivity = live_validator.test_exchange_connectivity("binance")
        if not connectivity["connected"]:
            pytest.skip(f"Cannot connect to binance: {connectivity['error']}")
        
        try:
            adapter = BinanceAdapter()
            symbol = "BTC/USDT"
            
            # Test different timeframes
            timeframes = ["1min", "5min", "1h"]
            
            for timeframe in timeframes:
                live_validator.enforce_rate_limit("binance")
                
                end_time = datetime.now()
                if timeframe == "1min":
                    start_time = end_time - timedelta(minutes=10)
                elif timeframe == "5min":
                    start_time = end_time - timedelta(minutes=30)
                else:  # 1h
                    start_time = end_time - timedelta(hours=3)
                
                data = adapter.get_ohlcv(symbol, timeframe, start_time, end_time)
                
                assert len(data) > 0, f"No data for {timeframe}"
                
                # Check freshness
                latest_timestamp = data.index[-1].timestamp()
                latest_time = datetime.fromtimestamp(latest_timestamp)
                time_diff = (datetime.now() - latest_time).total_seconds()
                
                # Different freshness expectations for different timeframes
                if timeframe == "1min":
                    max_age = 300  # 5 minutes
                elif timeframe == "5min":
                    max_age = 900  # 15 minutes
                else:  # 1h
                    max_age = 7200  # 2 hours
                
                assert time_diff < max_age, f"Data for {timeframe} is too old: {time_diff} seconds"
                
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")


if __name__ == "__main__":
    # Run with live marker
    pytest.main([__file__, "-v", "-m", "live"])