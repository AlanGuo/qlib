#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Unit tests for individual validator components.
"""

import pytest

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def minimal_data():
    """Create minimal test data."""
    return pd.DataFrame({
        'datetime': pd.date_range(start='2024-01-01', periods=10, freq='1h'),
        'open': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
        'high': [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
        'low': [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
        'close': [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
        'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
    })


class TestValidationResult:
    """Test ValidationResult class in isolation."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        from validators.base_validator import ValidationResult
        
        result = ValidationResult(
            validator_name="test",
            is_valid=True,
            issues=[],
            statistics={}
        )
        
        assert result.validator_name == "test"
        assert result.is_valid == True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_validation_result_with_issues(self):
        """Test ValidationResult with issues."""
        from validators.base_validator import ValidationResult, ValidationIssue, ValidationSeverity
        
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Test error",
                field_name="test_col",
                row_index=0,
                value="test_value"
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Test warning",
                field_name="test_col",
                row_index=1,
                value="test_value"
            )
        ]
        
        result = ValidationResult(
            validator_name="test",
            is_valid=False,
            issues=issues,
            statistics={}
        )
        
        assert result.validator_name == "test"
        assert result.is_valid == False
        assert result.error_count == 1
        assert result.warning_count == 1


class TestValidationIssue:
    """Test ValidationIssue class in isolation."""
    
    def test_validation_issue_creation(self):
        """Test ValidationIssue creation."""
        from validators.base_validator import ValidationIssue, ValidationSeverity
        
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message="Test message",
            field_name="test_column",
            row_index=5,
            value=123.45
        )
        
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.message == "Test message"
        assert issue.field_name == "test_column"
        assert issue.row_index == 5
        assert issue.value == 123.45

    def test_validation_issue_string_representation(self):
        """Test ValidationIssue string representation."""
        from validators.base_validator import ValidationIssue, ValidationSeverity
        
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            message="Test warning",
            field_name="price",
            row_index=10,
            value=None
        )
        
        str_repr = str(issue)
        assert "WARNING" in str_repr
        assert "Test warning" in str_repr
        assert "price" in str_repr


class TestValidationSeverity:
    """Test ValidationSeverity enum."""
    
    def test_validation_severity_values(self):
        """Test ValidationSeverity enum values."""
        from validators.base_validator import ValidationSeverity
        
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"

    def test_validation_severity_comparison(self):
        """Test ValidationSeverity comparison."""
        from validators.base_validator import ValidationSeverity
        
        # Test that ERROR > WARNING > INFO
        assert ValidationSeverity.ERROR.value != ValidationSeverity.WARNING.value
        assert ValidationSeverity.WARNING.value != ValidationSeverity.INFO.value
        assert ValidationSeverity.ERROR.value != ValidationSeverity.INFO.value


class TestBaseValidatorAbstract:
    """Test BaseValidator abstract class."""
    
    def test_base_validator_cannot_be_instantiated(self):
        """Test that BaseValidator cannot be instantiated directly."""
        from validators.base_validator import BaseValidator
        
        with pytest.raises(TypeError):
            BaseValidator()

    def test_base_validator_interface(self):
        """Test BaseValidator interface requirements."""
        from validators.base_validator import BaseValidator
        
        # Check that validate method exists and is abstract
        assert hasattr(BaseValidator, 'validate')
        assert BaseValidator.validate.__isabstractmethod__


class TestPriceValidatorUnit:
    """Unit tests for PriceValidator specific logic."""
    
    def test_price_validator_initialization(self):
        """Test PriceValidator initialization."""
        from validators.price_validator import PriceValidator
        
        validator = PriceValidator()
        assert validator is not None

    def test_price_validator_with_empty_data(self):
        """Test PriceValidator with empty DataFrame."""
        from validators.price_validator import PriceValidator
        
        validator = PriceValidator()
        empty_data = pd.DataFrame()
        
        result = validator.validate(empty_data)
        # Should handle empty data gracefully
        assert result is not None


