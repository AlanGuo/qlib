# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Time series validator for cryptocurrency data validation.

This module provides validation for time series data, including
timestamp validation, continuity checks, and interval consistency.
"""

import time

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from validators.base_validator import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity


class TimeSeriesValidator(BaseValidator):
    """
    Validator for time series data.
    
    Validates:
    - Timestamp ordering
    - Duplicate timestamps
    - Missing time periods
    - Interval consistency
    """
    
    def __init__(
        self, 
        expected_interval_seconds: Optional[int] = None,
        max_missing_ratio: float = 0.05,
        timestamp_column: str = 'timestamp',
        allow_duplicates: bool = False,
        name: Optional[str] = None
    ):
        """
        Initialize the time series validator.
        
        Parameters
        ----------
        expected_interval_seconds : int, optional
            Expected interval between consecutive timestamps in seconds.
            If None, will try to infer from data.
        max_missing_ratio : float, default 0.05
            Maximum allowed ratio of missing time periods (5%)
        timestamp_column : str, default 'timestamp'
            Name of the timestamp column
        allow_duplicates : bool, default False
            Whether to allow duplicate timestamps
        name : str, optional
            Name of the validator
        """
        super().__init__(name)
        self.expected_interval_seconds = expected_interval_seconds
        self.max_missing_ratio = max_missing_ratio
        self.timestamp_column = timestamp_column
        self.allow_duplicates = allow_duplicates
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate time series data.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with timestamp index or column
        
        Returns
        -------
        ValidationResult
            Validation result with any issues found
        """
        start_time = time.time()
        issues = []
        statistics = {}
        
        # Check if data is empty
        if data.empty:
            issues.append(self._create_issue(
                ValidationSeverity.CRITICAL,
                "Dataset is empty",
                details={'row_count': 0}
            ))
            return ValidationResult(
                validator_name=self.name,
                is_valid=False,
                issues=issues,
                statistics={'row_count': 0},
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Get timestamps
        timestamps = self._get_timestamps(data)
        if timestamps is None:
            issues.append(self._create_issue(
                ValidationSeverity.CRITICAL,
                f"Timestamp column '{self.timestamp_column}' not found and index is not datetime",
                field=self.timestamp_column
            ))
            return ValidationResult(
                validator_name=self.name,
                is_valid=False,
                issues=issues,
                statistics=statistics,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Validate timestamp ordering
        issues.extend(self._validate_timestamp_ordering(timestamps))
        
        # Check for duplicate timestamps
        if not self.allow_duplicates:
            issues.extend(self._check_duplicate_timestamps(timestamps))
        
        # Validate interval consistency
        issues.extend(self._validate_interval_consistency(timestamps))
        
        # Check for missing periods
        issues.extend(self._check_missing_periods(timestamps))
        
        # Calculate statistics
        statistics = self._calculate_statistics(timestamps)
        
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
    
    def _get_timestamps(self, data: pd.DataFrame) -> Optional[pd.Series]:
        """Extract timestamps from data."""
        if self.timestamp_column in data.columns:
            timestamps = pd.to_datetime(data[self.timestamp_column])
        elif isinstance(data.index, pd.DatetimeIndex):
            timestamps = pd.Series(data.index, index=data.index)
        else:
            return None
        
        return timestamps
    
    def _validate_timestamp_ordering(self, timestamps: pd.Series) -> List[ValidationIssue]:
        """Validate that timestamps are in ascending order."""
        issues = []
        
        # Check if timestamps are sorted
        if not timestamps.is_monotonic_increasing:
            # Find out-of-order timestamps
            for i in range(1, len(timestamps)):
                if timestamps.iloc[i] < timestamps.iloc[i-1]:
                    issues.append(self._create_issue(
                        ValidationSeverity.ERROR,
                        f"Timestamp out of order at index {i}: "
                        f"{timestamps.iloc[i]} < {timestamps.iloc[i-1]}",
                        field=self.timestamp_column,
                        row_index=timestamps.index[i],
                        current_timestamp=timestamps.iloc[i],
                        previous_timestamp=timestamps.iloc[i-1]
                    ))
        
        return issues
    
    def _check_duplicate_timestamps(self, timestamps: pd.Series) -> List[ValidationIssue]:
        """Check for duplicate timestamps."""
        issues = []
        
        duplicates = timestamps.duplicated()
        duplicate_count = duplicates.sum()
        
        if duplicate_count > 0:
            duplicate_values = timestamps[duplicates].unique()
            issues.append(self._create_issue(
                ValidationSeverity.ERROR,
                f"Found {duplicate_count} duplicate timestamps",
                field=self.timestamp_column,
                duplicate_count=duplicate_count,
                sample_duplicates=duplicate_values[:5].tolist()  # Show first 5 duplicates
            ))
        
        return issues
    
    def _validate_interval_consistency(self, timestamps: pd.Series) -> List[ValidationIssue]:
        """Validate consistency of time intervals."""
        issues = []
        
        if len(timestamps) < 2:
            return issues
        
        # Calculate intervals
        intervals = timestamps.diff().dropna()
        interval_seconds = intervals.dt.total_seconds()
        
        # Determine expected interval if not provided
        expected_interval = self.expected_interval_seconds
        if expected_interval is None:
            # Use the most common interval
            mode_interval = interval_seconds.mode()
            if len(mode_interval) > 0:
                expected_interval = mode_interval.iloc[0]
            else:
                expected_interval = interval_seconds.median()
        
        # Check for significant deviations from expected interval
        tolerance = 0.1  # 10% tolerance
        min_expected = expected_interval * (1 - tolerance)
        max_expected = expected_interval * (1 + tolerance)
        
        irregular_intervals = interval_seconds[
            (interval_seconds < min_expected) | (interval_seconds > max_expected)
        ]
        
        for idx in irregular_intervals.index:
            actual_interval = interval_seconds.loc[idx]
            issues.append(self._create_issue(
                ValidationSeverity.WARNING,
                f"Irregular time interval at index {idx}: "
                f"{actual_interval:.1f}s (expected: {expected_interval:.1f}s)",
                field=self.timestamp_column,
                row_index=idx,
                actual_interval=actual_interval,
                expected_interval=expected_interval,
                deviation_ratio=(actual_interval - expected_interval) / expected_interval
            ))
        
        return issues
    
    def _check_missing_periods(self, timestamps: pd.Series) -> List[ValidationIssue]:
        """Check for missing time periods."""
        issues = []
        
        if len(timestamps) < 2:
            return issues
        
        # Calculate expected number of periods
        start_time = timestamps.min()
        end_time = timestamps.max()
        
        # Determine interval
        intervals = timestamps.diff().dropna()
        interval_seconds = intervals.dt.total_seconds()
        
        if len(interval_seconds) == 0:
            return issues
        
        # Use median interval as expected
        expected_interval = interval_seconds.median()
        
        # Calculate expected number of periods
        total_duration = (end_time - start_time).total_seconds()
        expected_periods = int(total_duration / expected_interval) + 1
        actual_periods = len(timestamps)
        
        missing_periods = expected_periods - actual_periods
        missing_ratio = missing_periods / expected_periods if expected_periods > 0 else 0
        
        if missing_ratio > self.max_missing_ratio:
            issues.append(self._create_issue(
                ValidationSeverity.WARNING,
                f"High ratio of missing time periods: {missing_ratio:.2%} "
                f"({missing_periods} missing out of {expected_periods} expected)",
                field=self.timestamp_column,
                missing_periods=missing_periods,
                expected_periods=expected_periods,
                missing_ratio=missing_ratio
            ))
        
        # Find gaps larger than expected interval
        large_gaps = interval_seconds[interval_seconds > expected_interval * 2]
        
        for idx in large_gaps.index:
            gap_duration = interval_seconds.loc[idx]
            missing_in_gap = int(gap_duration / expected_interval) - 1
            
            if missing_in_gap > 0:
                issues.append(self._create_issue(
                    ValidationSeverity.INFO,
                    f"Data gap at index {idx}: {gap_duration:.1f}s "
                    f"(approximately {missing_in_gap} missing periods)",
                    field=self.timestamp_column,
                    row_index=idx,
                    gap_duration=gap_duration,
                    estimated_missing_periods=missing_in_gap
                ))
        
        return issues
    
    def _calculate_statistics(self, timestamps: pd.Series) -> Dict[str, Any]:
        """Calculate time series statistics."""
        stats = {
            'total_periods': len(timestamps),
            'start_time': timestamps.min().isoformat() if len(timestamps) > 0 else None,
            'end_time': timestamps.max().isoformat() if len(timestamps) > 0 else None,
        }
        
        if len(timestamps) > 1:
            # Calculate duration
            duration = timestamps.max() - timestamps.min()
            stats['total_duration_seconds'] = duration.total_seconds()
            stats['total_duration_hours'] = duration.total_seconds() / 3600
            stats['total_duration_days'] = duration.days
            
            # Calculate intervals
            intervals = timestamps.diff().dropna()
            interval_seconds = intervals.dt.total_seconds()
            
            if len(interval_seconds) > 0:
                stats['interval_mean_seconds'] = float(interval_seconds.mean())
                stats['interval_median_seconds'] = float(interval_seconds.median())
                stats['interval_std_seconds'] = float(interval_seconds.std())
                stats['interval_min_seconds'] = float(interval_seconds.min())
                stats['interval_max_seconds'] = float(interval_seconds.max())
                
                # Calculate regularity metrics
                stats['interval_coefficient_of_variation'] = float(
                    interval_seconds.std() / interval_seconds.mean() 
                    if interval_seconds.mean() > 0 else 0
                )
        
        # Check for duplicates
        duplicate_count = timestamps.duplicated().sum()
        stats['duplicate_timestamps'] = int(duplicate_count)
        stats['duplicate_ratio'] = float(duplicate_count / len(timestamps)) if len(timestamps) > 0 else 0
        
        # Check ordering
        stats['is_sorted'] = bool(timestamps.is_monotonic_increasing)
        
        return stats
