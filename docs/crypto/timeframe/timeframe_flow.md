# Timeframe 设计架构文档

## 概述

本文档详细说明了加密货币数据收集模块中 timeframe 的设计架构。经过重构，现在的设计遵循 Qlib 项目中其他数据收集器的统一模式，简化了转换逻辑，提高了一致性和可维护性。

## 架构流程图

```mermaid
graph TD
    A[用户配置] -->|"1h, 1d, 1w"| B[TimeframeManager]
    B -->|验证| C[标准格式]
    C -->|"1h → 1h (Binance)<br/>1h → 1H (OKX)"| D[交易所适配器]
    D -->|API调用| E[交易所API]
    E -->|原始数据| F[数据验证器]
    F -->|标准化数据| G[存储管理器]
    G -->|"1h → 1h (目录)<br/>1h → 1h (文件)"| H[Qlib存储]

    subgraph "配置层"
        A1[default.yaml<br/>timeframes: [1h, 1d]]
        A2[TIMEFRAME_MAPPING<br/>"1h": "1h"]
    end

    subgraph "转换层"
        B1[TimeframeManager<br/>简单验证]
        B2[EXCHANGE_TIMEFRAME_MAPPING<br/>交易所格式转换]
        B3[convert_for_qlib_internal<br/>仅限存储API使用]
    end

    subgraph "存储层"
        G1[目录结构<br/>data_dir/1h/features/]
        G2[文件命名<br/>field.1h.bin]
        G3[Qlib存储API<br/>1h→60min (严格限制)]
    end

    A --> A1
    A1 --> A2
    B --> B1
    B1 --> B2
    B2 --> B3
    G --> G1
    G1 --> G2
    G2 --> G3
```

## 重构后的简化设计

### 1. 统一的命名规范

**遵循现有 Qlib 项目模式**:
- 使用与其他数据收集器一致的命名规范
- 采用简单直观的格式：`1min`, `5min`, `15min`, `30min`, `1h`, `1d`, `1w`

```python
# 统一的时间格式标准
TIMEFRAME_MAPPING = {
    "1min": "1min",
    "5min": "5min",
    "15min": "15min", 
    "30min": "30min",
    "1h": "1h",      # 遵循现有模式
    "1d": "1d",      # 与BaseCollector一致
    "1w": "1w",      # 新增但保持一致性
}
```

### 2. 简化的交易所转换

**参考 Yahoo 收集器模式**:
- 简单的字符串映射，无复杂逻辑
- 类似 `interval = "1m" if interval in ["1m", "1min"] else interval`

```python
# 简化的交易所映射
EXCHANGE_TIMEFRAME_MAPPING = {
    "binance": {
        "1min": "1m",
        "5min": "5m",
        "1h": "1h",
        "1d": "1d",
        "1w": "1w",
    },
    "okx": {
        "1min": "1m",
        "5min": "5m", 
        "1h": "1H",    # 仅大小写不同
        "1d": "1D",
        "1w": "1W",
    },
}
```

### 3. 统一的存储结构

**直接使用 timeframe 作为目录名**:
- 与其他数据收集器保持一致
- 目录结构：`data_dir/1h/features/`
- 文件命名：`field.1h.bin`

```python
# 统一的存储结构
def create_storage_structure(self):
    for timeframe in TIMEFRAME_MAPPING.keys():
        timeframe_dir = self.data_dir / timeframe  # 直接使用 timeframe
        timeframe_dir.mkdir(exist_ok=True)
        (timeframe_dir / "features").mkdir(exist_ok=True)
        (timeframe_dir / "instruments").mkdir(exist_ok=True)
        (timeframe_dir / "calendars").mkdir(exist_ok=True)
```

### 4. 最小化的 Qlib 转换

**仅在必要时转换**:
- 只有 `1h → 60min` 需要转换（Qlib 存储API要求）
- 其他格式保持原样
- 严格限制使用边界，防止误用

```python
def convert_for_qlib_internal(timeframe: str) -> str:
    """
    仅在 Qlib 存储API 调用时使用
    
    严格使用边界：
    - 允许：storage_manager.py, qlib_data_generator.py
    - 禁止：用户API、数据收集、文件命名、配置处理
    """
    if timeframe == "1h":
        return "60min"  # Qlib 存储API要求
    return timeframe    # 其他格式保持不变
```

## 详细的值转换流程

### 1. 用户配置 → 标准格式

