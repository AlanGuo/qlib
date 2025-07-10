# Timeframe 系统完整指南

## 📖 什么是 Timeframe？

Timeframe（时间框架）定义了数据的时间间隔，比如：
- `1min` - 每分钟的数据
- `1h` - 每小时的数据  
- `1d` - 每天的数据

这就像是给数据拍照的频率 - 拍得越频繁，时间间隔越短。

## 🎯 支持的格式

我们使用简单直观的格式：

```
1min   - 1分钟
5min   - 5分钟  
15min  - 15分钟
30min  - 30分钟
1h     - 1小时
1d     - 1天
1w     - 1周
```

**为什么选择这些格式？**
- 简单易懂，一看就明白
- 与 Qlib 项目其他部分保持一致
- 国际通用，便于团队协作

## 🚀 快速开始

### 第一个例子：收集 BTC 数据

#### 1. 配置文件（config.yaml）

```yaml
collection:
  timeframes:
    - 1h      # 收集1小时数据
    - 1d      # 收集1天数据
  symbols:
    - BTC/USDT
  exchanges:
    - binance
```

#### 2. 命令行使用

```bash
# 收集数据
python cli.py collect --timeframes 1h 1d --symbols BTC/USDT

# 验证数据
python cli.py validate --data-dir crypto_data/1h
```

#### 3. 查看结果

收集完成后，你会看到这样的文件结构：

```
crypto_data/
├── 1h/                          # 1小时数据
│   └── features/
│       └── binance_spot_btc_usdt/
│           ├── close.1h.bin     # 收盘价
│           ├── high.1h.bin      # 最高价
│           ├── low.1h.bin       # 最低价
│           ├── open.1h.bin      # 开盘价
│           └── volume.1h.bin    # 成交量
└── 1d/                          # 1天数据
    └── features/
        └── binance_spot_btc_usdt/
            ├── close.1d.bin
            ├── high.1d.bin
            ├── low.1d.bin
            ├── open.1d.bin
            └── volume.1d.bin
```

**注意**：目录名和文件名都使用相同的 timeframe 格式！

## 📋 使用场景指南

### 根据用途选择 Timeframe

```python
# 不同交易策略的推荐配置
strategies = {
    "高频交易": ["1min", "5min"],
    "日内交易": ["5min", "15min", "1h"], 
    "波段交易": ["1h", "1d"],
    "长期投资": ["1d", "1w"],
    "研究回测": ["1h", "1d", "1w"]
}
```

### 数据量考虑

| Timeframe | 一年数据量 | 建议用途 |
|-----------|------------|----------|
| 1min | 525,600 条 | 高频分析，短期策略 |
| 1h | 8,760 条 | 通用分析，大多数策略 |
| 1d | 365 条 | 长期趋势，历史回测 |

**新人建议**：从 `1d` 开始，数据量小，便于学习！

## 💻 编程接口

### 基本使用

```python
from timeframe_manager import TimeframeManager

# 创建管理器
manager = TimeframeManager()

# 验证 timeframe 是否支持
if manager.validate_timeframe("1h"):
    print("1h 是支持的格式")

# 获取多个 timeframes
timeframes = ["1h", "1d", "invalid"]
valid_ones = manager.validate_timeframes(timeframes)
print(f"有效的: {valid_ones}")  # 输出: ['1h', '1d']
```

### 数据收集

```python
from collector import CryptoCollector

# 收集器配置
collector = CryptoCollector(
    timeframes=["1h", "1d"],        # 要收集的时间间隔
    symbols=["BTC/USDT", "ETH/USDT"], # 交易对
    exchanges=["binance"]            # 交易所
)

# 开始收集
collector.collect_data()
```

### 数据读取

```python
from storage_manager import CryptoStorageManager

# 存储管理器
storage = CryptoStorageManager(data_dir="./crypto_data")

# 读取数据
btc_prices = storage.load_feature_data(
    instrument="binance_spot_btc_usdt",
    field="close",
    freq="1h"  # 读取1小时收盘价数据
)

print(f"读取了 {len(btc_prices)} 条价格数据")
```

## ⚙️ 交易所格式转换

系统自动处理不同交易所的格式要求：

```python
# Binance 转换
1h -> 1h      # 无变化
1d -> 1d      # 无变化

# OKX 转换  
1h -> 1h      # 保持小写，注意：不是 1H！
1d -> 1d      # 保持小写，注意：不是 1D！
```

**⚠️ 重要提醒：OKX 格式**
```
OKX 使用小写格式 (1h, 1d, 1w)，不是大写 (1H, 1D, 1W)！
这是一个常见的错误假设。使用错误格式会导致 API 错误。

正确: "1h", "1d", "1w"
错误: "1H", "1D", "1W"
```

