# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Universe manager for cryptocurrency investment universe management.

This module provides the main UniverseManager class that coordinates
symbol discovery, filtering, ranking, and universe maintenance.
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from loguru import logger

from exchange_adapters.base_adapter import ExchangeAdapter
from symbol_discovery import SymbolDiscovery, SymbolInfo
from universe_filters import UniverseFilterChain, create_filter_chain_from_config
from config.universe_config import UniverseConfig, FilterConfig


class UniverseManager:
    """
    Main manager for cryptocurrency investment universes.
    
    This class coordinates symbol discovery, filtering, ranking, and
    universe maintenance across multiple exchanges and market types.
    """
    
    def __init__(self, 
                 adapters: Dict[str, ExchangeAdapter],
                 storage_path: str = "./universe_data"):
        """
        Initialize universe manager.
        
        Parameters
        ----------
        adapters : Dict[str, ExchangeAdapter]
            Dictionary of exchange adapters keyed by exchange name
        storage_path : str, default "./universe_data"
            Path to store universe data and history
        """
        self.adapters = adapters
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.discovery = SymbolDiscovery(adapters)
        self._universes: Dict[str, Dict[str, Any]] = {}
        self._universe_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Load existing universes
        self._load_universes()
    
    def create_universe(self, 
                       config: UniverseConfig,
                       force_refresh: bool = False) -> List[SymbolInfo]:
        """
        Create or update a universe based on configuration.
        
        Parameters
        ----------
        config : UniverseConfig
            Universe configuration
        force_refresh : bool, default False
            Whether to force refresh symbol discovery
            
        Returns
        -------
        List[SymbolInfo]
            List of symbols in the universe
        """
        logger.info(f"Creating universe: {config.name}")
        
        # Discover symbols
        logger.info(f"Discovering symbols on exchanges: {config.exchanges}")
        exchange_symbols = self.discovery.discover_symbols(
            exchanges=config.exchanges,
            market_types=config.market_types,
            force_refresh=force_refresh
        )
        
        # Flatten symbols from all exchanges
        all_symbols = []
        for exchange, symbols in exchange_symbols.items():
            all_symbols.extend(symbols)
        
        logger.info(f"Found {len(all_symbols)} total symbols before filtering")
        
        # Apply filters
        filter_chain = create_filter_chain_from_config(config.filters)
        filtered_symbols = filter_chain.apply(all_symbols)
        
        logger.info(f"After filtering: {len(filtered_symbols)} symbols remain")
        logger.debug(f"Filter chain: {filter_chain.get_description()}")
        
        # Rank and select symbols
        ranked_symbols = self._rank_symbols(filtered_symbols, config)
        
        # Apply size limits
        final_symbols = self._apply_size_limits(ranked_symbols, config)
        
        logger.info(f"Final universe size: {len(final_symbols)} symbols")
        
        # Store universe
        universe_data = {
            'config': config,
            'symbols': final_symbols,
            'created_at': datetime.now(),
            'statistics': self.discovery.get_symbol_statistics(final_symbols)
        }
        
        self._universes[config.name] = universe_data
        self._save_universe(config.name, universe_data)
        
        # Update history
        self._update_universe_history(config.name, final_symbols)
        
        return final_symbols
    
    def get_universe(self, name: str) -> Optional[List[SymbolInfo]]:
        """
        Get symbols from an existing universe.
        
        Parameters
        ----------
        name : str
            Universe name
            
        Returns
        -------
        Optional[List[SymbolInfo]]
            List of symbols or None if universe doesn't exist
        """
        if name in self._universes:
            return self._universes[name]['symbols']
        return None
    
    def get_universe_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get complete information about a universe.
        
        Parameters
        ----------
        name : str
            Universe name
            
        Returns
        -------
        Optional[Dict[str, Any]]
            Universe information or None if doesn't exist
        """
        return self._universes.get(name)
    
    def list_universes(self) -> List[str]:
        """Get list of available universe names."""
        return list(self._universes.keys())
    
    def update_universe(self, name: str, force_refresh: bool = False) -> Optional[List[SymbolInfo]]:
        """
        Update an existing universe.
        
        Parameters
        ----------
        name : str
            Universe name
        force_refresh : bool, default False
            Whether to force refresh symbol discovery
            
        Returns
        -------
        Optional[List[SymbolInfo]]
            Updated list of symbols or None if universe doesn't exist
        """
        if name not in self._universes:
            logger.warning(f"Universe {name} not found")
            return None
        
        config = self._universes[name]['config']
        return self.create_universe(config, force_refresh=force_refresh)
    
    def compare_universes(self, name1: str, name2: str) -> Dict[str, Any]:
        """
        Compare two universes.
        
        Parameters
        ----------
        name1 : str
            First universe name
        name2 : str
            Second universe name
            
        Returns
        -------
        Dict[str, Any]
            Comparison results
        """
        universe1 = self.get_universe(name1)
        universe2 = self.get_universe(name2)
        
        if not universe1 or not universe2:
            return {"error": "One or both universes not found"}
        
        symbols1 = {s.symbol for s in universe1}
        symbols2 = {s.symbol for s in universe2}
        
        return {
            'universe1': name1,
            'universe2': name2,
            'size1': len(symbols1),
            'size2': len(symbols2),
            'common_symbols': list(symbols1 & symbols2),
            'unique_to_1': list(symbols1 - symbols2),
            'unique_to_2': list(symbols2 - symbols1),
            'overlap_ratio': len(symbols1 & symbols2) / len(symbols1 | symbols2) if symbols1 | symbols2 else 0
        }
    
    def get_universe_changes(self, name: str, days: int = 7) -> Dict[str, Any]:
        """
        Get changes in universe over time.
        
        Parameters
        ----------
        name : str
            Universe name
        days : int, default 7
            Number of days to look back
            
        Returns
        -------
        Dict[str, Any]
            Universe changes over time
        """
        if name not in self._universe_history:
            return {"error": "No history found for universe"}
        
        history = self._universe_history[name]
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_history = [
            entry for entry in history
            if datetime.fromisoformat(entry['timestamp']) >= cutoff_date
        ]
        
        if len(recent_history) < 2:
            return {"error": "Insufficient history for comparison"}
        
        # Compare first and last entries
        first_symbols = set(recent_history[0]['symbols'])
        last_symbols = set(recent_history[-1]['symbols'])
        
        return {
            'period_days': days,
            'entries_count': len(recent_history),
            'initial_size': len(first_symbols),
            'final_size': len(last_symbols),
            'added_symbols': list(last_symbols - first_symbols),
            'removed_symbols': list(first_symbols - last_symbols),
            'stability_ratio': len(first_symbols & last_symbols) / len(first_symbols | last_symbols) if first_symbols | last_symbols else 0
        }
    
    def _rank_symbols(self, symbols: List[SymbolInfo], config: UniverseConfig) -> List[SymbolInfo]:
        """Rank symbols according to configuration."""
        if not config.ranking_criteria:
            return symbols
        
        # Convert to DataFrame for easier sorting
        df = pd.DataFrame([s.to_dict() for s in symbols])
        
        # Sort by ranking criteria
        sort_columns = []
        ascending_flags = []
        
        for criterion in config.ranking_criteria:
            if criterion in df.columns:
                sort_columns.append(criterion)
                ascending_flags.append(config.ranking_order == "asc")
        
        if sort_columns:
            df = df.sort_values(
                by=sort_columns,
                ascending=ascending_flags,
                na_position='last'
            )
        
        # Convert back to SymbolInfo objects
        ranked_symbols = []
        for _, row in df.iterrows():
            # Find original symbol object
            for symbol in symbols:
                if symbol.symbol == row['symbol'] and symbol.exchange == row['exchange']:
                    ranked_symbols.append(symbol)
                    break
        
        return ranked_symbols
    
    def _apply_size_limits(self, symbols: List[SymbolInfo], config: UniverseConfig) -> List[SymbolInfo]:
        """Apply size limits to symbol list."""
        result = symbols.copy()
        
        # Apply maximum limit
        if config.max_symbols and len(result) > config.max_symbols:
            result = result[:config.max_symbols]
            logger.info(f"Applied max_symbols limit: {len(symbols)} -> {len(result)}")
        
        # Check minimum limit
        if config.min_symbols and len(result) < config.min_symbols:
            logger.warning(f"Universe size {len(result)} is below minimum {config.min_symbols}")
        
        return result
    
    def _save_universe(self, name: str, universe_data: Dict[str, Any]) -> None:
        """Save universe data to storage."""
        filepath = self.storage_path / f"{name}.json"
        
        # Convert SymbolInfo objects to dicts for JSON serialization
        data_to_save = {
            'config': universe_data['config'].__dict__,
            'symbols': [s.to_dict() for s in universe_data['symbols']],
            'created_at': universe_data['created_at'].isoformat(),
            'statistics': universe_data['statistics']
        }
        
        # Handle nested dataclass in config
        if 'filters' in data_to_save['config']:
            data_to_save['config']['filters'] = universe_data['config'].filters.__dict__
        
        with open(filepath, 'w') as f:
            json.dump(data_to_save, f, indent=2, default=str)
        
        logger.debug(f"Saved universe {name} to {filepath}")
    
    def _load_universes(self) -> None:
        """Load existing universes from storage."""
        if not self.storage_path.exists():
            return
        
        for filepath in self.storage_path.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct universe data
                # Note: This is a simplified reconstruction
                # In practice, you might want more robust deserialization
                name = filepath.stem
                self._universes[name] = {
                    'symbols': [],  # Would need to reconstruct SymbolInfo objects
                    'created_at': datetime.fromisoformat(data['created_at']),
                    'statistics': data.get('statistics', {})
                }
                
                logger.debug(f"Loaded universe {name}")
                
            except Exception as e:
                logger.warning(f"Error loading universe from {filepath}: {e}")
    
    def _update_universe_history(self, name: str, symbols: List[SymbolInfo]) -> None:
        """Update universe history."""
        if name not in self._universe_history:
            self._universe_history[name] = []
        
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'symbols': [s.symbol for s in symbols],
            'size': len(symbols)
        }
        
        self._universe_history[name].append(history_entry)
        
        # Keep only recent history (last 100 entries)
        if len(self._universe_history[name]) > 100:
            self._universe_history[name] = self._universe_history[name][-100:]
        
        # Save history
        history_file = self.storage_path / f"{name}_history.json"
        with open(history_file, 'w') as f:
            json.dump(self._universe_history[name], f, indent=2)
