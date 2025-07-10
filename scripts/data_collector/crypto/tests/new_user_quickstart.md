# 🚀 新人测试快速入门卡片

## 🎯 一键运行所有测试（推荐）
```bash
# 1. 激活虚拟环境并进入测试目录
cd /Users/alanguo/Projects/qlib
source .venv/bin/activate
cd scripts/data_collector/crypto/tests

# 2. 运行所有测试（最简单）
python run_all_tests.py

# 3. 或者运行快速测试（跳过慢速测试）
python run_all_tests.py --fast

# 4. 或者跳过实时测试（无网络时）
python run_all_tests.py --no-live

# 5. 或者只查看测试计划
python run_all_tests.py --summary
```

## 📋 开始前检查清单
```bash
# 1. 激活虚拟环境
cd /Users/alanguo/Projects/qlib
source .venv/bin/activate

# 2. 进入测试目录  
cd scripts/data_collector/crypto/tests

# 3. 验证环境
pwd  # 应该显示: /Users/alanguo/Projects/qlib/scripts/data_collector/crypto/tests
ls -la  # 应该看到: unit/ live/ integration/ performance/ runners/
pytest --version  # 应该显示pytest版本
```

## 🎯 基础测试流程（5分钟）
```bash
# 测试1：单元测试（无网络）
pytest unit/test_crypto_alpha_factors.py -v

# 测试2：集成测试（快速功能测试）
pytest integration/test_cli_functions.py -v

# 测试3：检查所有测试数量
pytest --collect-only -q | wc -l
```

## 🌐 网络测试流程（需要代理）
```bash
# 配置代理（推荐这样设置）
export https_proxy=http://127.0.0.1:10808
export HTTPS_PROXY=http://127.0.0.1:10808

# 验证网络
curl -I https://api.binance.com/api/v3/ping

# 运行实时测试
pytest live/ -v -m live
```

## 🏃 可执行脚本测试
```bash
# 运行综合测试
python runners/run_comprehensive_live_test.py
```

## ❗ 遇到问题？
1. **导入错误**: 已修复，现在应该没有模块导入问题
2. **网络错误**: 检查代理配置，确保设置了 `https_proxy` 和 `HTTPS_PROXY`
3. **目录错误**: 确保在正确路径

## 📚 完整指南
详细步骤请查看: `docs/testing_guide.md`

---
🎉 成功运行任一测试即表示环境配置正确！