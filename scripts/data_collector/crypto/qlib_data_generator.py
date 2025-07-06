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

from config.timeframes import TIMEFRAME_MAPPING, validate_timeframe
from config.fields import STANDARD_FIELDS, CRYPTO_SPECIFIC_FIELDS
from storage_manager import CryptoStorageManager, convert_to_qlib_freq


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
        
        # Create timeframe directory
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
                # Convert symbol to instrument format, including market type
                symbol_clean = symbol.replace('/', '_').lower()
                instrument = f"{exchange.lower()}_{market_type.lower()}_{symbol_clean}"
                instruments.append(instrument)
        
        return sorted(instruments)
    
    def _create_instruments_file(self,
                                instruments: List[str],
                                market: str,
                                freq: str) -> None:
        """Create instruments file for a market and frequency."""
        try:
            # Convert to qlib frequency format
            qlib_freq = convert_to_qlib_freq(freq)

            # Ensure instruments directory exists
            if isinstance(self.provider_uri, dict):
                # Use the first available path from provider_uri
                base_path = Path(list(self.provider_uri.values())[0])
            else:
                base_path = Path(self.provider_uri) if self.provider_uri else self.data_dir

            instruments_dir = base_path / "instruments"
            instruments_dir.mkdir(parents=True, exist_ok=True)

            storage = FileInstrumentStorage(
                market=market,
                freq=qlib_freq,
                provider_uri=self.provider_uri
            )
            
            # Create instrument data with trading periods
            # For crypto, assume 24/7 trading from 2020 to 2030
            instrument_data = {}
            for instrument in instruments:
                instrument_data[instrument] = [
                    (datetime(2020, 1, 1), datetime(2030, 12, 31))
                ]
            
            # Write instrument data
            storage._write_instrument(instrument_data)
            
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
            # Convert to qlib frequency format
            qlib_freq = convert_to_qlib_freq(freq)

            # Ensure calendars directory exists
            if isinstance(self.provider_uri, dict):
                # Use the first available path from provider_uri
                base_path = Path(list(self.provider_uri.values())[0])
            else:
                base_path = Path(self.provider_uri) if self.provider_uri else self.data_dir

            calendars_dir = base_path / "calendars"
            calendars_dir.mkdir(parents=True, exist_ok=True)

            storage = FileCalendarStorage(
                freq=qlib_freq,
                future=future,
                provider_uri=self.provider_uri
            )
            
            # Generate calendar based on frequency
            if freq == "1d":
                calendar = pd.date_range(start=start_date, end=end_date, freq='D')
            elif freq == "1h":
                calendar = pd.date_range(start=start_date, end=end_date, freq='H')
            elif freq == "5m":
                calendar = pd.date_range(start=start_date, end=end_date, freq='5T')
            elif freq == "1m":
                calendar = pd.date_range(start=start_date, end=end_date, freq='T')
            else:
                # For other frequencies, try to parse
                try:
                    calendar = pd.date_range(start=start_date, end=end_date, freq=freq.upper())
                except Exception:
                    # Fallback to daily
                    calendar = pd.date_range(start=start_date, end=end_date, freq='D')
                    self.logger.warning(f"Unknown frequency {freq}, using daily calendar")
            
            # Write calendar
            storage._write_calendar(calendar)
            
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
                # Load existing instruments
                qlib_freq = convert_to_qlib_freq(timeframe)
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
                
                # Create feature directories for new instruments
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
                    qlib_freq = convert_to_qlib_freq(timeframe)
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
            
            # Check for calendar files
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
                qlib_freq = convert_to_qlib_freq(timeframe)
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
