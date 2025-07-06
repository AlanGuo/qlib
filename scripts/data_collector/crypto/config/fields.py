# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Data field configuration for cryptocurrency data collection.

This module defines the standard and extended data fields available
for cryptocurrency data collection.
"""

from typing import Dict, List, Set

from dataclasses import dataclass

@dataclass
class FieldConfig:
    """Configuration for a data field."""
    name: str
    description: str
    data_type: str
    required: bool = False
    default_value: any = None
    exchanges: Set[str] = None  # None means all exchanges support it
    market_types: Set[str] = None  # None means all market types support it

# Standard OHLCV fields (compatible with traditional finance)
STANDARD_FIELDS: Dict[str, FieldConfig] = {
    "open": FieldConfig(
        name="open",
        description="Opening price",
        data_type="float",
        required=True
    ),
    "high": FieldConfig(
        name="high", 
        description="Highest price",
        data_type="float",
        required=True
    ),
    "low": FieldConfig(
        name="low",
        description="Lowest price", 
        data_type="float",
        required=True
    ),
    "close": FieldConfig(
        name="close",
        description="Closing price",
        data_type="float", 
        required=True
    ),
    "volume": FieldConfig(
        name="volume",
        description="Trading volume (base currency)",
        data_type="float",
        required=True
    ),
}

# Crypto-specific fields
CRYPTO_SPECIFIC_FIELDS: Dict[str, FieldConfig] = {
    "funding_rate": FieldConfig(
        name="funding_rate",
        description="Funding rate for perpetual contracts",
        data_type="float",
        market_types={"perpetual", "futures"}
    ),
    "open_interest": FieldConfig(
        name="open_interest", 
        description="Open interest for futures/perpetual contracts",
        data_type="float",
        market_types={"perpetual", "futures"}
    ),
    "volume_quote": FieldConfig(
        name="volume_quote",
        description="Trading volume in quote currency",
        data_type="float"
    ),
    "volume_24h": FieldConfig(
        name="volume_24h",
        description="24-hour trading volume",
        data_type="float"
    ),
    "change_24h": FieldConfig(
        name="change_24h",
        description="24-hour price change percentage",
        data_type="float"
    ),
    "high_24h": FieldConfig(
        name="high_24h",
        description="24-hour highest price",
        data_type="float"
    ),
    "low_24h": FieldConfig(
        name="low_24h",
        description="24-hour lowest price", 
        data_type="float"
    ),
    "vwap": FieldConfig(
        name="vwap",
        description="Volume weighted average price",
        data_type="float"
    ),
    "trade_count": FieldConfig(
        name="trade_count",
        description="Number of trades",
        data_type="int"
    ),
}

# Market microstructure fields
MICROSTRUCTURE_FIELDS: Dict[str, FieldConfig] = {
    "bid_price": FieldConfig(
        name="bid_price",
        description="Best bid price",
        data_type="float"
    ),
    "ask_price": FieldConfig(
        name="ask_price", 
        description="Best ask price",
        data_type="float"
    ),
    "bid_size": FieldConfig(
        name="bid_size",
        description="Best bid size",
        data_type="float"
    ),
    "ask_size": FieldConfig(
        name="ask_size",
        description="Best ask size", 
        data_type="float"
    ),
    "spread": FieldConfig(
        name="spread",
        description="Bid-ask spread",
        data_type="float"
    ),
    "spread_pct": FieldConfig(
        name="spread_pct",
        description="Bid-ask spread percentage",
        data_type="float"
    ),
}

# Liquidation and risk fields
RISK_FIELDS: Dict[str, FieldConfig] = {
    "liquidation_volume": FieldConfig(
        name="liquidation_volume",
        description="Liquidation volume",
        data_type="float",
        market_types={"perpetual", "futures"}
    ),
    "long_liquidation": FieldConfig(
        name="long_liquidation",
        description="Long position liquidation volume",
        data_type="float",
        market_types={"perpetual", "futures"}
    ),
    "short_liquidation": FieldConfig(
        name="short_liquidation",
        description="Short position liquidation volume", 
        data_type="float",
        market_types={"perpetual", "futures"}
    ),
    "funding_rate_8h": FieldConfig(
        name="funding_rate_8h",
        description="8-hour funding rate",
        data_type="float",
        market_types={"perpetual"}
    ),
}

# All available fields
ALL_FIELDS: Dict[str, FieldConfig] = {
    **STANDARD_FIELDS,
    **CRYPTO_SPECIFIC_FIELDS, 
    **MICROSTRUCTURE_FIELDS,
    **RISK_FIELDS,
}

# Field groups for easy selection
FIELD_GROUPS: Dict[str, List[str]] = {
    "ohlcv": list(STANDARD_FIELDS.keys()),
    "basic": ["open", "high", "low", "close", "volume", "volume_quote"],
    "extended": ["open", "high", "low", "close", "volume", "volume_quote", "volume_24h", "change_24h"],
    "crypto_standard": [
        "open", "high", "low", "close", "volume", "volume_quote", 
        "volume_24h", "change_24h", "vwap", "trade_count"
    ],
    "futures": [
        "open", "high", "low", "close", "volume", "volume_quote",
        "funding_rate", "open_interest", "volume_24h"
    ],
    "microstructure": [
        "open", "high", "low", "close", "volume",
        "bid_price", "ask_price", "bid_size", "ask_size", "spread"
    ],
    "risk_analysis": [
        "open", "high", "low", "close", "volume", "funding_rate", 
        "open_interest", "liquidation_volume"
    ],
    "all": list(ALL_FIELDS.keys()),
}

# Default field sets by market type
DEFAULT_FIELDS_BY_MARKET: Dict[str, List[str]] = {
    "spot": FIELD_GROUPS["crypto_standard"],
    "futures": FIELD_GROUPS["futures"], 
    "perpetual": FIELD_GROUPS["futures"],
    "option": FIELD_GROUPS["basic"],
}

def get_fields_for_group(group: str) -> List[str]:
    """
    Get field list for a predefined group.
    
    Parameters
    ----------
    group : str
        Field group name
        
    Returns
    -------
    List[str]
        List of field names
    """
    return FIELD_GROUPS.get(group, [])

def get_fields_for_market_type(market_type: str) -> List[str]:
    """
    Get default fields for a market type.
    
    Parameters
    ----------
    market_type : str
        Market type (spot, futures, perpetual, option)
        
    Returns
    -------
    List[str]
        List of field names
    """
    return DEFAULT_FIELDS_BY_MARKET.get(market_type, FIELD_GROUPS["basic"])

def validate_field(field_name: str, market_type: str = None, exchange: str = None) -> bool:
    """
    Validate if a field is supported for given market type and exchange.
    
    Parameters
    ----------
    field_name : str
        Field name to validate
    market_type : str, optional
        Market type to check compatibility
    exchange : str, optional
        Exchange to check compatibility
        
    Returns
    -------
    bool
        True if field is supported
    """
    if field_name not in ALL_FIELDS:
        return False
    
    field_config = ALL_FIELDS[field_name]
    
    # Check market type compatibility
    if market_type and field_config.market_types:
        if market_type not in field_config.market_types:
            return False
    
    # Check exchange compatibility  
    if exchange and field_config.exchanges:
        if exchange not in field_config.exchanges:
            return False
    
    return True

def get_field_config(field_name: str) -> FieldConfig:
    """
    Get configuration for a field.

    Parameters
    ----------
    field_name : str
        Field name

    Returns
    -------
    FieldConfig
        Field configuration
    """
    return ALL_FIELDS.get(field_name)

def is_field_supported_for_exchange(field_name: str, exchange: str, market_type: str = None) -> bool:
    """
    Check if a field is supported for a specific exchange and market type.

    Parameters
    ----------
    field_name : str
        Field name
    exchange : str
        Exchange identifier
    market_type : str, optional
        Market type (spot, futures, perpetual, option)

    Returns
    -------
    bool
        True if field is supported
    """
    if field_name not in ALL_FIELDS:
        return False

    field_config = ALL_FIELDS[field_name]

    # Check exchange compatibility
    if field_config.exchanges and exchange not in field_config.exchanges:
        return False

    # Check market type compatibility
    if market_type and field_config.market_types:
        if market_type not in field_config.market_types:
            return False

    return True

def filter_fields_by_market_type(fields: List[str], market_type: str) -> List[str]:
    """
    Filter fields that are compatible with a market type.
    
    Parameters
    ----------
    fields : List[str]
        List of field names to filter
    market_type : str
        Market type to filter by
        
    Returns
    -------
    List[str]
        Filtered list of compatible fields
    """
    return [
        field for field in fields 
        if validate_field(field, market_type=market_type)
    ]

def get_required_fields() -> List[str]:
    """
    Get list of required fields.
    
    Returns
    -------
    List[str]
        List of required field names
    """
    return [
        name for name, config in ALL_FIELDS.items()
        if config.required
    ]


# Export aliases for backward compatibility and convenience
CRYPTO_FIELDS = ALL_FIELDS
EXTENDED_FIELDS = {**CRYPTO_SPECIFIC_FIELDS, **MICROSTRUCTURE_FIELDS, **RISK_FIELDS}
