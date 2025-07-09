# Timeframe 使用示例

## 概述

本文档提供了重构后的 timeframe 系统的使用示例。新的设计遵循 Qlib 项目的统一模式，简化了使用方式，提高了一致性。

## 基本使用

### 1. 配置文件设置

```yaml
# config/default.yaml
collection:
  timeframes:
    - 1min    # 1分钟
    - 5min    # 5分钟
    - 15min   # 15分钟
    - 1h      # 1小时
    - 1d      # 1天
    - 1w      # 1周
```

### 2. 验证 Timeframe

```python
from config.timeframes import validate_timeframe, TIMEFRAME_MAPPING

# 验证单个timeframe
print(validate_timeframe("1h"))     # True
print(validate_timeframe("1d"))     # True
print(validate_timeframe("invalid")) # False

# 查看所有支持的timeframes
print("支持的timeframes:", list(TIMEFRAME_MAPPING.keys()))
# 输出: ['1min', '5min', '15min', '30min', '1h', '1d', '1w']
```

### 3. 交易所格式转换

```python
from config.timeframes import get_exchange_timeframe

# Binance 格式转换
binance_1h = get_exchange_timeframe("binance", "1h")
print(f"Binance 1h: {binance_1h}")  # 输出: 1h

binance_1min = get_exchange_timeframe("binance", "1min")
print(f"Binance 1min: {binance_1min}")  # 输出: 1m

# OKX 格式转换 (注意大小写)
okx_1h = get_exchange_timeframe("okx", "1h")
print(f"OKX 1h: {okx_1h}")  # 输出: 1H

okx_1d = get_exchange_timeframe("okx", "1d")
print(f"OKX 1d: {okx_1d}")  # 输出: 1D
```

### 4. 使用 TimeframeManager

```python
from timeframe_manager import TimeframeManager

# 创建管理器实例
manager = TimeframeManager()

# 验证timeframes列表
timeframes = ["1h", "1d", "invalid", "1w"]
valid_timeframes = manager.validate_timeframes(timeframes)
print(f"有效的timeframes: {valid_timeframes}")
# 输出: ['1h', '1d', '1w']

# 获取多个交易所的共同timeframes
exchanges = ["binance", "okx"]
common_timeframes = manager.get_common_timeframes(exchanges)
print(f"共同支持的timeframes: {common_timeframes}")
# 输出: ['1d', '1h', '1w', '15min', '5min', '30min', '1min'] (按优先级排序)
```

## 高级用法

### 1. 按类别获取 Timeframes

```python
from config.timeframes import SUPPORTED_TIMEFRAMES

# 按类别获取
minute_timeframes = SUPPORTED_TIMEFRAMES["minute"]
print(f"分钟级别: {minute_timeframes}")
# 输出: ['1min', '5min', '15min', '30min']

hour_timeframes = SUPPORTED_TIMEFRAMES["hour"]
print(f"小时级别: {hour_timeframes}")
# 输出: ['1h']

common_timeframes = SUPPORTED_TIMEFRAMES["common"]
print(f"常用timeframes: {common_timeframes}")
# 输出: ['1min', '5min', '15min', '1h', '1d']
```

### 2. 优先级排序

```python
from config.timeframes import sort_timeframes_by_priority, TIMEFRAME_PRIORITIES

# 按优先级排序
timeframes = ["1min", "1h", "1d", "5min", "1w"]
sorted_timeframes = sort_timeframes_by_priority(timeframes)
print(f"按优先级排序: {sorted_timeframes}")
# 输出: ['1d', '1h', '1w', '5min', '1min']

# 查看优先级
for tf in sorted_timeframes:
    priority = TIMEFRAME_PRIORITIES.get(tf, 0)
    print(f"{tf}: {priority}")
```

### 3. 时间计算

```python
from config.timeframes import get_timeframe_seconds

# 获取timeframe的秒数
print(f"1min = {get_timeframe_seconds('1min')} 秒")    # 60
print(f"1h = {get_timeframe_seconds('1h')} 秒")        # 3600
print(f"1d = {get_timeframe_seconds('1d')} 秒")        # 86400
print(f"1w = {get_timeframe_seconds('1w')} 秒")        # 604800
```

### 4. Qlib 存储API转换（严格边界限制）

