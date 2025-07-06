# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Symbol discovery for cryptocurrency investment universe management.

This module provides functionality to discover and analyze available
trading symbols across different cryptocurrency exchanges.
"""

import time
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
from loguru import logger

from exchange_adapters.base_adapter import ExchangeAdapter
from config.universe_config import UniverseConfig, FilterConfig


@dataclass
class SymbolInfo:
    """Information about a trading symbol."""
    
    symbol: str
    base: str
    quote: str
    exchange: str
    market_type: str
    active: bool
    
    # Market data
    price: Optional[float] = None
    volume_24h: Optional[float] = None
    volume_usd_24h: Optional[float] = None
    change_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    
    # Contract info (for derivatives)
    contract_size: Optional[float] = None
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    
    # Trading info
    taker_fee: Optional[float] = None
    maker_fee: Optional[float] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # Metadata
    listing_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result


class SymbolDiscovery:
    """
    Symbol discovery and analysis for cryptocurrency exchanges.
    
    This class provides functionality to discover available trading symbols,
    collect their market information, and analyze their characteristics.
    """
    
    def __init__(self, adapters: Dict[str, ExchangeAdapter]):
        """
        Initialize symbol discovery.
        
        Parameters
        ----------
        adapters : Dict[str, ExchangeAdapter]
            Dictionary of exchange adapters keyed by exchange name
        """
        self.adapters = adapters
        self._symbol_cache: Dict[str, Dict[str, SymbolInfo]] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(hours=1)  # Cache for 1 hour
    
    def discover_symbols(
        self,
        exchanges: List[str] = None,
        market_types: List[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, List[SymbolInfo]]:
        """
        Discover available symbols across exchanges.
        
        Parameters
        ----------
        exchanges : List[str], optional
            List of exchanges to query. If None, uses all available adapters
        market_types : List[str], optional
            List of market types to include. If None, includes all types
        force_refresh : bool, default False
            Whether to force refresh the cache
            
        Returns
        -------
        Dict[str, List[SymbolInfo]]
            Dictionary mapping exchange names to lists of symbol information
        """
        if exchanges is None:
            exchanges = list(self.adapters.keys())
        
        if market_types is None:
            market_types = ["spot", "futures", "perpetual", "option"]
        
        results = {}
        
        for exchange in exchanges:
            if exchange not in self.adapters:
                logger.warning(f"Exchange {exchange} not available in adapters")
                continue
            
            logger.info(f"Discovering symbols on {exchange}")
            
            # Check cache
            cache_key = f"{exchange}_{'-'.join(market_types)}"
            if (not force_refresh and 
                cache_key in self._symbol_cache and 
                cache_key in self._cache_timestamp and
                datetime.now() - self._cache_timestamp[cache_key] < self.cache_ttl):
                
                logger.debug(f"Using cached symbols for {exchange}")
                results[exchange] = list(self._symbol_cache[cache_key].values())
                continue
            
            # Discover symbols for this exchange
            exchange_symbols = []
            adapter = self.adapters[exchange]
            
            for market_type in market_types:
                try:
                    symbols = adapter.get_symbols(market_type)
                    logger.info(f"Found {len(symbols)} {market_type} symbols on {exchange}")
                    
                    for symbol in symbols:
                        try:
                            symbol_info = self._get_symbol_info(adapter, symbol, exchange, market_type)
                            if symbol_info:
                                exchange_symbols.append(symbol_info)
                        except Exception as e:
                            logger.warning(f"Error getting info for {symbol} on {exchange}: {e}")
                            continue
                        
                        # Rate limiting
                        time.sleep(0.1)
                
                except Exception as e:
                    logger.error(f"Error discovering {market_type} symbols on {exchange}: {e}")
                    continue
            
            results[exchange] = exchange_symbols
            
            # Update cache
            self._symbol_cache[cache_key] = {s.symbol: s for s in exchange_symbols}
            self._cache_timestamp[cache_key] = datetime.now()
            
            logger.info(f"Discovered {len(exchange_symbols)} total symbols on {exchange}")
        
        return results
    
    def _get_symbol_info(
        self,
        adapter: ExchangeAdapter,
        symbol: str,
        exchange: str,
        market_type: str
    ) -> Optional[SymbolInfo]:
        """Get detailed information for a symbol."""
        try:
            # Get basic symbol info
            info = adapter.get_symbol_info(symbol)
            if not info:
                return None
            
            # Get market data
            try:
                ticker = adapter.get_ticker(symbol)
            except Exception:
                ticker = {}
            
            # Calculate USD volume if possible
            volume_usd_24h = None
            if ticker.get('volume_24h') and ticker.get('last'):
                try:
                    volume_usd_24h = float(ticker['volume_24h']) * float(ticker['last'])
                except (ValueError, TypeError):
                    pass
            
            # Get derivative-specific data
            funding_rate = None
            open_interest = None
            
            if market_type in ["futures", "perpetual"]:
                try:
                    funding_data = adapter.get_funding_rate(symbol)
                    if funding_data:
                        funding_rate = funding_data.get('funding_rate')
                except Exception:
                    pass
                
                try:
                    oi_data = adapter.get_open_interest(symbol)
                    if oi_data:
                        open_interest = oi_data.get('open_interest')
                except Exception:
                    pass
            
            return SymbolInfo(
                symbol=symbol,
                base=info.get('base', ''),
                quote=info.get('quote', ''),
                exchange=exchange,
                market_type=market_type,
                active=info.get('active', False),
                price=ticker.get('last'),
                volume_24h=ticker.get('volume_24h'),
                volume_usd_24h=volume_usd_24h,
                change_24h=ticker.get('change_24h'),
                high_24h=ticker.get('high_24h'),
                low_24h=ticker.get('low_24h'),
                funding_rate=funding_rate,
                open_interest=open_interest,
                taker_fee=info.get('taker_fee'),
                maker_fee=info.get('maker_fee'),
                min_amount=info.get('min_amount'),
                max_amount=info.get('max_amount'),
                min_price=info.get('min_price'),
                max_price=info.get('max_price'),
                last_updated=datetime.now(),
            )
            
        except Exception as e:
            logger.warning(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_symbol_statistics(
        self,
        symbols: List[SymbolInfo]
    ) -> Dict[str, Any]:
        """
        Get statistics about discovered symbols.
        
        Parameters
        ----------
        symbols : List[SymbolInfo]
            List of symbol information
            
        Returns
        -------
        Dict[str, Any]
            Statistics about the symbols
        """
        if not symbols:
            return {}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([s.to_dict() for s in symbols])
        
        stats = {
            'total_symbols': len(symbols),
            'active_symbols': len(df[df['active'] == True]),
            'inactive_symbols': len(df[df['active'] == False]),
            'exchanges': df['exchange'].value_counts().to_dict(),
            'market_types': df['market_type'].value_counts().to_dict(),
            'base_assets': df['base'].value_counts().head(20).to_dict(),
            'quote_assets': df['quote'].value_counts().to_dict(),
        }
        
        # Volume statistics
        volume_data = df[df['volume_usd_24h'].notna()]['volume_usd_24h']
        if not volume_data.empty:
            stats['volume_stats'] = {
                'mean': float(volume_data.mean()),
                'median': float(volume_data.median()),
                'min': float(volume_data.min()),
                'max': float(volume_data.max()),
                'total': float(volume_data.sum()),
            }
        
        # Price change statistics
        change_data = df[df['change_24h'].notna()]['change_24h']
        if not change_data.empty:
            stats['change_stats'] = {
                'mean': float(change_data.mean()),
                'median': float(change_data.median()),
                'min': float(change_data.min()),
                'max': float(change_data.max()),
                'std': float(change_data.std()),
            }
        
        return stats
    
    def find_common_symbols(
        self,
        exchange_symbols: Dict[str, List[SymbolInfo]],
        min_exchanges: int = 2
    ) -> List[str]:
        """
        Find symbols that are available on multiple exchanges.
        
        Parameters
        ----------
        exchange_symbols : Dict[str, List[SymbolInfo]]
            Dictionary mapping exchange names to symbol lists
        min_exchanges : int, default 2
            Minimum number of exchanges a symbol must be on
            
        Returns
        -------
        List[str]
            List of symbols available on at least min_exchanges
        """
        symbol_counts = {}
        
        for exchange, symbols in exchange_symbols.items():
            for symbol_info in symbols:
                symbol = symbol_info.symbol
                if symbol not in symbol_counts:
                    symbol_counts[symbol] = set()
                symbol_counts[symbol].add(exchange)
        
        common_symbols = [
            symbol for symbol, exchanges in symbol_counts.items()
            if len(exchanges) >= min_exchanges
        ]
        
        return sorted(common_symbols)
    
    def clear_cache(self) -> None:
        """Clear the symbol cache."""
        self._symbol_cache.clear()
        self._cache_timestamp.clear()
        logger.info("Symbol cache cleared")
