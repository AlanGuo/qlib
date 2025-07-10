# 新人测试完整指南 - 从0开始

> 🎯 本指南专为项目新人设计，确保任何人都能从零开始完成所有测试

## 🚀 第一步：环境准备

### 1.1 确认项目位置
```bash
# 首先确认你在正确的项目根目录
cd /Users/alanguo/Projects/qlib
pwd
# 应该显示: /Users/alanguo/Projects/qlib
```

### 1.2 激活虚拟环境
```bash
# 激活项目虚拟环境
source .venv/bin/activate

# 验证虚拟环境是否激活（命令行前缀应显示(.venv)）
which python
# 应该显示: /Users/alanguo/Projects/qlib/.venv/bin/python
```

### 1.3 进入测试目录
```bash
# 进入测试目录（所有测试都在这里运行）
cd scripts/data_collector/crypto/tests
pwd
# 应该显示: /Users/alanguo/Projects/qlib/scripts/data_collector/crypto/tests
```

## 🎯 最简单方式：一键运行所有测试

### 推荐选项1：运行所有测试
```bash
# 运行所有测试套件（包括实时测试）
python run_all_tests.py
```

### 推荐选项2：快速测试
```bash
# 只运行快速测试，跳过慢速测试
python run_all_tests.py --fast
```

### 推荐选项3：无网络测试
```bash
# 跳过实时测试（当网络有问题时）
python run_all_tests.py --no-live
```

### 查看测试计划
```bash
# 只查看会运行哪些测试，不实际执行
python run_all_tests.py --summary
```

## 📊 一键脚本功能说明

运行 `python run_all_tests.py` 会：

1. **自动设置环境** - 配置代理、检查目录
2. **按顺序运行** - 模拟数据 → 单元测试 → 集成测试 → 性能测试 → 实时测试
3. **生成报告** - 显示详细结果和保存测试报告文件
4. **智能超时** - 不同测试有不同的超时时间
5. **错误处理** - 即使某个测试失败，也会继续运行其他测试

**测试报告文件** 会自动保存为 `test_report_YYYYMMDD_HHMMSS.txt`

---

## 📁 手动分步测试（高级用户）

## 📁 测试目录结构

```
tests/ (当前目录)
├── unit/                     # 单元测试（包含模拟数据测试，无网络依赖）
├── integration/             # 集成测试 (多组件协作)
├── live/                    # 实时API测试 (需要网络代理)
├── performance/             # 性能和压力测试
├── runners/                 # 可执行测试脚本
├── config/                  # 配置文件
├── outputs/                 # 测试输出文件
└── docs/                    # 文档
```

## 🎯 第二步：新人测试路径（按顺序执行）

### 2.1 开始测试 - 单元测试（最简单，包含模拟数据，无网络依赖）

```bash
# ⚠️ 确保你在测试目录：/Users/alanguo/Projects/qlib/scripts/data_collector/crypto/tests
pwd

# 运行所有单元测试（包含模拟数据测试）
pytest unit/ -v

# 如果上面失败，试试单个文件
pytest unit/test_crypto_alpha_factors.py -v
```

**预期结果**: 应该看到测试运行并显示结果

### 2.2 单元测试（快速功能测试）

```bash
# 运行所有单元测试
pytest unit/ -v

# 如果有失败，可以运行单个文件调试
pytest unit/test_calendar_instruments.py -v
```

### 2.3 集成测试（组件协作测试）

```bash
# 运行集成测试
pytest integration/ -v

# 运行不包含慢速测试的版本
pytest integration/ -v -m "not slow"
```

### 2.4 性能测试（可能较慢）

```bash
# 运行性能测试
pytest performance/ -v

# 只运行快速性能测试
pytest performance/ -v -m "not slow"
```

### 2.5 实时API测试（需要网络代理）

**⚠️ 重要：实时测试需要代理配置**

```bash
# 第一步：配置代理环境变量
export http_proxy=http://127.0.0.1:10808
export https_proxy=http://127.0.0.1:10808
export HTTP_PROXY=http://127.0.0.1:10808
export HTTPS_PROXY=http://127.0.0.1:10808

# 第二步：验证代理是否工作
curl -I https://api.binance.com/api/v3/ping

# 第三步：运行实时测试
pytest live/ -v -m live

# 如果网络有问题，可以跳过实时测试
pytest live/ -v -m "not live"
```

