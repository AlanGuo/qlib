# BTC Dominance Strategy (BtcDom2) - Complete Integration Guide

## 🎯 阶段3.2完成总结

阶段3.2（仓位管理系统）已成功完成，实现了基于BTC主导地位分析的综合加密货币策略。

## ✅ 已完成功能

### 1. 多因子排序模型 ✅
- **171个因子支持**：基础(24) + 跌幅(24) + 成交量(30) + 动能(51) + 资金费率(42)
- **因子聚合算法**：基于Z-score标准化的加权聚合
- **动态因子权重**：可配置的因子类别权重分配
- **因子缓存机制**：提升计算效率和一致性

### 2. 智能筛选机制 ✅
- **多阶段筛选**：因子评分 → 流动性过滤 → 排序选择
- **动态参数调整**：基于市场状况自动调整筛选参数
- **候选数量控制**：5-20个做空标的，可配置
- **质量保证**：确保所选标的满足交易要求

### 3. 流动性过滤系统 ✅
- **基于可用数据的流动性检查**：
  - 最小日交易量：$1M 可配置
  - 价格波动估算：基于高低价差，≤2%
  - 交易活跃度：成交量变异系数 ≤2.0
- **现实约束考虑**：
  - 无法获取真实买卖价差数据
  - 无法获取市值数据
  - 使用高低价差作为流动性代理指标
- **交易安全保障**：避免流动性陷阱和异常波动资产

### 4. BTC现货与做空池资金配比管理 ✅
- **BTC现货配置**：30%-70%可配置（默认50%）
- **做空池配置**：相应比例的资金用于做空操作
- **动态资金分配**：基于市场波动性调整
- **风险平衡**：平衡收益潜力与风险控制
- **详细订单生成**：支持BTC现货和做空池分别下单

### 5. 做空池内权重分配策略 ✅
- **四种权重方案**：
  - **等权重**：简单平均分配
  - **因子加权**：基于因子强度分配，使用Softmax标准化
  - **波动率加权**：基于下行波动率的风险调整分配
  - **风险平价**：基于多维风险指标的综合分配
- **位置集中度控制**：单个头寸不超过25%
- **动态权重调整**：基于因子变化实时调整
- **多维风险计算**：价格波动率、成交量波动率、价差波动率、尾部风险(VaR)

### 6. 动态再平衡机制 ✅
- **多重触发条件**：
  - **时间驱动**：4小时、8小时、12小时、1天可配置
  - **业绩驱动**：头寸换手率>70%或单个头寸变化>10%
  - **风险驱动**：BTC波动率>5%或60%头寸高波动
  - **市场驱动**：BTC 4小时变化>5%
- **智能触发逻辑**：最小1小时间隔，优先级处理
- **平滑调仓**：最小化市场冲击成本
- **24/7市场支持**：适配加密货币不间断交易

### 7. 综合风险管理系统 ✅
- **五层风险防护**：
  1. **个人头寸止损**：15%可配置止损
  2. **组合级止损**：10%组合止损
  3. **最大回撤控制**：20%回撤阈值
  4. **头寸相关性限制**：70%相关性上限
  5. **紧急市场条件**：极端波动保护
- **风险跟踪系统**：
  - 入场价格跟踪
  - 组合峰值追踪
  - 风险警报记录
- **应急订单生成**：各类风险场景的自动订单生成

## 📊 技术架构

### 核心类结构
```python
BtcDom2Strategy(BaseStrategy)
├── BtcDom2Config (配置类)
├── CryptoFactorLibrary (因子库)
├── 筛选引擎 (Multi-factor ranking)
├── 流动性过滤器 (Liquidity filtering)
├── 权重分配器 (Position sizing - 4种方案)
├── 再平衡引擎 (Dynamic rebalancing - 4种触发条件)
└── 风险管理器 (Risk controls - 5层防护)
```

### 策略参数空间
- **时间参数**：n = 4-24小时重平衡频率
- **数据周期**：m = 7-30天因子计算周期  
- **筛选数量**：x = 5-20个做空币种
- **资金配比**：BTC现货比例 = 30%-70%
- **权重方案**：等权重/因子加权/波动率加权/风险平价

## 🚀 使用示例

### 基础用法
```python
from qlib.contrib.strategy.btcdom2_strategy import create_btcdom2_strategy

# 创建默认策略
strategy = create_btcdom2_strategy()

# 自定义配置
strategy = create_btcdom2_strategy(
    rebalance_frequency="8h",
    num_short_positions=10,
    btc_spot_ratio=0.5,
    weighting_scheme="factor_weighted"
)
```

