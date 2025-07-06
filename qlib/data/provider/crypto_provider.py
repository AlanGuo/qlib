# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Cryptocurrency data provider for Qlib.

This module provides a comprehensive data provider for cryptocurrency data
that integrates with multiple exchanges and supports crypto-specific features.
"""

import os
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

from qlib.data.data import BaseProvider, FeatureProvider, InstrumentProvider, CalendarProvider
from qlib.data.data import ProviderBackendMixin
from qlib.utils import get_module_logger
from qlib.config import C

# Import crypto-specific modules
try:
    from ..collector.crypto.exchange_adapters import ExchangeAdapter, BinanceAdapter
    from ..collector.crypto.config.exchanges import get_exchange_config, EXCHANGE_CONFIGS
    from ..collector.crypto.config.fields import get_fields_for_market_type, validate_field
    from ..collector.crypto.config.timeframes import validate_timeframe, get_timeframe_seconds
except ImportError:
    logger.warning("Crypto collector modules not found. Some features may be limited.")


class CryptoFeatureProvider(FeatureProvider, ProviderBackendMixin):
    """
    Cryptocurrency feature data provider.

    Provides feature data from cryptocurrency exchanges with support for
    both real-time data access and Qlib standard storage backend.
    """

    def __init__(self,
                 exchanges: Optional[List[str]] = None,
                 market_type: str = "spot",
                 cache_dir: Optional[str] = None,
                 backend: Dict = None,
                 provider_uri: Optional[str] = None,
                 **kwargs):
        """
        Initialize crypto feature provider.

        Parameters
        ----------
        exchanges : List[str], optional
            List of exchanges to use (default: ["binance"])
        market_type : str, default "spot"
            Market type: "spot", "futures", "perpetual"
        cache_dir : str, optional
            Directory for caching data
        backend : dict, optional
            Backend configuration for local storage
        provider_uri : str, optional
            Provider URI for Qlib storage backend
        **kwargs
            Additional parameters
        """
        # Initialize ProviderBackendMixin first
        ProviderBackendMixin.__init__(self, backend=backend)
        FeatureProvider.__init__(self)

        self.exchanges = exchanges or ["binance"]
        self.market_type = market_type
        self.cache_dir = cache_dir or os.path.expanduser("~/.qlib/crypto_cache")
        self.provider_uri = provider_uri

        # Initialize exchange adapters for real-time data
        self.adapters: Dict[str, ExchangeAdapter] = {}
        self._init_adapters(**kwargs)

        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)

        self.logger = get_module_logger("CryptoFeatureProvider")
    
    def _init_adapters(self, **kwargs):
        """Initialize exchange adapters."""
        for exchange in self.exchanges:
            try:
                if exchange.lower() == "binance":
                    adapter = BinanceAdapter(
                        market_type=self.market_type,
                        **kwargs.get(exchange, {})
                    )
                    self.adapters[exchange] = adapter
                    logger.info(f"Initialized {exchange} adapter")
                else:
                    logger.warning(f"Adapter for {exchange} not implemented yet")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange} adapter: {e}")
    
    def feature(self, instrument: str, field: str, start_index: int, end_index: int, freq: str):
        """
        Get feature data for an instrument.

        This method first tries to get data from Qlib storage backend,
        and falls back to real-time data from exchange adapters if needed.

        Parameters
        ----------
        instrument : str
            Instrument symbol (e.g., "binance_btc_usdt")
        field : str
            Field name (e.g., "close", "volume")
        start_index : int
            Start index
        end_index : int
            End index
        freq : str
            Frequency (e.g., "1d", "1h")

        Returns
        -------
        pd.Series
            Feature data
        """
        try:
            # Clean field name (remove $ prefix if present)
            clean_field = field.lstrip('$')

            # First try to get data from Qlib storage backend
            if hasattr(self, 'backend') and self.backend:
                try:
                    data = self._get_data_from_storage(instrument, clean_field, freq, start_index, end_index)
                    if data is not None and not data.empty:
                        self.logger.debug(f"Retrieved {len(data)} records from storage for {instrument}.{clean_field}")
                        return data
                except Exception as e:
                    self.logger.debug(f"Storage backend failed for {instrument}.{clean_field}: {e}")

            # Fallback to real-time data from exchange adapters
            return self._get_realtime_feature_data(instrument, clean_field, freq, start_index, end_index)

        except Exception as e:
            self.logger.error(f"Failed to get feature {field} for {instrument}: {e}")
            return pd.Series()

    def _get_data_from_storage(self, instrument: str, field: str, freq: str, start_index: int, end_index: int):
        """Get data from Qlib storage backend."""
        from qlib.data.storage.file_storage import FileFeatureStorage

        try:
            # Create storage instance
            storage = FileFeatureStorage(
                instrument=instrument,
                field=field,
                freq=freq,
                provider_uri=self.provider_uri
            )

            # Get data slice
            data = storage[start_index:end_index]
            return data

        except Exception as e:
            self.logger.debug(f"Failed to get data from storage: {e}")
            return None

    def _get_realtime_feature_data(self, instrument: str, field: str, freq: str, start_index: int, end_index: int):
        """Get real-time feature data from exchange adapters."""
        try:
            # Parse instrument to extract exchange, symbol, and market_type
            exchange, symbol, market_type = self._parse_instrument(instrument)

            if exchange not in self.adapters:
                self.logger.error(f"No adapter available for exchange: {exchange}")
                return pd.Series()

            adapter = self.adapters[exchange]

            # Validate field
            if not validate_field(field, market_type, exchange):
                self.logger.warning(f"Field {field} not supported for {exchange} {market_type}")
                return pd.Series()

            # Get data from adapter
            data = self._get_feature_data(adapter, symbol, field, freq, start_index, end_index)

            return data

        except Exception as e:
            self.logger.error(f"Failed to get real-time feature data: {e}")
            return pd.Series()
    
    def _parse_instrument(self, instrument: str) -> tuple:
        """
        Parse instrument string to extract exchange, market_type, and symbol.
        
        Parameters
        ----------
        instrument : str
            Instrument string (e.g., "binance_spot_BTC_USDT" or "BTC/USDT")
            
        Returns
        -------
        tuple
            (exchange, symbol, market_type)
        """
        if '_' in instrument:
            parts = instrument.split('_')
            if len(parts) >= 4:
                # New format: exchange_market_type_base_quote
                exchange = parts[0]
                market_type = parts[1]
                symbol = f"{parts[2]}/{parts[3]}"
                return exchange, symbol, market_type
            elif len(parts) >= 3:
                # Legacy format: exchange_base_quote (assume spot)
                exchange = parts[0]
                symbol = f"{parts[1]}/{parts[2]}"
                market_type = "spot"
                return exchange, symbol, market_type
        
        # Default to first available exchange
        if self.adapters:
            exchange = list(self.adapters.keys())[0]
            symbol = instrument
            market_type = self.market_type
            return exchange, symbol, market_type
        
        raise ValueError(f"Cannot parse instrument: {instrument}")
    
    def _get_feature_data(self, 
                         adapter: ExchangeAdapter, 
                         symbol: str, 
                         field: str, 
                         freq: str,
                         start_index: int, 
                         end_index: int) -> pd.Series:
        """Get feature data from adapter."""
        try:
            # For now, get recent data (this should be enhanced with proper indexing)
            limit = max(end_index - start_index + 1, 100)
            
            if field in ['open', 'high', 'low', 'close', 'volume']:
                # Get OHLCV data
                df = adapter.get_ohlcv(symbol, freq, limit=limit)
                if not df.empty and field in df.columns:
                    series = df[field]
                    # Return the requested slice
                    if len(series) > end_index - start_index + 1:
                        return series.iloc[start_index:end_index + 1]
                    return series
            
            elif field == 'funding_rate':
                # Get funding rate (single value for now)
                rate = adapter.get_funding_rate(symbol)
                if rate is not None:
                    # Create a series with the same length
                    length = end_index - start_index + 1
                    return pd.Series([rate] * length)
            
            elif field in ['volume_24h', 'change_24h', 'high_24h', 'low_24h']:
                # Get 24h stats
                stats = adapter.get_24h_stats(symbol)
                value = stats.get(field, 0)
                length = end_index - start_index + 1
                return pd.Series([value] * length)
            
            return pd.Series()
            
        except Exception as e:
            logger.error(f"Failed to get {field} data for {symbol}: {e}")
            return pd.Series()


class CryptoInstrumentProvider(InstrumentProvider):
    """
    Cryptocurrency instrument provider.
    
    Manages the universe of available cryptocurrency instruments.
    """
    
    def __init__(self, 
                 exchanges: Optional[List[str]] = None,
                 market_type: str = "spot",
                 **kwargs):
        """
        Initialize crypto instrument provider.
        
        Parameters
        ----------
        exchanges : List[str], optional
            List of exchanges to use
        market_type : str, default "spot"
            Market type
        **kwargs
            Additional parameters
        """
        super().__init__()
        self.exchanges = exchanges or ["binance"]
        self.market_type = market_type
        
        # Initialize adapters
        self.adapters: Dict[str, ExchangeAdapter] = {}
        self._init_adapters(**kwargs)
    
    def _init_adapters(self, **kwargs):
        """Initialize exchange adapters."""
        for exchange in self.exchanges:
            try:
                if exchange.lower() == "binance":
                    adapter = BinanceAdapter(
                        market_type=self.market_type,
                        **kwargs.get(exchange, {})
                    )
                    self.adapters[exchange] = adapter
            except Exception as e:
                logger.error(f"Failed to initialize {exchange} adapter: {e}")
    
    def list_instruments(self, market: str = "all", **kwargs) -> List[str]:
        """
        List available instruments.
        
        Parameters
        ----------
        market : str, default "all"
            Market filter
        **kwargs
            Additional filters
            
        Returns
        -------
        List[str]
            List of instrument identifiers
        """
        instruments = []
        
        for exchange, adapter in self.adapters.items():
            try:
                exchange_instruments = adapter.get_instruments(
                    market_type=self.market_type,
                    **kwargs
                )
                
                # Format instruments with exchange and market_type prefix
                formatted_instruments = [
                    f"{exchange}_{self.market_type}_{symbol.replace('/', '_')}"
                    for symbol in exchange_instruments
                ]
                
                instruments.extend(formatted_instruments)
                
            except Exception as e:
                logger.error(f"Failed to get instruments from {exchange}: {e}")
        
        return sorted(instruments)


class CryptoCalendarProvider(CalendarProvider):
    """
    Cryptocurrency calendar provider.
    
    Provides trading calendar for cryptocurrency markets (24/7 trading).
    """
    
    def calendar(self, start_time=None, end_time=None, freq="day", future=False):
        """
        Get trading calendar for crypto markets.
        
        Crypto markets trade 24/7, so this returns a continuous calendar.
        """
        if start_time is None:
            start_time = "2010-01-01"
        if end_time is None:
            end_time = datetime.now().strftime("%Y-%m-%d")
        
        # Convert frequency
        freq_map = {
            "day": "D",
            "1d": "D", 
            "hour": "H",
            "1h": "H",
            "minute": "T",
            "1m": "T"
        }
        
        pd_freq = freq_map.get(freq, "D")
        
        # Generate continuous calendar (crypto trades 24/7)
        calendar = pd.date_range(
            start=start_time,
            end=end_time, 
            freq=pd_freq
        )
        
        return calendar


class CryptoDataProvider(BaseProvider):
    """
    Main cryptocurrency data provider.
    
    Integrates feature, instrument, and calendar providers for comprehensive
    cryptocurrency data access.
    """
    
    def __init__(self,
                 exchanges: Optional[List[str]] = None,
                 market_type: str = "spot",
                 **kwargs):
        """
        Initialize crypto data provider.
        
        Parameters
        ----------
        exchanges : List[str], optional
            List of exchanges to use
        market_type : str, default "spot"
            Market type
        **kwargs
            Additional parameters
        """
        super().__init__()
        
        self.exchanges = exchanges or ["binance"]
        self.market_type = market_type
        
        # Initialize sub-providers
        self.feature_provider = CryptoFeatureProvider(
            exchanges=exchanges,
            market_type=market_type,
            **kwargs
        )
        
        self.instrument_provider = CryptoInstrumentProvider(
            exchanges=exchanges,
            market_type=market_type,
            **kwargs
        )
        
        self.calendar_provider = CryptoCalendarProvider()
    
    def features(self, instruments, fields, start_time=None, end_time=None, freq="day"):
        """Get feature data for multiple instruments."""
        # This would typically delegate to the feature provider
        # For now, return a simple implementation
        data = {}
        
        if isinstance(instruments, str):
            instruments = [instruments]
        if isinstance(fields, str):
            fields = [fields]
        
        for instrument in instruments:
            for field in fields:
                try:
                    # Get data using feature provider
                    # This is a simplified implementation
                    series = self.feature_provider.feature(
                        instrument, field, 0, 100, freq
                    )
                    data[f"{instrument}_{field}"] = series
                except Exception as e:
                    logger.error(f"Failed to get {field} for {instrument}: {e}")
        
        return pd.DataFrame(data)
    
    def calendar(self, start_time=None, end_time=None, freq="day", future=False):
        """Get trading calendar."""
        return self.calendar_provider.calendar(start_time, end_time, freq, future)
    
    def instruments(self, market="all", filter_pipe=None, start_time=None, end_time=None):
        """Get available instruments."""
        return self.instrument_provider.list_instruments(market)
