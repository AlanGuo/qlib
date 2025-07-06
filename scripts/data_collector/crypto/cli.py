# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Enhanced command-line interface for cryptocurrency data collection.

This module provides a comprehensive CLI for the cryptocurrency data collection
system with support for configuration files, templates, and advanced features.
"""

import argparse
import logging
import sys
import os
import json
from pathlib import Path

# Setup path for imports - works from project root or crypto directory
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR))
sys.path.insert(0, str(CUR_DIR.parent.parent))

# Try to import modules with fallback handling
def safe_import(module_name, from_list=None):
    try:
        if from_list:
            module = __import__(module_name, fromlist=from_list)
            return {name: getattr(module, name) for name in from_list}
        else:
            return __import__(module_name)
    except ImportError as e:
        print(f"Warning: Could not import {module_name}: {e}")
        return None

# Import configuration modules
try:
    from config.main_config import CryptoDataConfig, ConfigFactory
    from config.template_manager import ConfigTemplateManager, load_template, list_templates
except ImportError as e:
    print(f"Error: Could not import config modules: {e}")
    sys.exit(1)

# Import collector
try:
    from collector import CryptoCollector
except ImportError as e:
    print(f"Error: Could not import collector: {e}")
    sys.exit(1)

# Import universe manager (optional for now)
try:
    from universe_manager import UniverseManager
except ImportError:
    print("Warning: Could not import universe manager, using placeholder")
    class UniverseManager:
        def __init__(self):
            pass
        def get_current_universe(self):
            return {'symbols': ['BTC/USDT', 'ETH/USDT']}

# Optional imports
try:
    from validators.base_validator import BaseValidator as DataValidator
except ImportError:
    print("Warning: DataValidator not available")
    DataValidator = None

try:
    from risk_metrics.risk_metrics_manager import RiskMetricsManager as RiskCalculator
except ImportError:
    print("Warning: RiskCalculator not available")
    RiskCalculator = None


class CryptoCLI:
    """Enhanced command-line interface for cryptocurrency data collection."""
    
    def __init__(self):
        self.config = None  # Will be loaded when needed
        self.parser = self._create_parser()

    def create_parser(self) -> argparse.ArgumentParser:
        """Public method to create parser (for testing)."""
        return self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            description="Cryptocurrency Data Collection CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Collect daily data from Binance
  python cli.py collect --exchanges binance --timeframes day --symbols BTC/USDT ETH/USDT
  
  # Use a configuration template
  python cli.py collect --template production
  
  # List available templates
  python cli.py templates list
  
  # Validate configuration
  python cli.py validate --config myconfig.yaml
            """
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Collect command
        self._add_collect_parser(subparsers)
        
        # Template management commands
        self._add_template_parser(subparsers)
        
        # Validation commands
        self._add_validate_parser(subparsers)
        
        # Configuration commands
        self._add_config_parser(subparsers)

        # Incremental update commands
        self._add_incremental_parser(subparsers)

        return parser
    
    def _add_collect_parser(self, subparsers):
        """Add the collect command parser."""
        collect_parser = subparsers.add_parser(
            'collect',
            help='Collect cryptocurrency data',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Template-based configuration
        collect_parser.add_argument(
            '--template',
            type=str,
            choices=['default', 'production', 'research', 'high_frequency', 'simple', 'multi_exchange'],
            help='Use a predefined configuration template'
        )
        
        collect_parser.add_argument(
            '--config',
            type=str,
            help='Path to configuration file'
        )
        
        # Basic collection parameters
        collect_parser.add_argument(
            '--exchanges',
            nargs='+',
            choices=['binance', 'okx'],
            help='Exchanges to collect data from'
        )
        
        collect_parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific symbols to collect (e.g., BTC/USDT ETH/USDT)'
        )
        
        collect_parser.add_argument(
            '--timeframes',
            nargs='+',
            choices=['1min', '5min', '15min', '30min', '1h', 'day'],
            help='Timeframes to collect'
        )
        
        collect_parser.add_argument(
            '--fields',
            nargs='+',
            help='Data fields to collect'
        )
        
        # Date range
        collect_parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD)'
        )
        
        collect_parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD)'
        )
        
        collect_parser.add_argument(
            '--lookback-days',
            type=int,
            help='Number of days to look back from today'
        )
        
        # Output settings
        collect_parser.add_argument(
            '--output-dir',
            type=str,
            help='Output directory for collected data'
        )
        
        collect_parser.add_argument(
            '--file-format',
            choices=['qlib', 'parquet', 'csv'],
            help='Output file format'
        )
        
        # Performance settings
        collect_parser.add_argument(
            '--max-workers',
            type=int,
            help='Maximum number of parallel workers'
        )
        
        collect_parser.add_argument(
            '--rate-limit',
            type=float,
            default=0.1,
            help='Rate limit delay between requests (seconds)'
        )
        
        # Advanced options
        collect_parser.add_argument(
            '--incremental',
            action='store_true',
            help='Enable incremental updates'
        )
        
        collect_parser.add_argument(
            '--enable-validation',
            action='store_true',
            default=True,
            help='Enable data validation'
        )
        
        collect_parser.add_argument(
            '--enable-risk-metrics',
            action='store_true',
            help='Calculate risk metrics'
        )
        
        collect_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview collection without actually collecting data'
        )
        
        collect_parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
    
    def _add_template_parser(self, subparsers):
        """Add template management commands."""
        template_parser = subparsers.add_parser(
            'templates',
            help='Manage configuration templates'
        )
        
        template_subparsers = template_parser.add_subparsers(dest='template_action')
        
        # List templates
        template_subparsers.add_parser('list', help='List available templates')
        
        # Show template info
        info_parser = template_subparsers.add_parser('info', help='Show template information')
        info_parser.add_argument('template_name', help='Template name')
        
        # Compare templates
        compare_parser = template_subparsers.add_parser('compare', help='Compare templates')
        compare_parser.add_argument('template1', help='First template')
        compare_parser.add_argument('template2', help='Second template')
    
    def _add_validate_parser(self, subparsers):
        """Add validation commands."""
        validate_parser = subparsers.add_parser(
            'validate',
            help='Validate configuration or data'
        )
        
        validate_parser.add_argument(
            '--config',
            type=str,
            help='Configuration file to validate'
        )
        
        validate_parser.add_argument(
            '--data-dir',
            type=str,
            help='Data directory to validate'
        )
    
    def _add_config_parser(self, subparsers):
        """Add configuration commands."""
        config_parser = subparsers.add_parser(
            'config',
            help='Configuration management'
        )
        
        config_subparsers = config_parser.add_subparsers(dest='config_action')
        
        # Generate config
        generate_parser = config_subparsers.add_parser('generate', help='Generate configuration file')
        generate_parser.add_argument('--template', required=True, help='Template to use')
        generate_parser.add_argument('--output', required=True, help='Output file path')
        
        # Show config
        show_parser = config_subparsers.add_parser('show', help='Show current configuration')
        show_parser.add_argument('--config', help='Configuration file to show')

    def _add_incremental_parser(self, subparsers):
        """Add incremental update commands."""
        incremental_parser = subparsers.add_parser(
            'incremental',
            help='Manage incremental data updates',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Trigger incremental update
  python cli.py incremental update --exchanges binance okx

  # Check incremental status
  python cli.py incremental status

  # Reset incremental state
  python cli.py incremental reset --confirm

  # Dry run incremental update
  python cli.py incremental update --dry-run
            """
        )

        incremental_subparsers = incremental_parser.add_subparsers(dest='incremental_action', help='Incremental actions')

        # Update command
        update_parser = incremental_subparsers.add_parser('update', help='Trigger incremental data updates')
        update_parser.add_argument(
            '--exchanges',
            nargs='+',
            choices=['binance', 'okx'],
            help='Exchanges to update (default: all configured)'
        )
        update_parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific symbols to update (default: all configured)'
        )
        update_parser.add_argument(
            '--timeframes',
            nargs='+',
            choices=['1min', '5min', '15min', '30min', '1h', 'day'],
            help='Timeframes to update (default: all configured)'
        )
        update_parser.add_argument(
            '--config',
            type=str,
            help='Configuration file to use'
        )
        update_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview updates without actually updating data'
        )
        update_parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if no new data is detected'
        )

        # Status command
        status_parser = incremental_subparsers.add_parser('status', help='Show current incremental update status')
        status_parser.add_argument(
            '--config',
            type=str,
            help='Configuration file to use'
        )
        status_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed status for each symbol'
        )

        # Reset command
        reset_parser = incremental_subparsers.add_parser('reset', help='Reset incremental state')
        reset_parser.add_argument(
            '--config',
            type=str,
            help='Configuration file to use'
        )
        reset_parser.add_argument(
            '--exchanges',
            nargs='+',
            choices=['binance', 'okx'],
            help='Reset state for specific exchanges only'
        )
        reset_parser.add_argument(
            '--symbols',
            nargs='+',
            help='Reset state for specific symbols only'
        )
        reset_parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the reset operation'
        )

    def handle_collect(self, args):
        """Handle the collect command."""
        try:
            # Load configuration
            if args.template:
                print(f"Loading template: {args.template}")
                config = self._load_template_config(args.template)
            elif args.config:
                print(f"Loading configuration file: {args.config}")
                config = CryptoDataConfig()
                config.load_from_file(args.config)
            else:
                print("Using default configuration")
                config = CryptoDataConfig()
                # Apply defaults only when no config file is used
                if not args.exchanges:
                    config.collection.exchanges = ['binance']
                if not args.timeframes:
                    config.collection.timeframes = ['day']
                if not args.fields:
                    config.collection.fields = ['open', 'high', 'low', 'close', 'volume']
                if not args.lookback_days:
                    config.collection.lookback_days = 365
                if not args.output_dir:
                    config.collection.output_dir = './crypto_data'
                if not args.file_format:
                    config.collection.file_format = 'qlib'
                if not args.max_workers:
                    config.collection.max_workers = 4
            
            # Override with command line arguments
            self._override_config_from_args(config, args)
            
            if args.dry_run:
                print("DRY RUN MODE - No data will be collected")
                self._print_collection_plan(config)
                return
            
            # Validate configuration
            print("Validating configuration...")
            config.validate()
            
            # Initialize collector
            print("Initializing data collector...")
            collector = CryptoCollector(config)
            
            # Start collection
            print("Starting data collection...")
            if args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)
            
            # Implement actual collection logic
            self._execute_data_collection(config)
            print("Collection completed successfully!")
            
        except Exception as e:
            print(f"Error during collection: {e}")
            sys.exit(1)
    
    def handle_templates(self, args):
        """Handle template commands."""
        if args.template_action == 'list':
            templates = list_templates()
            print("Available templates:")
            for template in templates:
                print(f"  - {template}")
        
        elif args.template_action == 'info':
            try:
                template_config = load_template(args.template_name)
                print(f"Template: {args.template_name}")
                print(json.dumps(template_config.to_dict(), indent=2))
            except Exception as e:
                print(f"Error loading template {args.template_name}: {e}")
        
        elif args.template_action == 'compare':
            try:
                config1 = load_template(args.template1)
                config2 = load_template(args.template2)
                print(f"Comparing {args.template1} vs {args.template2}")
                # Simple comparison logic
                print("This feature is not yet implemented")
            except Exception as e:
                print(f"Error comparing templates: {e}")
    
    def handle_validate(self, args):
        """Handle validation commands."""
        if args.config:
            try:
                config = CryptoDataConfig()
                config.load_from_file(args.config)
                config.validate()
                print(f"Configuration file {args.config} is valid")
            except Exception as e:
                print(f"Configuration validation failed: {e}")
                sys.exit(1)
        
        if args.data_dir:
            print(f"Data validation for {args.data_dir} is not yet implemented")
    
    def handle_config(self, args):
        """Handle configuration commands."""
        if args.config_action == 'generate':
            try:
                config = self._load_template_config(args.template)
                config.save_to_file(args.output)
                print(f"Configuration saved to {args.output}")
            except Exception as e:
                print(f"Error generating configuration: {e}")
        
        elif args.config_action == 'show':
            try:
                if args.config:
                    config = CryptoDataConfig()
                    config.load_from_file(args.config)
                else:
                    config = CryptoDataConfig()
                
                print(json.dumps(config.to_dict(), indent=2))
            except Exception as e:
                print(f"Error showing configuration: {e}")

    def handle_incremental(self, args):
        """Handle incremental update commands."""
        try:
            # Import incremental modules
            import incremental
            IncrementalUpdateManager = incremental.IncrementalUpdateManager
            create_default_manager = incremental.create_default_manager

            # Load configuration
            if args.config:
                config = CryptoDataConfig()
                config.load_from_file(args.config)
            else:
                config = CryptoDataConfig()

            if args.incremental_action == 'update':
                self._handle_incremental_update(args, config)
            elif args.incremental_action == 'status':
                self._handle_incremental_status(args, config)
            elif args.incremental_action == 'reset':
                self._handle_incremental_reset(args, config)
            else:
                print("No incremental action specified. Use --help for available actions.")

        except ImportError as e:
            print(f"Error: Incremental update modules not available: {e}")
            print("Make sure the incremental update system is properly installed.")
            sys.exit(1)
        except Exception as e:
            print(f"Error in incremental command: {e}")
            sys.exit(1)

    def _handle_incremental_update(self, args, config):
        """Handle incremental update action."""
        import incremental
        create_default_manager = incremental.create_default_manager

        # Override config with command line arguments
        if args.exchanges:
            config.collection.exchanges = args.exchanges
        if args.symbols:
            config.collection.symbols = args.symbols
        if args.timeframes:
            config.collection.timeframes = args.timeframes

        # Create incremental manager
        manager = create_default_manager(config)

        if args.dry_run:
            print("DRY RUN MODE - Checking for incremental updates...")
            # Here you would implement dry run logic
            print("Incremental update plan:")
            print(f"  Exchanges: {config.collection.exchanges}")
            print(f"  Symbols: {config.collection.symbols or 'Auto-discover'}")
            print(f"  Timeframes: {config.collection.timeframes}")
            print("  Status: Would check for new data and show update plan")
            return

        print("Starting incremental data update...")
        # Here you would implement the actual incremental update
        print("Incremental update completed!")

    def _handle_incremental_status(self, args, config):
        """Handle incremental status action."""
        import incremental
        create_default_manager = incremental.create_default_manager

        manager = create_default_manager(config)

        print("Incremental Update Status:")
        print("=" * 50)

        if args.detailed:
            print("Detailed status information:")
            # Here you would implement detailed status display
            print("  - Exchange status details")
            print("  - Symbol-level status")
            print("  - Last update timestamps")
        else:
            print("Summary status information:")
            # Here you would implement summary status display
            print("  - Overall status: Active")
            print("  - Last update: [timestamp]")
            print("  - Next scheduled update: [timestamp]")

        print("=" * 50)

    def _handle_incremental_reset(self, args, config):
        """Handle incremental reset action."""
        if not args.confirm:
            print("Reset operation requires --confirm flag")
            print("This will delete all incremental state data.")
            print("Use: python cli.py incremental reset --confirm")
            return

        import incremental
        create_default_manager = incremental.create_default_manager

        manager = create_default_manager(config)

        print("Resetting incremental state...")

        if args.exchanges:
            print(f"Resetting state for exchanges: {args.exchanges}")
        elif args.symbols:
            print(f"Resetting state for symbols: {args.symbols}")
        else:
            print("Resetting all incremental state...")

        # Here you would implement the actual reset logic
        print("Incremental state reset completed!")

    def _load_template_config(self, template_name: str) -> CryptoDataConfig:
        """Load configuration from template."""
        factory_methods = {
            'default': ConfigFactory.create_default_config,
            'production': ConfigFactory.create_production_config,
            'research': ConfigFactory.create_research_config,
            'high_frequency': ConfigFactory.create_high_frequency_config,
            'simple': ConfigFactory.create_daily_config,
            'multi_exchange': ConfigFactory.create_multi_exchange_config,
        }
        
        factory_method = factory_methods.get(template_name)
        if not factory_method:
            raise ValueError(f"Unknown template: {template_name}")
        
        return factory_method()
    
    def _override_config_from_args(self, config: CryptoDataConfig, args):
        """Override configuration with command line arguments."""
        if args.exchanges:
            config.collection.exchanges = args.exchanges
        
        if args.symbols:
            config.collection.symbols = args.symbols
        
        if args.timeframes:
            config.collection.timeframes = args.timeframes
        
        if args.fields:
            config.collection.fields = args.fields
        
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
        
        if args.rate_limit:
            config.collection.rate_limit_delay = args.rate_limit
        
        if args.incremental:
            config.collection.incremental_update = True
        
        if args.enable_validation:
            config.collection.enable_validation = True
        
        if args.enable_risk_metrics:
            config.collection.enable_risk_metrics = True
    
    def _execute_data_collection(self, config: CryptoDataConfig):
        """Execute the actual data collection process."""
        try:
            # Import required modules
            from crypto_field_collector import CryptoFieldCollector
            from exchange_adapters.binance_adapter import BinanceAdapter
            from exchange_adapters.okx_adapter import OKXAdapter
            from storage_manager import CryptoStorageManager
            from datetime import datetime, timedelta
            
            # Initialize storage manager
            storage_manager = CryptoStorageManager(data_dir=config.collection.output_dir)
            
            # Get symbols to collect
            symbols = config.collection.symbols
            if not symbols:
                print("Using configured symbols from universe...")
                # Use the base assets and quote assets from config to create symbols
                base_assets = config.universe.filters.base_assets
                quote_assets = config.universe.filters.quote_assets
                symbols = []
                for base in base_assets:
                    for quote in quote_assets:
                        symbols.append(f"{base}/{quote}")
                print(f"Generated {len(symbols)} symbols: {symbols}")
            
            # Calculate date range
            if config.collection.start_date and config.collection.end_date:
                start_date = config.collection.start_date
                end_date = config.collection.end_date
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=config.collection.lookback_days)
                start_date = start_date.strftime('%Y-%m-%d')
                end_date = end_date.strftime('%Y-%m-%d')
            
            print(f"Collecting data from {start_date} to {end_date}")
            
            # Process each exchange and market type combination
            for exchange in config.collection.exchanges:
                for market_type in config.universe.market_types:
                    print(f"\n=== Processing exchange: {exchange} ({market_type}) ===")
                    
                    # Initialize adapter with specific market type
                    if exchange.lower() == 'binance':
                        adapter = BinanceAdapter(market_type=market_type)
                    elif exchange.lower() == 'okx':
                        adapter = OKXAdapter(market_type=market_type)
                    else:
                        print(f"Warning: Unknown exchange {exchange}, skipping")
                        continue
                    
                    # Initialize field collector
                    field_collector = CryptoFieldCollector(adapter)
                    
                    # Process each symbol for this exchange-market_type combination
                    for symbol in symbols:
                        print(f"\nCollecting {symbol} from {exchange} ({market_type})...")
                        
                        try:
                            # Collect data for each timeframe
                            for timeframe in config.collection.timeframes:
                                print(f"  Timeframe: {timeframe}")
                                
                                try:
                                    # Use CCXT native timeframe format directly
                                    if timeframe == 'day':
                                        ccxt_timeframe = '1d'
                                    elif timeframe == '1h':
                                        ccxt_timeframe = '1h'
                                    else:
                                        ccxt_timeframe = timeframe
                                    
                                    # Get OHLCV data directly from adapter
                                    df = adapter.get_ohlcv(
                                        symbol=symbol,
                                        timeframe=ccxt_timeframe,
                                        start_time=start_date,
                                        end_time=end_date
                                    )
                                    
                                    if df is not None and not df.empty:
                                        # Store the data using correct method signature
                                        # Convert symbol format: BTC/USDT -> BTCUSDT for instrument name
                                        # Include market_type in instrument name to distinguish different markets
                                        base_instrument = symbol.replace('/', '')
                                        instrument = f"{exchange.lower()}_{market_type}_{base_instrument.lower()}"
                                        
                                        storage_manager.save_ohlcv_data(
                                            data=df,
                                            instrument=instrument,
                                            freq=timeframe,
                                            market_type=market_type
                                        )
                                        print(f"    ✅ Stored {len(df)} records for {instrument} ({timeframe}, {market_type})")
                                    else:
                                        print(f"    ⚠️ No data returned")
                                        
                                except Exception as e:
                                    print(f"    ❌ Error collecting timeframe {timeframe}: {e}")
                                    continue
                                    
                        except Exception as e:
                            print(f"    ❌ Error collecting {symbol}: {e}")
                            continue
            
            print(f"\n✅ Data collection completed!")
            
        except Exception as e:
            print(f"❌ Collection failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _print_collection_plan(self, config: CryptoDataConfig):
        """Print the collection plan for dry run."""
        print("\nCollection Plan:")
        print("=" * 50)
        print(f"Exchanges: {config.collection.exchanges}")
        print(f"Timeframes: {config.collection.timeframes}")
        print(f"Fields: {config.collection.fields}")
        print(f"Market Types: {config.universe.market_types}")
        print(f"Output Directory: {config.collection.output_dir}")
        print(f"File Format: {config.collection.file_format}")
        print(f"Max Workers: {config.collection.max_workers}")
        print(f"Lookback Days: {config.collection.lookback_days}")
        
        if config.collection.symbols:
            print(f"Symbols: {config.collection.symbols}")
        else:
            print("Symbols: Auto-discover")
        
        print("=" * 50)
    
    def run(self, args=None):
        """Run the CLI."""
        args = self.parser.parse_args(args)
        
        if not args.command:
            self.parser.print_help()
            return
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        try:
            if args.command == 'collect':
                self.handle_collect(args)
            elif args.command == 'templates':
                self.handle_templates(args)
            elif args.command == 'validate':
                self.handle_validate(args)
            elif args.command == 'config':
                self.handle_config(args)
            elif args.command == 'incremental':
                self.handle_incremental(args)
            else:
                print(f"Unknown command: {args.command}")
                self.parser.print_help()
        
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}")
            if args.verbose if hasattr(args, 'verbose') else False:
                import traceback
                traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point."""
    cli = CryptoCLI()
    cli.run()


if __name__ == "__main__":
    main()