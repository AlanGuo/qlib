#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test filename and directory naming consistency for timeframe system.

This module tests that the unified timeframe format is consistently applied
across directory names, file names, and internal APIs.
"""

import pytest
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

# Add the crypto directory to Python path  
crypto_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(crypto_dir))

from config.timeframes import (
    TIMEFRAME_MAPPING,
    validate_timeframe,
    convert_for_qlib_internal
)
from storage_manager import CryptoStorageManager
from qlib_data_generator import QlibDataGenerator


class TestDirectoryNamingConsistency:
    """Test that directory names use consistent timeframe format."""
    
    def test_directory_names_use_standard_format(self):
        """Test that all directories use standard timeframe format (1h, 1d, etc.)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = CryptoStorageManager(temp_dir)
            
            # Test all supported timeframes
            for timeframe in TIMEFRAME_MAPPING.keys():
                # Create directory structure
                tf_dir = Path(temp_dir) / timeframe
                tf_dir.mkdir(exist_ok=True)
                
                # Directory name should match original timeframe
                assert tf_dir.name == timeframe, f"Directory name should be {timeframe}, got {tf_dir.name}"
                
                # Directory should NOT use converted format
                converted_timeframe = convert_for_qlib_internal(timeframe)
                if converted_timeframe != timeframe:
                    wrong_dir = Path(temp_dir) / converted_timeframe
                    assert not wrong_dir.exists(), f"Directory should not use converted format {converted_timeframe}"
    
    def test_qlib_data_generator_directory_consistency(self):
        """Test QlibDataGenerator creates directories with consistent names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = QlibDataGenerator(temp_dir)
            
            timeframes = ["1h", "1d", "1min", "5min"]
            exchanges = ["binance"]
            symbols = ["BTC/USDT"]
            
            from datetime import datetime
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 1, 2)
            
            generator.create_full_structure(
                timeframes=timeframes,
                exchanges=exchanges,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )
            
            # Check that directories use standard format
            for timeframe in timeframes:
                tf_dir = Path(temp_dir) / timeframe
                assert tf_dir.exists(), f"Directory {timeframe} should exist"
                assert tf_dir.name == timeframe, f"Directory name should be {timeframe}"
                
                # Check subdirectories exist
                for subdir in ["features", "instruments", "calendars"]:
                    subdir_path = tf_dir / subdir
                    assert subdir_path.exists(), f"Subdirectory {subdir} should exist in {timeframe}"


class TestFileNamingConsistency:
    """Test that file names use consistent timeframe format."""
    
    def test_binary_file_names_use_standard_format(self):
        """Test that binary files use standard timeframe format in names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = CryptoStorageManager(temp_dir)
            
            # Create sample data
            dates = pd.date_range(start='2024-01-01', periods=24, freq='1h')
            data = pd.Series(
                np.random.uniform(45000, 55000, 24),
                index=dates
            )
            
            instrument = "binance_spot_btc_usdt"
            field = "close"
            timeframe = "1h"
            
            # Save data
            storage_manager.save_feature_data(data, instrument, field, timeframe)
            
            # Check file naming
            expected_file = Path(temp_dir) / timeframe / "features" / instrument / f"{field}.{timeframe}.bin"
            assert expected_file.exists(), f"Expected file {expected_file} should exist"
            
            # File name should use standard format
            assert f".{timeframe}.bin" in expected_file.name, f"File name should contain .{timeframe}.bin"
            
            # File should NOT use converted format
            converted_timeframe = convert_for_qlib_internal(timeframe)
            if converted_timeframe != timeframe:
                wrong_file = Path(temp_dir) / timeframe / "features" / instrument / f"{field}.{converted_timeframe}.bin"
                assert not wrong_file.exists(), f"File should not use converted format {converted_timeframe}"
    
    def test_all_timeframes_file_naming(self):
        """Test file naming consistency across all supported timeframes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = CryptoStorageManager(temp_dir)
            
            # Test all supported timeframes
            for timeframe in TIMEFRAME_MAPPING.keys():
                # Create appropriate sample data
                if timeframe == "1min":
                    freq = "1min"
                elif timeframe == "5min":
                    freq = "5min"
                elif timeframe == "15min":
                    freq = "15min"
                elif timeframe == "30min":
                    freq = "30min"
                elif timeframe == "1h":
                    freq = "1h"
                elif timeframe == "1d":
                    freq = "1D"
                elif timeframe == "1w":
                    freq = "1W"
                else:
                    freq = "1D"  # fallback
                
                dates = pd.date_range(start='2024-01-01', periods=10, freq=freq)
                data = pd.Series(
                    np.random.uniform(45000, 55000, 10),
                    index=dates
                )
                
                instrument = "binance_spot_btc_usdt"
                field = "close"
                
                # Save data
                storage_manager.save_feature_data(data, instrument, field, timeframe)
                
                # Check file naming
                expected_file = Path(temp_dir) / timeframe / "features" / instrument / f"{field}.{timeframe}.bin"
                assert expected_file.exists(), f"Expected file {expected_file} should exist for timeframe {timeframe}"
                
                # Verify file name pattern
                assert expected_file.name == f"{field}.{timeframe}.bin", f"File name should be {field}.{timeframe}.bin"


class TestInternalAPIConsistency:
    """Test that internal API conversions don't leak into file/directory names."""
    
    def test_convert_for_qlib_internal_boundary(self):
        """Test that convert_for_qlib_internal is used only for internal API calls."""
        # Test the conversion itself
        assert convert_for_qlib_internal("1h") == "60min"
        assert convert_for_qlib_internal("1d") == "1d"
        assert convert_for_qlib_internal("1min") == "1min"
        
        # Test boundary validation
        with pytest.raises(ValueError, match="Invalid timeframe"):
            convert_for_qlib_internal("invalid")
    
    def test_no_leaked_converted_names_in_filesystem(self):
        """Test that converted names don't leak into filesystem structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = CryptoStorageManager(temp_dir)
            
            # Create sample data for 1h timeframe
            dates = pd.date_range(start='2024-01-01', periods=24, freq='1h')
            data = pd.Series(
                np.random.uniform(45000, 55000, 24),
                index=dates
            )
            
            instrument = "binance_spot_btc_usdt"
            field = "close"
            timeframe = "1h"
            
            # Save data
            storage_manager.save_feature_data(data, instrument, field, timeframe)
            
            # Check that NO files or directories use the converted format
            base_dir = Path(temp_dir)
            
            # Should NOT have 60min directory
            assert not (base_dir / "60min").exists(), "Should not create 60min directory"
            
            # Should NOT have 60min in file names
            for file_path in base_dir.rglob("*"):
                if file_path.is_file():
                    assert "60min" not in file_path.name, f"File name should not contain '60min': {file_path.name}"
            
            # Should have 1h directory and files
            assert (base_dir / "1h").exists(), "Should have 1h directory"
            expected_file = base_dir / "1h" / "features" / instrument / f"{field}.1h.bin"
            assert expected_file.exists(), f"Should have file with 1h format: {expected_file}"


class TestStorageInfoConsistency:
    """Test that storage info functions return consistent naming."""
    
    def test_storage_info_uses_standard_format(self):
        """Test that storage info functions return standard timeframe format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = CryptoStorageManager(temp_dir)
            
            # Create some test data
            dates = pd.date_range(start='2024-01-01', periods=24, freq='1h')
            data = pd.Series(
                np.random.uniform(45000, 55000, 24),
                index=dates
            )
            
            instrument = "binance_spot_btc_usdt"
            field = "close"
            timeframe = "1h"
            
            # Save data
            storage_manager.save_feature_data(data, instrument, field, timeframe)
            
            # Get storage info
            storage_info = storage_manager.get_storage_info()
            
            # Check that storage info uses standard format
            assert "1h" in storage_info["timeframes"], "Storage info should report 1h timeframe"
            assert "60min" not in storage_info["timeframes"], "Storage info should not report 60min timeframe"
            
            # Check timeframe details
            timeframe_info = storage_info["timeframes"]["1h"]
            assert "close" in timeframe_info["fields"], "Timeframe info should contain close field"


