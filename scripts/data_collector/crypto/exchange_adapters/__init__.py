# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Exchange adapters for cryptocurrency data collection.

This module provides adapters for different cryptocurrency exchanges,
implementing a unified interface for data access.
"""

from exchange_adapters.base_adapter import ExchangeAdapter
from exchange_adapters.binance_adapter import BinanceAdapter
from exchange_adapters.okx_adapter import OKXAdapter

__all__ = [
    "ExchangeAdapter",
    "BinanceAdapter",
    "OKXAdapter",
]