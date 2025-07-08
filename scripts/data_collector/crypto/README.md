# Cryptocurrency Data Collection Module

A comprehensive cryptocurrency data collection module for the Qlib quantitative framework.

## Directory Structure

```
scripts/data_collector/crypto/
├── readme.md                    # This file
├── __init__.py                  # Package initialization
├── __main__.py                  # CLI entry point
├── cli.py                       # Command-line interface
├── collector.py                 # Main data collector
├── storage_manager.py           # Data storage management
├── qlib_data_generator.py       # Qlib structure generator
├── data_validator.py            # Data validation
├── symbol_discovery.py          # Symbol discovery
├── universe_manager.py          # Universe management
├── universe_filters.py          # Universe filtering
├── timeframe_manager.py         # Timeframe management
├── crypto_field_collector.py    # Field collection
├── config/                      # Configuration modules
│   ├── __init__.py
│   ├── main_config.py          # Main configuration
│   ├── exchanges.py            # Exchange configurations
│   ├── fields.py               # Field definitions
│   ├── timeframes.py           # Timeframe mappings
│   ├── universe_config.py      # Universe configuration
│   ├── validation_config.py    # Validation settings
│   ├── risk_config.py          # Risk management
│   ├── template_manager.py     # Template management
│   └── templates/              # Configuration templates
├── exchange_adapters/           # Exchange-specific adapters
│   ├── __init__.py
│   ├── base_adapter.py         # Base adapter interface
│   ├── binance_adapter.py      # Binance adapter
│   └── okx_adapter.py          # OKX adapter
├── incremental/                 # Incremental update system
│   ├── __init__.py
│   ├── manager.py              # Update manager
│   ├── update_state.py         # State management
│   ├── state_storage.py        # State persistence
│   ├── update_strategy.py      # Update strategies
│   └── conflict_resolver.py    # Conflict resolution
├── risk_metrics/                # Risk calculation modules
│   ├── __init__.py
│   ├── base_calculator.py      # Base calculator
│   ├── risk_metrics_manager.py # Risk manager
│   ├── volatility_calculator.py
│   ├── sharpe_calculator.py
│   ├── beta_calculator.py
│   ├── var_calculator.py
│   └── drawdown_calculator.py
├── validators/                  # Data validation modules
│   ├── __init__.py
│   ├── base_validator.py       # Base validator
│   ├── anomaly_validator.py    # Anomaly detection
│   ├── completeness_validator.py
│   ├── consistency_validator.py
│   ├── price_validator.py
│   ├── timeseries_validator.py
│   └── volume_validator.py
├── scripts/                     # Utility scripts
│   └── enhanced_collector.py   # Enhanced collection script
├── tests/                       # Test files
│   ├── __init__.py
│   ├── test_storage_integration.py    # Storage integration tests
│   ├── test_storage_simple.py         # Simple storage tests
│   ├── test_integration_simple.py     # Simple integration tests
│   ├── test_incremental_integration.py # Incremental update tests
│   ├── test_universe_basic.py         # Basic universe management tests
│   ├── test_universe_simple.py        # Simple universe management tests
│   └── test_universe_management.py    # Comprehensive universe management tests
├── examples/                    # Example usage files
│   ├── cli_usage_examples.py    # CLI usage examples
│   ├── config_example.py        # Configuration examples
│   ├── incremental_update_example.py
│   ├── risk_metrics_example.py
│   ├── template_usage_example.py
│   ├── validation_example.py
│   └── storage_debug_example.py # Storage debugging example
└── docs/                        # Documentation
    ├── CLI_readme.md            # CLI documentation
    ├── INCREMENTAL_UPDATE_INTEGRATION.md
    └── incremental_readme.md    # Incremental update docs
```

## Quick Start

### Installation

1. Ensure you have Python 3.8+ installed
2. Install dependencies:
   ```bash
   pip install qlib ccxt pandas numpy
   ```

### Basic Usage

```python
from qlib.data.collector.crypto import CryptoStorageManager

# Initialize storage manager
storage = CryptoStorageManager(data_dir="./crypto_data")

# Save OHLCV data
storage.save_ohlcv_data(data, "binance_btc_usdt", "1h")

# Load data
close_data = storage.load_feature_data("binance_btc_usdt", "close", "1h")
```

### Running Tests

```bash
# Run all tests
cd tests/
python test_storage_integration.py

# Run simple tests
python test_storage_simple.py
```

### Examples

Check the `examples/` directory for detailed usage examples:

- `storage_debug_example.py` - Storage functionality and debugging
- `config_example.py` - Configuration setup
- `cli_usage_examples.py` - Command-line usage

### Documentation

See the `docs/` directory for detailed documentation:

- `CLI_readme.md` - Command-line interface guide
- `INCREMENTAL_UPDATE_INTEGRATION.md` - Incremental update system
- `incremental_readme.md` - Incremental update details

## Features

- ✅ **Multi-exchange support** via CCXT
- ✅ **Qlib format compatibility** with .bin storage
- ✅ **Frequency conversion** (crypto → qlib formats)
- ✅ **OHLCV data collection** and storage
- ✅ **Data validation** and quality checks
- ✅ **Incremental updates** for efficient data collection
- ✅ **Risk metrics** calculation
- ✅ **CLI interface** for easy usage
- ✅ **Comprehensive testing** suite

## License

Licensed under the MIT License. See the main Qlib repository for details.
