#!/usr/bin/env python3
"""
Unified Cryptocurrency Factor Library for Qlib

This module provides a comprehensive, standardized interface for cryptocurrency-specific factors,
including decline factors, volume factors, funding rate factors, and momentum factors.

Key Features:
- Unified factor interface with standardized parameters
- Automatic data format normalization and missing value handling
- Configurable factor categories and parameters
- Support for crypto market characteristics (24/7 trading, high volatility)
- Integration with qlib's factor computation framework

Author: CryptoAlpha Development Team
License: MIT
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings

from qlib.data.dataset.loader import QlibDataLoader
from qlib.contrib.data.crypto_loader import (
    _get_basic_factors,
    _get_decline_factors, 
    _get_volume_factors,
    _get_momentum_factors,
    _get_funding_factors
)


class FactorCategory(Enum):
    """Enumeration of available factor categories."""
    BASIC = "basic"
    DECLINE = "decline"
    VOLUME = "volume"
    MOMENTUM = "momentum"
    FUNDING = "funding"


class NormalizationMethod(Enum):
    """Enumeration of data normalization methods."""
    NONE = "none"
    ZSCORE = "zscore"
    MINMAX = "minmax"
    RANK = "rank"
    QUANTILE = "quantile"


@dataclass
class FactorConfig:
    """Configuration class for cryptocurrency factors."""
    
    # Factor categories to include
    categories: List[FactorCategory] = field(default_factory=lambda: [
        FactorCategory.BASIC,
        FactorCategory.DECLINE,
        FactorCategory.VOLUME,
        FactorCategory.MOMENTUM
    ])
    
    # Data processing settings
    normalization: NormalizationMethod = NormalizationMethod.ZSCORE
    handle_missing: str = "forward_fill"  # forward_fill, backward_fill, interpolate, drop, zero
    outlier_treatment: str = "winsorize"  # winsorize, clip, remove, none
    outlier_threshold: float = 0.05  # percentile threshold for outlier treatment
    
    # Factor-specific parameters
    basic_params: Dict[str, Any] = field(default_factory=dict)
    decline_params: Dict[str, Any] = field(default_factory=dict)
    volume_params: Dict[str, Any] = field(default_factory=dict)
    momentum_params: Dict[str, Any] = field(default_factory=dict)
    funding_params: Dict[str, Any] = field(default_factory=dict)
    
    # Performance optimization
    parallel_computation: bool = True
    cache_factors: bool = True
    
    # Validation settings
    validate_expressions: bool = True
    min_data_points: int = 100
    
    # Crypto-specific settings
    timezone: str = "UTC"
    trading_calendar: str = "24/7"  # 24/7, business_days
    market_type: str = "spot"  # spot, futures, perpetual
    min_volume_filter: float = 0.0  # minimum volume threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "categories": [cat.value for cat in self.categories],
            "normalization": self.normalization.value,
            "handle_missing": self.handle_missing,
            "outlier_treatment": self.outlier_treatment,
            "outlier_threshold": self.outlier_threshold,
            "basic_params": self.basic_params,
            "decline_params": self.decline_params,
            "volume_params": self.volume_params,
            "momentum_params": self.momentum_params,
            "funding_params": self.funding_params,
            "parallel_computation": self.parallel_computation,
            "cache_factors": self.cache_factors,
            "validate_expressions": self.validate_expressions,
            "min_data_points": self.min_data_points,
            "timezone": self.timezone,
            "trading_calendar": self.trading_calendar,
            "min_volume_filter": self.min_volume_filter
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'FactorConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        if "categories" in config_dict:
            config.categories = [FactorCategory(cat) for cat in config_dict["categories"]]
        if "normalization" in config_dict:
            config.normalization = NormalizationMethod(config_dict["normalization"])
            
        # Update other fields
        for key, value in config_dict.items():
            if hasattr(config, key) and key not in ["categories", "normalization"]:
                setattr(config, key, value)
                
        return config


class CryptoFactorLibrary:
    """
    Unified cryptocurrency factor library with standardized interface.
    
    This class provides a comprehensive solution for cryptocurrency factor computation,
    including automatic data preprocessing, normalization, and missing value handling.
    """
    
    def __init__(self, config: Optional[FactorConfig] = None):
        """
        Initialize the cryptocurrency factor library.
        
        Parameters
        ----------
        config : FactorConfig, optional
            Configuration for factor computation. If None, uses default configuration.
        """
        self.config = config or FactorConfig()
        self._factor_cache = {}
        self._expression_cache = {}
        
        # Initialize factor generators
        self._generators = {
            FactorCategory.BASIC: _get_basic_factors,
            FactorCategory.DECLINE: _get_decline_factors,
            FactorCategory.VOLUME: _get_volume_factors,
            FactorCategory.MOMENTUM: _get_momentum_factors,
            FactorCategory.FUNDING: _get_funding_factors
        }
    
    def get_factor_expressions(self, 
                             categories: Optional[List[FactorCategory]] = None) -> Tuple[List[str], List[str]]:
        """
        Get factor expressions for specified categories, filtered by market type.
        
        Parameters
        ----------
        categories : List[FactorCategory], optional
            List of factor categories to include. If None, uses config categories.
            
        Returns
        -------
        Tuple[List[str], List[str]]
            Tuple of (expressions, names) for the requested factors.
        """
        if categories is None:
            categories = self.config.categories
        
        # Filter categories based on market type
        categories = self._filter_categories_by_market_type(categories)
            
        cache_key = tuple(sorted([cat.value for cat in categories]))
        if self.config.cache_factors and cache_key in self._expression_cache:
            return self._expression_cache[cache_key]
        
        all_expressions = []
        all_names = []
        
        for category in categories:
            if category in self._generators:
                expressions, names = self._generators[category]()
                all_expressions.extend(expressions)
                all_names.extend(names)
        
        # Validate expressions if requested
        if self.config.validate_expressions:
            all_expressions, all_names = self._validate_expressions(all_expressions, all_names)
        
        result = (all_expressions, all_names)
        if self.config.cache_factors:
            self._expression_cache[cache_key] = result
            
        return result
    
    def _filter_categories_by_market_type(self, categories: List[FactorCategory]) -> List[FactorCategory]:
        """Filter factor categories based on market type availability."""
        filtered_categories = []
        
        for category in categories:
            # FUNDING factors are only available for perpetual/futures markets
            if category == FactorCategory.FUNDING and self.config.market_type == "spot":
                continue  # Skip funding factors for spot markets
            filtered_categories.append(category)
        
        return filtered_categories
    
    def get_factor_config_dict(self, 
                             categories: Optional[List[FactorCategory]] = None) -> Dict[str, Dict]:
        """
        Get factor configuration dictionary for qlib DataLoader.
        
        Parameters
        ----------
        categories : List[FactorCategory], optional
            List of factor categories to include.
            
        Returns
        -------
        Dict[str, Dict]
            Configuration dictionary compatible with qlib DataLoader.
        """
        if categories is None:
            categories = self.config.categories
            
        config_dict = {}
        for category in categories:
            config_dict[category.value] = getattr(self.config, f"{category.value}_params", {})
            
        return config_dict
    
    def compute_factors(self, 
                       data: pd.DataFrame,
                       categories: Optional[List[FactorCategory]] = None,
                       normalize: bool = True) -> pd.DataFrame:
        """
        Compute cryptocurrency factors from price/volume data.
        
        Parameters
        ----------
        data : pd.DataFrame
            Input data with columns: open, high, low, close, volume
            Index should be DatetimeIndex
        categories : List[FactorCategory], optional
            Factor categories to compute
        normalize : bool, default True
            Whether to apply normalization and preprocessing
            
        Returns
        -------
        pd.DataFrame
            Computed factors with standardized format
        """
        if len(data) < self.config.min_data_points:
            warnings.warn(f"Insufficient data points: {len(data)} < {self.config.min_data_points}")
        
        # Get expressions
        expressions, names = self.get_factor_expressions(categories)
        
        # Simulate factor computation (in real implementation, this would use qlib's expression engine)
        factors_df = self._simulate_factor_computation(data, expressions, names)
        
        if normalize:
            factors_df = self._preprocess_factors(factors_df)
            
        return factors_df
    
    def get_factor_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all available factors.
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Metadata dictionary with factor information
        """
        metadata = {}
        
        for category in FactorCategory:
            if category in self._generators:
                expressions, names = self._generators[category]()
                
                category_metadata = {
                    "category": category.value,
                    "count": len(names),
                    "factors": names,
                    "description": self._get_category_description(category)
                }
                metadata[category.value] = category_metadata
                
        return metadata
    
    def validate_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate input data for factor computation.
        
        Parameters
        ----------
        data : pd.DataFrame
            Input data to validate
            
        Returns
        -------
        Dict[str, Any]
            Validation results and recommendations
        """
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Missing required columns: {missing_columns}")
        
        # Check market-type specific fields
        if self.config.market_type in {"perpetual", "futures"}:
            if FactorCategory.FUNDING in self.config.categories:
                if 'funding_rate' not in data.columns:
                    validation_results["warnings"].append(
                        f"Funding factors requested but 'funding_rate' field not available for {self.config.market_type} market")
                    validation_results["recommendations"].append(
                        "Consider removing FUNDING category or switching to perpetual/futures data source")
        elif self.config.market_type == "spot":
            if FactorCategory.FUNDING in self.config.categories:
                validation_results["warnings"].append(
                    "Funding factors requested but not available for spot markets")
                validation_results["recommendations"].append(
                    "Funding factors will be automatically excluded for spot markets")
        
        # Check data quality
        if len(data) < self.config.min_data_points:
            validation_results["warnings"].append(
                f"Data length {len(data)} is below recommended minimum {self.config.min_data_points}")
        
        # Check for missing values
        missing_pct = (data.isnull().sum() / len(data) * 100).round(2)
        high_missing = missing_pct[missing_pct > 10]
        if not high_missing.empty:
            validation_results["warnings"].append(
                f"High missing value percentages: {high_missing.to_dict()}")
        
        # Check volume filter
        if self.config.min_volume_filter > 0 and 'volume' in data.columns:
            low_volume_pct = (data['volume'] < self.config.min_volume_filter).mean() * 100
            if low_volume_pct > 20:
                validation_results["recommendations"].append(
                    f"Consider adjusting min_volume_filter: {low_volume_pct:.1f}% of data below threshold")
        
        return validation_results
    
    def _validate_expressions(self, expressions: List[str], names: List[str]) -> Tuple[List[str], List[str]]:
        """Validate factor expressions for syntax and completeness."""
        valid_expressions = []
        valid_names = []
        
        for expr, name in zip(expressions, names):
            # Basic validation (in real implementation, would use qlib's expression parser)
            if expr and name and isinstance(expr, str) and isinstance(name, str):
                valid_expressions.append(expr)
                valid_names.append(name)
            else:
                warnings.warn(f"Invalid expression or name: {name}")
        
        return valid_expressions, valid_names
    
    def _simulate_factor_computation(self, 
                                   data: pd.DataFrame, 
                                   expressions: List[str], 
                                   names: List[str]) -> pd.DataFrame:
        """
        Simulate factor computation (placeholder for real qlib computation).
        
        In real implementation, this would use qlib's expression engine.
        """
        # Create synthetic factor data for demonstration
        np.random.seed(42)
        n_samples = len(data)
        n_factors = len(names)
        
        # Generate realistic factor values based on price data
        factor_data = {}
        
        for i, name in enumerate(names):
            if 'RSI' in name:
                # RSI-like values (0-100)
                factor_data[name] = np.random.normal(50, 15, n_samples).clip(0, 100)
            elif 'MACD' in name:
                # MACD-like values
                factor_data[name] = np.random.normal(0, 0.1, n_samples)
            elif 'VOL' in name:
                # Volume-related factors
                factor_data[name] = np.random.lognormal(0, 1, n_samples)
            elif 'FUNDING' in name:
                # Funding rate factors (small values)
                factor_data[name] = np.random.normal(0, 0.001, n_samples)
            else:
                # General factors
                factor_data[name] = np.random.normal(0, 1, n_samples)
        
        factors_df = pd.DataFrame(factor_data, index=data.index)
        
        # Add some realistic missing values
        for col in factors_df.columns:
            missing_mask = np.random.random(len(factors_df)) < 0.02  # 2% missing
            factors_df.loc[missing_mask, col] = np.nan
            
        return factors_df
    
    def _preprocess_factors(self, factors_df: pd.DataFrame) -> pd.DataFrame:
        """Apply preprocessing pipeline to factor data."""
        processed_df = factors_df.copy()
        
        # Handle missing values
        processed_df = self._handle_missing_values(processed_df)
        
        # Handle outliers
        processed_df = self._handle_outliers(processed_df)
        
        # Apply normalization
        processed_df = self._normalize_factors(processed_df)
        
        return processed_df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values according to configuration."""
        method = self.config.handle_missing
        
        if method == "forward_fill":
            return df.fillna(method='ffill')
        elif method == "backward_fill":
            return df.fillna(method='bfill')
        elif method == "interpolate":
            return df.interpolate()
        elif method == "zero":
            return df.fillna(0)
        elif method == "drop":
            return df.dropna()
        else:
            return df
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle outliers according to configuration."""
        method = self.config.outlier_treatment
        threshold = self.config.outlier_threshold
        
        if method == "none":
            return df
        
        processed_df = df.copy()
        
        for col in processed_df.columns:
            if method == "winsorize":
                lower = processed_df[col].quantile(threshold)
                upper = processed_df[col].quantile(1 - threshold)
                processed_df[col] = processed_df[col].clip(lower, upper)
            elif method == "clip":
                q99 = processed_df[col].quantile(0.99)
                q1 = processed_df[col].quantile(0.01)
                processed_df[col] = processed_df[col].clip(q1, q99)
            elif method == "remove":
                lower = processed_df[col].quantile(threshold)
                upper = processed_df[col].quantile(1 - threshold)
                mask = (processed_df[col] >= lower) & (processed_df[col] <= upper)
                processed_df.loc[~mask, col] = np.nan
        
        return processed_df
    
    def _normalize_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize factors according to configuration."""
        method = self.config.normalization
        
        if method == NormalizationMethod.NONE:
            return df
        
        normalized_df = df.copy()
        
        for col in normalized_df.columns:
            if method == NormalizationMethod.ZSCORE:
                mean_val = normalized_df[col].mean()
                std_val = normalized_df[col].std()
                if std_val > 0:
                    normalized_df[col] = (normalized_df[col] - mean_val) / std_val
            elif method == NormalizationMethod.MINMAX:
                min_val = normalized_df[col].min()
                max_val = normalized_df[col].max()
                if max_val > min_val:
                    normalized_df[col] = (normalized_df[col] - min_val) / (max_val - min_val)
            elif method == NormalizationMethod.RANK:
                normalized_df[col] = normalized_df[col].rank(pct=True)
            elif method == NormalizationMethod.QUANTILE:
                normalized_df[col] = normalized_df[col].rank(pct=True) * 2 - 1
        
        return normalized_df
    
    def _get_category_description(self, category: FactorCategory) -> str:
        """Get description for factor category."""
        descriptions = {
            FactorCategory.BASIC: "Basic price and volume factors including K-bar patterns",
            FactorCategory.DECLINE: "Multi-timeframe decline and drawdown factors for crypto markets",
            FactorCategory.VOLUME: "Volume anomaly detection and volume-price divergence factors",
            FactorCategory.MOMENTUM: "Advanced momentum factors with downward trend and rebound analysis",
            FactorCategory.FUNDING: "Funding rate factors for perpetual futures markets"
        }
        return descriptions.get(category, "No description available")


