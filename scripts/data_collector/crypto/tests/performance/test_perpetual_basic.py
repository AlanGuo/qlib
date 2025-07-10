#!/usr/bin/env python3
"""
永续合约基础功能测试

本测试验证永续合约功能的基础实现，不需要网络连接。
使用pytest框架，符合现有测试计划的格式和组织结构。

测试内容：
1. 配置支持验证
2. 适配器实现验证
3. 字段收集器验证
4. CCXT库支持验证
5. 市场类型逻辑验证
"""

import pytest
import sys
import os
import logging
from unittest.mock import patch, MagicMock

# Add the crypto module to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestPerpetualConfigSupport:
    """测试永续合约配置支持"""
    
    def test_binance_config_supports_perpetual(self):
        """测试Binance配置支持永续合约"""
        from config.exchanges import EXCHANGE_CONFIGS
        
        binance_config = EXCHANGE_CONFIGS.get("binance")
        assert binance_config is not None, "Binance配置不存在"
        
        assert "perpetual" in binance_config.supported_market_types, \
            f"Binance配置不支持永续合约，支持的市场类型: {binance_config.supported_market_types}"
        
        assert binance_config.has_funding_rates, "Binance配置应该支持资金费率"
        assert binance_config.has_open_interest, "Binance配置应该支持持仓量"
    
    def test_crypto_specific_fields_include_perpetual(self):
        """测试加密货币特定字段包含永续合约字段"""
        from config.fields import CRYPTO_SPECIFIC_FIELDS
        
        # 检查资金费率字段
        assert "funding_rate" in CRYPTO_SPECIFIC_FIELDS, "缺少资金费率字段"
        funding_rate_field = CRYPTO_SPECIFIC_FIELDS["funding_rate"]
        assert "perpetual" in funding_rate_field.market_types, \
            f"资金费率字段不支持永续合约市场，支持的市场类型: {funding_rate_field.market_types}"
        
        # 检查持仓量字段
        assert "open_interest" in CRYPTO_SPECIFIC_FIELDS, "缺少持仓量字段"
        open_interest_field = CRYPTO_SPECIFIC_FIELDS["open_interest"]
        assert "perpetual" in open_interest_field.market_types, \
            f"持仓量字段不支持永续合约市场，支持的市场类型: {open_interest_field.market_types}"


class TestPerpetualAdapterImplementation:
    """测试永续合约适配器实现"""
    
    def test_binance_adapter_has_perpetual_methods(self):
        """测试BinanceAdapter包含永续合约相关方法"""
        from exchange_adapters.binance_adapter import BinanceAdapter
        from exchange_adapters.base_adapter import ExchangeAdapter
        
        # 检查BinanceAdapter类
        assert hasattr(BinanceAdapter, 'get_funding_rate'), "BinanceAdapter缺少get_funding_rate方法"
        assert hasattr(BinanceAdapter, 'get_open_interest'), "BinanceAdapter缺少get_open_interest方法"
        assert hasattr(BinanceAdapter, 'get_instruments'), "BinanceAdapter缺少get_instruments方法"
        assert hasattr(BinanceAdapter, 'get_ohlcv'), "BinanceAdapter缺少get_ohlcv方法"
        assert hasattr(BinanceAdapter, 'get_symbol_info'), "BinanceAdapter缺少get_symbol_info方法"
        
        # 检查基类方法
        assert hasattr(ExchangeAdapter, 'get_funding_rate'), "ExchangeAdapter基类缺少get_funding_rate方法"
        assert hasattr(ExchangeAdapter, 'get_open_interest'), "ExchangeAdapter基类缺少get_open_interest方法"
    
    def test_binance_adapter_supports_perpetual_market_type(self):
        """测试BinanceAdapter支持永续合约市场类型"""
        with patch('exchange_adapters.binance_adapter.ccxt.binance') as mock_ccxt:
            mock_exchange = MagicMock()
            mock_ccxt.return_value = mock_exchange
            
            from exchange_adapters.binance_adapter import BinanceAdapter
            
            # 测试不同市场类型的初始化
            adapter_spot = BinanceAdapter(market_type="spot")
            assert adapter_spot.market_type == "spot"
            
            adapter_futures = BinanceAdapter(market_type="futures")
            assert adapter_futures.market_type == "futures"
            
            adapter_perpetual = BinanceAdapter(market_type="perpetual")
            assert adapter_perpetual.market_type == "perpetual"


class TestPerpetualFieldCollector:
    """测试永续合约字段收集器"""
    
    def test_crypto_field_collector_has_perpetual_methods(self):
        """测试CryptoFieldCollector包含永续合约相关方法"""
        from crypto_field_collector import CryptoFieldCollector
        
        assert hasattr(CryptoFieldCollector, 'collect_funding_rate'), \
            "CryptoFieldCollector缺少collect_funding_rate方法"
        assert hasattr(CryptoFieldCollector, 'collect_open_interest'), \
            "CryptoFieldCollector缺少collect_open_interest方法"
        assert hasattr(CryptoFieldCollector, 'collect_order_book_fields'), \
            "CryptoFieldCollector缺少collect_order_book_fields方法"


