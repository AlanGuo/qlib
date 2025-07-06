# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Cryptocurrency data collector for Qlib.

This module provides a unified interface for collecting cryptocurrency data
that is compatible with Qlib's standard data collector framework.
"""

import sys
import fire
from pathlib import Path
from typing import List, Optional, Dict, Any

# Setup path for imports - works from project root or crypto directory
CUR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CUR_DIR))
sys.path.insert(0, str(CUR_DIR.parent.parent))

# Import qlib base collector classes
try:
    from data_collector.base import BaseCollector as QlibBaseCollector, BaseNormalize, BaseRun
except ImportError:
    # Fallback for different qlib versions or when running from crypto directory
    try:
        from qlib.data.collector.base import BaseCollector as QlibBaseCollector, BaseNormalize, BaseRun
    except ImportError:
        QlibBaseCollector = object
        BaseNormalize = object
        BaseRun = object

# Import the existing crypto collector functionality
from config import CryptoDataConfig, ConfigFactory
from storage_manager import CryptoStorageManager


# Simple base class for our collector
class BaseCollectorLocal:
    """Simple base class for data collectors."""
    def __init__(self):
        try:
            from qlib.utils import get_module_logger
            self.logger = get_module_logger(self.__class__.__name__)
        except ImportError:
            import logging
            self.logger = logging.getLogger(self.__class__.__name__)


class CryptoCollector(BaseCollectorLocal):
    """
    Main cryptocurrency data collector.
    
    Integrates with Qlib's data provider system and supports multiple exchanges.
    """
    
    def __init__(self,
                 config: CryptoDataConfig = None,
                 storage_manager: Optional[CryptoStorageManager] = None):
        """
        Initialize crypto collector.
        
        Parameters
        ----------
        config : CryptoDataConfig, optional
            Configuration object for data collection
        storage_manager : CryptoStorageManager, optional
            Storage manager for handling data persistence
        """
        super().__init__()
        self.config = config or CryptoDataConfig()
        if storage_manager is None:
            # Use config's data directory or default
            data_dir = self.config.collection.qlib_data_dir or self.config.collection.output_dir or str(CUR_DIR / "data")
            self.storage_manager = CryptoStorageManager(data_dir=data_dir)
        else:
            self.storage_manager = storage_manager
        
        # Field collector will be initialized when needed with proper adapter
        self.field_collector = None
    
    def collect_data(self, symbols: List[str], start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Collect cryptocurrency data for specified symbols.
        
        Parameters
        ----------
        symbols : List[str]
            List of cryptocurrency symbols to collect
        start_date : str, optional
            Start date for data collection
        end_date : str, optional
            End date for data collection
            
        Returns
        -------
        Dict[str, Any]
            Collection results
        """
        # Initialize field collector with proper adapter when needed
        try:
            from crypto_field_collector import CryptoFieldCollector
            from exchange_adapters.binance_adapter import BinanceAdapter
            
            # Create adapter based on config
            adapter = BinanceAdapter()  # Default to Binance for now
            self.field_collector = CryptoFieldCollector(adapter)
            
            return self.field_collector.collect_data(symbols, start_date, end_date)
        except ImportError as e:
            self.logger.error(f"Could not initialize field collector: {e}")
            return {}


