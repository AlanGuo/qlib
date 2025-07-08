# BTC Dominance Strategy (BtcDom2) - Examples and Configuration

这个目录包含BTC主导地位策略（BtcDom2）的完整实现示例、配置模板和工作流配置。

## 📁 文件说明

### 核心文件
- `btcdom2_strategy_example.py` - 策略使用示例和演示
- `btcdom2_strategy_configs.yaml` - 7种预设策略配置模板
- `workflow_config_btcdom2_strategy.yaml` - Qlib工作流配置文件

## 🚀 快速开始

### 1. 运行基础示例
```bash
# 进入示例目录
cd /Users/alanguo/Projects/qlib/examples/crypto/btcdom2

# 运行策略示例
python btcdom2_strategy_example.py
```

### 2. 使用Qlib工作流
```bash
# 从项目根目录运行
cd /Users/alanguo/Projects/qlib
qrun examples/crypto/btcdom2/workflow_config_btcdom2_strategy.yaml
```

### 3. 自定义配置
```python
from qlib.contrib.strategy.btcdom2_strategy import create_btcdom2_strategy

# 使用预设模板
strategy = create_btcdom2_strategy(
    rebalance_frequency="8h",
    num_short_positions=10,
    btc_spot_ratio=0.5,
    weighting_scheme="factor_weighted"
)
```

## 📊 配置模板详情

### 1. Conservative Strategy (保守型)
- **BTC配比**: 70%
- **再平衡频率**: 1天
- **权重方案**: 等权重
- **适用场景**: 稳定收益，低风险

### 2. Aggressive Strategy (激进型)  
- **BTC配比**: 30%
- **再平衡频率**: 4小时
- **权重方案**: 因子加权
- **适用场景**: 高收益，承受更高风险

### 3. Balanced Strategy (平衡型)
- **BTC配比**: 50%
- **再平衡频率**: 8小时
- **权重方案**: 波动率加权
- **适用场景**: 风险收益平衡

### 4. Research Strategy (研究型)
- **头寸数量**: 20个
- **因子类别**: 全部5个类别
- **适用场景**: 学术研究，策略开发

### 5. High-Frequency Strategy (高频型)
- **再平衡频率**: 4小时
- **流动性要求**: 严格($10M日交易量)
- **适用场景**: 短期交易，高频操作

### 6. Risk-Managed Strategy (风险管理型)
- **权重方案**: 风险平价
- **止损设置**: 保守(12%)
- **适用场景**: 注重风险控制

### 7. BTC Dominance Focus (BTC主导聚焦型)
- **BTC配比**: 65%
- **因子聚焦**: 跌幅+动能
- **适用场景**: BTC主导期市场

## 🔧 自定义配置

### 基础参数
```yaml
rebalance_frequency: "8h"          # 再平衡频率
factor_lookback_days: 14           # 因子回看天数
num_short_positions: 10            # 做空头寸数量
btc_spot_ratio: 0.5               # BTC现货配比
weighting_scheme: "factor_weighted" # 权重分配方案
```

### 高级参数
```yaml
# 风险管理
stop_loss_threshold: 0.15         # 个人止损阈值
portfolio_stop_loss: 0.10         # 组合止损阈值
max_drawdown_threshold: 0.20      # 最大回撤阈值

# 流动性过滤
min_daily_volume: 3000000         # 最小日交易量($)
max_spread_estimate: 2.0          # 最大价差估算(%)

# 因子权重
factor_weights:
  decline: 0.3                    # 跌幅因子权重
  volume: 0.25                    # 成交量因子权重
  momentum: 0.25                  # 动能因子权重
  funding: 0.2                    # 资金费率因子权重
```

## 🧪 测试和验证

### 运行完整示例
```bash
python btcdom2_strategy_example.py
```

示例包含：
- 基础策略创建
- 高级配置示例
- 策略对比分析
- 因子分析演示
- 工作流模拟
- 性能指标计算

### 验证配置
```python
from qlib.contrib.strategy.btcdom2_strategy import BtcDom2Strategy, BtcDom2Config

# 加载配置模板
import yaml
with open('btcdom2_strategy_configs.yaml', 'r') as f:
    configs = yaml.safe_load(f)

# 测试特定配置
config_params = configs['balanced_strategy']['config']
strategy = BtcDom2Strategy(BtcDom2Config(**config_params))
```

## 📈 预期性能

基于策略设计的预期指标：
- **年化收益率**: 15-30%
- **最大回撤**: <15%
- **夏普比率**: >1.5
- **胜率**: >55%
- **与BTC相关性**: <0.8

## 🔗 相关文档

- [BTC Dominance Strategy Guide](../../../docs/crypto/btcdom2_strategy_guide.md)
- [Crypto Factors Integration Guide](../../../docs/crypto/crypto_factors_integration_guide.md)
- [Strategy Implementation](../../../qlib/contrib/strategy/btcdom2_strategy.py)

## ⚠️ 使用注意事项

1. **数据要求**: 需要完整的加密货币OHLCV数据和资金费率数据
2. **计算资源**: 171个因子计算需要一定的计算资源
3. **风险提示**: 加密货币市场波动较大，请注意风险控制
4. **回测建议**: 建议先进行充分的历史回测再用于实盘

---

**最后更新**: 2025年1月  
**策略版本**: BtcDom2 v1.0  
**状态**: 生产就绪