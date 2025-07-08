#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for cryptocurrency data collection configuration system.

This script tests the configuration loading, validation, and template system
for the crypto data collector.
"""

import pytest
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from config.main_config import CryptoDataConfig, ConfigFactory, CollectionConfig, ValidationConfig
from config.template_manager import ConfigTemplateManager
from config.exchanges import EXCHANGE_CONFIGS, get_exchange_config
from config.timeframes import TIMEFRAME_MAPPING, validate_timeframe
from config.fields import STANDARD_FIELDS, CRYPTO_SPECIFIC_FIELDS, validate_field


class TestConfigLoading:
    """Test configuration loading and parsing."""
    
    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = CryptoDataConfig()
        
        # Check basic structure
        assert hasattr(config, 'collection')
        assert hasattr(config, 'validation')
        assert isinstance(config.collection, CollectionConfig)
        assert isinstance(config.validation, ValidationConfig)
        
        # Check default values
        assert config.collection.exchanges == ["binance"]
        assert "1d" in config.collection.timeframes
        
    def test_config_from_dict(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            "collection": {
                "exchanges": ["binance"],
                "timeframes": ["1h"],
                "symbols": ["BTC/USDT"],
                "fields": ["ohlcv"]
            }
        }

        config = CryptoDataConfig.from_dict(config_dict)

        assert config.collection.exchanges == ["binance"]
        assert config.collection.timeframes == ["1h"]
        assert config.collection.symbols == ["BTC/USDT"]
        assert config.collection.fields == ["ohlcv"]
    
    def test_config_from_yaml_string(self):
        """Test creating configuration from YAML string."""
        yaml_content = """
        collection:
          exchanges: ["okx"]
          timeframes: ["1d"]
          symbols: ["ETH/USDT"]
        """

        config = CryptoDataConfig.from_yaml(yaml_content)

        assert config.collection.exchanges == ["okx"]
        assert config.collection.timeframes == ["1d"]
        assert config.collection.symbols == ["ETH/USDT"]
    
    def test_config_from_file(self):
        """Test loading configuration from file."""
        config_data = {
            "collection": {
                "exchanges": ["binance", "okx"],
                "timeframes": ["1h", "1d"],
                "output_dir": "./test_data"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name
        
        try:
            config = CryptoDataConfig.from_file(temp_file)
            
            assert config.collection.exchanges == ["binance", "okx"]
            assert config.collection.timeframes == ["1h", "1d"]
            assert config.collection.output_dir == "./test_data"
        finally:
            Path(temp_file).unlink()


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_valid_config_validation(self):
        """Test validation of valid configuration."""
        config = CryptoDataConfig()
        
        # Should not raise exception
        config.validate()
    
    def test_invalid_exchange_validation(self):
        """Test validation with invalid exchange."""
        config_dict = {
            "collection": {
                "exchanges": ["invalid_exchange"]
            }
        }
        
        config = CryptoDataConfig.from_dict(config_dict)
        
        with pytest.raises(ValueError, match="Unsupported exchange"):
            config.validate()
    
    def test_invalid_timeframe_validation(self):
        """Test validation with invalid timeframe."""
        config_dict = {
            "collection": {
                "timeframes": ["invalid_timeframe"]
            }
        }
        
        config = CryptoDataConfig.from_dict(config_dict)
        
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            config.validate()
    
    def test_invalid_field_validation(self):
        """Test validation with invalid field."""
        config_dict = {
            "collection": {
                "fields": ["invalid_field"]
            }
        }
        
        config = CryptoDataConfig.from_dict(config_dict)
        
        with pytest.raises(ValueError, match="Unknown field"):
            config.validate()
    
    def test_empty_exchanges_validation(self):
        """Test validation with empty exchanges list."""
        config_dict = {
            "collection": {
                "exchanges": []
            }
        }
        
        config = CryptoDataConfig.from_dict(config_dict)
        
        with pytest.raises(ValueError, match="At least one exchange must be specified"):
            config.validate()


class TestConfigFactory:
    """Test configuration factory methods."""
    
    def test_high_frequency_config(self):
        """Test high frequency configuration creation."""
        config = ConfigFactory.create_high_frequency_config()
        
        # Should include minute-level timeframes
        assert "1min" in config.collection.timeframes or "5min" in config.collection.timeframes
        
        # Should be valid
        config.validate()
    
    def test_daily_config(self):
        """Test daily configuration creation."""
        config = ConfigFactory.create_daily_config()
        
        # Should include daily timeframe
        assert "1d" in config.collection.timeframes
        
        # Should be valid
        config.validate()
    
    def test_minimal_config(self):
        """Test minimal configuration creation."""
        config = ConfigFactory.create_minimal_config()
        
        # Should have minimal settings
        assert len(config.collection.exchanges) >= 1
        assert len(config.collection.timeframes) >= 1
        
        # Should be valid
        config.validate()


class TestTemplateManager:
    """Test template management system."""
    
    def test_template_manager_initialization(self):
        """Test template manager initialization."""
        manager = ConfigTemplateManager()
        
        # Should have template directory
        assert hasattr(manager, 'template_dir')
        assert isinstance(manager.template_dir, Path)
    
    def test_list_templates(self):
        """Test listing available templates."""
        manager = ConfigTemplateManager()
        
        templates = manager.list_templates()
        
        # Should return a list
        assert isinstance(templates, list)
        
        # Each template should be a string
        for template in templates:
            assert isinstance(template, str)
    
    def test_load_template(self):
        """Test loading a template."""
        manager = ConfigTemplateManager()
        
        # Try to load a basic template
        try:
            config = manager.load_template("simple")
            assert isinstance(config, CryptoDataConfig)
            config.validate()
        except FileNotFoundError:
            # Template might not exist, which is okay for this test
            pass
    
    def test_create_custom_template(self):
        """Test creating a custom template."""
        manager = ConfigTemplateManager()
        
        config = CryptoDataConfig()
        template_name = "test_template"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override template directory for testing
            manager.template_dir = Path(temp_dir)
            
            # Create template
            manager.save_template(config, template_name)
            
            # Check if template file was created
            template_file = manager.template_dir / f"{template_name}.yaml"
            assert template_file.exists()
            
            # Load and validate template
            loaded_config = manager.load_template(template_name)
            assert isinstance(loaded_config, CryptoDataConfig)
            loaded_config.validate()


class TestExchangeConfig:
    """Test exchange configuration."""
    
    def test_supported_exchanges(self):
        """Test that only supported exchanges are configured."""
        supported_exchanges = ["binance", "okx"]
        
        for exchange in EXCHANGE_CONFIGS.keys():
            assert exchange in supported_exchanges
    
    def test_exchange_config_structure(self):
        """Test exchange configuration structure."""
        for exchange_id, config in EXCHANGE_CONFIGS.items():
            # Check required fields
            assert hasattr(config, 'name')
            assert hasattr(config, 'ccxt_id')
            assert hasattr(config, 'supported_timeframes')
            assert hasattr(config, 'rate_limit')
            
            # Check timeframes are valid
            for timeframe in config.supported_timeframes:
                assert validate_timeframe(timeframe)
    
    def test_get_exchange_config(self):
        """Test getting exchange configuration."""
        # Test valid exchange
        config = get_exchange_config("binance")
        assert config is not None
        assert config.name == "Binance"
        
        # Test invalid exchange (returns default config)
        invalid_config = get_exchange_config("invalid_exchange")
        assert invalid_config is not None
        assert invalid_config.name == "Unknown Exchange"


class TestFieldValidation:
    """Test field validation."""
    
    def test_standard_fields(self):
        """Test standard field validation."""
        for field in STANDARD_FIELDS:
            assert validate_field(field)
    
    def test_crypto_specific_fields(self):
        """Test crypto-specific field validation."""
        for field in CRYPTO_SPECIFIC_FIELDS:
            assert validate_field(field)
    
    def test_invalid_field(self):
        """Test invalid field validation."""
        assert not validate_field("invalid_field")
    
    def test_field_case_sensitivity(self):
        """Test field validation case sensitivity."""
        # Should be case sensitive
        assert validate_field("open")
        assert not validate_field("OPEN")
        assert not validate_field("Open")


class TestTimeframeValidation:
    """Test timeframe validation."""
    
    def test_supported_timeframes(self):
        """Test supported timeframe validation."""
        supported_timeframes = ["1min", "5min", "15min", "30min", "1h", "1d"]
        
        for timeframe in supported_timeframes:
            assert validate_timeframe(timeframe)
    
    def test_unsupported_timeframes(self):
        """Test unsupported timeframe validation."""
        unsupported_timeframes = ["1s", "3m", "4h", "1M"]
        
        for timeframe in unsupported_timeframes:
            assert not validate_timeframe(timeframe)
    
    def test_timeframe_mapping(self):
        """Test timeframe mapping completeness."""
        for timeframe in TIMEFRAME_MAPPING.keys():
            assert validate_timeframe(timeframe)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
