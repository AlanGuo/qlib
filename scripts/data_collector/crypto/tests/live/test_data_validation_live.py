"""
Live Data Validation Test Suite for Crypto Data Collector

This test suite validates the data collection system using actual exchange APIs.
It ensures real-world data integrity, API compatibility, and proper handling of
live market conditions including pagination scenarios.

WARNING: These tests make actual API calls to exchanges and may be rate-limited.
Use with caution and ensure you have proper API credentials if required.

Test Coverage:
- All supported exchanges (Binance, OKX)
- All supported timeframes (1min, 5min, 15min, 30min, 1h, 4h, 1d)
- Core trading pairs (BTC/USDT, ETH/USDT, BNB/USDT, TRX/USDT, DOGE/USDT)
- Real data structure validation
- Pagination vs non-pagination data quality comparison
- Large-scale pagination stress testing
- SimpleErrorLogCollector pagination logic validation
- Boundary batch data collection
- Rate limiting and error handling

Test Structure (Optimized):
- Exchange connectivity and symbol availability tests
- Core pagination comparison test (replaces separate small/large batch tests)
- Specialized pagination stress and boundary tests
- Error handling and integration workflow tests
"""

import pytest
import os
import sys
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import ccxt

# Add crypto collector to path
crypto_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(crypto_root))

