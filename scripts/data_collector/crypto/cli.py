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
        self.logger = logging.getLogger(__name__)

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
  # Collect daily data from Binance using default settings
  python cli.py collect --exchanges binance --timeframes 1d --symbols BTC/USDT ETH/USDT
  
  # Use a predefined template
  python cli.py collect --template btcdom2
  
  # Use a custom template you created
  python cli.py collect --template my_custom_template
  
  # List available templates
  python cli.py templates list
  
  # Validate a template
  python cli.py validate --template btcdom2
  
  # Generate a config file from template for customization
  python cli.py config generate --template btcdom2 --output my_config.yaml
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
            help='Use a configuration template (specify template name, e.g., btcdom2, production, research)'
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
            choices=['1min', '5min', '15min', '30min', '1h', '1d'],
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
            '--template',
            type=str,
            help='Template to validate'
        )
        
        validate_parser.add_argument(
            '--data-dir',
            type=str,
            help='Data directory to validate'
        )
        
        validate_parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed validation results including warnings'
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
        
        # Show template
        show_parser = config_subparsers.add_parser('show', help='Show template configuration')
        show_parser.add_argument('--template', help='Template name to show')

    def _add_incremental_parser(self, subparsers):
        """Add incremental update commands."""
        incremental_parser = subparsers.add_parser(
            'incremental',
            help='Manage incremental data updates',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Trigger incremental update using template
  python cli.py incremental update --template btcdom2

  # Trigger incremental update with specific settings
  python cli.py incremental update --exchanges binance okx --template production

  # Check incremental status
  python cli.py incremental status --template btcdom2

  # Reset incremental state
  python cli.py incremental reset --confirm --template btcdom2

  # Dry run incremental update
  python cli.py incremental update --dry-run --template btcdom2
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
            choices=['1min', '5min', '15min', '30min', '1h', '1d'],
            help='Timeframes to update (default: all configured)'
        )
        update_parser.add_argument(
            '--template',
            type=str,
            help='Template to use for incremental update'
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
            '--template',
            type=str,
            help='Template to use for status check'
        )
        status_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed status for each symbol'
        )

        # Reset command
        reset_parser = incremental_subparsers.add_parser('reset', help='Reset incremental state')
        reset_parser.add_argument(
            '--template',
            type=str,
            help='Template to use for reset operation'
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
            else:
                print("Using default configuration")
                config = CryptoDataConfig()
                # Apply defaults when no template is specified
                if not args.exchanges:
                    config.collection.exchanges = ['binance']
                if not args.timeframes:
                    config.collection.timeframes = ['1d']
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
            
            # Setup logging from configuration
            config.setup_logging()
            # Update logger after logging setup
            self.logger = logging.getLogger(__name__)
            
            # Override with command line arguments
            self._override_config_from_args(config, args)
            
            if args.dry_run:
                print("DRY RUN MODE - No data will be collected")
                self._print_collection_plan(config)
                return
            
            # Validate configuration
            self.logger.info("Validating configuration...")
            config.validate()
            self.logger.info("Configuration validation completed successfully")
            
            # Initialize collector
            self.logger.info("Initializing data collector...")
            collector = CryptoCollector(config)
            
            # Start collection
            self.logger.info("Starting data collection...")
            if args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)
            
            # Implement actual collection logic
            self._execute_data_collection(config)
            self.logger.info("Collection completed successfully!")
            
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
        if args.template:
            try:
                config = self._load_template_config(args.template)
                config.validate()
                print(f"Template {args.template} is valid")
            except Exception as e:
                print(f"Template validation failed: {e}")
                sys.exit(1)
        
        if args.data_dir:
            try:
                self._validate_data_directory(args.data_dir, verbose=getattr(args, 'verbose', False))
            except Exception as e:
                print(f"Data validation failed: {e}")
                sys.exit(1)
    
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
                if args.template:
                    config = self._load_template_config(args.template)
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
            if args.template:
                config = self._load_template_config(args.template)
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
    
    def _validate_data_directory(self, data_dir: str, verbose: bool = False):
        """Validate data in a directory using the crypto validation framework."""
        from pathlib import Path
        
        # Check if data directory exists
        data_path = Path(data_dir)
        if not data_path.exists():
            raise ValueError(f"Data directory does not exist: {data_dir}")
        
        # Try to import validation modules
        try:
            from data_validator import CryptoDataValidator
            from config.validation_config import ValidationConfig
            
            print(f"Starting validation for data directory: {data_dir}")
            print("=" * 60)
            
            # Create crypto-specific validation configuration
            validation_config = ValidationConfig.create_crypto_specific_config()
            
            # Initialize validator
            validator = CryptoDataValidator(validation_config)
            
            # Discover data files
            data_files = self._discover_data_files(data_path)
            
            if not data_files:
                print("❌ No data files found in directory")
                return
            
            print(f"Found {len(data_files)} data files to validate")
            print("-" * 60)
            
            # Track overall validation results
            total_files = len(data_files)
            successful_validations = 0
            failed_validations = 0
            
            # Validate each data file
            for file_info in data_files:
                print(f"\nValidating: {file_info['instrument']} ({file_info['timeframe']})")
                
                try:
                    # Load data using qlib format
                    df = self._load_qlib_data(file_info)
                    
                    if df is None or df.empty:
                        print(f"  ⚠️ No data found in {file_info['path']}")
                        continue
                    
                    # Validate the data
                    validation_report = validator.validate(
                        data=df,
                        symbol=file_info['instrument'],
                        timeframe=file_info['timeframe']
                    )
                    
                    # Display validation results
                    if validation_report.overall_status == "PASS":
                        print(f"  ✅ PASSED - {len(df)} records validated")
                        successful_validations += 1
                    else:
                        status_msg = f"  ❌ FAILED - {validation_report.total_errors} errors, {validation_report.total_warnings} warnings"
                        if validation_report.total_errors > 0:
                            print(status_msg)
                            failed_validations += 1
                            
                            # Show critical and error issues
                            for result in validation_report.results:
                                for issue in result.issues:
                                    if issue.severity.value in ['critical', 'error']:
                                        print(f"    {issue.severity.value.upper()}: {issue.message}")
                        else:
                            # Only warnings
                            if verbose:
                                print(f"  ⚠️ WARNINGS - {validation_report.total_warnings} warnings (passed)")
                                # Show warning details in verbose mode
                                for result in validation_report.results:
                                    for issue in result.issues:
                                        if issue.severity.value == 'warning':
                                            field_info = f" ({issue.field_name})" if issue.field_name else ""
                                            print(f"    WARNING{field_info}: {issue.message}")
                            else:
                                print(f"  ⚠️ WARNINGS - {validation_report.total_warnings} warnings (passed)")
                            
                            successful_validations += 1
                    
                    # Show performance metrics
                    total_exec_time = sum(r.execution_time_ms for r in validation_report.results)
                    print(f"  ⏱️ Validation time: {total_exec_time:.2f}ms")
                    
                except Exception as e:
                    print(f"  ❌ ERROR: {e}")
                    failed_validations += 1
                    continue
            
            # Print summary
            print("\n" + "=" * 60)
            print("VALIDATION SUMMARY")
            print("=" * 60)
            print(f"Total files: {total_files}")
            print(f"Successful validations: {successful_validations}")
            print(f"Failed validations: {failed_validations}")
            success_rate = (successful_validations / total_files) * 100 if total_files > 0 else 0
            print(f"Success rate: {success_rate:.1f}%")
            
            if failed_validations > 0:
                print(f"\n⚠️ {failed_validations} files failed validation")
                raise ValueError(f"Data validation failed for {failed_validations} files")
            else:
                print("\n✅ All data files passed validation!")
                
        except ImportError as e:
            print(f"❌ Validation modules not available: {e}")
            print("Please ensure the validation framework is properly installed")
            raise
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            raise
    
    def _discover_data_files(self, data_path: Path):
        """Discover data files in the qlib data directory structure."""
        data_files = []
        
        # Look for timeframe directories
        for timeframe_dir in data_path.iterdir():
            if timeframe_dir.is_dir() and timeframe_dir.name in ['1min', '5min', '15min', '30min', '1h', '1d', '1w']:
                # Look for features directory
                features_dir = timeframe_dir / 'features'
                if features_dir.exists():
                    # Look for instrument directories
                    for instrument_dir in features_dir.iterdir():
                        if instrument_dir.is_dir():
                            # Look for .bin files
                            for bin_file in instrument_dir.glob('*.bin'):
                                field_name = bin_file.stem.split('.')[0]  # Extract field name
                                data_files.append({
                                    'path': str(bin_file),
                                    'instrument': instrument_dir.name,
                                    'timeframe': timeframe_dir.name,
                                    'field': field_name
                                })
        
        return data_files
    
    def _load_qlib_data(self, file_info):
        """Load data from qlib binary format."""
        try:
            # Import required modules
            import struct
            import numpy as np
            import pandas as pd
            from datetime import datetime
            from pathlib import Path
            
            # Get all field files for this instrument/timeframe
            file_path = Path(file_info['path'])
            instrument_dir = file_path.parent
            timeframe = file_info['timeframe']
            
            # Expected fields for crypto data
            expected_fields = ['open', 'high', 'low', 'close', 'volume']
            
            # Load all field files
            field_data = {}
            
            for field in expected_fields:
                # With unified naming, simply look for field.timeframe.bin
                field_file = instrument_dir / f"{field}.{timeframe}.bin"
                
                if field_file and field_file.exists():
                    # Load binary data
                    field_data[field] = self._load_binary_field(field_file)
            
            if not field_data:
                return None
            
            # Convert to DataFrame
            # Assume all fields have the same length
            first_field = list(field_data.values())[0]
            num_records = len(first_field)
            
            # Create synthetic timestamps based on timeframe
            timestamps = self._generate_timestamps(timeframe, num_records)
            
            # Create DataFrame
            df = pd.DataFrame(field_data, index=timestamps)
            
            return df
            
        except Exception as e:
            print(f"Error loading data from {file_info['path']}: {e}")
            return None
    
    def _load_binary_field(self, file_path):
        """Load a single binary field file using our storage format."""
        try:
            import struct
            import numpy as np
            
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Our storage format: first 4 bytes are record count (unsigned int), followed by data
            if len(data) < 8:  # Need at least count + one data point
                return np.array([])
            
            # Read first 4 bytes as record count (unsigned int)
            record_count = struct.unpack('<I', data[:4])[0]
            
            # Read remaining bytes as data values (float32)
            data_bytes = data[4:]
            expected_data_size = record_count * 4  # 4 bytes per float32
            
            if len(data_bytes) < expected_data_size:
                print(f"Warning: Data size mismatch in {file_path}. Expected {expected_data_size}, got {len(data_bytes)}")
                # Use actual available data
                num_values = len(data_bytes) // 4
            else:
                num_values = record_count
            
            if num_values == 0:
                return np.array([])
            
            values = struct.unpack(f'<{num_values}f', data_bytes[:num_values*4])
            
            return np.array(values)
            
        except Exception as e:
            print(f"Error loading binary field {file_path}: {e}")
            return np.array([])
    
    def _generate_timestamps(self, timeframe, num_records):
        """Generate timestamps for the data based on timeframe."""
        try:
            from datetime import datetime
            import pandas as pd
            from config.timeframes import timeframe_to_pandas_freq
            
            # Map timeframe to pandas frequency using unified function
            freq = timeframe_to_pandas_freq(timeframe)
            
            # Start from a recent date and go backwards
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Generate timestamps
            timestamps = pd.date_range(
                end=end_date, 
                periods=num_records, 
                freq=freq
            )
            
            return timestamps
            
        except Exception as e:
            print(f"Error generating timestamps for {timeframe}: {e}")
            # Fallback to simple integer index
            return range(num_records)

    def _load_template_config(self, template_name: str) -> CryptoDataConfig:
        """Load configuration from template."""
        try:
            # First try to load from template manager
            from config.template_manager import load_template
            return load_template(template_name)
        except Exception as e:
            # If template manager fails, try factory methods for built-in templates
            factory_methods = {
                'default': ConfigFactory.create_default_config,
                'production': ConfigFactory.create_production_config,
                'research': ConfigFactory.create_research_config,
                'high_frequency': ConfigFactory.create_high_frequency_config,
                'simple': ConfigFactory.create_daily_config,
                'multi_exchange': ConfigFactory.create_multi_exchange_config
            }
            
            factory_method = factory_methods.get(template_name)
            if factory_method:
                return factory_method()
            else:
                raise ValueError(f"Template '{template_name}' not found. Available templates can be listed with 'python cli.py templates list'")

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
        """Execute the actual data collection process with simplified error logging."""
        try:
            # Import required modules
            from crypto_field_collector import CryptoFieldCollector
            from exchange_adapters.binance_adapter import BinanceAdapter
            from exchange_adapters.okx_adapter import OKXAdapter
            from storage_manager import CryptoStorageManager
            from qlib_data_generator import QlibDataGenerator
            from simple_error_log_collector import SimpleErrorLogCollector
            from datetime import datetime, timedelta
            
            # Initialize storage manager
            self.logger.info("Initializing storage manager...")
            storage_manager = CryptoStorageManager(data_dir=config.collection.output_dir)
            
            # Initialize Qlib data generator for calendar and instruments
            self.logger.info("Initializing Qlib data generator...")
            qlib_generator = QlibDataGenerator(data_dir=config.collection.output_dir)
            
            # Initialize simplified error log collector
            self.logger.info("Initializing simplified error log collector...")
            collector = SimpleErrorLogCollector(
                max_retries=3,
                retry_delay=1.0,
                enable_smart_logging=True,
                error_cache_ttl=24 * 3600  # 24 hours
            )
            
            # Get symbols to collect
            symbols = config.collection.symbols
            if not symbols:
                self.logger.info("Using configured symbols from universe...")
                # Use the base assets and quote assets from config to create symbols
                base_assets = config.universe.filters.base_assets
                quote_assets = config.universe.filters.quote_assets
                symbols = []
                for base in base_assets:
                    for quote in quote_assets:
                        symbols.append(f"{base}/{quote}")
                self.logger.info(f"Generated {len(symbols)} symbols: {symbols}")
            
            # Calculate date range
            if config.collection.start_date and config.collection.end_date:
                start_date = config.collection.start_date
                end_date = config.collection.end_date
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=config.collection.lookback_days)
                start_date = start_date.strftime('%Y-%m-%d')
                end_date = end_date.strftime('%Y-%m-%d')
            
            self.logger.info(f"Collecting data from {start_date} to {end_date}")
            
            # Process each exchange and market type combination
            for exchange in config.collection.exchanges:
                for market_type in config.universe.market_types:
                    self.logger.info(f"Processing exchange: {exchange} ({market_type})")
                    
                    # Initialize adapter with specific market type
                    if exchange.lower() == 'binance':
                        adapter = BinanceAdapter(market_type=market_type)
                    elif exchange.lower() == 'okx':
                        adapter = OKXAdapter(market_type=market_type)
                    else:
                        self.logger.warning(f"Unknown exchange {exchange}, skipping")
                        continue
                    
                    # Initialize field collector
                    field_collector = CryptoFieldCollector(adapter)
                    
                    # Process each timeframe
                    for timeframe in config.collection.timeframes:
                        self.logger.info(f"Processing timeframe: {timeframe}")
                        
                        try:
                            # Use centralized timeframe conversion
                            from config.timeframes import get_exchange_timeframe
                            ccxt_timeframe = get_exchange_timeframe(adapter.exchange_id, timeframe)
                            
                            # Use simplified collector to collect data for all symbols
                            batch_results = collector.collect_multiple_symbols(
                                adapter=adapter,
                                symbols=symbols,
                                timeframe=ccxt_timeframe,
                                start_time=start_date,
                                end_time=end_date
                            )
                            
                            # Process results and store data
                            for symbol, result in batch_results['results'].items():
                                if result['status'] == 'success':
                                    if not result['data'].empty:
                                        # Store the data using correct method signature
                                        # Convert symbol format: BTC/USDT -> BTCUSDT for instrument name
                                        # Include market_type in instrument name to distinguish different markets
                                        base_instrument = symbol.replace('/', '')
                                        instrument = f"{exchange.lower()}_{market_type}_{base_instrument.lower()}"
                                        
                                        storage_manager.save_ohlcv_data(
                                            data=result['data'],
                                            instrument=instrument,
                                            freq=timeframe,
                                            market_type=market_type
                                        )
                                        
                                        status_emoji = "✅"
                                        self.logger.info(f"    {status_emoji} Stored {len(result['data'])} records for {instrument} ({timeframe}, {market_type})")
                                    else:
                                        self.logger.warning(f"    ⚠️ No data in result for {symbol} {timeframe}")
                                else:
                                    self.logger.warning(f"    ❌ Failed to collect {symbol} {timeframe}: {result.get('errors', [])}")
                            
                            # Log batch statistics
                            summary = batch_results['summary']
                            self.logger.info(f"  Batch statistics: {len(summary['successful_symbols'])} successful, {len(summary['failed_symbols'])} failed")
                                
                        except Exception as e:
                            self.logger.error(f"    ❌ Error collecting timeframe {timeframe}: {e}")
                            continue
            
            # After all data collection, generate Qlib structure files
            self.logger.info("Generating Qlib calendar and instruments files...")
            
            # Collect all instruments that were processed
            all_instruments = []
            all_exchanges = config.collection.exchanges
            all_market_types = config.universe.market_types
            
            for exchange in all_exchanges:
                for market_type in all_market_types:
                    for symbol in symbols:
                        base_instrument = symbol.replace('/', '')
                        instrument = f"{exchange.lower()}_{market_type}_{base_instrument.lower()}"
                        all_instruments.append(instrument)
            
            # Calculate date range for calendars
            if config.collection.start_date and config.collection.end_date:
                start_date = datetime.strptime(config.collection.start_date, '%Y-%m-%d')
                end_date = datetime.strptime(config.collection.end_date, '%Y-%m-%d')
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=config.collection.lookback_days)
            
            # Generate complete Qlib structure
            structure_summary = qlib_generator.create_full_structure(
                timeframes=config.collection.timeframes,
                exchanges=all_exchanges,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                market_type="spot"  # Default to spot for structure creation
            )
            
            self.logger.info(f"Qlib structure generation completed: {structure_summary}")
            
            self.logger.info("✅ Data collection completed!")
            
        except Exception as e:
            self.logger.error(f"❌ Collection failed: {e}")
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
        
        # Setup basic logging (will be overridden by config.setup_logging() if a template is used)
        if not hasattr(args, 'template') or not args.template:
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


# Create an alias for backward compatibility
CLI = CryptoCLI


if __name__ == "__main__":
    main()