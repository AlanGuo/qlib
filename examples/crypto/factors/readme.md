# Crypto Factor Examples

This directory contains examples for working with cryptocurrency factors in Qlib.

## 📁 Contents

- `crypto_factors_integration_example.py` - Complete factor integration example
- `crypto_factor_dl_example.py` - Factor data loading example
- `factor_expressions_example.py` - Factor expression examples

## 🚀 Quick Start

### Running Factor Examples

```bash
# Navigate to the factors directory
cd /Users/alanguo/Projects/qlib/examples/crypto/factors

# Run the integration example
python crypto_factors_integration_example.py

# Run the data loading example
python crypto_factor_dl_example.py

# Run the expression example
python factor_expressions_example.py
```

## 📊 Factor Categories

The examples demonstrate usage of 171 cryptocurrency factors across 5 categories:

1. **Basic Factors (24)**: Price, volume, and basic technical indicators
2. **Decline Factors (24)**: Multi-timeframe decline analysis
3. **Volume Factors (30)**: Volume analysis and anomaly detection
4. **Momentum Factors (51)**: Momentum and trend analysis
5. **Funding Rate Factors (42)**: Funding rate analysis for perpetual contracts

## 🔧 Factor Integration

### Basic Usage

```python
from qlib.contrib.data.crypto_factors import CryptoFactorDL

# Initialize crypto factor data loader
factor_dl = CryptoFactorDL()

# Load factors for specific instruments
instruments = ["binance_spot_btcusdt", "binance_spot_ethusdt"]
factors = factor_dl.load_factors(instruments)
```

### Advanced Configuration

```python
from qlib.contrib.data.crypto_factors import CryptoFactorDL, FactorConfig

# Configure factor settings
config = FactorConfig(
    factor_categories=["decline", "volume", "momentum"],
    lookback_days=30,
    normalization="zscore"
)

factor_dl = CryptoFactorDL(config=config)
```

## 📚 Related Documentation

- [Crypto Factor Integration Guide](../../../docs/crypto/crypto_factors_integration_guide.md)
- [Crypto Factor Library Report](../../../docs/crypto/crypto_factor_library_report.md)
- [BTC Dominance Strategy](../btcdom2/readme.md)

## ⚠️ Requirements

- Complete crypto data (OHLCV + funding rates)
- Qlib with crypto data provider
- Python 3.8+

## 🔗 Related Examples

- [BTC Dominance Strategy](../btcdom2/) - Uses factors for trading strategy
- [Data Collection](../data_collection/) - How to collect factor data
- [Main Examples](../../) - Other crypto examples

---

**Last Updated**: January 2025  
**Status**: Production Ready