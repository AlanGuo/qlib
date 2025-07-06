# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Drawdown calculator for cryptocurrency risk metrics.

This module provides comprehensive drawdown analysis including maximum drawdown,
current drawdown, drawdown duration, and recovery analysis.
"""

from typing import List, Union, Optional, Dict, Any, Tuple
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from base_calculator import BaseRiskCalculator, RiskResult
from config.risk_config import RiskConfig


class DrawdownCalculator(BaseRiskCalculator):
    """
    Calculator for drawdown metrics.
    
    Supports:
    - Maximum drawdown
    - Current drawdown
    - Drawdown duration
    - Recovery time analysis
    - Underwater curve
    - Drawdown statistics
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize drawdown calculator.
        
        Parameters
        ----------
        config : RiskConfig, optional
            Configuration for drawdown calculation
        """
        super().__init__("DrawdownCalculator")
        self.config = config or RiskConfig()
    
    def calculate(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        lookback_periods: Optional[int] = None,
        **kwargs
    ) -> List[RiskResult]:
        """
        Calculate drawdown metrics.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        lookback_periods : int, optional
            Maximum lookback periods for calculation
        **kwargs
            Additional parameters
        
        Returns
        -------
        List[RiskResult]
            List of drawdown calculation results
        """
        self._validate_data(data)
        
        if lookback_periods is None:
            lookback_periods = self.config.drawdown_lookback_periods
        
        # Limit data to lookback periods
        if len(data) > lookback_periods:
            data = data.tail(lookback_periods)
        
        prices = data[self.config.price_column]
        timestamp = datetime.now()
        
        # Calculate basic drawdown metrics
        drawdown_series, max_drawdown_series = self._calculate_drawdown_series(prices)
        
        results = []
        
        # Maximum drawdown
        max_drawdown = max_drawdown_series.iloc[-1]
        results.append(RiskResult(
            metric_name="maximum_drawdown",
            value=max_drawdown,
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe,
            parameters={'lookback_periods': lookback_periods},
            metadata={
                'data_points': len(data),
                'calculation_method': 'peak_to_trough'
            }
        ))
        
        # Current drawdown
        current_drawdown = drawdown_series.iloc[-1]
        results.append(RiskResult(
            metric_name="current_drawdown",
            value=current_drawdown,
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe,
            parameters={'lookback_periods': lookback_periods},
            metadata={'data_points': len(data)}
        ))
        
        # Drawdown series
        results.append(RiskResult(
            metric_name="drawdown_series",
            value=drawdown_series,
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe,
            parameters={'lookback_periods': lookback_periods},
            metadata={'data_points': len(data)}
        ))
        
        # Drawdown duration analysis
        if self.config.drawdown_recovery_tracking:
            duration_stats = self._calculate_drawdown_duration_stats(
                prices, drawdown_series
            )
            results.append(RiskResult(
                metric_name="drawdown_duration_stats",
                value=duration_stats,
                timestamp=timestamp,
                symbol=symbol,
                timeframe=timeframe,
                parameters={'lookback_periods': lookback_periods},
                metadata={'data_points': len(data)}
            ))
        
        # Underwater curve (time spent in drawdown)
        underwater_curve = self._calculate_underwater_curve(drawdown_series)
        results.append(RiskResult(
            metric_name="underwater_curve",
            value=underwater_curve,
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe,
            parameters={'lookback_periods': lookback_periods},
            metadata={'data_points': len(data)}
        ))
        
        return results
    
    def _calculate_drawdown_series(
        self, 
        prices: pd.Series
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate drawdown series and maximum drawdown series.
        
        Parameters
        ----------
        prices : pd.Series
            Price series
        
        Returns
        -------
        Tuple[pd.Series, pd.Series]
            Drawdown series and maximum drawdown series
        """
        # Calculate running maximum (peak)
        peak = prices.expanding().max()
        
        # Calculate drawdown as percentage from peak
        drawdown = (prices - peak) / peak
        
        # Calculate maximum drawdown up to each point
        max_drawdown = drawdown.expanding().min()
        
        return drawdown, max_drawdown
    
    def _calculate_drawdown_duration_stats(
        self, 
        prices: pd.Series, 
        drawdown_series: pd.Series
    ) -> Dict[str, Any]:
        """
        Calculate drawdown duration statistics.
        
        Parameters
        ----------
        prices : pd.Series
            Price series
        drawdown_series : pd.Series
            Drawdown series
        
        Returns
        -------
        Dict[str, Any]
            Drawdown duration statistics
        """
        # Identify drawdown periods (when drawdown < 0)
        in_drawdown = drawdown_series < 0
        
        # Find drawdown periods
        drawdown_periods = []
        start_idx = None
        
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                # Start of drawdown
                start_idx = i
            elif not is_dd and start_idx is not None:
                # End of drawdown
                drawdown_periods.append((start_idx, i - 1))
                start_idx = None
        
        # Handle case where we're still in drawdown
        if start_idx is not None:
            drawdown_periods.append((start_idx, len(drawdown_series) - 1))
        
        if not drawdown_periods:
            return {
                'total_drawdown_periods': 0,
                'average_duration': 0,
                'max_duration': 0,
                'current_duration': 0,
                'time_in_drawdown_pct': 0.0
            }
        
        # Calculate duration statistics
        durations = [end - start + 1 for start, end in drawdown_periods]
        
        # Calculate recovery times
        recovery_times = []
        peak_series = prices.expanding().max()
        
        for start, end in drawdown_periods[:-1]:  # Exclude current if ongoing
            # Find when price recovers to previous peak
            peak_at_start = peak_series.iloc[start]
            recovery_idx = None
            
            for i in range(end + 1, len(prices)):
                if prices.iloc[i] >= peak_at_start:
                    recovery_idx = i
                    break
            
            if recovery_idx is not None:
                recovery_times.append(recovery_idx - end)
        
        # Current drawdown duration
        current_duration = 0
        if in_drawdown.iloc[-1]:
            # Find start of current drawdown
            for i in range(len(in_drawdown) - 1, -1, -1):
                if not in_drawdown.iloc[i]:
                    current_duration = len(in_drawdown) - 1 - i
                    break
            else:
                current_duration = len(in_drawdown)
        
        return {
            'total_drawdown_periods': len(drawdown_periods),
            'average_duration': np.mean(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'current_duration': current_duration,
            'time_in_drawdown_pct': sum(durations) / len(drawdown_series) * 100,
            'average_recovery_time': np.mean(recovery_times) if recovery_times else None,
            'max_recovery_time': max(recovery_times) if recovery_times else None,
            'drawdown_periods': drawdown_periods
        }
    
    def _calculate_underwater_curve(self, drawdown_series: pd.Series) -> pd.Series:
        """
        Calculate underwater curve (cumulative time in drawdown).
        
        Parameters
        ----------
        drawdown_series : pd.Series
            Drawdown series
        
        Returns
        -------
        pd.Series
            Underwater curve
        """
        # Binary series: 1 if in drawdown, 0 if at peak
        in_drawdown = (drawdown_series < 0).astype(int)
        
        # Cumulative sum gives total time spent underwater
        underwater_curve = in_drawdown.expanding().sum() / np.arange(1, len(in_drawdown) + 1)
        
        return underwater_curve
    
    def calculate_rolling_max_drawdown(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        window: int = 252
    ) -> RiskResult:
        """
        Calculate rolling maximum drawdown.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        window : int, default 252
            Rolling window size
        
        Returns
        -------
        RiskResult
            Rolling maximum drawdown result
        """
        prices = data[self.config.price_column]
        
        def rolling_max_dd(price_window):
            if len(price_window) < 2:
                return np.nan
            
            peak = np.maximum.accumulate(price_window)
            drawdown = (price_window - peak) / peak
            return np.min(drawdown)
        
        rolling_max_dd_series = prices.rolling(
            window=window,
            min_periods=max(1, window // 2)
        ).apply(rolling_max_dd, raw=True)
        
        return RiskResult(
            metric_name=f"rolling_max_drawdown_{window}d",
            value=rolling_max_dd_series,
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            window=window,
            parameters={'window': window},
            metadata={'data_points': len(data)}
        )
    
    def calculate_calmar_ratio(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        lookback_periods: Optional[int] = None
    ) -> RiskResult:
        """
        Calculate Calmar ratio (annual return / maximum drawdown).
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        lookback_periods : int, optional
            Lookback periods for calculation
        
        Returns
        -------
        RiskResult
            Calmar ratio result
        """
        if lookback_periods is None:
            lookback_periods = self.config.calmar_ratio_lookback
        
        # Limit data
        if len(data) > lookback_periods:
            data = data.tail(lookback_periods)
        
        prices = data[self.config.price_column]
        
        # Calculate annualized return
        total_return = (prices.iloc[-1] / prices.iloc[0]) - 1
        periods = len(prices) - 1
        annualized_return = (1 + total_return) ** (self.config.periods_per_year / periods) - 1
        
        # Calculate maximum drawdown
        _, max_drawdown_series = self._calculate_drawdown_series(prices)
        max_drawdown = abs(max_drawdown_series.iloc[-1])
        
        # Calculate Calmar ratio
        calmar_ratio = annualized_return / max_drawdown if max_drawdown != 0 else np.inf
        
        return RiskResult(
            metric_name="calmar_ratio",
            value=calmar_ratio,
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            parameters={
                'lookback_periods': lookback_periods,
                'annualized_return': annualized_return,
                'max_drawdown': max_drawdown
            },
            metadata={'data_points': len(data)}
        )
    
    def get_drawdown_summary(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str
    ) -> RiskResult:
        """
        Get comprehensive drawdown summary.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        
        Returns
        -------
        RiskResult
            Drawdown summary
        """
        prices = data[self.config.price_column]
        drawdown_series, max_drawdown_series = self._calculate_drawdown_series(prices)
        duration_stats = self._calculate_drawdown_duration_stats(prices, drawdown_series)
        
        summary = {
            'max_drawdown': max_drawdown_series.iloc[-1],
            'current_drawdown': drawdown_series.iloc[-1],
            'avg_drawdown': drawdown_series[drawdown_series < 0].mean(),
            'drawdown_volatility': drawdown_series.std(),
            'time_to_recovery_avg': duration_stats.get('average_recovery_time'),
            'time_underwater_pct': duration_stats['time_in_drawdown_pct'],
            'total_drawdown_periods': duration_stats['total_drawdown_periods'],
            'longest_drawdown_duration': duration_stats['max_duration']
        }
        
        return RiskResult(
            metric_name="drawdown_summary",
            value=summary,
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            metadata={'data_points': len(data)}
        )
