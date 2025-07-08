# Cryptocurrency Strategy Examples

This directory contains examples and configurations for cryptocurrency trading strategies in Qlib.

## 📂 Directory Contents

### BTC Dominance Strategy (BtcDom2)
- `btcdom2/` - Complete BTC Dominance Strategy implementation
  - `btcdom2_strategy_example.py` - Comprehensive usage examples
  - `btcdom2_strategy_configs.yaml` - 7 strategy configuration templates
  - `workflow_config_btcdom2_strategy.yaml` - Qlib workflow configuration
  - `readme.md` - Detailed strategy documentation

### Crypto Factor Examples
- `factors/` - Cryptocurrency factor examples and integration
  - `crypto_factors_integration_example.py` - Complete factor integration
  - `crypto_factor_dl_example.py` - Factor data loading
  - `factor_expressions_example.py` - Factor expression examples
  - `readme.md` - Factor usage documentation

### Data Collection Examples
- `data_collection/` - Cryptocurrency data collection examples
  - `cli_usage_examples.py` - CLI usage examples
  - `config_example.py` - Configuration examples
  - `incremental_update_example.py` - Incremental update examples
  - `validation_example.py` - Data validation examples
  - `readme.md` - Data collection documentation

## 🚀 BTC Dominance Strategy (BtcDom2)

The BTC Dominance Strategy is a sophisticated cryptocurrency trading strategy that:

- **Multi-Factor Analysis**: Uses 171 crypto-specific factors across 5 categories
- **BTC Dominance Focus**: Optimized for periods when BTC dominance is increasing
- **Dynamic Capital Allocation**: Manages allocation between BTC spot and altcoin shorts
- **Risk Management**: 5-layer risk protection system
- **24/7 Trading**: Supports continuous cryptocurrency markets

### Key Features

1. **Factor Categories**:
   - Basic (24 factors)
   - Decline (24 factors) 
   - Volume (30 factors)
   - Momentum (51 factors)
   - Funding Rate (42 factors)

2. **Weighting Schemes**:
   - Equal Weight
   - Factor Weighted (Softmax normalized)
   - Volatility Weighted (downside volatility)
   - Risk Parity (multi-dimensional risk)

3. **Rebalancing Triggers**:
   - Time-based (4h, 8h, 12h, 1d)
   - Performance-based (turnover >70%)
   - Risk-based (volatility spikes)
   - Market-based (BTC moves >5%)

4. **Risk Controls**:
   - Individual position stop loss (15%)
   - Portfolio stop loss (10%)
   - Maximum drawdown (20%)
   - Position correlation limits (70%)
   - Emergency market conditions

## 🔧 Quick Start

### Basic Usage
```python
from qlib.contrib.strategy.btcdom2_strategy import create_btcdom2_strategy

# Create default strategy
strategy = create_btcdom2_strategy()

# Custom configuration
strategy = create_btcdom2_strategy(
    rebalance_frequency="8h",
    num_short_positions=10,
    btc_spot_ratio=0.5,
    weighting_scheme="factor_weighted"
)
```

### Advanced Configuration
```python
from qlib.contrib.strategy.btcdom2_strategy import BtcDom2Strategy, BtcDom2Config

config = BtcDom2Config(
    rebalance_frequency=RebalanceFrequency.HOURLY_8,
    factor_lookback_days=14,
    num_short_positions=10,
    btc_spot_ratio=0.5,
    weighting_scheme=WeightingScheme.FACTOR_WEIGHTED,
    # ... additional parameters
)

strategy = BtcDom2Strategy(config=config)
```

## 📊 Configuration Templates

Seven pre-configured templates are available:

1. **Conservative**: 70% BTC, daily rebalancing, equal weight
2. **Aggressive**: 30% BTC, 4h rebalancing, factor weighted
3. **Balanced**: 50% BTC, 8h rebalancing, volatility weighted
4. **Research**: 40% BTC, 20 positions, all factors
5. **High-Frequency**: 4h rebalancing, strict liquidity
6. **Risk-Managed**: Risk parity, multiple controls
7. **BTC Dominance Focus**: 65% BTC, dominance optimized

## 🧪 Running Examples

```bash
# Run the comprehensive example
cd /Users/alanguo/Projects/qlib/examples/crypto/btcdom2
python btcdom2_strategy_example.py

# Run with Qlib workflow
cd /Users/alanguo/Projects/qlib
qrun examples/crypto/btcdom2/workflow_config_btcdom2_strategy.yaml

# Run factor examples
cd /Users/alanguo/Projects/qlib/examples/crypto/factors
python crypto_factors_integration_example.py

# Run data collection examples
cd /Users/alanguo/Projects/qlib/examples/crypto/data_collection
python cli_usage_examples.py
```

## 📈 Expected Performance

Based on strategy design:
- **Annual Return**: 15-30%
- **Maximum Drawdown**: <15%
- **Sharpe Ratio**: >1.5
- **Win Rate**: >55%
- **BTC Correlation**: <0.8

## 📚 Documentation

For detailed documentation, see:
- [BTC Dominance Strategy Guide](../../docs/crypto/BTCDOM2_STRATEGY_GUIDE.md)
- [Crypto Factors Integration Guide](../../docs/crypto/CRYPTO_FACTORS_INTEGRATION_GUIDE.md)
- [Crypto Factor Library Report](../../docs/crypto/CRYPTO_FACTOR_LIBRARY_REPORT.md)

## ⚠️ Requirements

- Qlib with crypto data provider
- Cryptocurrency market data (OHLCV + funding rates)
- Python 3.8+
- Dependencies: numpy, pandas, qlib

## 🔗 Related Examples

- [Traditional Alpha Examples](../benchmarks/)
- [High-Frequency Examples](../highfreq/)
- [Portfolio Optimization](../portfolio/)

---

**Status**: Production Ready  
**Last Updated**: January 2025  
**Strategy Version**: BtcDom2 v1.0