from exchange_adapters.binance_adapter import BinanceAdapter
from exchange_adapters.okx_adapter import OKXAdapter
from crypto_field_collector import CryptoFieldCollector
from simple_error_log_collector import SimpleErrorLogCollector
from config.exchanges import EXCHANGE_CONFIGS
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
    
    def validate_pagination_continuity(self, data: pd.DataFrame, expected_interval_minutes: int) -> Dict[str, Any]:
        """Validate data continuity and detect pagination artifacts"""
        if len(data) < 2:
            return {"valid": True, "gaps": [], "overlaps": [], "irregular_intervals": 0}
        
        timestamps = data.index.tolist()
        gaps = []
        overlaps = []
        irregular_intervals = 0
        expected_interval_ms = expected_interval_minutes * 60 * 1000
        
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds() * 1000
            
            # Check for gaps (missing data)
            if interval > expected_interval_ms * 1.5:
                gaps.append({
                    "start": timestamps[i-1],
                    "end": timestamps[i],
                    "missing_periods": int((interval / expected_interval_ms) - 1)
                })
            
            # Check for overlaps (should not happen with proper pagination)
            elif interval < expected_interval_ms * 0.5:
                overlaps.append({
                    "timestamp1": timestamps[i-1],
                    "timestamp2": timestamps[i],
                    "interval_ms": interval
                })
            
            # Count irregular intervals
            if abs(interval - expected_interval_ms) > expected_interval_ms * 0.1:
                irregular_intervals += 1
        
        return {
            "valid": len(gaps) == 0 and len(overlaps) == 0,
            "gaps": gaps,
            "overlaps": overlaps,
            "irregular_intervals": irregular_intervals,
            "total_intervals": len(timestamps) - 1
        }
    
    def compare_pagination_scenarios(self, non_paginated_result: Dict[str, Any], 
                                   paginated_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare validation results between non-paginated and paginated scenarios"""
        comparison = {
            "both_valid": non_paginated_result["valid"] and paginated_result["valid"],
            "quality_difference": {},
            "metrics_comparison": {},
            "recommendations": []
        }
        
        # Compare metrics
        np_metrics = non_paginated_result.get("metrics", {})
        p_metrics = paginated_result.get("metrics", {})
        
        for metric in ["total_records", "invalid_ohlc_relationships", "negative_volumes", "zero_volumes"]:
            if metric in np_metrics and metric in p_metrics:
                comparison["metrics_comparison"][metric] = {
                    "non_paginated": np_metrics[metric],
                    "paginated": p_metrics[metric],
                    "difference": p_metrics[metric] - np_metrics[metric]
                }
        
        # Quality assessment
        if not non_paginated_result["valid"] and paginated_result["valid"]:
            comparison["quality_difference"]["winner"] = "paginated"
            comparison["recommendations"].append("Non-paginated data has quality issues")
        elif non_paginated_result["valid"] and not paginated_result["valid"]:
            comparison["quality_difference"]["winner"] = "non_paginated" 
            comparison["recommendations"].append("Paginated data has quality issues")
        elif non_paginated_result["valid"] and paginated_result["valid"]:
            comparison["quality_difference"]["winner"] = "both"
            comparison["recommendations"].append("Both scenarios produce valid data")
        else:
            comparison["quality_difference"]["winner"] = "neither"
            comparison["recommendations"].append("Both scenarios have quality issues")
        
        return comparison
    
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
        for timeframe in ["1h", "1d"]
        for symbol in CORE_SYMBOLS[:2]  # Limit symbols to reduce test time
    ])
    def test_pagination_vs_non_pagination_data_quality(self, exchange, timeframe, symbol, live_validator):
        """
        Test comparing data quality between non-paginated and paginated scenarios.
        Core pagination validation test - compares small vs large batch data collection.
        """
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
            
            config = EXCHANGE_CONFIGS[exchange]
            
            # Scenario 1: Non-paginated (small batch within single request limit)
            end_time = datetime.now()
            if timeframe == "1h":
                small_batch_hours = min(config.max_candles_per_request * 0.4, 48)
                start_time_small = end_time - timedelta(hours=small_batch_hours)
            else:  # 1d
                small_batch_days = min(config.max_candles_per_request * 0.4, 30)
                start_time_small = end_time - timedelta(days=small_batch_days)
            
            print(f"\n📊 Testing {exchange}:{symbol}:{timeframe}")
            print(f"Non-paginated: {start_time_small} to {end_time}")
            
            data_small = adapter.get_ohlcv(symbol, timeframe, start_time_small, end_time)
            non_paginated_result = live_validator.validate_live_data(data_small, exchange, symbol, timeframe)
            
            time.sleep(RATE_LIMIT_DELAY)  # Rate limiting between requests
            
            # Scenario 2: Paginated (large batch requiring multiple requests)
            if timeframe == "1h":
                large_batch_hours = config.max_candles_per_request * 1.3
                start_time_large = end_time - timedelta(hours=large_batch_hours)
            else:  # 1d
                large_batch_days = config.max_candles_per_request * 1.3  
                start_time_large = end_time - timedelta(days=large_batch_days)
            
            print(f"Paginated: {start_time_large} to {end_time}")
            
            # Use get_historical_data_batch for pagination test
            data_large = adapter.get_historical_data_batch(symbol, timeframe, start_time_large, end_time)
            paginated_result = live_validator.validate_live_data(data_large, exchange, symbol, timeframe)
            
            # Validate pagination continuity for large batch
            timeframe_minutes = {"1h": 60, "1d": 1440}[timeframe]
            continuity_result = live_validator.validate_pagination_continuity(
                data_large, timeframe_minutes
            )
            
            # Compare scenarios
            comparison = live_validator.compare_pagination_scenarios(
                non_paginated_result, paginated_result
            )
            
            # Assertions for test pass/fail
            assert non_paginated_result["valid"], f"Non-paginated data invalid: {non_paginated_result['errors']}"
            assert paginated_result["valid"], f"Paginated data invalid: {paginated_result['errors']}"
            assert continuity_result["valid"] or len(continuity_result["gaps"]) < len(data_large) * 0.05, \
                f"Too many pagination gaps: {len(continuity_result['gaps'])}"
            
            # Additional pagination-specific checks
            assert len(data_large) > config.max_candles_per_request * 0.8, \
                f"Expected paginated data (>{config.max_candles_per_request * 0.8}), got {len(data_large)}"
            assert len(data_small) < config.max_candles_per_request, \
                f"Non-paginated data too large ({len(data_small)} >= {config.max_candles_per_request})"
            
            # Check data ordering across pagination
            if len(data_large) > 1:
                timestamps = data_large.index.tolist()
                assert timestamps == sorted(timestamps), "Paginated data timestamps not ordered"
                assert len(set(timestamps)) == len(timestamps), "Duplicate timestamps in paginated data"
            
            print(f"✓ Non-paginated: {len(data_small)} records, Valid: {non_paginated_result['valid']}")
            print(f"✓ Paginated: {len(data_large)} records, Valid: {paginated_result['valid']}")
            print(f"✓ Continuity: {continuity_result['valid']}, Gaps: {len(continuity_result['gaps'])}")
            print(f"✓ Comparison: {comparison['quality_difference']['winner']}")
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error for {exchange}: {e}")
        except Exception as e:
            pytest.fail(f"Pagination comparison test failed: {e}")
    
    @pytest.mark.parametrize("exchange", EXCHANGES)
    def test_large_scale_pagination_stress(self, exchange, live_validator):
        """
        Stress test with very large data requests requiring multiple pagination cycles.
        """
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
            
            config = EXCHANGE_CONFIGS[exchange]
            symbol = "BTC/USDT"
            timeframe = "1d"
            
            # Request 2.5x the max limit to force multiple pagination cycles
            target_records = int(config.max_candles_per_request * 2.5)
            end_time = datetime.now()
            start_time = end_time - timedelta(days=target_records)
            
            print(f"\n💪 Stress testing {exchange} pagination")
            print(f"Requesting ~{target_records} records (2.5x limit)")
            
            start_request_time = time.time()
            # Use get_historical_data_batch for stress test pagination
            data = adapter.get_historical_data_batch(symbol, timeframe, start_time, end_time)
            request_duration = time.time() - start_request_time
            
            # Validate stress test data
            result = live_validator.validate_live_data(data, exchange, symbol, timeframe)
            assert result["valid"], f"Stress test data invalid: {result['errors']}"
            
            # Validate pagination continuity
            continuity = live_validator.validate_pagination_continuity(data, 1440)  # 1 day = 1440 minutes
            
            # Assertions for stress test - More realistic expectations
            # Some exchanges may have limited historical data or API restrictions
            min_expected = max(target_records * 0.4, config.max_candles_per_request * 0.8)
            assert len(data) >= min_expected, \
                f"Expected at least {min_expected:.0f} records (40% of target or 80% of single request limit), got {len(data)}"
            assert len(continuity["gaps"]) < len(data) * 0.1, \
                f"Too many gaps ({len(continuity['gaps'])}) in stress test data"
            
            # Performance check - should complete within reasonable time
            assert request_duration < 300, f"Stress test took too long: {request_duration}s"
            
            print(f"✓ Stress test: {len(data)} records in {request_duration:.1f}s")
            print(f"✓ Continuity: {len(continuity['gaps'])} gaps, {continuity['irregular_intervals']} irregular intervals")
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error for {exchange}: {e}")
        except Exception as e:
            pytest.fail(f"Pagination stress test failed: {e}")
    
    @pytest.mark.parametrize("exchange,timeframe,symbol", [
        (exchange, timeframe, symbol)
        for exchange in EXCHANGES
        for timeframe in ["1h", "1d"]
        for symbol in ["BTC/USDT"]  # Single symbol to focus on pagination logic
    ])
    def test_simple_error_log_collector_pagination(self, exchange, timeframe, symbol, live_validator):
        """
        Test SimpleErrorLogCollector's automatic pagination logic.
        Verifies that the collector correctly chooses between direct and paginated methods.
        """
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
            
            config = EXCHANGE_CONFIGS[exchange]
            collector = SimpleErrorLogCollector()
            
            # Test small batch (should use direct method)
            end_time = datetime.now()
            if timeframe == "1h":
                small_batch_hours = min(config.max_candles_per_request * 0.3, 24)
                start_time_small = end_time - timedelta(hours=small_batch_hours)
            else:  # 1d
                small_batch_days = min(config.max_candles_per_request * 0.3, 10)
                start_time_small = end_time - timedelta(days=small_batch_days)
            
            print(f"\n🧪 Testing SimpleErrorLogCollector pagination logic for {exchange}:{symbol}:{timeframe}")
            print(f"Small batch: {start_time_small} to {end_time}")
            
            small_result = collector.collect_symbol_data(
                adapter=adapter,
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time_small,
                end_time=end_time
            )
            
            time.sleep(RATE_LIMIT_DELAY)
            
            # Test large batch (should use pagination)
            if timeframe == "1h":
                large_batch_hours = config.max_candles_per_request * 1.5
                start_time_large = end_time - timedelta(hours=large_batch_hours)
            else:  # 1d
                large_batch_days = config.max_candles_per_request * 1.5
                start_time_large = end_time - timedelta(days=large_batch_days)
            
            print(f"Large batch: {start_time_large} to {end_time}")
            
            large_result = collector.collect_symbol_data(
                adapter=adapter,
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time_large,
                end_time=end_time
            )
            
            # Get pagination statistics
            pagination_stats = collector.get_pagination_stats()
            
            # Validate results
            assert small_result['status'] == 'success', f"Small batch failed: {small_result['errors']}"
            assert large_result['status'] == 'success', f"Large batch failed: {large_result['errors']}"
            
            # Validate pagination logic was used appropriately
            assert pagination_stats['total_data_requests'] == 2, f"Expected 2 requests, got {pagination_stats['total_data_requests']}"
            assert pagination_stats['pagination_used'] >= 1, f"Expected at least 1 paginated request, got {pagination_stats['pagination_used']}"
            assert pagination_stats['direct_method_used'] >= 1, f"Expected at least 1 direct request, got {pagination_stats['direct_method_used']}"
            
            # Validate data quality
            small_validation = live_validator.validate_live_data(small_result['data'], exchange, symbol, timeframe)
            large_validation = live_validator.validate_live_data(large_result['data'], exchange, symbol, timeframe)
            
            assert small_validation['valid'], f"Small batch data invalid: {small_validation['errors']}"
            assert large_validation['valid'], f"Large batch data invalid: {large_validation['errors']}"
            
            # Validate pagination continuity for large batch
            timeframe_minutes = {"1h": 60, "1d": 1440}[timeframe]
            continuity_result = live_validator.validate_pagination_continuity(
                large_result['data'], timeframe_minutes
            )
            
            assert continuity_result['valid'] or len(continuity_result['gaps']) < len(large_result['data']) * 0.1, \
                f"Too many pagination gaps: {len(continuity_result['gaps'])}"
            
            print(f"✓ Small batch: {len(small_result['data'])} records, Method: direct")
            print(f"✓ Large batch: {len(large_result['data'])} records, Method: pagination")
            print(f"✓ Pagination stats: {pagination_stats['pagination_used']} paginated, {pagination_stats['direct_method_used']} direct")
            print(f"✓ Continuity: {len(continuity_result['gaps'])} gaps")
            
        except ccxt.BaseError as e:
            pytest.skip(f"Exchange API error for {exchange}: {e}")
        except Exception as e:
            pytest.fail(f"Data freshness test failed: {e}")


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
            pytest.fail(f"Boundary test failed: {e}")
    
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
            pytest.fail(f"Full integration test failed: {e}")


# =============================================================================
# TEST OPTIMIZATION NOTES
# =============================================================================
"""
This test suite has been optimized to remove redundant test cases:

REMOVED TESTS:
- test_small_batch_live_data: Functionality covered by test_pagination_vs_non_pagination_data_quality
- test_large_batch_live_data: Functionality covered by test_pagination_vs_non_pagination_data_quality

OPTIMIZATION BENEFITS:
- Reduced test execution time by ~6 test cases (4 small batch + 2 large batch)
- Eliminated functional redundancy while maintaining comprehensive coverage
- Cleaner test structure with focused, purpose-driven test methods

REMAINING CORE TESTS:
- test_pagination_vs_non_pagination_data_quality: Core pagination functionality
- test_large_scale_pagination_stress: Extreme pagination stress testing
- test_simple_error_log_collector_pagination: Component-specific pagination logic
- test_boundary_batch_live_data: Edge case boundary testing

The optimization maintains full test coverage while improving efficiency and clarity.
"""


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