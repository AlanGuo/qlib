# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Conflict resolution for incremental data collection.

This module handles conflicts that arise when collecting overlapping data,
such as duplicate timestamps, data quality differences, and merge strategies.
"""

from abc import ABC, abstractmethod
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import pandas as pd
import numpy as np
import logging


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving data conflicts."""
    KEEP_LATEST = "keep_latest"
    KEEP_OLDEST = "keep_oldest"
    KEEP_BEST_QUALITY = "keep_best_quality"
    MERGE_AVERAGE = "merge_average"
    MERGE_WEIGHTED = "merge_weighted"
    KEEP_BOTH = "keep_both"


class DataQualityMetrics:
    """Metrics for evaluating data quality."""
    
    @staticmethod
    def calculate_quality_score(data: pd.DataFrame) -> float:
        """
        Calculate a quality score for a data chunk.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Quality score between 0 and 1 (higher is better)
        """
        if data.empty:
            return 0.0
        
        score = 1.0
        
        # Check for missing values
        missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))
        score -= missing_ratio * 0.3
        
        # Check for zero volumes (suspicious)
        if 'volume' in data.columns:
            zero_volume_ratio = (data['volume'] == 0).sum() / len(data)
            score -= zero_volume_ratio * 0.2
        
        # Check for price consistency (OHLC relationships)
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            # High should be >= max(open, close) and low should be <= min(open, close)
            invalid_high = (data['high'] < data[['open', 'close']].max(axis=1)).sum()
            invalid_low = (data['low'] > data[['open', 'close']].min(axis=1)).sum()
            invalid_ratio = (invalid_high + invalid_low) / (len(data) * 2)
            score -= invalid_ratio * 0.3
        
        # Check for extreme price movements (potential errors)
        if 'close' in data.columns and len(data) > 1:
            price_changes = data['close'].pct_change().abs()
            extreme_changes = (price_changes > 0.5).sum()  # >50% change
            extreme_ratio = extreme_changes / len(data)
            score -= extreme_ratio * 0.2
        
        return max(0.0, score)
    
    @staticmethod
    def compare_data_quality(data1: pd.DataFrame, data2: pd.DataFrame) -> int:
        """
        Compare quality of two data chunks.
        
        Returns:
            -1 if data1 is better, 1 if data2 is better, 0 if equal
        """
        score1 = DataQualityMetrics.calculate_quality_score(data1)
        score2 = DataQualityMetrics.calculate_quality_score(data2)
        
        if abs(score1 - score2) < 0.01:  # Very close scores
            return 0
        elif score1 > score2:
            return -1
        else:
            return 1


class ConflictResolver(ABC):
    """Abstract base class for conflict resolution."""
    
    def __init__(self, strategy: ConflictResolutionStrategy):
        """Initialize conflict resolver."""
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def resolve_conflict(self, 
                        existing_data: pd.DataFrame,
                        new_data: pd.DataFrame,
                        overlap_start: datetime,
                        overlap_end: datetime) -> pd.DataFrame:
        """Resolve conflict between existing and new data."""
        pass