class CryptoFactorDataLoader(QlibDataLoader):
    """
    Enhanced DataLoader for cryptocurrency factors with integrated preprocessing.
    
    This class extends qlib's QlibDataLoader to provide cryptocurrency-specific
    factor computation and preprocessing capabilities.
    """
    
    def __init__(self, factor_config: Optional[FactorConfig] = None, **kwargs):
        """
        Initialize the CryptoFactorDataLoader.
        
        Parameters
        ----------
        factor_config : FactorConfig, optional
            Configuration for factor computation
        **kwargs
            Additional arguments passed to QlibDataLoader
        """
        self.factor_lib = CryptoFactorLibrary(factor_config)
        
        # Generate factor configuration for qlib
        expressions, names = self.factor_lib.get_factor_expressions()
        
        # QlibDataLoader expects (expressions, names) tuple directly
        factor_config = (expressions, names)
        
        # Handle user-provided config separately
        user_config = kwargs.pop("config", {})
        
        super().__init__(config=factor_config, **kwargs)
    
    def get_factor_metadata(self) -> Dict[str, Any]:
        """Get comprehensive factor metadata."""
        return self.factor_lib.get_factor_metadata()
    
    def validate_data_source(self, instruments: List[str], start_time: str, end_time: str) -> Dict[str, Any]:
        """Validate data source for factor computation."""
        # This would integrate with qlib's data validation in real implementation
        return {
            "status": "validation_placeholder",
            "instruments": len(instruments),
            "time_range": f"{start_time} to {end_time}",
            "recommendations": ["Ensure funding rate data is available for funding factors"]
        }