class TestCCXTLibrarySupport:
    """测试CCXT库对永续合约的支持"""
    
    def test_ccxt_library_available(self):
        """测试CCXT库可用性"""
        import ccxt
        
        assert hasattr(ccxt, 'binance'), "CCXT库不包含Binance交易所"
        
        # 创建测试实例（不连接网络）
        exchange = ccxt.binance({
            'apiKey': 'test',
            'secret': 'test',
            'sandbox': True,
            'enableRateLimit': True,
        })
        
        # 检查永续合约相关方法
        perpetual_methods = [
            'fetch_funding_rate',
            'fetch_funding_rates', 
            'fetch_open_interest',
            'fetch_ohlcv'
        ]
        
        for method_name in perpetual_methods:
            assert hasattr(exchange, method_name), f"CCXT Binance交易所缺少{method_name}方法"


class TestPerpetualMarketTypeLogic:
    """测试永续合约市场类型逻辑"""
    
    def test_market_type_filtering_logic(self):
        """测试市场类型过滤逻辑"""
        from config.fields import get_fields_for_market_type
        
        # 测试永续合约市场字段
        perpetual_fields = get_fields_for_market_type("perpetual")
        assert "funding_rate" in perpetual_fields, "永续合约市场应该包含资金费率字段"
        assert "open_interest" in perpetual_fields, "永续合约市场应该包含持仓量字段"
        
        # 测试期货市场字段
        futures_fields = get_fields_for_market_type("futures")
        assert "funding_rate" in futures_fields, "期货市场应该包含资金费率字段"
        assert "open_interest" in futures_fields, "期货市场应该包含持仓量字段"
        
        # 测试现货市场字段
        spot_fields = get_fields_for_market_type("spot")
        assert "funding_rate" not in spot_fields, "现货市场不应该包含资金费率字段"
        assert "open_interest" not in spot_fields, "现货市场不应该包含持仓量字段"
    
    def test_field_validation_for_market_types(self):
        """测试字段验证对市场类型的支持"""
        from config.fields import validate_field

        # 测试资金费率字段
        assert validate_field("funding_rate", market_type="perpetual"), \
            "资金费率字段应该支持永续合约市场"
        assert validate_field("funding_rate", market_type="futures"), \
            "资金费率字段应该支持期货市场"
        assert not validate_field("funding_rate", market_type="spot"), \
            "资金费率字段不应该支持现货市场"

        # 测试持仓量字段
        assert validate_field("open_interest", market_type="perpetual"), \
            "持仓量字段应该支持永续合约市场"
        assert validate_field("open_interest", market_type="futures"), \
            "持仓量字段应该支持期货市场"
        assert not validate_field("open_interest", market_type="spot"), \
            "持仓量字段不应该支持现货市场"


class TestPerpetualImplementationGaps:
    """测试永续合约实现缺口分析"""
    
    def test_no_critical_implementation_gaps(self):
        """测试没有关键实现缺口"""
        # 这个测试确保所有关键组件都已实现
        
        # 1. 配置层面
        from config.exchanges import EXCHANGE_CONFIGS
        from config.fields import CRYPTO_SPECIFIC_FIELDS
        
        binance_config = EXCHANGE_CONFIGS.get("binance")
        assert binance_config is not None
        assert "perpetual" in binance_config.supported_market_types
        assert binance_config.has_funding_rates
        assert binance_config.has_open_interest
        
        # 2. 字段定义层面
        assert "funding_rate" in CRYPTO_SPECIFIC_FIELDS
        assert "open_interest" in CRYPTO_SPECIFIC_FIELDS
        
        # 3. 适配器层面
        from exchange_adapters.binance_adapter import BinanceAdapter
        adapter_methods = ['get_funding_rate', 'get_open_interest', 'get_instruments', 'get_ohlcv']
        for method in adapter_methods:
            assert hasattr(BinanceAdapter, method)
        
        # 4. 字段收集器层面
        from crypto_field_collector import CryptoFieldCollector
        collector_methods = ['collect_funding_rate', 'collect_open_interest']
        for method in collector_methods:
            assert hasattr(CryptoFieldCollector, method)
        
        # 5. CCXT库层面
        import ccxt
        exchange = ccxt.binance({'sandbox': True})
        ccxt_methods = ['fetch_funding_rate', 'fetch_open_interest', 'fetch_ohlcv']
        for method in ccxt_methods:
            assert hasattr(exchange, method)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
