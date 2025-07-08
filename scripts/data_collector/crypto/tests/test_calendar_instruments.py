#!/usr/bin/env python3
"""
Calendar and Instruments Generation Tests for Crypto Data Collection.

This module contains pytest-compatible tests for the calendar and instruments
file generation functionality in the crypto data collection system.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add project paths for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
CRYPTO_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(CRYPTO_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Test setup
pytestmark = pytest.mark.crypto_data


@pytest.fixture(scope="session", autouse=True)
def setup_qlib():
    """Initialize qlib for all tests in this module."""
    try:
        import qlib
        return qlib
    except ImportError:
        pytest.skip("Qlib not available")


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for testing data generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def qlib_generator(temp_data_dir, setup_qlib):
    """Create a QlibDataGenerator instance for testing."""
    setup_qlib.init(provider_uri=temp_data_dir)
    
    from qlib_data_generator import QlibDataGenerator
    return QlibDataGenerator(data_dir=temp_data_dir, provider_uri=temp_data_dir)


@pytest.fixture
def test_parameters():
    """Standard test parameters for calendar and instruments generation."""
    return {
        'timeframes': ['1h', '1d'],
        'exchanges': ['binance'],
        'symbols': ['BTC/USDT', 'ETH/USDT'],
        'start_date': datetime.now() - timedelta(days=30),
        'end_date': datetime.now(),
        'market_type': 'spot'
    }


class TestQlibDataGenerator:
    """Test QlibDataGenerator functionality."""
    
    def test_generator_initialization(self, temp_data_dir, setup_qlib):
        """Test QlibDataGenerator can be initialized correctly."""
        setup_qlib.init(provider_uri=temp_data_dir)
        
        from qlib_data_generator import QlibDataGenerator
        generator = QlibDataGenerator(data_dir=temp_data_dir, provider_uri=temp_data_dir)
        
        assert generator.data_dir == Path(temp_data_dir)
        assert generator.provider_uri == temp_data_dir
        assert generator.data_dir.exists()
    
    def test_instruments_list_generation(self, qlib_generator):
        """Test instrument list generation from exchanges and symbols."""
        instruments = qlib_generator._generate_instruments_list(
            exchanges=['binance', 'okx'],
            symbols=['BTC/USDT', 'ETH/USDT'],
            market_type='spot'
        )
        
        expected = [
            'binance_spot_btcusdt',
            'binance_spot_ethusdt',
            'okx_spot_btcusdt',
            'okx_spot_ethusdt'
        ]
        
        assert instruments == expected
    
    def test_full_structure_creation(self, qlib_generator, test_parameters, temp_data_dir):
        """Test complete Qlib structure creation."""
        summary = qlib_generator.create_full_structure(**test_parameters)
        
        # Verify summary
        assert summary['timeframes_created'] == 2
        assert summary['instruments_files'] == 2
        assert summary['calendar_files'] == 4  # 2 timeframes × 2 calendars each
        assert summary['feature_directories'] == 4  # 2 timeframes × 2 instruments each
        assert len(summary['errors']) == 0
        
        # Verify directory structure
        data_path = Path(temp_data_dir)
        
        for timeframe in test_parameters['timeframes']:
            tf_dir = data_path / timeframe
            
            # Check main directories exist
            assert (tf_dir / "features").exists()
            assert (tf_dir / "instruments").exists()
            assert (tf_dir / "calendars").exists()
            
            # Check instruments file
            instruments_file = tf_dir / "instruments" / "crypto.txt"
            assert instruments_file.exists()
            
            # Check calendar files
            assert (tf_dir / "calendars" / f"{timeframe}.txt").exists()
            assert (tf_dir / "calendars" / f"{timeframe}_future.txt").exists()
            
            # Check feature directories
            feature_dirs = list((tf_dir / "features").iterdir())
            assert len(feature_dirs) == 2  # BTC and ETH
    
    def test_instruments_file_content(self, qlib_generator, temp_data_dir):
        """Test that instruments file contains correct content."""
        qlib_generator.create_full_structure(
            timeframes=['1h'],
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        instruments_file = Path(temp_data_dir) / "1h" / "instruments" / "crypto.txt"
        content = instruments_file.read_text()
        
        assert "binance_spot_btcusdt\t2020-01-01\t2030-12-31" in content
        
        lines = content.strip().split('\n')
        assert len(lines) == 1  # Only one instrument
    
    def test_calendar_file_content(self, qlib_generator, temp_data_dir):
        """Test that calendar files contain correct content."""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 3)
        
        qlib_generator.create_full_structure(
            timeframes=['1d'],
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=start_date,
            end_date=end_date,
            market_type='spot'
        )
        
        calendar_file = Path(temp_data_dir) / "1d" / "calendars" / "1d.txt"
        content = calendar_file.read_text()
        
        lines = content.strip().split('\n')
        assert len(lines) == 3  # 3 days
        assert "2025-01-01 00:00:00" in lines[0]
        assert "2025-01-02 00:00:00" in lines[1]
        assert "2025-01-03 00:00:00" in lines[2]
    
    def test_future_calendar_generation(self, qlib_generator, temp_data_dir):
        """Test that future calendar files are generated."""
        qlib_generator.create_full_structure(
            timeframes=['1h'],
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        future_calendar_file = Path(temp_data_dir) / "1h" / "calendars" / "1h_future.txt"
        assert future_calendar_file.exists()
        
        content = future_calendar_file.read_text()
        lines = content.strip().split('\n')
        assert len(lines) > 100  # Should have many future hours
    
    def test_multiple_timeframes(self, qlib_generator, temp_data_dir):
        """Test generation with multiple timeframes."""
        timeframes = ['1h', '1d', '5min']
        
        summary = qlib_generator.create_full_structure(
            timeframes=timeframes,
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        assert summary['timeframes_created'] == 3
        
        data_path = Path(temp_data_dir)
        for timeframe in timeframes:
            assert (data_path / timeframe).exists()
            assert (data_path / timeframe / "instruments" / "crypto.txt").exists()
            assert (data_path / timeframe / "calendars" / f"{timeframe}.txt").exists()
    
    def test_multiple_exchanges(self, qlib_generator, temp_data_dir):
        """Test generation with multiple exchanges."""
        summary = qlib_generator.create_full_structure(
            timeframes=['1h'],
            exchanges=['binance', 'okx'],
            symbols=['BTC/USDT'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        # Check that feature directories are created for both exchanges
        feature_dirs = list((Path(temp_data_dir) / "1h" / "features").iterdir())
        assert len(feature_dirs) == 2  # binance and okx
        
        dir_names = [d.name for d in feature_dirs]
        assert 'binance_spot_btcusdt' in dir_names
        assert 'okx_spot_btcusdt' in dir_names


class TestStructureValidation:
    """Test structure validation functionality."""
    
    def test_validation_with_complete_structure(self, qlib_generator, test_parameters):
        """Test validation passes for complete structure."""
        # Generate complete structure
        qlib_generator.create_full_structure(**test_parameters)
        
        # Validate structure
        validation_result = qlib_generator.validate_structure()
        
        assert validation_result['is_valid'] is True
        assert len(validation_result['missing_files']) == 0
        assert len(validation_result['timeframes']) == 2
    
    def test_validation_with_missing_files(self, qlib_generator, temp_data_dir):
        """Test validation fails when files are missing."""
        # Create partial structure (directories only)
        tf_dir = Path(temp_data_dir) / "1h"
        (tf_dir / "features").mkdir(parents=True)
        (tf_dir / "instruments").mkdir(parents=True)
        (tf_dir / "calendars").mkdir(parents=True)
        
        validation_result = qlib_generator.validate_structure()
        
        assert validation_result['is_valid'] is False
        assert len(validation_result['missing_files']) > 0
        assert "1h/instruments/crypto.txt" in validation_result['missing_files']
    
    def test_structure_info_generation(self, qlib_generator, test_parameters):
        """Test structure information generation."""
        qlib_generator.create_full_structure(**test_parameters)
        
        info = qlib_generator.get_structure_info()
        
        assert 'data_dir' in info
        assert 'timeframes' in info
        assert 'total_instruments' in info
        assert 'total_feature_dirs' in info
        assert len(info['timeframes']) == 2


class TestStorageManagerIntegration:
    """Test integration between QlibDataGenerator and StorageManager."""
    
    def test_storage_manager_compatibility(self, temp_data_dir, setup_qlib):
        """Test that QlibDataGenerator works with StorageManager."""
        setup_qlib.init(provider_uri=temp_data_dir)
        
        from storage_manager import CryptoStorageManager
        from qlib_data_generator import QlibDataGenerator
        
        # Initialize both components
        storage_manager = CryptoStorageManager(data_dir=temp_data_dir)
        generator = QlibDataGenerator(data_dir=temp_data_dir, provider_uri=temp_data_dir)
        
        # Generate structure
        summary = generator.create_full_structure(
            timeframes=['1h'],
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        assert summary['timeframes_created'] == 1
        
        # Verify all required components exist
        data_path = Path(temp_data_dir)
        required_components = [
            '1h/features',
            '1h/instruments',
            '1h/calendars',
            '1h/instruments/crypto.txt',
            '1h/calendars/1h.txt',
            '1h/calendars/1h_future.txt'
        ]
        
        for component in required_components:
            assert (data_path / component).exists(), f"Missing component: {component}"


class TestErrorHandling:
    """Test error handling in calendar and instruments generation."""
    
    def test_invalid_timeframe_handling(self, qlib_generator):
        """Test handling of invalid timeframes."""
        summary = qlib_generator.create_full_structure(
            timeframes=['invalid_tf', '1h'],
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        # Should still create structure for valid timeframes
        assert summary['timeframes_created'] >= 1
        assert len(summary['errors']) >= 1  # Should report invalid timeframe
    
    def test_empty_symbols_list(self, qlib_generator):
        """Test handling of empty symbols list."""
        summary = qlib_generator.create_full_structure(
            timeframes=['1h'],
            exchanges=['binance'],
            symbols=[],  # Empty symbols
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        # Should still create directory structure
        assert summary['timeframes_created'] == 1
        assert summary['feature_directories'] == 0  # No symbols = no feature directories


class TestPerformance:
    """Test performance aspects of calendar and instruments generation."""
    
    def test_large_symbol_list_performance(self, qlib_generator):
        """Test performance with large number of symbols."""
        import time
        
        # Create a large list of symbols
        symbols = [f"SYMBOL{i}/USDT" for i in range(100)]
        
        start_time = time.time()
        summary = qlib_generator.create_full_structure(
            timeframes=['1h'],
            exchanges=['binance'],
            symbols=symbols,
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            market_type='spot'
        )
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (< 10 seconds)
        assert elapsed_time < 10
        assert summary['timeframes_created'] == 1
        assert summary['feature_directories'] == 100
    
    def test_multiple_timeframes_performance(self, qlib_generator):
        """Test performance with multiple timeframes."""
        import time
        
        timeframes = ['1min', '5min', '15min', '30min', '1h', '1d']
        
        start_time = time.time()
        summary = qlib_generator.create_full_structure(
            timeframes=timeframes,
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            market_type='spot'
        )
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert elapsed_time < 5
        assert summary['timeframes_created'] == len(timeframes)


@pytest.mark.slow
class TestLargeDataGeneration:
    """Test generation with larger datasets (marked as slow)."""
    
    def test_long_date_range_calendar(self, qlib_generator, temp_data_dir):
        """Test calendar generation with long date range."""
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2025, 12, 31)
        
        summary = qlib_generator.create_full_structure(
            timeframes=['1d'],
            exchanges=['binance'],
            symbols=['BTC/USDT'],
            start_date=start_date,
            end_date=end_date,
            market_type='spot'
        )
        
        assert summary['timeframes_created'] == 1
        
        # Check calendar file size
        calendar_file = Path(temp_data_dir) / "1d" / "calendars" / "1d.txt"
        content = calendar_file.read_text()
        lines = content.strip().split('\n')
        
        # Should have approximately 6 years worth of days
        assert len(lines) > 2000


# Integration with pytest markers
@pytest.mark.integration
class TestFullIntegration:
    """Full integration tests for calendar and instruments generation."""
    
    def test_end_to_end_structure_generation(self, temp_data_dir, setup_qlib):
        """Test complete end-to-end structure generation."""
        setup_qlib.init(provider_uri=temp_data_dir)
        
        from qlib_data_generator import QlibDataGenerator
        from storage_manager import CryptoStorageManager
        
        # Initialize all components
        storage_manager = CryptoStorageManager(data_dir=temp_data_dir)
        generator = QlibDataGenerator(data_dir=temp_data_dir, provider_uri=temp_data_dir)
        
        # Simulate full data collection workflow
        timeframes = ['1h', '1d']
        exchanges = ['binance']
        symbols = ['BTC/USDT', 'ETH/USDT']
        
        # Generate structure
        summary = generator.create_full_structure(
            timeframes=timeframes,
            exchanges=exchanges,
            symbols=symbols,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            market_type='spot'
        )
        
        # Verify complete success
        assert summary['timeframes_created'] == 2
        assert summary['instruments_files'] == 2
        assert summary['calendar_files'] == 4
        assert summary['feature_directories'] == 4
        assert len(summary['errors']) == 0
        
        # Validate structure (only check the timeframes we actually created)
        validation_result = generator.validate_structure()
        
        # Check that our created timeframes are valid
        for timeframe in timeframes:
            if timeframe in validation_result['timeframes']:
                tf_validation = validation_result['timeframes'][timeframe]
                assert tf_validation['has_features'] is True
                assert tf_validation['has_instruments'] is True
                assert tf_validation['has_calendars'] is True
        
        # Get structure info
        info = generator.get_structure_info()
        assert info['total_instruments'] == 2
        assert info['total_feature_dirs'] == 4


if __name__ == "__main__":
    # Allow running this file directly for debugging
    pytest.main([__file__, "-v"])