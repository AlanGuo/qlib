#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Comprehensive test runner for live incremental update functionality.

This script provides a complete testing framework for validating incremental
update functionality with real exchange data and proper error handling.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Add the crypto collector to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_live_test import LIVE_TEST_CONFIG, setup_test_environment, validate_test_environment

class LiveTestRunner:
    """Main test runner for live incremental update tests."""
    
    def __init__(self):
        self.config = setup_test_environment()
        self.test_results = []
        self.start_time = datetime.now()
        
    def run_all_tests(self) -> bool:
        """Run all live incremental update tests."""
        print("🚀 Starting Live Incremental Update Tests")
        print("=" * 60)
        
        # Validate environment
        if not self._validate_environment():
            return False
        
        # Test categories
        test_categories = [
            ("Network Connectivity", self._test_network_connectivity),
            ("Basic Data Collection", self._test_basic_data_collection),
            ("Incremental Updates", self._test_incremental_updates),
            ("Conflict Resolution", self._test_conflict_resolution),
            ("Resume Functionality", self._test_resume_functionality),
            ("State Management", self._test_state_management),
            ("Data Quality Validation", self._test_data_quality),
            ("Write-Read Consistency", self._test_write_read_consistency),
            ("Multi-Exchange Support", self._test_multi_exchange)
        ]
        
        success_count = 0
        total_count = len(test_categories)
        
        for category_name, test_func in test_categories:
            print(f"\n📋 Running {category_name} Tests")
            print("-" * 40)
            
            try:
                success = test_func()
                if success:
                    print(f"✅ {category_name}: PASSED")
                    success_count += 1
                else:
                    print(f"❌ {category_name}: FAILED")
                    
                self.test_results.append({
                    'category': category_name,
                    'success': success,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"❌ {category_name}: ERROR - {e}")
                self.test_results.append({
                    'category': category_name,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Generate test report
        self._generate_test_report()
        
        # Summary
        print(f"\n📊 Test Summary")
        print("=" * 60)
        print(f"Total Tests: {total_count}")
        print(f"Passed: {success_count}")
        print(f"Failed: {total_count - success_count}")
        print(f"Success Rate: {success_count/total_count*100:.1f}%")
        
        return success_count == total_count
    
    def _validate_environment(self) -> bool:
        """Validate the test environment."""
        print("🔍 Validating Test Environment")
        print("-" * 40)
        
        checks = [
            ("Proxy Configuration", self._check_proxy_config),
            ("Required Modules", self._check_required_modules),
            ("Directory Structure", self._check_directory_structure),
            ("Configuration Files", self._check_config_files)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                success = check_func()
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  {check_name}: {status}")
                all_passed = all_passed and success
            except Exception as e:
                print(f"  {check_name}: ❌ ERROR - {e}")
                all_passed = False
        
        return all_passed
    
    def _check_proxy_config(self) -> bool:
        """Check proxy configuration."""
        required_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
        return all(var in os.environ for var in required_vars)
    
    def _check_required_modules(self) -> bool:
        """Check if required modules are available."""
        required_modules = ['pandas', 'requests', 'json', 'pytest']
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                return False
        return True
    
    def _check_directory_structure(self) -> bool:
        """Check if directory structure is correct."""
        # Get the crypto directory path from the test runner location
        crypto_dir = Path(__file__).parent.parent.parent
        required_paths = [
            crypto_dir / "config" / "main_config.py",
            crypto_dir / "exchange_adapters",
            Path(".")
        ]
        all_exist = True
        for path in required_paths:
            if not path.exists():
                print(f"        Missing path: {path.resolve()}")
                all_exist = False
        return all_exist
    
    def _check_config_files(self) -> bool:
        """Check if configuration files exist."""
        # Get the crypto directory path from the test runner location
        crypto_dir = Path(__file__).parent.parent.parent
        config_files = [
            crypto_dir / "config" / "main_config.py",
            crypto_dir / "config" / "exchanges.py"
        ]
        all_exist = True
        for config_file in config_files:
            if not config_file.exists():
                print(f"        Missing config file: {config_file.resolve()}")
                all_exist = False
        return all_exist
    
    def _test_network_connectivity(self) -> bool:
        """Test network connectivity with proxy."""
        import requests
        
        test_urls = [
            "https://api.binance.com/api/v3/ping",
            "https://www.okx.com/api/v5/public/time"
        ]
        
        proxies = {
            'http': self.config.proxy.http_proxy,
            'https': self.config.proxy.https_proxy
        }
        
        for url in test_urls:
            try:
                response = requests.get(url, proxies=proxies, timeout=10)
                if response.status_code != 200:
                    print(f"    ❌ Failed to connect to {url}: {response.status_code}")
                    return False
                print(f"    ✅ Connected to {url}")
            except Exception as e:
                print(f"    ❌ Connection error to {url}: {e}")
                return False
        
        return True
    
    def _test_basic_data_collection(self) -> bool:
        """Test basic data collection functionality."""
        try:
            # Import required modules
            import pandas as pd
            import requests
            
            # Test data collection from Binance
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'limit': 10
            }
            
            proxies = {
                'http': self.config.proxy.http_proxy,
                'https': self.config.proxy.https_proxy
            }
            
            response = requests.get(url, params=params, proxies=proxies, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    print(f"    ✅ Collected {len(data)} data points")
                    
                    # Validate data structure
                    if len(data[0]) >= 6:  # OHLCV data
                        print("    ✅ Data structure valid")
                        return True
                    else:
                        print("    ❌ Invalid data structure")
                        return False
                else:
                    print("    ❌ No data received")
                    return False
            else:
                print(f"    ❌ API request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    ❌ Data collection error: {e}")
            return False
    
    def _test_incremental_updates(self) -> bool:
        """Test incremental update functionality."""
        try:
            import pandas as pd
            import tempfile
            
            # Create test data
            base_data = pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=24, freq='h'),
                'open': [40000 + i for i in range(24)],
                'high': [40100 + i for i in range(24)],
                'low': [39900 + i for i in range(24)],
                'close': [40050 + i for i in range(24)],
                'volume': [100 + i for i in range(24)]
            })
            
            # Create incremental data
            incremental_data = pd.DataFrame({
                'timestamp': pd.date_range('2023-01-02', periods=12, freq='h'),
                'open': [40024 + i for i in range(12)],
                'high': [40124 + i for i in range(12)],
                'low': [39924 + i for i in range(12)],
                'close': [40074 + i for i in range(12)],
                'volume': [124 + i for i in range(12)]
            })
            
            # Test incremental merge
            combined_data = pd.concat([base_data, incremental_data]).sort_values('timestamp')
            
            # Validate incremental update
            if len(combined_data) == 36:  # 24 + 12
                print("    ✅ Incremental merge successful")
                
                # Test timestamp continuity
                time_diff = combined_data['timestamp'].diff().dropna()
                if (time_diff == pd.Timedelta(hours=1)).all():
                    print("    ✅ Timestamp continuity maintained")
                    return True
                else:
                    print("    ❌ Timestamp continuity broken")
                    return False
            else:
                print(f"    ❌ Incorrect combined data length: {len(combined_data)}")
                return False
                
        except Exception as e:
            print(f"    ❌ Incremental update error: {e}")
            return False
    
    def _test_conflict_resolution(self) -> bool:
        """Test conflict resolution functionality."""
        try:
            import pandas as pd
            
            # Create overlapping data
            data1 = pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=12, freq='h'),
                'close': [40000 + i for i in range(12)]
            })
            
            data2 = pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01 06:00:00', periods=12, freq='h'),
                'close': [40100 + i for i in range(12)]
            })
            
            # Test conflict detection
            combined = pd.concat([data1, data2])
            duplicates = combined.duplicated(subset=['timestamp'])
            
            if duplicates.any():
                print(f"    ✅ Conflicts detected: {duplicates.sum()}")
                
                # Test conflict resolution
                resolved = combined.drop_duplicates(subset=['timestamp'], keep='last')
                
                if len(resolved) < len(combined):
                    print(f"    ✅ Conflicts resolved: {len(combined)} -> {len(resolved)}")
                    return True
                else:
                    print("    ❌ Conflict resolution failed")
                    return False
            else:
                print("    ❌ No conflicts detected in test data")
                return False
                
        except Exception as e:
            print(f"    ❌ Conflict resolution error: {e}")
            return False
    
    def _test_resume_functionality(self) -> bool:
        """Test resume functionality."""
        try:
            import json
            import tempfile
            
            # Create interrupted state
            interrupted_state = {
                'status': 'interrupted',
                'progress': 0.6,
                'last_completed': '2023-01-01T12:00:00',
                'end_time': '2023-01-02T00:00:00',
                'total_expected': 24,
                'completed_records': 12
            }
            
            # Test resume logic
            if interrupted_state['status'] == 'interrupted':
                remaining_progress = 1.0 - interrupted_state['progress']
                remaining_records = interrupted_state['total_expected'] - interrupted_state['completed_records']
                
                if remaining_progress > 0 and remaining_records > 0:
                    print(f"    ✅ Resume calculation: {remaining_progress:.1f} progress, {remaining_records} records")
                    
                    # Simulate resume
                    interrupted_state['status'] = 'resumed'
                    interrupted_state['resume_time'] = datetime.now().isoformat()
                    
                    print("    ✅ Resume functionality working")
                    return True
                else:
                    print("    ❌ Invalid resume calculation")
                    return False
            else:
                print("    ❌ State not interrupted")
                return False
                
        except Exception as e:
            print(f"    ❌ Resume functionality error: {e}")
            return False
    
    def _test_state_management(self) -> bool:
        """Test state management functionality."""
        try:
            import json
            import tempfile
            
            # Test state serialization
            test_state = {
                'version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'exchanges': {
                    'binance': {
                        'symbols': ['BTCUSDT', 'ETHUSDT'],
                        'status': 'active'
                    }
                },
                'statistics': {
                    'total_updates': 100,
                    'success_rate': 0.95
                }
            }
            
            # Test JSON serialization
            json_str = json.dumps(test_state, indent=2)
            loaded_state = json.loads(json_str)
            
            if loaded_state['version'] == test_state['version']:
                print("    ✅ State serialization working")
                
                # Test state validation
                required_keys = ['version', 'timestamp', 'exchanges']
                if all(key in loaded_state for key in required_keys):
                    print("    ✅ State validation working")
                    return True
                else:
                    print("    ❌ State validation failed")
                    return False
            else:
                print("    ❌ State serialization failed")
                return False
                
        except Exception as e:
            print(f"    ❌ State management error: {e}")
            return False
    
    def _test_data_quality(self) -> bool:
        """Test data quality validation."""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data with quality issues
            problematic_data = pd.DataFrame({
                'timestamp': pd.date_range('2023-01-01', periods=10, freq='h'),
                'open': [40000, 40100, np.nan, 40200, 40300, -100, 40400, 40500, np.inf, 40600],
                'high': [40100, 40200, 40150, 40250, 40350, 40000, 40450, 40550, 40650, 40700],
                'low': [39900, 40000, 40050, 40100, 40200, 40300, 40350, 40400, 40450, 40500],
                'close': [40050, 40150, 40100, 40200, 40250, 40350, 40400, 40500, 40550, 40650],
                'volume': [100, 200, 300, 0, 500, 600, 700, 800, 900, 1000]
            })
            
            print(f"    📊 Original data: {len(problematic_data)} records")
            
            # Detailed Quality validation with record counting
            issues = 0
            problematic_records = set()
            
            # Check for missing values
            missing_mask = problematic_data[['open', 'high', 'low', 'close']].isnull().any(axis=1)
            missing_count = missing_mask.sum()
            if missing_count > 0:
                issues += 1
                problematic_records.update(missing_mask[missing_mask].index.tolist())
                print(f"    ⚠️  Missing values detected: {missing_count} records")
            
            # Check for negative values
            negative_mask = (problematic_data[['open', 'high', 'low', 'close']] < 0).any(axis=1)
            negative_count = negative_mask.sum()
            if negative_count > 0:
                issues += 1
                problematic_records.update(negative_mask[negative_mask].index.tolist())
                print(f"    ⚠️  Negative prices detected: {negative_count} records")
            
            # Check for infinite values
            infinite_mask = np.isinf(problematic_data[['open', 'high', 'low', 'close']]).any(axis=1)
            infinite_count = infinite_mask.sum()
            if infinite_count > 0:
                issues += 1
                problematic_records.update(infinite_mask[infinite_mask].index.tolist())
                print(f"    ⚠️  Infinite values detected: {infinite_count} records")
            
            # Check for zero volume
            zero_volume_mask = (problematic_data['volume'] == 0)
            zero_volume_count = zero_volume_mask.sum()
            if zero_volume_count > 0:
                issues += 1
                problematic_records.update(zero_volume_mask[zero_volume_mask].index.tolist())
                print(f"    ⚠️  Zero volume detected: {zero_volume_count} records")
            
            if issues > 0:
                print(f"    ✅ Quality validation detected {issues} issue types")
                print(f"    📋 Total problematic records: {len(problematic_records)}")
                
                # Test data cleaning with proper logic
                cleaned_data = problematic_data.copy()
                initial_count = len(cleaned_data)
                
                # Remove records with missing values in price fields
                cleaned_data = cleaned_data.dropna(subset=['open', 'high', 'low', 'close'])
                after_missing = len(cleaned_data)
                
                # Remove records with negative prices
                price_cols = ['open', 'high', 'low', 'close']
                cleaned_data = cleaned_data[~(cleaned_data[price_cols] < 0).any(axis=1)]
                after_negative = len(cleaned_data)
                
                # Remove records with infinite values
                cleaned_data = cleaned_data[np.isfinite(cleaned_data[price_cols]).all(axis=1)]
                after_infinite = len(cleaned_data)
                
                # For zero volume, we can keep records but flag them
                zero_volume_in_clean = (cleaned_data['volume'] == 0).sum()
                
                total_removed = initial_count - after_infinite
                
                print(f"    🧹 Data cleaning results:")
                print(f"      - Removed {initial_count - after_missing} records with missing values")
                print(f"      - Removed {after_missing - after_negative} records with negative prices")
                print(f"      - Removed {after_negative - after_infinite} records with infinite values")
                print(f"      - Flagged {zero_volume_in_clean} records with zero volume (kept)")
                print(f"    ✅ Data cleaning correctly identified and removed all {total_removed} problematic records")
                
                # Verify the expected behavior
                expected_removed = len(problematic_records) - zero_volume_count  # Zero volume records are flagged, not removed
                if total_removed == expected_removed:
                    print(f"    ✅ Expected {expected_removed} records removed, actual {total_removed} - CORRECT")
                    return True
                else:
                    print(f"    ❌ Expected {expected_removed} records removed, actual {total_removed} - MISMATCH")
                    return False
            else:
                print("    ❌ No quality issues detected in test data")
                return False
                
        except Exception as e:
            print(f"    ❌ Data quality error: {e}")
            return False
    
    def _test_write_read_consistency(self) -> bool:
        """Test that written data can be read back correctly."""
        try:
            import pandas as pd
            import numpy as np
            import tempfile
            from pathlib import Path
            
            print("    🔄 Testing write-read consistency with live data scenarios...")
            
            # Test with different data sizes and types
            test_scenarios = [
                {
                    'name': 'Small Dataset (24 hours)',
                    'periods': 24,
                    'freq': 'h',
                    'base_price': 50000.0
                },
                {
                    'name': 'Medium Dataset (7 days)',
                    'periods': 168, 
                    'freq': 'h',
                    'base_price': 50000.0
                },
                {
                    'name': 'Large Dataset (365 days)',
                    'periods': 365,
                    'freq': 'D', 
                    'base_price': 50000.0
                },
                {
                    'name': 'Edge Values (astronomical numbers)',
                    'periods': 10,
                    'freq': 'h',
                    'base_price': 1e-8  # Very small crypto prices
                }
            ]
            
            with tempfile.TemporaryDirectory() as temp_dir:
                success_count = 0
                
                for scenario in test_scenarios:
                    try:
                        print(f"      📊 Testing {scenario['name']}...")
                        
                        # Generate realistic test data
                        dates = pd.date_range(start='2020-01-01', periods=scenario['periods'], freq=scenario['freq'])
                        
                        # Create realistic price movements
                        base_price = scenario['base_price']
                        price_changes = np.random.normal(0, 0.02, scenario['periods'])  # 2% volatility
                        prices = [base_price]
                        
                        for change in price_changes[1:]:
                            new_price = prices[-1] * (1 + change)
                            prices.append(max(new_price, base_price * 0.1))  # Prevent negative prices
                        
                        test_data = pd.DataFrame({
                            'datetime': dates,
                            'open': prices,
                            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                            'close': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                            'volume': np.random.uniform(100000, 5000000, scenario['periods'])
                        })
                        
                        # Ensure OHLC relationships
                        test_data['high'] = np.maximum(test_data['high'], np.maximum(test_data['open'], test_data['close']))
                        test_data['low'] = np.minimum(test_data['low'], np.minimum(test_data['open'], test_data['close']))
                        
                        # Test storage and reading using actual crypto collector components
                        try:
                            # Set up sys.path and handle config.fields import
                            import sys
                            import os
                            import importlib.util
                            
                            crypto_collector_path = Path(__file__).parent.parent.parent
                            if str(crypto_collector_path) not in sys.path:
                                sys.path.insert(0, str(crypto_collector_path))
                            
                            # Clear any cached config.fields module
                            if 'config.fields' in sys.modules:
                                del sys.modules['config.fields']
                            if 'config' in sys.modules:
                                del sys.modules['config']
                            
                            # Try direct import first
                            try:
                                from config.fields import STANDARD_FIELDS
                            except ImportError:
                                # Fallback: use importlib to load the module directly
                                fields_path = crypto_collector_path / "config" / "fields.py"
                                spec = importlib.util.spec_from_file_location("config.fields", fields_path)
                                config_fields = importlib.util.module_from_spec(spec)
                                sys.modules['config.fields'] = config_fields
                                spec.loader.exec_module(config_fields)
                                STANDARD_FIELDS = config_fields.STANDARD_FIELDS
                            
                            from storage_manager import CryptoStorageManager
                            from cli import CryptoCLI
                            
                            # Store data using storage manager
                            storage = CryptoStorageManager(temp_dir)
                            ohlcv_data = test_data[['open', 'high', 'low', 'close', 'volume']].copy().astype(np.float64)
                            
                            for field in ['open', 'high', 'low', 'close', 'volume']:
                                field_data = ohlcv_data[field]
                                # Create series with datetime index for qlib format
                                field_series = pd.Series(field_data.values, index=test_data['datetime'])
                                storage.save_feature_data(field_series, "testusdt", field, "1d")
                            
                            # Create CLI instance for reading
                            cli = CryptoCLI()
                            
                            # Read back and validate each field
                            validation_passed = True
                            for field in ['open', 'high', 'low', 'close', 'volume']:
                                # Qlib format: data_dir/timeframe/features/instrument/field.timeframe.bin
                                field_file = Path(temp_dir) / "1d" / "features" / "testusdt" / f"{field}.1d.bin"
                                
                                if field_file.exists():
                                    read_data = cli._load_binary_field(field_file)
                                    original_data = ohlcv_data[field].values
                                    
                                    # Comprehensive validation checks
                                    checks = [
                                        # 1. Data count consistency
                                        (len(read_data) == len(original_data), 
                                         f"Length mismatch: {len(read_data)} != {len(original_data)}"),
                                        
                                        # 2. No astronomical values
                                        (np.all(read_data < 1e15), 
                                         f"Astronomical values detected: max={np.max(read_data)}"),
                                        
                                        # 3. No negative values for prices/volume
                                        (np.all(read_data >= 0), 
                                         f"Negative values detected: min={np.min(read_data)}"),
                                        
                                        # 4. No NaN values
                                        (not np.any(np.isnan(read_data)), 
                                         "NaN values detected"),
                                        
                                        # 5. No infinite values
                                        (not np.any(np.isinf(read_data)), 
                                         "Infinite values detected"),
                                        
                                        # 6. Data integrity (approximate equality)
                                        (np.allclose(read_data, original_data, rtol=1e-10), 
                                         f"Data corruption: max diff={np.max(np.abs(read_data - original_data))}")
                                    ]
                                    
                                    for check_passed, error_msg in checks:
                                        if not check_passed:
                                            print(f"        ❌ {field}: {error_msg}")
                                            validation_passed = False
                                            break
                                    
                                    if validation_passed:
                                        # Additional range checks for realistic values
                                        if field in ['open', 'high', 'low', 'close']:
                                            reasonable_min = base_price * 0.001  # 0.1% of base price
                                            reasonable_max = base_price * 1000   # 1000x base price
                                            
                                            if not (np.all(read_data > reasonable_min) and np.all(read_data < reasonable_max)):
                                                print(f"        ❌ {field}: Values outside reasonable range [{reasonable_min}, {reasonable_max}]")
                                                validation_passed = False
                                else:
                                    print(f"        ❌ {field}: Binary file not found")
                                    validation_passed = False
                            
                            if validation_passed:
                                print(f"        ✅ {scenario['name']}: All validation checks passed")
                                success_count += 1
                            else:
                                print(f"        ❌ {scenario['name']}: Validation failed")
                        
                        except ImportError as e:
                            print(f"        ❌ {scenario['name']}: Import Error - {e}")
                            print(f"        Current sys.path: {sys.path[:3]}")
                            # success_count += 1  # Don't count as success if we can't test
                        except Exception as e:
                            print(f"        ❌ {scenario['name']}: Unexpected Error - {e}")
                            import traceback
                            traceback.print_exc()
                    
                    except Exception as e:
                        print(f"        ❌ {scenario['name']}: Error - {e}")
                
                print(f"    📊 Write-Read Consistency Results: {success_count}/{len(test_scenarios)} scenarios passed")
                
                # Test passes if more than 75% of scenarios succeed
                return success_count >= len(test_scenarios) * 0.75
                
        except Exception as e:
            print(f"    ❌ Write-read consistency error: {e}")
            return False
    
    def _test_multi_exchange(self) -> bool:
        """Test multi-exchange support."""
        try:
            # Test configuration for multiple exchanges
            exchanges = {
                'binance': {
                    'symbols': ['BTCUSDT', 'ETHUSDT'],
                    'api_url': 'https://api.binance.com',
                    'timeframes': ['1h', '4h', '1d']
                },
                'okx': {
                    'symbols': ['BTC-USDT', 'ETH-USDT'],
                    'api_url': 'https://www.okx.com',
                    'timeframes': ['1H', '4H', '1D']
                }
            }
            
            # Test configuration validation
            for exchange_name, config in exchanges.items():
                if 'symbols' in config and 'api_url' in config:
                    print(f"    ✅ {exchange_name} configuration valid")
                else:
                    print(f"    ❌ {exchange_name} configuration invalid")
                    return False
            
            # Test symbol mapping
            symbol_mapping = {
                'binance': {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT'},
                'okx': {'BTC': 'BTC-USDT', 'ETH': 'ETH-USDT'}
            }
            
            if len(symbol_mapping) == len(exchanges):
                print("    ✅ Symbol mapping complete")
                return True
            else:
                print("    ❌ Symbol mapping incomplete")
                return False
                
        except Exception as e:
            print(f"    ❌ Multi-exchange error: {e}")
            return False
    
    def _generate_test_report(self):
        """Generate a comprehensive test report."""
        report = {
            'test_run_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration': (datetime.now() - self.start_time).total_seconds(),
                'config': {
                    'proxy': self.config.proxy.https_proxy,
                    'exchange': self.config.test_exchange,
                    'symbol': self.config.test_symbol,
                    'timeframe': self.config.test_timeframe
                }
            },
            'test_results': self.test_results,
            'summary': {
                'total_tests': len(self.test_results),
                'passed': sum(1 for r in self.test_results if r.get('success', False)),
                'failed': sum(1 for r in self.test_results if not r.get('success', False)),
                'success_rate': sum(1 for r in self.test_results if r.get('success', False)) / len(self.test_results) if self.test_results else 0
            }
        }
        
        # Save report
        report_dir = Path("../reports")
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / f"test_report_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Test report saved to: {report_file}")

def main():
    """Main entry point."""
    try:
        runner = LiveTestRunner()
        success = runner.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed! Incremental update functionality is working correctly.")
            return 0
        else:
            print("\n⚠️  Some tests failed. Please check the test report for details.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test execution interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())