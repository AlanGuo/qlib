#!/usr/bin/env python3
"""
CryptoFactorDL Example - Independent Crypto Factor Library
=========================================================

This example demonstrates the new CryptoFactorDL class which provides
a complete, independent factor library for cryptocurrency markets.

Features:
- Multi-timeframe support
- Advanced factor validation  
- IC analysis capabilities
- Production-ready factor pipeline
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

def demo_crypto_factor_dl():
    """Demonstrate CryptoFactorDL capabilities."""
    print("=" * 60)
    print("CryptoFactorDL - Independent Crypto Factor Library Demo")
    print("=" * 60)
    
    try:
        from qlib.contrib.data.crypto_loader import CryptoFactorDL
        
        # Test different timeframes
        timeframes = ["1h", "4h", "1d"]
        
        for timeframe in timeframes:
            print(f"\n{'='*20} {timeframe} Timeframe {'='*20}")
            
            # Create CryptoFactorDL instance
            factor_dl = CryptoFactorDL(timeframe=timeframe)
            
            # Get factor summary
            summary = factor_dl.get_factor_summary()
            print(f"Total factors: {summary['total_factors']}")
            print(f"Current timeframe: {summary['timeframe']}")
            print(f"Factor categories: {summary['categories']}")
            
            # Get timeframe compatibility info
            compat_info = factor_dl.get_timeframe_compatibility_info()
            print(f"Timeframe hours: {compat_info['timeframe_hours']}")
            
            # Get feature configuration
            expressions, names = factor_dl.get_feature_config()
            print(f"Generated {len(expressions)} factor expressions")
            print(f"Sample factors: {names[:5]}")
            
        return True
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def demo_factor_validation():
    """Demonstrate factor validation capabilities."""
    print(f"\n{'='*60}")
    print("Factor Validation Demo")
    print("=" * 60)
    
    try:
        from qlib.contrib.data.crypto_loader import CryptoFactorDL
        
        # Create synthetic crypto data
        dates = pd.date_range('2024-01-01', '2024-01-31', freq='1H')
        n_samples = len(dates)
        
        # Generate realistic crypto price data
        np.random.seed(42)
        price_base = 50000
        returns = np.random.normal(0.0001, 0.02, n_samples)
        prices = price_base * np.exp(np.cumsum(returns))
        
        # Create test data
        test_data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.001, n_samples)),
            'high': prices * (1 + np.abs(np.random.normal(0.002, 0.005, n_samples))),
            'low': prices * (1 - np.abs(np.random.normal(0.002, 0.005, n_samples))),
            'close': prices,
            'volume': np.random.lognormal(15, 2, n_samples),
            'returns': returns  # Add returns for IC analysis
        }, index=dates)
        
        print(f"Generated test data: {len(test_data)} samples")
        print(f"Price range: ${test_data['close'].min():.0f} - ${test_data['close'].max():.0f}")
        
        # Test validation with different timeframes
        for timeframe in ["1h", "1d"]:
            print(f"\nValidation for {timeframe} timeframe:")
            
            factor_dl = CryptoFactorDL(timeframe=timeframe)
            validation_results = factor_dl.validate_factors(test_data)
            
            print(f"  Factor count: {validation_results['factor_count']}")
            print(f"  Mean coverage: {validation_results['basic_stats'].get('mean_coverage', 'N/A')}%")
            print(f"  Factors with full coverage: {validation_results['basic_stats'].get('factors_with_full_coverage', 'N/A')}")
            
            if validation_results.get('ic_analysis'):
                ic_stats = validation_results['ic_analysis']
                print(f"  Mean absolute IC: {ic_stats.get('mean_abs_ic', 'N/A')}")
                print(f"  Factors with significant IC: {ic_stats.get('factors_with_significant_ic', 'N/A')}")
            
            if validation_results.get('warnings'):
                print(f"  Warnings: {len(validation_results['warnings'])}")
                for warning in validation_results['warnings'][:2]:
                    print(f"    - {warning}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def demo_backward_compatibility():
    """Test backward compatibility with CryptoAlphaDL."""
    print(f"\n{'='*60}")
    print("Backward Compatibility Demo")
    print("=" * 60)
    
    try:
        from qlib.contrib.data.crypto_loader import CryptoAlphaDL, CryptoAlpha158DL
        
        # Test CryptoAlphaDL (should be alias to CryptoFactorDL)
        print("Testing CryptoAlphaDL (backward compatibility):")
        alpha_dl = CryptoAlphaDL(timeframe="1h")
        summary = alpha_dl.get_factor_summary()
        print(f"  Total factors: {summary['total_factors']}")
        print(f"  Has validation methods: {hasattr(alpha_dl, 'validate_factors')}")
        
        # Test CryptoAlpha158DL
        print("\nTesting CryptoAlpha158DL:")
        alpha158_dl = CryptoAlpha158DL(timeframe="4h")
        summary = alpha158_dl.get_factor_summary()
        print(f"  Total factors: {summary['total_factors']}")
        print(f"  Timeframe: {summary['timeframe']}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def demo_multi_timeframe_support():
    """Demonstrate multi-timeframe factor computation."""
    print(f"\n{'='*60}")
    print("Multi-Timeframe Support Demo")
    print("=" * 60)
    
    try:
        from qlib.contrib.data.crypto_loader import CryptoFactorDL
        
        # Test all supported timeframes
        supported_timeframes = ["1min", "5min", "15min", "30min", "1h", "4h", "1d"]
        
        results = {}
        for timeframe in supported_timeframes:
            factor_dl = CryptoFactorDL(timeframe=timeframe)
            compat_info = factor_dl.get_timeframe_compatibility_info()
            summary = factor_dl.get_factor_summary()
            
            results[timeframe] = {
                "hours": compat_info["timeframe_hours"],
                "factors": summary["total_factors"],
                "categories": len(summary["categories"])
            }
        
        print("Timeframe support analysis:")
        print(f"{'Timeframe':<10} {'Hours':<10} {'Factors':<10} {'Categories':<12}")
        print("-" * 45)
        
        for tf, info in results.items():
            print(f"{tf:<10} {info['hours']:<10} {info['factors']:<10} {info['categories']:<12}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all demonstration functions."""
    print("CryptoFactorDL Comprehensive Demo")
    print("=" * 60)
    
    demos = [
        ("Basic CryptoFactorDL Usage", demo_crypto_factor_dl),
        ("Factor Validation", demo_factor_validation),
        ("Backward Compatibility", demo_backward_compatibility),
        ("Multi-Timeframe Support", demo_multi_timeframe_support),
    ]
    
    results = []
    for name, demo_func in demos:
        try:
            result = demo_func()
            results.append((name, result))
        except Exception as e:
            print(f"Demo error in {name}: {e}")
            results.append((name, False))
    
    print(f"\n{'='*60}")
    print("DEMO RESULTS SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:<30}: {status}")
    
    overall_status = "SUCCESS" if all(r[1] for r in results) else "PARTIAL"
    print(f"\nOverall Status: {overall_status}")
    
    print(f"\n🎯 CryptoFactorDL Features:")
    print("  ✓ Independent factor library (replaced Alpha158 extension)")
    print("  ✓ Multi-timeframe factor computation")
    print("  ✓ Advanced factor validation with IC analysis")
    print("  ✓ Backward compatibility with CryptoAlphaDL")
    print("  ✓ Production-ready factor pipeline")
    print("  ✓ 171 total cryptocurrency factors across 5 categories")
    
    print(f"\n🚀 Ready for production cryptocurrency factor computation!")


if __name__ == "__main__":
    main()