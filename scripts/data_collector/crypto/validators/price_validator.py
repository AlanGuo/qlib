# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Price validator for cryptocurrency data validation.

This module provides validation for OHLC price data, including logical
consistency checks, outlier detection, and price change validation.
"""

import time

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd



from validators.base_validator import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity


class PriceValidator(BaseValidator):
    """
    Validator for OHLC price data.
    
    Validates:
    - OHLC logical relationships (high >= max(open, close), etc.)
    - Price positivity
    - Price change reasonableness
    - Price outlier detection
    """
    
    def __init__(
        self, 
        max_price_change_pct: float = 50.0,
        outlier_threshold: float = 3.0,
        min_price: float = 0.0,
        name: Optional[str] = None
    ):
        """
        Initialize the price validator.
        
        Parameters
        ----------
        max_price_change_pct : float, default 50.0
            Maximum allowed price change percentage in a single period
        outlier_threshold : float, default 3.0
            Z-score threshold for outlier detection
        min_price : float, default 0.0
            Minimum allowed price value
        name : str, optional
            Name of the validator
        """
        super().__init__(name)
        self.max_price_change_pct = max_price_change_pct
        self.outlier_threshold = outlier_threshold
        self.min_price = min_price
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate OHLC price data.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with OHLC price columns
        
        Returns
        -------
        ValidationResult
            Validation result with any issues found
        """
        start_time = time.time()
        issues = []
        statistics = {}
        
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close']
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
        expected_types = {col: float for col in required_columns}
        issues.extend(self._check_data_types(data, expected_types))
        
        # Validate OHLC relationships
        issues.extend(self._validate_ohlc_relationships(data))
        
        # Validate price positivity
        issues.extend(self._validate_price_positivity(data))
        
        # Validate price changes
        issues.extend(self._validate_price_changes(data))
        
        # Detect price outliers
        issues.extend(self._detect_price_outliers(data))
        
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
    
    def _validate_ohlc_relationships(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate logical relationships between OHLC prices."""
        issues = []
        
        # Check high >= max(open, close)
        high_violations = data[data['high'] < np.maximum(data['open'], data['close'])]
        for idx in high_violations.index:
            issues.append(self._create_issue(
                ValidationSeverity.ERROR,
                f"High price ({data.loc[idx, 'high']}) is less than max(open, close)",
                field_name='high',
                row_index=idx,
                value=data.loc[idx, 'high'],
                open=data.loc[idx, 'open'],
                close=data.loc[idx, 'close']
            ))
        
        # Check low <= min(open, close)
        low_violations = data[data['low'] > np.minimum(data['open'], data['close'])]
        for idx in low_violations.index:
            issues.append(self._create_issue(
                ValidationSeverity.ERROR,
                f"Low price ({data.loc[idx, 'low']}) is greater than min(open, close)",
                field_name='low',
                row_index=idx,
                value=data.loc[idx, 'low'],
                open=data.loc[idx, 'open'],
                close=data.loc[idx, 'close']
            ))
        
        # Check high >= low
        hl_violations = data[data['high'] < data['low']]
        for idx in hl_violations.index:
            issues.append(self._create_issue(
                ValidationSeverity.ERROR,
                f"High price ({data.loc[idx, 'high']}) is less than low price ({data.loc[idx, 'low']})",
                field_name='high',
                row_index=idx,
                high=data.loc[idx, 'high'],
                low=data.loc[idx, 'low']
            ))
        
        return issues
    
    def _validate_price_positivity(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate that all prices are positive."""
        issues = []
        
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                negative_prices = data[data[col] <= self.min_price]
                for idx in negative_prices.index:
                    issues.append(self._create_issue(
                        ValidationSeverity.ERROR,
                        f"{col.capitalize()} price ({data.loc[idx, col]}) is not positive",
                        field_name=col,
                        row_index=idx,
                        value=data.loc[idx, col]
                    ))
        
        return issues
    
    def _validate_price_changes(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate that price changes are within reasonable bounds."""
        issues = []
        
        if len(data) < 2:
            return issues
        
        # Calculate price changes using close prices
        if 'close' in data.columns:
            price_changes = data['close'].pct_change().abs() * 100
            
            # Find excessive price changes
            excessive_changes = price_changes[price_changes > self.max_price_change_pct]
            
            for idx in excessive_changes.index:
                if pd.notna(excessive_changes.loc[idx]):
                    prev_idx = data.index[data.index.get_loc(idx) - 1]
                    issues.append(self._create_issue(
                        ValidationSeverity.WARNING,
                        f"Excessive price change: {excessive_changes.loc[idx]:.2f}% "
                        f"(from {data.loc[prev_idx, 'close']} to {data.loc[idx, 'close']})",
                        field_name='close',
                        row_index=idx,
                        change_pct=excessive_changes.loc[idx],
                        prev_price=data.loc[prev_idx, 'close'],
                        current_price=data.loc[idx, 'close']
                    ))
        
        return issues
    
    def _detect_price_outliers(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Detect price outliers using statistical methods."""
        issues = []
        
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns and len(data) > 10:  # Need sufficient data for outlier detection
                prices = data[col].dropna()
                
                if len(prices) > 10:
                    # Calculate Z-scores
                    z_scores = np.abs((prices - prices.mean()) / prices.std())
                    outliers = z_scores[z_scores > self.outlier_threshold]
                    
                    for idx in outliers.index:
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"{col.capitalize()} price ({data.loc[idx, col]}) is a statistical outlier "
                            f"(Z-score: {z_scores.loc[idx]:.2f})",
                            field_name=col,
                            row_index=idx,
                            value=data.loc[idx, col],
                            z_score=z_scores.loc[idx]
                        ))
        
        return issues
    
    def _calculate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate price-related statistics."""
        stats = {}
        
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                prices = data[col].dropna()
                if len(prices) > 0:
                    stats[f'{col}_mean'] = float(prices.mean())
                    stats[f'{col}_std'] = float(prices.std())
                    stats[f'{col}_min'] = float(prices.min())
                    stats[f'{col}_max'] = float(prices.max())
                    stats[f'{col}_null_count'] = int(data[col].isnull().sum())
        
        # Calculate price ranges
        if all(col in data.columns for col in ['high', 'low']):
            price_ranges = data['high'] - data['low']
            stats['price_range_mean'] = float(price_ranges.mean())
            stats['price_range_std'] = float(price_ranges.std())
        
        # Calculate price changes
        if 'close' in data.columns and len(data) > 1:
            price_changes = data['close'].pct_change().dropna()
            if len(price_changes) > 0:
                stats['price_change_mean'] = float(price_changes.mean())
                stats['price_change_std'] = float(price_changes.std())
                stats['max_price_change'] = float(price_changes.abs().max())
        
        return stats
