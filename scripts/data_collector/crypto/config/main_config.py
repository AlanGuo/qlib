# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Main configuration management system for cryptocurrency data collection.

This module provides a unified configuration management system that integrates
all configuration components and supports multiple formats, validation,
and environment variable overrides.
"""

import os
import sys
from pathlib import Path

import yaml
import json
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

from config.timeframes import TIMEFRAME_MAPPING, SUPPORTED_TIMEFRAMES
from config.fields import CRYPTO_FIELDS, STANDARD_FIELDS, EXTENDED_FIELDS
from config.exchanges import EXCHANGE_CONFIGS, DEFAULT_EXCHANGE_CONFIG
from config.risk_config import RiskConfig
from config.universe_config import UniverseConfig, FilterConfig
from config.validation_config import ValidationConfig


@dataclass
class CollectionConfig:
    """Configuration for data collection parameters."""
    
    # Basic collection settings
    exchanges: List[str] = field(default_factory=lambda: ["binance"])
    symbols: List[str] = field(default_factory=list)  # Empty means auto-discover
    timeframes: List[str] = field(default_factory=lambda: ["day"])
    fields: List[str] = field(default_factory=lambda: ["open", "high", "low", "close", "volume"])
    market_type: str = "spot"  # spot, futures, perpetual, option
    
    # Collection behavior
    max_workers: int = 4
    rate_limit_delay: float = 0.1
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Data range
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    lookback_days: int = 365
    
    # Storage settings
    output_dir: str = "./crypto_data"
    file_format: str = "qlib"  # qlib, parquet, csv, hdf5
    compression: Optional[str] = "snappy"

    # Qlib-specific storage settings
    qlib_data_dir: Optional[str] = None  # If None, uses output_dir
    create_qlib_structure: bool = True  # Create standard Qlib directory structure
    provider_uri: Optional[str] = None  # Qlib provider URI
    
    # Advanced settings
    enable_extended_fields: bool = False
    enable_risk_metrics: bool = False
    enable_validation: bool = True
    incremental_update: bool = True


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""

    # Memory management
    chunk_size: int = 10000
    max_memory_usage: float = 0.8  # 80% of available memory

    # Parallel processing
    enable_multiprocessing: bool = True
    process_pool_size: Optional[int] = None  # None = auto-detect

    # Caching
    enable_caching: bool = True
    cache_size_limit: int = 1000
    cache_ttl: int = 3600  # seconds

    # Database optimization
    batch_insert_size: int = 1000
    connection_pool_size: int = 5


@dataclass
class IncrementalConfig:
    """Configuration for incremental data updates."""

    # Update behavior
    enabled: bool = True
    max_concurrent_updates: int = 10
    max_age_hours: int = 24
    max_consecutive_failures: int = 3

    # Update intervals (timeframe -> minutes)
    update_intervals: Dict[str, int] = field(default_factory=lambda: {
        '1m': 5,     # Update every 5 minutes
        '5m': 15,    # Update every 15 minutes
        '15m': 30,   # Update every 30 minutes
        '30m': 60,   # Update every hour
        '1h': 120,   # Update every 2 hours
        '4h': 480,   # Update every 8 hours
        '1d': 1440,  # Update every day
        '1w': 10080  # Update every week
    })

    # State management
    state_storage_type: str = "file"  # file, memory, database
    state_file: Optional[str] = None  # Auto-generated if None
    backup_dir: Optional[str] = None  # Auto-generated if None
    max_backups: int = 10
    auto_backup: bool = True

    # Conflict resolution
    conflict_resolution: str = "keep_latest"  # keep_latest, keep_oldest, keep_best_quality, merge_average
    quality_threshold: float = 0.1

    # Update strategy
    strategy_type: str = "time_based"  # time_based, data_based, hybrid
    time_weight: float = 0.7  # For hybrid strategy
    data_weight: float = 0.3  # For hybrid strategy

    # Recovery and monitoring
    enable_recovery: bool = True
    recovery_timeout_minutes: int = 30
    progress_reporting: bool = True
    detailed_logging: bool = False


class CryptoDataConfig:
    """
    Main configuration class for cryptocurrency data collection.
    
    This class integrates all configuration components and provides
    a unified interface for configuration management.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Parameters
        ----------
        config_file : str, optional
            Path to configuration file (YAML or JSON)
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize sub-configurations with defaults
        self.collection = CollectionConfig()
        self.logging = LoggingConfig()
        self.performance = PerformanceConfig()
        self.incremental = IncrementalConfig()
        self.risk = RiskConfig()
        self.universe = UniverseConfig(name="default", description="Default cryptocurrency universe")
        self.validation = ValidationConfig()
        
        # Load configuration from file if provided
        if config_file:
            self.load_from_file(config_file)
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        # Validate configuration
        self.validate()
    
    def load_from_file(self, config_file: str):
        """
        Load configuration from file.
        
        Parameters
        ----------
        config_file : str
            Path to configuration file
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
            
            self._update_from_dict(config_data)
            self.logger.info(f"Configuration loaded from {config_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration from {config_file}: {str(e)}")
            raise
    
    def save_to_file(self, config_file: str, format: str = "yaml"):
        """
        Save configuration to file.
        
        Parameters
        ----------
        config_file : str
            Path to save configuration
        format : str, default "yaml"
            File format ("yaml" or "json")
        """
        config_data = self.to_dict()
        config_path = Path(config_file)
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if format.lower() in ['yaml', 'yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Configuration saved to {config_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration to {config_file}: {str(e)}")
            raise
    
    def _update_from_dict(self, config_data: Dict[str, Any]):
        """Update configuration from dictionary."""
        
        # Update collection config
        if 'collection' in config_data:
            self._update_dataclass(self.collection, config_data['collection'])
        
        # Update logging config
        if 'logging' in config_data:
            self._update_dataclass(self.logging, config_data['logging'])
        
        # Update performance config
        if 'performance' in config_data:
            self._update_dataclass(self.performance, config_data['performance'])

        # Update incremental config
        if 'incremental' in config_data:
            self._update_dataclass(self.incremental, config_data['incremental'])

        # Update risk config
        if 'risk' in config_data:
            self.risk = RiskConfig.from_dict(config_data['risk'])
        
        # Update universe config
        if 'universe' in config_data:
            universe_data = config_data['universe']
            # Handle FilterConfig conversion
            if 'filters' in universe_data and isinstance(universe_data['filters'], dict):
                universe_data['filters'] = FilterConfig(**universe_data['filters'])
            self.universe = UniverseConfig(**universe_data)
        
        # Update validation config
        if 'validation' in config_data:
            self.validation = ValidationConfig.from_dict(config_data['validation'])
    
    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """Update dataclass object from dictionary."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
            else:
                self.logger.warning(f"Unknown configuration key: {key}")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        env_mappings = {
            # Collection settings
            'CRYPTO_EXCHANGES': ('collection', 'exchanges', lambda x: x.split(',')),
            'CRYPTO_TIMEFRAMES': ('collection', 'timeframes', lambda x: x.split(',')),
            'CRYPTO_OUTPUT_DIR': ('collection', 'output_dir', str),
            'CRYPTO_MAX_WORKERS': ('collection', 'max_workers', int),
            'CRYPTO_LOOKBACK_DAYS': ('collection', 'lookback_days', int),
            
            # Logging settings
            'CRYPTO_LOG_LEVEL': ('logging', 'level', str),
            'CRYPTO_LOG_FILE': ('logging', 'file_path', str),
            
            # Performance settings
            'CRYPTO_CHUNK_SIZE': ('performance', 'chunk_size', int),
            'CRYPTO_ENABLE_CACHING': ('performance', 'enable_caching', lambda x: x.lower() == 'true'),
            'CRYPTO_CACHE_SIZE': ('performance', 'cache_size_limit', int),
        }
        
        for env_var, (section, key, converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    converted_value = converter(env_value)
                    section_obj = getattr(self, section)
                    setattr(section_obj, key, converted_value)
                    self.logger.debug(f"Applied environment override: {env_var}={converted_value}")
                except Exception as e:
                    self.logger.warning(f"Failed to apply environment override {env_var}: {str(e)}")
    
    def validate(self):
        """Validate configuration."""
        errors = []
        
        # Validate exchanges
        if not self.collection.exchanges:
            errors.append("At least one exchange must be specified")

        for exchange in self.collection.exchanges:
            if exchange not in EXCHANGE_CONFIGS:
                errors.append(f"Unsupported exchange: {exchange}")
        
        # Validate timeframes
        for timeframe in self.collection.timeframes:
            if timeframe not in TIMEFRAME_MAPPING:
                errors.append(f"Unsupported timeframe: {timeframe}")
        
        # Validate fields
        for field in self.collection.fields:
            if field not in CRYPTO_FIELDS:
                errors.append(f"Unknown field: {field}")
        
        # Validate file format
        if self.collection.file_format not in ['parquet', 'csv', 'hdf5', 'qlib']:
            errors.append(f"Unsupported file format: {self.collection.file_format}")
        
        # Validate logging level
        if self.logging.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            errors.append(f"Invalid logging level: {self.logging.level}")
        
        # Validate performance settings
        if self.performance.chunk_size <= 0:
            errors.append("Chunk size must be positive")
        
        if self.performance.max_memory_usage <= 0 or self.performance.max_memory_usage > 1:
            errors.append("Max memory usage must be between 0 and 1")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)
        
        self.logger.info("Configuration validation passed")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'collection': asdict(self.collection),
            'logging': asdict(self.logging),
            'performance': asdict(self.performance),
            'incremental': asdict(self.incremental),
            'risk': self.risk.to_dict(),
            'universe': asdict(self.universe),
            'validation': self.validation.to_dict()
        }
    
    def get_exchange_config(self, exchange: str) -> Dict[str, Any]:
        """Get configuration for specific exchange."""
        return EXCHANGE_CONFIGS.get(exchange, DEFAULT_EXCHANGE_CONFIG)
    
    def get_supported_timeframes(self, exchange: str) -> List[str]:
        """Get supported timeframes for exchange."""
        exchange_config = self.get_exchange_config(exchange)
        return exchange_config.get('supported_timeframes', SUPPORTED_TIMEFRAMES)
    
    def get_field_mapping(self) -> Dict[str, str]:
        """Get field mapping for data collection."""
        if self.collection.enable_extended_fields:
            return {**STANDARD_FIELDS, **EXTENDED_FIELDS}
        else:
            return STANDARD_FIELDS
    
    def create_output_path(self, exchange: str, symbol: str, timeframe: str) -> Path:
        """Create output path for data file."""
        base_path = Path(self.collection.output_dir)
        
        # Create directory structure: output_dir/exchange/timeframe/
        dir_path = base_path / exchange / timeframe
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename: symbol.format
        filename = f"{symbol.replace('/', '_')}.{self.collection.file_format}"
        
        return dir_path / filename
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"CryptoDataConfig(\n"
            f"  exchanges={self.collection.exchanges},\n"
            f"  timeframes={self.collection.timeframes},\n"
            f"  output_dir='{self.collection.output_dir}',\n"
            f"  enable_extended_fields={self.collection.enable_extended_fields},\n"
            f"  enable_risk_metrics={self.collection.enable_risk_metrics}\n"
            f")"
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'CryptoDataConfig':
        """
        Create configuration from dictionary.

        Parameters
        ----------
        config_dict : Dict[str, Any]
            Configuration dictionary

        Returns
        -------
        CryptoDataConfig
            Configuration instance
        """
        # Create default config first
        config = cls()

        # Update with provided values
        if 'collection' in config_dict:
            collection_dict = config_dict['collection']
            for key, value in collection_dict.items():
                if hasattr(config.collection, key):
                    setattr(config.collection, key, value)

        if 'validation' in config_dict:
            validation_dict = config_dict['validation']
            for key, value in validation_dict.items():
                if hasattr(config.validation, key):
                    setattr(config.validation, key, value)

        if 'universe' in config_dict:
            universe_dict = config_dict['universe']
            for key, value in universe_dict.items():
                if hasattr(config.universe, key):
                    setattr(config.universe, key, value)

        if 'risk' in config_dict:
            risk_dict = config_dict['risk']
            for key, value in risk_dict.items():
                if hasattr(config.risk, key):
                    setattr(config.risk, key, value)

        return config

    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'CryptoDataConfig':
        """
        Create configuration from YAML string.

        Parameters
        ----------
        yaml_content : str
            YAML configuration string

        Returns
        -------
        CryptoDataConfig
            Configuration instance
        """
        import yaml
        config_dict = yaml.safe_load(yaml_content)
        return cls.from_dict(config_dict)

    @classmethod
    def from_file(cls, file_path: str) -> 'CryptoDataConfig':
        """
        Load configuration from file.

        Parameters
        ----------
        file_path : str
            Path to configuration file (YAML or JSON)

        Returns
        -------
        CryptoDataConfig
            Configuration instance
        """
        file_path = Path(file_path)

        with open(file_path, 'r') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                config_dict = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                import json
                config_dict = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")

        return cls.from_dict(config_dict)


