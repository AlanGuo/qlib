# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Configuration for cryptocurrency data validation.

This module provides configuration classes for customizing validation
parameters and behavior.
"""

from dataclasses import dataclass, field

from typing import List, Optional


@dataclass
class ValidationConfig:
    """
    Configuration for cryptocurrency data validation.
    
    This class contains all configurable parameters for the validation process,
    allowing users to customize validation behavior for different use cases.
    """
    
    # General validation settings
    enable_price_validation: bool = True
    enable_volume_validation: bool = True
    enable_timeseries_validation: bool = True
    enable_consistency_validation: bool = True
    enable_anomaly_detection: bool = True
    
    # Required and optional fields
    required_fields: List[str] = field(default_factory=lambda: [
        'open', 'high', 'low', 'close', 'volume'
    ])
    optional_fields: List[str] = field(default_factory=lambda: [
        'volume_24h', 'volume_usd_24h', 'change_24h', 'funding_rate',
        'open_interest', 'bid_ask_spread', 'liquidation_data'
    ])
    
    # Completeness validation
    max_missing_ratio: float = 0.1  # 10% max missing values
    min_rows: int = 1
    
    # Price validation
    max_price_change_pct: float = 50.0  # 50% max price change
    price_outlier_threshold: float = 3.0  # Z-score threshold
    min_price: float = 0.0
    
    # Volume validation
    volume_outlier_threshold: float = 5.0  # Z-score threshold for volume
    min_volume: float = 0.0
    max_zero_volume_ratio: float = 0.1  # 10% max zero volume periods
    
    # Time series validation
    expected_interval_seconds: Optional[int] = None  # Auto-detect if None
    max_missing_periods_ratio: float = 0.05  # 5% max missing periods
    timestamp_column: str = 'timestamp'
    allow_duplicate_timestamps: bool = False
    
    # Consistency validation
    consistency_tolerance: float = 0.01  # 1% tolerance for numerical comparisons
    funding_rate_range: List[float] = field(default_factory=lambda: [-0.01, 0.01])  # -1% to 1%
    change_24h_range: List[float] = field(default_factory=lambda: [-100.0, 1000.0])  # -100% to 1000%
    
    # Anomaly detection
    anomaly_z_score_threshold: float = 3.0
    anomaly_iqr_multiplier: float = 1.5
    price_spike_threshold: float = 0.2  # 20% price spike
    volume_spike_threshold: float = 5.0  # 5x volume spike
    min_data_points_for_anomaly: int = 30
    
    @classmethod
    def create_strict_config(cls) -> 'ValidationConfig':
        """
        Create a strict validation configuration.
        
        Returns
        -------
        ValidationConfig
            Configuration with strict validation parameters
        """
        return cls(
            max_missing_ratio=0.05,  # 5% max missing
            max_price_change_pct=20.0,  # 20% max price change
            price_outlier_threshold=2.5,  # Lower threshold
            volume_outlier_threshold=3.0,  # Lower threshold
            max_zero_volume_ratio=0.05,  # 5% max zero volume
            max_missing_periods_ratio=0.02,  # 2% max missing periods
            consistency_tolerance=0.005,  # 0.5% tolerance
            anomaly_z_score_threshold=2.5,  # Lower threshold
            price_spike_threshold=0.1,  # 10% price spike
            volume_spike_threshold=3.0,  # 3x volume spike
        )
    
    @classmethod
    def create_lenient_config(cls) -> 'ValidationConfig':
        """
        Create a lenient validation configuration.
        
        Returns
        -------
        ValidationConfig
            Configuration with lenient validation parameters
        """
        return cls(
            max_missing_ratio=0.2,  # 20% max missing
            max_price_change_pct=100.0,  # 100% max price change
            price_outlier_threshold=4.0,  # Higher threshold
            volume_outlier_threshold=6.0,  # Higher threshold
            max_zero_volume_ratio=0.2,  # 20% max zero volume
            max_missing_periods_ratio=0.1,  # 10% max missing periods
            consistency_tolerance=0.05,  # 5% tolerance
            anomaly_z_score_threshold=4.0,  # Higher threshold
            price_spike_threshold=0.5,  # 50% price spike
            volume_spike_threshold=10.0,  # 10x volume spike
        )
    
    @classmethod
    def create_crypto_specific_config(cls) -> 'ValidationConfig':
        """
        Create a configuration optimized for cryptocurrency data.
        
        Returns
        -------
        ValidationConfig
            Configuration optimized for crypto market characteristics
        """
        return cls(
            required_fields=['open', 'high', 'low', 'close', 'volume'],
            optional_fields=[
                'volume_24h', 'volume_usd_24h', 'change_24h', 'funding_rate',
                'open_interest', 'bid_ask_spread', 'liquidation_data',
                'mark_price', 'index_price', 'premium_index'
            ],
            max_missing_ratio=0.1,
            max_price_change_pct=50.0,  # Crypto can be volatile
            price_outlier_threshold=3.5,
            volume_outlier_threshold=5.0,
            max_zero_volume_ratio=0.05,  # Low tolerance for zero volume
            funding_rate_range=(-0.02, 0.02),  # -2% to 2% for crypto
            change_24h_range=(-90.0, 2000.0),  # Wider range for crypto
            price_spike_threshold=0.3,  # 30% spike threshold
            volume_spike_threshold=8.0,  # 8x volume spike
        )
    
    @classmethod
    def create_high_frequency_config(cls) -> 'ValidationConfig':
        """
        Create a configuration for high-frequency data validation.
        
        Returns
        -------
        ValidationConfig
            Configuration optimized for high-frequency trading data
        """
        return cls(
            max_missing_ratio=0.02,  # Very low tolerance for missing data
            max_price_change_pct=5.0,  # Lower price change tolerance
            price_outlier_threshold=2.0,  # Stricter outlier detection
            volume_outlier_threshold=3.0,
            max_zero_volume_ratio=0.1,
            max_missing_periods_ratio=0.01,  # Very low tolerance for gaps
            allow_duplicate_timestamps=False,  # Strict timestamp uniqueness
            consistency_tolerance=0.001,  # Very tight tolerance
            anomaly_z_score_threshold=2.0,  # Stricter anomaly detection
            price_spike_threshold=0.05,  # 5% spike threshold
            volume_spike_threshold=5.0,
            min_data_points_for_anomaly=100,  # More data needed for HF
        )
    
    @classmethod
    def create_daily_config(cls) -> 'ValidationConfig':
        """
        Create a configuration for daily data validation.
        
        Returns
        -------
        ValidationConfig
            Configuration optimized for daily trading data
        """
        return cls(
            max_missing_ratio=0.05,  # 5% tolerance for daily data
            max_price_change_pct=30.0,  # 30% daily change tolerance
            price_outlier_threshold=3.0,
            volume_outlier_threshold=4.0,
            max_zero_volume_ratio=0.02,  # Very low tolerance for zero volume
            expected_interval_seconds=86400,  # 24 hours
            max_missing_periods_ratio=0.05,  # 5% missing days tolerance
            consistency_tolerance=0.01,
            price_spike_threshold=0.25,  # 25% daily spike
            volume_spike_threshold=6.0,
            min_data_points_for_anomaly=30,  # 30 days minimum
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'ValidationConfig':
        """Create configuration from dictionary."""
        # Filter out unknown fields
        valid_fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in config_dict.items() if k in valid_fields}
        return cls(**filtered_dict)
    
    def update(self, **kwargs) -> 'ValidationConfig':
        """
        Create a new configuration with updated parameters.
        
        Parameters
        ----------
        **kwargs
            Parameters to update
        
        Returns
        -------
        ValidationConfig
            New configuration with updated parameters
        """
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        return self.from_dict(config_dict)
