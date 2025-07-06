# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Tests for cryptocurrency universe management functionality.

This module tests the investment universe management system including
symbol discovery, filtering, ranking, and universe maintenance.
"""

import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

try:
    from universe_manager import UniverseManager
    from symbol_discovery import SymbolDiscovery, SymbolInfo
    from universe_filters import (
        VolumeFilter, PriceFilter, AssetFilter, UniverseFilterChain,
        create_filter_chain_from_config
    )
    from config.universe_config import (
        UniverseConfig, FilterConfig, get_universe_config, PREDEFINED_UNIVERSES
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Some dependencies may be missing. Running basic tests only.")


class TestSymbolInfo:
    """Test SymbolInfo dataclass."""
    
    def test_symbol_info_creation(self):
        """Test creating SymbolInfo objects."""
        symbol = SymbolInfo(
            symbol="BTC/USDT",
            base="BTC",
            quote="USDT",
            exchange="binance",
            market_type="spot",
            active=True,
            price=50000.0,
            volume_24h=1000.0,
            volume_usd_24h=50000000.0
        )
        
        assert symbol.symbol == "BTC/USDT"
        assert symbol.base == "BTC"
        assert symbol.quote == "USDT"
        assert symbol.exchange == "binance"
        assert symbol.market_type == "spot"
        assert symbol.active is True
        assert symbol.price == 50000.0
        assert symbol.volume_24h == 1000.0
        assert symbol.volume_usd_24h == 50000000.0
    
    def test_symbol_info_to_dict(self):
        """Test converting SymbolInfo to dictionary."""
        symbol = SymbolInfo(
            symbol="ETH/USDT",
            base="ETH",
            quote="USDT",
            exchange="okx",
            market_type="spot",
            active=True,
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        result = symbol.to_dict()
        
        assert result['symbol'] == "ETH/USDT"
        assert result['base'] == "ETH"
        assert result['quote'] == "USDT"
        assert result['exchange'] == "okx"
        assert result['market_type'] == "spot"
        assert result['active'] is True
        assert result['last_updated'] == "2023-01-01T12:00:00"


class TestUniverseFilters:
    """Test universe filtering functionality."""
    
    def setup_method(self):
        """Set up test data."""
        self.symbols = [
            SymbolInfo(
                symbol="BTC/USDT", base="BTC", quote="USDT", exchange="binance",
                market_type="spot", active=True, price=50000.0, volume_24h=1000.0,
                volume_usd_24h=50000000.0, change_24h=5.0
            ),
            SymbolInfo(
                symbol="ETH/USDT", base="ETH", quote="USDT", exchange="binance",
                market_type="spot", active=True, price=3000.0, volume_24h=2000.0,
                volume_usd_24h=6000000.0, change_24h=-2.0
            ),
            SymbolInfo(
                symbol="ADA/BTC", base="ADA", quote="BTC", exchange="binance",
                market_type="spot", active=True, price=0.0001, volume_24h=500.0,
                volume_usd_24h=500000.0, change_24h=10.0
            ),
            SymbolInfo(
                symbol="DOGE/USDT", base="DOGE", quote="USDT", exchange="binance",
                market_type="spot", active=False, price=0.1, volume_24h=100.0,
                volume_usd_24h=10000.0, change_24h=1.0
            ),
        ]
    
    def test_volume_filter(self):
        """Test volume filtering."""
        filter_obj = VolumeFilter(min_volume_usd_24h=1000000.0)
        result = filter_obj.apply(self.symbols)
        
        # Should filter out DOGE/USDT (volume too low) and ADA/BTC (volume too low)
        assert len(result) == 2
        symbols = [s.symbol for s in result]
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols
    
    def test_price_filter(self):
        """Test price filtering."""
        filter_obj = PriceFilter(min_price=1.0, max_price=10000.0)
        result = filter_obj.apply(self.symbols)
        
        # Should filter out ADA/BTC (price too low) and BTC/USDT (price too high)
        assert len(result) == 2
        symbols = [s.symbol for s in result]
        assert "ETH/USDT" in symbols
        assert "DOGE/USDT" in symbols
    
    def test_asset_filter(self):
        """Test asset filtering."""
        filter_obj = AssetFilter(
            base_assets=["BTC", "ETH"],
            quote_assets=["USDT"]
        )
        result = filter_obj.apply(self.symbols)
        
        # Should only include BTC/USDT and ETH/USDT
        assert len(result) == 2
        symbols = [s.symbol for s in result]
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols
    
    def test_filter_chain(self):
        """Test chaining multiple filters."""
        chain = UniverseFilterChain()
        chain.add_filter(VolumeFilter(min_volume_usd_24h=1000000.0))
        chain.add_filter(AssetFilter(quote_assets=["USDT"]))
        
        result = chain.apply(self.symbols)
        
        # Should only include BTC/USDT and ETH/USDT (high volume + USDT quote)
        assert len(result) == 2
        symbols = [s.symbol for s in result]
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols
    
    def test_create_filter_chain_from_config(self):
        """Test creating filter chain from configuration."""
        config = FilterConfig(
            min_volume_usd_24h=1000000.0,
            quote_assets=["USDT"],
            min_change_24h=3.0
        )
        
        chain = create_filter_chain_from_config(config)
        result = chain.apply(self.symbols)
        
        # Should only include BTC/USDT (meets all criteria)
        assert len(result) == 1
        assert result[0].symbol == "BTC/USDT"


class TestUniverseConfig:
    """Test universe configuration functionality."""
    
    def test_predefined_universes(self):
        """Test predefined universe configurations."""
        assert "top_spot_by_volume" in PREDEFINED_UNIVERSES
        assert "major_cryptocurrencies" in PREDEFINED_UNIVERSES
        assert "perpetual_contracts" in PREDEFINED_UNIVERSES
        
        config = get_universe_config("top_spot_by_volume")
        assert config is not None
        assert config.name == "top_spot_by_volume"
        assert "spot" in config.market_types
        assert config.max_symbols == 100
    
    def test_universe_config_creation(self):
        """Test creating universe configuration."""
        config = UniverseConfig(
            name="test_universe",
            description="Test universe",
            exchanges=["binance", "okx"],
            market_types=["spot"],
            max_symbols=50
        )
        
        assert config.name == "test_universe"
        assert config.description == "Test universe"
        assert config.exchanges == ["binance", "okx"]
        assert config.market_types == ["spot"]
        assert config.max_symbols == 50


class TestSymbolDiscovery:
    """Test symbol discovery functionality."""
    
    def setup_method(self):
        """Set up mock adapters."""
        self.mock_binance = Mock()
        self.mock_okx = Mock()
        
        # Mock symbol lists
        self.mock_binance.get_symbols.return_value = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        self.mock_okx.get_symbols.return_value = ["BTC/USDT", "ETH/USDT", "DOT/USDT"]
        
        # Mock symbol info
        def mock_binance_symbol_info(symbol):
            return {
                'symbol': symbol,
                'base': symbol.split('/')[0],
                'quote': symbol.split('/')[1],
                'active': True,
                'market_type': 'spot'
            }
        
        def mock_okx_symbol_info(symbol):
            return {
                'symbol': symbol,
                'base': symbol.split('/')[0],
                'quote': symbol.split('/')[1],
                'active': True,
                'market_type': 'spot'
            }
        
        self.mock_binance.get_symbol_info.side_effect = mock_binance_symbol_info
        self.mock_okx.get_symbol_info.side_effect = mock_okx_symbol_info
        
        # Mock ticker data
        def mock_ticker(symbol):
            return {
                'last': 50000.0 if 'BTC' in symbol else 3000.0,
                'volume_24h': 1000.0,
                'change_24h': 5.0
            }
        
        self.mock_binance.get_ticker.side_effect = mock_ticker
        self.mock_okx.get_ticker.side_effect = mock_ticker
        
        self.adapters = {
            'binance': self.mock_binance,
            'okx': self.mock_okx
        }
        
        self.discovery = SymbolDiscovery(self.adapters)
    
    def test_discover_symbols(self):
        """Test symbol discovery across exchanges."""
        result = self.discovery.discover_symbols(
            exchanges=['binance', 'okx'],
            market_types=['spot']
        )
        
        assert 'binance' in result
        assert 'okx' in result
        assert len(result['binance']) == 3
        assert len(result['okx']) == 3
        
        # Check symbol info structure
        binance_symbols = result['binance']
        assert all(isinstance(s, SymbolInfo) for s in binance_symbols)
        assert all(s.exchange == 'binance' for s in binance_symbols)
    
    def test_find_common_symbols(self):
        """Test finding symbols common across exchanges."""
        exchange_symbols = self.discovery.discover_symbols(
            exchanges=['binance', 'okx'],
            market_types=['spot']
        )
        
        common = self.discovery.find_common_symbols(exchange_symbols, min_exchanges=2)
        
        # BTC/USDT and ETH/USDT should be common
        assert "BTC/USDT" in common
        assert "ETH/USDT" in common
        assert len(common) == 2


class TestUniverseManager:
    """Test universe manager functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock adapters
        self.mock_binance = Mock()
        self.mock_binance.get_symbols.return_value = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        
        def mock_symbol_info(symbol):
            base_price = 50000.0 if 'BTC' in symbol else 3000.0 if 'ETH' in symbol else 1.0
            return {
                'symbol': symbol,
                'base': symbol.split('/')[0],
                'quote': symbol.split('/')[1],
                'active': True,
                'market_type': 'spot'
            }
        
        def mock_ticker(symbol):
            base_price = 50000.0 if 'BTC' in symbol else 3000.0 if 'ETH' in symbol else 1.0
            return {
                'last': base_price,
                'volume_24h': 1000.0,
                'change_24h': 5.0
            }
        
        self.mock_binance.get_symbol_info.side_effect = mock_symbol_info
        self.mock_binance.get_ticker.side_effect = mock_ticker
        
        adapters = {'binance': self.mock_binance}
        self.manager = UniverseManager(adapters, storage_path=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_universe(self):
        """Test creating a universe."""
        config = UniverseConfig(
            name="test_universe",
            exchanges=["binance"],
            market_types=["spot"],
            max_symbols=2
        )
        
        symbols = self.manager.create_universe(config)
        
        assert len(symbols) <= 2
        assert all(isinstance(s, SymbolInfo) for s in symbols)
        assert "test_universe" in self.manager.list_universes()
    
    def test_get_universe(self):
        """Test retrieving a universe."""
        config = UniverseConfig(
            name="test_universe",
            exchanges=["binance"],
            market_types=["spot"]
        )
        
        created_symbols = self.manager.create_universe(config)
        retrieved_symbols = self.manager.get_universe("test_universe")
        
        assert retrieved_symbols is not None
        assert len(retrieved_symbols) == len(created_symbols)
    
    def test_universe_with_filters(self):
        """Test creating universe with filters."""
        config = UniverseConfig(
            name="filtered_universe",
            exchanges=["binance"],
            market_types=["spot"],
            filters=FilterConfig(
                quote_assets=["USDT"],
                min_volume_usd_24h=1000000.0
            )
        )
        
        symbols = self.manager.create_universe(config)
        
        # All symbols should have USDT as quote
        assert all(s.quote == "USDT" for s in symbols)


if __name__ == "__main__":
    # Run basic tests
    print("Running universe management tests...")
    
    # Test SymbolInfo
    test_symbol_info = TestSymbolInfo()
    test_symbol_info.test_symbol_info_creation()
    test_symbol_info.test_symbol_info_to_dict()
    print("✓ SymbolInfo tests passed")
    
    # Test filters
    test_filters = TestUniverseFilters()
    test_filters.setup_method()
    test_filters.test_volume_filter()
    test_filters.test_price_filter()
    test_filters.test_asset_filter()
    test_filters.test_filter_chain()
    test_filters.test_create_filter_chain_from_config()
    print("✓ Universe filters tests passed")
    
    # Test config
    test_config = TestUniverseConfig()
    test_config.test_predefined_universes()
    test_config.test_universe_config_creation()
    print("✓ Universe config tests passed")
    
    print("All tests passed! ✓")
