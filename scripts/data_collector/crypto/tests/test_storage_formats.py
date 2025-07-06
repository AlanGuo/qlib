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
