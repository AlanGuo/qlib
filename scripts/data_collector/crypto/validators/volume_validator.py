# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Volume validator for cryptocurrency data validation.

This module provides validation for trading volume data, including
non-negativity checks, outlier detection, and volume consistency validation.
"""

import time

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from validators.base_validator import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity


class VolumeValidator(BaseValidator):
    """
    Validator for trading volume data.
    
    Validates:
    - Volume non-negativity
    - Volume outlier detection
    - Volume consistency across different fields
    - Zero volume detection
    """
    
    def __init__(
        self, 
        outlier_threshold: float = 5.0,
        min_volume: float = 0.0,
        max_zero_volume_ratio: float = 0.1,
        name: Optional[str] = None
    ):
        """
        Initialize the volume validator.
        
        Parameters
        ----------
        outlier_threshold : float, default 5.0
            Z-score threshold for volume outlier detection
        min_volume : float, default 0.0
            Minimum allowed volume value
        max_zero_volume_ratio : float, default 0.1
            Maximum allowed ratio of zero volume periods (10%)
        name : str, optional
            Name of the validator
        """
        super().__init__(name)
        self.outlier_threshold = outlier_threshold
        self.min_volume = min_volume
        self.max_zero_volume_ratio = max_zero_volume_ratio
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate volume data.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with volume columns
        
        Returns
        -------
        ValidationResult
            Validation result with any issues found
        """
        start_time = time.time()
        issues = []
        statistics = {}
        
        # Check required columns
        required_columns = ['volume']
        issues.extend(self._check_required_columns(data, required_columns))
        
        # If critical issues found, return early
        if any(issue.severity == ValidationSeverity.CRITICAL for issue in issues):
            return ValidationResult(
                validator_name=self.name,
                is_valid=False,
                issues=issues,
                statistics=statistics,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Check data types
        volume_columns = [col for col in ['volume', 'volume_24h', 'volume_usd_24h'] if col in data.columns]
        expected_types = {col: float for col in volume_columns}
        issues.extend(self._check_data_types(data, expected_types))
        
        # Validate volume non-negativity
        issues.extend(self._validate_volume_non_negativity(data))
        
        # Detect volume outliers
        issues.extend(self._detect_volume_outliers(data))
        
        # Check zero volume ratio
        issues.extend(self._check_zero_volume_ratio(data))
        
        # Validate volume consistency
        issues.extend(self._validate_volume_consistency(data))
        
        # Calculate statistics
        statistics = self._calculate_statistics(data)
        
        # Determine if validation passed
        is_valid = not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                          for issue in issues)
        
        return ValidationResult(
            validator_name=self.name,
            is_valid=is_valid,
            issues=issues,
            statistics=statistics,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def _validate_volume_non_negativity(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate that all volume values are non-negative."""
        issues = []
        
        volume_columns = [col for col in ['volume', 'volume_24h', 'volume_usd_24h'] if col in data.columns]
        
        for col in volume_columns:
            negative_volumes = data[data[col] < self.min_volume]
            for idx in negative_volumes.index:
                if pd.notna(data.loc[idx, col]):
                    issues.append(self._create_issue(
                        ValidationSeverity.ERROR,
                        f"{col.capitalize()} ({data.loc[idx, col]}) is negative",
                        field_name=col,
                        row_index=idx,
                        value=data.loc[idx, col]
                    ))
        
        return issues
    
    def _detect_volume_outliers(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Detect volume outliers using statistical methods."""
        issues = []
        
        volume_columns = [col for col in ['volume', 'volume_24h', 'volume_usd_24h'] if col in data.columns]
        
        for col in volume_columns:
            if len(data) > 10:  # Need sufficient data for outlier detection
                volumes = data[col].dropna()
                
                # Remove zero volumes for outlier calculation
                non_zero_volumes = volumes[volumes > 0]
                
                if len(non_zero_volumes) > 10:
                    # Use log transformation for volume data (often log-normal)
                    log_volumes = np.log(non_zero_volumes)
                    z_scores = np.abs((log_volumes - log_volumes.mean()) / log_volumes.std())
                    
                    # Find outliers in original data
                    outlier_indices = z_scores[z_scores > self.outlier_threshold].index
                    
                    for idx in outlier_indices:
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"{col.capitalize()} ({data.loc[idx, col]}) is a statistical outlier "
                            f"(Log Z-score: {z_scores.loc[idx]:.2f})",
                            field_name=col,
                            row_index=idx,
                            value=data.loc[idx, col],
                            log_z_score=z_scores.loc[idx]
                        ))
        
        return issues
    
    def _check_zero_volume_ratio(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Check if the ratio of zero volume periods is acceptable."""
        issues = []
        
        if 'volume' in data.columns:
            total_periods = len(data)
            zero_volume_periods = len(data[data['volume'] == 0])
            zero_volume_ratio = zero_volume_periods / total_periods if total_periods > 0 else 0
            
            if zero_volume_ratio > self.max_zero_volume_ratio:
                issues.append(self._create_issue(
                    ValidationSeverity.WARNING,
                    f"High ratio of zero volume periods: {zero_volume_ratio:.2%} "
                    f"(threshold: {self.max_zero_volume_ratio:.2%})",
                    field_name='volume',
                    zero_volume_periods=zero_volume_periods,
                    total_periods=total_periods,
                    ratio=zero_volume_ratio
                ))
        
        return issues
    
    def _validate_volume_consistency(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate consistency between different volume fields."""
        issues = []
        
        # Check if volume_usd_24h is consistent with volume and price
        if all(col in data.columns for col in ['volume', 'volume_usd_24h', 'close']):
            # Calculate expected USD volume
            expected_usd_volume = data['volume'] * data['close']
            actual_usd_volume = data['volume_usd_24h']
            
            # Allow for some tolerance (e.g., 10% difference)
            tolerance = 0.1
            
            for idx in data.index:
                if (pd.notna(expected_usd_volume.loc[idx]) and 
                    pd.notna(actual_usd_volume.loc[idx]) and
                    expected_usd_volume.loc[idx] > 0):
                    
                    relative_diff = abs(expected_usd_volume.loc[idx] - actual_usd_volume.loc[idx]) / expected_usd_volume.loc[idx]
                    
                    if relative_diff > tolerance:
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"Volume USD inconsistency: expected {expected_usd_volume.loc[idx]:.2f}, "
                            f"actual {actual_usd_volume.loc[idx]:.2f} "
                            f"(difference: {relative_diff:.2%})",
                            field_name='volume_usd_24h',
                            row_index=idx,
                            expected=expected_usd_volume.loc[idx],
                            actual=actual_usd_volume.loc[idx],
                            relative_diff=relative_diff
                        ))
        
        return issues
    
    def _calculate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate volume-related statistics."""
        stats = {}
        
        volume_columns = [col for col in ['volume', 'volume_24h', 'volume_usd_24h'] if col in data.columns]
        
        for col in volume_columns:
            volumes = data[col].dropna()
            if len(volumes) > 0:
                stats[f'{col}_mean'] = float(volumes.mean())
                stats[f'{col}_median'] = float(volumes.median())
                stats[f'{col}_std'] = float(volumes.std())
                stats[f'{col}_min'] = float(volumes.min())
                stats[f'{col}_max'] = float(volumes.max())
                stats[f'{col}_null_count'] = int(data[col].isnull().sum())
                stats[f'{col}_zero_count'] = int((volumes == 0).sum())
                
                # Calculate percentiles
                stats[f'{col}_p25'] = float(volumes.quantile(0.25))
                stats[f'{col}_p75'] = float(volumes.quantile(0.75))
                stats[f'{col}_p95'] = float(volumes.quantile(0.95))
                
                # Calculate zero volume ratio
                stats[f'{col}_zero_ratio'] = float((volumes == 0).sum() / len(volumes))
        
        # Calculate volume trends
        if 'volume' in data.columns and len(data) > 1:
            volume_changes = data['volume'].pct_change().dropna()
            if len(volume_changes) > 0:
                stats['volume_change_mean'] = float(volume_changes.mean())
                stats['volume_change_std'] = float(volume_changes.std())
                stats['max_volume_change'] = float(volume_changes.abs().max())
        
        return stats
