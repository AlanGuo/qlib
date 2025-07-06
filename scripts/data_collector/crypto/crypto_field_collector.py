#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Crypto Field Collector

This module provides functionality to collect cryptocurrency-specific data fields
such as funding rates, open interest, 24h volume, and bid-ask spreads.
"""

import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from exchange_adapters.base_adapter import ExchangeAdapter
from config.fields import (
    ALL_FIELDS, 
    is_field_supported_for_exchange,
    get_field_config,
    filter_fields_by_market_type
)


class CryptoFieldCollector:
    """
    Collector for cryptocurrency-specific data fields.
    
    This class coordinates the collection of crypto-specific fields like funding rates,
    open interest, 24h volume, and bid-ask spreads from various exchanges.
    """
    
    def __init__(self, adapter: ExchangeAdapter):
        """
        Initialize the crypto field collector.
        
        Parameters
        ----------
        adapter : ExchangeAdapter
            Exchange adapter instance
        """
        self.adapter = adapter
        self.exchange_id = adapter.exchange_id
        
    def collect_ticker_fields(self, symbol: str, fields: List[str] = None) -> Dict[str, Any]:
        """
        Collect ticker-based fields for a symbol.
        
        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")
        fields : List[str], optional
            Specific fields to collect. If None, collects all supported ticker fields
            
        Returns
        -------
        Dict[str, Any]
            Dictionary containing the collected field data
        """
        if fields is None:
            # Default ticker fields
            fields = ['volume_24h', 'change_24h', 'high_24h', 'low_24h', 'vwap', 'spread']
        
        try:
            ticker_data = self.adapter.get_ticker(symbol)
            
            result = {
                'symbol': symbol,
                'timestamp': ticker_data.get('timestamp'),
                'datetime': ticker_data.get('datetime'),
            }
            
            # Extract requested fields
            for field in fields:
                if field in ticker_data:
                    result[field] = ticker_data[field]
                else:
                    result[field] = None
                    
            return result
            
        except Exception as e:
            logger.error(f"Failed to collect ticker fields for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def collect_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Collect funding rate data for a perpetual contract.
        
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
            return self.adapter.get_funding_rate(symbol)
        except Exception as e:
            logger.error(f"Failed to collect funding rate for {symbol}: {e}")
            return None
    
    def collect_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Collect open interest data for a futures/perpetual contract.
        
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
            return self.adapter.get_open_interest(symbol)
        except Exception as e:
            logger.error(f"Failed to collect open interest for {symbol}: {e}")
            return None
    
    def collect_order_book_fields(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Collect order book based fields like bid-ask spread.
        
        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")
        limit : int, default 20
            Number of order book levels to fetch
            
        Returns
        -------
        Dict[str, Any]
            Order book derived data
        """
        try:
            order_book = self.adapter.get_order_book(symbol, limit)
            
            result = {
                'symbol': symbol,
                'timestamp': order_book.get('timestamp') if order_book else None,
                'datetime': order_book.get('datetime') if order_book else None,
            }
            
            if order_book:
                # Calculate bid-ask spread
                spread = self.adapter.calculate_bid_ask_spread(order_book)
                result['spread'] = spread
                
                # Add best bid/ask
                if order_book.get('bids') and order_book['bids']:
                    result['best_bid'] = float(order_book['bids'][0][0])
                    result['best_bid_size'] = float(order_book['bids'][0][1])
                
                if order_book.get('asks') and order_book['asks']:
                    result['best_ask'] = float(order_book['asks'][0][0])
                    result['best_ask_size'] = float(order_book['asks'][0][1])
            else:
                result['spread'] = None
                result['best_bid'] = None
                result['best_ask'] = None
                result['best_bid_size'] = None
                result['best_ask_size'] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to collect order book fields for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def collect_all_crypto_fields(self, symbol: str, market_type: str = "spot") -> Dict[str, Any]:
        """
        Collect all available cryptocurrency-specific fields for a symbol.
        
        Parameters
        ----------
        symbol : str
            Symbol in standard format (e.g., "BTC/USDT")
        market_type : str, default "spot"
            Market type (spot, futures, perpetual)
            
        Returns
        -------
        Dict[str, Any]
            Dictionary containing all collected crypto fields
        """
        result = {
            'symbol': symbol,
            'market_type': market_type,
            'exchange': self.exchange_id,
            'collection_timestamp': datetime.now().isoformat(),
        }
        
        # Collect ticker fields
        logger.info(f"Collecting ticker fields for {symbol}")
        ticker_data = self.collect_ticker_fields(symbol)
        result.update(ticker_data)
        
        # Collect funding rate for perpetual contracts
        if market_type in ["perpetual", "futures"]:
            logger.info(f"Collecting funding rate for {symbol}")
            funding_data = self.collect_funding_rate(symbol)
            if funding_data:
                result.update(funding_data)
        
        # Collect open interest for futures/perpetual contracts
        if market_type in ["perpetual", "futures"]:
            logger.info(f"Collecting open interest for {symbol}")
            oi_data = self.collect_open_interest(symbol)
            if oi_data:
                result.update(oi_data)
        
        # Collect order book fields
        logger.info(f"Collecting order book fields for {symbol}")
        ob_data = self.collect_order_book_fields(symbol)
        result.update(ob_data)
        
        return result
    
    def collect_batch_crypto_fields(
        self, 
        symbols: List[str], 
        market_type: str = "spot",
        delay: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Collect cryptocurrency fields for multiple symbols.
        
        Parameters
        ----------
        symbols : List[str]
            List of symbols to collect data for
        market_type : str, default "spot"
            Market type (spot, futures, perpetual)
        delay : float, default 0.1
            Delay between requests in seconds
            
        Returns
        -------
        List[Dict[str, Any]]
            List of collected data for each symbol
        """
        results = []
        
        for i, symbol in enumerate(symbols):
            logger.info(f"Collecting crypto fields for {symbol} ({i+1}/{len(symbols)})")
            
            try:
                data = self.collect_all_crypto_fields(symbol, market_type)
                results.append(data)
                
            except Exception as e:
                logger.error(f"Failed to collect crypto fields for {symbol}: {e}")
                results.append({
                    'symbol': symbol,
                    'error': str(e),
                    'collection_timestamp': datetime.now().isoformat(),
                })
            
            # Rate limiting
            if delay > 0 and i < len(symbols) - 1:
                time.sleep(delay)
        
        return results
    
    def get_supported_fields_for_market_type(self, market_type: str) -> List[str]:
        """
        Get list of supported crypto fields for a specific market type.
        
        Parameters
        ----------
        market_type : str
            Market type (spot, futures, perpetual)
            
        Returns
        -------
        List[str]
            List of supported field names
        """
        # Get all crypto-specific fields
        crypto_fields = [
            name for name, config in ALL_FIELDS.items()
            if config.description and any(keyword in config.description.lower() 
                                        for keyword in ['crypto', 'funding', 'perpetual', 'futures'])
        ]
        
        # Filter by market type
        supported_fields = filter_fields_by_market_type(crypto_fields, market_type)
        
        # Filter by exchange support
        exchange_supported = [
            field for field in supported_fields
            if is_field_supported_for_exchange(field, self.exchange_id, market_type)
        ]
        
        return exchange_supported