**输入**: `["1h", "1d", "1w"]`
**输出**: `["1h", "1d", "1w"]`
**转换**: 直接使用，无需转换

### 2. 标准格式 → 交易所格式

**Binance**: 
- `1h → 1h` (无变化)
- `1d → 1d` (无变化)

**OKX**:
- `1h → 1H` (仅大小写)
- `1d → 1D` (仅大小写)

### 3. 存储管理

**目录结构**: `data_dir/1h/features/`
**文件命名**: `close.1h.bin`
**一致性**: 目录名和文件名都使用相同格式

### 4. Qlib 内部转换

**仅限内部使用**: `1h → 60min`
**其他格式**: 保持不变
**使用场景**: 仅在调用 Qlib 存储 API 时（严格边界限制）

## 与现有项目的一致性对比

| 组件 | 现有项目 | 加密货币收集器 | 一致性 |
|------|----------|---------------|--------|
| **基础常量** | `INTERVAL_1min = "1min"` | `"1min"` | ✅ 一致 |
| **基础常量** | `INTERVAL_1d = "1d"` | `"1d"` | ✅ 一致 |
| **转换逻辑** | 简单字符串替换 | 简单映射 | ✅ 一致 |
| **目录结构** | 直接使用 interval | 直接使用 timeframe | ✅ 一致 |
| **文件命名** | 使用 interval 格式 | 使用 timeframe 格式 | ✅ 一致 |

## 关键转换点总结

| 阶段 | 输入格式 | 输出格式 | 转换方式 | 用途 |
|------|----------|----------|----------|------|
| **用户配置** | `"1h"` | `"1h"` | 直接使用 | 配置文件 |
| **格式验证** | `"1h"` | `"1h"` | 验证有效性 | 标准格式 |
| **交易所API** | `"1h"` | `"1h"/"1H"` | 简单映射 | API调用 |
| **目录创建** | `"1h"` | `"1h"` | 直接使用 | 文件夹名 |
| **文件命名** | `"1h"` | `"1h"` | 直接使用 | 文件名 |
| **Qlib存储API** | `"1h"` | `"60min"` | 严格边界限制 | 存储API专用 |

## 设计优势

### 1. **简化复杂性**
- 移除了多层转换逻辑
- 减少了配置复杂性
- 降低了维护成本

### 2. **提高一致性**
- 与现有 Qlib 项目模式保持一致
- 目录和文件命名统一
- 开发者体验更好

### 3. **增强可维护性**
- 代码逻辑更清晰
- 错误定位更容易
- 扩展新 timeframe 更简单

### 4. **保持兼容性**
- 与 Qlib 核心功能兼容
- 与其他数据收集器兼容
- 向后兼容现有配置

## 使用示例

### 配置文件 (default.yaml)
```yaml
timeframes:
  - 1h    # 1小时
  - 1d    # 1天
  - 1w    # 1周
```

### 目录结构
```
data_dir/
├── 1h/
│   ├── features/
│   ├── instruments/
│   └── calendars/
├── 1d/
│   ├── features/
│   ├── instruments/
│   └── calendars/
└── 1w/
    ├── features/
    ├── instruments/
    └── calendars/
```

### 文件命名
```
data_dir/1h/features/binance_spot_btc_usdt/
├── close.1h.bin     # 使用原始格式，不转换
├── high.1h.bin      # 使用原始格式，不转换
├── low.1h.bin       # 使用原始格式，不转换
├── open.1h.bin      # 使用原始格式，不转换
└── volume.1h.bin    # 使用原始格式，不转换
```

## 相关文件

- **核心配置**: `scripts/data_collector/crypto/config/timeframes.py`
- **管理器**: `scripts/data_collector/crypto/timeframe_manager.py`
- **存储管理**: `scripts/data_collector/crypto/storage_manager.py`
- **数据生成**: `scripts/data_collector/crypto/qlib_data_generator.py`
- **模板配置**: `scripts/data_collector/crypto/config/templates/default.yaml`

## 总结

重构后的 timeframe 设计显著简化了系统架构，提高了与现有 Qlib 项目的一致性。主要改进包括：

1. **统一命名规范**：采用与其他数据收集器一致的命名方式
2. **简化转换逻辑**：参考 Yahoo 和 BaoStock 收集器的简单转换模式
3. **统一存储结构**：目录和文件命名保持一致
4. **最小化转换**：仅在必要时进行格式转换

这种设计使得加密货币数据收集器更好地融入 Qlib 生态系统，提高了可维护性和开发效率。