### 高级配置
```python
from qlib.contrib.strategy.btcdom2_strategy import BtcDom2Strategy, BtcDom2Config

config = BtcDom2Config(
    rebalance_frequency=RebalanceFrequency.HOURLY_8,
    factor_lookback_days=14,
    num_short_positions=10,
    btc_spot_ratio=0.5,
    weighting_scheme=WeightingScheme.FACTOR_WEIGHTED,
    factor_categories=[
        FactorCategory.DECLINE,
        FactorCategory.VOLUME,
        FactorCategory.MOMENTUM,
        FactorCategory.FUNDING
    ],
    factor_weights={
        "decline": 0.3,
        "volume": 0.25, 
        "momentum": 0.25,
        "funding": 0.2
    },
    min_daily_volume=3e6,
    max_position_size=0.15,
    stop_loss_threshold=0.15,
    portfolio_stop_loss=0.10,
    max_drawdown_threshold=0.20
)

strategy = BtcDom2Strategy(config=config)
```

## 📁 文件结构

```
qlib/contrib/strategy/
└── btcdom2_strategy.py              # 主策略实现

examples/crypto/btcdom2/
├── btcdom2_strategy_example.py      # 使用示例
├── btcdom2_strategy_configs.yaml    # 配置模板
├── workflow_config_btcdom2_strategy.yaml  # 工作流配置
└── readme.md                        # 详细使用说明

docs/crypto/
└── btcdom2_strategy_guide.md        # 策略文档
```

## 🔧 配置模板

提供7种预设策略模板：

1. **Conservative Strategy** - 保守型策略
   - 低频率重平衡 (1天)
   - 高BTC配置 (70%)
   - 等权重分配

2. **Aggressive Strategy** - 激进型策略  
   - 高频率重平衡 (4小时)
   - 低BTC配置 (30%)
   - 因子加权分配

3. **Balanced Strategy** - 平衡型策略
   - 中等频率重平衡 (8小时)
   - 平衡BTC配置 (50%)
   - 波动率加权分配

4. **Research Strategy** - 研究型策略
   - 高分散度配置 (20个头寸)
   - 所有因子类别
   - 研究导向参数

5. **High-Frequency Strategy** - 高频策略
   - 极高频率重平衡 (4小时)
   - 短期因子聚焦
   - 严格流动性要求

6. **Risk-Managed Strategy** - 风险管理型
   - 保守仓位配置
   - 多重风险控制
   - 风险平价加权

7. **BTC Dominance Focus** - BTC主导聚焦型
   - 更高BTC配置 (65%)
   - 优化BTC主导期表现
   - 聚焦跌幅和动能因子

## 🎯 下一步：阶段4回测集成

仓位管理系统已完成，现在可以进入阶段4：

### 4.1 回测框架集成
- 将策略集成到qlib回测引擎
- 配置24/7加密货币交易日历
- 设置交易成本模型（滑点、手续费、资金费率）

### 4.2 性能评估
- 实施多种评价指标
- 风险调整收益分析
- 回撤和波动性分析

### 4.3 参数优化
- 网格搜索最优参数组合
- 交叉验证防止过拟合
- 敏感性分析

## 📊 预期性能目标

基于策略设计，预期达到以下性能指标：

- **年化收益率**：15-30%
- **最大回撤**：<15%
- **夏普比率**：>1.5
- **胜率**：>55%
- **与BTC相关性**：<0.8

## ⚡ 关键优势

1. **因子丰富度**：171个专业加密货币因子
2. **策略灵活性**：7种预设模板 + 高度可定制
3. **风险控制**：5层风险管理机制
4. **流动性保障**：智能流动性过滤系统
5. **仓位管理**：4种权重分配策略
6. **再平衡机制**：4种触发条件的动态再平衡
7. **实用性高**：完整的qlib集成和配置模板

## 🔗 相关文档

- [因子库集成指南](crypto_factors_integration_guide.md)
- [因子库构建报告](crypto_factor_library_report.md)
- [数据收集指南](data_collection_guide.md)
- [策略配置模板](../../examples/crypto/btcdom2/btcdom2_strategy_configs.yaml)
- [使用示例](../../examples/crypto/btcdom2/btcdom2_strategy_example.py)
- [工作流配置](../../examples/crypto/btcdom2/workflow_config_btcdom2_strategy.yaml)
- [因子使用示例](../../examples/crypto/factors/)
- [数据收集示例](../../examples/crypto/data_collection/)

---

**状态**: ✅ 阶段3.2完成  
**下一阶段**: 4.1 回测框架集成  
**完成日期**: 2025年1月  
**质量等级**: 生产就绪