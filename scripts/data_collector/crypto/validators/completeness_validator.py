# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Completeness validator for cryptocurrency data validation.

This module provides validation for data completeness, including
missing value detection, required field validation, and data coverage analysis.
"""

import time

from typing import Dict, List, Any, Optional, Set
import pandas as pd

from validators.base_validator import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity


class CompletenessValidator(BaseValidator):
    """
    Validator for data completeness.
    
    Validates:
    - Required fields presence
    - Missing value detection
    - Data coverage analysis
    - Row count validation
    """
    
    def __init__(
        self, 
        required_fields: Optional[List[str]] = None,
        optional_fields: Optional[List[str]] = None,
        max_missing_ratio: float = 0.1,
        min_rows: int = 1,
        name: Optional[str] = None
    ):
        """
        Initialize the completeness validator.
        
        Parameters
        ----------
        required_fields : List[str], optional
            List of required field names. Defaults to basic OHLCV fields.
        optional_fields : List[str], optional
            List of optional field names that should be checked if present.
        max_missing_ratio : float, default 0.1
            Maximum allowed ratio of missing values per field (10%)
        min_rows : int, default 1
            Minimum number of rows required
        name : str, optional
            Name of the validator
        """
        super().__init__(name)
        self.required_fields = required_fields or ['open', 'high', 'low', 'close', 'volume']
        self.optional_fields = optional_fields or [
            'volume_24h', 'volume_usd_24h', 'change_24h', 'funding_rate', 
            'open_interest', 'bid_ask_spread', 'liquidation_data'
        ]
        self.max_missing_ratio = max_missing_ratio
        self.min_rows = min_rows
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate data completeness.
        
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
        
        # Check minimum row count
        issues.extend(self._check_minimum_rows(data))
        
        # Check required fields
        issues.extend(self._check_required_fields(data))
        
        # Check missing values in required fields
        issues.extend(self._check_missing_values(data, self.required_fields, required=True))
        
        # Check missing values in optional fields (if present)
        present_optional_fields = [field for field in self.optional_fields if field in data.columns]
        issues.extend(self._check_missing_values(data, present_optional_fields, required=False))
        
        # Check data coverage
        issues.extend(self._check_data_coverage(data))
        
        # Check for completely empty rows
        issues.extend(self._check_empty_rows(data))
        
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
    
    def _check_minimum_rows(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Check if data meets minimum row requirements."""
        issues = []
        
        if len(data) < self.min_rows:
            issues.append(self._create_issue(
                ValidationSeverity.ERROR,
                f"Insufficient data: {len(data)} rows (minimum required: {self.min_rows})",
                details={'actual_rows': len(data), 'required_rows': self.min_rows}
            ))
        
        return issues
    
    def _check_required_fields(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Check if all required fields are present."""
        issues = []
        
        missing_fields = [field for field in self.required_fields if field not in data.columns]
        
        for field in missing_fields:
            issues.append(self._create_issue(
                ValidationSeverity.CRITICAL,
                f"Required field '{field}' is missing",
                field_name=field
            ))
        
        return issues
    
    def _check_missing_values(self, data: pd.DataFrame, fields: List[str], required: bool = True) -> List[ValidationIssue]:
        """Check for missing values in specified fields."""
        issues = []
        
        for field in fields:
            if field in data.columns:
                missing_count = data[field].isnull().sum()
                missing_ratio = missing_count / len(data) if len(data) > 0 else 0
                
                if missing_count > 0:
                    if required and missing_ratio > self.max_missing_ratio:
                        issues.append(self._create_issue(
                            ValidationSeverity.ERROR,
                            f"Required field '{field}' has too many missing values: "
                            f"{missing_count}/{len(data)} ({missing_ratio:.2%})",
                            field_name=field,
                            missing_count=missing_count,
                            total_count=len(data),
                            missing_ratio=missing_ratio
                        ))
                    elif not required and missing_ratio > self.max_missing_ratio:
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"Optional field '{field}' has many missing values: "
                            f"{missing_count}/{len(data)} ({missing_ratio:.2%})",
                            field_name=field,
                            missing_count=missing_count,
                            total_count=len(data),
                            missing_ratio=missing_ratio
                        ))
                    elif missing_count > 0:
                        issues.append(self._create_issue(
                            ValidationSeverity.INFO,
                            f"Field '{field}' has {missing_count} missing values ({missing_ratio:.2%})",
                            field_name=field,
                            missing_count=missing_count,
                            total_count=len(data),
                            missing_ratio=missing_ratio
                        ))
        
        return issues
    
    def _check_data_coverage(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Check overall data coverage."""
        issues = []
        
        total_cells = len(data) * len(data.columns)
        missing_cells = data.isnull().sum().sum()
        coverage_ratio = 1 - (missing_cells / total_cells) if total_cells > 0 else 0
        
        if coverage_ratio < (1 - self.max_missing_ratio):
            issues.append(self._create_issue(
                ValidationSeverity.WARNING,
                f"Low overall data coverage: {coverage_ratio:.2%} "
                f"(threshold: {1 - self.max_missing_ratio:.2%})",
                details={
                    'coverage_ratio': coverage_ratio,
                    'missing_cells': missing_cells,
                    'total_cells': total_cells
                }
            ))
        
        return issues
    
    def _check_empty_rows(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Check for completely empty rows."""
        issues = []
        
        # Find rows where all values are null
        empty_rows = data.isnull().all(axis=1)
        empty_row_count = empty_rows.sum()
        
        if empty_row_count > 0:
            empty_indices = data[empty_rows].index.tolist()
            issues.append(self._create_issue(
                ValidationSeverity.WARNING,
                f"Found {empty_row_count} completely empty rows",
                details={
                    'empty_row_count': empty_row_count,
                    'empty_row_indices': empty_indices[:10]  # Show first 10 indices
                }
            ))
        
        return issues
    
    def _calculate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate completeness-related statistics."""
        stats = {
            'total_rows': len(data),
            'total_columns': len(data.columns),
            'total_cells': len(data) * len(data.columns)
        }
        
        # Calculate missing value statistics
        missing_by_column = data.isnull().sum()
        stats['total_missing_cells'] = int(missing_by_column.sum())
        stats['overall_coverage'] = float(1 - (stats['total_missing_cells'] / stats['total_cells']) 
                                         if stats['total_cells'] > 0 else 0)
        
        # Field presence statistics
        stats['required_fields_present'] = len([f for f in self.required_fields if f in data.columns])
        stats['required_fields_total'] = len(self.required_fields)
        stats['optional_fields_present'] = len([f for f in self.optional_fields if f in data.columns])
        stats['optional_fields_total'] = len(self.optional_fields)
        
        # Missing value statistics by field type
        required_missing = sum(data[field].isnull().sum() for field in self.required_fields if field in data.columns)
        optional_missing = sum(data[field].isnull().sum() for field in self.optional_fields if field in data.columns)
        
        stats['required_fields_missing'] = int(required_missing)
        stats['optional_fields_missing'] = int(optional_missing)
        
        # Coverage by field
        field_coverage = {}
        for field in data.columns:
            missing_count = data[field].isnull().sum()
            coverage = 1 - (missing_count / len(data)) if len(data) > 0 else 0
            field_coverage[f'{field}_coverage'] = float(coverage)
            field_coverage[f'{field}_missing_count'] = int(missing_count)
        
        stats.update(field_coverage)
        
        # Empty row statistics
        empty_rows = data.isnull().all(axis=1).sum()
        stats['empty_rows'] = int(empty_rows)
        stats['empty_rows_ratio'] = float(empty_rows / len(data)) if len(data) > 0 else 0
        
        return stats
