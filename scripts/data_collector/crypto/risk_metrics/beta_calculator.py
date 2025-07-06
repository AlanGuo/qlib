# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Beta calculator for cryptocurrency risk metrics.

This module provides comprehensive beta calculation capabilities including
traditional beta, rolling beta, and various beta estimation methods.
"""

from typing import List, Union, Optional, Dict, Any, Tuple
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression

from base_calculator import BaseRiskCalculator, RiskResult, RiskMetricsUtility
from config.risk_config import RiskConfig


class BetaCalculator(BaseRiskCalculator):
    """
    Calculator for beta metrics.
    
    Supports:
    - Traditional beta (CAPM)
    - Rolling beta
    - Downside beta
    - Upside beta
    - Bull/Bear beta
    - Time-varying beta
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize beta calculator.
        
        Parameters
        ----------
        config : RiskConfig, optional
            Configuration for beta calculation
        """
        super().__init__("BetaCalculator")
        self.config = config or RiskConfig()
    
    def calculate(
        self, 
        data: pd.DataFrame, 
        benchmark_data: pd.DataFrame,
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        **kwargs
    ) -> List[RiskResult]:
        """
        Calculate beta metrics.
        
        Parameters
        ----------
        data : pd.DataFrame
            Asset price data
        benchmark_data : pd.DataFrame
            Benchmark price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes for calculation
        **kwargs
            Additional parameters
        
        Returns
        -------
        List[RiskResult]
            List of beta calculation results
        """
        self._validate_data(data)
        self._validate_data(benchmark_data)
        
        if windows is None:
            windows = self.config.beta_windows
        
        # Calculate returns
        asset_returns = self._calculate_returns(
            data[self.config.price_column], 
            self.config.return_method
        )
        benchmark_returns = self._calculate_returns(
            benchmark_data[self.config.price_column], 
            self.config.return_method
        )
        
        # Align data
        aligned_data = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        if aligned_data.empty:
            raise ValueError("No overlapping data between asset and benchmark")
        
        asset_returns = aligned_data.iloc[:, 0]
        benchmark_returns = aligned_data.iloc[:, 1]
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            cache_key = self._cache_key(
                symbol, timeframe, 
                window=window, 
                benchmark=self.config.beta_benchmark_symbol
            )
            
            # Check cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                results.append(cached_result)
                continue
            
            # Calculate beta
            beta_series = self._calculate_rolling_beta(
                asset_returns, benchmark_returns, window
            )
            
            # Create result
            result = RiskResult(
                metric_name=f"beta_{window}d",
                value=beta_series,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={
                    'benchmark': self.config.beta_benchmark_symbol,
                    'method': 'ols_regression'
                },
                metadata={
                    'data_points': len(aligned_data),
                    'valid_points': beta_series.count() if isinstance(beta_series, pd.Series) else 1
                }
            )
            
            # Cache and store result
            self._store_in_cache(cache_key, result)
            results.append(result)
        
        return results
    
    def _calculate_rolling_beta(
        self, 
        asset_returns: pd.Series, 
        benchmark_returns: pd.Series, 
        window: int
    ) -> pd.Series:
        """
        Calculate rolling beta using OLS regression.
        
        Parameters
        ----------
        asset_returns : pd.Series
            Asset return series
        benchmark_returns : pd.Series
            Benchmark return series
        window : int
            Rolling window size
        
        Returns
        -------
        pd.Series
            Rolling beta series
        """
        min_periods = self.config.get_min_periods(window, 'beta')
        
        def rolling_beta(asset_window, benchmark_window):
            if len(asset_window) < min_periods or len(benchmark_window) < min_periods:
                return np.nan
            
            # Remove any NaN values
            valid_data = pd.DataFrame({
                'asset': asset_window,
                'benchmark': benchmark_window
            }).dropna()
            
            if len(valid_data) < min_periods:
                return np.nan
            
            # Calculate beta using covariance method
            covariance = np.cov(valid_data['asset'], valid_data['benchmark'])[0, 1]
            benchmark_variance = np.var(valid_data['benchmark'], ddof=1)
            
            if benchmark_variance == 0:
                return np.nan
            
            return covariance / benchmark_variance
        
        # Combine series for rolling calculation
        combined = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        
        return combined.rolling(
            window=window, 
            min_periods=min_periods
        ).apply(
            lambda x: rolling_beta(x.iloc[:, 0], x.iloc[:, 1]), 
            raw=False
        )
    
    def calculate_downside_beta(
        self, 
        data: pd.DataFrame, 
        benchmark_data: pd.DataFrame,
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        threshold: float = 0.0
    ) -> List[RiskResult]:
        """
        Calculate downside beta (beta during negative market returns).
        
        Parameters
        ----------
        data : pd.DataFrame
            Asset price data
        benchmark_data : pd.DataFrame
            Benchmark price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes for calculation
        threshold : float, default 0.0
            Threshold for defining downside
        
        Returns
        -------
        List[RiskResult]
            Downside beta results
        """
        if windows is None:
            windows = self.config.beta_windows
        
        # Calculate returns
        asset_returns = self._calculate_returns(
            data[self.config.price_column], 
            self.config.return_method
        )
        benchmark_returns = self._calculate_returns(
            benchmark_data[self.config.price_column], 
            self.config.return_method
        )
        
        # Align data
        aligned_data = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        asset_returns = aligned_data.iloc[:, 0]
        benchmark_returns = aligned_data.iloc[:, 1]
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            downside_beta_series = self._calculate_conditional_beta(
                asset_returns, benchmark_returns, window, 
                condition=lambda x: x <= threshold, 
                condition_name="downside"
            )
            
            result = RiskResult(
                metric_name=f"downside_beta_{window}d",
                value=downside_beta_series,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={
                    'threshold': threshold,
                    'condition': 'benchmark_return <= threshold'
                },
                metadata={
                    'data_points': len(aligned_data),
                    'valid_points': downside_beta_series.count()
                }
            )
            
            results.append(result)
        
        return results
    
    def calculate_upside_beta(
        self, 
        data: pd.DataFrame, 
        benchmark_data: pd.DataFrame,
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        threshold: float = 0.0
    ) -> List[RiskResult]:
        """
        Calculate upside beta (beta during positive market returns).
        
        Parameters
        ----------
        data : pd.DataFrame
            Asset price data
        benchmark_data : pd.DataFrame
            Benchmark price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes for calculation
        threshold : float, default 0.0
            Threshold for defining upside
        
        Returns
        -------
        List[RiskResult]
            Upside beta results
        """
        if windows is None:
            windows = self.config.beta_windows
        
        # Calculate returns
        asset_returns = self._calculate_returns(
            data[self.config.price_column], 
            self.config.return_method
        )
        benchmark_returns = self._calculate_returns(
            benchmark_data[self.config.price_column], 
            self.config.return_method
        )
        
        # Align data
        aligned_data = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        asset_returns = aligned_data.iloc[:, 0]
        benchmark_returns = aligned_data.iloc[:, 1]
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            upside_beta_series = self._calculate_conditional_beta(
                asset_returns, benchmark_returns, window, 
                condition=lambda x: x > threshold, 
                condition_name="upside"
            )
            
            result = RiskResult(
                metric_name=f"upside_beta_{window}d",
                value=upside_beta_series,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={
                    'threshold': threshold,
                    'condition': 'benchmark_return > threshold'
                },
                metadata={
                    'data_points': len(aligned_data),
                    'valid_points': upside_beta_series.count()
                }
            )
            
            results.append(result)
        
        return results
    
    def _calculate_conditional_beta(
        self, 
        asset_returns: pd.Series, 
        benchmark_returns: pd.Series, 
        window: int,
        condition: callable,
        condition_name: str
    ) -> pd.Series:
        """
        Calculate conditional beta based on a condition.
        
        Parameters
        ----------
        asset_returns : pd.Series
            Asset return series
        benchmark_returns : pd.Series
            Benchmark return series
        window : int
            Rolling window size
        condition : callable
            Condition function for benchmark returns
        condition_name : str
            Name of the condition for identification
        
        Returns
        -------
        pd.Series
            Conditional beta series
        """
        min_periods = self.config.get_min_periods(window, 'beta')
        
        def conditional_beta(asset_window, benchmark_window):
            if len(asset_window) < min_periods:
                return np.nan
            
            # Apply condition
            condition_mask = condition(benchmark_window)
            
            if condition_mask.sum() < max(2, min_periods // 2):
                return np.nan
            
            # Filter data based on condition
            filtered_asset = asset_window[condition_mask]
            filtered_benchmark = benchmark_window[condition_mask]
            
            # Calculate beta
            covariance = np.cov(filtered_asset, filtered_benchmark)[0, 1]
            benchmark_variance = np.var(filtered_benchmark, ddof=1)
            
            if benchmark_variance == 0:
                return np.nan
            
            return covariance / benchmark_variance
        
        # Combine series for rolling calculation
        combined = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        
        return combined.rolling(
            window=window, 
            min_periods=min_periods
        ).apply(
            lambda x: conditional_beta(x.iloc[:, 0], x.iloc[:, 1]), 
            raw=False
        )
    
    def calculate_beta_stability(
        self, 
        data: pd.DataFrame, 
        benchmark_data: pd.DataFrame,
        symbol: str, 
        timeframe: str,
        window: int = 252,
        sub_periods: int = 4
    ) -> RiskResult:
        """
        Calculate beta stability metrics.
        
        Parameters
        ----------
        data : pd.DataFrame
            Asset price data
        benchmark_data : pd.DataFrame
            Benchmark price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        window : int, default 252
            Window size for beta calculation
        sub_periods : int, default 4
            Number of sub-periods for stability analysis
        
        Returns
        -------
        RiskResult
            Beta stability metrics
        """
        # Calculate returns
        asset_returns = self._calculate_returns(
            data[self.config.price_column], 
            self.config.return_method
        )
        benchmark_returns = self._calculate_returns(
            benchmark_data[self.config.price_column], 
            self.config.return_method
        )
        
        # Align data
        aligned_data = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        asset_returns = aligned_data.iloc[:, 0]
        benchmark_returns = aligned_data.iloc[:, 1]
        
        # Calculate rolling beta
        beta_series = self._calculate_rolling_beta(
            asset_returns, benchmark_returns, window
        ).dropna()
        
        if len(beta_series) < sub_periods:
            raise ValueError(f"Insufficient data for stability analysis. Need at least {sub_periods} beta observations.")
        
        # Split into sub-periods
        sub_period_size = len(beta_series) // sub_periods
        sub_period_betas = []
        
        for i in range(sub_periods):
            start_idx = i * sub_period_size
            end_idx = (i + 1) * sub_period_size if i < sub_periods - 1 else len(beta_series)
            sub_period_beta = beta_series.iloc[start_idx:end_idx].mean()
            sub_period_betas.append(sub_period_beta)
        
        # Calculate stability metrics
        beta_mean = np.mean(sub_period_betas)
        beta_std = np.std(sub_period_betas, ddof=1)
        beta_cv = beta_std / abs(beta_mean) if beta_mean != 0 else np.inf
        
        # Trend analysis
        periods = np.arange(len(sub_period_betas))
        slope, intercept, r_value, p_value, std_err = stats.linregress(periods, sub_period_betas)
        
        stability_metrics = {
            'sub_period_betas': sub_period_betas,
            'beta_mean': beta_mean,
            'beta_std': beta_std,
            'beta_coefficient_of_variation': beta_cv,
            'trend_slope': slope,
            'trend_r_squared': r_value ** 2,
            'trend_p_value': p_value,
            'is_stable': beta_cv < 0.5 and p_value > 0.05,  # Stability criteria
            'stability_score': max(0, 1 - beta_cv) * (1 - min(1, abs(p_value - 0.5) * 2))
        }
        
        return RiskResult(
            metric_name="beta_stability",
            value=stability_metrics,
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            window=window,
            parameters={
                'sub_periods': sub_periods,
                'window': window
            },
            metadata={
                'data_points': len(aligned_data),
                'beta_observations': len(beta_series)
            }
        )
    
    def calculate_alpha(
        self, 
        data: pd.DataFrame, 
        benchmark_data: pd.DataFrame,
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        risk_free_rate: Optional[float] = None
    ) -> List[RiskResult]:
        """
        Calculate Jensen's alpha.
        
        Parameters
        ----------
        data : pd.DataFrame
            Asset price data
        benchmark_data : pd.DataFrame
            Benchmark price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes for calculation
        risk_free_rate : float, optional
            Risk-free rate
        
        Returns
        -------
        List[RiskResult]
            Alpha calculation results
        """
        if windows is None:
            windows = self.config.beta_windows
        
        if risk_free_rate is None:
            risk_free_rate = self.config.risk_free_rate
        
        # Calculate returns
        asset_returns = self._calculate_returns(
            data[self.config.price_column], 
            self.config.return_method
        )
        benchmark_returns = self._calculate_returns(
            benchmark_data[self.config.price_column], 
            self.config.return_method
        )
        
        # Align data
        aligned_data = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        asset_returns = aligned_data.iloc[:, 0]
        benchmark_returns = aligned_data.iloc[:, 1]
        
        # Convert annual risk-free rate to period rate
        daily_rf_rate = risk_free_rate / self.config.periods_per_year
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            alpha_series = self._calculate_rolling_alpha(
                asset_returns, benchmark_returns, window, daily_rf_rate
            )
            
            result = RiskResult(
                metric_name=f"alpha_{window}d",
                value=alpha_series,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={
                    'risk_free_rate': risk_free_rate,
                    'annualized': True
                },
                metadata={
                    'data_points': len(aligned_data),
                    'valid_points': alpha_series.count()
                }
            )
            
            results.append(result)
        
        return results
    
    def _calculate_rolling_alpha(
        self, 
        asset_returns: pd.Series, 
        benchmark_returns: pd.Series, 
        window: int,
        daily_rf_rate: float
    ) -> pd.Series:
        """
        Calculate rolling Jensen's alpha.
        
        Parameters
        ----------
        asset_returns : pd.Series
            Asset return series
        benchmark_returns : pd.Series
            Benchmark return series
        window : int
            Rolling window size
        daily_rf_rate : float
            Daily risk-free rate
        
        Returns
        -------
        pd.Series
            Rolling alpha series
        """
        min_periods = self.config.get_min_periods(window, 'beta')
        
        def rolling_alpha(asset_window, benchmark_window):
            if len(asset_window) < min_periods:
                return np.nan
            
            # Calculate excess returns
            excess_asset = asset_window - daily_rf_rate
            excess_benchmark = benchmark_window - daily_rf_rate
            
            # Linear regression: excess_asset = alpha + beta * excess_benchmark
            X = excess_benchmark.values.reshape(-1, 1)
            y = excess_asset.values
            
            try:
                reg = LinearRegression().fit(X, y)
                alpha = reg.intercept_
                
                # Annualize alpha
                annualized_alpha = alpha * self.config.periods_per_year
                return annualized_alpha
            except:
                return np.nan
        
        # Combine series for rolling calculation
        combined = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
        
        return combined.rolling(
            window=window, 
            min_periods=min_periods
        ).apply(
            lambda x: rolling_alpha(x.iloc[:, 0], x.iloc[:, 1]), 
            raw=False
        )
