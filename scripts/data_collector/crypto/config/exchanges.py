# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Exchange configuration for cryptocurrency data collection.

This module defines configuration settings for different cryptocurrency exchanges.
"""

from typing import Dict, List, Set, Optional

from dataclasses import dataclass

@dataclass
class ExchangeConfig:
    """Configuration for a cryptocurrency exchange."""
    name: str
    id: str
    ccxt_id: str
    api_base_url: str
    sandbox_url: Optional[str] = None
    rate_limit: float = 0.1  # seconds between requests
    max_requests_per_minute: int = 600
    supported_market_types: Set[str] = None
    supported_timeframes: List[str] = None
    requires_api_key: bool = False
    has_funding_rates: bool = False
    has_open_interest: bool = False
    has_liquidation_data: bool = False
    max_candles_per_request: int = 1000
    historical_data_limit_days: int = 365
    
    def __post_init__(self):
        if self.supported_market_types is None:
            self.supported_market_types = {"spot"}
        if self.supported_timeframes is None:
            self.supported_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Exchange configurations - Only Binance and OKX supported
EXCHANGE_CONFIGS: Dict[str, ExchangeConfig] = {
    "binance": ExchangeConfig(
        name="Binance",
        id="binance",
        ccxt_id="binance",
        api_base_url="https://api.binance.com",
        sandbox_url="https://testnet.binance.vision",
        rate_limit=0.1,
        max_requests_per_minute=1200,
        supported_market_types={"spot", "futures", "perpetual"},
        supported_timeframes=[
            "1min", "5min", "15min", "30min", "1h", "day"
        ],
        requires_api_key=False,
        has_funding_rates=True,
        has_open_interest=True,
        has_liquidation_data=True,
        max_candles_per_request=1000,
        historical_data_limit_days=1000,
    ),
    
    "okx": ExchangeConfig(
        name="OKX",
        id="okx", 
        ccxt_id="okx",
        api_base_url="https://www.okx.com",
        sandbox_url="https://www.okx.com",
        rate_limit=0.1,
        max_requests_per_minute=600,
        supported_market_types={"spot", "futures", "perpetual", "option"},
        supported_timeframes=[
            "1min", "5min", "15min", "30min", "1h", "day"
        ],
        requires_api_key=False,
        has_funding_rates=True,
        has_open_interest=True,
        has_liquidation_data=True,
        max_candles_per_request=300,
        historical_data_limit_days=1095,
    ),
}

# Default configuration for unknown exchanges
DEFAULT_EXCHANGE_CONFIG = ExchangeConfig(
    name="Unknown Exchange",
    id="unknown",
    ccxt_id="unknown",
    api_base_url="",
    rate_limit=0.2,
    max_requests_per_minute=300,
    supported_market_types={"spot"},
    supported_timeframes=["1min", "5min", "15min", "30min", "1h", "day"],
    requires_api_key=False,
    has_funding_rates=False,
    has_open_interest=False,
    has_liquidation_data=False,
    max_candles_per_request=500,
    historical_data_limit_days=365,
)

# Exchange groups for batch operations
EXCHANGE_GROUPS: Dict[str, List[str]] = {
    "tier1": ["binance", "okx"],
    "spot_only": [],
    "derivatives": ["binance", "okx"],
    "funding_rates": ["binance", "okx"],
    "high_volume": ["binance", "okx"],
    "all": list(EXCHANGE_CONFIGS.keys()),
}

def get_exchange_config(exchange_id: str) -> ExchangeConfig:
    """
    Get configuration for an exchange.
    
    Parameters
    ----------
    exchange_id : str
        Exchange identifier
        
    Returns
    -------
    ExchangeConfig
        Exchange configuration
    """
    return EXCHANGE_CONFIGS.get(exchange_id.lower(), DEFAULT_EXCHANGE_CONFIG)

def get_exchanges_by_group(group: str) -> List[str]:
    """
    Get list of exchanges in a group.
    
    Parameters
    ----------
    group : str
        Exchange group name
        
    Returns
    -------
    List[str]
        List of exchange IDs
    """
    return EXCHANGE_GROUPS.get(group, [])

def get_exchanges_supporting_market_type(market_type: str) -> List[str]:
    """
    Get exchanges that support a specific market type.
    
    Parameters
    ----------
    market_type : str
        Market type (spot, futures, perpetual, option)
        
    Returns
    -------
    List[str]
        List of exchange IDs
    """
    return [
        exchange_id for exchange_id, config in EXCHANGE_CONFIGS.items()
        if market_type in config.supported_market_types
    ]

def get_exchanges_with_feature(feature: str) -> List[str]:
    """
    Get exchanges that support a specific feature.
    
    Parameters
    ----------
    feature : str
        Feature name (funding_rates, open_interest, liquidation_data)
        
    Returns
    -------
    List[str]
        List of exchange IDs
    """
    feature_map = {
        "funding_rates": "has_funding_rates",
        "open_interest": "has_open_interest", 
        "liquidation_data": "has_liquidation_data",
    }
    
    attr_name = feature_map.get(feature)
    if not attr_name:
        return []
    
    return [
        exchange_id for exchange_id, config in EXCHANGE_CONFIGS.items()
        if getattr(config, attr_name, False)
    ]

def validate_exchange_timeframe(exchange_id: str, timeframe: str) -> bool:
    """
    Validate if an exchange supports a timeframe.
    
    Parameters
    ----------
    exchange_id : str
        Exchange identifier
    timeframe : str
        Timeframe to validate
        
    Returns
    -------
    bool
        True if timeframe is supported
    """
    config = get_exchange_config(exchange_id)
    return timeframe in config.supported_timeframes

def get_optimal_batch_size(exchange_id: str, timeframe: str) -> int:
    """
    Get optimal batch size for data collection.
    
    Parameters
    ----------
    exchange_id : str
        Exchange identifier
    timeframe : str
        Data timeframe
        
    Returns
    -------
    int
        Optimal batch size
    """
    config = get_exchange_config(exchange_id)
    base_size = config.max_candles_per_request
    
    # Adjust based on timeframe
    timeframe_multipliers = {
        "1min": 1.0, "5min": 1.0, "15min": 1.2, 
        "30min": 1.5, "1h": 2.0, "day": 5.0
    }
    
    multiplier = timeframe_multipliers.get(timeframe, 1.0)
    return int(base_size * multiplier)
