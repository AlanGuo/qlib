# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test suite for the refactored timeframe design.

This module tests the simplified timeframe handling that follows
the existing Qlib project patterns used in other data collectors.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the crypto directory to Python path  
crypto_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(crypto_dir))

from config.timeframes import (
    TIMEFRAME_MAPPING,
    EXCHANGE_TIMEFRAME_MAPPING,
    SUPPORTED_TIMEFRAMES,
    TIMEFRAME_PRIORITIES,
    validate_timeframe,
    get_exchange_timeframe,
    get_supported_timeframes_for_exchange,
    get_timeframe_seconds,
    sort_timeframes_by_priority,
    convert_for_qlib_internal
)
from timeframe_manager import TimeframeManager


class TestTimeframeMapping:
    """Test the basic timeframe mapping functionality."""
    
    def test_timeframe_mapping_consistency(self):
        """Test that timeframe mapping is consistent with Qlib project patterns."""
        # Test that all mappings are identity mappings (no transformation)
        for timeframe, mapped in TIMEFRAME_MAPPING.items():
            assert timeframe == mapped, f"Timeframe {timeframe} should map to itself"
    
    def test_timeframe_naming_convention(self):
        """Test that timeframe names follow Qlib project conventions."""
        expected_timeframes = {"1min", "5min", "15min", "30min", "1h", "1d", "1w"}
        actual_timeframes = set(TIMEFRAME_MAPPING.keys())
        
        assert actual_timeframes == expected_timeframes, \
            f"Timeframes should match expected set: {expected_timeframes}"
    
    def test_validate_timeframe_function(self):
        """Test the validate_timeframe function."""
        # Valid timeframes
        valid_timeframes = ["1min", "5min", "15min", "30min", "1h", "1d", "1w"]
        for tf in valid_timeframes:
            assert validate_timeframe(tf), f"Timeframe {tf} should be valid"
        
        # Invalid timeframes
        invalid_timeframes = ["1s", "2h", "3d", "1month", "invalid", ""]
        for tf in invalid_timeframes:
            assert not validate_timeframe(tf), f"Timeframe {tf} should be invalid"


class TestExchangeTimeframeMapping:
    """Test exchange-specific timeframe conversion."""
    
    def test_binance_mapping(self):
        """Test Binance timeframe mapping."""
        binance_mapping = EXCHANGE_TIMEFRAME_MAPPING["binance"]
        
        # Test expected mappings
        expected_mappings = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "1h": "1h",
            "1d": "1d",
            "1w": "1w"
        }
        
        for standard, expected in expected_mappings.items():
            actual = binance_mapping.get(standard)
            assert actual == expected, \
                f"Binance mapping for {standard} should be {expected}, got {actual}"
    
    def test_okx_mapping(self):
        """Test OKX timeframe mapping."""
        okx_mapping = EXCHANGE_TIMEFRAME_MAPPING["okx"]
        
        # Test expected mappings (note: OKX uses LOWERCASE, not uppercase!)
        expected_mappings = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "1h": "1h",  # IMPORTANT: OKX uses lowercase, NOT "1H"
            "1d": "1d",  # IMPORTANT: OKX uses lowercase, NOT "1D"
            "1w": "1w"   # IMPORTANT: OKX uses lowercase, NOT "1W"
        }
        
        for standard, expected in expected_mappings.items():
            actual = okx_mapping.get(standard)
            assert actual == expected, \
                f"OKX mapping for {standard} should be {expected}, got {actual}"
    
    def test_get_exchange_timeframe_function(self):
        """Test the get_exchange_timeframe function."""
        # Test Binance
        assert get_exchange_timeframe("binance", "1h") == "1h"
        assert get_exchange_timeframe("binance", "1d") == "1d"
        
        # Test OKX (uses lowercase)
        assert get_exchange_timeframe("okx", "1h") == "1h"
        assert get_exchange_timeframe("okx", "1d") == "1d"
        
        # Test case insensitivity
        assert get_exchange_timeframe("BINANCE", "1h") == "1h"
        assert get_exchange_timeframe("OKX", "1h") == "1h"
        
        # Test unknown exchange
        assert get_exchange_timeframe("unknown", "1h") == "1h"
        
        # Test unknown timeframe
        assert get_exchange_timeframe("binance", "unknown") == "unknown"
    
    def test_get_supported_timeframes_for_exchange(self):
        """Test getting supported timeframes for exchanges."""
        # Test Binance
        binance_timeframes = get_supported_timeframes_for_exchange("binance")
        expected_binance = ["1min", "5min", "15min", "30min", "1h", "1d", "1w"]
        assert set(binance_timeframes) == set(expected_binance)
        
        # Test OKX
        okx_timeframes = get_supported_timeframes_for_exchange("okx")
        expected_okx = ["1min", "5min", "15min", "30min", "1h", "1d", "1w"]
        assert set(okx_timeframes) == set(expected_okx)
        
        # Test unknown exchange
        unknown_timeframes = get_supported_timeframes_for_exchange("unknown")
        assert unknown_timeframes == []


