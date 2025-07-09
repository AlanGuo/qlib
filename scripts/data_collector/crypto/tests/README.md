# 测试规范

本项目遵循以下测试文件规范和结构：

## 测试文件命名规范

### 1. pytest测试文件
- **格式**: `test_*.py`
- **用途**: 单元测试、集成测试，通过pytest运行
- **示例**: `test_crypto_alpha_factors.py`, `test_decline_factors.py`

### 2. 可执行测试文件
- **格式**: `run_*.py`
- **用途**: 演示脚本、性能测试、端到端测试
- **示例**: `run_factor_demo.py`, `run_integration_test.py`

## 环境配置

### 虚拟环境
所有测试应在项目根目录的`.venv`虚拟环境中运行：
```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行pytest测试
pytest scripts/data_collector/crypto/tests/

# 运行单个测试文件
python scripts/data_collector/crypto/tests/run_integration_test.py
```

### 代理配置
如需访问外部API，设置代理环境变量：
```bash
export http_proxy=http://127.0.0.1:10808
export https_proxy=http://127.0.0.1:10808
export HTTP_PROXY=http://127.0.0.1:10808
export HTTPS_PROXY=http://127.0.0.1:10808
```

## 测试文件路径结构

```
scripts/data_collector/crypto/tests/
├── readme.md                          # 测试规范说明
├── conftest.py                        # pytest配置和fixtures
├── test_crypto_alpha_factors.py       # CryptoAlpha因子测试
├── test_decline_factors.py            # 跌幅因子单元测试
├── test_volume_factors.py             # 成交量因子单元测试
├── test_momentum_factors.py           # 动能因子单元测试
├── test_delisting_scenarios.py        # 下架场景处理测试
├── run_factor_integration_test.py     # 因子集成测试演示
├── run_factor_validation.py           # 因子有效性验证
└── data/                              # 测试数据
    ├── sample_crypto_data.json
    └── mock_data/
```

## 测试数据路径

### 真实测试数据
```bash
scripts/data_collector/crypto/test_data/stability_test/crypto_data/
```

### 模拟测试数据
```bash
scripts/data_collector/crypto/tests/data/
```

## 测试分类

### 1. 单元测试 (test_*.py)
- 测试单个函数或类的功能
- 使用模拟数据
- 执行快速
- 不依赖外部服务

### 2. 集成测试 (test_integration_*.py)
- 测试模块间协作
- 使用真实数据格式
- 可能需要qlib环境

### 3. 演示测试 (run_*.py)
- 端到端功能演示
- 性能测试
- 数据验证
- 可视化输出

### 4. 特殊场景测试
- **下架场景测试**: `test_delisting_scenarios.py`
  - 符号生命周期管理测试
  - 部分数据收集功能测试
  - CCXT错误处理测试
  - 增量更新中的下架感知测试

## 运行方式

### pytest测试
```bash
# 从项目根目录运行
cd /Users/alanguo/Projects/qlib

# 运行所有pytest测试
pytest scripts/data_collector/crypto/tests/ -v

# 运行特定测试文件
pytest scripts/data_collector/crypto/tests/test_crypto_alpha_factors.py -v

# 运行特定测试函数
pytest scripts/data_collector/crypto/tests/test_crypto_alpha_factors.py::test_factor_expressions -v

# 运行下架场景测试
pytest scripts/data_collector/crypto/tests/test_delisting_scenarios.py -v

# 运行带标记的测试
pytest scripts/data_collector/crypto/tests/ -m "not slow" -v
```

### 直接运行测试
```bash
# 从项目根目录运行
cd /Users/alanguo/Projects/qlib

# 运行演示脚本
python scripts/data_collector/crypto/tests/run_factor_integration_test.py

# 运行验证脚本
python scripts/data_collector/crypto/tests/run_factor_validation.py
```

## 测试标记

使用pytest标记分类测试：
```python
import pytest

@pytest.mark.fast
def test_quick_function():
    pass

@pytest.mark.slow  
def test_long_running_function():
    pass

@pytest.mark.integration
def test_system_integration():
    pass
```

## 注意事项

1. **依赖隔离**: 测试不应依赖特定的外部环境
2. **数据清理**: 测试后清理生成的临时文件
3. **错误处理**: 测试异常情况和边界条件
4. **文档更新**: 新增测试时更新此文档
5. **代码覆盖**: 确保关键功能有测试覆盖
6. **路径一致**: 所有测试从项目根目录运行，保持路径一致性