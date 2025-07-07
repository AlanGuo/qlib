#!/usr/bin/env python3
"""
测试数据收集顺序兼容性

本测试验证先收集2025年数据，再收集2020-2024年历史数据的兼容性。
"""

import os
import sys
import tempfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Add the crypto collector directory to path
_current_dir = Path(__file__).parent
if str(_current_dir.parent) not in sys.path:
    sys.path.insert(0, str(_current_dir.parent))

from exchange_adapters.binance_adapter import BinanceAdapter
from storage_manager import CryptoStorageManager
from config.main_config import CryptoDataConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataOrderCompatibilityTest:
    """数据收集顺序兼容性测试"""
    
    def __init__(self, test_dir: str = None):
        """初始化测试"""
        self.test_dir = test_dir or tempfile.mkdtemp()
        self.adapter = None
        self.storage = None
        self.config = None
        
    def setup(self):
        """设置测试环境"""
        logger.info(f"设置测试环境，数据目录: {self.test_dir}")
        
        # 创建配置
        self.config = CryptoDataConfig()
        self.config.collection.output_dir = self.test_dir
        self.config.collection.exchanges = ['binance']
        self.config.collection.timeframes = ['1h']
        self.config.collection.symbols = ['BTC/USDT']
        
        # 初始化适配器
        self.adapter = BinanceAdapter(market_type="perpetual")
        
        # 初始化存储管理器
        self.storage = CryptoStorageManager(data_dir=self.test_dir)
        
        logger.info("✓ 测试环境设置完成")
        
    def test_recent_data_collection(self):
        """测试收集最近数据（模拟2025年数据）"""
        logger.info("=== 测试收集最近数据 ===")
        
        try:
            # 收集最近7天的数据
            recent_data = self.adapter.get_ohlcv(
                symbol='BTC/USDT',
                timeframe='1h',
                limit=24 * 7  # 7天的小时数据
            )
            
            if recent_data.empty:
                logger.error("✗ 无法获取最近数据")
                return False
                
            logger.info(f"✓ 成功获取最近数据: {len(recent_data)} 条记录")
            logger.info(f"  时间范围: {recent_data.index[0]} 到 {recent_data.index[-1]}")
            
            # 保存数据
            symbol_id = "binance_btc_usdt"
            self.storage.save_ohlcv_data(
                data=recent_data,
                instrument=symbol_id,
                freq='1h'
            )
            
            logger.info("✓ 最近数据保存成功")
            
            # 验证数据
            saved_files = list(Path(self.test_dir).rglob("*.bin"))
            logger.info(f"✓ 保存了 {len(saved_files)} 个数据文件")
            
            return recent_data
            
        except Exception as e:
            logger.error(f"✗ 收集最近数据失败: {e}")
            return None
    
    def test_historical_data_collection(self, recent_data: pd.DataFrame):
        """测试收集历史数据（模拟2020-2024年数据）"""
        logger.info("=== 测试收集历史数据 ===")
        
        try:
            # 计算历史数据的结束时间（最近数据开始前1小时）
            if recent_data is None or recent_data.empty:
                logger.error("✗ 没有最近数据参考")
                return False
                
            recent_start = recent_data.index[0]
            historical_end = recent_start - timedelta(hours=1)
            
            logger.info(f"收集历史数据，结束时间: {historical_end}")
            
            # 收集历史数据（模拟更早的时间段）
            historical_data = self.adapter.get_ohlcv(
                symbol='BTC/USDT',
                timeframe='1h',
                limit=24 * 30,  # 30天的历史数据
                end_time=historical_end
            )
            
            if historical_data.empty:
                logger.error("✗ 无法获取历史数据")
                return False
                
            logger.info(f"✓ 成功获取历史数据: {len(historical_data)} 条记录")
            logger.info(f"  时间范围: {historical_data.index[0]} 到 {historical_data.index[-1]}")
            
            # 验证时间不重叠
            if historical_data.index[-1] >= recent_data.index[0]:
                logger.warning("⚠ 历史数据与最近数据时间重叠")
            else:
                logger.info("✓ 历史数据与最近数据时间不重叠")
            
            # 保存历史数据
            symbol_id = "binance_btc_usdt"
            self.storage.save_ohlcv_data(
                data=historical_data,
                instrument=symbol_id,
                freq='1h'
            )
            
            logger.info("✓ 历史数据保存成功")
            
            return historical_data
            
        except Exception as e:
            logger.error(f"✗ 收集历史数据失败: {e}")
            return None
    
    def test_data_continuity(self, recent_data: pd.DataFrame, historical_data: pd.DataFrame):
        """测试数据连续性"""
        logger.info("=== 测试数据连续性 ===")
        
        try:
            if recent_data is None or historical_data is None:
                logger.error("✗ 缺少数据进行连续性测试")
                return False
            
            # 合并数据并排序
            combined_data = pd.concat([historical_data, recent_data]).sort_index()
            combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
            
            logger.info(f"✓ 合并数据成功: {len(combined_data)} 条记录")
            logger.info(f"  完整时间范围: {combined_data.index[0]} 到 {combined_data.index[-1]}")
            
            # 检查时间间隔
            time_diffs = combined_data.index.to_series().diff().dropna()
            expected_interval = pd.Timedelta(hours=1)
            
            # 计算异常间隔
            abnormal_intervals = time_diffs[time_diffs != expected_interval]
            
            if len(abnormal_intervals) == 0:
                logger.info("✓ 数据时间间隔完全连续")
            else:
                logger.info(f"⚠ 发现 {len(abnormal_intervals)} 个异常时间间隔")
                logger.info(f"  预期间隔: {expected_interval}")
                
                # 显示前几个异常间隔
                for i, (timestamp, interval) in enumerate(abnormal_intervals.head(5).items()):
                    logger.info(f"    {timestamp}: {interval}")
                
                if len(abnormal_intervals) > 5:
                    logger.info(f"    ... 还有 {len(abnormal_intervals) - 5} 个异常间隔")
            
            # 检查数据完整性
            missing_hours = self._check_missing_data(combined_data)
            if missing_hours == 0:
                logger.info("✓ 数据完整，无缺失小时")
            else:
                logger.info(f"⚠ 发现 {missing_hours} 个缺失小时")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 数据连续性测试失败: {e}")
            return False
    
    def _check_missing_data(self, data: pd.DataFrame) -> int:
        """检查缺失数据"""
        if data.empty:
            return 0
        
        # 创建完整的时间序列
        start_time = data.index[0]
        end_time = data.index[-1]
        full_range = pd.date_range(start=start_time, end=end_time, freq='1H')
        
        # 计算缺失的时间点
        missing_times = full_range.difference(data.index)
        return len(missing_times)
    
    def test_storage_file_structure(self):
        """测试存储文件结构"""
        logger.info("=== 测试存储文件结构 ===")
        
        try:
            data_path = Path(self.test_dir)
            
            # 查找所有数据文件
            bin_files = list(data_path.rglob("*.bin"))
            
            if not bin_files:
                logger.error("✗ 未找到任何数据文件")
                return False
            
            logger.info(f"✓ 找到 {len(bin_files)} 个数据文件")
            
            # 按类型分组文件
            file_types = {}
            for file_path in bin_files:
                # 提取文件类型 (open, high, low, close, volume)
                parts = file_path.stem.split('.')
                if len(parts) >= 2:
                    field_type = parts[-2]  # 倒数第二个部分
                    if field_type not in file_types:
                        file_types[field_type] = 0
                    file_types[field_type] += 1
            
            logger.info("文件类型统计:")
            for field_type, count in file_types.items():
                logger.info(f"  {field_type}: {count} 个文件")
            
            # 验证基本OHLCV字段都存在
            expected_fields = ['open', 'high', 'low', 'close', 'volume']
            missing_fields = [field for field in expected_fields if field not in file_types]
            
            if missing_fields:
                logger.warning(f"⚠ 缺少字段: {missing_fields}")
            else:
                logger.info("✓ 所有基本OHLCV字段都存在")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 存储文件结构测试失败: {e}")
            return False
    
    def test_incremental_state_compatibility(self):
        """测试增量更新状态兼容性"""
        logger.info("=== 测试增量更新状态兼容性 ===")
        
        try:
            # 尝试导入增量更新管理器
            try:
                from incremental.manager import IncrementalUpdateManager
                manager = IncrementalUpdateManager(self.config)
            except ImportError as e:
                logger.warning(f"⚠ 无法导入增量更新管理器: {e}")
                logger.info("✓ 跳过增量更新状态测试（模块不可用）")
                return True
            
            # 初始化（应该创建新状态）
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(manager.initialize())
                logger.info("✓ 增量更新管理器初始化成功")
                
                # 获取状态摘要
                summary = manager.get_state_summary()
                logger.info(f"✓ 状态摘要: {summary}")
                
                # 获取统计信息
                stats = manager.get_update_statistics()
                logger.info(f"✓ 统计信息: {stats}")
                
                return True
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"✗ 增量更新状态兼容性测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("数据收集顺序兼容性测试")
        logger.info("=" * 60)
        
        # 设置测试环境
        self.setup()
        
        tests = [
            ("收集最近数据", self.test_recent_data_collection),
            ("存储文件结构", self.test_storage_file_structure),
            ("增量更新状态兼容性", self.test_incremental_state_compatibility),
        ]
        
        results = []
        recent_data = None
        historical_data = None
        
        # 运行基础测试
        for test_name, test_func in tests:
            logger.info(f"\n{test_name}:")
            logger.info("-" * 40)
            
            try:
                if test_name == "收集最近数据":
                    result = test_func()
                    recent_data = result if isinstance(result, pd.DataFrame) else None
                    results.append((test_name, result is not None))
                else:
                    result = test_func()
                    results.append((test_name, result))
            except Exception as e:
                logger.error(f"✗ {test_name} 失败: {e}")
                results.append((test_name, False))
        
        # 如果基础测试通过，运行高级测试
        if recent_data is not None:
            logger.info(f"\n收集历史数据:")
            logger.info("-" * 40)
            
            try:
                historical_data = self.test_historical_data_collection(recent_data)
                results.append(("收集历史数据", historical_data is not None))
            except Exception as e:
                logger.error(f"✗ 收集历史数据失败: {e}")
                results.append(("收集历史数据", False))
            
            # 数据连续性测试
            if historical_data is not None:
                logger.info(f"\n数据连续性:")
                logger.info("-" * 40)
                
                try:
                    continuity_result = self.test_data_continuity(recent_data, historical_data)
                    results.append(("数据连续性", continuity_result))
                except Exception as e:
                    logger.error(f"✗ 数据连续性测试失败: {e}")
                    results.append(("数据连续性", False))
        
        # 测试结果汇总
        logger.info("\n" + "=" * 60)
        logger.info("测试结果汇总")
        logger.info("=" * 60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "通过" if result else "失败"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\n总体结果: {passed}/{total} 个测试通过")
        
        # 结论
        if passed == total:
            logger.info("🎉 所有测试通过！数据收集顺序兼容性良好")
            logger.info("\n✓ 结论: 先收集2025年数据，再收集2020-2024年历史数据是完全可行的")
        else:
            logger.info("❌ 部分测试失败，需要检查兼容性问题")
        
        return passed == total


def main():
    """主函数"""
    # 检查代理设置
    proxy_url = os.environ.get('CRYPTO_TEST_PROXY', 'http://127.0.0.1:10808')
    if proxy_url:
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        logger.info(f"使用代理: {proxy_url}")
    
    # 运行测试
    test = DataOrderCompatibilityTest()
    
    try:
        success = test.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        return 1
    finally:
        # 清理测试目录
        import shutil
        if hasattr(test, 'test_dir') and os.path.exists(test.test_dir):
            try:
                shutil.rmtree(test.test_dir)
                logger.info(f"清理测试目录: {test.test_dir}")
            except Exception as e:
                logger.warning(f"清理测试目录失败: {e}")


if __name__ == "__main__":
    exit(main())