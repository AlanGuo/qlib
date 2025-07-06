# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Example usage of cryptocurrency risk metrics calculation.

This example demonstrates how to use the risk metrics module to calculate
comprehensive risk indicators for cryptocurrency data.
"""

import pandas as pd
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
import numpy as np
from datetime import datetime, timedelta
import logging

# Import risk metrics components
from risk_metrics import (
    RiskMetricsManager,
    VolatilityCalculator,
    DrawdownCalculator,
    SharpeRatioCalculator,
    VaRCalculator,
    BetaCalculator
)
from config.risk_config import RiskConfig


def generate_sample_data(
    symbol: str = "BTC/USDT",
    days: int = 365,
    initial_price: float = 50000.0,
    volatility: float = 0.03
) -> pd.DataFrame:
    """
    Generate sample cryptocurrency price data for testing.
    
    Parameters
    ----------
    symbol : str
        Symbol name
    days : int
        Number of days of data
    initial_price : float
        Starting price
    volatility : float
        Daily volatility
    
    Returns
    -------
    pd.DataFrame
        Sample OHLC data
    """
    # Generate dates
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        end=datetime.now(),
        freq='D'
    )
    
    # Generate random returns
    np.random.seed(42)  # For reproducibility
    returns = np.random.normal(0.0005, volatility, len(dates))  # Slight positive drift
    
    # Calculate prices
    prices = [initial_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Generate OHLC data
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        # Add some intraday volatility
        daily_vol = volatility * 0.5
        high = price * (1 + np.random.uniform(0, daily_vol))
        low = price * (1 - np.random.uniform(0, daily_vol))
        open_price = prices[i-1] if i > 0 else price
        close = price
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': max(open_price, high, close),
            'low': min(open_price, low, close),
            'close': close,
            'volume': np.random.uniform(1000, 10000)
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


def example_basic_risk_calculation():
    """Example of basic risk metrics calculation."""
    print("=== Basic Risk Metrics Calculation ===")
    
    # Generate sample data
    btc_data = generate_sample_data("BTC/USDT", days=365, volatility=0.04)
    eth_data = generate_sample_data("ETH/USDT", days=365, initial_price=3000, volatility=0.05)
    
    # Create risk metrics manager with crypto-optimized config
    config = RiskConfig.create_crypto_optimized_config()
    risk_manager = RiskMetricsManager(config)
    
    # Calculate all risk metrics for BTC
    btc_metrics = risk_manager.calculate_all_metrics(
        data=btc_data,
        symbol="BTC/USDT",
        timeframe="1d",
        benchmark_data=None  # No benchmark for this example
    )
    
    print(f"Calculated {len(btc_metrics)} metric categories for BTC/USDT:")
    for category, results in btc_metrics.items():
        print(f"  {category}: {len(results)} metrics")
        
        # Show sample results
        for result in results[:2]:  # Show first 2 results
            if isinstance(result.value, pd.Series):
                latest_value = result.value.iloc[-1] if not result.value.empty else None
                print(f"    {result.metric_name}: {latest_value:.6f}")
            else:
                print(f"    {result.metric_name}: {result.value}")
    
    # Calculate risk summary
    risk_summary = risk_manager.calculate_risk_summary(
        data=btc_data,
        symbol="BTC/USDT",
        timeframe="1d"
    )
    
    print(f"\nRisk Summary for BTC/USDT:")
    summary_data = risk_summary.value
    for key, value in summary_data.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")


def example_individual_calculators():
    """Example of using individual risk calculators."""
    print("\n=== Individual Calculator Examples ===")
    
    # Generate sample data
    data = generate_sample_data("ETH/USDT", days=180, initial_price=3000)
    
    # Volatility calculation
    vol_calculator = VolatilityCalculator()
    vol_results = vol_calculator.calculate(
        data=data,
        symbol="ETH/USDT",
        timeframe="1d",
        windows=[7, 30, 90],
        method="historical"
    )
    
    print("Volatility Results:")
    for result in vol_results:
        latest_vol = result.value.iloc[-1] if isinstance(result.value, pd.Series) else result.value
        print(f"  {result.metric_name}: {latest_vol:.4f}")
    
    # Drawdown calculation
    dd_calculator = DrawdownCalculator()
    dd_results = dd_calculator.calculate(
        data=data,
        symbol="ETH/USDT",
        timeframe="1d"
    )
    
    print("\nDrawdown Results:")
    for result in dd_results:
        if result.metric_name in ['maximum_drawdown', 'current_drawdown']:
            print(f"  {result.metric_name}: {result.value:.4f}")
    
    # VaR calculation
    var_calculator = VaRCalculator()
    var_results = var_calculator.calculate(
        data=data,
        symbol="ETH/USDT",
        timeframe="1d",
        windows=[30],
        confidence_levels=[0.05],
        methods=["historical", "parametric"]
    )
    
    print("\nVaR Results:")
    for result in var_results:
        latest_var = result.value.iloc[-1] if isinstance(result.value, pd.Series) else result.value
        print(f"  {result.metric_name}: {latest_var:.4f}")


def example_beta_calculation():
    """Example of beta calculation with benchmark."""
    print("\n=== Beta Calculation Example ===")
    
    # Generate sample data
    btc_data = generate_sample_data("BTC/USDT", days=365, volatility=0.04)
    eth_data = generate_sample_data("ETH/USDT", days=365, initial_price=3000, volatility=0.05)
    
    # Calculate beta of ETH relative to BTC
    beta_calculator = BetaCalculator()
    beta_results = beta_calculator.calculate(
        data=eth_data,
        benchmark_data=btc_data,
        symbol="ETH/USDT",
        timeframe="1d",
        windows=[30, 90]
    )
    
    print("Beta Results (ETH vs BTC):")
    for result in beta_results:
        latest_beta = result.value.iloc[-1] if isinstance(result.value, pd.Series) else result.value
        print(f"  {result.metric_name}: {latest_beta:.4f}")
    
    # Calculate alpha
    alpha_results = beta_calculator.calculate_alpha(
        data=eth_data,
        benchmark_data=btc_data,
        symbol="ETH/USDT",
        timeframe="1d",
        windows=[30, 90]
    )
    
    print("\nAlpha Results (ETH vs BTC):")
    for result in alpha_results:
        latest_alpha = result.value.iloc[-1] if isinstance(result.value, pd.Series) else result.value
        print(f"  {result.metric_name}: {latest_alpha:.4f}")


def example_configuration_usage():
    """Example of different configuration options."""
    print("\n=== Configuration Examples ===")
    
    data = generate_sample_data("BTC/USDT", days=90)
    
    # High-frequency configuration
    hf_config = RiskConfig.create_high_frequency_config()
    hf_manager = RiskMetricsManager(hf_config)
    
    print("High-frequency config windows:")
    print(f"  Volatility: {hf_config.volatility_windows}")
    print(f"  VaR: {hf_config.var_windows}")
    
    # Conservative configuration
    conservative_config = RiskConfig.create_conservative_config()
    conservative_manager = RiskMetricsManager(conservative_config)
    
    print("\nConservative config windows:")
    print(f"  Volatility: {conservative_config.volatility_windows}")
    print(f"  VaR: {conservative_config.var_windows}")
    
    # Custom configuration
    custom_config = RiskConfig(
        volatility_windows=[5, 15, 45],
        var_confidence_levels=[0.01, 0.05, 0.10],
        risk_free_rate=0.03,
        periods_per_year=365
    )
    
    print("\nCustom config:")
    print(f"  Volatility windows: {custom_config.volatility_windows}")
    print(f"  VaR confidence levels: {custom_config.var_confidence_levels}")
    print(f"  Risk-free rate: {custom_config.risk_free_rate}")


def main():
    """Run all examples."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("Cryptocurrency Risk Metrics Examples")
    print("=" * 50)
    
    try:
        # Run examples
        example_basic_risk_calculation()
        example_individual_calculators()
        example_beta_calculation()
        example_configuration_usage()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
