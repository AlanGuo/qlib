# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Main data validator for cryptocurrency data collection.

This module provides the main CryptoDataValidator class that coordinates
all validation processes for cryptocurrency market data.
"""

import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd

from validators.base_validator import BaseValidator, ValidationResult, ValidationReport, ValidationSeverity
from validators.price_validator import PriceValidator
from validators.volume_validator import VolumeValidator
from validators.timeseries_validator import TimeSeriesValidator
from validators.completeness_validator import CompletenessValidator
from validators.consistency_validator import ConsistencyValidator
from validators.anomaly_validator import AnomalyValidator
from config.validation_config import ValidationConfig


class CryptoDataValidator:
    """
    Main validator for cryptocurrency data.
    
    Coordinates multiple validators to provide comprehensive data quality validation.
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize the crypto data validator.
        
        Parameters
        ----------
        config : ValidationConfig, optional
            Configuration for validation parameters. If None, uses default config.
        """
        self.config = config or ValidationConfig()
        self._validators = self._initialize_validators()
    
    def _initialize_validators(self) -> List[BaseValidator]:
        """Initialize all validators based on configuration."""
        validators = []
        
        # Completeness validator (always first)
        validators.append(CompletenessValidator(
            required_fields=self.config.required_fields,
            optional_fields=self.config.optional_fields,
            max_missing_ratio=self.config.max_missing_ratio,
            min_rows=self.config.min_rows
        ))
        
        # Price validator
        if self.config.enable_price_validation:
            validators.append(PriceValidator(
                max_price_change_pct=self.config.max_price_change_pct,
                outlier_threshold=self.config.price_outlier_threshold,
                min_price=self.config.min_price
            ))
        
        # Volume validator
        if self.config.enable_volume_validation:
            validators.append(VolumeValidator(
                outlier_threshold=self.config.volume_outlier_threshold,
                min_volume=self.config.min_volume,
                max_zero_volume_ratio=self.config.max_zero_volume_ratio
            ))
        
        # Time series validator
        if self.config.enable_timeseries_validation:
            validators.append(TimeSeriesValidator(
                expected_interval_seconds=self.config.expected_interval_seconds,
                max_missing_ratio=self.config.max_missing_periods_ratio,
                timestamp_column=self.config.timestamp_column,
                allow_duplicates=self.config.allow_duplicate_timestamps
            ))
        
        # Consistency validator
        if self.config.enable_consistency_validation:
            validators.append(ConsistencyValidator(
                tolerance=self.config.consistency_tolerance,
                funding_rate_range=self.config.funding_rate_range,
                change_24h_range=self.config.change_24h_range
            ))
        
        # Anomaly validator
        if self.config.enable_anomaly_detection:
            validators.append(AnomalyValidator(
                z_score_threshold=self.config.anomaly_z_score_threshold,
                iqr_multiplier=self.config.anomaly_iqr_multiplier,
                price_spike_threshold=self.config.price_spike_threshold,
                volume_spike_threshold=self.config.volume_spike_threshold,
                min_data_points=self.config.min_data_points_for_anomaly
            ))
        
        return validators
    
    def validate(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        validators: Optional[List[str]] = None
    ) -> ValidationReport:
        """
        Validate cryptocurrency data.
        
        Parameters
        ----------
        data : pd.DataFrame
            The data to validate
        symbol : str
            Symbol being validated (e.g., 'BTC/USDT')
        timeframe : str
            Timeframe of the data (e.g., '1h', '1d')
        validators : List[str], optional
            List of validator names to run. If None, runs all enabled validators.
        
        Returns
        -------
        ValidationReport
            Comprehensive validation report
        """
        start_time = datetime.now()
        results = []
        
        # Filter validators if specific ones requested
        validators_to_run = self._validators
        if validators:
            validator_map = {v.__class__.__name__: v for v in self._validators}
            validators_to_run = [validator_map[name] for name in validators if name in validator_map]
        
        # Run each validator
        for validator in validators_to_run:
            try:
                result = validator.validate(data)
                results.append(result)
            except Exception as e:
                # Create error result for failed validator
                from validators.base_validator import ValidationIssue
                error_issue = ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Validator failed with error: {str(e)}",
                    details={'error_type': type(e).__name__, 'error_message': str(e)}
                )
                error_result = ValidationResult(
                    validator_name=validator.name,
                    is_valid=False,
                    issues=[error_issue],
                    statistics={'error': True},
                    execution_time_ms=0.0
                )
                results.append(error_result)
        
        # Create validation report
        report = ValidationReport(
            symbol=symbol,
            timeframe=timeframe,
            validation_time=start_time,
            data_rows=len(data),
            results=results
        )
        
        return report
    
    def validate_batch(
        self, 
        data_batch: Dict[str, pd.DataFrame], 
        timeframe: str,
        validators: Optional[List[str]] = None
    ) -> Dict[str, ValidationReport]:
        """
        Validate multiple datasets in batch.
        
        Parameters
        ----------
        data_batch : Dict[str, pd.DataFrame]
            Dictionary mapping symbols to their data
        timeframe : str
            Timeframe of the data
        validators : List[str], optional
            List of validator names to run
        
        Returns
        -------
        Dict[str, ValidationReport]
            Dictionary mapping symbols to their validation reports
        """
        reports = {}
        
        for symbol, data in data_batch.items():
            reports[symbol] = self.validate(data, symbol, timeframe, validators)
        
        return reports
    
    def get_validator_names(self) -> List[str]:
        """Get names of all available validators."""
        return [validator.name for validator in self._validators]
    
    def get_validator(self, name: str) -> Optional[BaseValidator]:
        """Get a specific validator by name."""
        for validator in self._validators:
            if validator.name == name:
                return validator
        return None
    
    def add_validator(self, validator: BaseValidator) -> None:
        """Add a custom validator."""
        self._validators.append(validator)
    
    def remove_validator(self, name: str) -> bool:
        """Remove a validator by name."""
        for i, validator in enumerate(self._validators):
            if validator.name == name:
                del self._validators[i]
                return True
        return False
    
    def create_summary_report(self, reports: Dict[str, ValidationReport]) -> Dict[str, Any]:
        """
        Create a summary report from multiple validation reports.
        
        Parameters
        ----------
        reports : Dict[str, ValidationReport]
            Dictionary of validation reports
        
        Returns
        -------
        Dict[str, Any]
            Summary statistics across all reports
        """
        if not reports:
            return {}
        
        summary = {
            'total_symbols': len(reports),
            'total_data_rows': sum(report.data_rows for report in reports.values()),
            'overall_status_counts': {'PASS': 0, 'WARNING': 0, 'FAIL': 0},
            'total_errors': sum(report.total_errors for report in reports.values()),
            'total_warnings': sum(report.total_warnings for report in reports.values()),
            'validator_performance': {},
            'symbols_by_status': {'PASS': [], 'WARNING': [], 'FAIL': []},
            'execution_time_ms': sum(
                sum(result.execution_time_ms for result in report.results)
                for report in reports.values()
            )
        }
        
        # Count status distribution
        for symbol, report in reports.items():
            status = report.overall_status
            summary['overall_status_counts'][status] += 1
            summary['symbols_by_status'][status].append(symbol)
        
        # Aggregate validator performance
        validator_stats = {}
        for report in reports.values():
            for result in report.results:
                validator_name = result.validator_name
                if validator_name not in validator_stats:
                    validator_stats[validator_name] = {
                        'runs': 0,
                        'errors': 0,
                        'warnings': 0,
                        'execution_time_ms': 0.0
                    }
                
                validator_stats[validator_name]['runs'] += 1
                validator_stats[validator_name]['errors'] += result.error_count
                validator_stats[validator_name]['warnings'] += result.warning_count
                validator_stats[validator_name]['execution_time_ms'] += result.execution_time_ms
        
        summary['validator_performance'] = validator_stats
        
        return summary
