# Crypto Data Collection Examples

This directory contains examples for cryptocurrency data collection using Qlib's crypto data collector.

## 📁 Contents

- `cli_usage_examples.py` - Command-line interface usage examples
- `config_example.py` - Configuration management examples
- `incremental_update_example.py` - Incremental data update examples
- `validation_example.py` - Data validation examples
- `template_usage_example.py` - Template configuration examples
- `risk_metrics_example.py` - Risk metrics calculation examples
- `storage_debug_example.py` - Storage debugging examples
- `perpetual_usage_example.py` - Perpetual contract data examples

## 🚀 Quick Start

### Basic Data Collection

```bash
# Navigate to the data collection directory
cd /Users/alanguo/Projects/qlib/examples/crypto/data_collection

# Run CLI usage example
python cli_usage_examples.py

# Run configuration example
python config_example.py

# Run validation example
python validation_example.py
```

### Data Collector CLI

```bash
# Navigate to crypto data collector
cd /Users/alanguo/Projects/qlib/scripts/data_collector/crypto

# Run basic collection
python -m crypto_collector --config config/templates/default.yaml

# Run incremental update
python -m crypto_collector --config config/templates/default.yaml --incremental
```

## 📊 Data Collection Features

### 1. **Multi-Exchange Support**
- Binance Spot & Futures
- OKX Spot & Futures
- Extensible to other exchanges

### 2. **Multiple Timeframes**
- 1min, 5min, 15min, 30min, 1h, 4h, 1d, 1w
- Automatic timeframe conversion
- Optimized storage

### 3. **Data Validation**
- Price validation
- Volume validation
- Completeness checks
- Anomaly detection

### 4. **Incremental Updates**
- Production-ready incremental collection
- Conflict resolution
- State management
- Recovery mechanisms

## 🔧 Configuration Examples

### Basic Configuration

```yaml
# basic_collection.yaml
exchanges:
  binance:
    spot: true
    futures: false
    
timeframes: ["1d", "1h", "15min"]
universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
```

### Production Configuration

```yaml
# production.yaml
exchanges:
  binance:
    spot: true
    futures: true
  okx:
    spot: true
    futures: true
    
timeframes: ["1d", "4h", "1h", "15min"]
universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]

validation:
  enabled: true
  strict_mode: true
  
incremental:
  enabled: true
  update_interval: 300  # 5 minutes
```

## 📚 Related Documentation

- [Data Collector Usage Guide](../../../scripts/data_collector/crypto/docs/usage.md)
- [Testing Plan](../../../scripts/data_collector/crypto/docs/testing_plan.md)
- [Crypto Factor Examples](../factors/) - Using collected data for factors

## ⚠️ Requirements

- CCXT library for exchange connections
- Sufficient API rate limits
- Storage space for historical data
- Python 3.8+

## 🔗 Related Examples

- [Factor Examples](../factors/) - Using collected data for factors
- [BTC Dominance Strategy](../btcdom2/) - Complete trading strategy
- [Main Examples](../../) - Other crypto examples

---

**Last Updated**: January 2025  
**Status**: Production Ready