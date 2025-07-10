#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Pytest tests for field definitions and validation.
"""

import pytest
import sys
from pathlib import Path

# Add the crypto directory to Python path  
crypto_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(crypto_dir))

from config.fields import (
    STANDARD_FIELDS, CRYPTO_SPECIFIC_FIELDS, ALL_FIELDS,
    FieldConfig, validate_field, get_field_config,
    get_fields_for_market_type, get_required_fields
)


class TestFieldImports:
    """Test field configuration imports."""

    def test_field_imports_successful(self):
        """Test that all field imports are successful."""
        # If we reach this point, imports were successful
        assert STANDARD_FIELDS is not None
        assert CRYPTO_SPECIFIC_FIELDS is not None
        assert ALL_FIELDS is not None
        assert FieldConfig is not None

class TestStandardFields:
    """Test standard field definitions."""

    def test_standard_fields_exist(self):
        """Test that expected standard fields exist."""
        expected_fields = ["open", "high", "low", "close", "volume"]

        for field_name in expected_fields:
            assert field_name in STANDARD_FIELDS, f"Missing standard field: {field_name}"

            field_config = STANDARD_FIELDS[field_name]
            assert isinstance(field_config, FieldConfig), f"Field {field_name} is not a FieldConfig instance"

            # Check required properties
            assert field_config.name == field_name, f"Field name mismatch: {field_config.name} != {field_name}"
            assert field_config.description, f"Field {field_name} missing description"
            assert field_config.data_type in ["float", "int", "str"], f"Invalid data type for {field_name}: {field_config.data_type}"


class TestCryptoSpecificFields:
    """Test crypto-specific field definitions."""

    def test_crypto_specific_fields_exist(self):
        """Test that expected crypto-specific fields exist."""
        expected_fields = [
            "funding_rate", "open_interest", "volume_quote", "volume_24h",
            "change_24h", "high_24h", "low_24h", "vwap", "trade_count"
        ]

        for field_name in expected_fields:
            assert field_name in CRYPTO_SPECIFIC_FIELDS, f"Missing crypto field: {field_name}"

            field_config = CRYPTO_SPECIFIC_FIELDS[field_name]
            assert isinstance(field_config, FieldConfig), f"Field {field_name} is not a FieldConfig instance"

            # Check required properties
            assert field_config.name == field_name, f"Field name mismatch: {field_config.name} != {field_name}"
            assert field_config.description, f"Field {field_name} missing description"

class TestFieldValidation:
    """Test field validation function."""

    def test_valid_standard_fields(self):
        """Test validation of valid standard fields."""
        for field_name in STANDARD_FIELDS.keys():
            assert validate_field(field_name), f"Standard field {field_name} failed validation"

    def test_valid_crypto_fields(self):
        """Test validation of valid crypto fields."""
        for field_name in CRYPTO_SPECIFIC_FIELDS.keys():
            assert validate_field(field_name), f"Crypto field {field_name} failed validation"

    def test_invalid_fields(self):
        """Test validation correctly rejects invalid fields."""
        invalid_fields = ["invalid_field", "nonexistent", ""]
        for field_name in invalid_fields:
            assert not validate_field(field_name), f"Invalid field {field_name} passed validation"


class TestFieldConfigRetrieval:
    """Test field configuration retrieval."""

    def test_retrieve_standard_field_configs(self):
        """Test retrieving standard field configurations."""
        for field_name in STANDARD_FIELDS.keys():
            config = get_field_config(field_name)
            assert config is not None, f"Could not retrieve config for standard field: {field_name}"
            assert config.name == field_name, f"Config name mismatch for {field_name}"

    def test_retrieve_crypto_field_configs(self):
        """Test retrieving crypto field configurations."""
        for field_name in CRYPTO_SPECIFIC_FIELDS.keys():
            config = get_field_config(field_name)
            assert config is not None, f"Could not retrieve config for crypto field: {field_name}"
            assert config.name == field_name, f"Config name mismatch for {field_name}"

    def test_retrieve_invalid_field_config(self):
        """Test retrieving invalid field returns None."""
        invalid_config = get_field_config("invalid_field")
        assert invalid_config is None, "Should return None for invalid field"

class TestMarketTypeFiltering:
    """Test market type filtering."""

    def test_spot_market_fields(self):
        """Test spot market field filtering."""
        spot_fields = get_fields_for_market_type("spot")

        # Should include standard fields
        assert "open" in spot_fields, "Spot fields should include standard OHLC fields"
        assert "close" in spot_fields, "Spot fields should include standard OHLC fields"

    def test_futures_market_fields(self):
        """Test futures market field filtering."""
        futures_fields = get_fields_for_market_type("futures")

        # Should include funding rate and open interest
        assert "funding_rate" in futures_fields, "Futures fields should include funding_rate"
        assert "open_interest" in futures_fields, "Futures fields should include open_interest"

    def test_perpetual_market_fields(self):
        """Test perpetual market field filtering."""
        perpetual_fields = get_fields_for_market_type("perpetual")

        # Should include funding rate and open interest
        assert "funding_rate" in perpetual_fields, "Perpetual fields should include funding_rate"
        assert "open_interest" in perpetual_fields, "Perpetual fields should include open_interest"


class TestRequiredFields:
    """Test required fields identification."""

    def test_required_fields_identification(self):
        """Test required fields identification."""
        required_fields = get_required_fields()

        # Standard OHLCV fields should be required
        expected_required = ["open", "high", "low", "close", "volume"]
        for field in expected_required:
            assert field in required_fields, f"Required field {field} not in required fields list"


class TestFieldDataTypes:
    """Test field data type consistency."""

    def test_valid_data_types(self):
        """Test that all fields have valid data types."""
        valid_types = ["float", "int", "str", "bool"]

        for field_name, field_config in ALL_FIELDS.items():
            assert field_config.data_type in valid_types, f"Invalid data type for {field_name}: {field_config.data_type}"

    def test_price_field_types(self):
        """Test that price fields have float type."""
        price_fields = ["open", "high", "low", "close", "vwap"]
        for field in price_fields:
            if field in ALL_FIELDS:
                assert ALL_FIELDS[field].data_type == "float", f"Price field {field} should be float type"

    def test_volume_field_types(self):
        """Test that volume fields have float type."""
        volume_fields = ["volume", "volume_quote", "volume_24h"]
        for field in volume_fields:
            if field in ALL_FIELDS:
                assert ALL_FIELDS[field].data_type == "float", f"Volume field {field} should be float type"

    def test_count_field_types(self):
        """Test that count fields have int type."""
        count_fields = ["trade_count"]
        for field in count_fields:
            if field in ALL_FIELDS:
                assert ALL_FIELDS[field].data_type == "int", f"Count field {field} should be int type"
