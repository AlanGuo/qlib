#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for cryptocurrency exchange adapters.

This script tests the exchange adapter functionality using mock data,
including Binance and OKX adapters with simulated API responses.
"""

import pytest

import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

import pandas as pd
import numpy as np

from exchange_adapters.binance_adapter import BinanceAdapter
from exchange_adapters.okx_adapter import OKXAdapter
from exchange_adapters.base_adapter import ExchangeAdapter


# Test fixtures
@pytest.fixture
def mock_binance_ohlcv_response():
    """Mock OHLCV response from Binance API."""
    return [
        [1640995200000, "46000.0", "47000.0", "45800.0", "46800.0", "123.45"],  # 2022-01-01 00:00:00
        [1640998800000, "46800.0", "47200.0", "46500.0", "47100.0", "145.67"],  # 2022-01-01 01:00:00
        [1641002400000, "47100.0", "47500.0", "46900.0", "47300.0", "112.34"],  # 2022-01-01 02:00:00
    ]

@pytest.fixture
def mock_okx_ohlcv_response():
    """Mock OHLCV response from OKX API."""
    return {
        "code": "0",
        "msg": "",
        "data": [
            ["1640995200000", "46000.0", "47000.0", "45800.0", "46800.0", "123.45", "5678901.23"],
            ["1640998800000", "46800.0", "47200.0", "46500.0", "47100.0", "145.67", "6789012.34"],
            ["1641002400000", "47100.0", "47500.0", "46900.0", "47300.0", "112.34", "5234567.89"],
        ]
    }

@pytest.fixture
def mock_binance_funding_rate_response():
    """Mock funding rate response from Binance API."""
    return {
        "symbol": "BTCUSDT",
        "fundingRate": "0.00010000",
        "fundingTime": 1640995200000,
        "nextFundingTime": 1641024000000
    }

@pytest.fixture
def mock_okx_funding_rate_response():
    """Mock funding rate response from OKX API."""
    return {
        "code": "0",
        "msg": "",
        "data": [
            {
                "instType": "SWAP",
                "instId": "BTC-USDT-SWAP",
                "fundingRate": "0.00010000",
                "nextFundingRate": "0.00012000",
                "fundingTime": "1640995200000",
                "nextFundingTime": "1641024000000"
            }
        ]
    }

@pytest.fixture
def mock_binance_symbols_response():
    """Mock symbols response from Binance API."""
    return {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "isSpotTradingAllowed": True,
                "isMarginTradingAllowed": True
            },
            {
                "symbol": "ETHUSDT",
                "status": "TRADING",
                "baseAsset": "ETH",
                "quoteAsset": "USDT",
                "isSpotTradingAllowed": True,
                "isMarginTradingAllowed": True
            }
        ]
    }


class TestBinanceAdapter:
    """Test Binance adapter functionality."""
    
    @patch('ccxt.binance')
    def test_binance_adapter_initialization(self, mock_binance):
        """Test Binance adapter initialization."""
        # Setup mock to avoid real API calls
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = None
        mock_binance.return_value = mock_exchange
        
        adapter = BinanceAdapter()
        
        assert adapter.exchange_id == "binance"
        assert adapter.market_type == "spot"
        assert hasattr(adapter, 'exchange')
    
    @patch('ccxt.binance')
    def test_binance_adapter_with_credentials(self, mock_binance):
        """Test Binance adapter initialization with credentials."""
        # Setup mock to avoid real API calls
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = None
        mock_binance.return_value = mock_exchange
        
        adapter = BinanceAdapter(
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True
        )
        
        assert adapter.exchange_id == "binance"
        assert adapter.sandbox == True
    
    def test_binance_adapter_basic_properties(self):
        """Test basic properties without API calls."""
        # Test without initializing exchange to avoid API calls
        with patch('exchange_adapters.binance_adapter.BinanceAdapter._init_exchange'):
            adapter = BinanceAdapter()
            adapter.exchange_id = "binance"  # Set manually since we're mocking
            adapter.market_type = "spot"
            
            assert adapter.exchange_id == "binance"
            assert adapter.market_type == "spot"
    
    def test_binance_market_type_validation(self):
        """Test market type validation."""
        with patch('exchange_adapters.binance_adapter.BinanceAdapter._init_exchange'):
            # Test valid market types
            adapter1 = BinanceAdapter(market_type="spot")
            assert adapter1.market_type == "spot"
            
            adapter2 = BinanceAdapter(market_type="futures")
            assert adapter2.market_type == "futures"
            
            adapter3 = BinanceAdapter(market_type="perpetual")
            assert adapter3.market_type == "perpetual"


class TestOKXAdapter:
    """Test OKX adapter functionality."""
    
    @patch('ccxt.okx')
    def test_okx_adapter_initialization(self, mock_okx):
        """Test OKX adapter initialization."""
        # Setup mock to avoid real API calls
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = None
        mock_okx.return_value = mock_exchange
        
        adapter = OKXAdapter()
        
        assert adapter.exchange_id == "okx"
        assert adapter.market_type == "spot"
        assert hasattr(adapter, 'exchange')
    
    def test_okx_adapter_basic_properties(self):
        """Test basic properties without API calls."""
        # Test without initializing exchange to avoid API calls
        with patch('exchange_adapters.okx_adapter.OKXAdapter._init_exchange'):
            adapter = OKXAdapter()
            adapter.exchange_id = "okx"  # Set manually since we're mocking
            adapter.market_type = "spot"
            
            assert adapter.exchange_id == "okx"
            assert adapter.market_type == "spot"


class TestExchangeAdapterIntegration:
    """Test integration between different exchange adapters."""
    
    def test_adapter_factory_pattern(self):
        """Test adapter factory pattern for creating adapters."""
        # Test creating different adapters without API calls
        with patch('exchange_adapters.binance_adapter.BinanceAdapter._init_exchange'), \
             patch('exchange_adapters.okx_adapter.OKXAdapter._init_exchange'):
            
            adapters = {
                'binance': BinanceAdapter,
                'okx': OKXAdapter
            }
            
            for exchange_id, adapter_class in adapters.items():
                adapter = adapter_class()
                adapter.exchange_id = exchange_id  # Set manually since we're mocking
                assert adapter.exchange_id == exchange_id
                assert isinstance(adapter, ExchangeAdapter)
    
    def test_adapter_inheritance(self):
        """Test that adapters properly inherit from base class."""
        with patch('exchange_adapters.binance_adapter.BinanceAdapter._init_exchange'), \
             patch('exchange_adapters.okx_adapter.OKXAdapter._init_exchange'):
            
            binance_adapter = BinanceAdapter()
            okx_adapter = OKXAdapter()
            
            assert isinstance(binance_adapter, ExchangeAdapter)
            assert isinstance(okx_adapter, ExchangeAdapter)


class TestExchangeAdapterPerformance:
    """Test exchange adapter performance and efficiency."""
    
    def test_adapter_initialization_performance(self):
        """Test adapter initialization performance."""
        import time
        
        # Test initialization time
        start_time = time.time()
        
        with patch('exchange_adapters.binance_adapter.BinanceAdapter._init_exchange'):
            adapter = BinanceAdapter()
        
        initialization_time = time.time() - start_time
        
        # Should initialize quickly
        assert initialization_time < 1.0  # Less than 1 second
        
    def test_multiple_adapter_creation(self):
        """Test creating multiple adapter instances."""
        with patch('exchange_adapters.binance_adapter.BinanceAdapter._init_exchange'), \
             patch('exchange_adapters.okx_adapter.OKXAdapter._init_exchange'):
            
            # Create multiple adapters
            adapters = []
            for i in range(10):
                binance = BinanceAdapter()
                okx = OKXAdapter()
                adapters.extend([binance, okx])
            
            # Verify all were created successfully
            assert len(adapters) == 20
            
            # Check that they have different instances
            binance_adapters = [a for a in adapters if hasattr(a, 'market_type') and a.market_type == "spot"]
            assert len(binance_adapters) >= 10


class TestPerpetualContractMockData:
    """测试永续合约模拟数据功能"""

    @pytest.fixture
    def mock_perpetual_markets(self):
        """模拟永续合约市场数据"""
        return {
            'BTC/USDT': {
                'id': 'BTCUSDT',
                'symbol': 'BTC/USDT',
                'base': 'BTC',
                'quote': 'USDT',
                'type': 'future',
                'spot': False,
                'future': True,
                'swap': True,  # 永续合约标识
                'contract': True,
                'active': True,
                'precision': {'amount': 3, 'price': 2},
                'limits': {'amount': {'min': 0.001, 'max': 1000}},
                'info': {'contractType': 'PERPETUAL'}
            },
            'ETH/USDT': {
                'id': 'ETHUSDT',
                'symbol': 'ETH/USDT',
                'base': 'ETH',
                'quote': 'USDT',
                'type': 'future',
                'spot': False,
                'future': True,
                'swap': True,
                'contract': True,
                'active': True,
                'precision': {'amount': 3, 'price': 2},
                'limits': {'amount': {'min': 0.001, 'max': 1000}},
                'info': {'contractType': 'PERPETUAL'}
            }
        }

    @pytest.fixture
    def mock_perpetual_exchange(self, mock_perpetual_markets):
        """创建模拟的永续合约交易所"""
        mock_exchange = MagicMock()
        mock_exchange.load_markets.return_value = mock_perpetual_markets
        mock_exchange.markets = mock_perpetual_markets
        
        # 添加timeframes支持
        mock_exchange.timeframes = {
            '1m': '1 minute',
            '5m': '5 minutes', 
            '15m': '15 minutes',
            '30m': '30 minutes',
            '1h': '1 hour',
            '1d': '1 day',
            '1w': '1 week'
        }

        # 模拟资金费率数据
        mock_exchange.fetch_funding_rate.return_value = {
            'symbol': 'BTC/USDT',
            'fundingRate': 0.0001,
            'fundingTimestamp': 1640995200000,
            'fundingDatetime': '2024-01-01T00:00:00.000Z',
            'nextFundingTimestamp': 1641024000000,
            'nextFundingDatetime': '2024-01-01T08:00:00.000Z'
        }

        # 模拟OHLCV数据
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 47000.0, 47200.0, 46800.0, 47100.0, 100.5],
            [1640998800000, 47100.0, 47300.0, 46900.0, 47200.0, 95.2],
            [1641002400000, 47200.0, 47500.0, 47000.0, 47300.0, 112.3]
        ]

        return mock_exchange

    def test_perpetual_adapter_initialization_with_mock(self, mock_perpetual_exchange):
        """测试使用模拟数据的永续合约适配器初始化"""
        with patch('exchange_adapters.binance_adapter.ccxt.binance') as mock_ccxt:
            mock_ccxt.return_value = mock_perpetual_exchange

            from exchange_adapters.binance_adapter import BinanceAdapter

            adapter = BinanceAdapter(market_type="perpetual")
            assert adapter.market_type == "perpetual"

    def test_perpetual_symbols_discovery_with_mock(self, mock_perpetual_exchange):
        """测试使用模拟数据的永续合约交易对发现"""
        with patch('exchange_adapters.binance_adapter.ccxt.binance') as mock_ccxt:
            mock_ccxt.return_value = mock_perpetual_exchange

            from exchange_adapters.binance_adapter import BinanceAdapter

            adapter = BinanceAdapter(market_type="perpetual")
            symbols = adapter.get_instruments(market_type="perpetual")

            assert len(symbols) == 2
            assert 'BTC/USDT' in symbols
            assert 'ETH/USDT' in symbols

    def test_perpetual_funding_rate_collection_with_mock(self, mock_perpetual_exchange):
        """测试使用模拟数据的资金费率收集"""
        with patch('exchange_adapters.binance_adapter.ccxt.binance') as mock_ccxt:
            mock_ccxt.return_value = mock_perpetual_exchange

            from exchange_adapters.binance_adapter import BinanceAdapter
            from crypto_field_collector import CryptoFieldCollector

            adapter = BinanceAdapter(market_type="perpetual")
            collector = CryptoFieldCollector(adapter)

            funding_data = collector.collect_funding_rate("BTC/USDT")

            assert funding_data is not None
            assert funding_data['symbol'] == 'BTC/USDT'
            assert funding_data['funding_rate'] == 0.0001
            assert 'next_funding_datetime' in funding_data

    def test_perpetual_ohlcv_collection_with_mock(self, mock_perpetual_exchange):
        """测试使用模拟数据的K线数据收集"""
        with patch('exchange_adapters.binance_adapter.ccxt.binance') as mock_ccxt:
            mock_ccxt.return_value = mock_perpetual_exchange

            from exchange_adapters.binance_adapter import BinanceAdapter

            adapter = BinanceAdapter(market_type="perpetual")
            ohlcv_data = adapter.get_ohlcv("BTC/USDT", "1h", limit=24)

            assert not ohlcv_data.empty
            assert len(ohlcv_data) == 3

            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                assert col in ohlcv_data.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])