# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Example usage of the unified configuration system.

This example demonstrates how to use the configuration management system
for cryptocurrency data collection.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    CryptoDataConfig,
    ConfigFactory,
    RiskConfig,
    UniverseConfig,
    FilterConfig,
    ValidationConfig
)


def example_basic_configuration():
    """Example of basic configuration usage."""
    print("=== Basic Configuration Example ===")
    
    # Create default configuration
    config = CryptoDataConfig()
    
    print("Default Configuration:")
    print(f"  Exchanges: {config.collection.exchanges}")
    print(f"  Timeframes: {config.collection.timeframes}")
    print(f"  Output directory: {config.collection.output_dir}")
    print(f"  Max workers: {config.collection.max_workers}")
    print(f"  Enable risk metrics: {config.collection.enable_risk_metrics}")
    
    # Modify configuration
    config.collection.exchanges = ["binance", "okx"]
    config.collection.timeframes = ["1h", "1d"]
    config.collection.enable_extended_fields = True
    config.collection.output_dir = "./my_crypto_data"
    
    print("\nModified Configuration:")
    print(f"  Exchanges: {config.collection.exchanges}")
    print(f"  Timeframes: {config.collection.timeframes}")
    print(f"  Extended fields: {config.collection.enable_extended_fields}")
    print(f"  Output directory: {config.collection.output_dir}")


def example_predefined_configurations():
    """Example of using predefined configurations."""
    print("\n=== Predefined Configurations Example ===")
    
    # High-frequency configuration
    hf_config = ConfigFactory.create_high_frequency_config()
    print("High-frequency Configuration:")
    print(f"  Timeframes: {hf_config.collection.timeframes}")
    print(f"  Max workers: {hf_config.collection.max_workers}")
    print(f"  Rate limit delay: {hf_config.collection.rate_limit_delay}")
    print(f"  Cache size: {hf_config.performance.cache_size_limit}")
    
    # Daily configuration
    daily_config = ConfigFactory.create_daily_config()
    print("\nDaily Configuration:")
    print(f"  Timeframes: {daily_config.collection.timeframes}")
    print(f"  Lookback days: {daily_config.collection.lookback_days}")
    print(f"  Risk metrics enabled: {daily_config.collection.enable_risk_metrics}")
    
    # Research configuration
    research_config = ConfigFactory.create_research_config()
    print("\nResearch Configuration:")
    print(f"  Timeframes: {research_config.collection.timeframes}")
    print(f"  Max symbols: {research_config.universe.max_symbols}")
    print(f"  Market types: {research_config.universe.market_types}")
    print(f"  Lookback days: {research_config.collection.lookback_days}")
    
    # Production configuration
    prod_config = ConfigFactory.create_production_config()
    print("\nProduction Configuration:")
    print(f"  Timeframes: {prod_config.collection.timeframes}")
    print(f"  File format: {prod_config.collection.file_format}")
    print(f"  Logging level: {prod_config.logging.level}")
    print(f"  Log file: {prod_config.logging.file_path}")


def example_configuration_file_operations():
    """Example of saving and loading configuration files."""
    print("\n=== Configuration File Operations Example ===")
    
    # Create a custom configuration
    config = ConfigFactory.create_multi_exchange_config()
    config.collection.symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
    config.collection.lookback_days = 180
    config.universe.max_symbols = 50
    
    # Create temporary directory for examples
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Save as YAML
        yaml_file = temp_path / "config.yaml"
        config.save_to_file(str(yaml_file), format="yaml")
        print(f"Configuration saved to YAML: {yaml_file}")
        
        # Save as JSON
        json_file = temp_path / "config.json"
        config.save_to_file(str(json_file), format="json")
        print(f"Configuration saved to JSON: {json_file}")
        
        # Load from YAML
        loaded_config = CryptoDataConfig(str(yaml_file))
        print(f"Configuration loaded from YAML:")
        print(f"  Exchanges: {loaded_config.collection.exchanges}")
        print(f"  Symbols: {loaded_config.collection.symbols}")
        print(f"  Max symbols: {loaded_config.universe.max_symbols}")
        
        # Load from JSON
        json_config = CryptoDataConfig(str(json_file))
        print(f"Configuration loaded from JSON:")
        print(f"  Exchanges: {json_config.collection.exchanges}")
        print(f"  Lookback days: {json_config.collection.lookback_days}")


