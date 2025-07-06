#!/usr/bin/env python3
"""
永续合约数据收集使用示例

本示例展示如何使用crypto collector收集永续合约数据，包括：
1. 获取所有永续合约交易对
2. 收集BTCUSDT的资金费率和K线数据
3. 批量收集多个交易对的数据

使用前请确保：
1. 网络连接正常或已配置代理
2. 可选：配置Binance API密钥以获得更高限制
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd

# Add the crypto module to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchange_adapters.binance_adapter import BinanceAdapter
from crypto_field_collector import CryptoFieldCollector
from storage_manager import CryptoStorageManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerpetualDataCollector:
    """永续合约数据收集器"""
    
    def __init__(self, 
                 api_key: str = None,
                 api_secret: str = None,
                 proxy_url: str = None,
                 data_dir: str = "./perpetual_data"):
        """
        初始化永续合约数据收集器
        
        Parameters
        ----------
        api_key : str, optional
            Binance API密钥
        api_secret : str, optional
            Binance API密钥
        proxy_url : str, optional
            代理URL，如 "http://127.0.0.1:7890"
        data_dir : str, default "./perpetual_data"
            数据存储目录
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.proxy_url = proxy_url
        self.data_dir = data_dir
        
        # 设置代理
        if proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            logger.info(f"设置代理: {proxy_url}")
        
        # 初始化组件
        self.adapter = None
        self.collector = None
        self.storage = None
        
    def initialize(self):
        """初始化所有组件"""
        try:
            # 初始化Binance永续合约适配器
            self.adapter = BinanceAdapter(
                market_type="perpetual",
                api_key=self.api_key,
                api_secret=self.api_secret,
                sandbox=False
            )
            logger.info("✓ Binance永续合约适配器初始化成功")
            
            # 初始化字段收集器
            self.collector = CryptoFieldCollector(self.adapter)
            logger.info("✓ 字段收集器初始化成功")
            
            # 初始化存储管理器
            self.storage = CryptoStorageManager(data_dir=self.data_dir)
            logger.info("✓ 存储管理器初始化成功")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 初始化失败: {e}")
            return False
    
    def get_all_perpetual_symbols(self) -> List[str]:
        """获取所有永续合约交易对"""
        logger.info("获取所有永续合约交易对...")
        
        try:
            symbols = self.adapter.get_instruments(market_type="perpetual")
            logger.info(f"✓ 发现 {len(symbols)} 个永续合约交易对")
            
            # 显示前20个交易对
            logger.info("前20个永续合约交易对:")
            for i, symbol in enumerate(symbols[:20]):
                logger.info(f"  {i+1:2d}. {symbol}")
            
            if len(symbols) > 20:
                logger.info(f"  ... 还有 {len(symbols) - 20} 个交易对")
            
            return symbols
            
        except Exception as e:
            logger.error(f"✗ 获取永续合约交易对失败: {e}")
            return []
    
    def collect_btcusdt_data(self, timeframe: str = "1h", days: int = 7):
        """
        收集BTCUSDT的资金费率和K线数据
        
        Parameters
        ----------
        timeframe : str, default "1h"
            时间框架
        days : int, default 7
            收集天数
        """
        symbol = "BTC/USDT"
        logger.info(f"收集 {symbol} 的数据...")
        
        try:
            # 1. 收集资金费率
            logger.info("收集资金费率...")
            funding_rate = self.collector.collect_funding_rate(symbol)
            
            if funding_rate:
                logger.info("✓ 资金费率收集成功")
                logger.info(f"  当前资金费率: {funding_rate.get('funding_rate')}")
                logger.info(f"  下次资金费率时间: {funding_rate.get('next_funding_datetime')}")
            else:
                logger.warning("⚠ 资金费率收集失败")
            
            # 2. 收集K线数据
            logger.info(f"收集 {timeframe} K线数据（最近{days}天）...")
            
            # 计算需要的数据量
            timeframe_hours = {
                "1m": 1/60, "5m": 5/60, "15m": 15/60, "30m": 30/60,
                "1h": 1, "2h": 2, "4h": 4, "6h": 6, "8h": 8, "12h": 12,
                "1d": 24
            }
            
            hours_per_candle = timeframe_hours.get(timeframe, 1)
            limit = int(days * 24 / hours_per_candle)
            
            ohlcv_data = self.adapter.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=min(limit, 1000)  # Binance限制
            )
            
            if not ohlcv_data.empty:
                logger.info(f"✓ K线数据收集成功，共 {len(ohlcv_data)} 条记录")
                logger.info(f"  时间范围: {ohlcv_data.index[0]} 到 {ohlcv_data.index[-1]}")
                logger.info(f"  最新价格: {ohlcv_data['close'].iloc[-1]:.2f}")
                
                # 保存数据
                self.storage.save_ohlcv_data(
                    data=ohlcv_data,
                    symbol_id=f"binance_{symbol.replace('/', '_').lower()}",
                    timeframe=timeframe
                )
                logger.info("✓ K线数据保存成功")
                
                return {
                    'funding_rate': funding_rate,
                    'ohlcv_data': ohlcv_data,
                    'latest_price': float(ohlcv_data['close'].iloc[-1])
                }
            else:
                logger.error("✗ K线数据为空")
                return None
                
        except Exception as e:
            logger.error(f"✗ 收集 {symbol} 数据失败: {e}")
            return None
    
    def collect_multiple_symbols(self, 
                                symbols: List[str], 
                                timeframe: str = "1h",
                                limit: int = 100):
        """
        批量收集多个交易对的数据
        
        Parameters
        ----------
        symbols : List[str]
            交易对列表
        timeframe : str, default "1h"
            时间框架
        limit : int, default 100
            每个交易对的数据条数
        """
        logger.info(f"批量收集 {len(symbols)} 个交易对的数据...")
        
        results = {}
        
        for i, symbol in enumerate(symbols):
            logger.info(f"[{i+1}/{len(symbols)}] 收集 {symbol} 数据...")
            
            try:
                # 收集K线数据
                ohlcv_data = self.adapter.get_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit
                )
                
                if not ohlcv_data.empty:
                    # 收集资金费率
                    funding_rate = self.collector.collect_funding_rate(symbol)
                    
                    # 收集交易对信息
                    symbol_info = self.adapter.get_symbol_info(symbol)
                    
                    results[symbol] = {
                        'ohlcv_data': ohlcv_data,
                        'funding_rate': funding_rate,
                        'symbol_info': symbol_info,
                        'latest_price': float(ohlcv_data['close'].iloc[-1])
                    }
                    
                    logger.info(f"  ✓ {symbol} 数据收集成功，最新价格: {results[symbol]['latest_price']:.4f}")
                    
                    # 保存数据
                    symbol_id = f"binance_{symbol.replace('/', '_').lower()}"
                    self.storage.save_ohlcv_data(ohlcv_data, symbol_id, timeframe)
                    
                else:
                    logger.warning(f"  ⚠ {symbol} K线数据为空")
                    
            except Exception as e:
                logger.error(f"  ✗ {symbol} 数据收集失败: {e}")
                
            # 添加延迟以避免触发限制
            import time
            time.sleep(0.1)
        
        logger.info(f"批量收集完成，成功收集 {len(results)} 个交易对的数据")
        return results
    
    def generate_summary_report(self, results: Dict[str, Any]):
        """生成汇总报告"""
        logger.info("\n" + "="*60)
        logger.info("永续合约数据收集汇总报告")
        logger.info("="*60)
        
        if not results:
            logger.info("无数据可报告")
            return
        
        # 统计信息
        total_symbols = len(results)
        successful_funding_rates = sum(1 for r in results.values() if r.get('funding_rate'))
        
        logger.info(f"收集的交易对数量: {total_symbols}")
        logger.info(f"成功获取资金费率: {successful_funding_rates}")
        
        # 价格信息
        logger.info("\n价格信息:")
        for symbol, data in list(results.items())[:10]:  # 显示前10个
            price = data.get('latest_price', 0)
            funding_rate = data.get('funding_rate', {}).get('funding_rate', 0)
            logger.info(f"  {symbol:12s}: {price:12.4f} (资金费率: {funding_rate:8.6f})")
        
        if total_symbols > 10:
            logger.info(f"  ... 还有 {total_symbols - 10} 个交易对")


