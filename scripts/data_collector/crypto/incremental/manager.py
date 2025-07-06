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


class IncrementalUpdateError(Exception):
    """Base exception for incremental update errors."""
    pass


class IncrementalUpdateManager:
    """Main manager for incremental data updates."""
    
    def __init__(self,
                 config: CryptoDataConfig,
                 state_storage: Optional[StateStorage] = None,
                 update_strategy: Optional[UpdateStrategy] = None,
                 conflict_resolver: Optional[ConflictResolver] = None):
        """
        Initialize incremental update manager.
        
        Args:
            config: Crypto data configuration
            state_storage: State storage implementation
            update_strategy: Update strategy implementation
            conflict_resolver: Conflict resolver implementation
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
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
            'data_points_collected': 0,
            'conflicts_resolved': 0
        }
    
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
        Plan updates for specified criteria.
        
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
        
        # Plan updates using strategy
        update_plans = self.update_planner.plan_updates(symbol_states, self.update_strategy)
        
        self.logger.info(f"Planned {len(update_plans)} updates out of {len(symbol_states)} symbols")
        
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
                result = await self._execute_single_update(symbol_state, update_decision, dry_run)
                results.append(result)
                
                if result['success']:
                    successful_updates += 1
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
    
    async def _execute_single_update(self, 
                                   symbol_state: SymbolUpdateState,
                                   update_decision: UpdateDecision,
                                   dry_run: bool) -> Dict[str, Any]:
        """Execute a single update."""
        
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
            
            # Collect new data
            new_data = await self._collect_data(adapter, symbol_state, start_time, end_time)
            
            # Handle conflicts if there's existing data
            final_data = await self._handle_data_conflicts(symbol_state, new_data)
            
            # Update state
            data_points = len(final_data) if final_data is not None else 0
            last_timestamp = final_data.index.max() if data_points > 0 else None
            
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
                'reason': update_decision.reason
            }
            
        except Exception as e:
            error_msg = f"Data collection failed: {str(e)}"
            symbol_state.mark_update_failure(error_msg)
            
            return {
                'symbol': symbol_state.symbol,
                'exchange': symbol_state.exchange,
                'timeframe': symbol_state.timeframe,
                'success': False,
                'error': error_msg,
                'data_points': 0
            }
    
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
