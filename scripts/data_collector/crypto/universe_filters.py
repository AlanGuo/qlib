# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Universe filters for cryptocurrency investment universe management.

This module provides filtering functionality to select trading symbols
based on various criteria such as volume, market cap, volatility, etc.
"""

import re
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import pandas as pd
from loguru import logger

from symbol_discovery import SymbolInfo
from config.universe_config import FilterConfig


class BaseFilter(ABC):
    """Base class for universe filters."""
    
    @abstractmethod
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        """
        Apply the filter to a list of symbols.
        
        Parameters
        ----------
        symbols : List[SymbolInfo]
            List of symbols to filter
            
        Returns
        -------
        List[SymbolInfo]
            Filtered list of symbols
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of what this filter does."""
        pass


class VolumeFilter(BaseFilter):
    """Filter symbols by trading volume."""
    
    def __init__(self, 
                 min_volume_24h: Optional[float] = None,
                 max_volume_24h: Optional[float] = None,
                 min_volume_usd_24h: Optional[float] = None):
        self.min_volume_24h = min_volume_24h
        self.max_volume_24h = max_volume_24h
        self.min_volume_usd_24h = min_volume_usd_24h
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        filtered = []
        
        for symbol in symbols:
            # Check volume_24h filter
            if self.min_volume_24h is not None:
                if symbol.volume_24h is None or symbol.volume_24h < self.min_volume_24h:
                    continue
            
            if self.max_volume_24h is not None:
                if symbol.volume_24h is None or symbol.volume_24h > self.max_volume_24h:
                    continue
            
            # Check USD volume filter
            if self.min_volume_usd_24h is not None:
                if symbol.volume_usd_24h is None or symbol.volume_usd_24h < self.min_volume_usd_24h:
                    continue
            
            filtered.append(symbol)
        
        return filtered
    
    def get_description(self) -> str:
        conditions = []
        if self.min_volume_24h:
            conditions.append(f"volume_24h >= {self.min_volume_24h}")
        if self.max_volume_24h:
            conditions.append(f"volume_24h <= {self.max_volume_24h}")
        if self.min_volume_usd_24h:
            conditions.append(f"volume_usd_24h >= {self.min_volume_usd_24h}")
        
        return f"Volume filter: {' AND '.join(conditions)}"


class PriceFilter(BaseFilter):
    """Filter symbols by price range."""
    
    def __init__(self, 
                 min_price: Optional[float] = None,
                 max_price: Optional[float] = None):
        self.min_price = min_price
        self.max_price = max_price
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        filtered = []
        
        for symbol in symbols:
            if self.min_price is not None:
                if symbol.price is None or symbol.price < self.min_price:
                    continue
            
            if self.max_price is not None:
                if symbol.price is None or symbol.price > self.max_price:
                    continue
            
            filtered.append(symbol)
        
        return filtered
    
    def get_description(self) -> str:
        conditions = []
        if self.min_price:
            conditions.append(f"price >= {self.min_price}")
        if self.max_price:
            conditions.append(f"price <= {self.max_price}")
        
        return f"Price filter: {' AND '.join(conditions)}"


class ChangeFilter(BaseFilter):
    """Filter symbols by 24h price change."""
    
    def __init__(self, 
                 min_change_24h: Optional[float] = None,
                 max_change_24h: Optional[float] = None):
        self.min_change_24h = min_change_24h
        self.max_change_24h = max_change_24h
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        filtered = []
        
        for symbol in symbols:
            if self.min_change_24h is not None:
                if symbol.change_24h is None or abs(symbol.change_24h) < self.min_change_24h:
                    continue
            
            if self.max_change_24h is not None:
                if symbol.change_24h is None or abs(symbol.change_24h) > self.max_change_24h:
                    continue
            
            filtered.append(symbol)
        
        return filtered
    
    def get_description(self) -> str:
        conditions = []
        if self.min_change_24h:
            conditions.append(f"|change_24h| >= {self.min_change_24h}%")
        if self.max_change_24h:
            conditions.append(f"|change_24h| <= {self.max_change_24h}%")
        
        return f"Change filter: {' AND '.join(conditions)}"


class AssetFilter(BaseFilter):
    """Filter symbols by base/quote assets."""
    
    def __init__(self,
                 base_assets: Optional[List[str]] = None,
                 quote_assets: Optional[List[str]] = None,
                 exclude_base_assets: Optional[List[str]] = None,
                 exclude_quote_assets: Optional[List[str]] = None):
        self.base_assets = [asset.upper() for asset in base_assets] if base_assets else None
        self.quote_assets = [asset.upper() for asset in quote_assets] if quote_assets else None
        self.exclude_base_assets = [asset.upper() for asset in exclude_base_assets] if exclude_base_assets else None
        self.exclude_quote_assets = [asset.upper() for asset in exclude_quote_assets] if exclude_quote_assets else None
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        filtered = []
        
        for symbol in symbols:
            base = symbol.base.upper() if symbol.base else ""
            quote = symbol.quote.upper() if symbol.quote else ""
            
            # Check inclusion filters
            if self.base_assets and base not in self.base_assets:
                continue
            
            if self.quote_assets and quote not in self.quote_assets:
                continue
            
            # Check exclusion filters
            if self.exclude_base_assets and base in self.exclude_base_assets:
                continue
            
            if self.exclude_quote_assets and quote in self.exclude_quote_assets:
                continue
            
            filtered.append(symbol)
        
        return filtered
    
    def get_description(self) -> str:
        conditions = []
        if self.base_assets:
            conditions.append(f"base in {self.base_assets}")
        if self.quote_assets:
            conditions.append(f"quote in {self.quote_assets}")
        if self.exclude_base_assets:
            conditions.append(f"base not in {self.exclude_base_assets}")
        if self.exclude_quote_assets:
            conditions.append(f"quote not in {self.exclude_quote_assets}")
        
        return f"Asset filter: {' AND '.join(conditions)}"


class MarketTypeFilter(BaseFilter):
    """Filter symbols by market type."""
    
    def __init__(self, market_types: List[str]):
        self.market_types = [mt.lower() for mt in market_types]
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        return [s for s in symbols if s.market_type.lower() in self.market_types]
    
    def get_description(self) -> str:
        return f"Market type filter: market_type in {self.market_types}"


class ActiveFilter(BaseFilter):
    """Filter to include only active symbols."""
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        return [s for s in symbols if s.active]
    
    def get_description(self) -> str:
        return "Active filter: active == True"


class ExchangeFilter(BaseFilter):
    """Filter symbols by exchange."""
    
    def __init__(self, exchanges: List[str]):
        self.exchanges = [ex.lower() for ex in exchanges]
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        return [s for s in symbols if s.exchange.lower() in self.exchanges]
    
    def get_description(self) -> str:
        return f"Exchange filter: exchange in {self.exchanges}"


class CustomFilter(BaseFilter):
    """Custom filter using a user-defined function."""
    
    def __init__(self, filter_func: Callable[[SymbolInfo], bool], description: str):
        self.filter_func = filter_func
        self.description = description
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        return [s for s in symbols if self.filter_func(s)]
    
    def get_description(self) -> str:
        return f"Custom filter: {self.description}"


class UniverseFilterChain:
    """Chain of filters to apply to symbol universe."""
    
    def __init__(self):
        self.filters: List[BaseFilter] = []
    
    def add_filter(self, filter_obj: BaseFilter) -> 'UniverseFilterChain':
        """Add a filter to the chain."""
        self.filters.append(filter_obj)
        return self
    
    def apply(self, symbols: List[SymbolInfo]) -> List[SymbolInfo]:
        """Apply all filters in sequence."""
        result = symbols.copy()
        
        for filter_obj in self.filters:
            initial_count = len(result)
            result = filter_obj.apply(result)
            final_count = len(result)
            
            logger.debug(f"{filter_obj.get_description()}: {initial_count} -> {final_count} symbols")
        
        return result
    
    def get_description(self) -> str:
        """Get description of all filters in the chain."""
        if not self.filters:
            return "No filters applied"
        
        descriptions = [f.get_description() for f in self.filters]
        return " -> ".join(descriptions)


def create_filter_chain_from_config(config: FilterConfig) -> UniverseFilterChain:
    """
    Create a filter chain from a FilterConfig.
    
    Parameters
    ----------
    config : FilterConfig
        Filter configuration
        
    Returns
    -------
    UniverseFilterChain
        Configured filter chain
    """
    chain = UniverseFilterChain()
    
    # Add active filter (always include)
    chain.add_filter(ActiveFilter())
    
    # Add volume filter
    if (config.min_volume_24h is not None or 
        config.max_volume_24h is not None or 
        config.min_volume_usd_24h is not None):
        chain.add_filter(VolumeFilter(
            min_volume_24h=config.min_volume_24h,
            max_volume_24h=config.max_volume_24h,
            min_volume_usd_24h=config.min_volume_usd_24h
        ))
    
    # Add price filter
    if config.min_price is not None or config.max_price is not None:
        chain.add_filter(PriceFilter(
            min_price=config.min_price,
            max_price=config.max_price
        ))
    
    # Add change filter
    if config.min_change_24h is not None or config.max_change_24h is not None:
        chain.add_filter(ChangeFilter(
            min_change_24h=config.min_change_24h,
            max_change_24h=config.max_change_24h
        ))
    
    # Add asset filter
    if (config.base_assets or config.quote_assets or 
        config.exclude_base_assets or config.exclude_quote_assets):
        chain.add_filter(AssetFilter(
            base_assets=config.base_assets,
            quote_assets=config.quote_assets,
            exclude_base_assets=config.exclude_base_assets,
            exclude_quote_assets=config.exclude_quote_assets
        ))
    
    # Add market type filter
    if config.market_types:
        chain.add_filter(MarketTypeFilter(config.market_types))
    
    return chain
