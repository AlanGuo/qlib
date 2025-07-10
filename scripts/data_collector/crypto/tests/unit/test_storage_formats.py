#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Pytest tests for storage formats and data serialization.
"""

import pytest
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

@pytest.fixture
def sample_data():
    """Create sample data for storage testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')

    data = pd.DataFrame({
        'datetime': dates,
        'open': np.random.uniform(45000, 55000, 100),
        'high': np.random.uniform(46000, 56000, 100),
        'low': np.random.uniform(44000, 54000, 100),
        'close': np.random.uniform(45000, 55000, 100),
        'volume': np.random.uniform(100, 10000, 100),
        'volume_quote': np.random.uniform(1000000, 100000000, 100),
        'funding_rate': np.random.uniform(-0.001, 0.001, 100),
        'open_interest': np.random.uniform(1000000, 10000000, 100)
    })

    # Ensure OHLC relationships
    data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
    data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))

    return data


class TestStorageImports:
    """Test basic storage dependencies."""

    def test_storage_dependencies(self):
        """Test that storage dependencies are available."""
        # Test basic file operations
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.csv"
            test_data = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
            test_data.to_csv(test_file, index=False)
            loaded = pd.read_csv(test_file)
            assert len(loaded) == 3, "Basic file I/O failed"

class TestCSVStorage:
    """Test CSV storage format."""

    def test_csv_save_and_load(self, sample_data):
        """Test CSV save and load functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test saving data to CSV
            symbol = "BTCUSDT"
            timeframe = "1h"
            csv_file = Path(temp_dir) / f"{symbol}_{timeframe}.csv"

            sample_data.to_csv(csv_file, index=False)

            # Test loading data
            loaded_data = pd.read_csv(csv_file)

            assert loaded_data is not None, "Failed to load CSV data"
            assert len(loaded_data) == len(sample_data), f"Data length mismatch: {len(loaded_data)} != {len(sample_data)}"

            # Test data integrity
            for col in ['open', 'high', 'low', 'close', 'volume']:
                assert col in loaded_data.columns, f"Missing column: {col}"

            # Test data types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                assert pd.api.types.is_numeric_dtype(loaded_data[col]), f"Column {col} is not numeric after CSV round-trip"

class TestParquetStorage:
    """Test Parquet storage format."""

    def test_parquet_save_and_load(self, sample_data):
        """Test Parquet save and load functionality."""
        # Check if pyarrow is available for parquet support
        pytest.importorskip("pyarrow", reason="PyArrow not available")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test saving data to Parquet
            symbol = "ETHUSDT"
            timeframe = "1h"
            parquet_file = Path(temp_dir) / f"{symbol}_{timeframe}.parquet"

            sample_data.to_parquet(parquet_file, index=False)

            # Test loading data
            loaded_data = pd.read_parquet(parquet_file)

            assert loaded_data is not None, "Failed to load Parquet data"
            assert len(loaded_data) == len(sample_data), f"Data length mismatch: {len(loaded_data)} != {len(sample_data)}"

            # Test data integrity
            for col in ['open', 'high', 'low', 'close', 'volume']:
                assert col in loaded_data.columns, f"Missing column: {col}"
                assert pd.api.types.is_numeric_dtype(loaded_data[col]), f"Column {col} is not numeric after Parquet round-trip"

class TestQlibFormat:
    """Test Qlib-compatible data format."""

    def test_qlib_format_compatibility(self, sample_data):
        """Test Qlib format compatibility."""
        # Test that we can create datetime index (required for Qlib)
        test_data = sample_data.copy()
        if 'datetime' in test_data.columns:
            test_data['datetime'] = pd.to_datetime(test_data['datetime'])
            test_data.set_index('datetime', inplace=True)

        # Test required columns for Qlib
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            assert col in test_data.columns, f"Missing required Qlib column: {col}"


class TestBinaryDataFormat:
    """Test binary data format reading and writing consistency."""

    def test_binary_storage_consistency(self, sample_data):
        """Test that binary storage and reading are consistent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from pathlib import Path
            import sys
            
            # Add crypto collector to path
            crypto_path = Path(__file__).parent.parent.parent
            if str(crypto_path) not in sys.path:
                sys.path.insert(0, str(crypto_path))
            
            try:
                from storage_manager import StorageManager
                from cli import CryptoDataCLI
            except ImportError:
                pytest.skip("Cannot import crypto collector modules")
            
            # Test float64 data storage and retrieval
            test_data = sample_data[['open', 'high', 'low', 'close', 'volume']].copy()
            test_data = test_data.astype(np.float64)
            
            # Use temporary storage for testing
            storage = StorageManager(temp_dir)
            
            # Store data using storage manager
            for field in ['open', 'high', 'low', 'close', 'volume']:
                field_data = test_data[field]
                storage._store_binary_field(field, field_data, "test_symbol", "1d")
            
            # Create CLI instance for reading
            cli = CryptoDataCLI()
            
            # Test reading each field
            for field in ['open', 'high', 'low', 'close', 'volume']:
                field_file = Path(temp_dir) / "test_symbol" / "1d" / f"{field}.bin"
                if field_file.exists():
                    # Read using CLI method
                    read_data = cli._load_binary_field(field_file)
                    original_data = test_data[field].values
                    
                    # Verify data integrity
                    assert len(read_data) == len(original_data), f"Length mismatch for {field}: {len(read_data)} != {len(original_data)}"
                    
                    # Check for reasonable values (not astronomical)
                    max_reasonable_price = 1000000  # $1M max reasonable crypto price
                    min_reasonable_price = 0.001    # $0.001 min reasonable crypto price
                    
                    if field in ['open', 'high', 'low', 'close']:
                        assert np.all(read_data > min_reasonable_price), f"Found unreasonably low prices in {field}: min={np.min(read_data)}"
                        assert np.all(read_data < max_reasonable_price), f"Found unreasonably high prices in {field}: max={np.max(read_data)}"
                    
                    # Check for negative values where inappropriate
                    if field in ['open', 'high', 'low', 'close', 'volume']:
                        assert np.all(read_data >= 0), f"Found negative values in {field}: min={np.min(read_data)}"
                    
                    # Check for NaN values
                    assert not np.any(np.isnan(read_data)), f"Found NaN values in {field}"
                    
                    # Check for infinite values
                    assert not np.any(np.isinf(read_data)), f"Found infinite values in {field}"
                    
                    # Verify approximate equality with original data (allowing for float precision)
                    np.testing.assert_allclose(read_data, original_data, rtol=1e-10, 
                                             err_msg=f"Data corruption detected in {field}")

    def test_data_type_consistency(self, sample_data):
        """Test that data types remain consistent through storage pipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            from pathlib import Path
            import sys
            
            # Add crypto collector to path
            crypto_path = Path(__file__).parent.parent.parent
            if str(crypto_path) not in sys.path:
                sys.path.insert(0, str(crypto_path))
            
            try:
                from storage_manager import StorageManager
            except ImportError:
                pytest.skip("Cannot import storage_manager")
            
            storage = StorageManager(temp_dir)
            
            # Test different data types
            test_data = pd.DataFrame({
                'float64_field': np.array([1.1, 2.2, 3.3], dtype=np.float64),
                'float32_field': np.array([1.1, 2.2, 3.3], dtype=np.float32),
                'int64_field': np.array([1, 2, 3], dtype=np.int64)
            })
            
            # Store and verify each field maintains proper type
            for field, data in test_data.items():
                # Store the field
                storage._store_binary_field(field, data, "test_symbol", "1d")
                
                # Verify file was created
                field_file = Path(temp_dir) / "test_symbol" / "1d" / f"{field}.bin"
                assert field_file.exists(), f"Binary file not created for {field}"
                
                # Read raw binary data
                raw_data = np.fromfile(field_file, dtype=np.float64)
                
                # Verify data integrity
                assert len(raw_data) == len(data), f"Length mismatch for {field}"
                np.testing.assert_allclose(raw_data, data.astype(np.float64), rtol=1e-10)

    def test_calendar_data_count_consistency(self, sample_data):
        """Test that data counts match calendar expectations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a calendar file
            calendar_dir = Path(temp_dir) / "1d" / "calendars"
            calendar_dir.mkdir(parents=True, exist_ok=True)
            
            calendar_file = calendar_dir / "1d.txt"
            
            # Create calendar entries matching sample data
            dates = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='1D')
            with open(calendar_file, 'w') as f:
                for i, date in enumerate(dates, 1):
                    f.write(f"{i:6d}→{date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Verify calendar format and count
            with open(calendar_file, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            # Remove empty lines and count actual entries
            actual_entries = [line for line in lines if '→' in line]
            expected_count = len(sample_data)
            
            assert len(actual_entries) == expected_count, \
                f"Calendar entry count mismatch: {len(actual_entries)} != {expected_count}"
            
            # Verify calendar format
            for line in actual_entries:
                assert '→' in line, f"Invalid calendar format: {line}"
                parts = line.split('→')
                assert len(parts) == 2, f"Invalid calendar line format: {line}"
                
                # Verify date format
                try:
                    datetime.strptime(parts[1], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pytest.fail(f"Invalid date format in calendar: {parts[1]}")

    def test_ohlc_data_integrity(self, sample_data):
        """Test OHLC data relationships are preserved."""
        # Verify OHLC relationships in sample data
        ohlc_data = sample_data[['open', 'high', 'low', 'close']].copy()
        
        for i in range(len(ohlc_data)):
            row = ohlc_data.iloc[i]
            
            # High should be >= max(open, close)
            assert row['high'] >= max(row['open'], row['close']), \
                f"Row {i}: High {row['high']} < max(open={row['open']}, close={row['close']})"
            
            # Low should be <= min(open, close)
            assert row['low'] <= min(row['open'], row['close']), \
                f"Row {i}: Low {row['low']} > min(open={row['open']}, close={row['close']})"
            
            # All values should be positive
            for field in ['open', 'high', 'low', 'close']:
                assert row[field] > 0, f"Row {i}: {field} value {row[field]} is not positive"


class TestDataTypeConversion:
    """Test data type handling and conversion."""

    def test_data_type_conversion(self, sample_data):
        """Test data type handling and conversion."""
        test_data = sample_data.copy()

        # Ensure specific data types
        test_data['open'] = test_data['open'].astype('float64')
        test_data['volume'] = test_data['volume'].astype('float64')
        test_data['funding_rate'] = test_data['funding_rate'].astype('float32')

        # Verify data types
        assert test_data['open'].dtype == 'float64'
        assert test_data['volume'].dtype == 'float64'
        assert test_data['funding_rate'].dtype == 'float32'


class TestDirectoryStructure:
    """Test directory structure for organized storage."""

    def test_directory_structure(self, sample_data):
        """Test directory structure for organized storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save data for multiple symbols and timeframes
            symbols = ["BTCUSDT", "ETHUSDT"]
            timeframes = ["1h", "day"]

            base_path = Path(temp_dir)

            for symbol in symbols:
                symbol_dir = base_path / symbol
                symbol_dir.mkdir(exist_ok=True)

                for timeframe in timeframes:
                    # Save CSV file in symbol directory
                    csv_file = symbol_dir / f"{timeframe}.csv"
                    sample_data.to_csv(csv_file, index=False)

            # Check directory structure
            for symbol in symbols:
                symbol_dir = base_path / symbol
                assert symbol_dir.exists(), f"Symbol directory not created: {symbol}"

                for timeframe in timeframes:
                    # Check if data file exists
                    csv_file = symbol_dir / f"{timeframe}.csv"
                    assert csv_file.exists(), f"No data file found for {symbol} {timeframe}"

                    # Verify file content
                    loaded_data = pd.read_csv(csv_file)
                    assert len(loaded_data) == len(sample_data), f"Data integrity issue for {symbol} {timeframe}"