class DefaultConflictResolver(ConflictResolver):
    """Default implementation of conflict resolver."""
    
    def __init__(self, 
                 strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.KEEP_LATEST,
                 quality_threshold: float = 0.1):
        """
        Initialize default conflict resolver.
        
        Args:
            strategy: Resolution strategy to use
            quality_threshold: Minimum quality difference to prefer one dataset
        """
        super().__init__(strategy)
        self.quality_threshold = quality_threshold
    
    def resolve_conflict(self, 
                        existing_data: pd.DataFrame,
                        new_data: pd.DataFrame,
                        overlap_start: datetime,
                        overlap_end: datetime) -> pd.DataFrame:
        """Resolve conflict between existing and new data."""
        
        if existing_data.empty:
            return new_data
        
        if new_data.empty:
            return existing_data
        
        # Find overlapping data
        existing_overlap = self._get_overlap_data(existing_data, overlap_start, overlap_end)
        new_overlap = self._get_overlap_data(new_data, overlap_start, overlap_end)
        
        if existing_overlap.empty and new_overlap.empty:
            # No actual overlap, just concatenate
            return self._merge_non_overlapping(existing_data, new_data)
        
        # Apply resolution strategy
        if self.strategy == ConflictResolutionStrategy.KEEP_LATEST:
            return self._resolve_keep_latest(existing_data, new_data, existing_overlap, new_overlap)
        
        elif self.strategy == ConflictResolutionStrategy.KEEP_OLDEST:
            return self._resolve_keep_oldest(existing_data, new_data, existing_overlap, new_overlap)
        
        elif self.strategy == ConflictResolutionStrategy.KEEP_BEST_QUALITY:
            return self._resolve_keep_best_quality(existing_data, new_data, existing_overlap, new_overlap)
        
        elif self.strategy == ConflictResolutionStrategy.MERGE_AVERAGE:
            return self._resolve_merge_average(existing_data, new_data, existing_overlap, new_overlap)
        
        elif self.strategy == ConflictResolutionStrategy.KEEP_BOTH:
            return self._resolve_keep_both(existing_data, new_data)
        
        else:
            # Default to keep latest
            return self._resolve_keep_latest(existing_data, new_data, existing_overlap, new_overlap)
    
    def _get_overlap_data(self, data: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
        """Get data within the overlap period."""
        if data.empty:
            return data
        
        # Assume index is datetime
        mask = (data.index >= start) & (data.index <= end)
        return data[mask]
    
    def _merge_non_overlapping(self, existing_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        """Merge data with no overlaps."""
        combined = pd.concat([existing_data, new_data])
        combined = combined.sort_index()
        return combined.drop_duplicates()
    
    def _resolve_keep_latest(self, existing_data: pd.DataFrame, new_data: pd.DataFrame,
                           existing_overlap: pd.DataFrame, new_overlap: pd.DataFrame) -> pd.DataFrame:
        """Keep the latest data in overlapping regions."""
        # Remove overlapping part from existing data
        non_overlap_existing = existing_data.drop(existing_overlap.index, errors='ignore')
        
        # Combine non-overlapping existing data with all new data
        result = pd.concat([non_overlap_existing, new_data])
        result = result.sort_index()
        return result.drop_duplicates()
    
    def _resolve_keep_oldest(self, existing_data: pd.DataFrame, new_data: pd.DataFrame,
                           existing_overlap: pd.DataFrame, new_overlap: pd.DataFrame) -> pd.DataFrame:
        """Keep the oldest data in overlapping regions."""
        # Remove overlapping part from new data
        non_overlap_new = new_data.drop(new_overlap.index, errors='ignore')
        
        # Combine all existing data with non-overlapping new data
        result = pd.concat([existing_data, non_overlap_new])
        result = result.sort_index()
        return result.drop_duplicates()
    
    def _resolve_keep_best_quality(self, existing_data: pd.DataFrame, new_data: pd.DataFrame,
                                 existing_overlap: pd.DataFrame, new_overlap: pd.DataFrame) -> pd.DataFrame:
        """Keep the best quality data in overlapping regions."""
        
        # Compare quality of overlapping sections
        quality_comparison = DataQualityMetrics.compare_data_quality(existing_overlap, new_overlap)
        
        if quality_comparison <= 0:  # Existing is better or equal
            return self._resolve_keep_oldest(existing_data, new_data, existing_overlap, new_overlap)
        else:  # New is better
            return self._resolve_keep_latest(existing_data, new_data, existing_overlap, new_overlap)
    
    def _resolve_merge_average(self, existing_data: pd.DataFrame, new_data: pd.DataFrame,
                             existing_overlap: pd.DataFrame, new_overlap: pd.DataFrame) -> pd.DataFrame:
        """Merge overlapping data by averaging numeric columns."""
        
        # Get non-overlapping parts
        non_overlap_existing = existing_data.drop(existing_overlap.index, errors='ignore')
        non_overlap_new = new_data.drop(new_overlap.index, errors='ignore')
        
        # Merge overlapping parts by averaging
        if not existing_overlap.empty and not new_overlap.empty:
            # Align the overlapping data
            aligned_existing, aligned_new = existing_overlap.align(new_overlap, join='outer')
            
            # Average numeric columns
            numeric_cols = aligned_existing.select_dtypes(include=[np.number]).columns
            merged_overlap = aligned_existing.copy()
            
            for col in numeric_cols:
                # Average where both have data
                both_have_data = aligned_existing[col].notna() & aligned_new[col].notna()
                merged_overlap.loc[both_have_data, col] = (
                    aligned_existing.loc[both_have_data, col] + 
                    aligned_new.loc[both_have_data, col]
                ) / 2
                
                # Use new data where existing is missing
                existing_missing = aligned_existing[col].isna() & aligned_new[col].notna()
                merged_overlap.loc[existing_missing, col] = aligned_new.loc[existing_missing, col]
        else:
            merged_overlap = pd.concat([existing_overlap, new_overlap])
        
        # Combine all parts
        result = pd.concat([non_overlap_existing, merged_overlap, non_overlap_new])
        result = result.sort_index()
        return result.drop_duplicates()
    
    def _resolve_keep_both(self, existing_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        """Keep both datasets (useful for debugging)."""
        # Add source column to distinguish data
        existing_with_source = existing_data.copy()
        existing_with_source['data_source'] = 'existing'
        
        new_with_source = new_data.copy()
        new_with_source['data_source'] = 'new'
        
        result = pd.concat([existing_with_source, new_with_source])
        return result.sort_index()


class ConflictDetector:
    """Detects conflicts in data collection."""
    
    def __init__(self):
        """Initialize conflict detector."""
        self.logger = logging.getLogger(__name__)
    
    def detect_overlaps(self, 
                       existing_data: pd.DataFrame,
                       new_data: pd.DataFrame) -> List[Tuple[datetime, datetime]]:
        """
        Detect overlapping time periods between existing and new data.
        
        Returns:
            List of (start, end) tuples representing overlap periods
        """
        if existing_data.empty or new_data.empty:
            return []
        
        existing_start = existing_data.index.min()
        existing_end = existing_data.index.max()
        new_start = new_data.index.min()
        new_end = new_data.index.max()
        
        # Check for overlap
        overlap_start = max(existing_start, new_start)
        overlap_end = min(existing_end, new_end)
        
        if overlap_start <= overlap_end:
            return [(overlap_start, overlap_end)]
        else:
            return []
    
    def analyze_conflicts(self, 
                         existing_data: pd.DataFrame,
                         new_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze conflicts between existing and new data.
        
        Returns:
            Dictionary with conflict analysis results
        """
        overlaps = self.detect_overlaps(existing_data, new_data)
        
        analysis = {
            'has_conflicts': len(overlaps) > 0,
            'overlap_periods': overlaps,
            'total_overlap_duration': timedelta(0),
            'existing_data_points': len(existing_data),
            'new_data_points': len(new_data),
            'overlap_data_points': 0,
            'quality_comparison': None
        }
        
        if overlaps:
            # Calculate total overlap duration
            total_duration = sum(
                (end - start for start, end in overlaps),
                timedelta(0)
            )
            analysis['total_overlap_duration'] = total_duration
            
            # Count overlapping data points
            for start, end in overlaps:
                existing_overlap = existing_data[(existing_data.index >= start) & 
                                               (existing_data.index <= end)]
                new_overlap = new_data[(new_data.index >= start) & 
                                     (new_data.index <= end)]
                
                analysis['overlap_data_points'] += len(existing_overlap) + len(new_overlap)
                
                # Compare quality
                if not existing_overlap.empty and not new_overlap.empty:
                    quality_comparison = DataQualityMetrics.compare_data_quality(
                        existing_overlap, new_overlap
                    )
                    analysis['quality_comparison'] = quality_comparison
        
        return analysis


# Utility functions for common conflict scenarios
def resolve_simple_overlap(existing_data: pd.DataFrame,
                          new_data: pd.DataFrame,
                          strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.KEEP_LATEST) -> pd.DataFrame:
    """
    Simple utility function to resolve data overlap.
    
    Args:
        existing_data: Existing data DataFrame
        new_data: New data DataFrame
        strategy: Resolution strategy
        
    Returns:
        Merged DataFrame with conflicts resolved
    """
    detector = ConflictDetector()
    overlaps = detector.detect_overlaps(existing_data, new_data)
    
    if not overlaps:
        # No conflicts, simple concatenation
        result = pd.concat([existing_data, new_data])
        return result.sort_index().drop_duplicates()
    
    # Use resolver for conflicts
    resolver = DefaultConflictResolver(strategy)
    overlap_start, overlap_end = overlaps[0]  # Use first overlap
    
    return resolver.resolve_conflict(existing_data, new_data, overlap_start, overlap_end)
