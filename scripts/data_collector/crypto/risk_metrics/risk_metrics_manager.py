# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Risk metrics manager for cryptocurrency data collection.

This module provides a unified interface for calculating and managing
all risk metrics for cryptocurrency data.
"""

from typing import List, Dict, Any, Optional, Union
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime
import pandas as pd
import numpy as np
import logging

from base_calculator import RiskResult
from volatility_calculator import VolatilityCalculator
from drawdown_calculator import DrawdownCalculator
from sharpe_calculator import SharpeRatioCalculator
from var_calculator import VaRCalculator
from beta_calculator import BetaCalculator
from config.risk_config import RiskConfig


class RiskMetricsManager:
    """
    Unified manager for all cryptocurrency risk metrics calculation.
    
    This class coordinates multiple risk calculators and provides
    a single interface for comprehensive risk analysis.
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Initialize risk metrics manager.
        
        Parameters
        ----------
        config : RiskConfig, optional
            Configuration for risk metrics calculation
        """
        self.config = config or RiskConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize calculators
        self.volatility_calculator = VolatilityCalculator(self.config)
        self.drawdown_calculator = DrawdownCalculator(self.config)
        self.sharpe_calculator = SharpeRatioCalculator(self.config)
        self.var_calculator = VaRCalculator(self.config)
        self.beta_calculator = BetaCalculator(self.config)
        
        # Track calculation history
        self.calculation_history = []
    
    def calculate_all_metrics(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        benchmark_data: Optional[pd.DataFrame] = None,
        metrics: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, List[RiskResult]]:
        """
        Calculate all available risk metrics.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        benchmark_data : pd.DataFrame, optional
            Benchmark data for beta calculations
        metrics : List[str], optional
            Specific metrics to calculate
        **kwargs
            Additional parameters
        
        Returns
        -------
        Dict[str, List[RiskResult]]
            Dictionary of calculated risk metrics
        """
        if metrics is None:
            metrics = ['volatility', 'drawdown', 'sharpe', 'var']
            if benchmark_data is not None:
                metrics.append('beta')
        
        results = {}
        calculation_start = datetime.now()
        
        try:
            # Volatility metrics
            if 'volatility' in metrics:
                self.logger.info(f"Calculating volatility metrics for {symbol}")
                results['volatility'] = self.volatility_calculator.calculate(
                    data, symbol, timeframe, **kwargs
                )
            
            # Drawdown metrics
            if 'drawdown' in metrics:
                self.logger.info(f"Calculating drawdown metrics for {symbol}")
                results['drawdown'] = self.drawdown_calculator.calculate(
                    data, symbol, timeframe, **kwargs
                )
            
            # Sharpe ratio metrics
            if 'sharpe' in metrics:
                self.logger.info(f"Calculating Sharpe ratio metrics for {symbol}")
                results['sharpe'] = self.sharpe_calculator.calculate(
                    data, symbol, timeframe, **kwargs
                )
            
            # VaR metrics
            if 'var' in metrics:
                self.logger.info(f"Calculating VaR metrics for {symbol}")
                results['var'] = self.var_calculator.calculate(
                    data, symbol, timeframe, **kwargs
                )
            
            # Beta metrics (requires benchmark)
            if 'beta' in metrics and benchmark_data is not None:
                self.logger.info(f"Calculating beta metrics for {symbol}")
                results['beta'] = self.beta_calculator.calculate(
                    data, benchmark_data, symbol, timeframe, **kwargs
                )
            elif 'beta' in metrics and benchmark_data is None:
                self.logger.warning(f"Beta calculation requested but no benchmark data provided for {symbol}")
            
            # Record calculation
            calculation_end = datetime.now()
            self.calculation_history.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'metrics': metrics,
                'start_time': calculation_start,
                'end_time': calculation_end,
                'duration': (calculation_end - calculation_start).total_seconds(),
                'data_points': len(data),
                'success': True
            })
            
            self.logger.info(f"Successfully calculated {len(metrics)} metric types for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics for {symbol}: {str(e)}")
            self.calculation_history.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'metrics': metrics,
                'start_time': calculation_start,
                'end_time': datetime.now(),
                'error': str(e),
                'success': False
            })
            raise
        
        return results
    
    def calculate_risk_summary(
        self, 
        data: pd.DataFrame, 
        symbol: str, 
        timeframe: str,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> RiskResult:
        """
        Calculate a comprehensive risk summary.
        
        Parameters
        ----------
        data : pd.DataFrame
            Price data
        symbol : str
            Symbol identifier
        timeframe : str
            Data timeframe
        benchmark_data : pd.DataFrame, optional
            Benchmark data
        
        Returns
        -------
        RiskResult
            Comprehensive risk summary
        """
        # Calculate all metrics
        all_metrics = self.calculate_all_metrics(
            data, symbol, timeframe, benchmark_data
        )
        
        # Extract key metrics for summary
        summary = {
            'symbol': symbol,
            'timeframe': timeframe,
            'data_period': f"{data.index[0]} to {data.index[-1]}",
            'data_points': len(data)
        }
        
        # Volatility summary
        if 'volatility' in all_metrics:
            vol_30d = self._extract_metric_value(all_metrics['volatility'], 'historical_volatility_30d')
            summary['volatility_30d'] = vol_30d
        
        # Drawdown summary
        if 'drawdown' in all_metrics:
            max_dd = self._extract_metric_value(all_metrics['drawdown'], 'maximum_drawdown')
            current_dd = self._extract_metric_value(all_metrics['drawdown'], 'current_drawdown')
            summary['max_drawdown'] = max_dd
            summary['current_drawdown'] = current_dd
        
        # Sharpe ratio summary
        if 'sharpe' in all_metrics:
            sharpe_30d = self._extract_metric_value(all_metrics['sharpe'], 'sharpe_ratio_30d')
            summary['sharpe_ratio_30d'] = sharpe_30d
        
        # VaR summary
        if 'var' in all_metrics:
            var_5pct = self._extract_metric_value(all_metrics['var'], 'var_historical_5pct_30d')
            summary['var_5pct_30d'] = var_5pct
        
        # Beta summary
        if 'beta' in all_metrics:
            beta_30d = self._extract_metric_value(all_metrics['beta'], 'beta_30d')
            summary['beta_30d'] = beta_30d
        
        # Risk score calculation
        summary['risk_score'] = self._calculate_risk_score(summary)
        
        return RiskResult(
            metric_name="risk_summary",
            value=summary,
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            metadata={
                'calculation_method': 'comprehensive_analysis',
                'metrics_included': list(all_metrics.keys())
            }
        )
    
    def _extract_metric_value(self, metric_results: List[RiskResult], metric_name: str) -> Any:
        """Extract the latest value for a specific metric."""
        for result in metric_results:
            if result.metric_name == metric_name:
                if isinstance(result.value, pd.Series):
                    return result.value.iloc[-1] if not result.value.empty else None
                else:
                    return result.value
        return None
    
    def _calculate_risk_score(self, summary: Dict[str, Any]) -> float:
        """
        Calculate a composite risk score (0-100, higher = riskier).
        
        Parameters
        ----------
        summary : Dict[str, Any]
            Risk summary metrics
        
        Returns
        -------
        float
            Risk score
        """
        score = 0.0
        components = 0
        
        # Volatility component (0-30 points)
        vol_30d = summary.get('volatility_30d')
        if vol_30d is not None and not np.isnan(vol_30d):
            # Normalize volatility (0.5 = 50 points, 1.0 = 100 points)
            vol_score = min(30, vol_30d * 60)
            score += vol_score
            components += 1
        
        # Drawdown component (0-25 points)
        max_dd = summary.get('max_drawdown')
        if max_dd is not None and not np.isnan(max_dd):
            # Normalize drawdown (50% = 25 points)
            dd_score = min(25, abs(max_dd) * 50)
            score += dd_score
            components += 1
        
        # Sharpe ratio component (0-20 points, inverted)
        sharpe_30d = summary.get('sharpe_ratio_30d')
        if sharpe_30d is not None and not np.isnan(sharpe_30d):
            # Lower Sharpe = higher risk (Sharpe < 0 = 20 points, Sharpe > 2 = 0 points)
            sharpe_score = max(0, 20 - max(0, sharpe_30d) * 10)
            score += sharpe_score
            components += 1
        
        # VaR component (0-15 points)
        var_5pct = summary.get('var_5pct_30d')
        if var_5pct is not None and not np.isnan(var_5pct):
            # Normalize VaR (10% loss = 15 points)
            var_score = min(15, abs(var_5pct) * 150)
            score += var_score
            components += 1
        
        # Beta component (0-10 points)
        beta_30d = summary.get('beta_30d')
        if beta_30d is not None and not np.isnan(beta_30d):
            # High beta = higher risk (beta > 2 = 10 points)
            beta_score = min(10, max(0, abs(beta_30d) - 1) * 10)
            score += beta_score
            components += 1
        
        # Normalize by number of components
        if components > 0:
            return score / components * (5 / components)  # Scale to 0-100
        else:
            return 50.0  # Default moderate risk if no metrics available
    
    def get_calculation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about risk calculations performed.
        
        Returns
        -------
        Dict[str, Any]
            Calculation statistics
        """
        if not self.calculation_history:
            return {'total_calculations': 0}
        
        successful = [calc for calc in self.calculation_history if calc['success']]
        failed = [calc for calc in self.calculation_history if not calc['success']]
        
        stats = {
            'total_calculations': len(self.calculation_history),
            'successful_calculations': len(successful),
            'failed_calculations': len(failed),
            'success_rate': len(successful) / len(self.calculation_history) * 100,
        }
        
        if successful:
            durations = [calc['duration'] for calc in successful]
            stats.update({
                'avg_calculation_time': np.mean(durations),
                'min_calculation_time': np.min(durations),
                'max_calculation_time': np.max(durations),
            })
        
        # Most calculated symbols
        symbol_counts = {}
        for calc in self.calculation_history:
            symbol = calc['symbol']
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        if symbol_counts:
            stats['most_calculated_symbol'] = max(symbol_counts, key=symbol_counts.get)
            stats['symbol_calculation_counts'] = symbol_counts
        
        return stats
    
    def clear_cache(self):
        """Clear all calculator caches."""
        self.volatility_calculator._clear_cache()
        self.drawdown_calculator._clear_cache()
        self.sharpe_calculator._clear_cache()
        self.var_calculator._clear_cache()
        self.beta_calculator._clear_cache()
        
        self.logger.info("All risk calculator caches cleared")
    
    def get_supported_metrics(self) -> Dict[str, List[str]]:
        """
        Get list of all supported risk metrics.
        
        Returns
        -------
        Dict[str, List[str]]
            Dictionary of metric categories and their specific metrics
        """
        return {
            'volatility': [
                'historical_volatility', 'realized_volatility', 'parkinson_volatility',
                'garman_klass_volatility', 'yang_zhang_volatility', 'volatility_cone'
            ],
            'drawdown': [
                'maximum_drawdown', 'current_drawdown', 'drawdown_series',
                'drawdown_duration_stats', 'underwater_curve', 'calmar_ratio'
            ],
            'sharpe': [
                'sharpe_ratio', 'information_ratio', 'sortino_ratio', 'treynor_ratio'
            ],
            'var': [
                'var_historical', 'var_parametric', 'var_monte_carlo',
                'conditional_var', 'var_backtesting'
            ],
            'beta': [
                'beta', 'downside_beta', 'upside_beta', 'beta_stability', 'alpha'
            ]
        }
