# BTC Dominance Strategy (BtcDom2) - 回测执行计划

## 📋 当前状态
- ✅ 策略代码完成（BtcDom2Strategy + 171个因子）
- ✅ 数据收集器就绪
- ❌ **缺少历史数据** ← 当前关键任务
- ❌ 回测脚本未创建

## 🎯 执行目标
**回测时间范围**: 2020年1月1日 - 2024年12月31日（5年完整数据）
**预期完成时间**: 5-7个工作日

---

## 📊 第一阶段：历史数据收集（2-3天）

## ✅ **自定义模板配置**

**模板可用性确认**：CLI已支持自定义模板 `btcdom2_core` 和 `btcdom2`，通过文件模板系统自动发现。

**模板验证结果**：
- ✅ `btcdom2_core` - 8个核心币种专用配置
- ✅ `btcdom2` - 动态发现40-60个币种的完整配置
- ✅ 两个模板都已通过验证

---

### 1.0 前置准备和环境检查
```bash
# 在项目根目录执行所有命令
cd /Users/alanguo/Projects/qlib

# 检查crypto collector是否正常工作
python -m scripts.data_collector.crypto --help

# 查看可用的配置模板
python -m scripts.data_collector.crypto templates list

# 创建输出目录
mkdir -p crypto_data/{core,extended,futures}
```

**基于 BtcDom2 策略分析**：
- **重平衡频率**: 8小时（默认配置）
- **因子计算周期**: 14天回看期
- **做空币种数量**: 10个（可配置5-20个）
- **数据时间框架**: 1小时 + 1天
- **市场类型**: 现货（因子计算）+ 期货（做空执行 + 资金费率）

**具体数据需求**：
```yaml
时间范围: 2020-01-01 到 2024-12-31
交易所: Binance（专用）
时间框架: 1h, 1d
市场类型: spot, futures
币种筛选: 智能筛选40-60个币种（基于交易量）
筛选条件: 日交易量>500万USDT
特殊字段: funding_rate, open_interest（期货数据）
```

### 1.2 智能币种筛选策略

**筛选原则**：
- ✅ **核心币种保证**：BTC/USDT, ETH/USDT, LTC/USDT, XRP/USDT, BCH/USDT, TRX/USDT, DOGE/USDT（2020年确定存在）
- ✅ **现货交易量过滤**：现货日交易量 > 500万USDT（适应2020年市场规模）
- ✅ **候选池规模**：40-60个币种（为10个做空位置提供4-6倍选择空间）

**动态筛选逻辑**：
```yaml
筛选策略: 基于现货交易量的智能筛选
核心币种: 8个（确保基础）
扩展币种: 32-52个（动态发现）
总计: 40-60个币种
交易量标准: 现货市场日均交易量≥500万USDT
交易量排名: 或选择现货交易量排名前60位
数据源: 现货市场OHLCV数据
```

### 1.3 分步数据收集执行命令

**自定义模板策略（推荐方案）**

**步骤1: 收集核心币种（确保基础数据）**
```bash
# 在项目根目录执行，使用模块化调用
cd /Users/alanguo/Projects/qlib

# 使用核心币种专用配置收集8个基础币种
python -m scripts.data_collector.crypto collect \
    --template btcdom2_core \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --output-dir ./crypto_data/core
```

**步骤2: 收集扩展币种（动态筛选）**
```bash
# 使用配置文件自动筛选40-60个币种（基于现货交易量）
python -m scripts.data_collector.crypto collect \
    --template btcdom2 \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --output-dir ./crypto_data/extended
```

**配置文件说明**：
- 📁 **btcdom2_core.yaml**：8个核心币种（BTC/USDT, ETH/USDT, LTC/USDT, XRP/USDT, BCH/USDT, TRX/USDT, DOGE/USDT）
- 📁 **btcdom2.yaml**：动态筛选扩展币种（40-60个，基于交易量排序）

**实现效果**：
- ✅ **核心币种保证**：使用专用配置确保8个基础币种
- ✅ **动态扩展**：自动筛选40-60个高交易量币种
- ✅ **现货交易量过滤**：`min_volume_24h: 5000000`
- ✅ **配置化管理**：两个template便于维护和修改
- ✅ **零代码修改**：使用现有功能组合实现

**期货数据说明**：
`btcdom2` 模板已包含期货数据收集配置，包括 `funding_rate` 和 `open_interest` 字段，无需单独收集。

---

## 🚀 **一键执行脚本**

**使用自定义模板的简化执行脚本**：

```bash
# 创建一键脚本
cat > collect_btcdom2_data.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 BtcDom2 策略数据收集开始..."

# 进入项目根目录
cd /Users/alanguo/Projects/qlib

# 创建输出目录
mkdir -p crypto_data/{core,extended}

# 收集核心币种
echo "📊 步骤 1/3: 收集核心币种..."
python -m scripts.data_collector.crypto collect --template btcdom2_core --start-date 2020-01-01 --end-date 2024-12-31 --output-dir ./crypto_data/core

# 收集扩展币种（包含期货数据）
echo "🔍 步骤 2/3: 收集扩展币种和期货数据..."
python -m scripts.data_collector.crypto collect --template btcdom2 --start-date 2020-01-01 --end-date 2024-12-31 --output-dir ./crypto_data/extended

# 数据验证
echo "✅ 步骤 3/3: 数据验证..."
python -m scripts.data_collector.crypto validate --data-dir ./crypto_data/core --verbose

echo "🎉 BtcDom2 数据收集完成！"
echo "📊 数据统计信息："
python -m scripts.data_collector.crypto info --output-dir ./crypto_data
EOF

# 赋予执行权限
chmod +x collect_btcdom2_data.sh

# 执行数据收集
./collect_btcdom2_data.sh
```

