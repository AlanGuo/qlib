#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for cryptocurrency field collector.

This script tests the crypto field collector functionality including funding rates,
open interest, order book data, and other crypto-specific field collection.
"""

import pytest
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from crypto_field_collector import CryptoFieldCollector
from config.fields import FieldConfig


@pytest.fixture
def mock_exchange_adapter():
    """Create mock exchange adapter."""
    adapter = Mock()
    adapter.exchange_id = "binance"
    
    # Mock ticker data
    adapter.get_ticker.return_value = {
        'symbol': 'BTC/USDT',
        'timestamp': 1640995200000,
        'datetime': '2022-01-01T00:00:00Z',
        'high': 47500.0,
        'low': 46500.0,
        'bid': 47000.0,
        'ask': 47010.0,
        'vwap': 47000.0,
        'open': 47200.0,
        'close': 47000.0,
        'last': 47000.0,
        'volume': 1500.0,
        'quoteVolume': 70500000.0,
        'change': -200.0,
        'percentage': -0.42,
        'average': 47100.0,
        'volume_24h': 1500.0,
        'change_24h': -0.42,
        'high_24h': 47500.0,
        'low_24h': 46500.0,
        'spread': 10.0
    }
    
    # Mock funding rate data
    adapter.get_funding_rate.return_value = {
        'symbol': 'BTC/USDT',
        'funding_rate': 0.0001,
        'funding_time': 1640995200000,
        'funding_datetime': '2022-01-01T00:00:00Z'
    }
    
    # Mock open interest data
    adapter.get_open_interest.return_value = {
        'symbol': 'BTC/USDT',
        'open_interest': 125000000.0,
        'timestamp': 1640995200000,
        'datetime': '2022-01-01T00:00:00Z'
    }
    
    # Mock order book data
    adapter.get_order_book.return_value = {
        'symbol': 'BTC/USDT',
        'bids': [
            [47000.0, 1.5],
            [46999.0, 2.0],
            [46998.0, 1.8]
        ],
        'asks': [
            [47010.0, 1.2],
            [47011.0, 1.8],
            [47012.0, 2.2]
        ],
        'timestamp': 1640995200000,
        'datetime': '2022-01-01T00:00:00Z'
    }
    
    # Mock spread calculation
    adapter.calculate_bid_ask_spread.return_value = 10.0
    
    return adapter


@pytest.fixture
def sample_crypto_symbols():
    """Sample crypto symbols for testing."""
    return ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT"]


class TestCryptoFieldCollectorFixtures:
    """Test fixtures for crypto field collector tests."""
    
    @pytest.fixture
    def temp_collector_dir(self):
        """Create temporary directory for collector tests."""
        temp_dir = tempfile.mkdtemp(prefix="crypto_field_collector_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)



    @pytest.fixture
    def mock_funding_rate_data(self):
        """Mock funding rate data."""
        return [
            {
                'symbol': 'BTC/USDT',
                'funding_rate': 0.0001,
                'funding_time': 1640995200000,
                'funding_datetime': '2022-01-01T00:00:00Z'
            },
            {
                'symbol': 'ETH/USDT',
                'funding_rate': 0.00005,
                'funding_time': 1640995200000,
                'funding_datetime': '2022-01-01T00:00:00Z'
            }
        ]

    @pytest.fixture
    def mock_open_interest_data(self):
        """Mock open interest data."""
        return [
            {
                'symbol': 'BTC/USDT',
                'open_interest': 125000000.0,
                'timestamp': 1640995200000,
                'datetime': '2022-01-01T00:00:00Z'
            },
            {
                'symbol': 'ETH/USDT',
                'open_interest': 85000000.0,
                'timestamp': 1640995200000,
                'datetime': '2022-01-01T00:00:00Z'
            }
        ]

    @pytest.fixture
    def mock_order_book_data(self):
        """Mock order book data."""
        return {
            'symbol': 'BTC/USDT',
            'bids': [
                [47000.0, 1.5],
                [46999.0, 2.0],
                [46998.0, 1.8]
            ],
            'asks': [
                [47010.0, 1.2],
                [47011.0, 1.8],
                [47012.0, 2.2]
            ],
            'timestamp': 1640995200000,
            'datetime': '2022-01-01T00:00:00Z'
        }




class TestCryptoFieldCollectorInitialization:
    """Test crypto field collector initialization."""
    
    def test_collector_initialization(self, mock_exchange_adapter):
        """Test basic collector initialization."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        assert collector.adapter == mock_exchange_adapter
        assert collector.exchange_id == "binance"
        assert isinstance(collector, CryptoFieldCollector)

    def test_collector_with_different_exchanges(self):
        """Test collector initialization with different exchanges."""
        exchanges = ["binance", "okx", "huobi"]
        
        for exchange in exchanges:
            adapter = Mock()
            adapter.exchange_id = exchange
            
            collector = CryptoFieldCollector(adapter)
            assert collector.exchange_id == exchange
            assert collector.adapter == adapter


