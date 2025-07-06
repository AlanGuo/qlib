# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Sharpe ratio calculator for cryptocurrency risk metrics.

This module provides comprehensive Sharpe ratio calculation capabilities
including traditional Sharpe ratio, information ratio, and Sortino ratio.
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

from base_calculator import BaseRiskCalculator, RiskResult, RiskMetricsUtility
from config.risk_config import RiskConfig


class SharpeRatioCalculator(BaseRiskCalculator):
    """
    Calculator for Sharpe ratio and related risk-adjusted return metrics.
    
    Supports:
    - Traditional Sharpe ratio
    - Information ratio
    - Sortino ratio
    - Treynor ratio
    - Rolling Sharpe ratio
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize Sharpe ratio calculator.
        
        Parameters
        ----------
        config : RiskConfig, optional
            Configuration for Sharpe ratio calculation
        """
        super().__init__("SharpeRatioCalculator")
        self.config = config or RiskConfig()
    
    def calculate(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        risk_free_rate: Optional[float] = None,
        **kwargs
    ) -> List[RiskResult]:
        """
        Calculate Sharpe ratio metrics.
        
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
        risk_free_rate : float, optional
            Risk-free rate (annual)
        **kwargs
            Additional parameters
        
        Returns
        -------
        List[RiskResult]
            List of Sharpe ratio calculation results
        """
        self._validate_data(data)
        
        if windows is None:
            windows = self.config.sharpe_windows
        
        if risk_free_rate is None:
            risk_free_rate = self.config.risk_free_rate
        
        prices = data[self.config.price_column]
        returns = self._calculate_returns(prices, self.config.return_method)
        
        # Convert annual risk-free rate to period rate
        daily_rf_rate = risk_free_rate / self.config.periods_per_year
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            cache_key = self._cache_key(
                symbol, timeframe, 
                window=window, risk_free_rate=risk_free_rate
            )
            
            # Check cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                results.append(cached_result)
                continue
            
            # Calculate Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio(
                returns, window, daily_rf_rate
            )
            
            # Create result
            result = RiskResult(
                metric_name=f"sharpe_ratio_{window}d",
                value=sharpe_ratio,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={
                    'risk_free_rate_annual': risk_free_rate,
                    'risk_free_rate_daily': daily_rf_rate,
                    'annualized': self.config.sharpe_annualize
                },
                metadata={
                    'data_points': len(data),
                    'valid_points': sharpe_ratio.count() if isinstance(sharpe_ratio, pd.Series) else 1
                }
            )
            
            # Cache and store result
            self._store_in_cache(cache_key, result)
            results.append(result)
        
        return results
    
    def _calculate_sharpe_ratio(
        self, 
        returns: pd.Series, 
        window: int, 
        daily_rf_rate: float
    ) -> pd.Series:
        """
        Calculate rolling Sharpe ratio.
        
        Parameters
        ----------
        returns : pd.Series
            Return series
        window : int
            Rolling window size
        daily_rf_rate : float
            Daily risk-free rate
        
        Returns
        -------
        pd.Series
            Sharpe ratio series
        """
        # Calculate excess returns
        excess_returns = returns - daily_rf_rate
        
        min_periods = self.config.get_min_periods(window, 'sharpe')
        
        # Rolling mean and std of excess returns
        rolling_mean = excess_returns.rolling(
            window=window, 
            min_periods=min_periods
        ).mean()
        
        rolling_std = excess_returns.rolling(
            window=window, 
            min_periods=min_periods
        ).std()
        
        # Sharpe ratio
        sharpe_ratio = RiskMetricsUtility.safe_divide(rolling_mean, rolling_std)
        
        # Annualize if configured
        if self.config.sharpe_annualize:
            sharpe_ratio = self._annualize_metric(
                sharpe_ratio, 
                self.config.periods_per_year, 
                'sharpe'
            )
        
        return sharpe_ratio
    
    def calculate_information_ratio(
        self, 
        data: pd.DataFrame, 
        benchmark_data: pd.DataFrame,
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None
    ) -> List[RiskResult]:
        """
        Calculate information ratio (excess return / tracking error).
        
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
        
        Returns
        -------
        List[RiskResult]
            Information ratio results
        """
        if windows is None:
            windows = self.config.information_ratio_windows
        
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
        
        # Calculate excess returns
        excess_returns = asset_returns - benchmark_returns
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            min_periods = self.config.get_min_periods(window, 'information_ratio')
            
            # Rolling mean and std of excess returns
            rolling_mean = excess_returns.rolling(
                window=window, 
                min_periods=min_periods
            ).mean()
            
            tracking_error = excess_returns.rolling(
                window=window, 
                min_periods=min_periods
            ).std()
            
            # Information ratio
            info_ratio = RiskMetricsUtility.safe_divide(rolling_mean, tracking_error)
            
            # Annualize
            info_ratio = self._annualize_metric(
                info_ratio, 
                self.config.periods_per_year, 
                'sharpe'
            )
            
            result = RiskResult(
                metric_name=f"information_ratio_{window}d",
                value=info_ratio,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={'benchmark': 'provided'},
                metadata={
                    'data_points': len(aligned_data),
                    'valid_points': info_ratio.count()
                }
            )
            
            results.append(result)
        
        return results
    
    def calculate_sortino_ratio(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        target_return: float = 0.0,
        risk_free_rate: Optional[float] = None
    ) -> List[RiskResult]:
        """
        Calculate Sortino ratio (excess return / downside deviation).
        
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
        target_return : float, default 0.0
            Target return threshold
        risk_free_rate : float, optional
            Risk-free rate
        
        Returns
        -------
        List[RiskResult]
            Sortino ratio results
        """
        if windows is None:
            windows = self.config.sortino_ratio_windows
        
        if risk_free_rate is None:
            risk_free_rate = self.config.risk_free_rate
        
        prices = data[self.config.price_column]
        returns = self._calculate_returns(prices, self.config.return_method)
        
        # Convert annual rates to period rates
        daily_rf_rate = risk_free_rate / self.config.periods_per_year
        daily_target_return = target_return / self.config.periods_per_year
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            min_periods = self.config.get_min_periods(window, 'sortino')
            
            # Calculate excess returns
            excess_returns = returns - daily_rf_rate
            
            # Rolling mean of excess returns
            rolling_mean = excess_returns.rolling(
                window=window, 
                min_periods=min_periods
            ).mean()
            
            # Downside deviation
            downside_deviation = self._calculate_downside_deviation(
                returns, window, daily_target_return, min_periods
            )
            
            # Sortino ratio
            sortino_ratio = RiskMetricsUtility.safe_divide(rolling_mean, downside_deviation)
            
            # Annualize
            sortino_ratio = self._annualize_metric(
                sortino_ratio, 
                self.config.periods_per_year, 
                'sharpe'
            )
            
            result = RiskResult(
                metric_name=f"sortino_ratio_{window}d",
                value=sortino_ratio,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={
                    'target_return': target_return,
                    'risk_free_rate': risk_free_rate
                },
                metadata={
                    'data_points': len(data),
                    'valid_points': sortino_ratio.count()
                }
            )
            
            results.append(result)
        
        return results
    
    def _calculate_downside_deviation(
        self, 
        returns: pd.Series, 
        window: int, 
        target_return: float,
        min_periods: int
    ) -> pd.Series:
        """
        Calculate rolling downside deviation.
        
        Parameters
        ----------
        returns : pd.Series
            Return series
        window : int
            Rolling window size
        target_return : float
            Target return threshold
        min_periods : int
            Minimum periods required
        
        Returns
        -------
        pd.Series
            Downside deviation series
        """
        def downside_dev(return_window):
            if len(return_window) < min_periods:
                return np.nan
            
            # Only consider returns below target
            downside_returns = return_window[return_window < target_return]
            
            if len(downside_returns) == 0:
                return 0.0
            
            # Calculate downside deviation
            downside_variance = np.mean((downside_returns - target_return) ** 2)
            return np.sqrt(downside_variance)
        
        return returns.rolling(
            window=window, 
            min_periods=min_periods
        ).apply(downside_dev, raw=True)
    
    def calculate_treynor_ratio(
        self, 
        data: pd.DataFrame, 
        benchmark_data: pd.DataFrame,
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        risk_free_rate: Optional[float] = None
    ) -> List[RiskResult]:
        """
        Calculate Treynor ratio (excess return / beta).
        
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
            Treynor ratio results
        """
        if windows is None:
            windows = self.config.sharpe_windows
        
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
        
        daily_rf_rate = risk_free_rate / self.config.periods_per_year
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            min_periods = self.config.get_min_periods(window, 'beta')
            
            # Calculate rolling beta
            beta = self._calculate_rolling_beta(
                asset_returns, benchmark_returns, window, min_periods
            )
            
            # Calculate excess return
            excess_returns = asset_returns - daily_rf_rate
            rolling_excess_return = excess_returns.rolling(
                window=window, 
                min_periods=min_periods
            ).mean()
            
            # Treynor ratio
            treynor_ratio = RiskMetricsUtility.safe_divide(rolling_excess_return, beta)
            
            # Annualize
            treynor_ratio = self._annualize_metric(
                treynor_ratio, 
                self.config.periods_per_year, 
                'return'
            )
            
            result = RiskResult(
                metric_name=f"treynor_ratio_{window}d",
                value=treynor_ratio,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={'risk_free_rate': risk_free_rate},
                metadata={
                    'data_points': len(aligned_data),
                    'valid_points': treynor_ratio.count()
                }
            )
            
            results.append(result)
        
        return results
    
    def _calculate_rolling_beta(
        self, 
        asset_returns: pd.Series, 
        benchmark_returns: pd.Series, 
        window: int, 
        min_periods: int
    ) -> pd.Series:
        """
        Calculate rolling beta.
        
        Parameters
        ----------
        asset_returns : pd.Series
            Asset return series
        benchmark_returns : pd.Series
            Benchmark return series
        window : int
            Rolling window size
        min_periods : int
            Minimum periods required
        
        Returns
        -------
        pd.Series
            Rolling beta series
        """
        def rolling_beta(asset_window, benchmark_window):
            if len(asset_window) < min_periods or len(benchmark_window) < min_periods:
                return np.nan
            
            covariance = np.cov(asset_window, benchmark_window)[0, 1]
            benchmark_variance = np.var(benchmark_window, ddof=1)
            
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