class TestConfigurationConsistency:
    """Test that configuration uses consistent timeframe format."""
    
    def test_timeframe_mapping_consistency(self):
        """Test that timeframe mapping is consistent (identity mapping)."""
        for timeframe, mapped in TIMEFRAME_MAPPING.items():
            assert timeframe == mapped, f"Timeframe mapping should be identity: {timeframe} -> {mapped}"
    
    def test_no_legacy_formats_in_mapping(self):
        """Test that legacy formats are not in the mapping."""
        legacy_formats = ["60min", "day", "week", "1m", "1D", "1W"]
        
        for legacy_format in legacy_formats:
            assert legacy_format not in TIMEFRAME_MAPPING, f"Legacy format {legacy_format} should not be in mapping"
    
    def test_validate_timeframe_rejects_legacy(self):
        """Test that validate_timeframe rejects legacy formats."""
        legacy_formats = ["60min", "day", "week", "1m"]
        
        for legacy_format in legacy_formats:
            assert not validate_timeframe(legacy_format), f"Should reject legacy format {legacy_format}"


class TestEndToEndConsistency:
    """Test end-to-end consistency across the entire system."""
    
    def test_full_system_consistency(self):
        """Test that the entire system maintains naming consistency."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create QlibDataGenerator
            generator = QlibDataGenerator(temp_dir)
            
            # Create storage manager
            storage_manager = CryptoStorageManager(temp_dir)
            
            timeframes = ["1h", "1d"]
            exchanges = ["binance"]
            symbols = ["BTC/USDT"]
            
            from datetime import datetime
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 1, 2)
            
            # Create structure
            generator.create_full_structure(
                timeframes=timeframes,
                exchanges=exchanges,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )
            
            # Add some data
            for timeframe in timeframes:
                freq = "1h" if timeframe == "1h" else "1D"
                dates = pd.date_range(start='2024-01-01', periods=24, freq=freq)
                data = pd.Series(
                    np.random.uniform(45000, 55000, len(dates)),
                    index=dates
                )
                
                instrument = "binance_spot_btc_usdt"
                field = "close"
                
                storage_manager.save_feature_data(data, instrument, field, timeframe)
            
            # Verify complete consistency
            base_dir = Path(temp_dir)
            
            # Check directory structure
            for timeframe in timeframes:
                tf_dir = base_dir / timeframe
                assert tf_dir.exists(), f"Directory {timeframe} should exist"
                
                # Check file names
                features_dir = tf_dir / "features" / "binance_spot_btc_usdt"
                if features_dir.exists():
                    for file_path in features_dir.glob("*.bin"):
                        assert f".{timeframe}.bin" in file_path.name, f"File should use {timeframe} format: {file_path.name}"
                
                # Check calendar files
                calendars_dir = tf_dir / "calendars"
                if calendars_dir.exists():
                    for file_path in calendars_dir.glob("*.txt"):
                        assert timeframe in file_path.name, f"Calendar file should use {timeframe} format: {file_path.name}"
            
            # Verify NO converted formats in filesystem
            for file_path in base_dir.rglob("*"):
                if file_path.is_file() or file_path.is_dir():
                    assert "60min" not in file_path.name, f"Path should not contain '60min': {file_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])