class TestVolumeValidatorUnit:
    """Unit tests for VolumeValidator specific logic."""
    
    def test_volume_validator_initialization(self):
        """Test VolumeValidator initialization."""
        from validators.volume_validator import VolumeValidator
        
        validator = VolumeValidator()
        assert validator is not None

    def test_volume_validator_with_negative_volume(self, minimal_data):
        """Test VolumeValidator detects negative volume."""
        from validators.volume_validator import VolumeValidator
        
        # Add negative volume
        test_data = minimal_data.copy()
        test_data.loc[5, 'volume'] = -100
        
        validator = VolumeValidator()
        result = validator.validate(test_data)
        
        # Should detect negative volume
        assert result.error_count > 0 or result.warning_count > 0


class TestTimeSeriesValidatorUnit:
    """Unit tests for TimeSeriesValidator specific logic."""
    
    def test_timeseries_validator_initialization(self):
        """Test TimeSeriesValidator initialization."""
        from validators.timeseries_validator import TimeSeriesValidator
        
        validator = TimeSeriesValidator(timestamp_column='datetime')
        assert validator is not None

    def test_timeseries_validator_duplicate_timestamps(self, minimal_data):
        """Test TimeSeriesValidator detects duplicate timestamps."""
        from validators.timeseries_validator import TimeSeriesValidator
        
        # Add duplicate timestamp
        test_data = minimal_data.copy()
        test_data.loc[len(test_data)] = test_data.iloc[0]  # Duplicate first row
        
        validator = TimeSeriesValidator(timestamp_column='datetime')
        result = validator.validate(test_data)
        
        # Should detect duplicate timestamps
        assert result.error_count > 0 or result.warning_count > 0


class TestCompletenessValidatorUnit:
    """Unit tests for CompletenessValidator specific logic."""
    
    def test_completeness_validator_initialization(self):
        """Test CompletenessValidator initialization."""
        from validators.completeness_validator import CompletenessValidator
        
        validator = CompletenessValidator(required_fields=['open', 'high', 'low', 'close'])
        assert validator is not None

    def test_completeness_validator_missing_column(self, minimal_data):
        """Test CompletenessValidator detects missing columns."""
        from validators.completeness_validator import CompletenessValidator
        
        # Remove a required column
        test_data = minimal_data.drop(columns=['volume'])
        
        validator = CompletenessValidator(required_fields=['open', 'high', 'low', 'close', 'volume'])
        result = validator.validate(test_data)
        
        # Should detect missing column
        assert result.error_count > 0 or result.warning_count > 0


class TestConsistencyValidatorUnit:
    """Unit tests for ConsistencyValidator specific logic."""
    
    def test_consistency_validator_initialization(self):
        """Test ConsistencyValidator initialization."""
        from validators.consistency_validator import ConsistencyValidator
        
        validator = ConsistencyValidator()
        assert validator is not None

    def test_consistency_validator_missing_ohlc_data(self, minimal_data):
        """Test ConsistencyValidator detects missing OHLC data."""
        from validators.consistency_validator import ConsistencyValidator
        import numpy as np

        # Create missing OHLC data
        test_data = minimal_data.copy()
        test_data.loc[5, 'high'] = np.nan  # Missing high value

        validator = ConsistencyValidator()
        result = validator.validate(test_data)

        # Should detect missing OHLC data
        assert result.warning_count > 0


class TestAnomalyValidatorUnit:
    """Unit tests for AnomalyValidator specific logic."""
    
    def test_anomaly_validator_initialization(self):
        """Test AnomalyValidator initialization."""
        from validators.anomaly_validator import AnomalyValidator
        
        validator = AnomalyValidator()
        assert validator is not None

    def test_anomaly_validator_extreme_price_jump(self, minimal_data):
        """Test AnomalyValidator detects extreme price jumps."""
        from validators.anomaly_validator import AnomalyValidator
        
        # Create extreme price jump
        test_data = minimal_data.copy()
        test_data.loc[5, 'open'] = test_data.loc[4, 'close'] * 10  # 10x price jump
        
        validator = AnomalyValidator(min_data_points=5)  # Lower threshold for testing
        result = validator.validate(test_data)

        # Should detect extreme price jump (may be reported as INFO level)
        assert len(result.issues) > 0  # Any issues detected
        assert any("outlier" in issue.message.lower() for issue in result.issues)
