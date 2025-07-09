# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test cases for delisting scenarios in cryptocurrency data collection.

This module tests the comprehensive handling of symbol delisting events,
including partial data collection, lifecycle management, and error handling.
"""

import pytest
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add the crypto collector path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from symbol_lifecycle import (
    SymbolLifecycleManager, 
    SymbolStatus, 
    SymbolStatusRecord, 
    SymbolAvailabilityWindow
)
from delisting_aware_collector import DelistingAwareCollector
from exchange_adapters.base_adapter import ExchangeAdapter
from incremental.manager import IncrementalUpdateManager
from config.main_config import CryptoDataConfig

try:
    import ccxt
except ImportError:
    ccxt = None


class MockExchangeAdapter(ExchangeAdapter):
    """Mock exchange adapter for testing."""
    
    def __init__(self, exchange_id: str = "test_exchange", simulate_delisting: bool = False):
        self.exchange_id = exchange_id
        self.simulate_delisting = simulate_delisting
        self.delisted_symbols = set()
        self.suspended_symbols = set()
        
    def get_ohlcv(self, symbol: str, timeframe: str, start_time=None, end_time=None):
        """Mock OHLCV data collection with delisting simulation."""
        if symbol in self.delisted_symbols:
            if ccxt:
                raise ccxt.BadSymbol(f"Symbol {symbol} not found")
            else:
                raise Exception(f"BadSymbol: Symbol {symbol} not found")
        
        if symbol in self.suspended_symbols:
            if ccxt:
                raise ccxt.MarketClosed(f"Market for {symbol} is closed")
            else:
                raise Exception(f"MarketClosed: Market for {symbol} is closed")
        
        # Generate mock data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        data = pd.DataFrame({
            'open': [100.0] * 100,
            'high': [105.0] * 100,
            'low': [95.0] * 100,
            'close': [102.0] * 100,
            'volume': [1000.0] * 100
        }, index=dates)
        
        return data
    
    def simulate_symbol_delisting(self, symbol: str):
        """Simulate a symbol being delisted."""
        self.delisted_symbols.add(symbol)
    
    def simulate_symbol_suspension(self, symbol: str):
        """Simulate a symbol being suspended."""
        self.suspended_symbols.add(symbol)


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = MagicMock(spec=CryptoDataConfig)
    config.data_dir = "/tmp/test_crypto_data"
    config.incremental = {
        'max_retries': 3,
        'retry_delay': 0.1,
        'enable_partial_collection': True,
        'symbol_cache_ttl': 300,
        'max_concurrent_updates': 5
    }
    return config


@pytest.fixture
def lifecycle_manager(tmp_path):
    """Create a symbol lifecycle manager for testing."""
    return SymbolLifecycleManager(
        storage_dir=str(tmp_path / "symbol_lifecycle"),
        cache_ttl=300,
        enable_persistence=False  # Disable persistence for tests
    )


@pytest.fixture
def mock_adapter():
    """Create a mock exchange adapter."""
    return MockExchangeAdapter()


@pytest.fixture
def delisting_collector(lifecycle_manager):
    """Create a delisting-aware collector for testing."""
    return DelistingAwareCollector(
        lifecycle_manager=lifecycle_manager,
        max_retries=3,
        retry_delay=0.1,
        enable_partial_collection=True
    )


class TestSymbolLifecycleManager:
    """Test symbol lifecycle management functionality."""
    
    def test_symbol_status_detection_active(self, lifecycle_manager):
        """Test detection of active symbols."""
        with patch('symbol_lifecycle.ccxt.binance') as mock_exchange_class:
            mock_exchange = Mock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.load_markets.return_value = {
                'BTC/USDT': {'active': True, 'spot': True}
            }
            mock_exchange.fetch_ticker.return_value = {
                'timestamp': datetime.now().timestamp() * 1000
            }
            
            status = lifecycle_manager._fetch_symbol_status('BTC/USDT', 'binance', 'spot')
            
            assert status.symbol == 'BTC/USDT'
            assert status.status == SymbolStatus.ACTIVE
            assert status.exchange == 'binance'
            assert status.market_type == 'spot'
    
    def test_symbol_status_detection_delisted(self, lifecycle_manager):
        """Test detection of delisted symbols."""
        with patch('symbol_lifecycle.ccxt.binance') as mock_exchange_class:
            mock_exchange = Mock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.load_markets.return_value = {}  # Symbol not found
            
            status = lifecycle_manager._fetch_symbol_status('DELIST/USDT', 'binance', 'spot')
            
            assert status.symbol == 'DELIST/USDT'
            assert status.status == SymbolStatus.DELISTED
            assert status.reason == "Symbol not found in markets"
    
    def test_symbol_status_detection_suspended(self, lifecycle_manager):
        """Test detection of suspended symbols."""
        with patch('symbol_lifecycle.ccxt.binance') as mock_exchange_class:
            mock_exchange = Mock()
            mock_exchange_class.return_value = mock_exchange
            mock_exchange.load_markets.return_value = {
                'SUSPEND/USDT': {'active': False, 'spot': True}
            }
            
            status = lifecycle_manager._fetch_symbol_status('SUSPEND/USDT', 'binance', 'spot')
            
            assert status.symbol == 'SUSPEND/USDT'
            assert status.status == SymbolStatus.SUSPENDED
            assert status.reason == "Market marked as inactive"
    
    def test_availability_window_tracking(self, lifecycle_manager):
        """Test tracking of symbol availability windows."""
        # Mark symbol as active
        active_record = SymbolStatusRecord(
            symbol='BTC/USDT',
            status=SymbolStatus.ACTIVE,
            timestamp=datetime.now(),
            exchange='binance',
            market_type='spot'
        )
        lifecycle_manager._update_availability_windows(active_record)
        
        # Check that an availability window was created
        windows = lifecycle_manager.get_symbol_availability_windows('BTC/USDT', 'binance', 'spot')
        assert len(windows) == 1
        assert windows[0].is_active()
        
        # Mark symbol as delisted
        delisted_record = SymbolStatusRecord(
            symbol='BTC/USDT',
            status=SymbolStatus.DELISTED,
            timestamp=datetime.now() + timedelta(hours=1),
            exchange='binance',
            market_type='spot',
            reason='Symbol delisted'
        )
        lifecycle_manager._update_availability_windows(delisted_record)
        
        # Check that the window was closed
        windows = lifecycle_manager.get_symbol_availability_windows('BTC/USDT', 'binance', 'spot')
        assert len(windows) == 1
        assert not windows[0].is_active()
        assert windows[0].reason_ended == 'Symbol delisted'
    
    def test_collection_time_windows(self, lifecycle_manager):
        """Test calculation of collection time windows."""
        base_time = datetime.now()
        
        # Create an availability window
        window = SymbolAvailabilityWindow(
            symbol='BTC/USDT',
            start_time=base_time,
            end_time=base_time + timedelta(hours=6),
            exchange='binance',
            market_type='spot'
        )
        
        key = "binance_spot_BTC/USDT"
        lifecycle_manager._availability_windows[key] = [window]
        
        # Test collection windows within availability
        collection_windows = lifecycle_manager.get_collection_time_windows(
            symbol='BTC/USDT',
            exchange='binance',
            start_time=base_time + timedelta(hours=1),
            end_time=base_time + timedelta(hours=5),
            market_type='spot'
        )
        
        assert len(collection_windows) == 1
        assert collection_windows[0][0] == base_time + timedelta(hours=1)
        assert collection_windows[0][1] == base_time + timedelta(hours=5)
        
        # Test collection windows partially outside availability
        collection_windows = lifecycle_manager.get_collection_time_windows(
            symbol='BTC/USDT',
            exchange='binance',
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=8),
            market_type='spot'
        )
        
        assert len(collection_windows) == 1
        assert collection_windows[0][0] == base_time  # Clipped to availability start
        assert collection_windows[0][1] == base_time + timedelta(hours=6)  # Clipped to availability end


class TestDelistingAwareCollector:
    """Test delisting-aware data collection functionality."""
    
    def test_collect_active_symbol(self, delisting_collector, mock_adapter, lifecycle_manager):
        """Test collection of an active symbol."""
        # Mock active symbol status
        with patch.object(lifecycle_manager, 'get_symbol_status') as mock_status:
            mock_status.return_value = SymbolStatusRecord(
                symbol='BTC/USDT',
                status=SymbolStatus.ACTIVE,
                timestamp=datetime.now(),
                exchange='test_exchange',
                market_type='spot'
            )
            
            result = delisting_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='BTC/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            assert result['status'] == 'success'
            assert result['symbol'] == 'BTC/USDT'
            assert not result['data'].empty
            assert result['metadata']['collection_type'] == 'active_full'
    
    def test_collect_delisted_symbol_with_partial_collection(self, delisting_collector, mock_adapter, lifecycle_manager):
        """Test collection of a delisted symbol with partial collection enabled."""
        base_time = datetime.now()
        
        # Mock delisted symbol status
        with patch.object(lifecycle_manager, 'get_symbol_status') as mock_status:
            mock_status.return_value = SymbolStatusRecord(
                symbol='DELIST/USDT',
                status=SymbolStatus.DELISTED,
                timestamp=datetime.now(),
                exchange='test_exchange',
                market_type='spot'
            )
            
            # Mock availability windows (symbol was available before delisting)
            with patch.object(lifecycle_manager, 'get_collection_time_windows') as mock_windows:
                mock_windows.return_value = [
                    (base_time, base_time + timedelta(hours=12))  # Was available for 12 hours
                ]
                
                result = delisting_collector.collect_symbol_data(
                    adapter=mock_adapter,
                    symbol='DELIST/USDT',
                    timeframe='1h',
                    start_time=base_time - timedelta(hours=6),
                    end_time=base_time + timedelta(hours=18)
                )
                
                assert result['status'] == 'partial'
                assert result['symbol'] == 'DELIST/USDT'
                assert not result['data'].empty
                assert result['metadata']['collection_type'] == 'partial_delisted'
                assert len(result['collection_windows']) == 1
    
    def test_collect_delisted_symbol_no_partial_collection(self, lifecycle_manager):
        """Test collection of a delisted symbol with partial collection disabled."""
        delisting_collector = DelistingAwareCollector(
            lifecycle_manager=lifecycle_manager,
            enable_partial_collection=False
        )
        
        mock_adapter = MockExchangeAdapter()
        
        # Mock delisted symbol status
        with patch.object(lifecycle_manager, 'get_symbol_status') as mock_status:
            mock_status.return_value = SymbolStatusRecord(
                symbol='DELIST/USDT',
                status=SymbolStatus.DELISTED,
                timestamp=datetime.now(),
                exchange='test_exchange',
                market_type='spot'
            )
            
            result = delisting_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='DELIST/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            assert result['status'] == 'failed'
            assert 'partial collection is disabled' in result['errors'][0]
    
    def test_collect_suspended_symbol(self, delisting_collector, mock_adapter, lifecycle_manager):
        """Test collection of a suspended symbol."""
        # Mock suspended symbol status
        with patch.object(lifecycle_manager, 'get_symbol_status') as mock_status:
            mock_status.return_value = SymbolStatusRecord(
                symbol='SUSPEND/USDT',
                status=SymbolStatus.SUSPENDED,
                timestamp=datetime.now(),
                exchange='test_exchange',
                market_type='spot'
            )
            
            result = delisting_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='SUSPEND/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            # Suspended symbols should still allow historical data collection
            assert result['status'] == 'success'
            assert result['metadata']['collection_type'] == 'suspended_historical'
    
    def test_ccxt_error_handling(self, delisting_collector, lifecycle_manager):
        """Test handling of CCXT-specific errors."""
        mock_adapter = MockExchangeAdapter()
        
        # Simulate BadSymbol error
        mock_adapter.simulate_symbol_delisting('BADTEST/USDT')
        
        # Mock unknown symbol status (so it tries to collect)
        with patch.object(lifecycle_manager, 'get_symbol_status') as mock_status:
            mock_status.return_value = SymbolStatusRecord(
                symbol='BADTEST/USDT',
                status=SymbolStatus.UNKNOWN,
                timestamp=datetime.now(),
                exchange='test_exchange',
                market_type='spot'
            )
            
            # Mock the mark_symbol_delisted method
            with patch.object(lifecycle_manager, 'mark_symbol_delisted') as mock_mark:
                result = delisting_collector.collect_symbol_data(
                    adapter=mock_adapter,
                    symbol='BADTEST/USDT',
                    timeframe='1h',
                    start_time='2024-01-01',
                    end_time='2024-01-02'
                )
                
                assert result['status'] == 'failed'
                # Should have marked the symbol as delisted
                mock_mark.assert_called_once()
    
    def test_batch_collection_with_mixed_statuses(self, delisting_collector, mock_adapter, lifecycle_manager):
        """Test batch collection with symbols in different states."""
        symbols = ['ACTIVE/USDT', 'DELIST/USDT', 'SUSPEND/USDT']
        
        def mock_status_side_effect(symbol, exchange, market_type):
            if symbol == 'ACTIVE/USDT':
                return SymbolStatusRecord(
                    symbol=symbol, status=SymbolStatus.ACTIVE,
                    timestamp=datetime.now(), exchange=exchange, market_type=market_type
                )
            elif symbol == 'DELIST/USDT':
                return SymbolStatusRecord(
                    symbol=symbol, status=SymbolStatus.DELISTED,
                    timestamp=datetime.now(), exchange=exchange, market_type=market_type
                )
            else:  # SUSPEND/USDT
                return SymbolStatusRecord(
                    symbol=symbol, status=SymbolStatus.SUSPENDED,
                    timestamp=datetime.now(), exchange=exchange, market_type=market_type
                )
        
        with patch.object(lifecycle_manager, 'get_symbol_status', side_effect=mock_status_side_effect):
            # Mock availability windows for delisted symbol
            with patch.object(lifecycle_manager, 'get_collection_time_windows') as mock_windows:
                def mock_windows_side_effect(symbol, exchange, start_time, end_time, market_type):
                    if symbol == 'DELIST/USDT':
                        base_time = datetime.now()
                        return [(base_time, base_time + timedelta(hours=6))]
                    return []
                
                mock_windows.side_effect = mock_windows_side_effect
                
                batch_results = delisting_collector.collect_multiple_symbols(
                    adapter=mock_adapter,
                    symbols=symbols,
                    timeframe='1h',
                    start_time='2024-01-01',
                    end_time='2024-01-02'
                )
                
                # Check batch statistics
                assert batch_results['stats']['total_symbols'] == 3
                assert batch_results['stats']['successful_collections'] >= 2  # Active and suspended
                
                # Check individual results
                results = batch_results['results']
                assert results['ACTIVE/USDT']['status'] == 'success'
                assert results['SUSPEND/USDT']['status'] == 'success'
                
                # Delisted symbol should have partial or failed status depending on availability
                delist_status = results['DELIST/USDT']['status']
                assert delist_status in ['partial', 'failed']


class TestIncrementalManagerWithDelisting:
    """Test incremental update manager with delisting awareness."""
    
    @pytest.mark.asyncio
    async def test_plan_updates_filters_delisted_symbols(self, mock_config, lifecycle_manager):
        """Test that update planning filters out delisted symbols."""
        delisting_collector = DelistingAwareCollector(lifecycle_manager)
        
        manager = IncrementalUpdateManager(
            config=mock_config,
            lifecycle_manager=lifecycle_manager,
            delisting_collector=delisting_collector
        )
        
        # Mock global state with some symbols
        from incremental.update_state import GlobalUpdateState, ExchangeUpdateState, SymbolUpdateState
        
        global_state = GlobalUpdateState()
        exchange_state = ExchangeUpdateState(exchange="binance")
        
        # Create symbol states
        active_symbol = SymbolUpdateState(
            symbol="ACTIVE/USDT",
            exchange="binance",
            timeframe="1h"
        )
        delisted_symbol = SymbolUpdateState(
            symbol="DELIST/USDT",
            exchange="binance",
            timeframe="1h"
        )
        
        exchange_state.symbols["ACTIVE/USDT"] = {"1h": active_symbol}
        exchange_state.symbols["DELIST/USDT"] = {"1h": delisted_symbol}
        global_state.exchanges["binance"] = exchange_state
        
        manager.global_state = global_state
        
        # Mock lifecycle manager responses
        def mock_status_side_effect(symbol, exchange, market_type):
            if symbol == 'ACTIVE/USDT':
                return SymbolStatusRecord(
                    symbol=symbol, status=SymbolStatus.ACTIVE,
                    timestamp=datetime.now(), exchange=exchange, market_type=market_type
                )
            else:  # DELIST/USDT
                return SymbolStatusRecord(
                    symbol=symbol, status=SymbolStatus.DELISTED,
                    timestamp=datetime.now(), exchange=exchange, market_type=market_type
                )
        
        with patch.object(lifecycle_manager, 'get_symbol_status', side_effect=mock_status_side_effect):
            with patch.object(manager.update_planner, 'plan_updates') as mock_plan:
                mock_plan.return_value = []  # Empty plans for simplicity
                
                update_plans = await manager.plan_updates()
                
                # Should have called plan_updates with only the active symbol
                mock_plan.assert_called_once()
                planned_symbols = mock_plan.call_args[0][0]  # First argument is symbol_states list
                
                assert len(planned_symbols) == 1
                assert planned_symbols[0].symbol == "ACTIVE/USDT"
                
                # Check statistics
                assert manager.update_stats['delisted_symbols_skipped'] == 1
    
    @pytest.mark.asyncio
    async def test_execute_update_with_partial_collection(self, mock_config, lifecycle_manager):
        """Test executing updates with partial collection results."""
        delisting_collector = DelistingAwareCollector(lifecycle_manager)
        
        manager = IncrementalUpdateManager(
            config=mock_config,
            lifecycle_manager=lifecycle_manager,
            delisting_collector=delisting_collector
        )
        
        # Create mock adapter
        mock_adapter = MockExchangeAdapter()
        manager.register_exchange_adapter("test_exchange", mock_adapter)
        
        # Create symbol state
        from incremental.update_state import SymbolUpdateState
        from incremental.update_strategy import UpdateDecision
        
        symbol_state = SymbolUpdateState(
            symbol="PARTIAL/USDT",
            exchange="test_exchange",
            timeframe="1h"
        )
        
        update_decision = UpdateDecision(
            should_update=True,
            reason="Test update",
            estimated_data_points=100,
            priority=1.0
        )
        
        # Mock the delisting collector to return partial result
        partial_result = {
            'status': 'partial',
            'data': pd.DataFrame({'close': [100, 101, 102]}, 
                               index=pd.date_range('2024-01-01', periods=3, freq='1H')),
            'collection_windows': [{'start': '2024-01-01', 'end': '2024-01-01 12:00', 'records': 3}],
            'metadata': {'collection_type': 'partial_delisted'}
        }
        
        with patch.object(delisting_collector, 'collect_symbol_data', return_value=partial_result):
            result = await manager._execute_single_update_with_delisting_awareness(
                symbol_state, update_decision, dry_run=False
            )
            
            assert result['success'] is True
            assert result['partial'] is True
            assert result['data_points'] == 3
            assert result['collection_type'] == 'partial_delisted'
            assert len(result['collection_windows']) == 1


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    def test_network_error_retry(self, delisting_collector, lifecycle_manager):
        """Test retry logic for network errors."""
        mock_adapter = Mock(spec=ExchangeAdapter)
        
        # Mock network error on first call, success on second
        def mock_get_ohlcv_side_effect(*args, **kwargs):
            if mock_get_ohlcv_side_effect.call_count == 1:
                if ccxt:
                    raise ccxt.NetworkError("Network timeout")
                else:
                    raise Exception("NetworkError: Network timeout")
            else:
                # Return successful data
                dates = pd.date_range(start='2024-01-01', periods=10, freq='1H')
                return pd.DataFrame({
                    'open': [100.0] * 10,
                    'high': [105.0] * 10,
                    'low': [95.0] * 10,
                    'close': [102.0] * 10,
                    'volume': [1000.0] * 10
                }, index=dates)
        
        mock_get_ohlcv_side_effect.call_count = 0
        
        def increment_call_count(*args, **kwargs):
            mock_get_ohlcv_side_effect.call_count += 1
            return mock_get_ohlcv_side_effect(*args, **kwargs)
        
        mock_adapter.get_ohlcv = Mock(side_effect=increment_call_count)
        mock_adapter.exchange_id = "test_exchange"
        
        # Mock active symbol status
        with patch.object(lifecycle_manager, 'get_symbol_status') as mock_status:
            mock_status.return_value = SymbolStatusRecord(
                symbol='RETRY/USDT',
                status=SymbolStatus.ACTIVE,
                timestamp=datetime.now(),
                exchange='test_exchange',
                market_type='spot'
            )
            
            result = delisting_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='RETRY/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            # Should succeed after retry
            assert result['status'] == 'success'
            assert mock_adapter.get_ohlcv.call_count == 2
    
    def test_rate_limit_backoff(self, delisting_collector, lifecycle_manager):
        """Test exponential backoff for rate limiting."""
        mock_adapter = Mock(spec=ExchangeAdapter)
        mock_adapter.exchange_id = "test_exchange"
        
        # Set very short retry delay for testing
        delisting_collector.retry_delay = 0.01
        delisting_collector.max_retries = 2
        
        # Mock rate limit error
        if ccxt:
            rate_limit_error = ccxt.RateLimitExceeded("Rate limit exceeded")
        else:
            rate_limit_error = Exception("RateLimitExceeded: Rate limit exceeded")
        
        mock_adapter.get_ohlcv = Mock(side_effect=rate_limit_error)
        
        # Mock active symbol status
        with patch.object(lifecycle_manager, 'get_symbol_status') as mock_status:
            mock_status.return_value = SymbolStatusRecord(
                symbol='RATELIMIT/USDT',
                status=SymbolStatus.ACTIVE,
                timestamp=datetime.now(),
                exchange='test_exchange',
                market_type='spot'
            )
            
            import time
            start_time = time.time()
            
            result = delisting_collector.collect_symbol_data(
                adapter=mock_adapter,
                symbol='RATELIMIT/USDT',
                timeframe='1h',
                start_time='2024-01-01',
                end_time='2024-01-02'
            )
            
            end_time = time.time()
            
            # Should fail after retries
            assert result['status'] == 'failed'
            # Should have waited for backoff (very minimal due to short delay)
            assert end_time - start_time >= 0.01  # At least one retry delay
            assert mock_adapter.get_ohlcv.call_count == 3  # Initial + 2 retries


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])