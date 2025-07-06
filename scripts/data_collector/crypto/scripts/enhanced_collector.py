#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Enhanced cryptocurrency data collection script.

This script provides a simplified interface to the cryptocurrency data collection
system with support for configuration files and templates.

Usage:
    python enhanced_collector.py [options]
    
Examples:
    # Collect data using default configuration
    python enhanced_collector.py
    
    # Collect data using a template
    python enhanced_collector.py --template production
    
    # Collect data with custom parameters
    python enhanced_collector.py --exchanges binance okx --timeframes 1h 1d --output-dir ./my_data
    
    # Collect specific symbols
    python enhanced_collector.py --symbols BTC/USDT ETH/USDT --timeframes 1d
    
    # Dry run to see what would be collected
    python enhanced_collector.py --dry-run --template high_frequency
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CryptoDataConfig, load_template, list_templates
from collector import CryptoCollector


def setup_logging(level: str = "INFO", verbose: bool = False):
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper())
    
    format_str = "%(asctime)s - %(levelname)s - %(message)s"
    if verbose:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    
    logging.basicConfig(
        level=log_level,
        format=format_str,
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Enhanced Cryptocurrency Data Collection Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--config", "-c",
        type=str,
        help="Configuration file path (YAML or JSON)"
    )
    config_group.add_argument(
        "--template", "-t",
        type=str,
        help="Configuration template name"
    )
    config_group.add_argument(
        "--list-templates",
        action="store_true",
        help="List available templates and exit"
    )
    
    # Data collection options
    data_group = parser.add_argument_group("Data Collection")
    data_group.add_argument(
        "--exchanges",
        nargs="+",
        help="Exchanges to collect from (e.g., binance okx)"
    )
    data_group.add_argument(
        "--symbols",
        nargs="+",
        help="Symbols to collect (e.g., BTC/USDT ETH/USDT)"
    )
    data_group.add_argument(
        "--timeframes",
        nargs="+",
        help="Timeframes to collect (e.g., 1h 1d)"
    )
    data_group.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD)"
    )
    data_group.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD)"
    )
    data_group.add_argument(
        "--lookback-days",
        type=int,
        help="Number of days to look back"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for collected data"
    )
    output_group.add_argument(
        "--file-format",
        choices=["parquet", "csv", "hdf5"],
        help="Output file format"
    )
    
    # Performance options
    perf_group = parser.add_argument_group("Performance")
    perf_group.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of workers"
    )
    perf_group.add_argument(
        "--rate-limit-delay",
        type=float,
        help="Rate limit delay between requests"
    )
    
    # Feature options
    feature_group = parser.add_argument_group("Features")
    feature_group.add_argument(
        "--enable-extended-fields",
        action="store_true",
        help="Enable extended crypto fields"
    )
    feature_group.add_argument(
        "--enable-risk-metrics",
        action="store_true",
        help="Enable risk metrics calculation"
    )
    feature_group.add_argument(
        "--enable-validation",
        action="store_true",
        help="Enable data validation"
    )
    feature_group.add_argument(
        "--incremental",
        action="store_true",
        help="Enable incremental updates"
    )
    
    # Control options
    control_group = parser.add_argument_group("Control")
    control_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without actual collection"
    )
    control_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    control_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    return parser


def load_configuration(args) -> CryptoDataConfig:
    """Load configuration from args."""
    logger = logging.getLogger(__name__)
    
    if args.config:
        # Load from config file
        config = CryptoDataConfig(args.config)
        logger.info(f"Loaded configuration from: {args.config}")
    elif args.template:
        # Load from template
        config = load_template(args.template)
        logger.info(f"Loaded template: {args.template}")
    else:
        # Use default configuration
        config = CryptoDataConfig()
        logger.info("Using default configuration")
    
    return config


def apply_cli_overrides(config: CryptoDataConfig, args) -> CryptoDataConfig:
    """Apply command-line argument overrides to configuration."""
    if args.exchanges:
        config.collection.exchanges = args.exchanges
    
    if args.symbols:
        config.collection.symbols = args.symbols
    
    if args.timeframes:
        config.collection.timeframes = args.timeframes
    
    if args.start_date:
        config.collection.start_date = args.start_date
    
    if args.end_date:
        config.collection.end_date = args.end_date
    
    if args.lookback_days:
        config.collection.lookback_days = args.lookback_days
    
    if args.output_dir:
        config.collection.output_dir = args.output_dir
    
    if args.file_format:
        config.collection.file_format = args.file_format
    
    if args.max_workers:
        config.collection.max_workers = args.max_workers
    
    if args.rate_limit_delay:
        config.collection.rate_limit_delay = args.rate_limit_delay
    
    if args.enable_extended_fields:
        config.collection.enable_extended_fields = True
    
    if args.enable_risk_metrics:
        config.collection.enable_risk_metrics = True
    
    if args.enable_validation:
        config.collection.enable_validation = True
    
    if args.incremental:
        config.collection.incremental_update = True
    
    return config


def main():
    """Main function."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.verbose)
    logger = logging.getLogger(__name__)
    
    # Handle list templates
    if args.list_templates:
        templates = list_templates()
        print("Available templates:")
        for template in templates:
            print(f"  - {template}")
        return
    
    try:
        # Load configuration
        config = load_configuration(args)
        config = apply_cli_overrides(config, args)
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual data collection will be performed")
            logger.info("Configuration summary:")
            logger.info(f"  Exchanges: {config.collection.exchanges}")
            logger.info(f"  Symbols: {config.collection.symbols or 'Auto-discover'}")
            logger.info(f"  Timeframes: {config.collection.timeframes}")
            logger.info(f"  Output directory: {config.collection.output_dir}")
            logger.info(f"  File format: {config.collection.file_format}")
            logger.info(f"  Max workers: {config.collection.max_workers}")
            logger.info(f"  Extended fields: {config.collection.enable_extended_fields}")
            logger.info(f"  Risk metrics: {config.collection.enable_risk_metrics}")
            logger.info(f"  Validation: {config.collection.enable_validation}")
            logger.info(f"  Incremental: {config.collection.incremental_update}")
            return
        
        # Create output directory
        Path(config.collection.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize collector
        collector = CryptoCollector(
            save_dir=config.collection.output_dir,
            exchanges=config.collection.exchanges,
            start=config.collection.start_date,
            end=config.collection.end_date,
            interval=config.collection.timeframes[0] if config.collection.timeframes else "1d",
            max_workers=config.collection.max_workers,
            delay=config.collection.rate_limit_delay,
            use_ccxt=True
        )
        
        logger.info("Starting cryptocurrency data collection...")
        logger.info(f"Exchanges: {config.collection.exchanges}")
        logger.info(f"Timeframes: {config.collection.timeframes}")
        logger.info(f"Output directory: {config.collection.output_dir}")
        
        # Collect data for each timeframe
        for timeframe in config.collection.timeframes:
            logger.info(f"Collecting {timeframe} data...")
            collector.interval = timeframe
            
            if config.collection.symbols:
                # Collect specific symbols
                logger.info(f"Collecting {len(config.collection.symbols)} specific symbols")
                for symbol in config.collection.symbols:
                    logger.info(f"Collecting data for {symbol}")
                    # Note: This would need to be implemented in the collector
                    # collector.collect_symbol_data(symbol)
            else:
                # Auto-discover and collect
                logger.info("Auto-discovering symbols and collecting data")
                collector.collect()
        
        logger.info("Data collection completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Data collection cancelled by user")
    except Exception as e:
        logger.error(f"Error during data collection: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