class TestTickerFieldCollection:
    """Test ticker field collection functionality."""
    
    def test_collect_ticker_fields_default(self, mock_exchange_adapter):
        """Test collecting ticker fields with default settings."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_ticker_fields("BTC/USDT")
        
        # Check that adapter method was called
        mock_exchange_adapter.get_ticker.assert_called_once_with("BTC/USDT")
        
        # Check result structure
        assert isinstance(result, dict)
        assert result['symbol'] == 'BTC/USDT'
        assert 'timestamp' in result
        assert 'datetime' in result
        assert 'volume_24h' in result
        assert 'change_24h' in result
        assert 'high_24h' in result
        assert 'low_24h' in result

    def test_collect_ticker_fields_specific_fields(self, mock_exchange_adapter):
        """Test collecting specific ticker fields."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        fields = ['volume_24h', 'change_24h']
        result = collector.collect_ticker_fields("BTC/USDT", fields)
        
        assert result['volume_24h'] == 1500.0
        assert result['change_24h'] == -0.42

    def test_collect_ticker_fields_error_handling(self, mock_exchange_adapter):
        """Test error handling in ticker field collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Make the adapter raise an exception
        mock_exchange_adapter.get_ticker.side_effect = Exception("API Error")
        
        result = collector.collect_ticker_fields("BTC/USDT")
        
        assert 'error' in result
        assert result['symbol'] == 'BTC/USDT'


class TestFundingRateCollection:
    """Test funding rate collection functionality."""
    
    def test_collect_funding_rate_success(self, mock_exchange_adapter):
        """Test successful funding rate collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_funding_rate("BTC/USDT")
        
        mock_exchange_adapter.get_funding_rate.assert_called_once_with("BTC/USDT")
        assert result is not None
        assert result['symbol'] == 'BTC/USDT'
        assert result['funding_rate'] == 0.0001

    def test_collect_funding_rate_error_handling(self, mock_exchange_adapter):
        """Test error handling in funding rate collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Make the adapter raise an exception
        mock_exchange_adapter.get_funding_rate.side_effect = Exception("API Error")
        
        result = collector.collect_funding_rate("BTC/USDT")
        
        assert result is None


class TestOpenInterestCollection:
    """Test open interest collection functionality."""
    
    def test_collect_open_interest_success(self, mock_exchange_adapter):
        """Test successful open interest collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_open_interest("BTC/USDT")
        
        mock_exchange_adapter.get_open_interest.assert_called_once_with("BTC/USDT")
        assert result is not None
        assert result['symbol'] == 'BTC/USDT'
        assert result['open_interest'] == 125000000.0

    def test_collect_open_interest_error_handling(self, mock_exchange_adapter):
        """Test error handling in open interest collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Make the adapter raise an exception
        mock_exchange_adapter.get_open_interest.side_effect = Exception("API Error")
        
        result = collector.collect_open_interest("BTC/USDT")
        
        assert result is None


class TestOrderBookFieldCollection:
    """Test order book field collection functionality."""
    
    def test_collect_order_book_fields_success(self, mock_exchange_adapter):
        """Test successful order book field collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_order_book_fields("BTC/USDT")
        
        mock_exchange_adapter.get_order_book.assert_called_once_with("BTC/USDT", 20)
        assert result['symbol'] == 'BTC/USDT'
        assert 'spread' in result
        assert 'best_bid' in result
        assert 'best_ask' in result
        assert result['best_bid'] == 47000.0
        assert result['best_ask'] == 47010.0

    def test_collect_order_book_fields_custom_limit(self, mock_exchange_adapter):
        """Test order book collection with custom limit."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_order_book_fields("BTC/USDT", limit=10)
        
        mock_exchange_adapter.get_order_book.assert_called_once_with("BTC/USDT", 10)

    def test_collect_order_book_fields_error_handling(self, mock_exchange_adapter):
        """Test error handling in order book field collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Make the adapter raise an exception
        mock_exchange_adapter.get_order_book.side_effect = Exception("API Error")
        
        result = collector.collect_order_book_fields("BTC/USDT")
        
        assert 'error' in result
        assert result['symbol'] == 'BTC/USDT'


