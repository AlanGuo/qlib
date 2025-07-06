# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Value at Risk (VaR) calculator for cryptocurrency risk metrics.

This module provides comprehensive VaR calculation capabilities including
historical simulation, parametric, and Monte Carlo methods.
"""

from typing import List, Union, Optional, Dict, Any
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats

from base_calculator import BaseRiskCalculator, RiskResult
from config.risk_config import RiskConfig


class VaRCalculator(BaseRiskCalculator):
    """
    Calculator for Value at Risk (VaR) metrics.
    
    Supports:
    - Historical simulation VaR
    - Parametric VaR (normal distribution)
    - Monte Carlo simulation VaR
    - Conditional VaR (Expected Shortfall)
    - Component VaR
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize VaR calculator.
        
        Parameters
        ----------
        config : RiskConfig, optional
            Configuration for VaR calculation
        """
        super().__init__("VaRCalculator")
        self.config = config or RiskConfig()
    
    def calculate(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        confidence_levels: Optional[List[float]] = None,
        methods: Optional[List[str]] = None,
        **kwargs
    ) -> List[RiskResult]:
        """
        Calculate VaR metrics.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes for calculation
        confidence_levels : List[float], optional
            Confidence levels (e.g., [0.01, 0.05])
        methods : List[str], optional
            VaR calculation methods
        **kwargs
            Additional parameters
        
        Returns
        -------
        List[RiskResult]
            List of VaR calculation results
        """
        self._validate_data(data)
        
        if windows is None:
            windows = self.config.var_windows
        
        if confidence_levels is None:
            confidence_levels = self.config.var_confidence_levels
        
        if methods is None:
            methods = self.config.var_methods
        
        prices = data[self.config.price_column]
        returns = self._calculate_returns(prices, self.config.return_method)
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            for confidence_level in confidence_levels:
                for method in methods:
                    cache_key = self._cache_key(
                        symbol, timeframe, 
                        window=window, 
                        confidence_level=confidence_level,
                        method=method
                    )
                    
                    # Check cache
                    cached_result = self._get_from_cache(cache_key)
                    if cached_result is not None:
                        results.append(cached_result)
                        continue
                    
                    # Calculate VaR
                    if method == "historical":
                        var_series = self._calculate_historical_var(
                            returns, window, confidence_level
                        )
                    elif method == "parametric":
                        var_series = self._calculate_parametric_var(
                            returns, window, confidence_level
                        )
                    elif method == "monte_carlo":
                        var_series = self._calculate_monte_carlo_var(
                            returns, window, confidence_level
                        )
                    else:
                        raise ValueError(f"Unknown VaR method: {method}")
                    
                    # Create result
                    confidence_pct = int(confidence_level * 100)
                    result = RiskResult(
                        metric_name=f"var_{method}_{confidence_pct}pct_{window}d",
                        value=var_series,
                        timestamp=timestamp,
                        symbol=symbol,
                        timeframe=timeframe,
                        window=window,
                        parameters={
                            'method': method,
                            'confidence_level': confidence_level,
                            'confidence_pct': confidence_pct
                        },
                        metadata={
                            'data_points': len(data),
                            'valid_points': var_series.count() if isinstance(var_series, pd.Series) else 1
                        }
                    )
                    
                    # Cache and store result
                    self._store_in_cache(cache_key, result)
                    results.append(result)
        
        return results
    
    def _calculate_historical_var(
        self, 
        returns: pd.Series, 
        window: int, 
        confidence_level: float
    ) -> pd.Series:
        """
        Calculate historical simulation VaR.
        
        Parameters
        ----------
        returns : pd.Series
            Return series
        window : int
            Rolling window size
        confidence_level : float
            Confidence level (e.g., 0.05 for 95% VaR)
        
        Returns
        -------
        pd.Series
            Historical VaR series
        """
        min_periods = self.config.get_min_periods(window, 'var')
        
        def historical_var(return_window):
            if len(return_window) < min_periods:
                return np.nan
            return np.percentile(return_window, confidence_level * 100)
        
        return returns.rolling(
            window=window, 
            min_periods=min_periods
        ).apply(historical_var, raw=True)
    
    def _calculate_parametric_var(
        self, 
        returns: pd.Series, 
        window: int, 
        confidence_level: float
    ) -> pd.Series:
        """
        Calculate parametric VaR assuming normal distribution.
        
        Parameters
        ----------
        returns : pd.Series
            Return series
        window : int
            Rolling window size
        confidence_level : float
            Confidence level
        
        Returns
        -------
        pd.Series
            Parametric VaR series
        """
        min_periods = self.config.get_min_periods(window, 'var')
        
        # Rolling mean and standard deviation
        rolling_mean = returns.rolling(
            window=window, 
            min_periods=min_periods
        ).mean()
        
        rolling_std = returns.rolling(
            window=window, 
            min_periods=min_periods
        ).std()
        
        # Z-score for confidence level
        z_score = stats.norm.ppf(confidence_level)
        
        # Parametric VaR
        var_series = rolling_mean + z_score * rolling_std
        
        return var_series
    
    def _calculate_monte_carlo_var(
        self, 
        returns: pd.Series, 
        window: int, 
        confidence_level: float
    ) -> pd.Series:
        """
        Calculate Monte Carlo simulation VaR.
        
        Parameters
        ----------
        returns : pd.Series
            Return series
        window : int
            Rolling window size
        confidence_level : float
            Confidence level
        
        Returns
        -------
        pd.Series
            Monte Carlo VaR series
        """
        min_periods = self.config.get_min_periods(window, 'var')
        n_simulations = self.config.var_monte_carlo_simulations
        
        def monte_carlo_var(return_window):
            if len(return_window) < min_periods:
                return np.nan
            
            # Estimate parameters
            mean = np.mean(return_window)
            std = np.std(return_window, ddof=1)
            
            # Generate random scenarios
            np.random.seed(42)  # For reproducibility
            simulated_returns = np.random.normal(mean, std, n_simulations)
            
            # Calculate VaR
            return np.percentile(simulated_returns, confidence_level * 100)
        
        return returns.rolling(
            window=window, 
            min_periods=min_periods
        ).apply(monte_carlo_var, raw=True)
    
    def calculate_conditional_var(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        confidence_levels: Optional[List[float]] = None,
        method: str = "historical"
    ) -> List[RiskResult]:
        """
        Calculate Conditional VaR (Expected Shortfall).
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes for calculation
        confidence_levels : List[float], optional
            Confidence levels
        method : str, default "historical"
            Calculation method
        
        Returns
        -------
        List[RiskResult]
            Conditional VaR results
        """
        if windows is None:
            windows = self.config.var_windows
        
        if confidence_levels is None:
            confidence_levels = self.config.var_confidence_levels
        
        prices = data[self.config.price_column]
        returns = self._calculate_returns(prices, self.config.return_method)
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            for confidence_level in confidence_levels:
                if method == "historical":
                    cvar_series = self._calculate_historical_cvar(
                        returns, window, confidence_level
                    )
                elif method == "parametric":
                    cvar_series = self._calculate_parametric_cvar(
                        returns, window, confidence_level
                    )
                else:
                    raise ValueError(f"Unknown CVaR method: {method}")
                
                confidence_pct = int(confidence_level * 100)
                result = RiskResult(
                    metric_name=f"cvar_{method}_{confidence_pct}pct_{window}d",
                    value=cvar_series,
                    timestamp=timestamp,
                    symbol=symbol,
                    timeframe=timeframe,
                    window=window,
                    parameters={
                        'method': method,
                        'confidence_level': confidence_level
                    },
                    metadata={
                        'data_points': len(data),
                        'valid_points': cvar_series.count()
                    }
                )
                
                results.append(result)
        
        return results
    
    def _calculate_historical_cvar(
        self, 
        returns: pd.Series, 
        window: int, 
        confidence_level: float
    ) -> pd.Series:
        """
        Calculate historical Conditional VaR.
        
        Parameters
        ----------
        returns : pd.Series
            Return series
        window : int
            Rolling window size
        confidence_level : float
            Confidence level
        
        Returns
        -------
        pd.Series
            Historical CVaR series
        """
        min_periods = self.config.get_min_periods(window, 'var')
        
        def historical_cvar(return_window):
            if len(return_window) < min_periods:
                return np.nan
            
            # Find VaR threshold
            var_threshold = np.percentile(return_window, confidence_level * 100)
            
            # Calculate expected value of returns below VaR
            tail_returns = return_window[return_window <= var_threshold]
            
            if len(tail_returns) == 0:
                return var_threshold
            
            return np.mean(tail_returns)
        
        return returns.rolling(
            window=window, 
            min_periods=min_periods
        ).apply(historical_cvar, raw=True)
    
    def _calculate_parametric_cvar(
        self, 
        returns: pd.Series, 
        window: int, 
        confidence_level: float
    ) -> pd.Series:
        """
        Calculate parametric Conditional VaR.
        
        Parameters
        ----------
        returns : pd.Series
            Return series
        window : int
            Rolling window size
        confidence_level : float
            Confidence level
        
        Returns
        -------
        pd.Series
            Parametric CVaR series
        """
        min_periods = self.config.get_min_periods(window, 'var')
        
        # Rolling mean and standard deviation
        rolling_mean = returns.rolling(
            window=window, 
            min_periods=min_periods
        ).mean()
        
        rolling_std = returns.rolling(
            window=window, 
            min_periods=min_periods
        ).std()
        
        # Calculate CVaR using normal distribution
        z_alpha = stats.norm.ppf(confidence_level)
        phi_z_alpha = stats.norm.pdf(z_alpha)
        
        cvar_series = rolling_mean - rolling_std * phi_z_alpha / confidence_level
        
        return cvar_series
    
    def calculate_var_backtesting(
        self, 
        data: pd.DataFrame, 
        var_series: pd.Series,
        symbol: str, 
        timeframe: str,
        confidence_level: float
    ) -> RiskResult:
        """
        Perform VaR backtesting.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        var_series : pd.Series
            VaR estimates
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        confidence_level : float
            Confidence level used for VaR
        
        Returns
        -------
        RiskResult
            VaR backtesting results
        """
        prices = data[self.config.price_column]
        returns = self._calculate_returns(prices, self.config.return_method)
        
        # Align data
        aligned_data = pd.concat([returns, var_series], axis=1).dropna()
        actual_returns = aligned_data.iloc[:, 0]
        var_estimates = aligned_data.iloc[:, 1]
        
        # Count violations (actual return < VaR)
        violations = actual_returns < var_estimates
        violation_count = violations.sum()
        total_observations = len(violations)
        
        # Expected violation rate
        expected_violations = confidence_level * total_observations
        actual_violation_rate = violation_count / total_observations
        
        # Kupiec test (likelihood ratio test)
        if violation_count > 0 and violation_count < total_observations:
            lr_stat = 2 * (
                violation_count * np.log(actual_violation_rate / confidence_level) +
                (total_observations - violation_count) * 
                np.log((1 - actual_violation_rate) / (1 - confidence_level))
            )
            p_value = 1 - stats.chi2.cdf(lr_stat, df=1)
        else:
            lr_stat = np.inf
            p_value = 0.0
        
        backtesting_results = {
            'violation_count': violation_count,
            'total_observations': total_observations,
            'expected_violations': expected_violations,
            'actual_violation_rate': actual_violation_rate,
            'expected_violation_rate': confidence_level,
            'kupiec_lr_statistic': lr_stat,
            'kupiec_p_value': p_value,
            'test_passed': p_value > 0.05,  # 5% significance level
            'violation_dates': violations[violations].index.tolist()
        }
        
        return RiskResult(
            metric_name="var_backtesting",
            value=backtesting_results,
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            parameters={'confidence_level': confidence_level},
            metadata={
                'data_points': total_observations,
                'test_period': f"{aligned_data.index[0]} to {aligned_data.index[-1]}"
            }
        )
