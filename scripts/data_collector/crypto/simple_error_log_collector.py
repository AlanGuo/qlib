# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Simplified error logging collector for cryptocurrency data collection.

This module provides a simple data collection capability that handles
BadSymbol error logging intelligently to avoid log pollution, without
complex delisting detection or lifecycle management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Set
import pandas as pd
import time

try:
    import ccxt
except ImportError:
    logging.error("ccxt library is required. Install with: pip install ccxt")
    raise

from exchange_adapters.base_adapter import ExchangeAdapter

logger = logging.getLogger(__name__)


class SimpleErrorLogCollector:
    """
    Simplified data collector that handles BadSymbol error logging intelligently.
    
    Features:
    - Smart logging level management for BadSymbol errors
    - Simple error caching to avoid log pollution
    - Basic retry mechanism for network errors
    - No complex delisting detection or lifecycle management
    """
    
    def __init__(self, 
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 enable_smart_logging: bool = True,
                 error_cache_ttl: int = 24 * 3600):
        """
        Initialize simplified error logging collector.
        
        Parameters
        ----------
        max_retries : int
            Maximum number of retries for failed requests
        retry_delay : float
            Delay between retries in seconds
        enable_smart_logging : bool
            Enable smart logging level management for BadSymbol errors
        error_cache_ttl : int
            Error cache TTL in seconds (default: 24 hours)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Smart logging management
        self.enable_smart_logging = enable_smart_logging
        self.error_cache_ttl = error_cache_ttl
        self._logged_bad_symbols: Set[str] = set()
        self._bad_symbol_cache: Dict[str, datetime] = {}
        
        # Basic statistics
        self.stats = {
            'total_attempts': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'bad_symbol_errors': 0,
            'other_errors': 0
        }
    
    def _get_symbol_cache_key(self, adapter: ExchangeAdapter, symbol: str) -> str:
        """
        Generate cache key for symbol error tracking.
        
        Parameters
        ----------
        adapter : ExchangeAdapter
            Exchange adapter instance
        symbol : str
            Trading symbol
            
        Returns
        -------
        str
            Cache key in format: {exchange_id}_{symbol}
        """
        return f"{adapter.exchange_id}_{symbol}"
    
    def _should_log_bad_symbol_error(self, cache_key: str) -> bool:
        """
        Determine if BadSymbol error should be logged at WARNING level.
        
        Parameters
        ----------
        cache_key : str
            Symbol cache key
            
        Returns
        -------
        bool
            True if should log at WARNING level, False for DEBUG level
        """
        if not self.enable_smart_logging:
            return True  # Always log if smart logging is disabled
        
        # Clean up expired cache entries
        self._cleanup_expired_cache()
        
        # Check if we've already logged this symbol
        return cache_key not in self._logged_bad_symbols
    
    def _mark_bad_symbol_logged(self, cache_key: str):
        """
        Mark symbol as having been logged for BadSymbol error.
        
        Parameters
        ----------
        cache_key : str
            Symbol cache key
        """
        if not self.enable_smart_logging:
            return
        
        current_time = datetime.now()
        self._logged_bad_symbols.add(cache_key)
        self._bad_symbol_cache[cache_key] = current_time
    
    def _cleanup_expired_cache(self):
        """Clean up expired error cache entries."""
        if not self.enable_smart_logging:
            return
        
        current_time = datetime.now()
        expired_keys = [
            key for key, timestamp in self._bad_symbol_cache.items()
            if (current_time - timestamp).total_seconds() > self.error_cache_ttl
        ]
        
        for key in expired_keys:
            self._bad_symbol_cache.pop(key, None)
            self._logged_bad_symbols.discard(key)
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired error cache entries")
    
    def collect_symbol_data(self,
                          adapter: ExchangeAdapter,
                          symbol: str,
                          timeframe: str,
                          start_time: Union[datetime, str],
                          end_time: Union[datetime, str]) -> Dict[str, Any]:
        """
        Collect data for a single symbol with smart error logging.
        
        Parameters
        ----------
        adapter : ExchangeAdapter
            Exchange adapter instance
        symbol : str
            Trading symbol
        timeframe : str
            Data timeframe
        start_time : Union[datetime, str]
            Start time for data collection
        end_time : Union[datetime, str]
            End time for data collection
            
        Returns
        -------
        Dict[str, Any]
            Collection result with data and metadata
        """
        # Convert string dates to datetime
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time)
        
        self.stats['total_attempts'] += 1
        
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'start_time': start_time,
            'end_time': end_time,
            'status': 'pending',
            'data': pd.DataFrame(),
            'errors': []
        }
        
        try:
            # Attempt to collect data with retry logic
            data = self._collect_data_with_retry(adapter, symbol, timeframe, start_time, end_time)
            
            if not data.empty:
                result['data'] = data
                result['status'] = 'success'
                self.stats['successful_collections'] += 1
                logger.debug(f"Successfully collected {len(data)} records for {symbol}")
            else:
                result['status'] = 'failed'
                result['errors'].append('No data returned')
                self.stats['failed_collections'] += 1
                logger.warning(f"No data returned for {symbol}")
                
        except Exception as e:
            logger.error(f"Error collecting data for {symbol}: {e}")
            result['status'] = 'failed'
            result['errors'].append(str(e))
            self.stats['failed_collections'] += 1
            
            # Update specific error statistics
            if isinstance(e, ccxt.BadSymbol):
                self.stats['bad_symbol_errors'] += 1
            else:
                self.stats['other_errors'] += 1
        
        return result
    
    def _collect_data_with_retry(self,
                               adapter: ExchangeAdapter,
                               symbol: str,
                               timeframe: str,
                               start_time: datetime,
                               end_time: datetime) -> pd.DataFrame:
        """Collect data with retry logic and smart error handling."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Collecting data for {symbol} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Attempt to get data from adapter
                data = adapter.get_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if not data.empty:
                    return data
                else:
                    logger.warning(f"Empty data returned for {symbol} on attempt {attempt + 1}")
                    
            except ccxt.BadSymbol as e:
                # Smart logging for BadSymbol errors
                cache_key = self._get_symbol_cache_key(adapter, symbol)
                
                if self._should_log_bad_symbol_error(cache_key):
                    logger.warning(f"Symbol {symbol} not found: {e}")
                    self._mark_bad_symbol_logged(cache_key)
                else:
                    logger.debug(f"Symbol {symbol} not found (known issue): {e}")
                
                # Directly raise the exception without complex handling
                raise
                
            except ccxt.MarketClosed as e:
                logger.warning(f"Market closed for {symbol}: {e}")
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise
                    
            except ccxt.ExchangeNotAvailable as e:
                logger.warning(f"Exchange not available for {symbol}: {e}")
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise
                    
            except ccxt.RateLimitExceeded as e:
                logger.warning(f"Rate limit exceeded for {symbol}: {e}")
                # Exponential backoff for rate limiting
                backoff_time = self.retry_delay * (2 ** attempt)
                logger.info(f"Rate limit hit, waiting {backoff_time} seconds before retry")
                time.sleep(backoff_time)
                last_exception = e
                if attempt < self.max_retries:
                    continue
                else:
                    raise
                    
            except ccxt.NetworkError as e:
                logger.warning(f"Network error for {symbol}: {e}")
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error collecting data for {symbol}: {e}")
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise Exception(f"Failed to collect data for {symbol} after {self.max_retries + 1} attempts")
    
    def collect_multiple_symbols(self,
                               adapter: ExchangeAdapter,
                               symbols: List[str],
                               timeframe: str,
                               start_time: Union[datetime, str],
                               end_time: Union[datetime, str]) -> Dict[str, Any]:
        """
        Collect data for multiple symbols with smart error logging.
        
        Parameters
        ----------
        adapter : ExchangeAdapter
            Exchange adapter instance
        symbols : List[str]
            List of trading symbols
        timeframe : str
            Data timeframe
        start_time : Union[datetime, str]
            Start time for data collection
        end_time : Union[datetime, str]
            End time for data collection
            
        Returns
        -------
        Dict[str, Any]
            Collection results for all symbols
        """
        logger.info(f"Collecting data for {len(symbols)} symbols from {start_time} to {end_time}")
        
        # Reset stats for this batch
        batch_start_stats = self.stats.copy()
        results = {}
        
        for symbol in symbols:
            logger.info(f"Collecting data for {symbol}")
            
            try:
                result = self.collect_symbol_data(
                    adapter=adapter,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=end_time
                )
                results[symbol] = result
                
                # Log result
                if result['status'] == 'success':
                    logger.info(f"✅ Successfully collected {len(result['data'])} records for {symbol}")
                else:
                    logger.warning(f"❌ Failed to collect data for {symbol}: {result['errors']}")
                    
            except Exception as e:
                logger.error(f"Error processing symbol {symbol}: {e}")
                results[symbol] = {
                    'symbol': symbol,
                    'status': 'error',
                    'errors': [str(e)],
                    'data': pd.DataFrame()
                }
        
        # Calculate batch statistics
        batch_stats = {
            'total_symbols': len(symbols),
            'successful_symbols': [s for s, r in results.items() if r['status'] == 'success'],
            'failed_symbols': [s for s, r in results.items() if r['status'] in ['failed', 'error']],
            'attempts_in_batch': self.stats['total_attempts'] - batch_start_stats['total_attempts'],
            'success_rate': len([r for r in results.values() if r['status'] == 'success']) / len(symbols) * 100
        }
        
        logger.info(f"Batch collection completed: {len(batch_stats['successful_symbols'])} successful, "
                   f"{len(batch_stats['failed_symbols'])} failed")
        
        return {
            'results': results,
            'batch_stats': batch_stats,
            'summary': batch_stats
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset collection statistics."""
        self.stats = {
            'total_attempts': 0,
            'successful_collections': 0,
            'failed_collections': 0,
            'bad_symbol_errors': 0,
            'other_errors': 0
        }
    
    def get_smart_logging_stats(self) -> Dict[str, Any]:
        """
        Get smart logging statistics.
        
        Returns
        -------
        Dict[str, Any]
            Statistics about smart logging cache
        """
        self._cleanup_expired_cache()  # Clean up before reporting
        
        return {
            'smart_logging_enabled': self.enable_smart_logging,
            'error_cache_ttl': self.error_cache_ttl,
            'cached_bad_symbols': len(self._logged_bad_symbols),
            'cache_entries': list(self._logged_bad_symbols),
            'oldest_cache_entry': min(self._bad_symbol_cache.values()) if self._bad_symbol_cache else None,
            'newest_cache_entry': max(self._bad_symbol_cache.values()) if self._bad_symbol_cache else None
        }
    
    def update_smart_logging_config(self, 
                                  enable_smart_logging: Optional[bool] = None,
                                  error_cache_ttl: Optional[int] = None):
        """
        Update smart logging configuration at runtime.
        
        Parameters
        ----------
        enable_smart_logging : bool, optional
            Enable/disable smart logging
        error_cache_ttl : int, optional
            New cache TTL in seconds
        """
        if enable_smart_logging is not None:
            self.enable_smart_logging = enable_smart_logging
            if not enable_smart_logging:
                # Clear cache when disabling
                self._logged_bad_symbols.clear()
                self._bad_symbol_cache.clear()
                logger.info("Smart logging disabled, cleared error cache")
        
        if error_cache_ttl is not None:
            self.error_cache_ttl = error_cache_ttl
            # Clean up with new TTL
            self._cleanup_expired_cache()
            logger.info(f"Updated error cache TTL to {error_cache_ttl} seconds")
