#!/usr/bin/env python3
"""
Storage debug example - demonstrates storage functionality and debugging.

This example shows how to use the CryptoStorageManager for debugging
storage issues and testing frequency conversion.
"""

import sys
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path

# Add the qlib root directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import qlib
from storage_manager import CryptoStorageManager, convert_to_qlib_freq

def test_frequency_conversion():
    """Test frequency conversion directly"""
    print("=== Testing Frequency Conversion ===")
    
    test_cases = ['1h', '1d', '1w', '1M', '1m', '5m']
    for tf in test_cases:
        converted = convert_to_qlib_freq(tf)
        print(f'{tf} -> {converted}')
        
        # Test if converted format is valid
        from qlib.utils.time import Freq
        try:
            result = Freq.parse(converted)
            print(f'  {converted} is valid: {result}')
        except Exception as e:
            print(f'  {converted} is INVALID: {e}')

def test_storage_manager():
    """Test storage manager with debug output"""
    print("\n=== Testing Storage Manager ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp dir: {temp_dir}")
        
        # Initialize qlib
        qlib.init(provider_uri=temp_dir, region='cn')
        
        # Create storage manager
        storage_manager = CryptoStorageManager(data_dir=temp_dir, create_dirs=True)
        print(f"Provider URI: {storage_manager.provider_uri}")

        # Test all provider_uri keys
        print("\n=== Testing Provider URI Keys ===")
        from qlib.utils.time import Freq
        for key in storage_manager.provider_uri.keys():
            try:
                result = Freq.parse(key)
                print(f'{key} is valid: {result}')
            except Exception as e:
                print(f'{key} is INVALID: {e}')
        
        # Create test data with all required fields
        dates = pd.date_range('2024-01-01', periods=5, freq='h')
        data = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [101.5, 102.5, 103.5, 104.5, 105.5],
            'low': [99.5, 100.5, 101.5, 102.5, 103.5],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0],
            'volume': [1000.0, 1100.0, 1200.0, 1300.0, 1400.0],
        }, index=dates)
        
        print('About to call save_ohlcv_data...')
        try:
            storage_manager.save_ohlcv_data(data, 'test_btc', '1h')
            print('✓ save_ohlcv_data completed successfully')
        except Exception as e:
            print(f'✗ save_ohlcv_data failed: {e}')
            import traceback
            traceback.print_exc()
            return

        # Test data reading
        print('\n=== Testing Data Reading ===')
        try:
            # Read back the data
            read_data = storage_manager.load_feature_data('test_btc', 'open', '1h')
            print(f'✓ Successfully read {len(read_data)} records for open field')
            print(f'  First value: {read_data.iloc[0]:.1f}')
            print(f'  Last value: {read_data.iloc[-1]:.1f}')

            # Test reading all OHLCV fields
            for field in ['open', 'high', 'low', 'close', 'volume']:
                field_data = storage_manager.load_feature_data('test_btc', field, '1h')
                print(f'✓ {field}: {len(field_data)} records, range {field_data.min():.1f}-{field_data.max():.1f}')

        except Exception as e:
            print(f'✗ Data reading failed: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_frequency_conversion()
    test_storage_manager()