**优点**：
- ✅ **使用专门配置**：完全匹配策略需求
- ✅ **简化流程**：3步完成所有数据收集
- ✅ **自动验证**：内置数据质量检查

---

### 1.4 数据验证和质量检查
```bash
# 验证数据完整性和质量
python -m scripts.data_collector.crypto validate \
    --data-dir ./crypto_data/core \
    --verbose

# 检查数据统计信息
python -m scripts.data_collector.crypto info \
    --output-dir ./crypto_data

# 查看可用的配置模板
python -m scripts.data_collector.crypto templates list
```

**验证检查项**：
- ✅ 核心币种数据完整性（自动检查核心币种）
- ✅ 总币种数量（通过配置文件控制）
- ✅ 数据缺失率（通过验证框架检查）
- ✅ 交易量数据一致性（VolumeValidator）
- ✅ 时间序列连续性（TimeSeriesValidator）
- ✅ 期货数据资金费率完整性（字段验证）

---

## 🚀 第二阶段：回测脚本开发（1-2天）

### 2.1 创建回测脚本
**文件**: `backtest/crypto/btcdom2/backtest.py`

### 2.2 配置 Qlib 数据源
```python
# 配置 Qlib 使用我们收集的加密货币数据
import qlib
qlib.init(
    provider_uri="./crypto_data",
    region="crypto"
)
```

### 2.3 回测参数配置
```python
# BtcDom2策略回测配置
BACKTEST_CONFIG = {
    "start_time": "2020-01-01",
    "end_time": "2024-12-31",
    "account": 1000000,  # 100万USDT初始资金
    "benchmark": "BTC/USDT",  # 以BTC为基准
    "exchange_kwargs": {
        "freq": "1h",  # 1小时频率（匹配8h重平衡）
        "limit_threshold": 0.095,  # 涨跌停限制
        "deal_price": "close",  # 成交价格
        "open_cost": 0.0015,  # 开仓手续费 0.15%
        "close_cost": 0.0015,  # 平仓手续费 0.15%
        "min_cost": 1,  # 最小手续费 1 USDT
        "trade_unit": "USDT",  # 交易单位
        "support_short": True,  # 支持做空
    }
}

# BtcDom2策略参数
STRATEGY_CONFIG = {
    "rebalance_frequency": "8h",  # 8小时重平衡
    "num_short_positions": 10,   # 做空10个币种
    "btc_spot_ratio": 0.5,       # 50% BTC现货
    "short_pool_ratio": 0.5,     # 50% 做空池
    "weighting_scheme": "factor_weighted",  # 因子加权
    "factor_lookback_days": 14,   # 14天因子回看期
    "min_daily_volume": 5000000,  # 最小日交易量500万USDT
    "max_position_size": 0.15,    # 单币种最大仓位15%
    "stop_loss_threshold": 0.15,  # 止损阈值15%
}
```

---

## 📈 第三阶段：回测执行（1天）

### 3.1 基础回测
```bash
cd /Users/alanguo/Projects/qlib

# 首先创建回测脚本目录
mkdir -p backtest/crypto/btcdom2

# 运行基础回测
python backtest/crypto/btcdom2/backtest.py \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --output-dir ./backtest_results/btcdom2_default \
    --data-dir ./crypto_data
```

### 3.2 参数敏感性测试
```bash
# 测试不同重平衡频率
python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --rebalance-frequency 4h \
    --output-dir ./backtest_results/btcdom2_4h

python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --rebalance-frequency 12h \
    --output-dir ./backtest_results/btcdom2_12h

# 测试不同做空币种数量
python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --num-short-positions 5 \
    --output-dir ./backtest_results/btcdom2_short5

python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --num-short-positions 15 \
    --output-dir ./backtest_results/btcdom2_short15

# 测试不同BTC配比
python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --btc-spot-ratio 0.3 \
    --output-dir ./backtest_results/btcdom2_btc30

python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --btc-spot-ratio 0.7 \
    --output-dir ./backtest_results/btcdom2_btc70

# 测试不同候选池大小（如果收集了更多币种）
python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --universe-size 30 \
    --output-dir ./backtest_results/btcdom2_universe30

python backtest/crypto/btcdom2/btcdom2_backtest.py \
    --universe-size 60 \
    --output-dir ./backtest_results/btcdom2_universe60
```

---

## 📊 第四阶段：结果分析（1-2天）

### 4.1 性能指标分析
- 年化收益率
- 最大回撤
- 夏普比率
- 胜率
- 与BTC相关性

### 4.2 风险分析
- VaR计算
- 最大单日损失
- 连续亏损期分析

### 4.3 策略优化建议
- 参数调优方向
- 风险控制改进
- 因子权重优化

---

## ⚠️ 注意事项

1. **数据收集时间**: 5年历史数据收集可能需要6-12小时
2. **存储空间**: 预计需要10-20GB存储空间
3. **网络稳定性**: 确保网络连接稳定，避免数据收集中断
4. **API限制**: 注意交易所API调用频率限制
5. **数据质量**: 收集完成后务必验证数据完整性

---

## 🎯 成功标准

- [ ] 收集到2020-2024年完整的50个币种数据
- [ ] 数据验证通过，缺失率<5%
- [ ] 回测脚本成功运行
- [ ] 获得完整的5年回测结果
- [ ] 策略年化收益率>15%，最大回撤<20%

---

**预计总耗时**: 5-7个工作日
**关键里程碑**: 数据收集完成 → 回测脚本就绪 → 首次回测成功
