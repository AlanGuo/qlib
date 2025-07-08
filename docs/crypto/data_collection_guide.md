# Crypto Data Collection Guide

This guide covers the cryptocurrency data collection system in Qlib, including setup, usage, and best practices.

## 📋 Overview

The crypto data collector provides comprehensive cryptocurrency market data collection with:

- **Multi-exchange support**: Binance, OKX, and more
- **Multiple timeframes**: 1min to 1w
- **Production-ready**: Incremental updates, validation, monitoring
- **Extensible**: Easy to add new exchanges and data types

## 🚀 Quick Start

### Basic Setup

```bash
# Navigate to crypto data collector
cd /Users/alanguo/Projects/qlib/scripts/data_collector/crypto

# Install dependencies
pip install -r requirements.txt

# Run basic collection
python -m crypto_collector --config config/templates/default.yaml
```

### Configuration

```yaml
# config/templates/basic.yaml
exchanges:
  binance:
    spot: true
    futures: false
    
timeframes: ["1d", "1h"]
universe: ["BTCUSDT", "ETHUSDT"]

storage:
  qlib_data_path: "./crypto_data"
  
validation:
  enabled: true
```

## 📊 Data Collection Features

### 1. **Exchange Support**

Currently supported exchanges:
- **Binance**: Spot & Futures
- **OKX**: Spot & Futures

Adding new exchanges:
```python
from exchange_adapters.base_adapter import BaseExchangeAdapter

class NewExchangeAdapter(BaseExchangeAdapter):
    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
        # Implementation here
        pass
```

### 2. **Timeframe Management**

Supported timeframes:
- **High frequency**: 1min, 5min, 15min, 30min
- **Medium frequency**: 1h, 4h, 8h, 12h
- **Low frequency**: 1d, 1w

Automatic conversion between timeframes is supported.

### 3. **Data Validation**

Multiple validation layers:
- **Price validation**: Check for outliers and errors
- **Volume validation**: Ensure volume data integrity
- **Completeness**: Check for missing data
- **Consistency**: Cross-timeframe validation

### 4. **Incremental Updates**

Production-ready incremental collection:
```python
from incremental.manager import IncrementalManager

manager = IncrementalManager(config)
manager.run_incremental_update()
```

## 🔧 Configuration Guide

### Template Configurations

Seven pre-built templates:

1. **default.yaml**: Basic configuration for testing
2. **production.yaml**: Production-ready setup
3. **research.yaml**: Extended universe for research
4. **high_frequency.yaml**: High-frequency data collection
5. **multi_exchange.yaml**: Multiple exchange setup
6. **simple.yaml**: Minimal configuration
7. **live_test_4_1.yaml**: Live testing configuration

### Custom Configuration

```yaml
# Custom configuration example
exchanges:
  binance:
    spot: true
    futures: true
    rate_limit: 1200  # requests per minute
  okx:
    spot: true
    futures: false
    rate_limit: 600

timeframes: ["1d", "4h", "1h", "15min"]

universe:
  - "BTCUSDT"
  - "ETHUSDT"
  - "BNBUSDT"
  - "SOLUSDT"
  - "ADAUSDT"

storage:
  qlib_data_path: "./crypto_data"
  backup_enabled: true
  compression: true

validation:
  enabled: true
  strict_mode: true
  max_price_change: 0.5  # 50% max price change
  min_volume_threshold: 1000

incremental:
  enabled: true
  update_interval: 300  # 5 minutes
  max_retries: 3
  recovery_enabled: true

logging:
  level: "INFO"
  file: "logs/crypto_collector.log"
  max_size: "100MB"
  backup_count: 5
```

## 🛠️ Command Line Usage

### Basic Commands

```bash
# Basic collection
python -m crypto_collector --config config/templates/default.yaml

# Incremental update
python -m crypto_collector --config config/templates/default.yaml --incremental

# Specific timeframe
python -m crypto_collector --config config/templates/default.yaml --timeframes 1d,1h

# Specific exchange
python -m crypto_collector --config config/templates/default.yaml --exchanges binance

# Debug mode
python -m crypto_collector --config config/templates/default.yaml --debug

# Test configuration
python -m crypto_collector --config config/templates/default.yaml --test
```

### Advanced Usage

```bash
# Full production run
python -m crypto_collector \
  --config config/templates/production.yaml \
  --incremental \
  --monitor \
  --log-level INFO

# Recovery mode
python -m crypto_collector \
  --config config/templates/production.yaml \
  --recovery \
  --start-date 2024-01-01

# Validation only
python -m crypto_collector \
  --config config/templates/production.yaml \
  --validate-only \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

## 📈 Monitoring and Maintenance

### Health Monitoring

```python
from monitor_stability_test import StabilityMonitor

monitor = StabilityMonitor(config)
health_metrics = monitor.run_health_check()
```

### Performance Metrics

Key metrics to monitor:
- **Collection rate**: Records per second
- **Error rate**: Failed requests percentage
- **Data quality**: Validation pass rate
- **Storage efficiency**: Compression ratio

### Maintenance Tasks

Regular maintenance:
- **Data validation**: Weekly full validation
- **Storage cleanup**: Remove temporary files
- **Index optimization**: Rebuild indexes
- **Backup verification**: Test backup integrity

## 🔗 Integration with Qlib

### Data Provider Setup

```python
import qlib
from qlib.config import REG_CN

# Initialize qlib with crypto data
qlib.init(provider_uri="./crypto_data", region=REG_CN)

# Load crypto data
from qlib.data import D
data = D.features(["binance_spot_btcusdt"], ["$close", "$volume"])
```

### Factor Integration

```python
from qlib.contrib.data.crypto_factors import CryptoFactorDL

# Load crypto factors
factor_dl = CryptoFactorDL()
factors = factor_dl.load_factors(["binance_spot_btcusdt"])
```

## ⚠️ Best Practices

### 1. **Rate Limiting**
- Respect exchange rate limits
- Use appropriate intervals between requests
- Implement exponential backoff for errors

### 2. **Data Quality**
- Always enable validation
- Monitor for data gaps
- Implement data quality alerts

### 3. **Storage Management**
- Use compression for historical data
- Implement data retention policies
- Regular backup verification

### 4. **Error Handling**
- Implement robust error recovery
- Log all errors for analysis
- Use circuit breaker patterns

### 5. **Monitoring**
- Set up alerting for failures
- Monitor collection performance
- Track data quality metrics

## 🔗 Related Documentation

- [Usage Guide](../../../scripts/data_collector/crypto/docs/usage.md)
- [Testing Plan](../../../scripts/data_collector/crypto/docs/testing_plan.md)
- [Factor Examples](../factors/) - Using collected data
- [Strategy Examples](../btcdom2/) - Complete trading strategies

---

**Last Updated**: January 2025  
**Version**: v1.0  
**Status**: Production Ready