class TestTimeframeUtilities:
    """Test utility functions for timeframes."""
    
    def test_get_timeframe_seconds(self):
        """Test getting timeframe duration in seconds."""
        expected_seconds = {
            "1min": 60,
            "5min": 300,
            "15min": 900,
            "30min": 1800,
            "1h": 3600,
            "1d": 86400,
            "1w": 604800
        }
        
        for timeframe, expected in expected_seconds.items():
            actual = get_timeframe_seconds(timeframe)
            assert actual == expected, \
                f"Timeframe {timeframe} should be {expected} seconds, got {actual}"
        
        # Test unknown timeframe
        assert get_timeframe_seconds("unknown") == 0
    
    def test_sort_timeframes_by_priority(self):
        """Test sorting timeframes by priority."""
        timeframes = ["1min", "1h", "1d", "5min", "1w"]
        sorted_timeframes = sort_timeframes_by_priority(timeframes)
        
        # Check that daily has highest priority
        assert sorted_timeframes[0] == "1d"
        
        # Check that the order follows priorities
        priorities = [TIMEFRAME_PRIORITIES.get(tf, 0) for tf in sorted_timeframes]
        assert priorities == sorted(priorities, reverse=True)
    
    def test_supported_timeframes_categories(self):
        """Test timeframe categories."""
        # Test minute category
        minute_timeframes = SUPPORTED_TIMEFRAMES["minute"]
        expected_minute = ["1min", "5min", "15min", "30min"]
        assert minute_timeframes == expected_minute
        
        # Test hour category
        hour_timeframes = SUPPORTED_TIMEFRAMES["hour"]
        expected_hour = ["1h"]
        assert hour_timeframes == expected_hour
        
        # Test daily category
        daily_timeframes = SUPPORTED_TIMEFRAMES["daily"]
        expected_daily = ["1d"]
        assert daily_timeframes == expected_daily
        
        # Test weekly category
        weekly_timeframes = SUPPORTED_TIMEFRAMES["weekly"]
        expected_weekly = ["1w"]
        assert weekly_timeframes == expected_weekly
        
        # Test all category
        all_timeframes = SUPPORTED_TIMEFRAMES["all"]
        expected_all = list(TIMEFRAME_MAPPING.keys())
        assert set(all_timeframes) == set(expected_all)
        
        # Test common category
        common_timeframes = SUPPORTED_TIMEFRAMES["common"]
        expected_common = ["1min", "5min", "15min", "1h", "1d"]
        assert common_timeframes == expected_common


class TestQlibConversion:
    """Test Qlib internal conversion functionality."""
    
    def test_convert_for_qlib_internal(self):
        """Test the simplified Qlib internal conversion."""
        # Test that only 1h gets converted
        assert convert_for_qlib_internal("1h") == "60min"
        
        # Test that all other timeframes remain unchanged
        unchanged_timeframes = ["1min", "5min", "15min", "30min", "1d", "1w"]
        for tf in unchanged_timeframes:
            assert convert_for_qlib_internal(tf) == tf
        
        # Test invalid timeframe raises ValueError (boundary validation)
        with pytest.raises(ValueError, match="Invalid timeframe"):
            convert_for_qlib_internal("unknown")
    
    def test_minimal_conversion_philosophy(self):
        """Test that the conversion is minimal and only when necessary."""
        # Only one conversion should exist
        conversions = 0
        for tf in TIMEFRAME_MAPPING.keys():
            if convert_for_qlib_internal(tf) != tf:
                conversions += 1
        
        assert conversions == 1, "Only one timeframe should require conversion"
        
        # That conversion should be 1h -> 60min
        assert convert_for_qlib_internal("1h") == "60min"