class Run:
    """Main runner class for crypto data collection, compatible with fire.Fire()"""
    
    def __init__(self, config_file: str = None, source_dir: str = None):
        """
        Initialize the crypto data collection runner.
        
        Parameters
        ----------
        config_file : str, optional
            Path to configuration file
        source_dir : str, optional
            Directory to save raw data, default "Path(__file__).parent/source"
        """
        self.config_file = config_file
        self.source_dir = source_dir or str(CUR_DIR / "source")
        self.collector = None
        
    @property
    def default_base_dir(self) -> Path:
        return CUR_DIR
    
    def collect(self,
                exchanges=None,
                timeframes=None,
                symbols=None,
                start_date=None,
                end_date=None,
                config_file=None,
                output_dir=None,
                template=None):
        """
        Collect cryptocurrency data.
        
        Parameters
        ----------
        exchanges : str or List[str], optional
            Exchange(s) to collect from (e.g., 'binance' or ['binance', 'okx'])
        timeframes : str or List[str], optional
            Timeframe(s) (e.g., 'day' or ['1h', 'day'])
        symbols : str or List[str], optional
            Symbol(s) (e.g., 'BTC/USDT' or ['BTC/USDT', 'ETH/USDT'])
        start_date : str, optional
            Start date in YYYY-MM-DD format
        end_date : str, optional
            End date in YYYY-MM-DD format
        config_file : str, optional
            Path to configuration file
        output_dir : str, optional
            Output directory for collected data
        template : str, optional
            Configuration template to use
        
        Examples
        --------
        # Collect daily data from Binance
        python collector.py collect --exchanges binance --timeframes day --symbols BTC/USDT
        
        # Collect using template
        python collector.py collect --template production
        """
        try:
            # Import CLI to avoid circular imports
            from cli import CryptoCLI
            
            # Create CLI instance
            cli = CryptoCLI()
            
            # Prepare arguments namespace
            import argparse
            args = argparse.Namespace()
            
            # Set arguments
            args.exchanges = [exchanges] if isinstance(exchanges, str) else exchanges
            args.timeframes = [timeframes] if isinstance(timeframes, str) else timeframes
            args.symbols = [symbols] if isinstance(symbols, str) else symbols
            args.start_date = start_date
            args.end_date = end_date
            args.config = config_file or self.config_file
            args.output_dir = output_dir
            args.template = template  # Don't force default template
            args.fields = None
            args.lookback_days = None
            args.file_format = 'qlib'
            args.max_workers = None
            args.rate_limit = None
            args.incremental = False
            args.enable_validation = False
            args.enable_risk_metrics = False
            args.dry_run = False
            args.verbose = False
            
            # Call the CLI handler directly
            cli.handle_collect(args)
            print("✅ Data collection completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during collection: {e}")
            raise
    
    def validate(self, data_dir: str = None, config_file: str = None):
        """
        Validate collected data.
        
        Parameters
        ----------
        data_dir : str, optional
            Directory containing data to validate
        config_file : str, optional
            Path to configuration file
        
        Examples
        --------
        python collector.py validate --data_dir ./data
        """
        from cli import CryptoCLI
        
        args = []
        if data_dir:
            args.extend(['--data-dir', data_dir])
        if config_file or self.config_file:
            args.extend(['--config-file', config_file or self.config_file])
        
        cli = CryptoCLI()
        parsed_args = cli.parser.parse_args(['validate'] + args)
        cli.handle_validate(parsed_args)
    
    def incremental_update(self, action: str = 'update', config_file: str = None):
        """
        Handle incremental data updates.
        
        Parameters
        ----------
        action : str
            Action to perform: 'update', 'status', or 'reset'
        config_file : str, optional
            Path to configuration file
        
        Examples
        --------
        python collector.py incremental_update --action update
        python collector.py incremental_update --action status
        """
        from cli import CryptoCLI
        
        args = [action]
        if config_file or self.config_file:
            args.extend(['--config-file', config_file or self.config_file])
        
        cli = CryptoCLI()
        parsed_args = cli.parser.parse_args(['incremental'] + args)
        cli.handle_incremental(parsed_args)
    
    def templates(self, action: str = 'list', template_name: str = None):
        """
        Manage configuration templates.
        
        Parameters
        ----------
        action : str
            Action to perform: 'list', 'info', or 'compare'
        template_name : str, optional
            Name of template (for info action)
        
        Examples
        --------
        python collector.py templates --action list
        python collector.py templates --action info --template_name simple
        """
        try:
            from cli import CryptoCLI
            import argparse
            
            # Create CLI instance
            cli = CryptoCLI()
            
            # Prepare arguments namespace
            args = argparse.Namespace()
            args.template_action = action
            args.template_name = template_name
            args.config = None
            
            # Call the CLI handler directly
            cli.handle_templates(args)
            
        except Exception as e:
            print(f"❌ Error managing templates: {e}")
            raise


if __name__ == "__main__":
    fire.Fire(Run)