## 🛠️ 第三步：可执行脚本测试

**⚠️ 注意：这些脚本需要从crypto目录运行，不是tests目录**

```bash
# 返回到crypto目录
cd ..
pwd
# 应该显示: /Users/alanguo/Projects/qlib/scripts/data_collector/crypto

# 运行综合测试脚本
python tests/runners/run_comprehensive_live_test.py

# 运行验证脚本
python tests/runners/run_validation_tests.py

# 运行增量更新测试
python tests/runners/run_incremental_live.py

# 返回测试目录继续其他测试
cd tests
```

## 📊 第四步：验证所有测试完成

```bash
# 确保在测试目录
cd /Users/alanguo/Projects/qlib/scripts/data_collector/crypto/tests

# 运行完整测试套件总结
echo "=== 测试完成情况汇总 ==="
echo "1. 单元测试（含模拟数据）:" && pytest unit/ --collect-only -q | wc -l
echo "2. 集成测试:" && pytest integration/ --collect-only -q | wc -l
echo "3. 性能测试:" && pytest performance/ --collect-only -q | wc -l
echo "4. 实时测试:" && pytest live/ --collect-only -q | wc -l
```

## ❗ 常见问题和解决方案

### Q1: 虚拟环境没有激活
**错误**: `command not found: pytest` 或 `ModuleNotFoundError`
```bash
# 解决方案：激活虚拟环境
cd /Users/alanguo/Projects/qlib
source .venv/bin/activate
# 验证：命令行前缀应显示 (.venv)
```

### Q2: 在错误的目录运行测试
**错误**: `No tests ran` 或 `collection failed`
```bash
# 解决方案：确保在正确目录
cd /Users/alanguo/Projects/qlib/scripts/data_collector/crypto/tests
ls -la  # 应该看到 unit/ mock/ live/ 等目录
```

### Q3: 代理配置问题
**错误**: `requests.exceptions.ConnectionError` 或 `Network is unreachable`
```bash
# 解决方案：配置代理
export https_proxy=http://127.0.0.1:10808
curl -I https://api.binance.com/api/v3/ping  # 验证代理工作
```

### Q4: 导入错误（Import Errors）
**错误**: `ModuleNotFoundError: No module named 'config'`
```bash
# 这是已知问题，部分测试在重组后需要修复导入路径
# 暂时可以跳过失败的测试，继续其他测试
pytest unit/ -v --tb=short  # 查看简短错误信息
```

### Q5: 权限问题
**错误**: `Permission denied`
```bash
# 解决方案：检查文件权限
chmod +x runners/*.py
```

## 🎯 测试类别说明

### 测试标记（Markers）
- `@pytest.mark.fast` - 快速单元测试 (< 1秒)
- `@pytest.mark.slow` - 长时间运行测试 (> 10秒)
- `@pytest.mark.live` - 需要实时API连接的测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.validation` - 数据验证测试
- `@pytest.mark.smoke` - 快速冒烟测试

### 按标记运行测试
```bash
# 只运行快速测试
pytest -v -m fast

# 排除慢速测试
pytest -v -m "not slow"

# 只运行实时测试（需要代理）
pytest -v -m live

# 运行集成测试但排除慢速
pytest -v -m "integration and not slow"
```

## 📋 完整测试检查清单

**新人完成所有测试的检查清单：**

- [ ] ✅ 环境准备完成（虚拟环境激活，在正确目录）
- [ ] ✅ 单元测试通过（含模拟数据）(`pytest unit/ -v`)
- [ ] ✅ 集成测试通过 (`pytest integration/ -v`)
- [ ] ✅ 性能测试通过 (`pytest performance/ -v`)
- [ ] ✅ 代理配置完成
- [ ] ✅ 实时测试通过 (`pytest live/ -v -m live`)
- [ ] ✅ 可执行脚本测试完成 (从crypto目录运行)
- [ ] ✅ 所有测试汇总检查完成

## 🆘 获取帮助

如果遇到问题：
1. **检查错误信息**: 仔细阅读pytest的错误输出
2. **查看日志**: `cat tests.log` (如果存在)
3. **简化测试**: 从单个文件开始，逐步扩大范围
4. **环境重置**: 重新激活虚拟环境，确认目录位置
5. **跳过问题测试**: 使用 `-k "not problematic_test"` 跳过有问题的测试