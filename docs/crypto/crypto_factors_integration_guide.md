# Cryptocurrency Factor Library Integration Guide

## Overview

The unified cryptocurrency factor library (`crypto_factors.py`) provides a standardized interface for computing and managing cryptocurrency-specific factors in qlib. This integration consolidates all factor categories into a single, easy-to-use system with automatic data preprocessing and normalization.

## Quick Start

### Basic Usage

```python
from qlib.contrib.data.crypto_factors import CryptoFactorLibrary

# Create factor library with default settings
factor_lib = CryptoFactorLibrary()

# Get all factor expressions
expressions, names = factor_lib.get_factor_expressions()
print(f"Available factors: {len(names)}")
```

### Custom Configuration

```python
from qlib.contrib.data.crypto_factors import (
    CryptoFactorLibrary, FactorConfig, FactorCategory, NormalizationMethod
)

# Create custom configuration
config = FactorConfig(
    categories=[FactorCategory.MOMENTUM, FactorCategory.VOLUME],
    normalization=NormalizationMethod.RANK,
    handle_missing="interpolate",
    outlier_treatment="winsorize"
)

# Create library with custom config
factor_lib = CryptoFactorLibrary(config)
```

## Factor Categories

| Category | Count | Description |
|----------|--------|-------------|
| **BASIC** | 24 | Basic price and volume factors including K-bar patterns |
| **DECLINE** | 24 | Multi-timeframe decline and drawdown factors |
| **VOLUME** | 30 | Volume anomaly detection and volume-price divergence |
| **MOMENTUM** | 51 | Advanced momentum with downward trend and rebound analysis |
| **FUNDING** | 42 | Funding rate factors for perpetual futures markets |

## Data Processing Features

### Normalization Methods
- **Z-Score**: `(x - mean) / std`
- **Min-Max**: `(x - min) / (max - min)`
- **Rank**: Percentile ranking
- **Quantile**: Quantile normalization

### Missing Value Handling
- **Forward Fill**: Use last valid value
- **Backward Fill**: Use next valid value
- **Interpolate**: Linear interpolation
- **Zero**: Replace with zero
- **Drop**: Remove missing observations

### Outlier Treatment
- **Winsorize**: Cap extreme values at percentiles
- **Clip**: Hard clipping at percentiles
- **Remove**: Mark outliers as missing
- **None**: No outlier treatment

## Integration with Qlib

### DataLoader Integration

```python
from qlib.contrib.data.crypto_factors import CryptoFactorDataLoader, FactorConfig

# Create enhanced DataLoader
config = FactorConfig(categories=[FactorCategory.BASIC, FactorCategory.MOMENTUM])
dataloader = CryptoFactorDataLoader(factor_config=config)

# Get factor metadata
metadata = dataloader.get_factor_metadata()
```

### Using with Existing Workflows

```python
# Replace crypto_loader usage
# OLD:
# from qlib.contrib.data.crypto_loader import CryptoAlphaDL
# expressions, names = CryptoAlphaDL.get_feature_config()

# NEW:
from qlib.contrib.data.crypto_factors import get_crypto_factor_expressions
expressions, names = get_crypto_factor_expressions()
```

## Advanced Features

### Factor Computation with Data Processing

```python
import pandas as pd
from qlib.contrib.data.crypto_factors import CryptoFactorLibrary

# Load your crypto price data
crypto_data = pd.read_csv('your_crypto_data.csv')  # Must have OHLCV columns

# Create factor library
factor_lib = CryptoFactorLibrary()

# Validate data quality
validation = factor_lib.validate_data(crypto_data)
if validation['valid']:
    # Compute factors with automatic preprocessing
    factors_df = factor_lib.compute_factors(
        crypto_data,
        categories=[FactorCategory.MOMENTUM, FactorCategory.VOLUME],
        normalize=True
    )
```

### Configuration Management

```python
# Save configuration
config = FactorConfig(normalization=NormalizationMethod.RANK)
config_dict = config.to_dict()

# Restore configuration
restored_config = FactorConfig.from_dict(config_dict)

# Quick configuration creation
from qlib.contrib.data.crypto_factors import create_crypto_factor_config
quick_config = create_crypto_factor_config(
    normalization="zscore",
    categories=['momentum', 'volume']
)
```

## Migration from crypto_loader

### Compatibility
- ✅ **75.4% compatibility** with existing crypto_loader factors
- ✅ **All factor categories** available
- ✅ **Same factor expressions** for basic, decline, volume, momentum factors
- ✅ **Funding factors** now included by default

### Migration Steps

1. **Replace imports**:
   ```python
   # OLD
   from qlib.contrib.data.crypto_loader import CryptoAlphaDL
   
   # NEW
   from qlib.contrib.data.crypto_factors import CryptoFactorLibrary
   ```

2. **Update factor generation**:
   ```python
   # OLD
   expressions, names = CryptoAlphaDL.get_feature_config()
   
   # NEW
   factor_lib = CryptoFactorLibrary()
   expressions, names = factor_lib.get_factor_expressions()
   ```

3. **Add data preprocessing** (optional):
   ```python
   # NEW: Automatic data preprocessing
   factors_df = factor_lib.compute_factors(data, normalize=True)
   ```

## Performance Optimization

### Caching
```python
config = FactorConfig(cache_factors=True)
factor_lib = CryptoFactorLibrary(config)

# First call computes and caches
expressions1, names1 = factor_lib.get_factor_expressions()

# Second call uses cache
expressions2, names2 = factor_lib.get_factor_expressions()
```

### Parallel Computation
```python
config = FactorConfig(parallel_computation=True)
factor_lib = CryptoFactorLibrary(config)
```

## Best Practices

1. **Data Validation**: Always validate input data before factor computation
2. **Configuration Management**: Use consistent configurations across experiments
3. **Missing Value Handling**: Choose appropriate method based on your data characteristics
4. **Normalization**: Use rank normalization for robust cross-sectional analysis
5. **Outlier Treatment**: Winsorize for crypto data due to high volatility
6. **Category Selection**: Start with basic + momentum factors for initial testing

## Example Workflow

```python
from qlib.contrib.data.crypto_factors import (
    CryptoFactorLibrary, FactorConfig, FactorCategory, NormalizationMethod
)

# 1. Create configuration
config = FactorConfig(
    categories=[FactorCategory.BASIC, FactorCategory.MOMENTUM, FactorCategory.VOLUME],
    normalization=NormalizationMethod.RANK,
    handle_missing="forward_fill",
    outlier_treatment="winsorize",
    min_data_points=500
)

# 2. Initialize library
factor_lib = CryptoFactorLibrary(config)

# 3. Validate data
validation = factor_lib.validate_data(your_crypto_data)
print(f"Data validation: {validation}")

# 4. Compute factors
if validation['valid']:
    factors_df = factor_lib.compute_factors(your_crypto_data)
    print(f"Computed {factors_df.shape[1]} factors for {factors_df.shape[0]} observations")

# 5. Use in qlib workflow
expressions, names = factor_lib.get_factor_expressions()
# ... continue with qlib model training
```

## Support and Development

- **Location**: `qlib/contrib/data/crypto_factors.py`
- **Examples**: `scripts/data_collector/crypto/examples/crypto_factors_integration_example.py`
- **Tests**: Integrated with existing crypto factor test suite
- **Documentation**: This guide and inline docstrings

For additional support or feature requests, refer to the qlib cryptocurrency module documentation.