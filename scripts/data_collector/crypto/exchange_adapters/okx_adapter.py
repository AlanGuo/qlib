# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
OKX exchange adapter for cryptocurrency data collection.

This module implements the OKX-specific adapter using the ccxt library.
"""

import os
import time

from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

try:
    import ccxt
except ImportError:
    logger.error("ccxt library is required. Install with: pip install ccxt")
    raise



import sys
from pathlib import Path

# Add the crypto directory to Python path
crypto_dir = Path(__file__).parent.parent
sys.path.insert(0, str(crypto_dir))

from exchange_adapters.base_adapter import ExchangeAdapter
from config.timeframes import get_exchange_timeframe, get_timeframe_seconds
from config.exchanges import get_exchange_config


class OKXAdapter(ExchangeAdapter):
    """
    OKX exchange adapter using ccxt library.
    
    Supports spot, futures, perpetual, and option markets with comprehensive 
    data collection including OHLCV, funding rates, and open interest.
    """
    
    def __init__(self, 
                 market_type: str = "spot",
                 api_key: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 passphrase: Optional[str] = None,
                 sandbox: bool = False,
                 **kwargs):
        """
        Initialize OKX adapter.
        
        Parameters
        ----------
        market_type : str, default "spot"
            Market type: "spot", "futures", "perpetual", "option"
        api_key : str, optional
            OKX API key
        api_secret : str, optional
            OKX API secret
        passphrase : str, optional
            OKX API passphrase (required for OKX)
        sandbox : bool, default False
            Use demo trading environment
        **kwargs
            Additional parameters
        """
        self.market_type = market_type.lower()
        self.passphrase = passphrase
        
        # Get exchange configuration
        self.config = get_exchange_config("okx")
        
        super().__init__(
            exchange_id="okx",
            api_key=api_key,
            api_secret=api_secret,
            sandbox=sandbox,
            rate_limit=self.config.rate_limit,
            **kwargs
        )
    
    def _init_exchange(self, **kwargs):
        """Initialize OKX ccxt exchange instance."""
        try:
            # Check for proxy configuration
            proxy_config = {}
            proxy_url = (os.environ.get('CRYPTO_TEST_PROXY') or 
                        os.environ.get('https_proxy') or 
                        os.environ.get('HTTPS_PROXY') or 
                        os.environ.get('HTTP_PROXY') or 
                        os.environ.get('http_proxy'))
            if proxy_url:
                proxy_config['proxies'] = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                logger.info(f"Using proxy: {proxy_url}")

            # OKX configuration
            config = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'password': self.passphrase,  # OKX requires passphrase
                'sandbox': self.sandbox,
                'timeout': self.timeout * 1000,  # ccxt uses milliseconds
                'enableRateLimit': True,
                **proxy_config,
                **kwargs
            }
            
            # Set market type specific options
            if self.market_type in ["futures", "perpetual"]:
                config['options'] = {
                    'defaultType': 'swap',  # OKX uses 'swap' for perpetual futures
                }
            elif self.market_type == "option":
                config['options'] = {
                    'defaultType': 'option',
                }
            else:
                config['options'] = {
                    'defaultType': 'spot',
                }
            
            self.exchange = ccxt.okx(config)
            
            # Load markets
            self.exchange.load_markets()
            logger.info(f"Initialized OKX {self.market_type} adapter")
            
        except Exception as e:
            logger.error(f"Failed to initialize OKX adapter: {e}")
            raise
    
    def get_instruments(self, 
                       market_type: Optional[str] = None,
                       base_currency: Optional[str] = None,
                       quote_currency: Optional[str] = None) -> List[str]:
        """Get list of available trading instruments."""
        self._rate_limit_wait()
        
        try:
            markets = self.exchange.load_markets()
            instruments = []
            
            # Filter by market type
            target_market_type = market_type or self.market_type
            
            for symbol, market in markets.items():
                # OKX market type mapping
                market_type_map = {
                    'spot': 'spot',
                    'futures': 'future',
                    'perpetual': 'swap',
                    'option': 'option'
                }
                
                expected_type = market_type_map.get(target_market_type, 'spot')
                
                # Skip if market type doesn't match
                if market.get('type') != expected_type:
                    continue
                
                # Filter by base currency
                if base_currency and market.get('base') != base_currency.upper():
                    continue
                
                # Filter by quote currency  
                if quote_currency and market.get('quote') != quote_currency.upper():
                    continue
                
                # Only include active markets
                if market.get('active', True):
                    instruments.append(symbol)
            
            logger.info(f"Found {len(instruments)} instruments for {target_market_type}")
            return sorted(instruments)
            
        except Exception as e:
            logger.error(f"Failed to get instruments: {e}")
            return []
    
    def get_ohlcv(self,
                  symbol: str,
                  timeframe: str,
                  start_time: Optional[Union[datetime, str, int]] = None,
                  end_time: Optional[Union[datetime, str, int]] = None,
                  limit: Optional[int] = None) -> pd.DataFrame:
        """Get OHLCV data from OKX with automatic pagination for large requests."""
        
        # Convert string dates to datetime objects
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time)
        
        # Check if this is a large request that needs pagination
        if start_time and end_time and isinstance(start_time, datetime) and isinstance(end_time, datetime):
            timeframe_seconds = get_timeframe_seconds(timeframe)
            total_periods = int((end_time - start_time).total_seconds() / timeframe_seconds)
            
            # If the request is larger than our single request limit, use batching
            if total_periods > self.config.max_candles_per_request:
                logger.debug(f"Large request detected ({total_periods} periods), using pagination")
                return self.get_historical_data_batch(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=end_time
                )
        
        # For smaller requests, use the single request method
        self._rate_limit_wait()
        
        try:
            # Use centralized timeframe conversion instead of hardcoded mapping
            # IMPORTANT: OKX uses lowercase timeframes (1h, 1d, 1w), NOT uppercase!
            ccxt_timeframe = get_exchange_timeframe('okx', timeframe)
            
            # Validate against CCXT supported timeframes
            if ccxt_timeframe not in self.exchange.timeframes:
                raise ValueError(f"Timeframe {ccxt_timeframe} not supported by OKX. Supported: {list(self.exchange.timeframes.keys())}")

            # Prepare parameters
            params = {}
            if start_time:
                if isinstance(start_time, datetime):
                    start_time = int(start_time.timestamp() * 1000)
                params['since'] = start_time

            # Note: CCXT fetch_ohlcv doesn't support 'until' parameter
            # We'll use limit to control the amount of data returned
            if limit:
                params['limit'] = min(limit, self.config.max_candles_per_request)
            else:
                # Default limit for historical data
                params['limit'] = min(1000, self.config.max_candles_per_request)

            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(
                symbol,
                ccxt_timeframe,
                **params
            )
            
            if not ohlcv:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Ensure numeric types
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].astype(float)
            
            # Apply end_time filtering if specified
            if end_time:
                if isinstance(end_time, int):
                    end_time = pd.to_datetime(end_time, unit='ms')
                elif isinstance(end_time, datetime):
                    pass  # Already datetime
                
                # Filter data to only include records before end_time
                df = df[df.index < end_time]
            
            logger.debug(f"Retrieved {len(df)} OHLCV records for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker information."""
        self._rate_limit_wait()
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            return {}
    
    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Get current funding rate for perpetual contracts."""
        if self.market_type not in ["futures", "perpetual"]:
            return None
        
        self._rate_limit_wait()
        
        try:
            funding_rate = self.exchange.fetch_funding_rate(symbol)
            return funding_rate.get('fundingRate')
        except Exception as e:
            logger.warning(f"Failed to get funding rate for {symbol}: {e}")
            return None
    
    def get_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Get order book data."""
        self._rate_limit_wait()
        
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit)
            return order_book
        except Exception as e:
            logger.error(f"Failed to get order book for {symbol}: {e}")
            return {"bids": [], "asks": [], "timestamp": time.time() * 1000}
    
    def get_open_interest(self, symbol: str) -> Optional[float]:
        """Get open interest for futures/perpetual contracts."""
        if self.market_type not in ["futures", "perpetual"]:
            return None
        
        self._rate_limit_wait()
        
        try:
            if hasattr(self.exchange, 'fetch_open_interest'):
                oi = self.exchange.fetch_open_interest(symbol)
                return oi.get('openInterestAmount')
            else:
                return None
        except Exception as e:
            logger.warning(f"Failed to get open interest for {symbol}: {e}")
            return None
    
    def normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol format to OKX format."""
        # OKX uses the standard format (BTC/USDT)
        return symbol
    
    def standardize_symbol(self, symbol: str) -> str:
        """Convert OKX symbol to standard format."""
        # OKX already uses standard format
        return symbol
    
    def get_supported_timeframes(self) -> List[str]:
        """Get list of supported timeframes."""
        return self.config.supported_timeframes
    
    def validate_timeframe(self, timeframe: str) -> bool:
        """Validate if timeframe is supported."""
        return timeframe in self.config.supported_timeframes

    def get_24h_stats(self, symbol: str) -> Dict[str, Any]:
        """Get 24-hour statistics."""
        ticker = self.get_ticker(symbol)
        if not ticker:
            return {}

        return {
            "volume_24h": ticker.get("quoteVolume", 0),
            "change_24h": ticker.get("percentage", 0),
            "high_24h": ticker.get("high", 0),
            "low_24h": ticker.get("low", 0),
            "vwap": ticker.get("vwap", 0),
        }

    def get_historical_data_batch(self,
                                 symbol: str,
                                 timeframe: str,
                                 start_time: datetime,
                                 end_time: datetime,
                                 batch_size: Optional[int] = None) -> pd.DataFrame:
        """
        Get historical data in batches to handle large date ranges.

        Parameters
        ----------
        symbol : str
            Trading symbol
        timeframe : str
            Time interval
        start_time : datetime
            Start time
        end_time : datetime
            End time
        batch_size : int, optional
            Number of candles per batch

        Returns
        -------
        pd.DataFrame
            Combined historical data
        """
        if not batch_size:
            batch_size = self.config.max_candles_per_request

        # Calculate time delta per batch
        timeframe_seconds = get_timeframe_seconds(timeframe)
        batch_timedelta = timedelta(seconds=timeframe_seconds * batch_size)

        all_data = []
        current_start = start_time

        while current_start < end_time:
            current_end = min(current_start + batch_timedelta, end_time)

            batch_data = self.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_time=current_start,
                end_time=current_end,
                limit=batch_size
            )

            if not batch_data.empty:
                all_data.append(batch_data)

            current_start = current_end

            # Rate limiting
            time.sleep(self.rate_limit)

        if all_data:
            combined_data = pd.concat(all_data, ignore_index=False)
            combined_data = combined_data.drop_duplicates().sort_index()
            return combined_data

        return pd.DataFrame()

    def get_funding_history(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Get funding rate history for perpetual contracts.

        Parameters
        ----------
        symbol : str
            Trading symbol
        limit : int, default 100
            Number of records to retrieve

        Returns
        -------
        pd.DataFrame
            Funding rate history
        """
        if self.market_type not in ["futures", "perpetual"]:
            return pd.DataFrame()

        self._rate_limit_wait()

        try:
            if hasattr(self.exchange, 'fetch_funding_rate_history'):
                funding_history = self.exchange.fetch_funding_rate_history(symbol, limit=limit)

                if funding_history:
                    df = pd.DataFrame(funding_history)
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('timestamp', inplace=True)
                    return df

            return pd.DataFrame()

        except Exception as e:
            logger.warning(f"Failed to get funding history for {symbol}: {e}")
            return pd.DataFrame()

    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed market information for a symbol.

        Parameters
        ----------
        symbol : str
            Trading symbol

        Returns
        -------
        Dict[str, Any]
            Market information
        """
        try:
            markets = self.exchange.load_markets()
            market = markets.get(symbol, {})

            return {
                'symbol': symbol,
                'base': market.get('base'),
                'quote': market.get('quote'),
                'type': market.get('type'),
                'active': market.get('active'),
                'precision': market.get('precision', {}),
                'limits': market.get('limits', {}),
                'fees': market.get('fees', {}),
                'contract_size': market.get('contractSize'),
                'expiry': market.get('expiry'),
                'strike': market.get('strike'),
            }

        except Exception as e:
            logger.error(f"Failed to get market info for {symbol}: {e}")
            return {}

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
        try:
            ticker = self.exchange.fetch_ticker(symbol)

            # Standardize ticker data
            standardized_ticker = {
                'symbol': symbol,
                'timestamp': ticker.get('timestamp'),
                'datetime': ticker.get('datetime'),
                'last': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'volume': ticker.get('baseVolume'),  # Base volume
                'volume_quote': ticker.get('quoteVolume'),  # Quote volume (24h)
                'volume_24h': ticker.get('quoteVolume'),  # 24h volume in quote currency
                'change_24h': ticker.get('percentage'),  # 24h percentage change
                'high_24h': ticker.get('high'),
                'low_24h': ticker.get('low'),
                'open_24h': ticker.get('open'),
                'close_24h': ticker.get('close'),
                'vwap': ticker.get('vwap'),
            }

            # Calculate additional fields
            if ticker.get('bid') and ticker.get('ask'):
                bid = float(ticker['bid'])
                ask = float(ticker['ask'])
                if bid > 0:
                    standardized_ticker['bid_ask_spread'] = (ask - bid) / bid

            return standardized_ticker

        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol} on OKX: {e}")
            raise

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
        try:
            # Check if symbol is a perpetual contract
            market = self.exchange.market(symbol)
            if not market.get('swap', False):
                logger.debug(f"Symbol {symbol} is not a perpetual contract")
                return None

            # Fetch funding rate
            funding_rate = self.exchange.fetch_funding_rate(symbol)

            if funding_rate:
                return {
                    'symbol': symbol,
                    'funding_rate': funding_rate.get('fundingRate'),
                    'funding_timestamp': funding_rate.get('fundingTimestamp'),
                    'funding_datetime': funding_rate.get('fundingDatetime'),
                    'next_funding_time': funding_rate.get('nextFundingTime'),
                    'next_funding_datetime': funding_rate.get('nextFundingDatetime'),
                }

            return None

        except Exception as e:
            logger.warning(f"Failed to get funding rate for {symbol} on OKX: {e}")
            return None

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
        try:
            # Check if symbol is a futures/perpetual contract
            market = self.exchange.market(symbol)
            if not (market.get('future', False) or market.get('swap', False)):
                logger.debug(f"Symbol {symbol} is not a futures/perpetual contract")
                return None

            # Fetch open interest
            open_interest = self.exchange.fetch_open_interest(symbol)

            if open_interest:
                return {
                    'symbol': symbol,
                    'open_interest': open_interest.get('openInterestAmount'),
                    'open_interest_value': open_interest.get('openInterestValue'),
                    'timestamp': open_interest.get('timestamp'),
                    'datetime': open_interest.get('datetime'),
                }

            return None

        except Exception as e:
            logger.warning(f"Failed to get open interest for {symbol} on OKX: {e}")
            return None

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
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit)
            return order_book

        except Exception as e:
            logger.warning(f"Failed to get order book for {symbol} on OKX: {e}")
            return None

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
        try:
            markets = self.exchange.load_markets()

            if market_type == "spot":
                symbols = [symbol for symbol, market in markets.items()
                          if market.get('spot', False) and market.get('active', True)]
            elif market_type == "futures":
                symbols = [symbol for symbol, market in markets.items()
                          if market.get('future', False) and market.get('active', True)]
            elif market_type == "perpetual":
                symbols = [symbol for symbol, market in markets.items()
                          if market.get('swap', False) and market.get('active', True)]
            elif market_type == "option":
                symbols = [symbol for symbol, market in markets.items()
                          if market.get('option', False) and market.get('active', True)]
            else:
                logger.warning(f"Unsupported market type for OKX: {market_type}")
                return []

            return sorted(symbols)

        except Exception as e:
            logger.error(f"Error getting symbols from OKX: {e}")
            return []

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
        try:
            markets = self.exchange.load_markets()

            if symbol not in markets:
                logger.warning(f"Symbol {symbol} not found on OKX")
                return {}

            market = markets[symbol]

            # Get additional market data
            try:
                ticker_data = self.get_ticker(symbol)
            except Exception:
                ticker_data = {}

            symbol_info = {
                'symbol': symbol,
                'base': market.get('base'),
                'quote': market.get('quote'),
                'active': market.get('active', False),
                'spot': market.get('spot', False),
                'future': market.get('future', False),
                'swap': market.get('swap', False),
                'option': market.get('option', False),
                'contract': market.get('contract', False),
                'linear': market.get('linear'),
                'inverse': market.get('inverse'),
                'taker_fee': market.get('taker'),
                'maker_fee': market.get('maker'),
                'min_amount': market.get('limits', {}).get('amount', {}).get('min'),
                'max_amount': market.get('limits', {}).get('amount', {}).get('max'),
                'min_price': market.get('limits', {}).get('price', {}).get('min'),
                'max_price': market.get('limits', {}).get('price', {}).get('max'),
                'price_precision': market.get('precision', {}).get('price'),
                'amount_precision': market.get('precision', {}).get('amount'),
                'volume_24h': ticker_data.get('volume_24h'),
                'price': ticker_data.get('last'),
                'change_24h': ticker_data.get('change_24h'),
                'timestamp': ticker_data.get('timestamp'),
            }

            # Determine market type for OKX
            if market.get('spot'):
                symbol_info['market_type'] = 'spot'
            elif market.get('future'):
                symbol_info['market_type'] = 'futures'
            elif market.get('swap'):
                symbol_info['market_type'] = 'perpetual'
            elif market.get('option'):
                symbol_info['market_type'] = 'option'
            else:
                symbol_info['market_type'] = 'unknown'

            return symbol_info

        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol} from OKX: {e}")
            return {}
