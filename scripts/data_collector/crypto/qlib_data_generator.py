# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Qlib data directory structure generator for cryptocurrency data.

This module provides utilities to create and maintain Qlib standard
data directory structures for cryptocurrency data.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd

from qlib.utils import get_module_logger
from qlib.data.storage.file_storage import FileInstrumentStorage, FileCalendarStorage

import sys
import os
from pathlib import Path

# Add the crypto directory to Python path
crypto_dir = Path(__file__).parent
sys.path.insert(0, str(crypto_dir))

from config.timeframes import TIMEFRAME_MAPPING, validate_timeframe, convert_for_qlib_internal
from config.fields import STANDARD_FIELDS, CRYPTO_SPECIFIC_FIELDS
from storage_manager import CryptoStorageManager


class QlibDataGenerator:
    """
    Generator for Qlib standard data directory structure.
    
    This class creates and maintains the standard Qlib data directory
    structure for cryptocurrency data, including instruments and calendars.
    """
    
    def __init__(self,
                 data_dir: str,
                 provider_uri: Optional[Union[str, Dict[str, str]]] = None):
        """
        Initialize Qlib data generator.

        Parameters
        ----------
        data_dir : str
            Base directory for Qlib data
        provider_uri : str or dict, optional
            Provider URI for Qlib storage (can be string or frequency mapping dict)
        """
        self.data_dir = Path(data_dir)
        
        # Ensure provider_uri is a string pointing to data_dir
        if provider_uri is None:
            self.provider_uri = str(data_dir)
        elif isinstance(provider_uri, dict):
            # If it's a dict, use the first value or default to data_dir
            self.provider_uri = list(provider_uri.values())[0] if provider_uri else str(data_dir)
        else:
            self.provider_uri = provider_uri
            
        self.logger = get_module_logger("QlibDataGenerator")
        
        # Ensure base directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def create_full_structure(self,
                             timeframes: List[str],
                             exchanges: List[str],
                             symbols: List[str],
                             start_date: datetime,
                             end_date: datetime,
                             market_type: str = "spot") -> Dict[str, any]:
        """
        Create complete Qlib data directory structure.
        
        Parameters
        ----------
        timeframes : List[str]
            List of timeframes to support
        exchanges : List[str]
            List of exchanges
        symbols : List[str]
            List of symbols
        start_date : datetime
            Start date for calendars
        end_date : datetime
            End date for calendars
            
        Returns
        -------
        dict
            Summary of created structure
        """
        summary = {
            'timeframes_created': 0,
            'instruments_files': 0,
            'calendar_files': 0,
            'feature_directories': 0,
            'errors': []
        }
        
        # Validate timeframes
        valid_timeframes = [tf for tf in timeframes if validate_timeframe(tf)]
        if len(valid_timeframes) != len(timeframes):
            invalid = set(timeframes) - set(valid_timeframes)
            self.logger.warning(f"Invalid timeframes ignored: {invalid}")
            summary['errors'].append(f"Invalid timeframes: {invalid}")
        
        # Create structure for each timeframe
        for timeframe in valid_timeframes:
            try:
                tf_summary = self._create_timeframe_structure(
                    timeframe, exchanges, symbols, start_date, end_date, market_type
                )
                
                summary['timeframes_created'] += 1
                summary['instruments_files'] += tf_summary['instruments_files']
                summary['calendar_files'] += tf_summary['calendar_files']
                summary['feature_directories'] += tf_summary['feature_directories']
                
            except Exception as e:
                error_msg = f"Failed to create structure for {timeframe}: {e}"
                self.logger.error(error_msg)
                summary['errors'].append(error_msg)
        
        self.logger.info(f"Created Qlib structure: {summary}")
        return summary
    
    def _create_timeframe_structure(self,
                                   timeframe: str,
                                   exchanges: List[str],
                                   symbols: List[str],
                                   start_date: datetime,
                                   end_date: datetime,
                                   market_type: str = "spot") -> Dict[str, int]:
        """Create directory structure for a specific timeframe."""
        summary = {
            'instruments_files': 0,
            'calendar_files': 0,
            'feature_directories': 0
        }
        
        # Create timeframe directory using original timeframe name
        # This maintains consistency with data collection expectations
        tf_dir = self.data_dir / timeframe
        tf_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        features_dir = tf_dir / "features"
        instruments_dir = tf_dir / "instruments"
        calendars_dir = tf_dir / "calendars"
        
        for subdir in [features_dir, instruments_dir, calendars_dir]:
            subdir.mkdir(exist_ok=True)
        
        # Create instruments file
        instruments = self._generate_instruments_list(exchanges, symbols, market_type)
        self._create_instruments_file(instruments, "crypto", timeframe)
        summary['instruments_files'] = 1
        
        # Create calendar files
        self._create_calendar_files(timeframe, start_date, end_date)
        summary['calendar_files'] = 2  # Regular and future calendars
        
        # Create feature directories for each instrument
        for instrument in instruments:
            instrument_dir = features_dir / instrument
            instrument_dir.mkdir(exist_ok=True)
            summary['feature_directories'] += 1
        
        return summary
    
    def _generate_instruments_list(self, exchanges: List[str], symbols: List[str], market_type: str = "spot") -> List[str]:
        """Generate list of instrument identifiers."""
        instruments = []
        
        for exchange in exchanges:
            for symbol in symbols:
                # Convert symbol to instrument format, matching data collection naming
                # Remove '/' and make lowercase to match actual data collection format
                symbol_clean = symbol.replace('/', '').lower()
                instrument = f"{exchange.lower()}_{market_type.lower()}_{symbol_clean}"
                instruments.append(instrument)
        
        return sorted(instruments)
    
    def _create_instruments_file(self,
                                instruments: List[str],
                                market: str,
                                freq: str) -> None:
        """Create instruments file for a market and frequency."""
        try:
            # Use original frequency for directory structure
            # This maintains consistency with data collection expectations
            tf_dir = self.data_dir / freq
            instruments_dir = tf_dir / "instruments"
            instruments_dir.mkdir(parents=True, exist_ok=True)

            # Create instruments file directly
            instruments_file = instruments_dir / f"{market}.txt"
            
            with open(instruments_file, 'w') as f:
                for instrument in instruments:
                    # Each line: instrument_name start_date end_date
                    f.write(f"{instrument}\t2020-01-01\t2030-12-31\n")
            
            self.logger.debug(f"Created instruments file for {market}.{freq} with {len(instruments)} instruments")
            
        except Exception as e:
            self.logger.error(f"Failed to create instruments file for {market}.{freq}: {e}")
            raise
    
    def _create_calendar_files(self,
                              freq: str,
                              start_date: datetime,
                              end_date: datetime) -> None:
        """Create calendar files for a frequency."""
        # Create regular calendar
        self._create_single_calendar(freq, start_date, end_date, future=False)
        
        # Create future calendar (for forecasting)
        future_start = end_date + timedelta(days=1)
        future_end = future_start + timedelta(days=365)  # 1 year future
        self._create_single_calendar(freq, future_start, future_end, future=True)
    
    def _create_single_calendar(self,
                               freq: str,
                               start_date: datetime,
                               end_date: datetime,
                               future: bool = False) -> None:
        """Create a single calendar file."""
        try:
            # BOUNDARY: convert_for_qlib_internal usage - ONLY for Qlib storage API
            # This conversion is required because FileCalendarStorage expects Qlib format
            qlib_freq = convert_for_qlib_internal(freq)

            # Use original timeframe for directory structure (maintains consistency with data collection)
            tf_dir = self.data_dir / freq
            calendars_dir = tf_dir / "calendars"
            calendars_dir.mkdir(parents=True, exist_ok=True)

            # Normalize start_date based on frequency to ensure proper alignment
            # Simple calendar generation based on frequency
            # Time alignment logic for different frequencies
            # Each frequency requires specific alignment for proper calendar generation
            if freq == "1d":
                aligned_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif freq == "1h":
                aligned_start = start_date.replace(minute=0, second=0, microsecond=0)
            elif freq == "5min":
                aligned_start = start_date.replace(minute=(start_date.minute // 5) * 5, second=0, microsecond=0)
            elif freq == "1min":
                aligned_start = start_date.replace(second=0, microsecond=0)
            elif freq == "15min":
                aligned_start = start_date.replace(minute=(start_date.minute // 15) * 15, second=0, microsecond=0)
            elif freq == "30min":
                aligned_start = start_date.replace(minute=(start_date.minute // 30) * 30, second=0, microsecond=0)
            elif freq == "1w":
                aligned_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                days_since_monday = aligned_start.weekday()
                aligned_start = aligned_start - timedelta(days=days_since_monday)
            else:
                # Fallback to daily alignment
                aligned_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                self.logger.warning(f"Unknown frequency {freq}, using daily alignment")
            
            # Generate calendar using unified pandas frequency conversion
            try:
                from config.timeframes import timeframe_to_pandas_freq
                pandas_freq = timeframe_to_pandas_freq(freq)
                calendar = pd.date_range(start=aligned_start, end=end_date, freq=pandas_freq)
            except (ValueError, ImportError) as e:
                # Fallback to daily calendar if timeframe conversion fails
                self.logger.warning(f"Failed to convert timeframe {freq} to pandas frequency: {e}")
                calendar = pd.date_range(start=aligned_start, end=end_date, freq='D')
            
            # Create calendar file name using original timeframe format (for user consistency)
            if future:
                calendar_file = calendars_dir / f"{freq}_future.txt"
            else:
                calendar_file = calendars_dir / f"{freq}.txt"
            
            # Write calendar file directly
            with open(calendar_file, 'w') as f:
                for timestamp in calendar:
                    f.write(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            calendar_type = "future" if future else "regular"
            self.logger.debug(f"Created {calendar_type} calendar for {freq} with {len(calendar)} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to create calendar for {freq} (future={future}): {e}")
            raise
    
    def update_instruments(self,
                          new_instruments: List[str],
                          market: str = "crypto",
                          timeframes: Optional[List[str]] = None) -> None:
        """
        Update instruments files with new instruments.
        
        Parameters
        ----------
        new_instruments : List[str]
            List of new instrument identifiers
        market : str, default "crypto"
            Market name
        timeframes : List[str], optional
            Timeframes to update. If None, updates all existing timeframes
        """
        if timeframes is None:
            # Find all existing timeframes
            timeframes = [d.name for d in self.data_dir.iterdir() 
                         if d.is_dir() and validate_timeframe(d.name)]
        
        for timeframe in timeframes:
            try:
                # BOUNDARY: convert_for_qlib_internal usage - ONLY for Qlib storage API
                # This conversion is required because FileInstrumentStorage expects Qlib format
                qlib_freq = convert_for_qlib_internal(timeframe)
                storage = FileInstrumentStorage(
                    market=market,
                    freq=qlib_freq,
                    provider_uri=self.provider_uri
                )
                
                existing_data = storage.data
                existing_instruments = set(existing_data.keys())
                
                # Add new instruments
                updated_data = dict(existing_data)
                for instrument in new_instruments:
                    if instrument not in existing_instruments:
                        updated_data[instrument] = [
                            (datetime(2020, 1, 1), datetime(2030, 12, 31))
                        ]
                
                # Write updated data
                storage._write_instrument(updated_data)
                
                # Create feature directories for new instruments using original timeframe format
                features_dir = self.data_dir / timeframe / "features"
                for instrument in new_instruments:
                    if instrument not in existing_instruments:
                        instrument_dir = features_dir / instrument
                        instrument_dir.mkdir(exist_ok=True)
                
                self.logger.info(f"Updated instruments for {timeframe}: added {len(new_instruments)} instruments")
                
            except Exception as e:
                self.logger.error(f"Failed to update instruments for {timeframe}: {e}")
    
    def validate_structure(self) -> Dict[str, any]:
        """
        Validate the Qlib data directory structure.
        
        Returns
        -------
        dict
            Validation results
        """
        validation = {
            'is_valid': True,
            'timeframes': {},
            'missing_files': [],
            'errors': []
        }
        
        # Check each timeframe directory
        for tf_dir in self.data_dir.iterdir():
            if not tf_dir.is_dir() or not validate_timeframe(tf_dir.name):
                continue
            
            timeframe = tf_dir.name
            tf_validation = {
                'has_features': False,
                'has_instruments': False,
                'has_calendars': False,
                'instrument_count': 0,
                'feature_directories': 0
            }
            
            # Check subdirectories
            features_dir = tf_dir / "features"
            instruments_dir = tf_dir / "instruments"
            calendars_dir = tf_dir / "calendars"
            
            tf_validation['has_features'] = features_dir.exists()
            tf_validation['has_instruments'] = instruments_dir.exists()
            tf_validation['has_calendars'] = calendars_dir.exists()
            
            if features_dir.exists():
                tf_validation['feature_directories'] = len([
                    d for d in features_dir.iterdir() if d.is_dir()
                ])
            
            # Check for instruments file
            instruments_file = instruments_dir / "crypto.txt"
            if instruments_file.exists():
                try:
                    # BOUNDARY: convert_for_qlib_internal usage - ONLY for Qlib storage API
                    # This conversion is required because FileInstrumentStorage expects Qlib format
                    qlib_freq = convert_for_qlib_internal(timeframe)
                    storage = FileInstrumentStorage(
                        market="crypto",
                        freq=qlib_freq,
                        provider_uri=self.provider_uri
                    )
                    instruments_data = storage.data
                    tf_validation['instrument_count'] = len(instruments_data)
                except Exception as e:
                    validation['errors'].append(f"Failed to read instruments for {timeframe}: {e}")
            else:
                validation['missing_files'].append(f"{timeframe}/instruments/crypto.txt")
                validation['is_valid'] = False
            
            # Check for calendar files using original timeframe format
            calendar_file = calendars_dir / f"{timeframe}.txt"
            future_calendar_file = calendars_dir / f"{timeframe}_future.txt"
            
            if not calendar_file.exists():
                validation['missing_files'].append(f"{timeframe}/calendars/{timeframe}.txt")
                validation['is_valid'] = False
            
            if not future_calendar_file.exists():
                validation['missing_files'].append(f"{timeframe}/calendars/{timeframe}_future.txt")
                validation['is_valid'] = False
            
            validation['timeframes'][timeframe] = tf_validation
        
        return validation
    
    def get_structure_info(self) -> Dict[str, any]:
        """Get information about the current data structure."""
        info = {
            'data_dir': str(self.data_dir),
            'timeframes': {},
            'total_instruments': 0,
            'total_feature_dirs': 0
        }
        
        all_instruments = set()
        
        for tf_dir in self.data_dir.iterdir():
            if not tf_dir.is_dir() or not validate_timeframe(tf_dir.name):
                continue
            
            timeframe = tf_dir.name
            tf_info = {
                'features_dir': str(tf_dir / "features"),
                'instruments_dir': str(tf_dir / "instruments"),
                'calendars_dir': str(tf_dir / "calendars"),
                'instrument_count': 0,
                'feature_directories': 0
            }
            
            # Count feature directories
            features_dir = tf_dir / "features"
            if features_dir.exists():
                feature_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
                tf_info['feature_directories'] = len(feature_dirs)
                info['total_feature_dirs'] += len(feature_dirs)
                
                # Add to all instruments set
                all_instruments.update(d.name for d in feature_dirs)
            
            # Count instruments from file
            try:
                # BOUNDARY: convert_for_qlib_internal usage - ONLY for Qlib storage API
                # This conversion is required because FileInstrumentStorage expects Qlib format
                qlib_freq = convert_for_qlib_internal(timeframe)
                storage = FileInstrumentStorage(
                    market="crypto",
                    freq=qlib_freq,
                    provider_uri=self.provider_uri
                )
                instruments_data = storage.data
                tf_info['instrument_count'] = len(instruments_data)
            except Exception:
                tf_info['instrument_count'] = 0
            
            info['timeframes'][timeframe] = tf_info
        
        info['total_instruments'] = len(all_instruments)
        return info
