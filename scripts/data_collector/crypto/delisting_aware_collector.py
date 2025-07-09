# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Delisting-aware data collection module.

This module provides enhanced data collection capabilities that handle
symbol delisting scenarios gracefully, including partial data collection
and delisting detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
from pathlib import Path
import time

try:
    import ccxt
except ImportError:
    logging.error("ccxt library is required. Install with: pip install ccxt")
    raise

from symbol_lifecycle import SymbolLifecycleManager, SymbolStatus
from exchange_adapters.base_adapter import ExchangeAdapter

logger = logging.getLogger(__name__)


class DelistingAwareCollector:
    """
    Enhanced data collector that handles symbol delisting scenarios.
    
    Features:
    - Partial data collection for symbols delisted mid-period
    - Automatic delisting detection
    - Graceful error handling for delisted symbols
    - Collection resumption after temporary suspensions
    """
    
    def __init__(self, 
                 lifecycle_manager: SymbolLifecycleManager,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 enable_partial_collection: bool = True):
        """
        Initialize delisting-aware collector.
        
        Parameters
        ----------
        lifecycle_manager : SymbolLifecycleManager
            Symbol lifecycle manager instance
        max_retries : int
            Maximum number of retries for failed requests
        retry_delay : float
            Delay between retries in seconds
        enable_partial_collection : bool
            Enable partial data collection for delisted symbols
        """
        self.lifecycle_manager = lifecycle_manager
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_partial_collection = enable_partial_collection
        
        # Collection statistics
        self.stats = {
            'total_symbols': 0,
            'successful_collections': 0,
            'partial_collections': 0,
            'failed_collections': 0,
            'delisted_symbols': 0,
            'suspended_symbols': 0,
            'collection_windows': []
        }
    
    def collect_symbol_data(self,
                          adapter: ExchangeAdapter,
                          symbol: str,
                          timeframe: str,
                          start_time: Union[datetime, str],
                          end_time: Union[datetime, str],
                          fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Collect data for a single symbol with delisting awareness.
        
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
        fields : Optional[List[str]]
            Data fields to collect
            
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
        
        self.stats['total_symbols'] += 1
        
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'start_time': start_time,
            'end_time': end_time,
            'status': 'pending',
            'data': pd.DataFrame(),
            'collection_windows': [],
            'delisting_events': [],
            'errors': [],
            'metadata': {}
        }
        
        try:
            # Check symbol lifecycle status
            status_record = self.lifecycle_manager.get_symbol_status(
                symbol=symbol,
                exchange=adapter.exchange_id,
                market_type=getattr(adapter, 'market_type', 'spot')
            )
            
            # Handle different symbol statuses
            if status_record.status == SymbolStatus.DELISTED:
                return self._handle_delisted_symbol(adapter, symbol, timeframe, start_time, end_time, result)
            
            elif status_record.status == SymbolStatus.SUSPENDED:
                return self._handle_suspended_symbol(adapter, symbol, timeframe, start_time, end_time, result)
            
            elif status_record.status == SymbolStatus.ACTIVE:
                return self._handle_active_symbol(adapter, symbol, timeframe, start_time, end_time, result)
            
            else:  # UNKNOWN status
                return self._handle_unknown_symbol(adapter, symbol, timeframe, start_time, end_time, result)
                
        except Exception as e:
            logger.error(f"Error collecting data for {symbol}: {e}")
            result['status'] = 'failed'
            result['errors'].append(str(e))
            self.stats['failed_collections'] += 1
            return result
    
    def _handle_delisted_symbol(self,
                              adapter: ExchangeAdapter,
                              symbol: str,
                              timeframe: str,
                              start_time: datetime,
                              end_time: datetime,
                              result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data collection for a delisted symbol."""
        logger.info(f"Handling delisted symbol: {symbol}")
        
        if not self.enable_partial_collection:
            result['status'] = 'failed'
            result['errors'].append('Symbol is delisted and partial collection is disabled')
            self.stats['failed_collections'] += 1
            return result
        
        # Get availability windows for the requested period
        collection_windows = self.lifecycle_manager.get_collection_time_windows(
            symbol=symbol,
            exchange=adapter.exchange_id,
            start_time=start_time,
            end_time=end_time,
            market_type=getattr(adapter, 'market_type', 'spot')
        )
        
        if not collection_windows:
            result['status'] = 'failed'
            result['errors'].append('No availability windows found for delisted symbol')
            self.stats['failed_collections'] += 1
            return result
        
        # Collect data for each availability window
        all_data = []
        for window_start, window_end in collection_windows:
            logger.info(f"Collecting partial data for {symbol} from {window_start} to {window_end}")
            
            try:
                window_data = self._collect_data_window(adapter, symbol, timeframe, window_start, window_end)
                if not window_data.empty:
                    all_data.append(window_data)
                    result['collection_windows'].append({
                        'start': window_start,
                        'end': window_end,
                        'records': len(window_data)
                    })
            except Exception as e:
                logger.warning(f"Failed to collect data for window {window_start}-{window_end}: {e}")
                result['errors'].append(f"Window {window_start}-{window_end}: {e}")
        
        # Combine all collected data
        if all_data:
            result['data'] = pd.concat(all_data, ignore_index=False).sort_index()
            result['status'] = 'partial'
            result['metadata']['collection_type'] = 'partial_delisted'
            self.stats['partial_collections'] += 1
        else:
            result['status'] = 'failed'
            result['errors'].append('No data collected from any availability window')
            self.stats['failed_collections'] += 1
        
        self.stats['delisted_symbols'] += 1
        return result
    
    def _handle_suspended_symbol(self,
                               adapter: ExchangeAdapter,
                               symbol: str,
                               timeframe: str,
                               start_time: datetime,
                               end_time: datetime,
                               result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data collection for a suspended symbol."""
        logger.info(f"Handling suspended symbol: {symbol}")
        
        # Try to collect historical data (may work even if currently suspended)
        try:
            data = self._collect_data_with_retry(adapter, symbol, timeframe, start_time, end_time)
            if not data.empty:
                result['data'] = data
                result['status'] = 'success'
                result['metadata']['collection_type'] = 'suspended_historical'
                self.stats['successful_collections'] += 1
            else:
                result['status'] = 'failed'
                result['errors'].append('No historical data available for suspended symbol')
                self.stats['failed_collections'] += 1
        except Exception as e:
            logger.warning(f"Failed to collect historical data for suspended symbol {symbol}: {e}")
            result['status'] = 'failed'
            result['errors'].append(f'Historical data collection failed: {e}')
            self.stats['failed_collections'] += 1
        
        self.stats['suspended_symbols'] += 1
        return result
    
    def _handle_active_symbol(self,
                            adapter: ExchangeAdapter,
                            symbol: str,
                            timeframe: str,
                            start_time: datetime,
                            end_time: datetime,
                            result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data collection for an active symbol."""
        logger.debug(f"Handling active symbol: {symbol}")
        
        try:
            data = self._collect_data_with_retry(adapter, symbol, timeframe, start_time, end_time)
            if not data.empty:
                result['data'] = data
                result['status'] = 'success'
                result['metadata']['collection_type'] = 'active_full'
                self.stats['successful_collections'] += 1
            else:
                result['status'] = 'failed'
                result['errors'].append('No data returned for active symbol')
                self.stats['failed_collections'] += 1
        except Exception as e:
            logger.error(f"Failed to collect data for active symbol {symbol}: {e}")
            result['status'] = 'failed'
            result['errors'].append(f'Data collection failed: {e}')
            self.stats['failed_collections'] += 1
        
        return result
    
    def _handle_unknown_symbol(self,
                             adapter: ExchangeAdapter,
                             symbol: str,
                             timeframe: str,
                             start_time: datetime,
                             end_time: datetime,
                             result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data collection for a symbol with unknown status."""
        logger.warning(f"Handling symbol with unknown status: {symbol}")
        
        # Try to collect data anyway - this will help determine the actual status
        try:
            data = self._collect_data_with_retry(adapter, symbol, timeframe, start_time, end_time)
            if not data.empty:
                result['data'] = data
                result['status'] = 'success'
                result['metadata']['collection_type'] = 'unknown_successful'
                self.stats['successful_collections'] += 1
                
                # Update symbol status to active since collection was successful
                self.lifecycle_manager.mark_symbol_delisted(
                    symbol=symbol,
                    exchange=adapter.exchange_id,
                    delisting_time=datetime.now(),
                    reason="Collection successful - symbol appears active",
                    market_type=getattr(adapter, 'market_type', 'spot')
                )
            else:
                result['status'] = 'failed'
                result['errors'].append('No data returned for unknown symbol')
                self.stats['failed_collections'] += 1
        except Exception as e:
            logger.error(f"Failed to collect data for unknown symbol {symbol}: {e}")
            result['status'] = 'failed'
            result['errors'].append(f'Data collection failed: {e}')
            self.stats['failed_collections'] += 1
        
        return result
    
    def _collect_data_window(self,
                           adapter: ExchangeAdapter,
                           symbol: str,
                           timeframe: str,
                           start_time: datetime,
                           end_time: datetime) -> pd.DataFrame:
        """Collect data for a specific time window."""
        return self._collect_data_with_retry(adapter, symbol, timeframe, start_time, end_time)
    
    def _collect_data_with_retry(self,
                               adapter: ExchangeAdapter,
                               symbol: str,
                               timeframe: str,
                               start_time: datetime,
                               end_time: datetime) -> pd.DataFrame:
        """Collect data with retry logic and enhanced error handling."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Collecting data for {symbol} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Use adapter's get_ohlcv method
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
                logger.warning(f"Symbol {symbol} not found: {e}")
                # Mark as delisted
                self.lifecycle_manager.mark_symbol_delisted(
                    symbol=symbol,
                    exchange=adapter.exchange_id,
                    delisting_time=datetime.now(),
                    reason=f"BadSymbol error: {e}",
                    market_type=getattr(adapter, 'market_type', 'spot')
                )
                raise
                
            except ccxt.MarketClosed as e:
                logger.warning(f"Market closed for {symbol}: {e}")
                # This might be temporary, so retry
                last_exception = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise
                    
            except ccxt.ExchangeNotAvailable as e:
                logger.warning(f"Exchange not available for {symbol}: {e}")
                # This might be temporary, so retry
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
                               end_time: Union[datetime, str],
                               fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Collect data for multiple symbols with delisting awareness.
        
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
        fields : Optional[List[str]]
            Data fields to collect
            
        Returns
        -------
        Dict[str, Any]
            Collection results for all symbols
        """
        logger.info(f"Collecting data for {len(symbols)} symbols from {start_time} to {end_time}")
        
        # Reset stats for this batch
        self.stats = {
            'total_symbols': 0,
            'successful_collections': 0,
            'partial_collections': 0,
            'failed_collections': 0,
            'delisted_symbols': 0,
            'suspended_symbols': 0,
            'collection_windows': []
        }
        
        results = {}
        
        for symbol in symbols:
            logger.info(f"Collecting data for {symbol}")
            
            try:
                result = self.collect_symbol_data(
                    adapter=adapter,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=end_time,
                    fields=fields
                )
                results[symbol] = result
                
                # Log result
                if result['status'] == 'success':
                    logger.info(f"✅ Successfully collected {len(result['data'])} records for {symbol}")
                elif result['status'] == 'partial':
                    logger.info(f"⚠️ Partially collected {len(result['data'])} records for {symbol}")
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
                self.stats['failed_collections'] += 1
        
        # Summary statistics
        batch_stats = self.stats.copy()
        batch_stats['success_rate'] = (batch_stats['successful_collections'] / batch_stats['total_symbols']) * 100 if batch_stats['total_symbols'] > 0 else 0
        batch_stats['partial_rate'] = (batch_stats['partial_collections'] / batch_stats['total_symbols']) * 100 if batch_stats['total_symbols'] > 0 else 0
        
        logger.info(f"Batch collection completed: {batch_stats['successful_collections']} successful, "
                   f"{batch_stats['partial_collections']} partial, {batch_stats['failed_collections']} failed")
        
        return {
            'results': results,
            'stats': batch_stats,
            'summary': {
                'total_symbols': len(symbols),
                'successful_symbols': [s for s, r in results.items() if r['status'] == 'success'],
                'partial_symbols': [s for s, r in results.items() if r['status'] == 'partial'],
                'failed_symbols': [s for s, r in results.items() if r['status'] in ['failed', 'error']],
                'delisted_symbols': [s for s, r in results.items() if 'delisted' in r.get('metadata', {}).get('collection_type', '')],
                'suspended_symbols': [s for s, r in results.items() if 'suspended' in r.get('metadata', {}).get('collection_type', '')]
            }
        }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset collection statistics."""
        self.stats = {
            'total_symbols': 0,
            'successful_collections': 0,
            'partial_collections': 0,
            'failed_collections': 0,
            'delisted_symbols': 0,
            'suspended_symbols': 0,
            'collection_windows': []
        }