# Crypto Data Collector Usage Guide

This guide explains how to use the cryptocurrency data collection module from different locations and with different execution methods.

## Execution Methods

The crypto data collector supports multiple execution methods to provide flexibility for different use cases:

### 1. From Project Root (Recommended)

You can run the crypto collector from the qlib project root directory using several methods:

#### Using Python Module Execution
```bash
# From qlib project root
python -m scripts.data_collector.crypto --help
python -m scripts.data_collector.crypto collect --exchanges binance --timeframes day --symbols BTC/USDT
```

#### Using Direct Script Execution
```bash
# From qlib project root  
python scripts/data_collector/crypto/collector.py --help
python scripts/data_collector/crypto/collector.py collect --exchanges binance --timeframes day --symbols BTC/USDT
```

### 2. From Crypto Directory

If you prefer to work within the crypto module directory:

```bash
# Navigate to crypto directory
cd scripts/data_collector/crypto

# Run CLI directly
python cli.py collect --exchanges binance --timeframes day --symbols BTC/USDT

# Or use collector.py
python collector.py collect --exchanges binance --timeframes day --symbols BTC/USDT
```

## Available Commands

### Data Collection

#### Basic Collection
```bash
# Collect daily data from Binance
python scripts/data_collector/crypto/collector.py collect \
    --exchanges binance \
    --timeframes day \
    --symbols BTC/USDT ETH/USDT

# Collect hourly data from multiple exchanges
python scripts/data_collector/crypto/collector.py collect \
    --exchanges binance okx \
    --timeframes 1h \
    --symbols BTC/USDT ETH/USDT ADA/USDT
```

#### Using Configuration Templates
```bash
# Use predefined template
python scripts/data_collector/crypto/collector.py collect --template production

# List available templates
python scripts/data_collector/crypto/collector.py templates --action list

# Show template details
python scripts/data_collector/crypto/collector.py templates --action show --template_name production
```

### Data Validation

```bash
# Validate collected data
python scripts/data_collector/crypto/collector.py validate --data_dir ./data

# Validate with specific configuration
python scripts/data_collector/crypto/collector.py validate \
    --data_dir ./data \
    --config_file config/my_config.json
```

### Incremental Updates

```bash
# Update data incrementally
python scripts/data_collector/crypto/collector.py incremental_update --action update

# Check incremental update status
python scripts/data_collector/crypto/collector.py incremental_update --action status

# Reset incremental update state
python scripts/data_collector/crypto/collector.py incremental_update --action reset
```

## Configuration

### Using Configuration Files

```bash
# Use custom configuration file
python scripts/data_collector/crypto/collector.py collect \
    --config_file config/my_custom_config.json

# Override config with command line arguments
python scripts/data_collector/crypto/collector.py collect \
    --config_file config/base_config.json \
    --exchanges binance \
    --symbols BTC/USDT
```

### Template Management

```bash
# List all available templates
python scripts/data_collector/crypto/collector.py templates --action list

# Create new template (interactive)
python scripts/data_collector/crypto/collector.py templates --action create --template_name my_template

# Show template configuration
python scripts/data_collector/crypto/collector.py templates --action show --template_name production
```

## Advanced Usage

### Full CLI Interface

For advanced users who need access to all CLI features:

```bash
# Using the full CLI from project root
python -m scripts.data_collector.crypto collect \
    --template production \
    --exchanges binance okx \
    --timeframes day 1h \
    --symbols BTC/USDT ETH/USDT \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --output-dir ./crypto_data \
    --enable-validation \
    --enable-risk-metrics \
    --max-workers 4
```

### Dry Run Mode

Test your configuration without actually collecting data:

```bash
python scripts/data_collector/crypto/collector.py collect \
    --exchanges binance \
    --timeframes day \
    --symbols BTC/USDT \
    --dry-run
```

## Testing

The test suite continues to work as before:

```bash
# Run all tests from crypto directory
cd scripts/data_collector/crypto
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_cli_functions.py -v
python -m pytest tests/test_config_system.py -v
python -m pytest tests/test_exchange_adapters.py -v
```

## Compatibility

### With Existing Qlib Data Collectors

The crypto module is designed to be compatible with other qlib data collectors:

```bash
# Similar to other collectors like yahoo or cn_index
python scripts/data_collector/crypto/collector.py collect --exchanges binance --timeframes day
python scripts/data_collector/yahoo/collector.py download_data --region CN --interval 1d
python scripts/data_collector/cn_index/collector.py --index_name CSI300 --method parse_instruments
```

### Fire.Fire Integration

The collector.py uses Fire for command-line interface, similar to other qlib collectors:

```bash
# All these work with Fire's automatic argument parsing
python scripts/data_collector/crypto/collector.py collect --help
python scripts/data_collector/crypto/collector.py validate --help
python scripts/data_collector/crypto/collector.py templates --help
```

## Troubleshooting

### Import Issues

If you encounter import errors:

1. Make sure you're running from the correct directory
2. Check that all required dependencies are installed
3. Verify the Python path includes the necessary modules

### Configuration Issues

If configuration loading fails:

1. Check that configuration files exist and are valid JSON/YAML
2. Verify template names are correct (use `templates --action list`)
3. Ensure output directories are writable

### Connection Issues

If exchange connections fail:

1. Check your internet connection
2. Verify API keys if using authenticated endpoints
3. Check rate limiting settings
4. Ensure exchange is currently supported

## Examples

### Complete Data Collection Workflow

```bash
# 1. List available templates
python scripts/data_collector/crypto/collector.py templates --action list

# 2. Collect data using template
python scripts/data_collector/crypto/collector.py collect --template production

# 3. Validate collected data
python scripts/data_collector/crypto/collector.py validate

# 4. Set up incremental updates
python scripts/data_collector/crypto/collector.py incremental_update --action update
```

### Custom Configuration Workflow

```bash
# 1. Create custom config (manually edit config file)
# 2. Test with dry run
python scripts/data_collector/crypto/collector.py collect \
    --config_file config/my_config.json \
    --dry-run

# 3. Run actual collection
python scripts/data_collector/crypto/collector.py collect \
    --config_file config/my_config.json

# 4. Validate results
python scripts/data_collector/crypto/collector.py validate \
    --config_file config/my_config.json
```

This flexible execution model ensures the crypto data collector can be used in various environments and workflows while maintaining compatibility with existing qlib patterns.