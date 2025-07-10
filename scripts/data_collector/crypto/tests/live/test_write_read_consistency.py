#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Live test for write-read consistency validation.
This test runs after data collection to validate storage integrity.
"""

import pytest
import sys
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Add crypto collector to path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))

@pytest.fixture
def realistic_crypto_data():
    """Generate realistic cryptocurrency data for different scenarios."""
    scenarios = {
        'btc_daily_2020': {
            'periods': 366,
            'freq': 'D',
            'base_price': 7200.0,
            'final_price': 28875.0,
            'volatility': 0.05
        },
        'eth_hourly_week': {
            'periods': 168,
            'freq': 'H', 
            'base_price': 130.0,
            'final_price': 750.0,
            'volatility': 0.04
        },
        'small_cap_coin': {
            'periods': 24,
            'freq': 'H',
            'base_price': 0.000123,  # Very small price
            'final_price': 0.000456,
            'volatility': 0.08
        }
    }
    
    result = {}
    for scenario_name, config in scenarios.items():
        dates = pd.date_range(start='2020-01-01', periods=config['periods'], freq=config['freq'])
        
        # Create realistic price progression
        price_ratio = config['final_price'] / config['base_price']
        growth_rate = (price_ratio ** (1/config['periods'])) - 1
        
        prices = []
        current_price = config['base_price']
        
        for i in range(config['periods']):
            # Add trend growth
            current_price *= (1 + growth_rate)
            
            # Add realistic volatility
            volatility_change = np.random.normal(0, config['volatility'])
            current_price *= (1 + volatility_change)
            
            # Ensure price doesn't go negative
            current_price = max(current_price, config['base_price'] * 0.01)
            prices.append(current_price)
        
        # Create OHLCV data
        data = pd.DataFrame({
            'datetime': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.02))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.02))) for p in prices],
            'close': [p * (1 + np.random.normal(0, 0.01)) for p in prices],
            'volume': np.random.uniform(100000, 10000000, config['periods'])
        })
        
        # Ensure OHLC relationships
        data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
        data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
        
        result[scenario_name] = data
    
    return result


class TestWriteReadConsistency:
    """Test write-read consistency for live data collection scenarios."""
    
    def test_storage_manager_cli_consistency(self, realistic_crypto_data):
        """Test that StorageManager and CLI read/write are consistent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                from storage_manager import StorageManager
                from cli import CryptoDataCLI
            except ImportError:
                pytest.skip("Cannot import crypto collector modules")
            
            storage = StorageManager(temp_dir)
            cli = CryptoDataCLI()
            
            for scenario_name, test_data in realistic_crypto_data.items():
                print(f"  Testing {scenario_name} ({len(test_data)} records)...")
                
                # Convert to float64 (the expected storage format)
                ohlcv_data = test_data[['open', 'high', 'low', 'close', 'volume']].copy().astype(np.float64)
                
                # Store data using storage manager
                symbol = f"TEST{scenario_name.upper()}"
                timeframe = "1d"
                
                for field in ['open', 'high', 'low', 'close', 'volume']:
                    field_data = ohlcv_data[field]
                    storage._store_binary_field(field, field_data, symbol, timeframe)
                
                # Read back using CLI and validate
                for field in ['open', 'high', 'low', 'close', 'volume']:
                    field_file = Path(temp_dir) / symbol / timeframe / f"{field}.bin"
                    
                    assert field_file.exists(), f"Binary file not created for {scenario_name}/{field}"
                    
                    # Read using CLI method
                    read_data = cli._load_binary_field(field_file)
                    original_data = ohlcv_data[field].values
                    
                    # Validation checks that would catch the original corruption
                    assert len(read_data) == len(original_data), \
                        f"{scenario_name}/{field}: Length mismatch {len(read_data)} != {len(original_data)}"
                    
                    assert np.all(read_data >= 0), \
                        f"{scenario_name}/{field}: Negative values detected: min={np.min(read_data)}"
                    
                    assert np.all(read_data < 1e15), \
                        f"{scenario_name}/{field}: Astronomical values detected: max={np.max(read_data)}"
                    
                    assert not np.any(np.isnan(read_data)), \
                        f"{scenario_name}/{field}: NaN values detected"
                    
                    assert not np.any(np.isinf(read_data)), \
                        f"{scenario_name}/{field}: Infinite values detected"
                    
                    # Test data integrity with high precision
                    np.testing.assert_allclose(read_data, original_data, rtol=1e-12, 
                                             err_msg=f"{scenario_name}/{field}: Data corruption detected")
                    
                    print(f"    ✅ {scenario_name}/{field}: {len(read_data)} values validated")

    def test_real_collection_data_integrity(self):
        """Test integrity of actually collected data."""
        crypto_data_dir = Path("/Users/alanguo/Projects/qlib/crypto_data/core")
        
        if not crypto_data_dir.exists():
            pytest.skip("No collected crypto data found")
        
        try:
            from cli import CryptoDataCLI
        except ImportError:
            pytest.skip("Cannot import CLI module")
        
        cli = CryptoDataCLI()
        
        # Find collected data
        timeframe_dirs = [d for d in crypto_data_dir.iterdir() if d.is_dir()]
        
        for timeframe_dir in timeframe_dirs:
            timeframe = timeframe_dir.name
            symbol_dirs = [d for d in timeframe_dir.iterdir() if d.is_dir() and d.name != "calendars"]
            
            for symbol_dir in symbol_dirs[:3]:  # Test first 3 symbols to avoid long test times
                symbol = symbol_dir.name
                print(f"  Validating {symbol} {timeframe}...")
                
                # Check each OHLCV field
                for field in ['open', 'high', 'low', 'close', 'volume']:
                    field_file = symbol_dir / f"{field}.bin"
                    
                    if field_file.exists():
                        try:
                            data = cli._load_binary_field(field_file)
                            
                            if len(data) > 0:
                                # Validation checks
                                assert not np.any(np.isnan(data)), \
                                    f"{symbol}/{timeframe}/{field}: Contains NaN values"
                                
                                assert not np.any(np.isinf(data)), \
                                    f"{symbol}/{timeframe}/{field}: Contains infinite values"
                                
                                assert np.all(data >= 0), \
                                    f"{symbol}/{timeframe}/{field}: Contains negative values: min={np.min(data)}"
                                
                                # Price reasonableness checks
                                if field in ['open', 'high', 'low', 'close']:
                                    assert np.all(data < 1000000), \
                                        f"{symbol}/{timeframe}/{field}: Unreasonably high prices: max={np.max(data)}"
                                    
                                    assert np.all(data > 0.000001), \
                                        f"{symbol}/{timeframe}/{field}: Unreasonably low prices: min={np.min(data)}"
                                
                                print(f"    ✅ {symbol}/{timeframe}/{field}: {len(data)} values OK")
                        
                        except Exception as e:
                            pytest.fail(f"Failed to read {symbol}/{timeframe}/{field}: {e}")
                    else:
                        print(f"    ⚠️  {symbol}/{timeframe}/{field}: File not found")

    def test_calendar_data_consistency(self):
        """Test that calendar entries match data counts."""
        crypto_data_dir = Path("/Users/alanguo/Projects/qlib/crypto_data/core")
        
        if not crypto_data_dir.exists():
            pytest.skip("No collected crypto data found")
        
        try:
            from cli import CryptoDataCLI
        except ImportError:
            pytest.skip("Cannot import CLI module")
        
        cli = CryptoDataCLI()
        
        # Check each timeframe
        for timeframe_dir in crypto_data_dir.iterdir():
            if not timeframe_dir.is_dir():
                continue
                
            timeframe = timeframe_dir.name
            calendar_file = timeframe_dir / "calendars" / f"{timeframe}.txt"
            
            if calendar_file.exists():
                # Read calendar
                with open(calendar_file, 'r') as f:
                    calendar_lines = [line.strip() for line in f if line.strip() and '→' in line]
                
                calendar_count = len(calendar_lines)
                print(f"  Calendar {timeframe}: {calendar_count} entries")
                
                # Check symbol data counts match calendar
                symbol_dirs = [d for d in timeframe_dir.iterdir() 
                              if d.is_dir() and d.name != "calendars"]
                
                for symbol_dir in symbol_dirs[:2]:  # Check first 2 symbols
                    symbol = symbol_dir.name
                    
                    # Check close price data count
                    close_file = symbol_dir / "close.bin"
                    if close_file.exists():
                        data = cli._load_binary_field(close_file)
                        data_count = len(data)
                        
                        assert data_count == calendar_count, \
                            f"{symbol}/{timeframe}: Data count {data_count} != calendar count {calendar_count}"
                        
                        print(f"    ✅ {symbol}: {data_count} records match calendar")

    def test_ohlc_relationships(self):
        """Test that OHLC relationships are maintained in stored data."""
        crypto_data_dir = Path("/Users/alanguo/Projects/qlib/crypto_data/core")
        
        if not crypto_data_dir.exists():
            pytest.skip("No collected crypto data found")
        
        try:
            from cli import CryptoDataCLI
        except ImportError:
            pytest.skip("Cannot import CLI module")
        
        cli = CryptoDataCLI()
        
        # Test OHLC relationships for collected data
        for timeframe_dir in crypto_data_dir.iterdir():
            if not timeframe_dir.is_dir():
                continue
                
            timeframe = timeframe_dir.name
            symbol_dirs = [d for d in timeframe_dir.iterdir() 
                          if d.is_dir() and d.name != "calendars"]
            
            for symbol_dir in symbol_dirs[:2]:  # Test first 2 symbols
                symbol = symbol_dir.name
                
                # Load OHLC data
                ohlc_data = {}
                for field in ['open', 'high', 'low', 'close']:
                    field_file = symbol_dir / f"{field}.bin"
                    if field_file.exists():
                        ohlc_data[field] = cli._load_binary_field(field_file)
                
                if len(ohlc_data) == 4:  # All OHLC fields present
                    # Check lengths match
                    lengths = [len(data) for data in ohlc_data.values()]
                    assert all(l == lengths[0] for l in lengths), \
                        f"{symbol}/{timeframe}: OHLC field lengths don't match"
                    
                    # Check OHLC relationships
                    for i in range(min(100, lengths[0])):  # Check first 100 records
                        o, h, l, c = [ohlc_data[field][i] for field in ['open', 'high', 'low', 'close']]
                        
                        assert h >= max(o, c), \
                            f"{symbol}/{timeframe} record {i}: High {h} < max(open={o}, close={c})"
                        
                        assert l <= min(o, c), \
                            f"{symbol}/{timeframe} record {i}: Low {l} > min(open={o}, close={c})"
                    
                    print(f"    ✅ {symbol}/{timeframe}: OHLC relationships valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])