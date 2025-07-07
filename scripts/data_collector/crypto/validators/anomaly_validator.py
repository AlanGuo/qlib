# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Anomaly validator for cryptocurrency data validation.

This module provides validation for detecting anomalies and outliers
in cryptocurrency market data using statistical methods.
"""

import time

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from scipy import stats

from validators.base_validator import BaseValidator, ValidationResult, ValidationIssue, ValidationSeverity


class AnomalyValidator(BaseValidator):
    """
    Validator for detecting anomalies in market data.
    
    Validates:
    - Statistical outliers using Z-score and IQR methods
    - Price spike detection
    - Volume anomalies
    - Market microstructure anomalies
    """
    
    def __init__(
        self, 
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        price_spike_threshold: float = 0.2,  # 20% price spike
        volume_spike_threshold: float = 5.0,  # 5x volume spike
        min_data_points: int = 30,
        name: Optional[str] = None
    ):
        """
        Initialize the anomaly validator.
        
        Parameters
        ----------
        z_score_threshold : float, default 3.0
            Z-score threshold for outlier detection
        iqr_multiplier : float, default 1.5
            IQR multiplier for outlier detection
        price_spike_threshold : float, default 0.2
            Threshold for detecting price spikes (20%)
        volume_spike_threshold : float, default 5.0
            Threshold for detecting volume spikes (5x normal)
        min_data_points : int, default 30
            Minimum number of data points required for anomaly detection
        name : str, optional
            Name of the validator
        """
        super().__init__(name)
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.price_spike_threshold = price_spike_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.min_data_points = min_data_points
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate data for anomalies.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame to validate
        
        Returns
        -------
        ValidationResult
            Validation result with any issues found
        """
        start_time = time.time()
        issues = []
        statistics = {}
        
        # Check if data is sufficient for anomaly detection
        if len(data) < self.min_data_points:
            issues.append(self._create_issue(
                ValidationSeverity.INFO,
                f"Insufficient data for anomaly detection: {len(data)} rows "
                f"(minimum required: {self.min_data_points})",
                details={'row_count': len(data), 'min_required': self.min_data_points}
            ))
            return ValidationResult(
                validator_name=self.name,
                is_valid=True,
                issues=issues,
                statistics={'row_count': len(data)},
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Detect price anomalies
        issues.extend(self._detect_price_anomalies(data))
        
        # Detect volume anomalies
        issues.extend(self._detect_volume_anomalies(data))
        
        # Detect price spikes
        issues.extend(self._detect_price_spikes(data))
        
        # Detect volume spikes
        issues.extend(self._detect_volume_spikes(data))
        
        # Detect statistical outliers
        issues.extend(self._detect_statistical_outliers(data))
        
        # Calculate statistics
        statistics = self._calculate_statistics(data)
        
        # Determine if validation passed (anomalies are warnings, not failures)
        is_valid = not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                          for issue in issues)
        
        return ValidationResult(
            validator_name=self.name,
            is_valid=is_valid,
            issues=issues,
            statistics=statistics,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def _detect_price_anomalies(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Detect price anomalies using statistical methods."""
        issues = []
        
        price_columns = ['open', 'high', 'low', 'close']
        
        for col in price_columns:
            if col in data.columns:
                prices = data[col].dropna()
                
                if len(prices) >= self.min_data_points:
                    # Z-score method
                    z_scores = pd.Series(np.abs(stats.zscore(prices)), index=prices.index)
                    outliers = prices[z_scores > self.z_score_threshold]
                    
                    for idx in outliers.index:
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"Price anomaly detected in {col} at index {idx}: "
                            f"{data.loc[idx, col]} (Z-score: {z_scores.loc[idx]:.2f})",
                            field_name=col,
                            row_index=idx,
                            value=data.loc[idx, col],
                            z_score=z_scores.loc[idx],
                            anomaly_type='statistical_outlier'
                        ))
        
        return issues
    
    def _detect_volume_anomalies(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Detect volume anomalies using statistical methods."""
        issues = []
        
        volume_columns = ['volume', 'volume_24h', 'volume_usd_24h']
        
        for col in volume_columns:
            if col in data.columns:
                volumes = data[col].dropna()
                
                # Remove zero volumes for analysis
                non_zero_volumes = volumes[volumes > 0]
                
                if len(non_zero_volumes) >= self.min_data_points:
                    # Use log transformation for volume data
                    log_volumes = np.log(non_zero_volumes)
                    z_scores = pd.Series(np.abs(stats.zscore(log_volumes)), index=non_zero_volumes.index)
                    outliers = non_zero_volumes[z_scores > self.z_score_threshold]
                    
                    for idx in outliers.index:
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"Volume anomaly detected in {col} at index {idx}: "
                            f"{data.loc[idx, col]} (Log Z-score: {z_scores.loc[idx]:.2f})",
                            field_name=col,
                            row_index=idx,
                            value=data.loc[idx, col],
                            log_z_score=z_scores.loc[idx],
                            anomaly_type='volume_outlier'
                        ))
        
        return issues
    
    def _detect_price_spikes(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Detect sudden price spikes."""
        issues = []
        
        if 'close' in data.columns and len(data) > 1:
            price_changes = data['close'].pct_change().abs()
            
            spikes = price_changes[price_changes > self.price_spike_threshold]
            
            for idx in spikes.index:
                if pd.notna(spikes.loc[idx]):
                    prev_idx = data.index[data.index.get_loc(idx) - 1]
                    issues.append(self._create_issue(
                        ValidationSeverity.WARNING,
                        f"Price spike detected at index {idx}: "
                        f"{spikes.loc[idx]:.2%} change "
                        f"(from {data.loc[prev_idx, 'close']} to {data.loc[idx, 'close']})",
                        field_name='close',
                        row_index=idx,
                        price_change=spikes.loc[idx],
                        prev_price=data.loc[prev_idx, 'close'],
                        current_price=data.loc[idx, 'close'],
                        anomaly_type='price_spike'
                    ))
        
        return issues
    
    def _detect_volume_spikes(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Detect sudden volume spikes."""
        issues = []
        
        if 'volume' in data.columns and len(data) > 1:
            volumes = data['volume']
            
            # Calculate rolling median volume (excluding current period)
            window_size = min(20, len(data) // 2)  # Use 20 periods or half the data
            if window_size >= 5:
                rolling_median = volumes.rolling(window=window_size, center=True).median()
                
                # Find volume spikes
                volume_ratios = volumes / rolling_median
                spikes = volume_ratios[volume_ratios > self.volume_spike_threshold]
                
                for idx in spikes.index:
                    if pd.notna(spikes.loc[idx]) and pd.notna(rolling_median.loc[idx]):
                        issues.append(self._create_issue(
                            ValidationSeverity.WARNING,
                            f"Volume spike detected at index {idx}: "
                            f"{volumes.loc[idx]} ({spikes.loc[idx]:.1f}x normal volume)",
                            field_name='volume',
                            row_index=idx,
                            volume=volumes.loc[idx],
                            normal_volume=rolling_median.loc[idx],
                            spike_ratio=spikes.loc[idx],
                            anomaly_type='volume_spike'
                        ))
        
        return issues
    
    def _detect_statistical_outliers(self, data: pd.DataFrame) -> List[ValidationIssue]:
        """Detect statistical outliers using IQR method."""
        issues = []
        
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            values = data[col].dropna()
            
            if len(values) >= self.min_data_points:
                # IQR method
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - self.iqr_multiplier * IQR
                upper_bound = Q3 + self.iqr_multiplier * IQR
                
                outliers = values[(values < lower_bound) | (values > upper_bound)]
                
                for idx in outliers.index:
                    bound_type = "lower" if values.loc[idx] < lower_bound else "upper"
                    bound_value = lower_bound if values.loc[idx] < lower_bound else upper_bound
                    
                    issues.append(self._create_issue(
                        ValidationSeverity.INFO,
                        f"Statistical outlier in {col} at index {idx}: "
                        f"{values.loc[idx]} (outside {bound_type} bound {bound_value:.4f})",
                        field_name=col,
                        row_index=idx,
                        value=values.loc[idx],
                        bound_type=bound_type,
                        bound_value=bound_value,
                        anomaly_type='iqr_outlier'
                    ))
        
        return issues
    
    def _calculate_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate anomaly detection statistics."""
        statistics = {
            'total_rows': len(data),
            'min_data_points_threshold': self.min_data_points,
            'sufficient_data': len(data) >= self.min_data_points
        }
        
        if len(data) >= self.min_data_points:
            # Price statistics
            if 'close' in data.columns:
                prices = data['close'].dropna()
                if len(prices) > 1:
                    price_changes = prices.pct_change().abs().dropna()
                    statistics['max_price_change'] = float(price_changes.max())
                    statistics['mean_price_change'] = float(price_changes.mean())
                    statistics['price_spikes_count'] = int((price_changes > self.price_spike_threshold).sum())
            
            # Volume statistics
            if 'volume' in data.columns:
                volumes = data['volume'].dropna()
                non_zero_volumes = volumes[volumes > 0]
                if len(non_zero_volumes) > 0:
                    statistics['max_volume'] = float(volumes.max())
                    statistics['mean_volume'] = float(non_zero_volumes.mean())
                    statistics['volume_coefficient_of_variation'] = float(
                        non_zero_volumes.std() / non_zero_volumes.mean()
                    )
            
            # Outlier counts by method
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            z_score_outliers = 0
            iqr_outliers = 0
            
            for col in numeric_columns:
                values = data[col].dropna()
                if len(values) >= self.min_data_points:
                    # Z-score outliers
                    z_scores = np.abs(stats.zscore(values))
                    z_score_outliers += (z_scores > self.z_score_threshold).sum()
                    
                    # IQR outliers
                    Q1 = values.quantile(0.25)
                    Q3 = values.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - self.iqr_multiplier * IQR
                    upper_bound = Q3 + self.iqr_multiplier * IQR
                    iqr_outliers += ((values < lower_bound) | (values > upper_bound)).sum()
            
            statistics['z_score_outliers_count'] = int(z_score_outliers)
            statistics['iqr_outliers_count'] = int(iqr_outliers)

        return statistics
