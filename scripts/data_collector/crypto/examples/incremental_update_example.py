#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Example script demonstrating incremental update functionality.

This script shows how to use the incremental update system for cryptocurrency
data collection with various configuration options and update strategies.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CryptoDataConfig
from incremental import (
    IncrementalUpdateManager,
    TimeBasedStrategy,
    DataBasedStrategy,
    HybridStrategy,
    FileStateStorage,
    DefaultConflictResolver
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def basic_incremental_update():
    """Basic incremental update example."""
    logger.info("=== Basic Incremental Update Example ===")
    
    # Create configuration
    config = CryptoDataConfig()
    config.collection.exchanges = ["binance"]
    config.collection.timeframes = ["1d"]
    config.collection.output_dir = "./crypto_data_incremental"
    
    # Initialize manager
    manager = IncrementalUpdateManager(config)
    await manager.initialize()
    
    # Plan and execute updates
    update_plans = await manager.plan_updates()
    
    if update_plans:
        logger.info(f"Executing {len(update_plans)} updates...")
        results = await manager.execute_updates(update_plans)
        logger.info(f"Results: {results['successful']} successful, {results['failed']} failed")
    else:
        logger.info("No updates needed")
    
    # Show statistics
    stats = manager.get_update_statistics()
    logger.info(f"Statistics: {stats}")


async def custom_strategy_example():
    """Example with custom update strategy."""
    logger.info("=== Custom Strategy Example ===")
    
    # Create configuration
    config = CryptoDataConfig()
    config.collection.exchanges = ["binance", "okx"]
    config.collection.timeframes = ["1h", "1d"]
    
    # Create custom strategy (hybrid approach)
    strategy = HybridStrategy(
        time_interval_hours=6,  # Update every 6 hours
        data_staleness_hours=12,  # Consider data stale after 12 hours
        priority_symbols=["BTC/USDT", "ETH/USDT"]  # Prioritize major pairs
    )
    
    # Initialize manager with custom strategy
    manager = IncrementalUpdateManager(
        config=config,
        update_strategy=strategy
    )
    await manager.initialize()
    
    # Plan updates with specific filters
    update_plans = await manager.plan_updates(
        exchanges=["binance"],
        symbols=["BTC/USDT", "ETH/USDT", "ADA/USDT"],
        timeframes=["1d"]
    )
    
    logger.info(f"Planned {len(update_plans)} updates with custom strategy")
    
    # Execute with dry run first
    dry_results = await manager.execute_updates(update_plans, dry_run=True)
    logger.info(f"Dry run results: {dry_results}")
    
    # Execute actual updates
    if input("Proceed with actual updates? (y/n): ").lower() == 'y':
        results = await manager.execute_updates(update_plans, dry_run=False)
        logger.info(f"Actual results: {results}")


async def state_management_example():
    """Example demonstrating state management."""
    logger.info("=== State Management Example ===")
    
    # Create configuration with custom state storage
    config = CryptoDataConfig()
    config.incremental.state_file = "./custom_state.json"
    config.incremental.backup_count = 5
    
    # Create custom state storage
    state_storage = FileStateStorage(
        state_file=config.incremental.state_file,
        backup_count=config.incremental.backup_count
    )
    
    # Initialize manager
    manager = IncrementalUpdateManager(
        config=config,
        state_storage=state_storage
    )
    await manager.initialize()
    
    # Show current state
    state_summary = manager.get_state_summary()
    logger.info(f"Current state summary: {state_summary}")
    
    # Reset state for specific exchange
    if input("Reset Binance state? (y/n): ").lower() == 'y':
        manager.reset_exchange_state("binance")
        logger.info("Reset Binance state")
    
    # Show updated state
    updated_summary = manager.get_state_summary()
    logger.info(f"Updated state summary: {updated_summary}")


async def conflict_resolution_example():
    """Example demonstrating conflict resolution."""
    logger.info("=== Conflict Resolution Example ===")
    
    # Create configuration
    config = CryptoDataConfig()
    config.incremental.conflict_resolution_strategy = "keep_best_quality"
    
    # Create custom conflict resolver
    conflict_resolver = DefaultConflictResolver(
        default_strategy="keep_best_quality",
        quality_weights={
            'completeness': 0.4,
            'recency': 0.3,
            'volume_consistency': 0.3
        }
    )
    
    # Initialize manager with custom conflict resolver
    manager = IncrementalUpdateManager(
        config=config,
        conflict_resolver=conflict_resolver
    )
    await manager.initialize()
    
    # Plan and execute updates
    update_plans = await manager.plan_updates()
    
    if update_plans:
        logger.info(f"Executing {len(update_plans)} updates with conflict resolution...")
        results = await manager.execute_updates(update_plans)
        
        # Show conflict statistics
        stats = manager.get_update_statistics()
        logger.info(f"Conflicts resolved: {stats.get('conflicts_resolved', 0)}")
    else:
        logger.info("No updates needed")


async def monitoring_example():
    """Example demonstrating monitoring and statistics."""
    logger.info("=== Monitoring Example ===")
    
    # Create configuration
    config = CryptoDataConfig()
    config.collection.exchanges = ["binance"]
    
    # Initialize manager
    manager = IncrementalUpdateManager(config)
    await manager.initialize()
    
    # Show detailed status
    state_summary = manager.get_state_summary()
    logger.info("=== Current Status ===")
    logger.info(f"Last updated: {state_summary.get('last_updated', 'Never')}")
    logger.info(f"Total symbols: {state_summary.get('total_symbols', 0)}")
    logger.info(f"Stale symbols: {state_summary.get('stale_symbols', 0)}")
    
    # Show exchange-specific status
    for exchange, info in state_summary.get('exchanges', {}).items():
        logger.info(f"{exchange}: {info.get('total_symbols', 0)} symbols, "
                   f"{info.get('stale_symbols', 0)} stale")
    
    # Show update statistics
    stats = manager.get_update_statistics()
    logger.info("=== Update Statistics ===")
    for key, value in stats.items():
        logger.info(f"{key}: {value}")


async def main():
    """Main function to run examples."""
    examples = {
        '1': ("Basic Incremental Update", basic_incremental_update),
        '2': ("Custom Strategy", custom_strategy_example),
        '3': ("State Management", state_management_example),
        '4': ("Conflict Resolution", conflict_resolution_example),
        '5': ("Monitoring", monitoring_example),
    }
    
    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    
    choice = input("\nSelect example (1-5) or 'all' to run all: ").strip()
    
    if choice.lower() == 'all':
        for name, func in examples.values():
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {name}")
            logger.info(f"{'='*50}")
            try:
                await func()
            except Exception as e:
                logger.error(f"Example failed: {e}")
            logger.info(f"Completed: {name}\n")
    elif choice in examples:
        name, func = examples[choice]
        logger.info(f"Running: {name}")
        await func()
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