```python
from config.timeframes import convert_for_qlib_internal

# ❌ 错误用法 - 用户代码不应该直接调用
# print(f"1h -> {convert_for_qlib_internal('1h')}")     # 请勿在用户代码中使用

# ✅ 正确用法 - 仅在storage_manager.py中使用
# 这个函数只在以下场景中使用：
# 1. storage_manager.py - 调用Qlib存储API时
# 2. qlib_data_generator.py - 创建Qlib存储对象时

# 用户代码应该始终使用原始格式
timeframe = "1h"  # 始终使用原始格式
print(f"用户应该看到: {timeframe}")  # 1h

# 警告：直接调用此函数可能触发边界违规警告
```

## 数据收集示例

### 1. 基本数据收集

```python
from collector import CryptoCollector

# 创建收集器
collector = CryptoCollector(
    exchanges=["binance"],
    timeframes=["1h", "1d"],
    symbols=["BTC/USDT", "ETH/USDT"]
)

# 收集数据
collector.collect_data()
```

### 2. 多交易所数据收集

```python
from collector import CryptoCollector
from timeframe_manager import TimeframeManager

# 使用manager获取共同支持的timeframes
manager = TimeframeManager()
exchanges = ["binance", "okx"]
timeframes = manager.get_common_timeframes(exchanges)

# 只使用高优先级的timeframes
high_priority_timeframes = timeframes[:3]  # 取前3个

collector = CryptoCollector(
    exchanges=exchanges,
    timeframes=high_priority_timeframes,
    symbols=["BTC/USDT", "ETH/USDT"]
)

collector.collect_data()
```

### 3. 高频数据收集

```python
from config.timeframes import SUPPORTED_TIMEFRAMES

# 使用分钟级别的timeframes
minute_timeframes = SUPPORTED_TIMEFRAMES["minute"]
print(f"收集分钟级别数据: {minute_timeframes}")

collector = CryptoCollector(
    exchanges=["binance"],
    timeframes=minute_timeframes,
    symbols=["BTC/USDT"],
    max_workers=8,  # 高频数据使用更多worker
    rate_limit_delay=0.05  # 更短的延迟
)

collector.collect_data()
```

## 存储结构示例

### 1. 目录结构

```
crypto_data/
├── 1min/
│   ├── features/
│   │   ├── binance_spot_btc_usdt/
│   │   │   ├── open.1min.bin
│   │   │   ├── high.1min.bin
│   │   │   ├── low.1min.bin
│   │   │   ├── close.1min.bin
│   │   │   └── volume.1min.bin
│   │   └── binance_spot_eth_usdt/
│   │       └── ...
│   ├── instruments/
│   │   └── crypto.txt
│   └── calendars/
│       └── crypto.txt
├── 1h/
│   ├── features/
│   │   └── ...
│   ├── instruments/
│   └── calendars/
└── 1d/
    ├── features/
    ├── instruments/
    └── calendars/
```

### 2. 存储管理

```python
from storage_manager import CryptoStorageManager

# 创建存储管理器
storage_manager = CryptoStorageManager(
    data_dir="./crypto_data",
    create_dirs=True
)

# 保存数据（内部会自动处理Qlib格式转换）
storage_manager.save_feature_data(
    data=price_data,
    instrument="binance_spot_btc_usdt",
    field="close",
    freq="1h"  # 使用原始格式，存储管理器内部处理转换
)

# 读取数据（内部会自动处理Qlib格式转换）
data = storage_manager.load_feature_data(
    instrument="binance_spot_btc_usdt",
    field="close",
    freq="1h"  # 使用原始格式，存储管理器内部处理转换
)

# 注意：convert_for_qlib_internal 在storage_manager内部使用
# 用户代码始终使用原始的 "1h" 格式
```

## 配置模板示例

### 1. 基础配置

```yaml
# templates/basic.yaml
collection:
  timeframes:
    - 1d
  exchanges:
    - binance
  symbols: []
  fields:
    - open
    - high
    - low
    - close
    - volume
```

### 2. 高频配置

```yaml
# templates/high_frequency.yaml
collection:
  timeframes:
    - 1min
    - 5min
    - 15min
    - 1h
  exchanges:
    - binance
    - okx
  max_workers: 8
  rate_limit_delay: 0.05
```

### 3. 研究配置

