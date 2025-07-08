"""
Test CryptoAlpha factors expressions and configurations.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from qlib.contrib.data.crypto_loader import CryptoAlphaDL, CryptoAlpha158DL


@pytest.mark.fast
@pytest.mark.unit
class TestCryptoAlphaFactors:
    """Test cases for CryptoAlpha factor system."""
    
    def test_crypto_alpha_expressions(self):
        """Test that CryptoAlpha expressions are generated correctly."""
        # Test default configuration
        loader = CryptoAlphaDL()
        expressions, names = loader.get_feature_config()
        
        assert len(expressions) > 0, "Should generate some expressions"
        assert len(expressions) == len(names), "Expressions and names should match"
        
        # Check that we have a reasonable number of factors
        assert len(expressions) >= 50, f"Expected at least 50 factors, got {len(expressions)}"
        
    def test_factor_group_configurations(self):
        """Test different factor group configurations."""
        configs = [
            {"basic": {}},
            {"decline": {}}, 
            {"volume": {}},
            {"momentum": {}},
            {"basic": {}, "decline": {}},
            {"basic": {}, "decline": {}, "volume": {}, "momentum": {}},
        ]
        
        for config in configs:
            expressions, names = CryptoAlphaDL.get_feature_config(config)
            assert len(expressions) > 0, f"Config {config} should generate factors"
            assert len(expressions) == len(names), f"Config {config} expressions/names mismatch"
            
    def test_individual_factor_groups(self):
        """Test individual factor groups."""
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
            assert len(expressions) > 0, f"{group_name} should generate factors"
            assert len(expressions) == len(names), f"{group_name} expressions/names mismatch"
            
    def test_expression_validity(self):
        """Test that expressions contain valid qlib syntax."""
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
        
        # All expressions should be valid
        assert valid_count == len(expressions), f"Invalid expressions found: {invalid_expressions}"
        
    def test_factor_naming_conventions(self):
        """Test that factor names follow conventions."""
        loader = CryptoAlphaDL()
        expressions, names = loader.get_feature_config()
        
        # Check naming patterns
        naming_rules = [
            ("Basic factors", lambda name: any(prefix in name for prefix in ["KMID", "KLEN", "CLOSE", "VOLUME"])),
            ("Decline factors", lambda name: any(prefix in name for prefix in ["DECLINE_", "MAXDD_"])),
            ("Volume factors", lambda name: any(prefix in name for prefix in ["VOL_ZSCORE", "VOL_RATIO", "PRICE_VOL_CORR", "OBV_TREND"])),
            ("Momentum factors", lambda name: any(prefix in name for prefix in ["RSI_", "MACD_", "BB_POS_", "ROC_"])),
        ]
        
        categorized_count = 0
        for name in names:
            for rule_name, rule_func in naming_rules:
                if rule_func(name):
                    categorized_count += 1
                    break
        
        # Most factors should follow naming conventions
        assert categorized_count >= len(names) * 0.8, f"Only {categorized_count}/{len(names)} factors follow naming conventions"
        
    def test_no_duplicate_factor_names(self):
        """Test that there are no duplicate factor names."""
        loader = CryptoAlphaDL()
        expressions, names = loader.get_feature_config()
        
        duplicates = set([name for name in names if names.count(name) > 1])
        assert len(duplicates) == 0, f"Duplicate factor names found: {duplicates}"
        
    def test_crypto_alpha158_compatibility(self):
        """Test CryptoAlpha158DL compatibility."""
        loader = CryptoAlpha158DL()
        expressions, names = loader.get_feature_config()
        
        assert len(expressions) > 0, "CryptoAlpha158DL should generate factors"
        assert len(expressions) == len(names), "CryptoAlpha158DL expressions/names should match"


@pytest.mark.fast
@pytest.mark.unit
class TestFactorGroups:
    """Test individual factor group functions."""
    
    def test_basic_factors(self):
        """Test basic factor generation."""
        from qlib.contrib.data.crypto_loader import _get_basic_factors
        
        expressions, names = _get_basic_factors()
        
        assert len(expressions) > 0, "Should generate basic factors"
        assert len(expressions) == len(names), "Basic factors expressions/names mismatch"
        
        # Should include K-bar factors
        assert any("KMID" in name for name in names), "Should include KMID factor"
        assert any("KLEN" in name for name in names), "Should include KLEN factor"
        
    def test_decline_factors(self):
        """Test decline factor generation."""
        from qlib.contrib.data.crypto_loader import _get_decline_factors
        
        expressions, names = _get_decline_factors()
        
        assert len(expressions) > 0, "Should generate decline factors"
        assert len(expressions) == len(names), "Decline factors expressions/names mismatch"
        
        # Should include different time periods
        periods = ['4H', '8H', '24H', '168H', '336H', '720H']
        for period in periods:
            assert any(period in name for name in names), f"Should include {period} factors"
            
    def test_volume_factors(self):
        """Test volume factor generation."""
        from qlib.contrib.data.crypto_loader import _get_volume_factors
        
        expressions, names = _get_volume_factors()
        
        assert len(expressions) > 0, "Should generate volume factors"
        assert len(expressions) == len(names), "Volume factors expressions/names mismatch"
        
        # Should include volume anomaly detection
        assert any("VOL_ZSCORE" in name for name in names), "Should include volume Z-score factors"
        
    def test_momentum_factors(self):
        """Test momentum factor generation."""
        from qlib.contrib.data.crypto_loader import _get_momentum_factors
        
        expressions, names = _get_momentum_factors()
        
        assert len(expressions) > 0, "Should generate momentum factors"
        assert len(expressions) == len(names), "Momentum factors expressions/names mismatch"
        
        # Should include RSI and other momentum indicators
        assert any("RSI_" in name for name in names), "Should include RSI factors"
        assert any("MACD_" in name for name in names), "Should include MACD factors"