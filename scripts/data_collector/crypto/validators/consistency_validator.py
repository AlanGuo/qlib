# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Consistency validator for cryptocurrency data validation.

This module provides validation for data consistency across fields,
including cross-field relationships and crypto-specific validations.
"""

import time

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from validators.base_validator import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity


class ConsistencyValidator(BaseValidator):
    """
    Validator for data consistency across fields.
    
    Validates:
    - Cross-field relationships
    - Crypto-specific field consistency
    - Logical constraints
    - Data type consistency
    """
    
    def __init__(
        self, 
        tolerance: float = 0.01,
        funding_rate_range: tuple = (-0.01, 0.01),  # -1% to 1%
        change_24h_range: tuple = (-100.0, 1000.0),  # -100% to 1000%
        name: Optional[str] = None
    ):
        """
        Initialize the consistency validator.
        
        Parameters
        ----------
        tolerance : float, default 0.01
            Tolerance for numerical comparisons (1%)
        funding_rate_range : tuple, default (-0.01, 0.01)
            Valid range for funding rates
        change_24h_range : tuple, default (-100.0, 1000.0)
            Valid range for 24h price changes (in percentage)
        name : str, optional
            Name of the validator
        """
        super().__init__(name)
        self.tolerance = tolerance
        self.funding_rate_range = funding_rate_range
        self.change_24h_range = change_24h_range
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate data consistency.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame to validate
        
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
            return ValidationResult(
                validator_name=self.name,
                is_valid=True,
                issues=[],
                statistics={'row_count': 0},
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Validate OHLC consistency (already covered in PriceValidator, but double-check)
        issues.extend(self._validate_ohlc_consistency(data))
        
        # Validate volume consistency
        issues.extend(self._validate_volume_consistency(data))
        
        # Validate crypto-specific fields
        issues.extend(self._validate_crypto_fields(data))
        
        # Validate cross-field relationships
        issues.extend(self._validate_cross_field_relationships(data))
        
        # Validate data type consistency
        issues.extend(self._validate_data_types(data))
        
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
    
    def _validate_ohlc_consistency(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate OHLC price consistency."""
        issues = []
        
        ohlc_columns = ['open', 'high', 'low', 'close']
        if not all(col in data.columns for col in ohlc_columns):
            return issues
        
        # Check for NaN values in OHLC that would break consistency
        for idx in data.index:
            ohlc_values = data.loc[idx, ohlc_columns]
            if ohlc_values.isnull().any():
                null_fields = ohlc_values[ohlc_values.isnull()].index.tolist()
                issues.append(self._create_issue(
                    ValidationSeverity.WARNING,
                    f"Incomplete OHLC data at index {idx}: missing {null_fields}",
                    row_index=idx,
                    missing_fields=null_fields
                ))
        
        return issues
    
    def _validate_volume_consistency(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate volume field consistency."""
        issues = []
        
        # Check volume vs volume_usd_24h consistency
        if all(col in data.columns for col in ['volume', 'volume_usd_24h', 'close']):
            for idx in data.index:
                volume = data.loc[idx, 'volume']
                volume_usd = data.loc[idx, 'volume_usd_24h']
                price = data.loc[idx, 'close']
                
                if pd.notna(volume) and pd.notna(volume_usd) and pd.notna(price) and price > 0:
                    expected_volume_usd = volume * price
                    relative_diff = abs(expected_volume_usd - volume_usd) / expected_volume_usd
                    
                    if relative_diff > self.tolerance:
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"Volume USD inconsistency at index {idx}: "
                            f"expected {expected_volume_usd:.2f}, actual {volume_usd:.2f} "
                            f"(difference: {relative_diff:.2%})",
                            field='volume_usd_24h',
                            row_index=idx,
                            expected=expected_volume_usd,
                            actual=volume_usd,
                            relative_diff=relative_diff
                        ))
        
        # Check volume_24h vs volume consistency (if both present)
        if all(col in data.columns for col in ['volume', 'volume_24h']):
            for idx in data.index:
                volume = data.loc[idx, 'volume']
                volume_24h = data.loc[idx, 'volume_24h']
                
                if pd.notna(volume) and pd.notna(volume_24h):
                    # volume_24h should generally be >= volume for the period
                    if volume_24h < volume * 0.5:  # Allow some tolerance
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"24h volume ({volume_24h}) is much smaller than period volume ({volume}) at index {idx}",
                            field='volume_24h',
                            row_index=idx,
                            volume_24h=volume_24h,
                            period_volume=volume
                        ))
        
        return issues
    
    def _validate_crypto_fields(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate crypto-specific fields."""
        issues = []
        
        # Validate funding rate
        if 'funding_rate' in data.columns:
            funding_rates = data['funding_rate'].dropna()
            out_of_range = funding_rates[
                (funding_rates < self.funding_rate_range[0]) | 
                (funding_rates > self.funding_rate_range[1])
            ]
            
            for idx in out_of_range.index:
                issues.append(self._create_issue(
                    ValidationSeverity.WARNING,
                    f"Funding rate ({data.loc[idx, 'funding_rate']:.4f}) outside normal range "
                    f"{self.funding_rate_range} at index {idx}",
                    field='funding_rate',
                    row_index=idx,
                    value=data.loc[idx, 'funding_rate']
                ))
        
        # Validate 24h change
        if 'change_24h' in data.columns:
            changes = data['change_24h'].dropna()
            out_of_range = changes[
                (changes < self.change_24h_range[0]) | 
                (changes > self.change_24h_range[1])
            ]
            
            for idx in out_of_range.index:
                issues.append(self._create_issue(
                    ValidationSeverity.WARNING,
                    f"24h change ({data.loc[idx, 'change_24h']:.2f}%) outside normal range "
                    f"{self.change_24h_range} at index {idx}",
                    field='change_24h',
                    row_index=idx,
                    value=data.loc[idx, 'change_24h']
                ))
        
        # Validate open interest (should be non-negative)
        if 'open_interest' in data.columns:
            negative_oi = data[data['open_interest'] < 0]
            for idx in negative_oi.index:
                if pd.notna(data.loc[idx, 'open_interest']):
                    issues.append(self._create_issue(
                        ValidationSeverity.ERROR,
                        f"Negative open interest ({data.loc[idx, 'open_interest']}) at index {idx}",
                        field='open_interest',
                        row_index=idx,
                        value=data.loc[idx, 'open_interest']
                    ))
        
        # Validate bid-ask spread (should be non-negative)
        if 'bid_ask_spread' in data.columns:
            negative_spread = data[data['bid_ask_spread'] < 0]
            for idx in negative_spread.index:
                if pd.notna(data.loc[idx, 'bid_ask_spread']):
                    issues.append(self._create_issue(
                        ValidationSeverity.ERROR,
                        f"Negative bid-ask spread ({data.loc[idx, 'bid_ask_spread']}) at index {idx}",
                        field='bid_ask_spread',
                        row_index=idx,
                        value=data.loc[idx, 'bid_ask_spread']
                    ))
        
        return issues
    
    def _validate_cross_field_relationships(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate relationships between different fields."""
        issues = []
        
        # Validate change_24h vs price data
        if all(col in data.columns for col in ['change_24h', 'open', 'close']):
            for idx in data.index:
                change_24h = data.loc[idx, 'change_24h']
                open_price = data.loc[idx, 'open']
                close_price = data.loc[idx, 'close']
                
                if pd.notna(change_24h) and pd.notna(open_price) and pd.notna(close_price) and open_price > 0:
                    # Calculate expected change based on open/close
                    expected_change = ((close_price - open_price) / open_price) * 100
                    diff = abs(expected_change - change_24h)
                    
                    # Allow for some tolerance as change_24h might be calculated differently
                    if diff > 10.0:  # 10% tolerance
                        issues.append(self._create_issue(
                            ValidationSeverity.INFO,
                            f"24h change ({change_24h:.2f}%) doesn't match open/close calculation "
                            f"({expected_change:.2f}%) at index {idx}",
                            field='change_24h',
                            row_index=idx,
                            reported_change=change_24h,
                            calculated_change=expected_change,
                            difference=diff
                        ))
        
        return issues
    
    def _validate_data_types(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Validate data type consistency."""
        issues = []
        
        # Expected numeric fields
        numeric_fields = [
            'open', 'high', 'low', 'close', 'volume', 'volume_24h', 'volume_usd_24h',
            'change_24h', 'funding_rate', 'open_interest', 'bid_ask_spread'
        ]
        
        for field in numeric_fields:
            if field in data.columns:
                # Check if field is numeric
                if not pd.api.types.is_numeric_dtype(data[field]):
                    issues.append(self._create_issue(
                        ValidationSeverity.ERROR,
                        f"Field '{field}' should be numeric but has type {data[field].dtype}",
                        field=field,
                        actual_dtype=str(data[field].dtype)
                    ))
                
                # Check for infinite values
                if pd.api.types.is_numeric_dtype(data[field]):
                    inf_count = np.isinf(data[field]).sum()
                    if inf_count > 0:
                        issues.append(self._create_issue(
                            ValidationSeverity.ERROR,
                            f"Field '{field}' contains {inf_count} infinite values",
                            field=field,
                            infinite_count=inf_count
                        ))
        
        return issues
    
    def _calculate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate consistency-related statistics."""
        stats = {
            'total_rows': len(data),
            'total_columns': len(data.columns)
        }
        
        # Count fields by type
        numeric_fields = []
        non_numeric_fields = []
        
        for col in data.columns:
            if pd.api.types.is_numeric_dtype(data[col]):
                numeric_fields.append(col)
            else:
                non_numeric_fields.append(col)
        
        stats['numeric_fields_count'] = len(numeric_fields)
        stats['non_numeric_fields_count'] = len(non_numeric_fields)
        
        # Check for infinite values
        infinite_counts = {}
        for col in numeric_fields:
            inf_count = np.isinf(data[col]).sum()
            if inf_count > 0:
                infinite_counts[f'{col}_infinite_count'] = int(inf_count)
        
        stats.update(infinite_counts)
        
        # Crypto-specific field statistics
        crypto_fields = ['funding_rate', 'open_interest', 'change_24h', 'bid_ask_spread']
        present_crypto_fields = [field for field in crypto_fields if field in data.columns]
        stats['crypto_fields_present'] = len(present_crypto_fields)
        stats['crypto_fields_available'] = present_crypto_fields
        
        return stats