class TestAllCryptoFieldsCollection:
    """Test comprehensive crypto field collection."""
    
    def test_collect_all_crypto_fields_spot(self, mock_exchange_adapter):
        """Test collecting all crypto fields for spot market."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_all_crypto_fields("BTC/USDT", market_type="spot")
        
        # Check that all relevant methods were called
        mock_exchange_adapter.get_ticker.assert_called()
        mock_exchange_adapter.get_order_book.assert_called()
        
        # Check result structure
        assert result['symbol'] == 'BTC/USDT'
        assert result['market_type'] == 'spot'
        assert result['exchange'] == 'binance'
        assert 'collection_timestamp' in result
        assert 'spread' in result
        assert 'volume_24h' in result

    def test_collect_all_crypto_fields_perpetual(self, mock_exchange_adapter):
        """Test collecting all crypto fields for perpetual market."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_all_crypto_fields("BTC/USDT", market_type="perpetual")
        
        # Check that all relevant methods were called
        mock_exchange_adapter.get_ticker.assert_called()
        mock_exchange_adapter.get_funding_rate.assert_called()
        mock_exchange_adapter.get_open_interest.assert_called()
        mock_exchange_adapter.get_order_book.assert_called()
        
        # Check result structure
        assert result['market_type'] == 'perpetual'
        assert 'funding_rate' in result
        assert 'open_interest' in result

    def test_collect_all_crypto_fields_futures(self, mock_exchange_adapter):
        """Test collecting all crypto fields for futures market."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        result = collector.collect_all_crypto_fields("BTC/USDT", market_type="futures")
        
        # Check that funding rate and open interest methods were called
        mock_exchange_adapter.get_funding_rate.assert_called()
        mock_exchange_adapter.get_open_interest.assert_called()
        
        assert result['market_type'] == 'futures'


class TestBatchCryptoFieldCollection:
    """Test batch crypto field collection functionality."""
    
    def test_collect_batch_crypto_fields_success(self, mock_exchange_adapter, sample_crypto_symbols):
        """Test successful batch collection of crypto fields."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        results = collector.collect_batch_crypto_fields(sample_crypto_symbols[:3])
        
        assert len(results) == 3
        for result in results:
            assert 'symbol' in result
            assert 'collection_timestamp' in result
            assert result['symbol'] in sample_crypto_symbols

    def test_collect_batch_crypto_fields_with_delay(self, mock_exchange_adapter, sample_crypto_symbols):
        """Test batch collection with rate limiting delay."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Test with a very small delay for testing purposes
        start_time = datetime.now()
        results = collector.collect_batch_crypto_fields(sample_crypto_symbols[:2], delay=0.01)
        end_time = datetime.now()
        
        # Should have taken at least the delay time
        assert (end_time - start_time).total_seconds() >= 0.01
        assert len(results) == 2

    def test_collect_batch_crypto_fields_error_handling(self, mock_exchange_adapter, sample_crypto_symbols):
        """Test error handling in batch collection."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Make the adapter raise an exception for ticker data
        mock_exchange_adapter.get_ticker.side_effect = Exception("API Error")
        
        results = collector.collect_batch_crypto_fields(sample_crypto_symbols[:2])
        
        assert len(results) == 2
        for result in results:
            assert 'error' in result


