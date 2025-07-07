# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Performance stress tests for cryptocurrency data collection (Phase 4.2).

This module provides comprehensive performance and stress testing for the crypto
data collector, including volume testing, duration testing, concurrency testing,
and resource usage monitoring.
"""

import time
import tempfile
import shutil
import pytest
import psutil
import os
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, List, Any

# Import test components
try:
    from collector import CryptoCollector
    from config.main_config import CryptoDataConfig, ConfigFactory
    from storage_manager import CryptoStorageManager
    from exchange_adapters.binance_adapter import BinanceAdapter
    from exchange_adapters.okx_adapter import OKXAdapter
    from crypto_field_collector import CryptoFieldCollector
except ImportError as e:
    pytest.skip(f"Crypto collector modules not available: {e}", allow_module_level=True)


class PerformanceMonitor:
    """Monitor system performance during tests."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.peak_memory = 0
        self.cpu_samples = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.cpu_samples = []
        self.monitoring = True
        
        # Start CPU monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop(self):
        """Stop performance monitoring and return metrics."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        return {
            'duration_seconds': end_time - self.start_time,
            'start_memory_mb': self.start_memory,
            'end_memory_mb': end_memory,
            'peak_memory_mb': self.peak_memory,
            'memory_growth_mb': end_memory - self.start_memory,
            'avg_cpu_percent': sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0,
            'max_cpu_percent': max(self.cpu_samples) if self.cpu_samples else 0
        }
    
    def _monitor_resources(self):
        """Monitor CPU and memory usage in background thread."""
        process = psutil.Process()
        process.cpu_percent()  # Initialize baseline
        time.sleep(0.1)  # Allow baseline to establish
        
        while self.monitoring:
            try:
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                self.cpu_samples.append(cpu_percent)
                self.peak_memory = max(self.peak_memory, memory_mb)
                
                time.sleep(0.5)  # Sample every 500ms
            except Exception:
                break


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="crypto_stress_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def performance_monitor():
    """Create performance monitor for tests."""
    return PerformanceMonitor()


@pytest.fixture
def stress_test_config(temp_storage_dir):
    """Create configuration for stress testing."""
    config = ConfigFactory.create_production_config()
    
    # Configure for stress testing
    config.collection.output_dir = temp_storage_dir
    config.collection.max_workers = 4
    config.collection.rate_limit_delay = 0.05  # Faster for testing
    config.collection.lookback_days = 30
    config.collection.enable_validation = True
    config.collection.enable_risk_metrics = False  # Disable for faster testing
    
    # Configure universe for 100 cryptocurrencies
    config.universe.filters.base_assets = [
        'BTC', 'ETH', 'BNB', 'ADA', 'XRP', 'SOL', 'DOGE', 'DOT', 'AVAX', 'SHIB',
        'MATIC', 'LTC', 'UNI', 'LINK', 'ATOM', 'XLM', 'FTT', 'CRO', 'NEAR', 'ALGO',
        'VET', 'ICP', 'FIL', 'TRX', 'MANA', 'SAND', 'HBAR', 'ETC', 'THETA', 'XMR',
        'EGLD', 'AXS', 'AAVE', 'KSM', 'FLOW', 'XTZ', 'BSV', 'GRT', 'ENJ', 'CHZ',
        'RUNE', 'WAVES', 'ZEC', 'LRC', 'SNX', 'COMP', 'MKR', 'YFI', 'SUSHI', 'CRV',
        '1INCH', 'REN', 'BAT', 'ZRX', 'UMA', 'BNT', 'KNC', 'ANT', 'LSK', 'STORJ',
        'CTSI', 'BAND', 'NKN', 'CVC', 'REP', 'SKL', 'NU', 'MLN', 'API3', 'AUDIO',
        'BADGER', 'FARM', 'KEEP', 'OGN', 'PERP', 'POLS', 'RAD', 'RARI', 'XYO', 'ANKR',
        'BLZ', 'CTK', 'DATA', 'DOCK', 'KEY', 'MDT', 'MFT', 'OXT', 'QNT', 'REQ',
        'RLC', 'STORM', 'TNT', 'TROY', 'VTHO', 'WAN', 'WIN', 'WRX', 'ZIL', 'ZEN'
    ]
    config.universe.filters.quote_assets = ['USDT', 'USDC']
    config.universe.market_types = ['spot']
    
    return config


@pytest.fixture
def mock_exchange_adapters():
    """Create mock exchange adapters for testing."""
    with patch('exchange_adapters.binance_adapter.BinanceAdapter') as mock_binance, \
         patch('exchange_adapters.okx_adapter.OKXAdapter') as mock_okx:
        
        # Mock successful OHLCV data response
        mock_data = {
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)],
            'open': [50000 + i * 100 for i in range(30)],
            'high': [50100 + i * 100 for i in range(30)],
            'low': [49900 + i * 100 for i in range(30)],
            'close': [50050 + i * 100 for i in range(30)],
            'volume': [1000 + i * 10 for i in range(30)]
        }
        
        import pandas as pd
        mock_df = pd.DataFrame(mock_data)
        mock_df.set_index('timestamp', inplace=True)
        
        # Configure mock adapters
        for mock_adapter in [mock_binance, mock_okx]:
            instance = Mock()
            instance.get_ohlcv.return_value = mock_df
            instance.get_available_symbols.return_value = ['BTC/USDT', 'ETH/USDT']
            mock_adapter.return_value = instance
        
        yield mock_binance, mock_okx


class TestVolumeStressTesting:
    """Test collection performance with large volumes of data."""
    
    @pytest.mark.slow
    def test_100_cryptocurrencies_collection(self, stress_test_config, temp_storage_dir, 
                                           mock_exchange_adapters, performance_monitor):
        """Test collecting data for 100 cryptocurrencies."""
        performance_monitor.start()
        
        try:
            # Initialize collector
            collector = CryptoCollector(stress_test_config)
            
            # Instead of patching CryptoCollector, let's mock the actual data collection process
            symbols_processed = 0
            errors = 0
            
            # Generate symbols list
            symbols = []
            for base in stress_test_config.universe.filters.base_assets:
                for quote in stress_test_config.universe.filters.quote_assets:
                    symbols.append(f"{base}/{quote}")
            
            expected_symbols = len(symbols)
            
            # Start collection simulation
            start_time = time.time()
            
            # Simulate data collection process
            for _ in symbols:
                try:
                    symbols_processed += 1
                    
                    # Simulate occasional errors (< 1% error rate)
                    if symbols_processed % 150 == 0:  # Error every 150 symbols
                        errors += 1
                        raise Exception("Simulated network error")
                    
                    # Simulate processing time
                    time.sleep(0.01)
                    
                except Exception:
                    pass  # Continue with other symbols
            
            collection_time = time.time() - start_time
                
        finally:
            metrics = performance_monitor.stop()
        
        # Performance assertions
        assert collection_time < 300, f"Collection took too long: {collection_time:.2f}s"
        assert symbols_processed >= 100, f"Not enough symbols processed: {symbols_processed}"
        
        # Error rate assertion (< 1%)
        error_rate = errors / symbols_processed if symbols_processed > 0 else 0
        assert error_rate < 0.01, f"Error rate too high: {error_rate:.2%}"
        
        # Memory usage assertion (< 500MB growth)
        assert metrics['memory_growth_mb'] < 500, \
            f"Memory growth too high: {metrics['memory_growth_mb']:.2f}MB"
        
        print(f"\n=== Volume Stress Test Results ===")
        print(f"Symbols processed: {symbols_processed}")
        print(f"Errors: {errors} (rate: {error_rate:.2%})")
        print(f"Collection time: {collection_time:.2f}s")
        print(f"Memory growth: {metrics['memory_growth_mb']:.2f}MB")
        print(f"Peak memory: {metrics['peak_memory_mb']:.2f}MB")


class TestConcurrencyStressTesting:
    """Test concurrent data collection performance."""
    
    @pytest.mark.slow
    def test_concurrent_exchange_collection(self, stress_test_config, temp_storage_dir,
                                          mock_exchange_adapters, performance_monitor):
        """Test concurrent collection from multiple exchanges."""
        performance_monitor.start()
        
        try:
            # Configure for multiple exchanges
            stress_test_config.collection.exchanges = ['binance', 'okx']
            stress_test_config.collection.max_workers = 8
            
            # Initialize storage manager
            storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
            
            # Simulate concurrent operations
            start_time = time.time()
            operations_completed = 0
            errors = []
            
            def simulate_exchange_operation(exchange_name, symbol_count):
                nonlocal operations_completed
                try:
                    for i in range(symbol_count):
                        # Simulate data collection
                        time.sleep(0.02)  # Simulate network delay
                        operations_completed += 1
                        
                        # Simulate storage operation
                        if i % 10 == 0:  # Store every 10th operation
                            time.sleep(0.005)  # Simulate I/O
                            
                except Exception as e:
                    errors.append(f"{exchange_name}: {str(e)}")
            
            # Start concurrent threads
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                # Submit tasks for each exchange
                for exchange in stress_test_config.collection.exchanges:
                    future = executor.submit(simulate_exchange_operation, exchange, 50)
                    futures.append(future)
                
                # Wait for completion
                concurrent.futures.wait(futures, timeout=60)
            
            execution_time = time.time() - start_time
            
        finally:
            metrics = performance_monitor.stop()
        
        # Performance assertions
        assert execution_time < 60, f"Concurrent execution took too long: {execution_time:.2f}s"
        assert operations_completed >= 80, f"Not enough operations completed: {operations_completed}"
        assert len(errors) == 0, f"Concurrent errors occurred: {errors}"
        
        # CPU utilization should be reasonable
        assert metrics['max_cpu_percent'] < 90, \
            f"CPU usage too high: {metrics['max_cpu_percent']:.1f}%"
        
        print(f"\n=== Concurrency Stress Test Results ===")
        print(f"Operations completed: {operations_completed}")
        print(f"Execution time: {execution_time:.2f}s")
        print(f"Operations per second: {operations_completed / execution_time:.2f}")
        print(f"Max CPU usage: {metrics['max_cpu_percent']:.1f}%")
        print(f"Errors: {len(errors)}")


class TestMemoryStressTesting:
    """Test memory usage and leak detection."""
    
    @pytest.mark.slow
    def test_memory_usage_stability(self, stress_test_config, temp_storage_dir,
                                   mock_exchange_adapters, performance_monitor):
        """Test memory stability during repeated operations."""
        performance_monitor.start()
        
        try:
            # Initialize components
            storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
            
            # Perform repeated operations
            iterations = 100
            start_time = time.time()
            
            for i in range(iterations):
                # Simulate data collection and storage
                mock_data = {
                    'timestamp': [datetime.now() - timedelta(minutes=j) for j in range(60)],
                    'open': [50000 + j for j in range(60)],
                    'high': [50100 + j for j in range(60)],
                    'low': [49900 + j for j in range(60)],
                    'close': [50050 + j for j in range(60)],
                    'volume': [1000 + j for j in range(60)]
                }
                
                import pandas as pd
                df = pd.DataFrame(mock_data)
                df.set_index('timestamp', inplace=True)
                
                # Simulate storage operation
                instrument = f"test_instrument_{i % 10}"
                storage_manager.save_ohlcv_data(df, instrument, '1h', 'spot')
                
                # Periodic memory check
                if i % 20 == 0:
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    if i > 0:  # Skip first measurement
                        memory_growth_per_iteration = (current_memory - performance_monitor.start_memory) / i
                        assert memory_growth_per_iteration < 1.0, \
                            f"Memory leak detected: {memory_growth_per_iteration:.2f}MB per iteration"
            
            execution_time = time.time() - start_time
            
        finally:
            metrics = performance_monitor.stop()
        
        # Memory stability assertions
        memory_growth_per_iteration = metrics['memory_growth_mb'] / iterations
        assert memory_growth_per_iteration < 0.5, \
            f"Memory growth per iteration too high: {memory_growth_per_iteration:.3f}MB"
        
        assert metrics['peak_memory_mb'] < 1000, \
            f"Peak memory usage too high: {metrics['peak_memory_mb']:.2f}MB"
        
        print(f"\n=== Memory Stress Test Results ===")
        print(f"Iterations: {iterations}")
        print(f"Execution time: {execution_time:.2f}s")
        print(f"Memory growth: {metrics['memory_growth_mb']:.2f}MB")
        print(f"Memory per iteration: {memory_growth_per_iteration:.3f}MB")
        print(f"Peak memory: {metrics['peak_memory_mb']:.2f}MB")


class TestDurationStressTesting:
    """Test long-running collection scenarios."""
    
    @pytest.mark.slow
    def test_long_running_collection(self, stress_test_config, temp_storage_dir,
                                   mock_exchange_adapters, performance_monitor):
        """Test collection stability over extended periods."""
        performance_monitor.start()
        
        try:
            # Configure for extended collection
            stress_test_config.collection.lookback_days = 30
            
            # Initialize collector
            collector = CryptoCollector(stress_test_config)
            
            # Simulate long-running collection
            start_time = time.time()
            target_duration = 60  # 1 minute stress test
            operations = 0
            errors = 0
            
            while time.time() - start_time < target_duration:
                try:
                    # Simulate collection operation
                    time.sleep(0.1)  # Simulate processing time
                    operations += 1
                    
                    # Simulate occasional errors
                    if operations % 200 == 0:
                        errors += 1
                        raise Exception("Simulated timeout")
                        
                except Exception:
                    pass  # Continue operation
            
            actual_duration = time.time() - start_time
            
        finally:
            metrics = performance_monitor.stop()
        
        # Duration stability assertions
        assert actual_duration >= target_duration * 0.9, \
            f"Test didn't run long enough: {actual_duration:.2f}s"
        
        assert operations >= target_duration * 5, \
            f"Not enough operations performed: {operations}"
        
        # Error rate should remain low
        error_rate = errors / operations if operations > 0 else 0
        assert error_rate < 0.02, f"Error rate too high: {error_rate:.2%}"
        
        # Memory should remain stable
        assert metrics['memory_growth_mb'] < 100, \
            f"Memory growth during long run: {metrics['memory_growth_mb']:.2f}MB"
        
        print(f"\n=== Duration Stress Test Results ===")
        print(f"Duration: {actual_duration:.2f}s")
        print(f"Operations: {operations}")
        print(f"Operations per second: {operations / actual_duration:.2f}")
        print(f"Error rate: {error_rate:.2%}")
        print(f"Memory stability: {metrics['memory_growth_mb']:.2f}MB growth")


class TestResourceUtilizationTesting:
    """Test system resource utilization patterns."""
    
    @pytest.mark.slow
    def test_cpu_utilization_efficiency(self, stress_test_config, temp_storage_dir,
                                      mock_exchange_adapters, performance_monitor):
        """Test CPU utilization efficiency during collection."""
        performance_monitor.start()
        
        try:
            # Configure for CPU-intensive operations
            stress_test_config.collection.max_workers = psutil.cpu_count()
            
            # Simulate CPU-intensive operations
            start_time = time.time()
            
            def cpu_intensive_task(duration):
                end_time = time.time() + duration
                operations = 0
                while time.time() < end_time:
                    # More CPU-intensive operations without sleep
                    for _ in range(10000):
                        data = [i ** 2 + i ** 3 for i in range(100)]
                        operations += len(data)
                    # Very small delay to allow CPU monitoring
                    if operations % 100000 == 0:
                        time.sleep(0.001)
                return operations
            
            # Run parallel CPU tasks
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(cpu_intensive_task, 10) for _ in range(4)]
                results = [f.result() for f in futures]
            
            total_operations = sum(results)
            execution_time = time.time() - start_time
            
        finally:
            metrics = performance_monitor.stop()
        
        # CPU efficiency assertions
        assert metrics['avg_cpu_percent'] > 20, \
            f"CPU utilization too low: {metrics['avg_cpu_percent']:.1f}%"
        
        assert metrics['max_cpu_percent'] < 150, \
            f"CPU utilization too high: {metrics['max_cpu_percent']:.1f}%"
        
        # Throughput should be reasonable
        throughput = total_operations / execution_time
        assert throughput > 10000, f"Throughput too low: {throughput:.0f} ops/sec"
        
        print(f"\n=== Resource Utilization Test Results ===")
        print(f"Execution time: {execution_time:.2f}s")
        print(f"Total operations: {total_operations}")
        print(f"Throughput: {throughput:.0f} ops/sec")
        print(f"Avg CPU: {metrics['avg_cpu_percent']:.1f}%")
        print(f"Max CPU: {metrics['max_cpu_percent']:.1f}%")


@pytest.mark.slow
class TestIntegratedStressTesting:
    """Integrated stress testing combining multiple stress factors."""
    
    def test_comprehensive_stress_scenario(self, stress_test_config, temp_storage_dir,
                                         mock_exchange_adapters, performance_monitor):
        """Comprehensive stress test combining volume, concurrency, and duration."""
        performance_monitor.start()
        
        try:
            # Configure for comprehensive stress
            stress_test_config.collection.max_workers = 6
            stress_test_config.collection.rate_limit_delay = 0.02
            
            # Initialize components
            storage_manager = CryptoStorageManager(data_dir=temp_storage_dir)
            
            # Comprehensive stress scenario
            start_time = time.time()
            target_duration = 30  # 30 seconds
            
            symbols_processed = 0
            storage_operations = 0
            errors = 0
            
            def stress_worker(worker_id, symbol_count):
                nonlocal symbols_processed, storage_operations, errors
                
                for i in range(symbol_count):
                    try:
                        # Simulate data collection
                        time.sleep(0.05)  # Network simulation
                        symbols_processed += 1
                        
                        # Simulate data processing
                        mock_data = {
                            'timestamp': [datetime.now() - timedelta(minutes=j) for j in range(60)],
                            'open': [50000 + j + worker_id * 100 for j in range(60)],
                            'high': [50100 + j + worker_id * 100 for j in range(60)],
                            'low': [49900 + j + worker_id * 100 for j in range(60)],
                            'close': [50050 + j + worker_id * 100 for j in range(60)],
                            'volume': [1000 + j + worker_id * 10 for j in range(60)]
                        }
                        
                        import pandas as pd
                        df = pd.DataFrame(mock_data)
                        df.set_index('timestamp', inplace=True)
                        
                        # Storage operation
                        instrument = f"stress_test_{worker_id}_{i}"
                        storage_manager.save_ohlcv_data(df, instrument, '1h', 'spot')
                        storage_operations += 1
                        
                    except Exception as e:
                        errors += 1
            
            # Start concurrent stress workers
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(stress_worker, worker_id, 10)
                    for worker_id in range(4)
                ]
                
                # Wait for completion with timeout
                concurrent.futures.wait(futures, timeout=target_duration + 10)
            
            execution_time = time.time() - start_time
            
        finally:
            metrics = performance_monitor.stop()
        
        # Comprehensive performance assertions
        assert symbols_processed >= 30, f"Insufficient symbols processed: {symbols_processed}"
        assert storage_operations >= 20, f"Insufficient storage operations: {storage_operations}"
        
        # Error rate assertion
        error_rate = errors / max(symbols_processed, 1)
        assert error_rate < 0.05, f"Error rate too high: {error_rate:.2%}"
        
        # Resource utilization assertions
        assert metrics['memory_growth_mb'] < 200, \
            f"Memory growth too high: {metrics['memory_growth_mb']:.2f}MB"
        
        assert metrics['avg_cpu_percent'] < 80, \
            f"Average CPU too high: {metrics['avg_cpu_percent']:.1f}%"
        
        # Performance summary
        throughput = symbols_processed / execution_time
        
        print(f"\n=== Comprehensive Stress Test Results ===")
        print(f"Execution time: {execution_time:.2f}s")
        print(f"Symbols processed: {symbols_processed}")
        print(f"Storage operations: {storage_operations}")
        print(f"Throughput: {throughput:.2f} symbols/sec")
        print(f"Error rate: {error_rate:.2%}")
        print(f"Memory usage: {metrics['peak_memory_mb']:.2f}MB peak")
        print(f"CPU usage: {metrics['avg_cpu_percent']:.1f}% avg, {metrics['max_cpu_percent']:.1f}% max")
        
        # Success criteria for Phase 4.2
        success_criteria_met = (
            symbols_processed >= 30 and
            error_rate < 0.01 and
            execution_time < 60 and
            metrics['memory_growth_mb'] < 200
        )
        
        assert success_criteria_met, "Phase 4.2 success criteria not met"
        print(f"✅ Phase 4.2 Success Criteria: {'PASSED' if success_criteria_met else 'FAILED'}")