**用户无需关心**: 这些转换在内部自动处理，用户始终使用统一格式。

## 🔧 配置模板

### 新手模板（basic.yaml）

```yaml
collection:
  timeframes:
    - 1d           # 只收集日数据，简单易懂
  exchanges:
    - binance      # 只用一个交易所
  symbols:
    - BTC/USDT     # 只收集 BTC
  fields:
    - open
    - high  
    - low
    - close
    - volume
```

### 研究模板（research.yaml）

```yaml
collection:
  timeframes:
    - 1h           # 小时数据用于详细分析
    - 1d           # 日数据用于趋势分析
    - 1w           # 周数据用于长期趋势
  exchanges:
    - binance
  symbols: []      # 可以添加你关心的交易对
  lookback_days: 365  # 收集一年数据
```

### 高频交易模板（high_frequency.yaml）

```yaml
collection:
  timeframes:
    - 1min
    - 5min
    - 15min
    - 1h
  exchanges:
    - binance
    - okx
  max_workers: 8      # 更多线程，提高收集速度
  rate_limit_delay: 0.05
```

## ❓ 常见问题

### Q1: 我应该选择哪个 timeframe？

**A**: 这取决于你的用途：
- **刚开始学习**：建议用 `1d`，数据量小，容易理解
- **做短期分析**：用 `1h` 或 `15min`
- **做长期研究**：用 `1d` 或 `1w`
- **高频交易**：用 `1min` 或 `5min`

### Q2: 可以同时收集多个 timeframe 吗？

**A**: 当然可以！而且推荐这样做：

```yaml
timeframes:
  - 1h
  - 1d
  - 1w
```

### Q3: 为什么文件名是 `close.1h.bin` 而不是 `close.60min.bin`？

**A**: 我们统一使用用户友好的格式（`1h`），让系统更容易理解和使用。内部的技术转换对用户是透明的。

### Q4: 如何知道数据收集是否成功？

**A**: 几种方法：

```bash
# 1. 使用验证命令
python cli.py validate --data-dir crypto_data

# 2. 检查文件大小
ls -lh crypto_data/1h/features/binance_spot_btc_usdt/

# 3. 查看日志输出
```

### Q5: 出现错误怎么办？

**A**: 常见错误和解决方法：

```
Error: Invalid timeframe 'hour'
解决：使用标准格式 '1h' 而不是 'hour'

Error: No data found for symbol
解决：检查交易对名称，确保格式正确（如 BTC/USDT）

Error: Exchange not supported  
解决：检查 exchanges 配置，确保拼写正确
```

## 🛠️ 故障排查

### 1. 文件未找到

```bash
# 检查目录结构
ls -la crypto_data/1h/features/

# 检查文件命名
ls -la crypto_data/1h/features/binance_spot_btc_usdt/
```

### 2. 格式验证失败

```python
from config.timeframes import validate_timeframe

# 检查格式是否支持
print(validate_timeframe("1h"))    # True
print(validate_timeframe("hour"))  # False
```

### 3. 数据质量问题

```bash
# 运行数据验证
python cli.py validate --data-dir crypto_data --verbose
```

## 📚 下一步学习

完成基础练习后，你可以：

1. **深入学习**：阅读 [技术参考](reference.md) 了解系统架构
2. **实际应用**：开始你的第一个交易策略分析
3. **参与开发**：查看项目的 GitHub 仓库，参与贡献

## 💡 实践练习

### 练习1：第一次数据收集

1. 复制 `basic.yaml` 模板
2. 修改 symbols 为你感兴趣的币种
3. 运行收集命令
4. 检查生成的文件

### 练习2：多时间间隔分析

1. 使用 `research.yaml` 模板
2. 收集 BTC 的 1h 和 1d 数据
3. 比较两种数据的条数差异
4. 思考：什么情况下用哪种数据？

### 练习3：数据验证

1. 收集一些数据
2. 运行验证命令
3. 理解验证报告的含义
4. 尝试修复任何发现的问题

## 🔗 获取帮助

如果遇到问题：

1. **查看日志**：大多数问题都能从日志中找到线索
2. **阅读文档**：查看技术参考文档
3. **示例代码**：参考 `examples/` 目录下的示例
4. **社区支持**：在 GitHub Issues 中提问
5. **联系维护者**：直接联系项目维护团队

---

**恭喜！你已经掌握了 timeframe 系统的完整知识。现在可以开始自己的加密货币数据分析之旅了！** 🚀