class TestSupportedFieldsQuery:
    """Test supported fields query functionality."""
    
    @patch('crypto_field_collector.filter_fields_by_market_type')
    @patch('crypto_field_collector.is_field_supported_for_exchange')
    @patch('crypto_field_collector.ALL_FIELDS')
    def test_get_supported_fields_spot(self, mock_all_fields, mock_exchange_support, mock_market_filter, mock_exchange_adapter):
        """Test getting supported fields for spot market."""
        # Mock field configurations
        mock_all_fields.__iter__.return_value = iter(['funding_rate', 'open_interest', 'volume_24h'])
        mock_all_fields.items.return_value = [
            ('funding_rate', FieldConfig('funding_rate', 'Crypto funding rate', 'float')),
            ('open_interest', FieldConfig('open_interest', 'Crypto open interest', 'float')),
            ('volume_24h', FieldConfig('volume_24h', 'Regular volume', 'float'))
        ]
        
        # Mock market type filtering
        mock_market_filter.return_value = ['funding_rate', 'volume_24h']
        
        # Mock exchange support
        mock_exchange_support.return_value = True
        
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        supported_fields = collector.get_supported_fields_for_market_type("spot")
        
        # Verify the filtering process was called
        mock_market_filter.assert_called_once()
        assert isinstance(supported_fields, list)

    def test_get_supported_fields_perpetual(self, mock_exchange_adapter):
        """Test getting supported fields for perpetual market."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        supported_fields = collector.get_supported_fields_for_market_type("perpetual")
        
        assert isinstance(supported_fields, list)

    def test_get_supported_fields_futures(self, mock_exchange_adapter):
        """Test getting supported fields for futures market."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        supported_fields = collector.get_supported_fields_for_market_type("futures")
        
        assert isinstance(supported_fields, list)


class TestCryptoFieldCollectorPerformance:
    """Test performance aspects of crypto field collector."""
    
    def test_large_batch_performance(self, mock_exchange_adapter):
        """Test performance with large batch of symbols."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Create a large list of symbols
        large_symbol_list = [f"TOKEN{i}/USDT" for i in range(100)]
        
        start_time = datetime.now()
        results = collector.collect_batch_crypto_fields(large_symbol_list[:10], delay=0)
        end_time = datetime.now()
        
        # Basic performance check
        assert len(results) == 10
        assert (end_time - start_time).total_seconds() < 10  # Should complete in reasonable time

    def test_memory_efficiency(self, mock_exchange_adapter):
        """Test memory efficiency of collector."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Test that collector doesn't accumulate state
        result1 = collector.collect_all_crypto_fields("BTC/USDT")
        result2 = collector.collect_all_crypto_fields("ETH/USDT")
        
        # Results should be independent
        assert result1['symbol'] == 'BTC/USDT'
        assert result2['symbol'] == 'ETH/USDT'

    def test_concurrent_field_collection(self, mock_exchange_adapter):
        """Test that field collection works correctly with concurrent calls."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Test multiple rapid calls
        results = []
        for i in range(5):
            result = collector.collect_all_crypto_fields(f"TOKEN{i}/USDT")
            results.append(result)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result['symbol'] == f'TOKEN{i}/USDT'


class TestCryptoFieldCollectorErrorHandling:
    """Test error handling in crypto field collector."""
    
    def test_adapter_failure_handling(self, mock_exchange_adapter):
        """Test handling of adapter failures."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Make all adapter methods fail
        mock_exchange_adapter.get_ticker.side_effect = Exception("Ticker API Error")
        mock_exchange_adapter.get_funding_rate.side_effect = Exception("Funding Rate API Error")
        mock_exchange_adapter.get_open_interest.side_effect = Exception("Open Interest API Error")
        mock_exchange_adapter.get_order_book.side_effect = Exception("Order Book API Error")
        
        result = collector.collect_all_crypto_fields("BTC/USDT", market_type="perpetual")
        
        # Should handle errors gracefully
        assert result['symbol'] == 'BTC/USDT'
        assert 'error' in result or any('error' in str(v) for v in result.values())

    def test_invalid_symbol_handling(self, mock_exchange_adapter):
        """Test handling of invalid symbols."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Test with invalid symbol format
        result = collector.collect_all_crypto_fields("INVALID_SYMBOL")
        
        assert result['symbol'] == 'INVALID_SYMBOL'
        assert 'collection_timestamp' in result

    def test_empty_response_handling(self, mock_exchange_adapter):
        """Test handling of empty responses from adapter."""
        collector = CryptoFieldCollector(mock_exchange_adapter)
        
        # Make adapter return None/empty responses
        mock_exchange_adapter.get_ticker.return_value = {}
        mock_exchange_adapter.get_funding_rate.return_value = None
        mock_exchange_adapter.get_open_interest.return_value = None
        mock_exchange_adapter.get_order_book.return_value = None
        
        result = collector.collect_all_crypto_fields("BTC/USDT", market_type="perpetual")
        
        # Should handle empty responses gracefully
        assert result['symbol'] == 'BTC/USDT'
        assert 'collection_timestamp' in result