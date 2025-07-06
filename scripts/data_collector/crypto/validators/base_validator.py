# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Base validator classes for cryptocurrency data validation.

This module defines the base classes and data structures used by all
data validators in the crypto data collection system.
"""

import abc

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    row_index: Optional[int] = None
    value: Optional[Any] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a single validator's execution."""
    validator_name: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return len([i for i in self.issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]])
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len([i for i in self.issues if i.severity == ValidationSeverity.WARNING])
    
    @property
    def has_errors(self) -> bool:
        """Whether this result contains any errors."""
        return self.error_count > 0
    
    @property
    def has_warnings(self) -> bool:
        """Whether this result contains any warnings."""
        return self.warning_count > 0


@dataclass
class ValidationReport:
    """Complete validation report for a dataset."""
    symbol: str
    timeframe: str
    validation_time: datetime
    data_rows: int
    results: List[ValidationResult] = field(default_factory=list)
    
    @property
    def overall_status(self) -> str:
        """Overall validation status."""
        if any(r.has_errors for r in self.results):
            return "FAIL"
        elif any(r.has_warnings for r in self.results):
            return "WARNING"
        else:
            return "PASS"
    
    @property
    def total_errors(self) -> int:
        """Total number of errors across all validators."""
        return sum(r.error_count for r in self.results)
    
    @property
    def total_warnings(self) -> int:
        """Total number of warnings across all validators."""
        return sum(r.warning_count for r in self.results)
    
    @property
    def summary(self) -> Dict[str, Any]:
        """Summary statistics for the validation report."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "validation_time": self.validation_time.isoformat(),
            "data_rows": self.data_rows,
            "overall_status": self.overall_status,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "validators_run": len(self.results),
            "validators_passed": len([r for r in self.results if not r.has_errors]),
            "execution_time_ms": sum(r.execution_time_ms for r in self.results),
        }


class BaseValidator(abc.ABC):
    """
    Base class for all data validators.
    
    All validators should inherit from this class and implement the validate method.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize the validator.
        
        Parameters
        ----------
        name : str, optional
            Name of the validator. If not provided, uses the class name.
        """
        self.name = name or self.__class__.__name__
    
    @abc.abstractmethod
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate the provided data.
        
        Parameters
        ----------
        data : pd.DataFrame
            The data to validate. Expected to have columns like 'open', 'high', 
            'low', 'close', 'volume', and potentially crypto-specific fields.
        
        Returns
        -------
        ValidationResult
            The result of the validation, including any issues found.
        """
        pass
    
    def _create_issue(
        self,
        severity: ValidationSeverity,
        message: str,
        field_name: Optional[str] = None,
        row_index: Optional[int] = None,
        value: Optional[Any] = None,
        **details
    ) -> ValidationIssue:
        """
        Helper method to create a validation issue.
        
        Parameters
        ----------
        severity : ValidationSeverity
            Severity level of the issue
        message : str
            Description of the issue
        field : str, optional
            Field name where the issue was found
        row_index : int, optional
            Row index where the issue was found
        value : Any, optional
            The problematic value
        **details
            Additional details about the issue
        
        Returns
        -------
        ValidationIssue
            The created validation issue
        """
        return ValidationIssue(
            severity=severity,
            message=message,
            field_name=field_name,
            row_index=row_index,
            value=value,
            details=details
        )
    
    def _check_required_columns(self, data: pd.DataFrame, required_columns: List[str]) -> List[ValidationIssue]:
        """
        Check if required columns are present in the data.
        
        Parameters
        ----------
        data : pd.DataFrame
            The data to check
        required_columns : List[str]
            List of required column names
        
        Returns
        -------
        List[ValidationIssue]
            List of issues for missing columns
        """
        issues = []
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        for col in missing_columns:
            issues.append(self._create_issue(
                ValidationSeverity.CRITICAL,
                f"Required column '{col}' is missing",
                field_name=col
            ))
        
        return issues
    
    def _check_data_types(self, data: pd.DataFrame, expected_types: Dict[str, type]) -> List[ValidationIssue]:
        """
        Check if columns have expected data types.
        
        Parameters
        ----------
        data : pd.DataFrame
            The data to check
        expected_types : Dict[str, type]
            Dictionary mapping column names to expected types
        
        Returns
        -------
        List[ValidationIssue]
            List of issues for incorrect data types
        """
        issues = []
        
        for col, expected_type in expected_types.items():
            if col in data.columns:
                if not pd.api.types.is_numeric_dtype(data[col]) and expected_type in [int, float]:
                    issues.append(self._create_issue(
                        ValidationSeverity.ERROR,
                        f"Column '{col}' should be numeric but has type {data[col].dtype}",
                        field_name=col
                    ))
        
        return issues
