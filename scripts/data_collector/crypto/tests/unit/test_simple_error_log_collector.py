# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test cases for simplified error logging collector.

This module tests the simple error logging functionality that prevents
repeated BadSymbol error logs from polluting the log output.
"""

import pytest
import pandas as pd
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add the crypto collector path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from simple_error_log_collector import SimpleErrorLogCollector
from exchange_adapters.base_adapter import ExchangeAdapter

try:
    import ccxt
except ImportError:
    ccxt = None


class MockExchangeAdapter(ExchangeAdapter):
    """Mock exchange adapter for testing simple error logging."""
    
    def __init__(self, exchange_id: str = "test_exchange"):
        self.exchange_id = exchange_id
        self.bad_symbols = set()
        self.network_error_symbols = set()
        # Initialize parent class
        super().__init__(exchange_id)
        
    def _init_exchange(self, **kwargs):
        """Initialize exchange-specific settings."""
        pass
    
    def get_instruments(self, market_type: str = "spot", base_currency=None, quote_currency=None):
        """Get list of available trading instruments."""
        return ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
    
    def get_symbols(self, market_type: str = "spot"):
        """Get list of available symbols."""
        return ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
    
    def get_symbol_info(self, symbol: str):
        """Get symbol information."""
        return {
            "symbol": symbol,
            "base": symbol.split('/')[0],
            "quote": symbol.split('/')[1],
            "active": True
        }
    
    def normalize_symbol(self, symbol: str):
        """Normalize symbol format."""
        return symbol.replace('-', '/').upper()
    
    def standardize_symbol(self, symbol: str):
        """Standardize symbol format."""
        return symbol.replace('-', '/').upper()
    
    def get_ticker(self, symbol: str):
        """Get ticker information."""
        return {
            "symbol": symbol,
            "last": 50000.0,
            "bid": 49999.0,
            "ask": 50001.0,
            "volume": 1000.0
        }
    
    def get_funding_rate(self, symbol: str):
        """Get funding rate for perpetual contracts."""
        return {
            "symbol": symbol,
            "funding_rate": 0.0001,
            "next_funding_time": datetime.now() + timedelta(hours=8)
        }
    
    def get_open_interest(self, symbol: str):
        """Get open interest for futures contracts."""
        return {
            "symbol": symbol,
            "open_interest": 10000.0,
            "timestamp": datetime.now()
        }
        
    def get_ohlcv(self, symbol: str, timeframe: str, start_time=None, end_time=None):
        """Mock OHLCV data collection with error simulation."""
        if symbol in self.bad_symbols:
            if ccxt:
                raise ccxt.BadSymbol(f"Symbol {symbol} not found")
            else:
                raise Exception(f"BadSymbol: Symbol {symbol} not found")
                
        if symbol in self.network_error_symbols:
            if ccxt:
                raise ccxt.NetworkError(f"Network error for {symbol}")
            else:
                raise Exception(f"NetworkError: Network error for {symbol}")
        
        # Return mock data
        dates = pd.date_range(
            start=start_time or datetime.now() - timedelta(days=1),
            end=end_time or datetime.now(),
            freq='1h'
        )[:10]  # Limit to 10 rows
        
        return pd.DataFrame({
            'open': [100.0] * 10,
            'high': [105.0] * 10,
            'low': [95.0] * 10,
            'close': [102.0] * 10,
            'volume': [1000.0] * 10
        }, index=dates)
    
    def add_bad_symbol(self, symbol: str):
        """Add a symbol to the bad symbols list."""
        self.bad_symbols.add(symbol)
    
    def add_network_error_symbol(self, symbol: str):
        """Add a symbol to the network error list."""
        self.network_error_symbols.add(symbol)


@pytest.fixture
def mock_adapter():
    """Create a mock exchange adapter."""
    return MockExchangeAdapter()


@pytest.fixture
def simple_collector():
    """Create a simple error log collector with smart logging enabled."""
    return SimpleErrorLogCollector(
        max_retries=1,  # Reduce retries for faster tests
        retry_delay=0.1,
        enable_smart_logging=True,
        error_cache_ttl=3600  # 1 hour for tests
    )


@pytest.fixture
def no_smart_logging_collector():
    """Create a simple error log collector with smart logging disabled."""
    return SimpleErrorLogCollector(
        max_retries=1,
        retry_delay=0.1,
        enable_smart_logging=False
    )


class TestSimpleErrorLogCollector:
    """Test simple error logging functionality."""
    
    def test_basic_initialization(self):
        """Test basic collector initialization."""
        collector = SimpleErrorLogCollector()
        
        assert collector.max_retries == 3
        assert collector.retry_delay == 1.0
        assert collector.enable_smart_logging is True
        assert collector.error_cache_ttl == 24 * 3600
        assert len(collector._logged_bad_symbols) == 0
        assert len(collector._bad_symbol_cache) == 0
    
    def test_cache_key_generation(self, simple_collector, mock_adapter):
        """Test cache key generation for different symbols."""
        key1 = simple_collector._get_symbol_cache_key(mock_adapter, 'BTC/USDT')
        assert key1 == "test_exchange_BTC/USDT"
        
        key2 = simple_collector._get_symbol_cache_key(mock_adapter, 'ETH/USDT')
        assert key2 == "test_exchange_ETH/USDT"
        assert key1 != key2
    
    def test_successful_data_collection(self, simple_collector, mock_adapter):
        """Test successful data collection."""
        result = simple_collector.collect_symbol_data(
            adapter=mock_adapter,
            symbol='BTC/USDT',
            timeframe='1h',
            start_time='2024-01-01',
            end_time='2024-01-02'
        )
        
        assert result['status'] == 'success'
        assert result['symbol'] == 'BTC/USDT'
        assert not result['data'].empty
        assert len(result['errors']) == 0
        
        # Check statistics
        stats = simple_collector.get_stats()
        assert stats['successful_collections'] == 1
        assert stats['failed_collections'] == 0
    
    def test_first_bad_symbol_logs_warning(self, simple_collector, mock_adapter):
        """Test that first BadSymbol error logs at WARNING level."""
        mock_adapter.add_bad_symbol('BADTEST/USDT')
        
        with patch('simple_error_log_collector.logger') as mock_logger:
            result = simple_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BADTEST/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            # Should log at WARNING level for first occurrence
            mock_logger.warning.assert_called()
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not found' in str(call)]
            assert len(warning_calls) > 0
            
            # Result should be failed
            assert result['status'] == 'failed'
            assert 'not found' in str(result['errors'])
    
    def test_subsequent_bad_symbol_logs_debug(self, simple_collector, mock_adapter):
        """Test that subsequent BadSymbol errors log at DEBUG level."""
        mock_adapter.add_bad_symbol('BADTEST/USDT')
        
        # First call - should log WARNING
        with patch('simple_error_log_collector.logger') as mock_logger:
            simple_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BADTEST/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            # Verify WARNING was called
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not found' in str(call)]
            assert len(warning_calls) > 0
        
        # Second call - should log DEBUG
        with patch('simple_error_log_collector.logger') as mock_logger:
            simple_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BADTEST/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            # Should log at DEBUG level for subsequent occurrence
            debug_calls = [call for call in mock_logger.debug.call_args_list 
                         if 'known issue' in str(call)]
            assert len(debug_calls) > 0
            
            # Should not log WARNING again
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not found' in str(call)]
            assert len(warning_calls) == 0
    
    def test_different_symbols_log_separately(self, simple_collector, mock_adapter):
        """Test that different symbols are tracked separately."""
        mock_adapter.add_bad_symbol('BAD1/USDT')
        mock_adapter.add_bad_symbol('BAD2/USDT')
        
        # First symbol - should log WARNING
        with patch('simple_error_log_collector.logger') as mock_logger:
            simple_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BAD1/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not found' in str(call)]
            assert len(warning_calls) > 0
        
        # Different symbol - should also log WARNING (first time for this symbol)
        with patch('simple_error_log_collector.logger') as mock_logger:
            simple_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BAD2/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not found' in str(call)]
            assert len(warning_calls) > 0
    
    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        # Create collector with very short TTL
        collector = SimpleErrorLogCollector(
            enable_smart_logging=True,
            error_cache_ttl=1  # 1 second TTL
        )
        
        mock_adapter = MockExchangeAdapter()
        mock_adapter.add_bad_symbol('BADTEST/USDT')
        
        # First call - should log WARNING
        with patch('simple_error_log_collector.logger') as mock_logger:
            collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BADTEST/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not found' in str(call)]
            assert len(warning_calls) > 0
        
        # Wait for cache to expire
        time.sleep(2)
        
        # Second call after expiration - should log WARNING again
        with patch('simple_error_log_collector.logger') as mock_logger:
            collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BADTEST/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            # Should log at WARNING level again after cache expiration
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not found' in str(call)]
            assert len(warning_calls) > 0
    
    def test_smart_logging_disabled(self, no_smart_logging_collector, mock_adapter):
        """Test behavior when smart logging is disabled."""
        mock_adapter.add_bad_symbol('BADTEST/USDT')
        
        # Multiple calls should all log at WARNING level
        for i in range(3):
            with patch('simple_error_log_collector.logger') as mock_logger:
                no_smart_logging_collector.collect_symbol_data(
                    adapter=mock_adapter,
                    symbol='BADTEST/USDT',
                    timeframe='1h',
                    start_time='2024-01-01',
                    end_time='2024-01-02'
                )
                
                # Should always log at WARNING level when smart logging is disabled
                warning_calls = [call for call in mock_logger.warning.call_args_list 
                               if 'not found' in str(call)]
                assert len(warning_calls) > 0
    
    def test_batch_collection(self, simple_collector, mock_adapter):
        """Test batch collection with mixed symbol statuses."""
        mock_adapter.add_bad_symbol('BAD/USDT')
        
        symbols = ['BTC/USDT', 'ETH/USDT', 'BAD/USDT']
        
        batch_results = simple_collector.collect_multiple_symbols(
            adapter=mock_adapter,
            symbols=symbols,
            timeframe='1h',
            start_time='2024-01-01',
            end_time='2024-01-02'
        )
        
        # Check batch results
        assert batch_results['batch_stats']['total_symbols'] == 3
        assert len(batch_results['batch_stats']['successful_symbols']) == 2  # BTC and ETH
        assert len(batch_results['batch_stats']['failed_symbols']) == 1      # BAD
        
        # Check individual results
        results = batch_results['results']
        assert results['BTC/USDT']['status'] == 'success'
        assert results['ETH/USDT']['status'] == 'success'
        assert results['BAD/USDT']['status'] == 'failed'
    
    def test_network_error_retry(self, simple_collector, mock_adapter):
        """Test retry logic for network errors."""
        mock_adapter.add_network_error_symbol('NETWORK/USDT')
        
        result = simple_collector.collect_symbol_data(
            adapter=mock_adapter,
            symbol='NETWORK/USDT',
            timeframe='1h',
            start_time='2024-01-01',
            end_time='2024-01-02'
        )
        
        # Should fail after retries
        assert result['status'] == 'failed'
        assert 'Network error' in str(result['errors'])
    
    def test_statistics_tracking(self, simple_collector, mock_adapter):
        """Test that statistics are tracked correctly."""
        mock_adapter.add_bad_symbol('BAD/USDT')
        
        # Successful collection
        simple_collector.collect_symbol_data(
            adapter=mock_adapter,
            symbol='BTC/USDT',
            timeframe='1h',
            start_time='2024-01-01',
            end_time='2024-01-02'
        )
        
        # Failed collection (BadSymbol)
        simple_collector.collect_symbol_data(
            adapter=mock_adapter,
            symbol='BAD/USDT',
            timeframe='1h',
            start_time='2024-01-01',
            end_time='2024-01-02'
        )
        
        stats = simple_collector.get_stats()
        assert stats['total_attempts'] == 2
        assert stats['successful_collections'] == 1
        assert stats['failed_collections'] == 1
        assert stats['bad_symbol_errors'] == 1
        assert stats['other_errors'] == 0
    
    def test_smart_logging_stats(self, simple_collector, mock_adapter):
        """Test smart logging statistics."""
        # Initial stats
        stats = simple_collector.get_smart_logging_stats()
        assert stats['smart_logging_enabled'] is True
        assert stats['cached_bad_symbols'] == 0
        
        # Add some cached symbols
        mock_adapter.add_bad_symbol('BAD1/USDT')
        mock_adapter.add_bad_symbol('BAD2/USDT')
        
        # Trigger caching
        for symbol in ['BAD1/USDT', 'BAD2/USDT']:
            simple_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol=symbol,
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
        
        # Check updated stats
        stats = simple_collector.get_smart_logging_stats()
        assert stats['cached_bad_symbols'] == 2
        assert len(stats['cache_entries']) == 2
        assert stats['oldest_cache_entry'] is not None
        assert stats['newest_cache_entry'] is not None
    
    def test_config_update(self, simple_collector):
        """Test runtime configuration updates."""
        # Initial state
        assert simple_collector.enable_smart_logging is True
        assert simple_collector.error_cache_ttl == 3600
        
        # Update configuration
        simple_collector.update_smart_logging_config(
            enable_smart_logging=False,
            error_cache_ttl=7200
        )
        
        # Verify updates
        assert simple_collector.enable_smart_logging is False
        assert simple_collector.error_cache_ttl == 7200
        
        # Cache should be cleared when disabling
        assert len(simple_collector._logged_bad_symbols) == 0
        assert len(simple_collector._bad_symbol_cache) == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
