#!/usr/bin/env python3

"""
Test script to verify pagination logic in SimpleErrorLogCollector.
"""

from datetime import datetime
import sys
import os

# Add the crypto collector to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts/data_collector/crypto'))

from simple_error_log_collector import SimpleErrorLogCollector

def test_pagination_calculation():
    """Test the pagination calculation logic."""
    
    collector = SimpleErrorLogCollector()
    
    # Test case 1: 5 years of 1-hour data (should require pagination)
    start_time = datetime(2020, 1, 1)
    end_time = datetime(2024, 12, 31)
    
    # Calculate expected data points for 1h timeframe
    timeframe_hours = collector._get_timeframe_hours('1h')
    total_hours = (end_time - start_time).total_seconds() / 3600
    estimated_points = int(total_hours / timeframe_hours)
    
    print(f"📊 Test Case 1: 5 years of 1h data")
    print(f"   Timeframe hours: {timeframe_hours}")
    print(f"   Total hours: {total_hours:.1f}")
    print(f"   Estimated points: {estimated_points}")
    print(f"   Should require pagination: {estimated_points > 1000}")
    
    # Test case 2: 5 years of 1-day data (should require pagination)
    timeframe_hours = collector._get_timeframe_hours('1d')
    estimated_points_1d = int(total_hours / timeframe_hours)
    
    print(f"\n📊 Test Case 2: 5 years of 1d data")
    print(f"   Timeframe hours: {timeframe_hours}")
    print(f"   Estimated points: {estimated_points_1d}")
    print(f"   Should require pagination: {estimated_points_1d > 1000}")
    
    # Test case 3: 30 days of 1h data (should NOT require pagination)
    start_time_short = datetime(2024, 12, 1)
    end_time_short = datetime(2024, 12, 31)
    total_hours_short = (end_time_short - start_time_short).total_seconds() / 3600
    estimated_points_short = int(total_hours_short / collector._get_timeframe_hours('1h'))
    
    print(f"\n📊 Test Case 3: 30 days of 1h data")
    print(f"   Total hours: {total_hours_short:.1f}")
    print(f"   Estimated points: {estimated_points_short}")
    print(f"   Should require pagination: {estimated_points_short > 1000}")
    
    # Test timeframe conversion
    print(f"\n🔧 Timeframe conversion tests:")
    timeframes = ['1m', '5m', '1h', '1d', '1w']
    for tf in timeframes:
        hours = collector._get_timeframe_hours(tf)
        print(f"   {tf}: {hours} hours")

if __name__ == "__main__":
    test_pagination_calculation()