```yaml
# templates/research.yaml
collection:
  timeframes:
    - 15min
    - 1h
    - 1d
    - 1w
  exchanges:
    - binance
  lookback_days: 730  # 2年历史数据
  enable_extended_fields: true
  enable_risk_metrics: true
```

## 最佳实践

### 1. Timeframe 选择原则

```python
# 根据用途选择timeframe
use_cases = {
    "高频交易": ["1min", "5min"],
    "日内交易": ["5min", "15min", "1h"],
    "波段交易": ["1h", "1d"],
    "长期投资": ["1d", "1w"],
    "回测研究": ["1h", "1d", "1w"]
}
```

### 2. 性能优化

```python
from config.timeframes import sort_timeframes_by_priority

# 按优先级收集，确保重要数据先收集
timeframes = ["1min", "5min", "1h", "1d", "1w"]
sorted_timeframes = sort_timeframes_by_priority(timeframes)

# 分批收集
for timeframe in sorted_timeframes:
    print(f"收集 {timeframe} 数据...")
    # 收集逻辑
```

### 3. 错误处理

```python
from config.timeframes import validate_timeframe

def safe_collect_data(timeframes):
    """安全的数据收集函数"""
    valid_timeframes = []
    
    for tf in timeframes:
        if validate_timeframe(tf):
            valid_timeframes.append(tf)
        else:
            print(f"警告: 无效的timeframe {tf}")
    
    if not valid_timeframes:
        raise ValueError("没有有效的timeframes")
    
    return collect_data(valid_timeframes)
```

## 迁移指南

### 从旧版本迁移

```python
# 旧版本 (不推荐)
old_timeframes = ["day", "week", "1m"]

# 新版本 (推荐)
new_timeframes = ["1d", "1w", "1min"]

# 迁移函数
def migrate_timeframes(old_timeframes):
    migration_map = {
        "day": "1d",
        "week": "1w",
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min"
    }
    
    new_timeframes = []
    for tf in old_timeframes:
        if tf in migration_map:
            new_timeframes.append(migration_map[tf])
        elif validate_timeframe(tf):
            new_timeframes.append(tf)
        else:
            print(f"无法迁移timeframe: {tf}")
    
    return new_timeframes
```

## 常见问题

### Q: 为什么不支持 "1m" 格式？

A: 为了与 Qlib 项目中的 BaseCollector 保持一致，我们使用 "1min" 格式。这提高了整个项目的一致性。

### Q: 如何添加新的 timeframe？

A: 在 `TIMEFRAME_MAPPING` 中添加新的映射，并在 `EXCHANGE_TIMEFRAME_MAPPING` 中添加对应的交易所格式。

### Q: 目录名和文件名为什么一样？

A: 重构后统一使用相同的格式，避免了之前目录用 "1h" 文件用 "60min" 的混乱情况。

### Q: 为什么 `convert_for_qlib_internal` 有严格的使用边界？

A: 这个函数是Qlib存储API的实现细节，不应该泄露到系统的其他部分。严格的边界确保：
- 用户始终看到一致的格式
- 防止转换逻辑扩散到不相关的代码
- 保持系统的简洁性和可维护性

### Q: 如果我在错误的地方使用了 `convert_for_qlib_internal` 会发生什么？

A: 系统会发出边界违规警告，提示您应该使用原始格式。这有助于保持代码的一致性和正确性。

### Q: 什么时候需要调用 `convert_for_qlib_internal`？

A: **用户代码永远不应该直接调用这个函数**。它只在以下严格限制的场景中使用：

✅ **允许使用**：
- `storage_manager.py` - 调用Qlib存储API时
- `qlib_data_generator.py` - 创建Qlib存储对象时

❌ **禁止使用**：
- 用户代码、配置处理、数据收集、文件命名
- timeframe_manager.py、collector.py、exchange_adapters
- 任何用户可见的API

直接调用此函数会触发边界违规警告。

## 总结

重构后的 timeframe 系统提供了：

1. **统一的命名规范**：与 Qlib 项目其他部分保持一致
2. **简化的转换逻辑**：只在必要时进行格式转换
3. **清晰的目录结构**：目录名和文件名保持一致
4. **易于使用的API**：简单直观的接口设计

这些改进使得加密货币数据收集器更好地融入了 Qlib 生态系统，提高了开发效率和用户体验。