class TestTimeframeManager:
    """Test the simplified TimeframeManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = TimeframeManager()
    
    def test_manager_initialization(self):
        """Test that the manager initializes correctly."""
        manager = TimeframeManager()
        assert hasattr(manager, '_validated_cache')
        assert isinstance(manager._validated_cache, set)
    
    def test_validate_timeframe_with_caching(self):
        """Test timeframe validation with caching."""
        manager = TimeframeManager()
        
        # First validation should cache the result
        assert manager.validate_timeframe("1h") is True
        assert "1h" in manager._validated_cache
        
        # Second validation should use cache
        assert manager.validate_timeframe("1h") is True
        
        # Invalid timeframe should not be cached
        assert manager.validate_timeframe("invalid") is False
        assert "invalid" not in manager._validated_cache
    
    def test_validate_timeframes_list(self):
        """Test validating a list of timeframes."""
        manager = TimeframeManager()
        
        timeframes = ["1h", "1d", "invalid", "1w", "unknown"]
        valid_timeframes = manager.validate_timeframes(timeframes)
        
        expected_valid = ["1h", "1d", "1w"]
        assert valid_timeframes == expected_valid
    
    def test_get_exchange_timeframe_with_validation(self):
        """Test getting exchange timeframe with validation."""
        manager = TimeframeManager()
        
        # Valid timeframe
        result = manager.get_exchange_timeframe("binance", "1h")
        assert result == "1h"
        
        # Invalid timeframe should return None
        result = manager.get_exchange_timeframe("binance", "invalid")
        assert result is None
    
    def test_get_common_timeframes(self):
        """Test getting common timeframes across exchanges."""
        manager = TimeframeManager()
        
        exchanges = ["binance", "okx"]
        common_timeframes = manager.get_common_timeframes(exchanges)
        
        # Should include all timeframes since both exchanges support all
        expected_common = ["1min", "5min", "15min", "30min", "1h", "1d", "1w"]
        assert set(common_timeframes) == set(expected_common)
        
        # Should be sorted by priority
        assert common_timeframes[0] == "1d"  # Highest priority
    
    def test_get_timeframes_by_category(self):
        """Test getting timeframes by category."""
        manager = TimeframeManager()
        
        # Test minute category
        minute_timeframes = manager.get_timeframes_by_category("minute")
        assert minute_timeframes == ["1min", "5min", "15min", "30min"]
        
        # Test unknown category
        unknown_timeframes = manager.get_timeframes_by_category("unknown")
        assert unknown_timeframes == []
    
    def test_get_timeframe_info(self):
        """Test getting timeframe information."""
        manager = TimeframeManager()
        
        # Valid timeframe
        info = manager.get_timeframe_info("1h")
        assert info["timeframe"] == "1h"
        assert info["seconds"] == 3600
        assert info["priority"] == 90
        assert info["is_valid"] is True
        
        # Invalid timeframe
        info = manager.get_timeframe_info("invalid")
        assert info == {}


class TestConsistencyWithOtherCollectors:
    """Test consistency with other Qlib data collectors."""
    
    def test_naming_consistency_with_base_collector(self):
        """Test that our naming is consistent with BaseCollector."""
        # Our 1min should match BaseCollector.INTERVAL_1min
        assert "1min" in TIMEFRAME_MAPPING
        
        # Our 1d should match BaseCollector.INTERVAL_1d
        assert "1d" in TIMEFRAME_MAPPING
        
        # Test that we don't use inconsistent naming
        assert "1m" not in TIMEFRAME_MAPPING  # Should be 1min
        assert "day" not in TIMEFRAME_MAPPING  # Should be 1d
    
    def test_simple_conversion_like_yahoo_collector(self):
        """Test that our conversion is simple like Yahoo collector."""
        # Test that conversion is simple string mapping
        binance_1h = get_exchange_timeframe("binance", "1h")
        okx_1h = get_exchange_timeframe("okx", "1h")
        
        # Should be simple string conversion
        assert binance_1h == "1h"
        assert okx_1h == "1h"  # OKX uses lowercase, not uppercase
        
        # Test that it's similar to Yahoo's: interval = "1m" if interval in ["1m", "1min"] else interval
        binance_1min = get_exchange_timeframe("binance", "1min")
        assert binance_1min == "1m"
    
    def test_directory_structure_consistency(self):
        """Test that directory structure follows other collectors."""
        # Our timeframes should be usable directly as directory names
        for timeframe in TIMEFRAME_MAPPING.keys():
            # Should be valid directory name
            assert "/" not in timeframe
            assert "\\" not in timeframe
            assert ":" not in timeframe
            
            # Should be consistent format
            assert timeframe.isalnum() or all(c.isalnum() or c in "min" for c in timeframe)


class TestBackwardCompatibility:
    """Test backward compatibility and migration."""
    
    def test_no_legacy_formats(self):
        """Test that we don't support legacy formats that cause confusion."""
        # Should not support legacy formats that were causing confusion
        assert "day" not in TIMEFRAME_MAPPING
        assert "week" not in TIMEFRAME_MAPPING
        assert "1m" not in TIMEFRAME_MAPPING  # Should be 1min
        
        # Should not validate legacy formats
        assert not validate_timeframe("day")
        assert not validate_timeframe("week")
        assert not validate_timeframe("1m")
    
    def test_config_file_compatibility(self):
        """Test that config files use the correct format."""
        # Test that expected timeframes are in the standard mapping
        config_timeframes = ["1h", "1d", "1w", "1min", "5min", "15min"]
        
        for tf in config_timeframes:
            assert tf in TIMEFRAME_MAPPING, f"Config timeframe {tf} should be supported"
            assert validate_timeframe(tf), f"Config timeframe {tf} should be valid"


if __name__ == "__main__":
    pytest.main([__file__])