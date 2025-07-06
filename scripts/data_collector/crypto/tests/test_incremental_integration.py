#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Test script for incremental update integration.

This script tests the integration between the CLI and incremental update system
without requiring external dependencies.
"""

import asyncio
import sys
import tempfile
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_cli_parser():
    """Test CLI parser integration."""
    print("Testing CLI parser integration...")
    
    try:
        from cli import CryptoCLI
        
        # Create CLI instance
        cli = CryptoCLI()
        
        # Test parser creation
        parser = cli.create_parser()
        
        # Test incremental subcommand
        args = parser.parse_args(['incremental', 'update', '--dry-run'])
        assert args.command == 'incremental'
        assert args.incremental_action == 'update'
        assert args.dry_run == True
        
        print("✓ CLI parser integration successful")
        return True
        
    except Exception as e:
        print(f"✗ CLI parser integration failed: {e}")
        return False


def test_config_integration():
    """Test configuration integration."""
    print("Testing configuration integration...")
    
    try:
        from config import CryptoDataConfig
        
        # Create config
        config = CryptoDataConfig()
        
        # Test incremental config
        assert hasattr(config, 'incremental')
        assert hasattr(config.incremental, 'enabled')
        assert hasattr(config.incremental, 'state_file')
        assert hasattr(config.incremental, 'max_concurrent_updates')
        
        print("✓ Configuration integration successful")
        return True
        
    except Exception as e:
        print(f"✗ Configuration integration failed: {e}")
        return False


def test_incremental_imports():
    """Test incremental module imports."""
    print("Testing incremental module imports...")
    
    try:
        from incremental import (
            IncrementalUpdateManager,
            UpdateState,
            FileStateStorage,
            TimeBasedStrategy,
            DefaultConflictResolver
        )
        
        print("✓ Incremental module imports successful")
        return True
        
    except Exception as e:
        print(f"✗ Incremental module imports failed: {e}")
        return False


@pytest.mark.asyncio
async def test_incremental_manager():
    """Test incremental manager basic functionality."""
    print("Testing incremental manager...")
    
    try:
        from config import CryptoDataConfig
        from incremental import IncrementalUpdateManager
        
        # Create temporary config
        with tempfile.TemporaryDirectory() as temp_dir:
            config = CryptoDataConfig()
            config.collection.output_dir = temp_dir
            config.incremental.state_file = str(Path(temp_dir) / "test_state.json")
            
            # Create manager
            manager = IncrementalUpdateManager(config)
            
            # Test initialization
            await manager.initialize()
            
            # Test state summary
            summary = manager.get_state_summary()
            assert isinstance(summary, dict)
            
            # Test statistics
            stats = manager.get_update_statistics()
            assert isinstance(stats, dict)
            
            print("✓ Incremental manager basic functionality successful")
            return True
            
    except Exception as e:
        print(f"✗ Incremental manager test failed: {e}")
        return False


def test_cli_incremental_methods():
    """Test CLI incremental methods."""
    print("Testing CLI incremental methods...")
    
    try:
        from cli import CryptoCLI
        
        # Create CLI instance
        cli = CryptoCLI()
        
        # Check if incremental methods exist
        assert hasattr(cli, 'execute_incremental')
        assert hasattr(cli, '_run_incremental_update')
        assert hasattr(cli, '_show_incremental_status')
        assert hasattr(cli, '_reset_incremental_state')
        assert hasattr(cli, '_run_incremental_collection')
        
        print("✓ CLI incremental methods exist")
        return True
        
    except Exception as e:
        print(f"✗ CLI incremental methods test failed: {e}")
        return False


def test_collector_incremental_support():
    """Test collector incremental support."""
    print("Testing collector incremental support...")
    
    try:
        # Import from scripts directory
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts" / "data_collector" / "crypto"))
        from collector import CryptoCollector
        
        # Test incremental mode parameter
        collector = CryptoCollector(
            save_dir="./test",
            incremental_mode=True
        )
        
        assert hasattr(collector, 'incremental_mode')
        assert collector.incremental_mode == True
        assert hasattr(collector, 'incremental_manager')
        assert hasattr(collector, 'run_incremental_update')
        
        print("✓ Collector incremental support successful")
        return True
        
    except Exception as e:
        print(f"✗ Collector incremental support test failed: {e}")
        return False


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Incremental Update Integration Tests")
    print("=" * 60)
    
    tests = [
        ("CLI Parser Integration", test_cli_parser),
        ("Configuration Integration", test_config_integration),
        ("Incremental Imports", test_incremental_imports),
        ("CLI Incremental Methods", test_cli_incremental_methods),
        ("Collector Incremental Support", test_collector_incremental_support),
        ("Incremental Manager", test_incremental_manager),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("❌ Some integration tests failed")
        return False


def main():
    """Main function."""
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