def example_environment_variables():
    """Example of environment variable overrides."""
    print("\n=== Environment Variables Example ===")
    
    # Set environment variables
    os.environ['CRYPTO_EXCHANGES'] = 'binance,okx'
    os.environ['CRYPTO_TIMEFRAMES'] = '1h,4h,1d'
    os.environ['CRYPTO_OUTPUT_DIR'] = '/tmp/crypto_data'
    os.environ['CRYPTO_MAX_WORKERS'] = '8'
    os.environ['CRYPTO_LOG_LEVEL'] = 'DEBUG'
    
    # Create configuration (will apply environment overrides)
    config = CryptoDataConfig()
    
    print("Configuration with environment overrides:")
    print(f"  Exchanges: {config.collection.exchanges}")
    print(f"  Timeframes: {config.collection.timeframes}")
    print(f"  Output directory: {config.collection.output_dir}")
    print(f"  Max workers: {config.collection.max_workers}")
    print(f"  Log level: {config.logging.level}")
    
    # Clean up environment variables
    for var in ['CRYPTO_EXCHANGES', 'CRYPTO_TIMEFRAMES', 'CRYPTO_OUTPUT_DIR', 
                'CRYPTO_MAX_WORKERS', 'CRYPTO_LOG_LEVEL']:
        if var in os.environ:
            del os.environ[var]


def example_custom_universe_configuration():
    """Example of custom universe configuration."""
    print("\n=== Custom Universe Configuration Example ===")
    
    # Create custom filter configuration
    custom_filter = FilterConfig(
        min_volume_24h=1000000,  # Minimum 1M volume
        min_market_cap=100000000,  # Minimum 100M market cap
        base_assets=["BTC", "ETH", "BNB", "ADA", "DOT"],
        quote_assets=["USDT", "BUSD"],
        market_types=["spot"]
    )
    
    # Create custom universe configuration
    custom_universe = UniverseConfig(
        name="top_crypto_universe",
        description="Top cryptocurrency universe for trading",
        exchanges=["binance", "okx"],
        market_types=["spot"],
        filters=custom_filter,
        max_symbols=30,
        ranking_criteria=["volume_24h", "market_cap"],
        ranking_order="desc",
        update_frequency="daily"
    )
    
    # Create configuration with custom universe
    config = CryptoDataConfig()
    config.universe = custom_universe
    config.collection.exchanges = ["binance", "okx"]
    config.collection.enable_extended_fields = True
    
    print("Custom Universe Configuration:")
    print(f"  Universe name: {config.universe.name}")
    print(f"  Exchanges: {config.universe.exchanges}")
    print(f"  Max symbols: {config.universe.max_symbols}")
    print(f"  Base assets filter: {config.universe.filters.base_assets}")
    print(f"  Min volume 24h: {config.universe.filters.min_volume_24h}")
    print(f"  Ranking criteria: {config.universe.ranking_criteria}")


def example_risk_configuration():
    """Example of risk configuration customization."""
    print("\n=== Risk Configuration Example ===")
    
    # Create custom risk configuration
    custom_risk = RiskConfig(
        volatility_windows=[7, 14, 30, 90],
        var_confidence_levels=[0.01, 0.05],
        var_methods=["historical", "parametric", "monte_carlo"],
        risk_free_rate=0.02,
        periods_per_year=365
    )
    
    # Create configuration with custom risk settings
    config = CryptoDataConfig()
    config.risk = custom_risk
    config.collection.enable_risk_metrics = True
    
    print("Custom Risk Configuration:")
    print(f"  Volatility windows: {config.risk.volatility_windows}")
    print(f"  VaR confidence levels: {config.risk.var_confidence_levels}")
    print(f"  VaR methods: {config.risk.var_methods}")
    print(f"  Risk-free rate: {config.risk.risk_free_rate}")
    print(f"  Periods per year: {config.risk.periods_per_year}")


def example_validation_configuration():
    """Example of validation configuration."""
    print("\n=== Validation Configuration Example ===")
    
    # Create custom validation configuration
    custom_validation = ValidationConfig(
        enable_price_validation=True,
        enable_volume_validation=True,
        enable_anomaly_detection=True,
        max_price_change_pct=30.0,  # 30% max price change
        price_outlier_threshold=2.5,
        volume_outlier_threshold=4.0,
        max_missing_ratio=0.05  # 5% max missing values
    )
    
    # Create configuration with custom validation
    config = CryptoDataConfig()
    config.validation = custom_validation
    config.collection.enable_validation = True
    
    print("Custom Validation Configuration:")
    print(f"  Price validation: {config.validation.enable_price_validation}")
    print(f"  Anomaly detection: {config.validation.enable_anomaly_detection}")
    print(f"  Max price change: {config.validation.max_price_change_pct}%")
    print(f"  Price outlier threshold: {config.validation.price_outlier_threshold}")
    print(f"  Max missing ratio: {config.validation.max_missing_ratio}")


def main():
    """Run all configuration examples."""
    print("Cryptocurrency Data Collection Configuration Examples")
    print("=" * 60)
    
    try:
        example_basic_configuration()
        example_predefined_configurations()
        example_configuration_file_operations()
        example_environment_variables()
        example_custom_universe_configuration()
        example_risk_configuration()
        example_validation_configuration()
        
        print("\n" + "=" * 60)
        print("All configuration examples completed successfully!")
        
    except Exception as e:
        print(f"Error running configuration examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
