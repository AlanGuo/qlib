# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Base classes for risk metrics calculation.

This module provides the foundation for all risk metrics calculators,
including common interfaces, data structures, and utility functions.
"""

from abc import ABC, abstractmethod
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class RiskResult:
    """
    Container for risk metrics calculation results.
    
    Attributes
    ----------
    metric_name : str
        Name of the risk metric
    value : Union[float, pd.Series, pd.DataFrame]
        Calculated risk metric value(s)
    timestamp : datetime
        Calculation timestamp
    symbol : str
        Symbol for which the metric was calculated
    timeframe : str
        Data timeframe used for calculation
    window : Optional[int]
        Window size used for calculation
    parameters : Dict[str, Any]
        Parameters used in calculation
    metadata : Dict[str, Any]
        Additional metadata about the calculation
    """
    metric_name: str
    value: Union[float, pd.Series, pd.DataFrame]
    timestamp: datetime
    symbol: str
    timeframe: str
    window: Optional[int] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            'metric_name': self.metric_name,
            'value': self.value,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'window': self.window,
            'parameters': self.parameters,
            'metadata': self.metadata
        }
    
    def is_scalar(self) -> bool:
        """Check if the result is a scalar value."""
        return isinstance(self.value, (int, float, np.number))
    
    def is_series(self) -> bool:
        """Check if the result is a pandas Series."""
        return isinstance(self.value, pd.Series)
    
    def is_dataframe(self) -> bool:
        """Check if the result is a pandas DataFrame."""
        return isinstance(self.value, pd.DataFrame)


class BaseRiskCalculator(ABC):
    """
    Abstract base class for all risk metrics calculators.
    
    This class defines the common interface and provides utility methods
    for risk metrics calculation.
    """
    
    def __init__(self, name: str):
        """
        Initialize the risk calculator.
        
        Parameters
        ----------
        name : str
            Name of the risk calculator
        """
        self.name = name
        self._cache = {}
        self._cache_size_limit = 1000
    
    @abstractmethod
    def calculate(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        **kwargs
    ) -> Union[RiskResult, List[RiskResult]]:
        """
        Calculate the risk metric.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price/return data for calculation
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        **kwargs
            Additional parameters for calculation
        
        Returns
        -------
        Union[RiskResult, List[RiskResult]]
            Calculated risk metric result(s)
        """
        pass
    
    def _validate_data(self, data: pd.DataFrame) -> None:
        """
        Validate input data for calculation.
        
        Parameters
        ----------
        data : pd.DataFrame
            Input data to validate
        
        Raises
        ------
        ValueError
            If data is invalid for calculation
        """
        if data.empty:
            raise ValueError("Input data is empty")
        
        required_columns = self._get_required_columns()
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
    
    def _get_required_columns(self) -> List[str]:
        """
        Get list of required columns for calculation.
        
        Returns
        -------
        List[str]
            List of required column names
        """
        return ['close']  # Default requirement
    
    def _calculate_returns(
        self, 
        prices: pd.Series, 
        method: str = 'log'
    ) -> pd.Series:
        """
        Calculate returns from price series.
        
        Parameters
        ----------
        prices : pd.Series
            Price series
        method : str, default 'log'
            Return calculation method ('log' or 'simple')
        
        Returns
        -------
        pd.Series
            Calculated returns
        """
        if method == 'log':
            return np.log(prices / prices.shift(1)).dropna()
        elif method == 'simple':
            return (prices / prices.shift(1) - 1).dropna()
        else:
            raise ValueError(f"Unknown return calculation method: {method}")
    
    def _annualize_metric(
        self, 
        metric: Union[float, pd.Series], 
        periods_per_year: int = 365,
        metric_type: str = 'volatility'
    ) -> Union[float, pd.Series]:
        """
        Annualize a risk metric.
        
        Parameters
        ----------
        metric : Union[float, pd.Series]
            Metric to annualize
        periods_per_year : int, default 365
            Number of periods per year (365 for crypto, 252 for traditional markets)
        metric_type : str, default 'volatility'
            Type of metric ('volatility', 'return', 'sharpe')
        
        Returns
        -------
        Union[float, pd.Series]
            Annualized metric
        """
        if metric_type == 'volatility':
            return metric * np.sqrt(periods_per_year)
        elif metric_type == 'return':
            return metric * periods_per_year
        elif metric_type == 'sharpe':
            return metric * np.sqrt(periods_per_year)
        else:
            raise ValueError(f"Unknown metric type for annualization: {metric_type}")
    
    def _cache_key(self, symbol: str, timeframe: str, **kwargs) -> str:
        """
        Generate cache key for results.
        
        Parameters
        ----------
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        **kwargs
            Additional parameters
        
        Returns
        -------
        str
            Cache key
        """
        key_parts = [self.name, symbol, timeframe]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return "|".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[RiskResult]:
        """Get result from cache."""
        return self._cache.get(cache_key)
    
    def _store_in_cache(self, cache_key: str, result: RiskResult) -> None:
        """Store result in cache."""
        if len(self._cache) >= self._cache_size_limit:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[cache_key] = result
    
    def clear_cache(self) -> None:
        """Clear the calculation cache."""
        self._cache.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        return {
            'size': len(self._cache),
            'limit': self._cache_size_limit,
            'keys': list(self._cache.keys())
        }


class RiskMetricsUtility:
    """
    Utility class for common risk metrics calculations.
    """
    
    @staticmethod
    def rolling_window_apply(
        data: pd.Series, 
        window: int, 
        func: callable,
        min_periods: Optional[int] = None
    ) -> pd.Series:
        """
        Apply function to rolling window.
        
        Parameters
        ----------
        data : pd.Series
            Input data series
        window : int
            Window size
        func : callable
            Function to apply
        min_periods : Optional[int]
            Minimum periods required
        
        Returns
        -------
        pd.Series
            Result series
        """
        if min_periods is None:
            min_periods = max(1, window // 2)
        
        return data.rolling(window=window, min_periods=min_periods).apply(func, raw=True)
    
    @staticmethod
    def expanding_window_apply(
        data: pd.Series, 
        func: callable,
        min_periods: int = 1
    ) -> pd.Series:
        """
        Apply function to expanding window.
        
        Parameters
        ----------
        data : pd.Series
            Input data series
        func : callable
            Function to apply
        min_periods : int, default 1
            Minimum periods required
        
        Returns
        -------
        pd.Series
            Result series
        """
        return data.expanding(min_periods=min_periods).apply(func, raw=True)
    
    @staticmethod
    def safe_divide(numerator: Union[float, pd.Series], 
                   denominator: Union[float, pd.Series]) -> Union[float, pd.Series]:
        """
        Safely divide two values, handling division by zero.
        
        Parameters
        ----------
        numerator : Union[float, pd.Series]
            Numerator
        denominator : Union[float, pd.Series]
            Denominator
        
        Returns
        -------
        Union[float, pd.Series]
            Division result with NaN for division by zero
        """
        if isinstance(denominator, pd.Series):
            return numerator / denominator.replace(0, np.nan)
        else:
            return numerator / denominator if denominator != 0 else np.nan
