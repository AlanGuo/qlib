#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Pytest tests for timeframe conversion functionality.
"""

import pytest
import sys
from pathlib import Path

# Add the crypto directory to Python path  
crypto_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(crypto_dir))

from config.timeframes import (
    TIMEFRAME_MAPPING,
    EXCHANGE_TIMEFRAME_MAPPING,
    validate_timeframe
)


class TestTimeframeMapping:
    """Test timeframe mapping functionality."""

    def test_timeframe_mapping_exists(self):
        """Test that basic timeframe mapping exists."""
        expected_timeframes = ["1min", "5min", "15min", "30min", "1h", "1d"]
        actual_timeframes = list(TIMEFRAME_MAPPING.keys())

        for tf in expected_timeframes:
            assert tf in actual_timeframes, f"Missing timeframe: {tf}"

    def test_exchange_mappings_exist(self):
        """Test that exchange mappings exist for supported exchanges."""
        expected_exchanges = ["binance", "okx"]

        for exchange in expected_exchanges:
            assert exchange in EXCHANGE_TIMEFRAME_MAPPING, f"Missing exchange mapping: {exchange}"
            assert isinstance(EXCHANGE_TIMEFRAME_MAPPING[exchange], dict), f"Exchange mapping for {exchange} should be a dict"

    def test_timeframe_mapping_structure(self):
        """Test that timeframe mappings have correct structure."""
        for timeframe, mapping in TIMEFRAME_MAPPING.items():
            assert isinstance(timeframe, str), f"Timeframe key should be string: {timeframe}"
            assert isinstance(mapping, str), f"Timeframe mapping should be string: {mapping}"


class TestTimeframeValidation:
    """Test timeframe validation functionality."""

    def test_valid_timeframes(self):
        """Test validation of valid timeframes."""
        valid_timeframes = ["1min", "5min", "15min", "30min", "1h", "1d"]

        for tf in valid_timeframes:
            assert validate_timeframe(tf), f"Valid timeframe {tf} failed validation"

    def test_invalid_timeframes(self):
        """Test validation correctly rejects invalid timeframes."""
        invalid_timeframes = ["1s", "3m", "4h", "1M"]

        for tf in invalid_timeframes:
            assert not validate_timeframe(tf), f"Invalid timeframe {tf} passed validation"


class TestQlibConversion:
    """Test conversion to Qlib format."""

    def test_qlib_format_conversion(self):
        """Test conversion to Qlib format."""
        from config.timeframes import convert_for_qlib_internal, validate_timeframe

        test_cases = {
            "1min": "1min",
            "5min": "5min",
            "15min": "15min",
            "30min": "30min",
            "1h": "60min",     # 1h maps to qlib's 60min format
            "1d": "1d",        # 1d maps to qlib's 1d format
            "1w": "1w",        # 1w maps to qlib's 1w format
        }

        # Test all conversions
        for input_tf, expected_output in test_cases.items():
            actual_output = convert_for_qlib_internal(input_tf)
            assert actual_output == expected_output, f"Conversion failed: {input_tf} -> {actual_output}, expected {expected_output}"

            # Check if it's qlib compatible
            assert validate_timeframe(input_tf), f"Timeframe {input_tf} should be valid"

class TestExchangeTimeframeConversion:
    """Test exchange-specific timeframe conversion."""

    def test_binance_timeframe_conversion(self):
        """Test Binance timeframe conversion."""
        from config.timeframes import get_exchange_timeframe

        binance_cases = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "1h": "1h",
            "1d": "1d"
        }

        for standard_tf, expected_binance_tf in binance_cases.items():
            actual_binance_tf = get_exchange_timeframe("binance", standard_tf)
            assert actual_binance_tf == expected_binance_tf, f"Binance conversion failed: {standard_tf} -> {actual_binance_tf}, expected {expected_binance_tf}"

    def test_okx_timeframe_conversion(self):
        """Test OKX timeframe conversion."""
        from config.timeframes import get_exchange_timeframe

        okx_cases = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "1h": "1h",  # OKX uses lowercase, NOT "1H"
            "1d": "1d"   # OKX uses lowercase, NOT "1D"
        }

        for standard_tf, expected_okx_tf in okx_cases.items():
            actual_okx_tf = get_exchange_timeframe("okx", standard_tf)
            assert actual_okx_tf == expected_okx_tf, f"OKX conversion failed: {standard_tf} -> {actual_okx_tf}, expected {expected_okx_tf}"

class TestTimeframeSeconds:
    """Test timeframe to seconds conversion."""

    def test_timeframe_seconds_conversion(self):
        """Test timeframe to seconds conversion."""
        from config.timeframes import get_timeframe_seconds

        test_cases = {
            "1min": 60,
            "5min": 300,
            "15min": 900,
            "30min": 1800,
            "1h": 3600,
            "1d": 86400
        }

        for timeframe, expected_seconds in test_cases.items():
            actual_seconds = get_timeframe_seconds(timeframe)
            assert actual_seconds == expected_seconds, f"Seconds conversion failed: {timeframe} -> {actual_seconds}, expected {expected_seconds}"


