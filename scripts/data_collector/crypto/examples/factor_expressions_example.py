#!/usr/bin/env python3
"""
Demo script for CryptoAlpha factors expressions and configurations.
Run from project root: python scripts/data_collector/crypto/tests/run_factor_expressions_demo.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from qlib.contrib.data.crypto_loader import CryptoAlphaDL, CryptoAlpha158DL


def demo_crypto_alpha_expressions():
    """Demo CryptoAlpha expressions generation."""
    print("=" * 60)
    print("CryptoAlpha Factor Expressions Demo")
    print("=" * 60)
    
    # Test default configuration
    loader = CryptoAlphaDL()
    expressions, names = loader.get_feature_config()
    
    print(f"Generated {len(expressions)} expressions and {len(names)} names")
    print(f"Expressions and names match: {len(expressions) == len(names)}")
    
    # Print sample expressions
    print("\nSample expressions:")
    for i in range(min(10, len(expressions))):
        print(f"  {names[i]}: {expressions[i]}")
    
    return True


def demo_factor_group_configurations():
    """Demo different factor group configurations."""
    print("\n" + "=" * 60)
    print("Factor Group Configurations Demo")
    print("=" * 60)
    
    configs = [
        {"basic": {}},
        {"decline": {}},
        {"volume": {}},
        {"momentum": {}},
        {"basic": {}, "decline": {}},
        {"basic": {}, "decline": {}, "volume": {}, "momentum": {}},
    ]
    
    for i, config in enumerate(configs):
        expressions, names = CryptoAlphaDL.get_feature_config(config)
        print(f"Config {i+1} {list(config.keys())}: {len(expressions)} factors")
    
    return True


def demo_individual_factor_groups():
    """Demo individual factor groups."""
    print("\n" + "=" * 60)
    print("Individual Factor Groups Demo")
    print("=" * 60)
    
    # Import factor group functions
    from qlib.contrib.data.crypto_loader import (
        _get_basic_factors,
        _get_decline_factors, 
        _get_volume_factors,
        _get_momentum_factors
    )
    
    groups = [
        ("Basic", _get_basic_factors),
        ("Decline", _get_decline_factors),
        ("Volume", _get_volume_factors),
        ("Momentum", _get_momentum_factors),
    ]
    
    for group_name, func in groups:
        expressions, names = func()
        print(f"\n{group_name} factors: {len(expressions)} expressions")
        
        # Show sample factors
        print(f"Sample {group_name} factors:")
        for i in range(min(5, len(expressions))):
            print(f"  {names[i]}: {expressions[i]}")
    
    return True


def demo_expression_validity():
    """Demo expression validity checking."""
    print("\n" + "=" * 60)
    print("Expression Validity Demo")
    print("=" * 60)
    
    loader = CryptoAlphaDL()
    expressions, names = loader.get_feature_config()
    
    # Check for common qlib operators
    qlib_operators = ['$close', '$open', '$high', '$low', '$volume', 'Ref', 'Mean', 'Std', 'Max', 'Min']
    
    valid_count = 0
    invalid_expressions = []
    
    for i, expr in enumerate(expressions):
        has_qlib_op = any(op in expr for op in qlib_operators)
        if has_qlib_op:
            valid_count += 1
        else:
            invalid_expressions.append(f"{names[i]}: {expr}")
    
    print(f"Valid expressions: {valid_count}/{len(expressions)}")
    print(f"Validity rate: {100*valid_count/len(expressions):.1f}%")
    
    if invalid_expressions:
        print("Invalid expressions found:")
        for expr in invalid_expressions:
            print(f"  {expr}")
    
    return len(invalid_expressions) == 0


def demo_factor_naming_analysis():
    """Demo factor naming pattern analysis."""
    print("\n" + "=" * 60)
    print("Factor Naming Analysis Demo")
    print("=" * 60)
    
    loader = CryptoAlphaDL()
    expressions, names = loader.get_feature_config()
    
    # Check naming patterns
    naming_rules = [
        ("Basic factors", lambda name: any(prefix in name for prefix in ["KMID", "KLEN", "CLOSE", "VOLUME"])),
        ("Decline factors", lambda name: any(prefix in name for prefix in ["DECLINE_", "MAXDD_"])),
        ("Volume factors", lambda name: any(prefix in name for prefix in ["VOL_ZSCORE", "VOL_RATIO", "PRICE_VOL_CORR", "OBV_TREND"])),
        ("Momentum factors", lambda name: any(prefix in name for prefix in ["RSI_", "MACD_", "BB_POS_", "ROC_"])),
    ]
    
    total_categorized = 0
    for rule_name, rule_func in naming_rules:
        matching_names = [name for name in names if rule_func(name)]
        total_categorized += len(matching_names)
        print(f"{rule_name}: {len(matching_names)} factors")
        if matching_names:
            print(f"  Examples: {matching_names[:3]}")
    
    uncategorized = len(names) - total_categorized
    if uncategorized > 0:
        uncategorized_names = []
        for name in names:
            categorized = False
            for rule_name, rule_func in naming_rules:
                if rule_func(name):
                    categorized = True
                    break
            if not categorized:
                uncategorized_names.append(name)
        
        print(f"\nUncategorized factors: {uncategorized}")
        print(f"  Examples: {uncategorized_names[:5]}")
    
    # Check for duplicates
    duplicates = set([name for name in names if names.count(name) > 1])
    if duplicates:
        print(f"\nWARNING: Duplicate factor names found: {duplicates}")
        return False
    else:
        print(f"\nNo duplicate factor names found ✓")
    
    return True


def main():
    """Run all demos."""
    print("CryptoAlpha Factor System Demo")
    print("Run from project root with:")
    print("python scripts/data_collector/crypto/tests/run_factor_expressions_demo.py\n")
    
    try:
        demo1 = demo_crypto_alpha_expressions()
        demo2 = demo_factor_group_configurations()
        demo3 = demo_individual_factor_groups()
        demo4 = demo_expression_validity()
        demo5 = demo_factor_naming_analysis()
        
        print("\n" + "=" * 60)
        print("DEMO RESULTS:")
        print(f"Expression generation: {'✓' if demo1 else '✗'}")
        print(f"Factor group configs: {'✓' if demo2 else '✗'}")
        print(f"Individual groups: {'✓' if demo3 else '✗'}")
        print(f"Expression validity: {'✓' if demo4 else '✗'}")
        print(f"Factor naming: {'✓' if demo5 else '✗'}")
        
        all_pass = demo1 and demo2 and demo3 and demo4 and demo5
        print(f"\nOverall: {'ALL DEMOS SUCCESSFUL' if all_pass else 'SOME DEMOS FAILED'}")
        
        if all_pass:
            print("\n✅ CryptoAlpha factor system is working correctly!")
            print("\nNext steps:")
            print("1. Run integration tests: python scripts/data_collector/crypto/tests/run_factor_integration_test.py")
            print("2. Run pytest unit tests: pytest scripts/data_collector/crypto/tests/test_crypto_alpha_factors.py")
            print("3. Test with real data using factor validation scripts")
        
        return 0 if all_pass else 1
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())