# Convenience functions for backward compatibility and easy usage

def get_crypto_factor_expressions(categories: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
    """
    Get cryptocurrency factor expressions.
    
    Parameters
    ----------
    categories : List[str], optional
        List of category names. If None, returns all categories.
        
    Returns
    -------
    Tuple[List[str], List[str]]
        Tuple of (expressions, names)
    """
    if categories is None:
        factor_categories = [FactorCategory.BASIC, FactorCategory.DECLINE, 
                           FactorCategory.VOLUME, FactorCategory.MOMENTUM]
    else:
        factor_categories = [FactorCategory(cat) for cat in categories]
    
    factory = CryptoFactorLibrary()
    return factory.get_factor_expressions(factor_categories)


def create_crypto_factor_config(normalization: str = "zscore",
                               handle_missing: str = "forward_fill",
                               outlier_treatment: str = "winsorize",
                               categories: Optional[List[str]] = None) -> FactorConfig:
    """
    Create a cryptocurrency factor configuration with common settings.
    
    Parameters
    ----------
    normalization : str, default "zscore"
        Normalization method
    handle_missing : str, default "forward_fill"
        Missing value handling method
    outlier_treatment : str, default "winsorize"
        Outlier treatment method
    categories : List[str], optional
        Factor categories to include
        
    Returns
    -------
    FactorConfig
        Configured factor settings
    """
    config = FactorConfig()
    config.normalization = NormalizationMethod(normalization)
    config.handle_missing = handle_missing
    config.outlier_treatment = outlier_treatment
    
    if categories is not None:
        config.categories = [FactorCategory(cat) for cat in categories]
    
    return config


# Export key classes and functions
__all__ = [
    'CryptoFactorLibrary',
    'CryptoFactorDataLoader', 
    'FactorConfig',
    'FactorCategory',
    'NormalizationMethod',
    'get_crypto_factor_expressions',
    'create_crypto_factor_config'
]