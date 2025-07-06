# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Base exchange adapter for cryptocurrency data collection.

This module defines the abstract interface that all exchange adapters must implement.
"""

import abc

import time
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger


class ExchangeAdapter(abc.ABC):
    """
    Abstract base class for cryptocurrency exchange adapters.
    
    This class defines the unified interface that all exchange adapters must implement
    to provide consistent access to cryptocurrency data across different exchanges.
    """
    
    def __init__(self, 
                 exchange_id: str,
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 sandbox: bool = False,
                 rate_limit: float = 0.1,
                 timeout: int = 30,
                 **kwargs):
        """
        Initialize the exchange adapter.
        
        Parameters
        ----------
        exchange_id : str
            The exchange identifier (e.g., 'binance', 'okx', 'bybit')
        api_key : str, optional
            API key for authenticated requests
        api_secret : str, optional
            API secret for authenticated requests
        sandbox : bool, default False
            Whether to use sandbox/testnet environment
        rate_limit : float, default 0.1
            Minimum delay between requests in seconds
        timeout : int, default 30
            Request timeout in seconds
        **kwargs
            Additional exchange-specific parameters
        """
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.last_request_time = 0
        
        # Initialize exchange-specific settings
        self._init_exchange(**kwargs)
    
    @abc.abstractmethod
    def _init_exchange(self, **kwargs):
        """Initialize exchange-specific settings and connections."""
        pass
    
    def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        self.last_request_time = time.time()
    
    @abc.abstractmethod
    def get_instruments(self, 
                       market_type: str = "spot",
                       base_currency: Optional[str] = None,
                       quote_currency: Optional[str] = None) -> List[str]:
        """
        Get list of available trading instruments.
        
        Parameters
        ----------
        market_type : str, default "spot"
            Market type: "spot", "futures", "perpetual", "option"
        base_currency : str, optional
            Filter by base currency (e.g., "BTC", "ETH")
        quote_currency : str, optional
            Filter by quote currency (e.g., "USDT", "USD")
            
        Returns
        -------
        List[str]
            List of instrument symbols (e.g., ["BTC/USDT", "ETH/USDT"])
        """
        pass
    
    @abc.abstractmethod
    def get_ohlcv(self,
                  symbol: str,
                  timeframe: str,
                  start_time: Optional[Union[datetime, str, int]] = None,
                  end_time: Optional[Union[datetime, str, int]] = None,
                  limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get OHLCV (Open, High, Low, Close, Volume) data.
        
        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT")
        timeframe : str
            Time interval (e.g., "1m", "5m", "1h", "1d")
        start_time : datetime, str, or int, optional
            Start time for data retrieval
        end_time : datetime, str, or int, optional
            End time for data retrieval
        limit : int, optional
            Maximum number of data points to retrieve
            
        Returns
        -------
        pd.DataFrame
            DataFrame with columns: [timestamp, open, high, low, close, volume]
        """
        pass
    
    @abc.abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker information.
        
        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT")
            
        Returns
        -------
        Dict[str, Any]
            Ticker information including price, volume, change, etc.
        """
        pass
    
    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Get current funding rate for perpetual contracts.
        
        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT")
            
        Returns
        -------
        float or None
            Current funding rate, None if not applicable
        """
        # Default implementation returns None for exchanges that don't support funding rates
        return None
    
    def get_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get order book data.
        
        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT")
        limit : int, default 10
            Number of price levels to retrieve
            
        Returns
        -------
        Dict[str, Any]
            Order book with 'bids' and 'asks' arrays
        """
        # Default implementation returns empty order book
        return {"bids": [], "asks": [], "timestamp": time.time() * 1000}
    
    def get_open_interest(self, symbol: str) -> Optional[float]:
        """
        Get open interest for futures/perpetual contracts.

        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT")

        Returns
        -------
        float or None
            Open interest value, None if not applicable
        """
        # Default implementation returns None
        return None

    @abc.abstractmethod
    def get_symbols(self, market_type: str = "spot") -> List[str]:
        """
        Get list of available trading symbols.

        Parameters
        ----------
        market_type : str, default "spot"
            Market type ("spot", "futures", "perpetual", "option")

        Returns
        -------
        List[str]
            List of available trading symbols
        """
        pass

    @abc.abstractmethod
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed information about a trading symbol.

        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT")

        Returns
        -------
        Dict[str, Any]
            Symbol information including base/quote assets, market type, etc.
        """
        pass
    
    def get_24h_stats(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24-hour statistics.
        
        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC/USDT")
            
        Returns
        -------
        Dict[str, Any]
            24-hour statistics including volume, price change, etc.
        """
        # Default implementation uses ticker data
        ticker = self.get_ticker(symbol)
        return {
            "volume_24h": ticker.get("quoteVolume", 0),
            "change_24h": ticker.get("percentage", 0),
            "high_24h": ticker.get("high", 0),
            "low_24h": ticker.get("low", 0),
        }
    
    @abc.abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format to exchange-specific format.
        
        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")
            
        Returns
        -------
        str
            Symbol in exchange-specific format
        """
        pass
    
    @abc.abstractmethod
    def standardize_symbol(self, symbol: str) -> str:
        """
        Convert exchange-specific symbol to standard format.
        
        Parameters
        ----------
        symbol : str
            Symbol in exchange-specific format
            
        Returns
        -------
        str
            Symbol in standard format (e.g., "BTC/USDT")
        """
        pass
    
    def validate_timeframe(self, timeframe: str) -> bool:
        """
        Validate if timeframe is supported by the exchange.

        Parameters
        ----------
        timeframe : str
            Time interval (e.g., "1m", "5m", "1h", "1d")

        Returns
        -------
        bool
            True if timeframe is supported
        """
        return timeframe in self.get_supported_timeframes()

    def convert_timeframe_to_exchange_format(self, timeframe: str) -> str:
        """
        Convert standard timeframe to exchange-specific format.

        Parameters
        ----------
        timeframe : str
            Standard timeframe

        Returns
        -------
        str
            Exchange-specific timeframe format
        """
        from config.timeframes import EXCHANGE_TIMEFRAME_MAPPING

        exchange_mapping = EXCHANGE_TIMEFRAME_MAPPING.get(self.exchange_id.lower(), {})
        return exchange_mapping.get(timeframe, timeframe)
    
    def get_supported_timeframes(self) -> List[str]:
        """
        Get list of supported timeframes.
        
        Returns
        -------
        List[str]
            List of supported timeframe strings
        """
        # Default implementation - should be overridden by specific adapters
        return ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    
    def health_check(self) -> bool:
        """
        Check if the exchange connection is healthy.
        
        Returns
        -------
        bool
            True if connection is healthy
        """
        try:
            # Try to get a simple ticker to test connectivity
            instruments = self.get_instruments()
            if instruments:
                self.get_ticker(instruments[0])
                return True
        except Exception as e:
            logger.warning(f"Health check failed for {self.exchange_id}: {e}")
        return False

    # Crypto-specific data collection methods

    @abc.abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a symbol.

        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")

        Returns
        -------
        Dict[str, Any]
            Ticker data including volume_24h, change_24h, etc.
        """
        pass

    @abc.abstractmethod
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get funding rate for a perpetual contract.

        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")

        Returns
        -------
        Optional[Dict[str, Any]]
            Funding rate data or None if not available
        """
        pass

    @abc.abstractmethod
    def get_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get open interest for a futures/perpetual contract.

        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")

        Returns
        -------
        Optional[Dict[str, Any]]
            Open interest data or None if not available
        """
        pass

    def get_order_book(self, symbol: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        """
        Get order book data for calculating bid-ask spread.

        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")
        limit : int, default 20
            Number of order book levels to fetch

        Returns
        -------
        Optional[Dict[str, Any]]
            Order book data or None if not available
        """
        # Default implementation returns None
        # Specific adapters should override if supported
        return None

    def calculate_bid_ask_spread(self, order_book: Dict[str, Any]) -> Optional[float]:
        """
        Calculate bid-ask spread from order book data.

        Parameters
        ----------
        order_book : Dict[str, Any]
            Order book data

        Returns
        -------
        Optional[float]
            Bid-ask spread or None if cannot calculate
        """
        try:
            if not order_book or 'bids' not in order_book or 'asks' not in order_book:
                return None

            bids = order_book['bids']
            asks = order_book['asks']

            if not bids or not asks:
                return None

            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])

            if best_bid <= 0 or best_ask <= 0:
                return None

            spread = (best_ask - best_bid) / best_bid
            return spread

        except (IndexError, ValueError, TypeError):
            return None
