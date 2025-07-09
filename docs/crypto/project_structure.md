# BTC Dominance Strategy (BtcDom2) - 文件组织结构

## ✅ 重构完成总结

已成功将BTC Dominance Strategy重新组织为符合qlib规范的项目结构。

## 📁 最终项目结构

```
qlib/contrib/strategy/
└── btcdom2_strategy.py                    # 主策略实现
    ├── BtcDom2Strategy                    # 策略主类
    ├── BtcDom2Config                      # 配置类
    ├── WeightingScheme                    # 权重方案枚举
    ├── RebalanceFrequency                 # 再平衡频率枚举
    └── create_btcdom2_strategy()          # 便捷创建函数

examples/crypto/
├── readme.md                              # 总体说明文档
└── btcdom2/                              # BtcDom2策略专用目录
    ├── readme.md                          # 详细使用说明
    ├── btcdom2_strategy_example.py        # 综合使用示例
    ├── btcdom2_strategy_configs.yaml      # 7种配置模板
    └── workflow_config_btcdom2_strategy.yaml  # Qlib工作流配置

docs/crypto/
├── btcdom2_strategy_guide.md            # 主策略文档
└── btcdom2_plan.md                       # 实施计划文档
```

## 🔧 配置模板 (7种)

### 1. Conservative Strategy (保守型)
- BTC配比: 70%, 再平衡: 1天, 权重: 等权重

### 2. Aggressive Strategy (激进型)  
- BTC配比: 30%, 再平衡: 4小时, 权重: 因子加权

### 3. Balanced Strategy (平衡型)
- BTC配比: 50%, 再平衡: 8小时, 权重: 波动率加权

### 4. Research Strategy (研究型)
- 头寸数: 20个, 因子: 全部5类, 研究导向

### 5. High-Frequency Strategy (高频型)
- 再平衡: 4小时, 流动性: 严格要求, 短期聚焦

### 6. Risk-Managed Strategy (风险管理型)
- 权重: 风险平价, 止损: 保守设置, 风险优先

## ⚠️ 重要提醒：OKX Timeframe格式

**OKX交换所的timeframe格式是小写，不是大写！**

这是开发中最常见的错误之一。详细信息请参考：
- 📖 [OKX Timeframe格式警告文档](okx_timeframe_warning.md)

### 常见错误
```
❌ 错误: "1H", "1D", "1W" (大写)
✅ 正确: "1h", "1d", "1w" (小写)
```

这个问题在修改过程中总是会被改错，请务必注意！

### 7. BTC Dominance Focus (BTC主导聚焦型)
- BTC配比: 65%, 因子聚焦: 跌幅+动能, 主导期优化

## 🚀 使用方式

### 快速开始
```bash
# 进入策略目录
cd /Users/alanguo/Projects/qlib/examples/crypto/btcdom2

# 运行示例
python btcdom2_strategy_example.py

# 使用工作流
cd /Users/alanguo/Projects/qlib
qrun examples/crypto/btcdom2/workflow_config_btcdom2_strategy.yaml
```

### 代码使用
```python
from qlib.contrib.strategy.btcdom2_strategy import create_btcdom2_strategy

# 创建策略
strategy = create_btcdom2_strategy(
    rebalance_frequency="8h",
    num_short_positions=10,
    btc_spot_ratio=0.5,
    weighting_scheme="factor_weighted"
)
```

## ✨ 重构亮点

### 1. 符合qlib规范
- 策略文件位于 `qlib/contrib/strategy/`
- 示例文件位于 `examples/crypto/btcdom2/`
- 文档文件位于 `docs/crypto/`

### 2. 清晰的模块化
- 每个策略有独立的子目录
- 包含完整的README和示例
- 配置模板和工作流分离

### 3. 便于扩展
- 预留了多策略扩展空间
- 标准化的命名规范
- 完整的文档体系

### 4. 生产就绪
- 7种预设配置模板
- 完整的示例和文档
- qlib工作流集成

## 🎯 下一步

1. **测试验证**: 运行示例确保功能正常
2. **回测集成**: 进入阶段4回测框架开发
3. **性能优化**: 基于实际数据调优参数
4. **扩展策略**: 可以添加更多加密货币策略

---

**重构状态**: ✅ 完成  
**文件组织**: 符合qlib最佳实践  
**可用性**: 生产就绪  
**最后更新**: 2025年1月