# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Storage manager for cryptocurrency data in Qlib format.

This module provides the CryptoStorageManager class that handles conversion
and storage of cryptocurrency data in Qlib's standard binary format.
"""

import os
import struct
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

from qlib.data.storage.file_storage import FileFeatureStorage, FileInstrumentStorage, FileCalendarStorage
from qlib.data.storage import FeatureStorage, InstrumentStorage, CalendarStorage
from qlib.config import C
from qlib.utils.time import Freq
from qlib.utils import get_module_logger
import qlib

from config.fields import STANDARD_FIELDS, CRYPTO_SPECIFIC_FIELDS
from config.timeframes import TIMEFRAME_MAPPING, validate_timeframe


def convert_to_qlib_freq(timeframe: str) -> str:
    """
    Convert crypto timeframe to qlib frequency format.

    Parameters
    ----------
    timeframe : str
        Crypto timeframe (e.g., "1h", "1d", "5m")

    Returns
    -------
    str
        Qlib frequency format (e.g., "60min", "day", "5min")
    """
    # Mapping from crypto timeframes to qlib frequencies
    qlib_freq_mapping = {
        # Minutes
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",

        # Hours (convert to minutes)
        "1h": "60min",
        "2h": "120min",
        "4h": "240min",
        "6h": "360min",
        "8h": "480min",
        "12h": "720min",

        # Days
        "1d": "day",
        "3d": "3day",  # Not standard but might work

        # Weeks
        "1w": "week",

        # Months
        "1M": "month",
    }

    return qlib_freq_mapping.get(timeframe, timeframe)


class CryptoStorageManager:
    """
    Manager for cryptocurrency data storage in Qlib format.
    
    This class handles the conversion and storage of cryptocurrency data
    from various formats (parquet, CSV) to Qlib's standard binary format.
    """
    
    def __init__(self,
                 data_dir: str,
                 provider_uri: Optional[Dict] = None,
                 create_dirs: bool = True):
        """
        Initialize crypto storage manager.

        Parameters
        ----------
        data_dir : str
            Base directory for Qlib data storage
        provider_uri : dict, optional
            Provider URI configuration for Qlib
        create_dirs : bool, default True
            Whether to create directories if they don't exist
        """
        self.data_dir = Path(data_dir)

        # Initialize Qlib with minimal configuration
        qlib_config = {
            "provider_uri": str(self.data_dir),
            "mount_path": str(self.data_dir),
            "auto_mount": False,
            "flask_server": False,
            "logging_level": "INFO"
        }

        # Initialize qlib if not already initialized
        try:
            qlib.init(**qlib_config)
        except Exception:
            # Qlib might already be initialized, that's okay
            pass

        # Set default provider_uri if not provided
        if provider_uri is None:
            # Create provider_uri for qlib frequency formats pointing to qlib frequency directories
            self.provider_uri = {}

            for timeframe in TIMEFRAME_MAPPING.keys():
                # Convert to qlib frequency format
                qlib_freq = convert_to_qlib_freq(timeframe)
                # Map qlib frequency to the corresponding qlib frequency directory
                self.provider_uri[qlib_freq] = str(self.data_dir / qlib_freq)
            # Note: We don't add C.DEFAULT_FREQ to avoid Freq.parse() issues in support_freq
        else:
            self.provider_uri = provider_uri
        self.logger = get_module_logger("CryptoStorageManager")

        if create_dirs:
            self._create_directory_structure()
    
    def _create_directory_structure(self):
        """Create Qlib standard directory structure."""
        # Create base directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different timeframes using qlib frequency names
        for timeframe in TIMEFRAME_MAPPING.keys():
            qlib_freq = convert_to_qlib_freq(timeframe)
            timeframe_dir = self.data_dir / qlib_freq
            timeframe_dir.mkdir(exist_ok=True)
            
            # Create features, instruments, and calendars directories
            (timeframe_dir / "features").mkdir(exist_ok=True)
            (timeframe_dir / "instruments").mkdir(exist_ok=True)
            (timeframe_dir / "calendars").mkdir(exist_ok=True)
        
        self.logger.info(f"Created Qlib directory structure at {self.data_dir}")
    
    def save_feature_data(self, 
                         data: pd.Series,
                         instrument: str,
                         field: str,
                         freq: str,
                         market_type: str = None) -> None:
        """
        Save feature data in Qlib binary format.
        
        Parameters
        ----------
        data : pd.Series
            Time series data with datetime index
        instrument : str
            Instrument identifier (e.g., "binance_spot_btc_usdt")
        field : str
            Field name (e.g., "open", "close", "volume")
        freq : str
            Frequency/timeframe (e.g., "1d", "1h")
        market_type : str, optional
            Market type for validation/context
        """
        try:
            # Validate inputs
            if not validate_timeframe(freq):
                raise ValueError(f"Invalid timeframe: {freq}")

            if field not in STANDARD_FIELDS and field not in CRYPTO_SPECIFIC_FIELDS:
                self.logger.warning(f"Unknown field: {field}")

            # Convert to qlib frequency format
            qlib_freq = convert_to_qlib_freq(freq)
            # Create storage instance
            storage = FileFeatureStorage(
                instrument=instrument,
                field=field,
                freq=qlib_freq,
                provider_uri=self.provider_uri
            )
            
            # Ensure data is properly sorted by index
            if not data.index.is_monotonic_increasing:
                data = data.sort_index()
            
            # Convert to numpy array for storage
            data_array = data.values.astype(np.float32)

            # Ensure parent directory exists
            storage.uri.parent.mkdir(parents=True, exist_ok=True)

            # Write data to storage
            storage.write(data_array)
            
            self.logger.info(f"Saved {len(data)} records for {instrument}.{field}.{freq}")
            
        except Exception as e:
            self.logger.error(f"Failed to save feature data for {instrument}.{field}.{freq}: {e}")
            raise
    
    def save_ohlcv_data(self,
                       data: pd.DataFrame,
                       instrument: str,
                       freq: str,
                       market_type: str = None) -> None:
        """
        Save OHLCV data for an instrument.

        Parameters
        ----------
        data : pd.DataFrame
            OHLCV data with datetime index and columns: open, high, low, close, volume
        instrument : str
            Instrument identifier
        freq : str
            Frequency/timeframe
        market_type : str, optional
            Market type for validation/context
        """
        required_fields = ['open', 'high', 'low', 'close', 'volume']

        for field in required_fields:
            if field in data.columns:
                self.save_feature_data(data[field], instrument, field, freq, market_type)
            else:
                self.logger.warning(f"Missing field {field} for {instrument}")
    
    def save_crypto_specific_data(self,
                                 data: pd.DataFrame,
                                 instrument: str,
                                 freq: str,
                                 market_type: str = None) -> None:
        """
        Save crypto-specific data fields.
        
        Parameters
        ----------
        data : pd.DataFrame
            Data with crypto-specific fields
        instrument : str
            Instrument identifier
        freq : str
            Frequency/timeframe
        market_type : str, optional
            Market type for validation/context
        """
        crypto_fields = ['funding_rate', 'open_interest', 'volume_24h', 'change_24h']
        
        for field in crypto_fields:
            if field in data.columns:
                self.save_feature_data(data[field], instrument, field, freq, market_type)
    
    def load_feature_data(self,
                         instrument: str,
                         field: str,
                         freq: str,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> pd.Series:
        """
        Load feature data from Qlib storage.
        
        Parameters
        ----------
        instrument : str
            Instrument identifier
        field : str
            Field name
        freq : str
            Frequency/timeframe
        start_time : datetime, optional
            Start time for data range
        end_time : datetime, optional
            End time for data range
            
        Returns
        -------
        pd.Series
            Time series data
        """
        try:
            # Convert to qlib frequency format
            qlib_freq = convert_to_qlib_freq(freq)

            storage = FileFeatureStorage(
                instrument=instrument,
                field=field,
                freq=qlib_freq,
                provider_uri=self.provider_uri
            )
            
            # Load all data
            data = storage.data
            
            # Filter by time range if specified
            if start_time is not None:
                data = data[data.index >= start_time]
            if end_time is not None:
                data = data[data.index <= end_time]
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load feature data for {instrument}.{field}.{freq}: {e}")
            return pd.Series()

    def load_ohlcv_data(self,
                       instrument: str,
                       freq: str,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load OHLCV data from Qlib storage.

        Parameters
        ----------
        instrument : str
            Instrument identifier
        freq : str
            Frequency/timeframe
        start_time : datetime, optional
            Start time for data range
        end_time : datetime, optional
            End time for data range

        Returns
        -------
        pd.DataFrame
            OHLCV data with columns: open, high, low, close, volume
        """
        try:
            # Load all OHLCV fields
            ohlcv_fields = ['open', 'high', 'low', 'close', 'volume']
            data_dict = {}

            for field in ohlcv_fields:
                series = self.load_feature_data(
                    instrument=instrument,
                    field=field,
                    freq=freq,
                    start_time=start_time,
                    end_time=end_time
                )
                if not series.empty:
                    data_dict[field] = series

            if not data_dict:
                return pd.DataFrame()

            # Combine into DataFrame
            df = pd.DataFrame(data_dict)
            return df

        except Exception as e:
            self.logger.error(f"Failed to load OHLCV data for {instrument}.{freq}: {e}")
            return pd.DataFrame()

    def convert_parquet_to_qlib(self,
                               source_dir: str,
                               instrument_mapping: Optional[Dict[str, str]] = None) -> None:
        """
        Convert parquet files to Qlib binary format.
        
        Parameters
        ----------
        source_dir : str
            Directory containing parquet files
        instrument_mapping : dict, optional
            Mapping from source instrument names to Qlib format
        """
        source_path = Path(source_dir)
        
        if not source_path.exists():
            raise ValueError(f"Source directory does not exist: {source_dir}")
        
        # Find all parquet files
        parquet_files = list(source_path.glob("**/*.parquet"))
        
        self.logger.info(f"Found {len(parquet_files)} parquet files to convert")
        
        for parquet_file in parquet_files:
            try:
                self._convert_single_parquet(parquet_file, instrument_mapping)
            except Exception as e:
                self.logger.error(f"Failed to convert {parquet_file}: {e}")
    
    def _convert_single_parquet(self,
                               parquet_file: Path,
                               instrument_mapping: Optional[Dict[str, str]] = None) -> None:
        """Convert a single parquet file to Qlib format."""
        # Load parquet data
        df = pd.read_parquet(parquet_file)
        
        # Extract metadata from filename or data
        # This is a simplified implementation - you may need to adjust based on your file naming convention
        filename_parts = parquet_file.stem.split('_')
        
        if len(filename_parts) >= 3:
            exchange = filename_parts[0]
            symbol = '_'.join(filename_parts[1:-1])
            freq = filename_parts[-1]
        else:
            # Fallback: try to extract from data or use defaults
            exchange = "unknown"
            symbol = parquet_file.stem
            freq = "1d"
        
        # Create instrument identifier
        instrument = f"{exchange}_{symbol}".lower()
        
        if instrument_mapping and instrument in instrument_mapping:
            instrument = instrument_mapping[instrument]
        
        # Ensure datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'timestamp' in df.columns:
                df.set_index('timestamp', inplace=True)
            elif 'date' in df.columns:
                df.set_index('date', inplace=True)
            else:
                self.logger.warning(f"No datetime index found for {parquet_file}")
                return
        
        # Save OHLCV data
        self.save_ohlcv_data(df, instrument, freq)
        
        # Save crypto-specific data if available
        self.save_crypto_specific_data(df, instrument, freq)
        
        self.logger.info(f"Converted {parquet_file} -> {instrument}.{freq}")
    
    def create_instruments_file(self,
                               instruments: List[str],
                               market: str = "crypto",
                               freq: str = "1d") -> None:
        """
        Create instruments file for Qlib.
        
        Parameters
        ----------
        instruments : List[str]
            List of instrument identifiers
        market : str, default "crypto"
            Market name
        freq : str, default "1d"
            Frequency
        """
        try:
            storage = FileInstrumentStorage(
                market=market,
                freq=freq,
                provider_uri=self.provider_uri
            )
            
            # Create instrument data with start/end dates
            # For crypto, we assume 24/7 trading
            instrument_data = {}
            for instrument in instruments:
                # You may want to determine actual start/end dates from data
                instrument_data[instrument] = [
                    (datetime(2020, 1, 1), datetime(2030, 12, 31))
                ]
            
            # Write instrument data
            storage._write_instrument(instrument_data)
            
            self.logger.info(f"Created instruments file for {len(instruments)} instruments")
            
        except Exception as e:
            self.logger.error(f"Failed to create instruments file: {e}")
            raise
    
    def create_calendar_file(self,
                            start_date: datetime,
                            end_date: datetime,
                            freq: str = "1d",
                            future: bool = False) -> None:
        """
        Create calendar file for crypto trading (24/7).
        
        Parameters
        ----------
        start_date : datetime
            Start date for calendar
        end_date : datetime
            End date for calendar
        freq : str, default "1d"
            Frequency
        future : bool, default False
            Whether this is a future calendar
        """
        try:
            storage = FileCalendarStorage(
                freq=freq,
                future=future,
                provider_uri=self.provider_uri
            )
            
            # Generate 24/7 calendar for crypto
            if freq == "1d":
                calendar = pd.date_range(start=start_date, end=end_date, freq='D')
            elif freq == "1h":
                calendar = pd.date_range(start=start_date, end=end_date, freq='H')
            else:
                # For other frequencies, generate based on the frequency
                calendar = pd.date_range(start=start_date, end=end_date, freq=freq.upper())
            
            # Write calendar
            storage._write_calendar(calendar)
            
            self.logger.info(f"Created calendar file with {len(calendar)} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to create calendar file: {e}")
            raise
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about stored data.
        
        Returns
        -------
        dict
            Storage information including instruments, timeframes, and data ranges
        """
        info = {
            'data_dir': str(self.data_dir),
            'timeframes': {},
            'total_instruments': 0,
            'total_files': 0
        }
        
        # Get all qlib frequencies that should exist
        expected_qlib_freqs = set()
        for timeframe in TIMEFRAME_MAPPING.keys():
            qlib_freq = convert_to_qlib_freq(timeframe)
            expected_qlib_freqs.add(qlib_freq)
        
        for timeframe_dir in self.data_dir.iterdir():
            if timeframe_dir.is_dir() and timeframe_dir.name in expected_qlib_freqs:
                features_dir = timeframe_dir / "features"
                if features_dir.exists():
                    instruments = [d.name for d in features_dir.iterdir() if d.is_dir()]
                    
                    timeframe_info = {
                        'instruments': len(instruments),
                        'instrument_list': instruments[:10],  # First 10 for preview
                        'fields': set()
                    }
                    
                    # Count files and collect field names
                    file_count = 0
                    for instrument_dir in features_dir.iterdir():
                        if instrument_dir.is_dir():
                            for file in instrument_dir.glob("*.bin"):
                                file_count += 1
                                field_name = file.stem.split('.')[0]
                                timeframe_info['fields'].add(field_name)
                    
                    timeframe_info['files'] = file_count
                    timeframe_info['fields'] = list(timeframe_info['fields'])
                    
                    info['timeframes'][timeframe_dir.name] = timeframe_info
                    info['total_files'] += file_count
        
        # Calculate total unique instruments
        all_instruments = set()
        for tf_info in info['timeframes'].values():
            all_instruments.update(tf_info.get('instrument_list', []))
        info['total_instruments'] = len(all_instruments)
        
        return info