def main():
    """主函数 - 使用示例"""
    logger.info("永续合约数据收集示例")
    
    # 配置参数
    config = {
        # 'api_key': 'your_api_key',      # 可选：API密钥
        # 'api_secret': 'your_api_secret', # 可选：API密钥
        # 'proxy_url': 'http://127.0.0.1:7890',  # 可选：代理URL
        'data_dir': './perpetual_data'
    }
    
    # 初始化收集器
    collector = PerpetualDataCollector(**config)
    
    if not collector.initialize():
        logger.error("初始化失败，退出")
        return 1
    
    try:
        # 1. 获取所有永续合约交易对
        all_symbols = collector.get_all_perpetual_symbols()
        
        if not all_symbols:
            logger.error("无法获取交易对列表，退出")
            return 1
        
        # 2. 收集BTCUSDT数据
        btc_data = collector.collect_btcusdt_data(timeframe="1h", days=7)
        
        # 3. 批量收集热门交易对数据
        popular_symbols = [s for s in all_symbols if any(coin in s for coin in ['BTC', 'ETH', 'BNB', 'ADA', 'SOL'])][:10]
        
        if popular_symbols:
            logger.info(f"\n收集热门交易对: {popular_symbols}")
            batch_results = collector.collect_multiple_symbols(
                symbols=popular_symbols,
                timeframe="1h",
                limit=24
            )
            
            # 生成报告
            collector.generate_summary_report(batch_results)
        
        logger.info("\n✓ 数据收集完成")
        return 0
        
    except Exception as e:
        logger.error(f"数据收集过程中出错: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
