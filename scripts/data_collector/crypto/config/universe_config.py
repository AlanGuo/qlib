# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Universe configuration for cryptocurrency data collection.

This module defines configuration classes and settings for managing
cryptocurrency investment universes, including filtering criteria,
update schedules, and universe definitions.
"""

from typing import Dict, List, Optional, Any, Union

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json


@dataclass
class FilterConfig:
    """Configuration for universe filtering criteria."""
    
    # Volume filters
    min_volume_24h: Optional[float] = None
    max_volume_24h: Optional[float] = None
    min_volume_usd_24h: Optional[float] = None
    
    # Price filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # Market cap filters (if available)
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    
    # Change filters
    min_change_24h: Optional[float] = None
    max_change_24h: Optional[float] = None
    
    # Listing time filters
    min_listing_days: Optional[int] = None  # Minimum days since listing
    max_listing_days: Optional[int] = None  # Maximum days since listing
    
    # Asset filters
    base_assets: Optional[List[str]] = None  # e.g., ["BTC", "ETH", "BNB"]
    quote_assets: Optional[List[str]] = None  # e.g., ["USDT", "BUSD", "BTC"]
    exclude_base_assets: Optional[List[str]] = None
    exclude_quote_assets: Optional[List[str]] = None
    
    # Market type filters
    market_types: Optional[List[str]] = field(default_factory=lambda: ["spot"])
    
    # Exchange specific filters
    exchange_filters: Optional[Dict[str, Dict[str, Any]]] = None
    
    # Custom filters
    custom_filters: Optional[Dict[str, Any]] = None


@dataclass
class UniverseConfig:
    """Configuration for a cryptocurrency investment universe."""
    
    # Universe identification
    name: str
    description: str = ""
    
    # Exchange configuration
    exchanges: List[str] = field(default_factory=lambda: ["binance"])
    primary_exchange: str = "binance"
    
    # Market types to include
    market_types: List[str] = field(default_factory=lambda: ["spot"])
    
    # Filtering configuration
    filters: FilterConfig = field(default_factory=FilterConfig)
    
    # Update configuration
    update_frequency: str = "daily"  # "hourly", "daily", "weekly"
    update_time: str = "00:00"  # Time to update (HH:MM format)
    
    # Size limits
    max_symbols: Optional[int] = None
    min_symbols: Optional[int] = None
    
    # Ranking criteria for selection when max_symbols is set
    ranking_criteria: List[str] = field(default_factory=lambda: ["volume_24h"])
    ranking_order: str = "desc"  # "asc" or "desc"
    
    # Rebalancing
    rebalance_frequency: str = "weekly"  # How often to rebalance the universe
    rebalance_threshold: float = 0.1  # Minimum change to trigger rebalance
    
    # Data collection settings
    collect_fields: Optional[List[str]] = None
    
    # Storage settings
    save_history: bool = True
    history_retention_days: int = 365


# Predefined universe configurations
PREDEFINED_UNIVERSES: Dict[str, UniverseConfig] = {
    "top_spot_by_volume": UniverseConfig(
        name="top_spot_by_volume",
        description="Top spot trading pairs by 24h volume",
        exchanges=["binance", "okx"],
        market_types=["spot"],
        filters=FilterConfig(
            min_volume_usd_24h=1_000_000,  # $1M minimum daily volume
            quote_assets=["USDT", "BUSD", "USDC"],
            min_listing_days=30,  # At least 30 days since listing
        ),
        max_symbols=100,
        ranking_criteria=["volume_24h"],
        ranking_order="desc",
        update_frequency="daily",
    ),
    
    "major_cryptocurrencies": UniverseConfig(
        name="major_cryptocurrencies",
        description="Major cryptocurrencies (top market cap)",
        exchanges=["binance", "okx"],
        market_types=["spot"],
        filters=FilterConfig(
            base_assets=["BTC", "ETH", "BNB", "ADA", "XRP", "SOL", "DOT", "AVAX", "MATIC", "LINK"],
            quote_assets=["USDT", "BUSD", "USDC"],
            min_volume_usd_24h=5_000_000,  # $5M minimum daily volume
        ),
        max_symbols=50,
        ranking_criteria=["volume_24h"],
        ranking_order="desc",
        update_frequency="daily",
    ),
    
    "perpetual_contracts": UniverseConfig(
        name="perpetual_contracts",
        description="Active perpetual contracts",
        exchanges=["binance", "okx"],
        market_types=["perpetual"],
        filters=FilterConfig(
            min_volume_usd_24h=10_000_000,  # $10M minimum daily volume
            quote_assets=["USDT", "BUSD"],
            min_listing_days=7,  # At least 7 days since listing
        ),
        max_symbols=50,
        ranking_criteria=["volume_24h", "open_interest"],
        ranking_order="desc",
        update_frequency="daily",
    ),
    
    "defi_tokens": UniverseConfig(
        name="defi_tokens",
        description="DeFi tokens universe",
        exchanges=["binance", "okx"],
        market_types=["spot"],
        filters=FilterConfig(
            base_assets=["UNI", "AAVE", "COMP", "MKR", "SNX", "CRV", "1INCH", "SUSHI", "YFI", "BAL"],
            quote_assets=["USDT", "BUSD", "USDC"],
            min_volume_usd_24h=1_000_000,  # $1M minimum daily volume
        ),
        max_symbols=30,
        ranking_criteria=["volume_24h"],
        ranking_order="desc",
        update_frequency="daily",
    ),
    
    "layer1_blockchains": UniverseConfig(
        name="layer1_blockchains",
        description="Layer 1 blockchain tokens",
        exchanges=["binance", "okx"],
        market_types=["spot"],
        filters=FilterConfig(
            base_assets=["BTC", "ETH", "BNB", "ADA", "SOL", "DOT", "AVAX", "ATOM", "NEAR", "FTM"],
            quote_assets=["USDT", "BUSD", "USDC"],
            min_volume_usd_24h=2_000_000,  # $2M minimum daily volume
        ),
        max_symbols=20,
        ranking_criteria=["volume_24h"],
        ranking_order="desc",
        update_frequency="daily",
    ),
    
    "high_volatility": UniverseConfig(
        name="high_volatility",
        description="High volatility trading pairs",
        exchanges=["binance", "okx"],
        market_types=["spot"],
        filters=FilterConfig(
            min_change_24h=5.0,  # At least 5% daily change
            min_volume_usd_24h=500_000,  # $500K minimum daily volume
            quote_assets=["USDT", "BUSD", "USDC"],
            min_listing_days=14,  # At least 14 days since listing
        ),
        max_symbols=50,
        ranking_criteria=["change_24h", "volume_24h"],
        ranking_order="desc",
        update_frequency="hourly",
    ),
    
    "stable_pairs": UniverseConfig(
        name="stable_pairs",
        description="Low volatility, stable trading pairs",
        exchanges=["binance", "okx"],
        market_types=["spot"],
        filters=FilterConfig(
            max_change_24h=2.0,  # Maximum 2% daily change
            min_volume_usd_24h=10_000_000,  # $10M minimum daily volume
            quote_assets=["USDT", "BUSD", "USDC"],
            min_listing_days=90,  # At least 90 days since listing
        ),
        max_symbols=30,
        ranking_criteria=["volume_24h"],
        ranking_order="desc",
        update_frequency="daily",
    ),
}


def get_universe_config(name: str) -> Optional[UniverseConfig]:
    """
    Get a predefined universe configuration by name.
    
    Parameters
    ----------
    name : str
        Name of the predefined universe
        
    Returns
    -------
    Optional[UniverseConfig]
        Universe configuration or None if not found
    """
    return PREDEFINED_UNIVERSES.get(name)


def list_predefined_universes() -> List[str]:
    """
    Get list of available predefined universe names.
    
    Returns
    -------
    List[str]
        List of predefined universe names
    """
    return list(PREDEFINED_UNIVERSES.keys())


def create_custom_universe(
    name: str,
    description: str = "",
    exchanges: List[str] = None,
    market_types: List[str] = None,
    **filter_kwargs
) -> UniverseConfig:
    """
    Create a custom universe configuration.
    
    Parameters
    ----------
    name : str
        Universe name
    description : str, optional
        Universe description
    exchanges : List[str], optional
        List of exchanges to use
    market_types : List[str], optional
        List of market types to include
    **filter_kwargs
        Additional filter criteria
        
    Returns
    -------
    UniverseConfig
        Custom universe configuration
    """
    if exchanges is None:
        exchanges = ["binance"]
    
    if market_types is None:
        market_types = ["spot"]
    
    filters = FilterConfig(**filter_kwargs)
    
    return UniverseConfig(
        name=name,
        description=description,
        exchanges=exchanges,
        market_types=market_types,
        filters=filters,
    )


def save_universe_config(config: UniverseConfig, filepath: str) -> None:
    """
    Save universe configuration to JSON file.
    
    Parameters
    ----------
    config : UniverseConfig
        Universe configuration to save
    filepath : str
        Path to save the configuration file
    """
    import json
    from dataclasses import asdict
    
    with open(filepath, 'w') as f:
        json.dump(asdict(config), f, indent=2, default=str)


def load_universe_config(filepath: str) -> UniverseConfig:
    """
    Load universe configuration from JSON file.
    
    Parameters
    ----------
    filepath : str
        Path to the configuration file
        
    Returns
    -------
    UniverseConfig
        Loaded universe configuration
    """
    import json
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Convert filters dict to FilterConfig
    if 'filters' in data:
        data['filters'] = FilterConfig(**data['filters'])
    
    return UniverseConfig(**data)
