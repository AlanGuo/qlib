# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Configuration module for crypto data collection.
"""

from config.timeframes import TIMEFRAME_MAPPING, SUPPORTED_TIMEFRAMES
from config.fields import CRYPTO_FIELDS, STANDARD_FIELDS, EXTENDED_FIELDS
from config.exchanges import EXCHANGE_CONFIGS, DEFAULT_EXCHANGE_CONFIG
from config.main_config import CryptoDataConfig, ConfigFactory
from config.risk_config import RiskConfig
from config.universe_config import UniverseConfig, FilterConfig
from config.validation_config import ValidationConfig
from config.template_manager import ConfigTemplateManager, load_template, list_templates

__all__ = [
    "TIMEFRAME_MAPPING",
    "SUPPORTED_TIMEFRAMES",
    "CRYPTO_FIELDS",
    "STANDARD_FIELDS",
    "EXTENDED_FIELDS",
    "EXCHANGE_CONFIGS",
    "DEFAULT_EXCHANGE_CONFIG",
    "CryptoDataConfig",
    "ConfigFactory",
    "RiskConfig",
    "UniverseConfig",
    "FilterConfig",
    "ValidationConfig",
    "ConfigTemplateManager",
    "load_template",
    "list_templates",
]
