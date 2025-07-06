# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Configuration for cryptocurrency risk metrics calculation.

This module provides configuration classes for customizing risk metrics
calculation parameters and behavior.
"""

from dataclasses import dataclass, field

from typing import List, Dict, Any, Optional


@dataclass
class RiskConfig:
    """
    Configuration for cryptocurrency risk metrics calculation.
    
    This class contains all configurable parameters for risk metrics calculation,
    allowing users to customize calculation behavior for different use cases.
    """
    
    # General configuration
    calculation_frequency: str = "1h"  # Calculation frequency
    cache_enabled: bool = True
    cache_size_limit: int = 1000
    periods_per_year: int = 365  # 365 for crypto (24/7), 252 for traditional markets
    
    # Data configuration
    price_column: str = "close"
    return_method: str = "log"  # 'log' or 'simple'
    min_periods_ratio: float = 0.5  # Minimum periods as ratio of window
    
    # Volatility configuration
    volatility_windows: List[int] = field(default_factory=lambda: [7, 30, 90, 252])
    volatility_annualize: bool = True
    volatility_min_periods: Optional[int] = None
    
    # VaR configuration
    var_confidence_levels: List[float] = field(default_factory=lambda: [0.01, 0.05, 0.10])
    var_methods: List[str] = field(default_factory=lambda: ["historical", "parametric"])
    var_windows: List[int] = field(default_factory=lambda: [30, 90, 252])
    var_monte_carlo_simulations: int = 10000
    
    # Drawdown configuration
    drawdown_lookback_periods: int = 1000  # Maximum lookback for drawdown calculation
    drawdown_recovery_tracking: bool = True
    
    # Sharpe ratio configuration
    risk_free_rate: float = 0.02  # Annual risk-free rate
    sharpe_windows: List[int] = field(default_factory=lambda: [30, 90, 252])
    sharpe_annualize: bool = True
    sharpe_min_periods: Optional[int] = None
    
    # Beta calculation configuration
    beta_windows: List[int] = field(default_factory=lambda: [30, 90, 252])
    beta_benchmark_symbol: str = "BTC/USDT"  # Default benchmark
    beta_min_periods: Optional[int] = None
    
    # Advanced metrics configuration
    information_ratio_windows: List[int] = field(default_factory=lambda: [30, 90, 252])
    calmar_ratio_lookback: int = 252
    sortino_ratio_windows: List[int] = field(default_factory=lambda: [30, 90, 252])
    downside_deviation_threshold: float = 0.0  # Threshold for downside deviation
    
    # Performance optimization
    parallel_calculation: bool = False
    max_workers: Optional[int] = None
    chunk_size: int = 1000  # For large dataset processing
    
    @classmethod
    def create_high_frequency_config(cls) -> 'RiskConfig':
        """
        Create configuration optimized for high-frequency data.
        
        Returns
        -------
        RiskConfig
            Configuration for high-frequency risk calculation
        """
        return cls(
            calculation_frequency="1m",
            volatility_windows=[60, 240, 1440],  # 1h, 4h, 1d in minutes
            var_windows=[60, 240, 1440],
            sharpe_windows=[240, 1440, 10080],  # 4h, 1d, 1w in minutes
            beta_windows=[240, 1440, 10080],
            periods_per_year=525600,  # Minutes per year
            min_periods_ratio=0.3,  # Lower requirement for HF data
            cache_size_limit=5000,
        )
    
    @classmethod
    def create_daily_config(cls) -> 'RiskConfig':
        """
        Create configuration optimized for daily data.
        
        Returns
        -------
        RiskConfig
            Configuration for daily risk calculation
        """
        return cls(
            calculation_frequency="1d",
            volatility_windows=[7, 30, 90, 252],
            var_windows=[30, 90, 252],
            sharpe_windows=[30, 90, 252],
            beta_windows=[30, 90, 252],
            periods_per_year=365,
            min_periods_ratio=0.7,  # Higher requirement for daily data
            cache_size_limit=2000,
        )
    
    @classmethod
    def create_conservative_config(cls) -> 'RiskConfig':
        """
        Create conservative configuration with longer windows.
        
        Returns
        -------
        RiskConfig
            Conservative risk calculation configuration
        """
        return cls(
            volatility_windows=[30, 90, 252, 504],  # Up to 2 years
            var_windows=[90, 252, 504],
            sharpe_windows=[90, 252, 504],
            beta_windows=[90, 252, 504],
            var_confidence_levels=[0.01, 0.05],  # More conservative VaR
            min_periods_ratio=0.8,  # Higher data requirement
            drawdown_lookback_periods=2000,  # Longer lookback
        )
    
    @classmethod
    def create_aggressive_config(cls) -> 'RiskConfig':
        """
        Create aggressive configuration with shorter windows.
        
        Returns
        -------
        RiskConfig
            Aggressive risk calculation configuration
        """
        return cls(
            volatility_windows=[3, 7, 14, 30],  # Shorter windows
            var_windows=[7, 14, 30],
            sharpe_windows=[7, 14, 30],
            beta_windows=[7, 14, 30],
            var_confidence_levels=[0.05, 0.10, 0.20],  # Less conservative VaR
            min_periods_ratio=0.3,  # Lower data requirement
            drawdown_lookback_periods=252,  # Shorter lookback
        )
    
    @classmethod
    def create_crypto_optimized_config(cls) -> 'RiskConfig':
        """
        Create configuration optimized for cryptocurrency characteristics.
        
        Returns
        -------
        RiskConfig
            Crypto-optimized risk calculation configuration
        """
        return cls(
            # Crypto-specific settings
            periods_per_year=365,  # 24/7 trading
            risk_free_rate=0.05,  # Higher risk-free rate for crypto
            
            # Shorter windows due to high volatility
            volatility_windows=[3, 7, 14, 30, 90],
            var_windows=[7, 14, 30, 90],
            sharpe_windows=[14, 30, 90],
            beta_windows=[14, 30, 90],
            
            # More conservative VaR due to extreme events
            var_confidence_levels=[0.01, 0.025, 0.05],
            var_methods=["historical", "parametric"],
            
            # Crypto-specific benchmarks
            beta_benchmark_symbol="BTC/USDT",
            
            # Performance settings
            parallel_calculation=True,
            cache_size_limit=3000,
        )
    
    def get_window_config(self, metric_type: str) -> List[int]:
        """
        Get window configuration for specific metric type.
        
        Parameters
        ----------
        metric_type : str
            Type of metric ('volatility', 'var', 'sharpe', 'beta')
        
        Returns
        -------
        List[int]
            List of window sizes for the metric
        """
        window_map = {
            'volatility': self.volatility_windows,
            'var': self.var_windows,
            'sharpe': self.sharpe_windows,
            'beta': self.beta_windows,
            'information_ratio': self.information_ratio_windows,
            'sortino': self.sortino_ratio_windows,
        }
        
        return window_map.get(metric_type, [30])
    
    def get_min_periods(self, window: int, metric_type: str) -> int:
        """
        Get minimum periods required for calculation.
        
        Parameters
        ----------
        window : int
            Window size
        metric_type : str
            Type of metric
        
        Returns
        -------
        int
            Minimum periods required
        """
        # Check for metric-specific min periods
        metric_min_periods = {
            'volatility': self.volatility_min_periods,
            'sharpe': self.sharpe_min_periods,
            'beta': self.beta_min_periods,
        }
        
        specific_min = metric_min_periods.get(metric_type)
        if specific_min is not None:
            return specific_min
        
        # Use ratio-based calculation
        return max(1, int(window * self.min_periods_ratio))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'RiskConfig':
        """Create configuration from dictionary."""
        # Filter out unknown fields
        valid_fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_fields}
        return cls(**filtered_dict)
    
    def update(self, **kwargs) -> 'RiskConfig':
        """
        Create a new configuration with updated parameters.
        
        Parameters
        ----------
        **kwargs
            Parameters to update
        
        Returns
        -------
        RiskConfig
            New configuration with updated parameters
        """
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return self.from_dict(config_dict)
