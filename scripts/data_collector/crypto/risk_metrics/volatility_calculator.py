# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Volatility calculator for cryptocurrency risk metrics.

This module provides comprehensive volatility calculation capabilities
including historical volatility, realized volatility, and GARCH-based volatility.
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

from risk_metrics.base_calculator import BaseRiskCalculator, RiskResult
from config.risk_config import RiskConfig


class VolatilityCalculator(BaseRiskCalculator):
    """
    Calculator for various volatility metrics.
    
    Supports:
    - Historical volatility (rolling standard deviation)
    - Realized volatility (sum of squared returns)
    - Parkinson volatility (high-low estimator)
    - Garman-Klass volatility (OHLC estimator)
    - Yang-Zhang volatility (drift-independent estimator)
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize volatility calculator.
        
        Parameters
        ----------
        config : RiskConfig, optional
            Configuration for volatility calculation
        """
        super().__init__("VolatilityCalculator")
        self.config = config or RiskConfig()
    
    def calculate(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        method: str = "historical",
        annualize: bool = True,
        **kwargs
    ) -> List[RiskResult]:
        """
        Calculate volatility metrics.
        
        Parameters
        ----------
        data : pd.DataFrame
            OHLC price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes for calculation
        method : str, default "historical"
            Volatility calculation method
        annualize : bool, default True
            Whether to annualize the volatility
        **kwargs
            Additional parameters
        
        Returns
        -------
        List[RiskResult]
            List of volatility calculation results
        """
        self._validate_data(data)
        
        if windows is None:
            windows = self.config.volatility_windows
        
        results = []
        timestamp = datetime.now()
        
        for window in windows:
            cache_key = self._cache_key(
                symbol, timeframe, 
                window=window, method=method, annualize=annualize
            )
            
            # Check cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                results.append(cached_result)
                continue
            
            # Calculate volatility
            if method == "historical":
                volatility = self._calculate_historical_volatility(
                    data, window, annualize
                )
            elif method == "realized":
                volatility = self._calculate_realized_volatility(
                    data, window, annualize
                )
            elif method == "parkinson":
                volatility = self._calculate_parkinson_volatility(
                    data, window, annualize
                )
            elif method == "garman_klass":
                volatility = self._calculate_garman_klass_volatility(
                    data, window, annualize
                )
            elif method == "yang_zhang":
                volatility = self._calculate_yang_zhang_volatility(
                    data, window, annualize
                )
            else:
                raise ValueError(f"Unknown volatility method: {method}")
            
            # Create result
            result = RiskResult(
                metric_name=f"{method}_volatility_{window}d",
                value=volatility,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
                parameters={
                    'method': method,
                    'annualize': annualize,
                    'periods_per_year': self.config.periods_per_year
                },
                metadata={
                    'data_points': len(data),
                    'valid_points': volatility.count() if isinstance(volatility, pd.Series) else 1
                }
            )
            
            # Cache and store result
            self._store_in_cache(cache_key, result)
            results.append(result)
        
        return results
    
    def _get_required_columns(self) -> List[str]:
        """Get required columns for volatility calculation."""
        return ['close']  # Minimum requirement
    
    def _calculate_historical_volatility(
        self, 
        data: pd.DataFrame, 
        window: int, 
        annualize: bool
    ) -> pd.Series:
        """
        Calculate historical volatility using rolling standard deviation.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        window : int
            Rolling window size
        annualize : bool
            Whether to annualize
        
        Returns
        -------
        pd.Series
            Historical volatility
        """
        prices = data[self.config.price_column]
        returns = self._calculate_returns(prices, self.config.return_method)
        
        min_periods = self.config.get_min_periods(window, 'volatility')
        volatility = returns.rolling(
            window=window, 
            min_periods=min_periods
        ).std()
        
        if annualize:
            volatility = self._annualize_metric(
                volatility, 
                self.config.periods_per_year, 
                'volatility'
            )
        
        return volatility
    
    def _calculate_realized_volatility(
        self, 
        data: pd.DataFrame, 
        window: int, 
        annualize: bool
    ) -> pd.Series:
        """
        Calculate realized volatility using sum of squared returns.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        window : int
            Rolling window size
        annualize : bool
            Whether to annualize
        
        Returns
        -------
        pd.Series
            Realized volatility
        """
        prices = data[self.config.price_column]
        returns = self._calculate_returns(prices, self.config.return_method)
        
        min_periods = self.config.get_min_periods(window, 'volatility')
        squared_returns = returns ** 2
        realized_var = squared_returns.rolling(
            window=window, 
            min_periods=min_periods
        ).sum()
        
        volatility = np.sqrt(realized_var)
        
        if annualize:
            volatility = self._annualize_metric(
                volatility, 
                self.config.periods_per_year, 
                'volatility'
            )
        
        return volatility
    
    def _calculate_parkinson_volatility(
        self, 
        data: pd.DataFrame, 
        window: int, 
        annualize: bool
    ) -> pd.Series:
        """
        Calculate Parkinson volatility using high-low estimator.
        
        Parameters
        ----------
        data : pd.DataFrame
            OHLC price data
        window : int
            Rolling window size
        annualize : bool
            Whether to annualize
        
        Returns
        -------
        pd.Series
            Parkinson volatility
        """
        if 'high' not in data.columns or 'low' not in data.columns:
            raise ValueError("High and low prices required for Parkinson volatility")
        
        high = data['high']
        low = data['low']
        
        # Parkinson estimator: (1/(4*ln(2))) * ln(H/L)^2
        hl_ratio = np.log(high / low) ** 2
        parkinson_factor = 1 / (4 * np.log(2))
        
        min_periods = self.config.get_min_periods(window, 'volatility')
        volatility = np.sqrt(
            hl_ratio.rolling(
                window=window, 
                min_periods=min_periods
            ).mean() * parkinson_factor
        )
        
        if annualize:
            volatility = self._annualize_metric(
                volatility, 
                self.config.periods_per_year, 
                'volatility'
            )
        
        return volatility
    
    def _calculate_garman_klass_volatility(
        self, 
        data: pd.DataFrame, 
        window: int, 
        annualize: bool
    ) -> pd.Series:
        """
        Calculate Garman-Klass volatility using OHLC estimator.
        
        Parameters
        ----------
        data : pd.DataFrame
            OHLC price data
        window : int
            Rolling window size
        annualize : bool
            Whether to annualize
        
        Returns
        -------
        pd.Series
            Garman-Klass volatility
        """
        required_cols = ['open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing columns for Garman-Klass volatility: {missing_cols}")
        
        high = data['high']
        low = data['low']
        close = data['close']
        open_price = data['open']
        
        # Garman-Klass estimator
        hl_component = 0.5 * (np.log(high / low) ** 2)
        co_component = (2 * np.log(2) - 1) * (np.log(close / open_price) ** 2)
        
        gk_estimator = hl_component - co_component
        
        min_periods = self.config.get_min_periods(window, 'volatility')
        volatility = np.sqrt(
            gk_estimator.rolling(
                window=window, 
                min_periods=min_periods
            ).mean()
        )
        
        if annualize:
            volatility = self._annualize_metric(
                volatility, 
                self.config.periods_per_year, 
                'volatility'
            )
        
        return volatility
    
    def _calculate_yang_zhang_volatility(
        self, 
        data: pd.DataFrame, 
        window: int, 
        annualize: bool
    ) -> pd.Series:
        """
        Calculate Yang-Zhang volatility (drift-independent estimator).
        
        Parameters
        ----------
        data : pd.DataFrame
            OHLC price data
        window : int
            Rolling window size
        annualize : bool
            Whether to annualize
        
        Returns
        -------
        pd.Series
            Yang-Zhang volatility
        """
        required_cols = ['open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing columns for Yang-Zhang volatility: {missing_cols}")
        
        high = data['high']
        low = data['low']
        close = data['close']
        open_price = data['open']
        
        # Previous close
        prev_close = close.shift(1)
        
        # Yang-Zhang components
        overnight = np.log(open_price / prev_close)
        rs = np.log(high / close) * np.log(high / open_price) + \
             np.log(low / close) * np.log(low / open_price)
        
        min_periods = self.config.get_min_periods(window, 'volatility')
        
        # Rolling calculations
        overnight_var = overnight.rolling(
            window=window, 
            min_periods=min_periods
        ).var()
        
        rs_mean = rs.rolling(
            window=window, 
            min_periods=min_periods
        ).mean()
        
        # Yang-Zhang estimator
        k = 0.34 / (1.34 + (window + 1) / (window - 1))
        volatility = np.sqrt(overnight_var + k * overnight_var + (1 - k) * rs_mean)
        
        if annualize:
            volatility = self._annualize_metric(
                volatility, 
                self.config.periods_per_year, 
                'volatility'
            )
        
        return volatility
    
    def calculate_volatility_cone(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        windows: Optional[List[int]] = None,
        percentiles: List[float] = [10, 25, 50, 75, 90]
    ) -> RiskResult:
        """
        Calculate volatility cone (percentiles across different windows).
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        windows : List[int], optional
            Window sizes
        percentiles : List[float], default [10, 25, 50, 75, 90]
            Percentiles to calculate
        
        Returns
        -------
        RiskResult
            Volatility cone result
        """
        if windows is None:
            windows = self.config.volatility_windows
        
        cone_data = {}
        
        for window in windows:
            volatility = self._calculate_historical_volatility(data, window, True)
            cone_data[f"{window}d"] = [
                np.percentile(volatility.dropna(), p) for p in percentiles
            ]
        
        cone_df = pd.DataFrame(
            cone_data, 
            index=[f"P{p}" for p in percentiles]
        )
        
        return RiskResult(
            metric_name="volatility_cone",
            value=cone_df,
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            parameters={'percentiles': percentiles, 'windows': windows},
            metadata={'data_points': len(data)}
        )
