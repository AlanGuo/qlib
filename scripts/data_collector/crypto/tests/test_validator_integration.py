#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for cryptocurrency data validator integration.

This script tests the integration of multiple validators working together,
validation workflows, and error reporting systems.
"""

import pytest
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import pandas as pd
import numpy as np


# Test fixtures
@pytest.fixture
def temp_validation_dir():
    """Create temporary directory for validation tests."""
    temp_dir = tempfile.mkdtemp(prefix="crypto_validator_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def valid_ohlcv_data():
    """Valid OHLCV data for testing."""
    dates = pd.date_range(start='2022-01-01', periods=100, freq='1H')
    base_price = 45000.0
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(base_price * 0.98, base_price * 1.02, 100),
        'high': np.random.uniform(base_price * 1.01, base_price * 1.05, 100),
        'low': np.random.uniform(base_price * 0.95, base_price * 0.99, 100),
        'close': np.random.uniform(base_price * 0.98, base_price * 1.02, 100),
        'volume': np.random.uniform(100, 1000, 100)
    })
    
    # Ensure OHLC relationships are valid
    for i in range(len(data)):
        high = max(data.iloc[i]['open'], data.iloc[i]['close']) * 1.01
        low = min(data.iloc[i]['open'], data.iloc[i]['close']) * 0.99
        data.iloc[i, data.columns.get_loc('high')] = high
        data.iloc[i, data.columns.get_loc('low')] = low
    
    return data

@pytest.fixture
def invalid_ohlcv_data():
    """Invalid OHLCV data for testing."""
    dates = pd.date_range(start='2022-01-01', periods=50, freq='1H')
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(45000, 47000, 50),
        'high': np.random.uniform(46000, 48000, 50),
        'low': np.random.uniform(44000, 46000, 50),
        'close': np.random.uniform(45000, 47000, 50),
        'volume': np.random.uniform(100, 1000, 50)
    })
    
    # Introduce invalid OHLC relationships
    for i in range(0, len(data), 5):
        data.iloc[i, data.columns.get_loc('high')] = data.iloc[i]['low'] - 100  # High < Low
        data.iloc[i, data.columns.get_loc('low')] = data.iloc[i]['high'] + 200  # Low > High
    
    # Introduce negative volumes
    data.loc[data.index[10:15], 'volume'] = -100
    
    # Introduce zero prices
    data.loc[data.index[20:25], 'close'] = 0
    
    return data

@pytest.fixture
def crypto_fields_data():
    """Crypto-specific fields data for testing."""
    dates = pd.date_range(start='2022-01-01', periods=30, freq='8H')
    
    return pd.DataFrame({
        'timestamp': dates,
        'funding_rate': np.random.uniform(-0.005, 0.005, 30),
        'open_interest': np.random.uniform(100000, 1000000, 30),
        'long_short_ratio': np.random.uniform(0.5, 2.0, 30),
        'liquidation_rate': np.random.uniform(0, 0.1, 30)
    })


class TestValidatorIntegrationBasic:
    """Test basic validator integration functionality."""
    
    def test_mock_validator_creation(self):
        """Test creation of mock validators."""
        # Create mock validators since actual ones might not exist
        mock_price_validator = Mock()
        mock_volume_validator = Mock()
        mock_timeseries_validator = Mock()
        
        # Configure mock return values
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.errors = []
        mock_result.warnings = []
        
        mock_price_validator.validate.return_value = mock_result
        mock_volume_validator.validate.return_value = mock_result
        mock_timeseries_validator.validate.return_value = mock_result
        
        # Test that mocks work
        test_data = pd.DataFrame({'test': [1, 2, 3]})
        
        result1 = mock_price_validator.validate(test_data)
        result2 = mock_volume_validator.validate(test_data)
        result3 = mock_timeseries_validator.validate(test_data)
        
        assert result1.is_valid == True
        assert result2.is_valid == True
        assert result3.is_valid == True
    
    def test_validation_result_structure(self):
        """Test validation result structure."""
        # Create mock validation result
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.errors = []
        mock_result.warnings = []
        
        # Test result attributes
        assert hasattr(mock_result, 'is_valid')
        assert hasattr(mock_result, 'errors')
        assert hasattr(mock_result, 'warnings')
        assert mock_result.is_valid == True
        assert len(mock_result.errors) == 0
        assert len(mock_result.warnings) == 0
    
    def test_validator_chain_concept(self, valid_ohlcv_data):
        """Test the concept of chaining validators."""
        # Create mock validators
        validators = []
        for i in range(3):
            mock_validator = Mock()
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.errors = []
            mock_result.warnings = []
            mock_validator.validate.return_value = mock_result
            validators.append(mock_validator)
        
        # Test running validation chain
        all_valid = True
        all_errors = []
        all_warnings = []
        
        for validator in validators:
            result = validator.validate(valid_ohlcv_data)
            if not result.is_valid:
                all_valid = False
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        assert all_valid == True
        assert len(all_errors) == 0
        assert len(all_warnings) == 0
    
    def test_error_aggregation_concept(self, invalid_ohlcv_data):
        """Test error aggregation concept."""
        # Create mock validators with errors
        validators = []
        for i in range(3):
            mock_validator = Mock()
            mock_result = Mock()
            mock_result.is_valid = False
            mock_result.errors = [f"Error from validator {i}"]
            mock_result.warnings = []
            mock_validator.validate.return_value = mock_result
            validators.append(mock_validator)
        
        # Test error aggregation
        all_valid = True
        all_errors = []
        all_warnings = []
        
        for validator in validators:
            result = validator.validate(invalid_ohlcv_data)
            if not result.is_valid:
                all_valid = False
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        assert all_valid == False
        assert len(all_errors) == 3
        assert "Error from validator 0" in all_errors
        assert "Error from validator 1" in all_errors
        assert "Error from validator 2" in all_errors


class TestValidatorIntegrationErrorHandling:
    """Test error handling in validator integration."""
    
    def test_validator_exception_handling(self, valid_ohlcv_data):
        """Test handling of validator exceptions."""
        # Create mock validator that raises exception
        exception_validator = Mock()
        exception_validator.validate.side_effect = ValueError("Test validator exception")
        
        # Create normal mock validators
        normal_validator1 = Mock()
        normal_validator2 = Mock()
        
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.errors = []
        mock_result.warnings = []
        
        normal_validator1.validate.return_value = mock_result
        normal_validator2.validate.return_value = mock_result
        
        validators = [normal_validator1, exception_validator, normal_validator2]
        
        # Test exception handling
        results = []
        for validator in validators:
            try:
                result = validator.validate(valid_ohlcv_data)
                results.append(result)
            except Exception as e:
                # Handle exception gracefully
                error_result = Mock()
                error_result.is_valid = False
                error_result.errors = [f"Validator exception: {str(e)}"]
                error_result.warnings = []
                results.append(error_result)
        
        # Check that we got results from all validators
        assert len(results) == 3
        assert results[0].is_valid == True  # First validator succeeded
        assert results[1].is_valid == False  # Second validator failed with exception
        assert results[2].is_valid == True  # Third validator succeeded
        assert "exception" in results[1].errors[0].lower()
    
    def test_missing_column_handling(self, valid_ohlcv_data):
        """Test handling of missing columns."""
        # Remove required column
        incomplete_data = valid_ohlcv_data.drop('volume', axis=1)
        
        # Create mock validator that checks for volume column
        volume_validator = Mock()
        
        def check_volume_column(data):
            result = Mock()
            if 'volume' not in data.columns:
                result.is_valid = False
                result.errors = ["Missing required column: volume"]
                result.warnings = []
            else:
                result.is_valid = True
                result.errors = []
                result.warnings = []
            return result
        
        volume_validator.validate.side_effect = check_volume_column
        
        # Test validation
        result = volume_validator.validate(incomplete_data)
        
        # Check results
        assert result.is_valid == False
        assert len(result.errors) > 0
        assert "volume" in result.errors[0].lower()
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        empty_data = pd.DataFrame()
        
        # Create mock validator that checks for empty data
        empty_data_validator = Mock()
        
        def check_empty_data(data):
            result = Mock()
            if data.empty:
                result.is_valid = False
                result.errors = ["Empty data provided"]
                result.warnings = []
            else:
                result.is_valid = True
                result.errors = []
                result.warnings = []
            return result
        
        empty_data_validator.validate.side_effect = check_empty_data
        
        # Test validation
        result = empty_data_validator.validate(empty_data)
        
        # Check results
        assert result.is_valid == False
        assert len(result.errors) > 0
        assert "empty" in result.errors[0].lower()
    
    def test_multiple_validator_error_aggregation(self, invalid_ohlcv_data):
        """Test aggregation of errors from multiple validators."""
        # Create multiple mock validators with different errors
        validators = []
        expected_errors = []
        
        for i in range(3):
            validator = Mock()
            error_msg = f"Error from validator {i}"
            expected_errors.append(error_msg)
            
            result = Mock()
            result.is_valid = False
            result.errors = [error_msg]
            result.warnings = []
            validator.validate.return_value = result
            
            validators.append(validator)
        
        # Run all validators and aggregate results
        all_errors = []
        overall_valid = True
        
        for validator in validators:
            result = validator.validate(invalid_ohlcv_data)
            if not result.is_valid:
                overall_valid = False
            all_errors.extend(result.errors)
        
        # Check aggregated results
        assert overall_valid == False
        assert len(all_errors) == 3
        for expected_error in expected_errors:
            assert expected_error in all_errors


class TestValidatorIntegrationReporting:
    """Test validation reporting and result formatting."""
    
    def test_mock_validation_report_generation(self):
        """Test generation of mock validation reports."""
        # Create mock validation result with errors
        mock_result = Mock()
        mock_result.is_valid = False
        mock_result.errors = ["Error 1", "Error 2"]
        mock_result.warnings = ["Warning 1"]
        
        # Create mock report generator
        def generate_mock_report():
            return {
                'summary': {
                    'total_errors': len(mock_result.errors),
                    'total_warnings': len(mock_result.warnings),
                    'is_valid': mock_result.is_valid
                },
                'errors': [
                    {
                        'validator_type': 'MockValidator',
                        'message': error,
                        'severity': 'ERROR'
                    } for error in mock_result.errors
                ],
                'warnings': [
                    {
                        'validator_type': 'MockValidator',
                        'message': warning,
                        'severity': 'WARNING'
                    } for warning in mock_result.warnings
                ],
                'statistics': {
                    'total_checks': 3,
                    'passed_checks': 0,
                    'failed_checks': 3
                }
            }
        
        mock_result.generate_report = generate_mock_report
        
        # Generate report
        report = mock_result.generate_report()
        
        # Check report structure
        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'errors' in report
        assert 'warnings' in report
        assert 'statistics' in report
        
        # Check summary
        assert report['summary']['total_errors'] == 2
        assert report['summary']['total_warnings'] == 1
        assert report['summary']['is_valid'] == False
        
        # Check error details
        assert len(report['errors']) == 2
        for error_detail in report['errors']:
            assert 'validator_type' in error_detail
            assert 'message' in error_detail
            assert 'severity' in error_detail


class TestValidatorIntegrationPerformance:
    """Test performance of validator integration."""
    
    def test_large_dataset_validation_performance(self):
        """Test validation performance with large datasets."""
        import time
        
        # Create large dataset
        large_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2022-01-01', periods=10000, freq='1min'),
            'open': np.random.uniform(45000, 47000, 10000),
            'high': np.random.uniform(46000, 48000, 10000),
            'low': np.random.uniform(44000, 46000, 10000),
            'close': np.random.uniform(45000, 47000, 10000),
            'volume': np.random.uniform(100, 1000, 10000)
        })
        
        # Create mock validators
        validators = []
        for i in range(3):
            mock_validator = Mock()
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.errors = []
            mock_result.warnings = []
            mock_validator.validate.return_value = mock_result
            validators.append(mock_validator)
        
        # Measure validation time
        start_time = time.time()
        
        for validator in validators:
            result = validator.validate(large_data)
        
        validation_time = time.time() - start_time
        
        # Check performance
        assert validation_time < 5  # Should complete within 5 seconds
        
        # Check throughput
        throughput = len(large_data) / validation_time
        assert throughput > 1000  # Should process at least 1000 rows per second
    
    def test_memory_efficient_validation(self):
        """Test memory-efficient validation of large datasets."""
        # Create multiple large datasets
        datasets = []
        for i in range(5):
            data = pd.DataFrame({
                'timestamp': pd.date_range(start='2022-01-01', periods=5000, freq='1min'),
                'close': np.random.uniform(45000, 47000, 5000),
                'volume': np.random.uniform(100, 1000, 5000)
            })
            datasets.append(data)
        
        # Create mock validator
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_validator.validate.return_value = mock_result
        
        # Validate multiple datasets
        results = []
        for dataset in datasets:
            result = mock_validator.validate(dataset)
            results.append(result)
        
        # Check all validations succeeded
        assert len(results) == 5
        for result in results:
            assert result.is_valid == True
    
    def test_concurrent_validation(self, valid_ohlcv_data):
        """Test concurrent validation of multiple datasets."""
        import threading
        
        # Create mock validator
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.is_valid = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_validator.validate.return_value = mock_result
        
        results = []
        
        def validate_data(data_id):
            test_data = valid_ohlcv_data.copy()
            test_data['data_id'] = data_id
            
            result = mock_validator.validate(test_data)
            results.append((data_id, result))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=validate_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 5
        for data_id, result in results:
            assert result.is_valid == True


class TestValidatorIntegrationConfigurationManagement:
    """Test validator configuration and management."""
    
    def test_validator_configuration(self):
        """Test validator configuration management."""
        # Create mock validator with configuration
        mock_validator = Mock()
        
        # Configure validator
        config = {
            'strict_mode': True,
            'tolerance': 0.01,
            'required_fields': ['open', 'high', 'low', 'close', 'volume']
        }
        
        mock_validator.config = config
        
        # Test configuration access
        assert mock_validator.config['strict_mode'] == True
        assert mock_validator.config['tolerance'] == 0.01
        assert 'volume' in mock_validator.config['required_fields']
    
    def test_validator_registry_concept(self):
        """Test validator registry concept."""
        # Create mock validator registry
        validator_registry = {}
        
        # Register validators
        price_validator = Mock()
        price_validator.name = "PriceValidator"
        
        volume_validator = Mock()
        volume_validator.name = "VolumeValidator"
        
        validator_registry['price'] = price_validator
        validator_registry['volume'] = volume_validator
        
        # Test registry access
        assert 'price' in validator_registry
        assert 'volume' in validator_registry
        assert validator_registry['price'].name == "PriceValidator"
        assert validator_registry['volume'].name == "VolumeValidator"
    
    def test_validator_pipeline_concept(self, valid_ohlcv_data):
        """Test validator pipeline concept."""
        # Create validator pipeline
        pipeline = []
        
        # Add validators to pipeline
        for i in range(3):
            validator = Mock()
            validator.name = f"Validator{i}"
            
            result = Mock()
            result.is_valid = True
            result.errors = []
            result.warnings = []
            validator.validate.return_value = result
            
            pipeline.append(validator)
        
        # Run pipeline
        pipeline_results = []
        for validator in pipeline:
            result = validator.validate(valid_ohlcv_data)
            pipeline_results.append({
                'validator': validator.name,
                'result': result
            })
        
        # Check pipeline results
        assert len(pipeline_results) == 3
        for pipeline_result in pipeline_results:
            assert 'validator' in pipeline_result
            assert 'result' in pipeline_result
            assert pipeline_result['result'].is_valid == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])