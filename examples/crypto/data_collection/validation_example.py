#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Example script demonstrating cryptocurrency data validation.

This script shows how to use the CryptoDataValidator to validate
cryptocurrency market data with different configurations.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_validator import CryptoDataValidator
from config.validation_config import ValidationConfig


def create_sample_data(rows: int = 100, add_issues: bool = False) -> pd.DataFrame:
    """
    Create sample cryptocurrency data for testing.
    
    Parameters
    ----------
    rows : int, default 100
        Number of rows to generate
    add_issues : bool, default False
        Whether to add data quality issues for testing
    
    Returns
    -------
    pd.DataFrame
        Sample cryptocurrency data
    """
    # Generate timestamps
    start_time = datetime.now() - timedelta(hours=rows)
    timestamps = [start_time + timedelta(hours=i) for i in range(rows)]
    
    # Generate base price data
    np.random.seed(42)  # For reproducible results
    base_price = 50000.0  # Starting price
    price_changes = np.random.normal(0, 0.02, rows)  # 2% volatility
    
    prices = [base_price]
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))  # Ensure positive prices
    
    # Generate OHLC data
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # Generate realistic OHLC
        volatility = abs(np.random.normal(0, 0.01))
        high = close * (1 + volatility)
        low = close * (1 - volatility)
        open_price = prices[i-1] if i > 0 else close
        
        # Generate volume
        base_volume = 1000000
        volume = base_volume * (1 + np.random.normal(0, 0.5))
        volume = max(volume, 0)
        
        row = {
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'volume_24h': volume * 24,
            'volume_usd_24h': volume * 24 * close,
            'change_24h': np.random.normal(0, 5),  # 24h change percentage
            'funding_rate': np.random.normal(0, 0.001),  # Small funding rate
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Add data quality issues if requested
    if add_issues:
        # Add some missing values
        df.loc[10:12, 'volume'] = np.nan
        df.loc[20, 'close'] = np.nan
        
        # Add OHLC inconsistency
        df.loc[30, 'high'] = df.loc[30, 'low'] - 100  # High < Low
        
        # Add negative price
        df.loc[40, 'open'] = -1000
        
        # Add extreme price change
        df.loc[50, 'close'] = df.loc[49, 'close'] * 3  # 200% increase
        
        # Add negative volume
        df.loc[60, 'volume'] = -5000
        
        # Add extreme funding rate
        df.loc[70, 'funding_rate'] = 0.1  # 10% funding rate
        
        # Add duplicate timestamp
        df.loc[80, 'timestamp'] = df.loc[79, 'timestamp']
    
    return df


def demonstrate_basic_validation():
    """Demonstrate basic data validation."""
    print("=== Basic Data Validation ===")
    
    # Create sample data with issues
    data = create_sample_data(rows=100, add_issues=True)
    print(f"Created sample data with {len(data)} rows")
    
    # Initialize validator with default configuration
    validator = CryptoDataValidator()
    
    # Validate the data
    report = validator.validate(data, symbol="BTC/USDT", timeframe="1h")
    
    # Print results
    print(f"\nValidation Results:")
    print(f"Overall Status: {report.overall_status}")
    print(f"Total Errors: {report.total_errors}")
    print(f"Total Warnings: {report.total_warnings}")
    print(f"Validators Run: {len(report.results)}")
    
    # Show issues by validator
    for result in report.results:
        if result.issues:
            print(f"\n{result.validator_name}:")
            for issue in result.issues[:3]:  # Show first 3 issues
                print(f"  - {issue.severity.value.upper()}: {issue.message}")
            if len(result.issues) > 3:
                print(f"  ... and {len(result.issues) - 3} more issues")


def demonstrate_configuration_options():
    """Demonstrate different validation configurations."""
    print("\n=== Configuration Options ===")
    
    # Create clean data
    clean_data = create_sample_data(rows=50, add_issues=False)
    
    # Test different configurations
    configs = {
        "Default": ValidationConfig(),
        "Strict": ValidationConfig.create_strict_config(),
        "Lenient": ValidationConfig.create_lenient_config(),
        "Crypto-Specific": ValidationConfig.create_crypto_specific_config(),
    }
    
    for config_name, config in configs.items():
        validator = CryptoDataValidator(config)
        report = validator.validate(clean_data, symbol="ETH/USDT", timeframe="1h")
        
        print(f"\n{config_name} Configuration:")
        print(f"  Status: {report.overall_status}")
        print(f"  Errors: {report.total_errors}")
        print(f"  Warnings: {report.total_warnings}")


def demonstrate_batch_validation():
    """Demonstrate batch validation of multiple symbols."""
    print("\n=== Batch Validation ===")
    
    # Create data for multiple symbols
    symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
    data_batch = {}
    
    for i, symbol in enumerate(symbols):
        # Add different types of issues to different symbols
        add_issues = i == 1  # Only add issues to ETH/USDT
        data_batch[symbol] = create_sample_data(rows=50, add_issues=add_issues)
    
    # Validate batch
    validator = CryptoDataValidator()
    reports = validator.validate_batch(data_batch, timeframe="1h")
    
    # Create summary
    summary = validator.create_summary_report(reports)
    
    print(f"Batch Validation Summary:")
    print(f"Total Symbols: {summary['total_symbols']}")
    print(f"Total Data Rows: {summary['total_data_rows']}")
    print(f"Overall Status Distribution: {summary['overall_status_counts']}")
    print(f"Total Execution Time: {summary['execution_time_ms']:.2f}ms")
    
    # Show per-symbol results
    for symbol, report in reports.items():
        print(f"\n{symbol}: {report.overall_status} "
              f"(Errors: {report.total_errors}, Warnings: {report.total_warnings})")


def demonstrate_custom_validation():
    """Demonstrate custom validation scenarios."""
    print("\n=== Custom Validation ===")
    
    # Create data with specific issues
    data = create_sample_data(rows=30, add_issues=False)
    
    # Run only specific validators
    validator = CryptoDataValidator()
    
    # Test individual validators
    validators_to_test = ["PriceValidator", "VolumeValidator", "CompletenessValidator"]
    
    for validator_name in validators_to_test:
        report = validator.validate(data, symbol="BTC/USDT", timeframe="1h", 
                                  validators=[validator_name])
        
        result = report.results[0] if report.results else None
        if result:
            print(f"\n{validator_name}:")
            print(f"  Valid: {result.is_valid}")
            print(f"  Issues: {len(result.issues)}")
            print(f"  Execution Time: {result.execution_time_ms:.2f}ms")
            
            # Show some statistics
            if result.statistics:
                stats_to_show = list(result.statistics.keys())[:3]
                for stat in stats_to_show:
                    print(f"  {stat}: {result.statistics[stat]}")


def main():
    """Main function to run all demonstrations."""
    print("Cryptocurrency Data Validation Examples")
    print("=" * 50)
    
    try:
        demonstrate_basic_validation()
        demonstrate_configuration_options()
        demonstrate_batch_validation()
        demonstrate_custom_validation()
        
        print("\n" + "=" * 50)
        print("All validation examples completed successfully!")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
