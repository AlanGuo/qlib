#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Real-time monitoring script for Phase 4.3 Stability Test

This script provides real-time monitoring of the stability test progress,
including data collection status, system health, and test metrics.
"""

import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
import subprocess

def get_test_data_dir():
    """Get the test data directory from environment variable."""
    return Path(os.environ.get('CRYPTO_TEST_DATA_DIR', './test_data/stability_test'))

def check_test_status():
    """Check if the stability test is running."""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        return 'test_long_term_stability.py' in result.stdout
    except:
        return False

def get_latest_log_entries(log_file, num_lines=10):
    """Get the latest log entries."""
    try:
        if log_file.exists():
            result = subprocess.run(['tail', f'-{num_lines}', str(log_file)], 
                                  capture_output=True, text=True)
            return result.stdout.strip().split('\n')
        return []
    except:
        return []

def parse_performance_log(log_file):
    """Parse performance metrics from log file."""
    metrics = {
        'latest_cpu': 'N/A',
        'latest_memory': 'N/A',
        'latest_collections': 'N/A',
        'latest_error_rate': 'N/A'
    }
    
    try:
        if log_file.exists():
            lines = get_latest_log_entries(log_file, 10)  # Get more lines to ensure we get the latest
            # Parse from the end to get the most recent data
            for line in reversed(lines):
                if 'CPU:' in line and 'Memory:' in line and 'Collections:' in line:
                    # Parse performance line: CPU: 11.4% | Memory: 572.6MB (1.6%) | Collections: 184.00/hr | Error Rate: 0.00%
                    try:
                        # Split by '|' and parse each part
                        parts = line.split('|')
                        for part in parts:
                            part = part.strip()
                            if 'CPU:' in part:
                                # Extract: "CPU: 11.4%" -> "11.4%"
                                cpu_part = part.split('CPU:')[1].strip()
                                metrics['latest_cpu'] = cpu_part
                            elif 'Memory:' in part:
                                # Extract: "Memory: 572.6MB (1.6%)" -> "572.6MB"
                                memory_part = part.split('Memory:')[1].strip()
                                if '(' in memory_part:
                                    memory_part = memory_part.split('(')[0].strip()
                                metrics['latest_memory'] = memory_part
                            elif 'Collections:' in part:
                                # Extract: "Collections: 184.00/hr" -> "184.00/hr"
                                collections_part = part.split('Collections:')[1].strip()
                                metrics['latest_collections'] = collections_part
                            elif 'Error Rate:' in part:
                                # Extract: "Error Rate: 0.00%" -> "0.00%"
                                error_part = part.split('Error Rate:')[1].strip()
                                metrics['latest_error_rate'] = error_part
                        break  # Use the first valid performance line found (which is the latest since we reversed)
                    except Exception as parse_error:
                        print(f"Error parsing performance line: {parse_error}")
                        continue
    except Exception as e:
        print(f"Error reading performance log: {e}")
    
    return metrics

def get_data_file_count(data_dir):
    """Count the number of data files collected."""
    count = 0
    try:
        crypto_data_dir = data_dir / 'crypto_data'
        if crypto_data_dir.exists():
            for timeframe_dir in crypto_data_dir.iterdir():
                if timeframe_dir.is_dir():
                    features_dir = timeframe_dir / 'features'
                    if features_dir.exists():
                        for instrument_dir in features_dir.iterdir():
                            if instrument_dir.is_dir():
                                count += len(list(instrument_dir.glob('*.bin')))
    except:
        pass
    return count

def display_status(test_data_dir):
    """Display current test status."""
    print("\033[2J\033[H")  # Clear screen and move cursor to top
    print("=" * 80)
    print("PHASE 4.3 LONG-TERM STABILITY TEST - REAL-TIME MONITOR")
    print("=" * 80)
    print(f"Monitor Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test Data Directory: {test_data_dir}")
    print()
    
    # Test status
    is_running = check_test_status()
    status_color = "\033[92m" if is_running else "\033[91m"  # Green if running, red if not
    print(f"Test Status: {status_color}{'RUNNING' if is_running else 'NOT RUNNING'}\033[0m")
    print()
    
    # Log files status
    log_dir = test_data_dir / 'logs'
    main_log = log_dir / 'stability_test.log'
    perf_log = log_dir / 'performance.log'
    error_log = log_dir / 'errors.log'
    
    print("Log Files:")
    print(f"  Main Log: {'✅' if main_log.exists() else '❌'} {main_log}")
    print(f"  Performance Log: {'✅' if perf_log.exists() else '❌'} {perf_log}")
    print(f"  Error Log: {'✅' if error_log.exists() else '❌'} {error_log}")
    print()
    
    # Performance metrics
    if perf_log.exists():
        metrics = parse_performance_log(perf_log)
        print("Latest Performance Metrics:")
        print(f"  CPU Usage: {metrics['latest_cpu']}")
        print(f"  Memory Usage: {metrics['latest_memory']}")
        print(f"  Collection Rate: {metrics['latest_collections']}")
        print(f"  Error Rate: {metrics['latest_error_rate']}")
        print()
    
    # Data collection status
    data_file_count = get_data_file_count(test_data_dir)
    print(f"Data Files Collected: {data_file_count}")
    print()
    
    # Recent log entries
    if main_log.exists():
        print("Recent Log Entries (last 5):")
        recent_logs = get_latest_log_entries(main_log, 5)
        for log_entry in recent_logs[-5:]:
            if log_entry.strip():
                # Color code log levels
                if 'ERROR' in log_entry:
                    print(f"  \033[91m{log_entry}\033[0m")  # Red for errors
                elif 'WARNING' in log_entry:
                    print(f"  \033[93m{log_entry}\033[0m")  # Yellow for warnings
                else:
                    print(f"  {log_entry}")
        print()
    
    # Error summary
    if error_log.exists() and error_log.stat().st_size > 0:
        error_count = len(get_latest_log_entries(error_log, 100))
        print(f"\033[91m⚠️  Recent Errors: {error_count} (check {error_log})\033[0m")
        print()
    
    # Test results
    results_file = test_data_dir / 'test_results.json'
    if results_file.exists():
        try:
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            print("Test Results Summary:")
            print(f"  Duration: {results.get('duration_hours', 'N/A'):.2f} hours")
            print(f"  Total Collections: {results.get('total_collections', 'N/A')}")
            print(f"  Success Rate: {(results.get('successful_collections', 0) / max(1, results.get('total_collections', 1)) * 100):.1f}%")
            print(f"  Average CPU: {results.get('avg_cpu_percent', 'N/A'):.1f}%")
            print(f"  Peak Memory: {results.get('peak_memory_mb', 'N/A'):.1f}MB")
            print()
        except:
            pass
    
    print("=" * 80)
    print("Press Ctrl+C to exit monitor")

def main():
    """Main monitoring loop."""
    parser = argparse.ArgumentParser(description="Monitor Phase 4.3 Stability Test")
    parser.add_argument('--refresh', type=int, default=10, 
                       help='Refresh interval in seconds (default: 10)')
    args = parser.parse_args()
    
    test_data_dir = get_test_data_dir()
    
    print(f"Starting monitor for test data directory: {test_data_dir}")
    print(f"Refresh interval: {args.refresh} seconds")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            display_status(test_data_dir)
            time.sleep(args.refresh)
    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user")

if __name__ == "__main__":
    main()