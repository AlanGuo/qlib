# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Incremental update manager for cryptocurrency data collection.

This module provides the main interface for managing incremental data updates,
coordinating state management, update strategies, and conflict resolution.
"""

import asyncio
import sys
from pathlib import Path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
import logging
import pandas as pd

from .update_state import GlobalUpdateState, ExchangeUpdateState, SymbolUpdateState, UpdateStatus
from .state_storage import StateStorage, FileStateStorage
from .update_strategy import UpdateStrategy, TimeBasedStrategy, PriorityUpdatePlanner, UpdateDecision
from .conflict_resolver import ConflictResolver, DefaultConflictResolver, ConflictResolutionStrategy
from ..config.main_config import CryptoDataConfig
from ..symbol_lifecycle import SymbolLifecycleManager, SymbolStatus
from ..delisting_aware_collector import DelistingAwareCollector


class IncrementalUpdateError(Exception):
    """Base exception for incremental update errors."""
    pass


class IncrementalUpdateManager:
    """Main manager for incremental data updates."""
    
    def __init__(self,
                 config: CryptoDataConfig,
                 lifecycle_manager: Optional[SymbolLifecycleManager] = None,
                 delisting_collector: Optional[DelistingAwareCollector] = None,
                 state_storage: Optional[StateStorage] = None,
                 update_strategy: Optional[UpdateStrategy] = None,
                 conflict_resolver: Optional[ConflictResolver] = None):
        """
        Initialize incremental update manager with delisting awareness.
        
        Args:
            config: Crypto data configuration
            lifecycle_manager: Symbol lifecycle manager for delisting detection
            delisting_collector: Delisting-aware data collector
            state_storage: State storage implementation
            update_strategy: Update strategy implementation
            conflict_resolver: Conflict resolver implementation
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize delisting-aware components
        self.lifecycle_manager = lifecycle_manager or self._create_default_lifecycle_manager()
        self.delisting_collector = delisting_collector or self._create_default_delisting_collector()
        
        # Initialize components
        self.state_storage = state_storage or self._create_default_state_storage()
        self.update_strategy = update_strategy or self._create_default_update_strategy()
        self.conflict_resolver = conflict_resolver or self._create_default_conflict_resolver()
        self.update_planner = PriorityUpdatePlanner(
            max_concurrent_updates=config.incremental.get('max_concurrent_updates', 10)
        )
        
        # State management
        self.global_state: Optional[GlobalUpdateState] = None
        self.exchange_adapters: Dict[str, ExchangeAdapter] = {}
        
        # Statistics
        self.update_stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'partial_updates': 0,
            'delisted_symbols_skipped': 0,
            'suspended_symbols_retried': 0,
            'data_points_collected': 0,
            'conflicts_resolved': 0
        }
    
    def _create_default_lifecycle_manager(self) -> SymbolLifecycleManager:
        """Create default symbol lifecycle manager."""
        lifecycle_dir = Path(self.config.data_dir) / "symbol_lifecycle"
        return SymbolLifecycleManager(
            storage_dir=str(lifecycle_dir),
            cache_ttl=self.config.incremental.get('symbol_cache_ttl', 3600),
            enable_persistence=True
        )
    
    def _create_default_delisting_collector(self) -> DelistingAwareCollector:
        """Create default delisting-aware collector."""
        return DelistingAwareCollector(
            lifecycle_manager=self.lifecycle_manager,
            max_retries=self.config.incremental.get('max_retries', 3),
            retry_delay=self.config.incremental.get('retry_delay', 1.0),
            enable_partial_collection=self.config.incremental.get('enable_partial_collection', True)
        )
    
    def _create_default_state_storage(self) -> StateStorage:
        """Create default state storage."""
        state_dir = Path(self.config.data_dir) / "incremental_state"
        return FileStateStorage(
            state_file=str(state_dir / "update_state.json"),
            backup_dir=str(state_dir / "backups"),
            max_backups=self.config.incremental.get('max_backups', 10),
            auto_backup=self.config.incremental.get('auto_backup', True)
        )
    
    def _create_default_update_strategy(self) -> UpdateStrategy:
        """Create default update strategy."""
        # Get update intervals from config
        update_intervals = self.config.incremental.get('update_intervals', {
            '1m': 5,    # Update every 5 minutes
            '5m': 15,   # Update every 15 minutes
            '15m': 30,  # Update every 30 minutes
            '30m': 60,  # Update every hour
            '1h': 120,  # Update every 2 hours
            '4h': 480,  # Update every 8 hours
            '1d': 1440, # Update every day
            '1w': 10080 # Update every week
        })
        
        return TimeBasedStrategy(
            update_intervals=update_intervals,
            max_age_hours=self.config.incremental.get('max_age_hours', 24),
            force_update_after_failures=self.config.incremental.get('max_consecutive_failures', 3)
        )
    
    def _create_default_conflict_resolver(self) -> ConflictResolver:
        """Create default conflict resolver."""
        strategy_name = self.config.incremental.get('conflict_resolution', 'keep_latest')
        strategy = ConflictResolutionStrategy(strategy_name)
        return DefaultConflictResolver(strategy)
    
    async def initialize(self) -> None:
        """Initialize the update manager."""
        try:
            # Load existing state
            self.global_state = self.state_storage.load_state()
            
            if self.global_state is None:
                self.logger.info("No existing state found, creating new state")
                self.global_state = GlobalUpdateState()
                self.state_storage.save_state(self.global_state)
            else:
                self.logger.info(f"Loaded existing state with {len(self.global_state.exchanges)} exchanges")
            
            # Initialize exchange adapters
            await self._initialize_exchange_adapters()
            
            self.logger.info("Incremental update manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize update manager: {str(e)}")
            raise IncrementalUpdateError(f"Initialization failed: {str(e)}")
    
    async def _initialize_exchange_adapters(self) -> None:
        """Initialize exchange adapters."""
        # This would be implemented to create exchange adapters
        # For now, we'll assume they're provided externally
        pass
    
    def register_exchange_adapter(self, exchange: str, adapter: ExchangeAdapter) -> None:
        """Register an exchange adapter."""
        self.exchange_adapters[exchange] = adapter
        self.logger.info(f"Registered adapter for exchange: {exchange}")
    
    async def plan_updates(self, 
                          exchanges: Optional[List[str]] = None,
                          symbols: Optional[List[str]] = None,
                          timeframes: Optional[List[str]] = None) -> List[Tuple[SymbolUpdateState, UpdateDecision]]:
        """
        Plan updates for specified criteria with delisting awareness.
        
        Args:
            exchanges: List of exchanges to update (None for all)
            symbols: List of symbols to update (None for all)
            timeframes: List of timeframes to update (None for all)
            
        Returns:
            List of (symbol_state, update_decision) tuples
        """
        if not self.global_state:
            raise IncrementalUpdateError("Manager not initialized")
        
        # Get all symbol states that match criteria
        symbol_states = self._get_matching_symbol_states(exchanges, symbols, timeframes)
        
        # Filter out permanently delisted symbols
        active_symbol_states = []
        for symbol_state in symbol_states:
            try:
                # Check symbol lifecycle status
                status_record = self.lifecycle_manager.get_symbol_status(
                    symbol=symbol_state.symbol,
                    exchange=symbol_state.exchange,
                    market_type=getattr(symbol_state, 'market_type', 'spot')
                )
                
                if status_record.status == SymbolStatus.DELISTED:
                    self.logger.info(f"Skipping delisted symbol: {symbol_state.symbol} on {symbol_state.exchange}")
                    self.update_stats['delisted_symbols_skipped'] += 1
                    # Mark symbol state as permanently failed to avoid future planning
                    symbol_state.mark_permanently_failed("Symbol is delisted")
                    continue
                
                elif status_record.status == SymbolStatus.SUSPENDED:
                    self.logger.warning(f"Symbol {symbol_state.symbol} on {symbol_state.exchange} is suspended, will retry")
                    self.update_stats['suspended_symbols_retried'] += 1
                    # Continue with planning - suspended symbols might come back
                
                # Symbol is active or suspended - include in planning
                active_symbol_states.append(symbol_state)
                
            except Exception as e:
                self.logger.warning(f"Failed to check lifecycle status for {symbol_state.symbol}: {e}")
                # If we can't check status, include the symbol anyway
                active_symbol_states.append(symbol_state)
        
        # Plan updates using strategy
        update_plans = self.update_planner.plan_updates(active_symbol_states, self.update_strategy)
        
        self.logger.info(f"Planned {len(update_plans)} updates out of {len(symbol_states)} symbols "
                        f"({len(symbol_states) - len(active_symbol_states)} delisted/skipped)")
        
        return update_plans
    
    def _get_matching_symbol_states(self,
                                   exchanges: Optional[List[str]] = None,
                                   symbols: Optional[List[str]] = None,
                                   timeframes: Optional[List[str]] = None) -> List[SymbolUpdateState]:
        """Get symbol states matching the specified criteria."""
        matching_states = []
        
        for exchange_name, exchange_state in self.global_state.exchanges.items():
            # Filter by exchange
            if exchanges and exchange_name not in exchanges:
                continue
            
            for symbol, timeframe_dict in exchange_state.symbols.items():
                # Filter by symbol
                if symbols and symbol not in symbols:
                    continue
                
                for timeframe, symbol_state in timeframe_dict.items():
                    # Filter by timeframe
                    if timeframes and timeframe not in timeframes:
                        continue
                    
                    matching_states.append(symbol_state)
        
        return matching_states
    
    async def execute_updates(self, 
                            update_plans: List[Tuple[SymbolUpdateState, UpdateDecision]],
                            dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute planned updates.
        
        Args:
            update_plans: List of (symbol_state, update_decision) tuples
            dry_run: If True, don't actually collect data
            
        Returns:
            Dictionary with execution results
        """
        if not update_plans:
            return {'message': 'No updates to execute', 'results': []}
        
        self.logger.info(f"Executing {len(update_plans)} updates (dry_run={dry_run})")
        
        results = []
        successful_updates = 0
        failed_updates = 0
        
        # Execute updates (could be parallelized)
        for symbol_state, update_decision in update_plans:
            try:
                result = await self._execute_single_update_with_delisting_awareness(
                    symbol_state, update_decision, dry_run
                )
                results.append(result)
                
                if result['success']:
                    successful_updates += 1
                elif result.get('partial', False):
                    successful_updates += 1  # Count partial as success for stats
                    self.update_stats['partial_updates'] += 1
                else:
                    failed_updates += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to update {symbol_state.symbol}: {str(e)}")
                results.append({
                    'symbol': symbol_state.symbol,
                    'exchange': symbol_state.exchange,
                    'timeframe': symbol_state.timeframe,
                    'success': False,
                    'error': str(e),
                    'data_points': 0
                })
                failed_updates += 1
        
        # Update statistics
        self.update_stats['total_updates'] += len(update_plans)
        self.update_stats['successful_updates'] += successful_updates
        self.update_stats['failed_updates'] += failed_updates
        
        # Save state if not dry run
        if not dry_run and self.global_state:
            self.state_storage.save_state(self.global_state)
        
        return {
            'total_planned': len(update_plans),
            'successful': successful_updates,
            'failed': failed_updates,
            'results': results,
            'dry_run': dry_run
        }
    
    async def _execute_single_update_with_delisting_awareness(self, 
                                                           symbol_state: SymbolUpdateState,
                                                           update_decision: UpdateDecision,
                                                           dry_run: bool) -> Dict[str, Any]:
        """Execute a single update with delisting awareness."""
        
        # Mark update start
        symbol_state.mark_update_start()
        
        if dry_run:
            # Simulate update
            await asyncio.sleep(0.1)  # Simulate work
            symbol_state.mark_update_success(
                data_timestamp=datetime.now(timezone.utc),
                data_points=update_decision.estimated_data_points
            )
            
            return {
                'symbol': symbol_state.symbol,
                'exchange': symbol_state.exchange,
                'timeframe': symbol_state.timeframe,
                'success': True,
                'data_points': update_decision.estimated_data_points,
                'dry_run': True,
                'reason': update_decision.reason
            }
        
        # Get exchange adapter
        adapter = self.exchange_adapters.get(symbol_state.exchange)
        if not adapter:
            error_msg = f"No adapter found for exchange {symbol_state.exchange}"
            symbol_state.mark_update_failure(error_msg)
            return {
                'symbol': symbol_state.symbol,
                'exchange': symbol_state.exchange,
                'timeframe': symbol_state.timeframe,
                'success': False,
                'error': error_msg,
                'data_points': 0
            }
        
        try:
            # Get update timeframe
            start_time, end_time = self.update_strategy.get_update_timeframe(symbol_state)
            
            # Use delisting-aware collector for data collection
            collection_result = self.delisting_collector.collect_symbol_data(
                adapter=adapter,
                symbol=symbol_state.symbol,
                timeframe=symbol_state.timeframe,
                start_time=start_time,
                end_time=end_time
            )
            
            # Process collection result
            if collection_result['status'] == 'success':
                # Full success
                data_points = len(collection_result['data'])
                last_timestamp = collection_result['data'].index.max() if data_points > 0 else None
                
                # Handle conflicts if there's existing data
                final_data = await self._handle_data_conflicts(symbol_state, collection_result['data'])
                
                symbol_state.mark_update_success(
                    data_timestamp=last_timestamp,
                    data_points=data_points
                )
                
                self.update_stats['data_points_collected'] += data_points
                
                return {
                    'symbol': symbol_state.symbol,
                    'exchange': symbol_state.exchange,
                    'timeframe': symbol_state.timeframe,
                    'success': True,
                    'data_points': data_points,
                    'start_time': start_time,
                    'end_time': end_time,
                    'reason': update_decision.reason,
                    'collection_type': collection_result.get('metadata', {}).get('collection_type', 'unknown')
                }
                
            elif collection_result['status'] == 'partial':
                # Partial success (symbol was delisted mid-period)
                data_points = len(collection_result['data'])
                last_timestamp = collection_result['data'].index.max() if data_points > 0 else None
                
                # Handle conflicts if there's existing data
                final_data = await self._handle_data_conflicts(symbol_state, collection_result['data'])
                
                symbol_state.mark_update_success(
                    data_timestamp=last_timestamp,
                    data_points=data_points
                )
                
                self.update_stats['data_points_collected'] += data_points
                
                return {
                    'symbol': symbol_state.symbol,
                    'exchange': symbol_state.exchange,
                    'timeframe': symbol_state.timeframe,
                    'success': True,
                    'partial': True,
                    'data_points': data_points,
                    'start_time': start_time,
                    'end_time': end_time,
                    'reason': update_decision.reason,
                    'collection_type': collection_result.get('metadata', {}).get('collection_type', 'unknown'),
                    'collection_windows': collection_result.get('collection_windows', []),
                    'delisting_events': collection_result.get('delisting_events', [])
                }
                
            else:
                # Failed collection
                error_msg = f"Collection failed: {collection_result.get('errors', [])}"
                symbol_state.mark_update_failure(error_msg)
                
                return {
                    'symbol': symbol_state.symbol,
                    'exchange': symbol_state.exchange,
                    'timeframe': symbol_state.timeframe,
                    'success': False,
                    'error': error_msg,
                    'data_points': 0,
                    'collection_errors': collection_result.get('errors', [])
                }
            
        except Exception as e:
            error_msg = f"Update execution failed: {str(e)}"
            symbol_state.mark_update_failure(error_msg)
            
            return {
                'symbol': symbol_state.symbol,
                'exchange': symbol_state.exchange,
                'timeframe': symbol_state.timeframe,
                'success': False,
                'error': error_msg,
                'data_points': 0
            }
    
    async def _execute_single_update(self, 
                                   symbol_state: SymbolUpdateState,
                                   update_decision: UpdateDecision,
                                   dry_run: bool) -> Dict[str, Any]:
        """Execute a single update (legacy method for backward compatibility)."""
        return await self._execute_single_update_with_delisting_awareness(
            symbol_state, update_decision, dry_run
        )
    
    async def _collect_data(self, 
                          adapter: ExchangeAdapter,
                          symbol_state: SymbolUpdateState,
                          start_time: Optional[datetime],
                          end_time: Optional[datetime]) -> pd.DataFrame:
        """Collect data from exchange adapter."""
        # This would call the actual adapter method
        # For now, return empty DataFrame
        return pd.DataFrame()
    
    async def _handle_data_conflicts(self, 
                                   symbol_state: SymbolUpdateState,
                                   new_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Handle conflicts between existing and new data."""
        # This would load existing data and resolve conflicts
        # For now, just return new data
        return new_data
    
    def get_update_statistics(self) -> Dict[str, Any]:
        """Get update statistics."""
        if not self.global_state:
            return {'error': 'Manager not initialized'}
        
        overall_stats = self.global_state.get_overall_statistics()
        overall_stats.update(self.update_stats)
        
        return overall_stats
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state."""
        if not self.global_state:
            return {'error': 'Manager not initialized'}
        
        summary = {
            'exchanges': {},
            'total_symbols': 0,
            'stale_symbols': 0,
            'failed_symbols': 0,
            'last_updated': self.global_state.updated_at
        }
        
        for exchange_name, exchange_state in self.global_state.exchanges.items():
            all_states = exchange_state.get_all_symbol_states()
            stale_states = exchange_state.get_stale_symbols()
            failed_states = exchange_state.get_failed_symbols()
            
            summary['exchanges'][exchange_name] = {
                'total_symbols': len(all_states),
                'stale_symbols': len(stale_states),
                'failed_symbols': len(failed_states),
                'enabled': exchange_state.enabled,
                'last_full_update': exchange_state.last_full_update
            }
            
            summary['total_symbols'] += len(all_states)
            summary['stale_symbols'] += len(stale_states)
            summary['failed_symbols'] += len(failed_states)
        
        return summary