class ConfigFactory:
    """Factory class for creating predefined configurations."""

    @staticmethod
    def create_default_config() -> CryptoDataConfig:
        """Create default configuration."""
        return CryptoDataConfig()

    @staticmethod
    def create_high_frequency_config() -> CryptoDataConfig:
        """Create configuration optimized for high-frequency data collection."""
        config = CryptoDataConfig()

        # High-frequency collection settings
        config.collection.timeframes = ["1min", "5min", "15min", "1h"]
        config.collection.max_workers = 8
        config.collection.rate_limit_delay = 0.05
        config.collection.lookback_days = 30
        config.collection.enable_extended_fields = True

        # Performance optimization
        config.performance.chunk_size = 5000
        config.performance.enable_multiprocessing = True
        config.performance.enable_caching = True
        config.performance.cache_size_limit = 2000

        # High-frequency risk config
        config.risk = RiskConfig.create_high_frequency_config()

        return config

    @staticmethod
    def create_daily_config() -> CryptoDataConfig:
        """Create configuration for daily data collection."""
        config = CryptoDataConfig()

        # Daily collection settings
        config.collection.timeframes = ["day"]
        config.collection.max_workers = 4
        config.collection.lookback_days = 365
        config.collection.enable_risk_metrics = True

        # Daily risk config
        config.risk = RiskConfig.create_daily_config()

        return config

    @staticmethod
    def create_multi_exchange_config() -> CryptoDataConfig:
        """Create configuration for multi-exchange data collection."""
        config = CryptoDataConfig()

        # Multi-exchange settings
        config.collection.exchanges = ["binance", "okx"]
        config.collection.timeframes = ["1h", "day"]
        config.collection.max_workers = 6
        config.collection.enable_extended_fields = True

        # Universe config for multi-exchange
        config.universe.exchanges = ["binance", "okx"]
        config.universe.max_symbols = 100
        config.universe.ranking_criteria = ["volume_24h", "market_cap"]

        return config

    @staticmethod
    def create_research_config() -> CryptoDataConfig:
        """Create configuration for research purposes."""
        config = CryptoDataConfig()

        # Research settings
        config.collection.timeframes = ["1min", "5min", "15min", "30min", "1h", "day"]
        config.collection.enable_extended_fields = True
        config.collection.enable_risk_metrics = True
        config.collection.lookback_days = 730  # 2 years

        # Extended universe
        config.universe.max_symbols = 200
        config.universe.market_types = ["spot", "futures"]

        # Comprehensive risk analysis
        config.risk = RiskConfig.create_crypto_optimized_config()

        # Enhanced validation
        config.validation.enable_anomaly_detection = True
        config.validation.max_missing_ratio = 0.05  # Stricter validation

        return config

    @staticmethod
    def create_production_config() -> CryptoDataConfig:
        """Create configuration for production environment."""
        config = CryptoDataConfig()

        # Production settings
        config.collection.timeframes = ["1h", "day"]
        config.collection.max_workers = 4
        config.collection.retry_attempts = 5
        config.collection.incremental_update = True
        config.collection.file_format = "qlib"
        config.collection.compression = "snappy"
        config.collection.create_qlib_structure = True

        # Conservative performance settings
        config.performance.chunk_size = 10000
        config.performance.max_memory_usage = 0.6
        config.performance.enable_caching = True

        # Production logging
        config.logging.level = "INFO"
        config.logging.file_path = "/var/log/crypto_collector.log"
        config.logging.max_file_size = 50 * 1024 * 1024  # 50MB

        # Conservative risk config
        config.risk = RiskConfig.create_conservative_config()

        return config

    @staticmethod
    def create_minimal_config() -> CryptoDataConfig:
        """Create minimal configuration for basic testing."""
        config = CryptoDataConfig()

        # Minimal settings
        config.collection.exchanges = ["binance"]
        config.collection.timeframes = ["day"]
        config.collection.fields = ["open", "high", "low", "close", "volume"]
        config.collection.max_workers = 1
        config.collection.enable_extended_fields = False
        config.collection.enable_risk_metrics = False
        config.collection.enable_validation = False

        return config

    @staticmethod
    def create_multi_exchange_config() -> CryptoDataConfig:
        """Create configuration for multiple exchanges."""
        config = CryptoDataConfig()

        # Multi-exchange settings
        config.collection.exchanges = ["binance", "okx"]
        config.collection.timeframes = ["1h", "day"]
        config.collection.max_workers = 6
        config.collection.enable_extended_fields = True

        return config
