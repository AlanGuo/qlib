# 加密货币数据收集模块测试计划

## 测试概述

本测试计划采用**从低耦合到高耦合**的渐进式测试策略，确保每个组件的稳定性，并最小化修复对其他组件的影响。

### 测试原则

1. **风险递增**：从无外部依赖的单元测试开始，逐步增加复杂度
2. **回归保护**：每次修复后重新运行相关测试，确保不影响已验证功能
3. **用户参与**：在关键节点邀请用户验证功能和数据质量
4. **可重现性**：使用固定的测试数据和配置，确保结果可重现

## 阶段1：基础组件单元测试（1-2天）

**目标**：验证最基础的功能，无外部依赖，风险极低

### 1.1 配置系统测试
- **测试内容**：YAML配置解析、配置验证逻辑、模板生成功能
- **测试文件**：`tests/test_config_system.py`
- **成功标准**：所有配置模板能正确加载和验证

### 1.2 时间框架转换测试
- **测试内容**：Qlib格式转换、交易所格式映射、时间框架验证
- **测试文件**：`tests/test_timeframe_conversion.py`
- **成功标准**：所有支持的时间框架能正确转换

### 1.3 字段定义测试
- **测试内容**：字段定义、市场类型过滤、交易所兼容性检查
- **测试文件**：`tests/test_field_definitions.py`
- **成功标准**：字段配置逻辑正确，过滤规则有效

### 1.4 验证器单元测试
- **测试内容**：价格验证器、成交量验证器、时间序列验证器等
- **测试文件**：`tests/test_validators_unit.py`
- **成功标准**：每个验证器能正确识别和报告问题

### 1.5 存储格式测试
- **测试内容**：Qlib格式存储、CSV格式存储、数据类型转换
- **测试文件**：`tests/test_storage_format.py`
- **成功标准**：数据能正确序列化和反序列化

## 阶段2：核心组件测试（2-3天）

**目标**：测试核心业务逻辑，使用模拟数据，风险较低

### 2.1 交易所适配器测试
- **测试内容**：使用模拟数据测试Binance和OKX适配器
- **测试文件**：`tests/test_exchange_adapters.py`
- **模拟数据**：预定义的API响应数据
- **成功标准**：适配器能正确解析数据并处理错误

### 2.2 存储管理器测试
- **测试内容**：本地文件存储功能，目录结构创建
- **测试文件**：`tests/test_storage_manager.py`
- **测试环境**：临时目录
- **成功标准**：数据能正确写入和读取

### 2.3 数据验证器集成测试
- **测试内容**：多个验证器协同工作，验证流程
- **测试文件**：`tests/test_validator_integration.py`
- **成功标准**：验证流程正确，错误报告准确

### 2.4 投资域管理器测试
- **测试内容**：符号发现和过滤逻辑，投资域管理
- **测试文件**：`tests/test_universe_manager.py`
- **成功标准**：能正确创建和管理投资域

### 2.5 加密货币字段收集器测试
- **测试内容**：资金费率、持仓量、订单簿数据收集
- **测试文件**：`tests/test_crypto_field_collector.py`
- **成功标准**：特有字段能正确收集和格式化

### 2.6 Calendar和Instruments生成测试
- **测试内容**：Qlib数据结构文件生成、目录结构创建、文件内容验证
- **测试文件**：`tests/test_calendar_instruments.py`
- **成功标准**：所有timeframe的calendar和instruments文件正确生成

### 2.7 永续合约专项验证
- **测试内容**：永续合约功能完整性验证，包括配置支持、适配器实现、字段收集器、CCXT库支持、市场类型逻辑
- **测试文件**：`tests/test_perpetual_basic.py`
- **测试特点**：无网络依赖，纯功能验证
- **成功标准**：所有永续合约核心功能验证通过，无关键实现缺口

## 阶段3：集成测试（2-3天）

**目标**：测试组件间协作，少量真实API调用，风险中等

### 3.1 交易所连接测试
- **测试内容**：真实API连接，但限制请求量
- **测试文件**：`tests/test_exchange_connection.py`
- **测试配置**：使用测试API密钥，限制请求频率
- **成功标准**：能成功连接并获取基本数据

### 3.2 端到端数据流测试
- **测试内容**：从数据获取到存储的完整流程
- **测试文件**：`tests/test_end_to_end.py`
- **测试范围**：收集2-3个币种1小时的数据
- **成功标准**：数据流程完整，格式正确

### 3.3 Qlib集成测试
- **测试内容**：数据提供者集成，数据加载，策略运行
- **测试文件**：`tests/test_qlib_integration.py`
- **成功标准**：能在Qlib中正常使用收集的数据

### 3.4 CLI功能测试
- **测试内容**：命令行工具的各项功能
- **测试脚本**：`tests/test_cli_functions.py`
- **成功标准**：所有CLI命令能正常执行

### 3.5 增量更新测试
- **测试内容**：状态管理、冲突解决、断点续传
- **测试文件**：`tests/test_incremental_update.py`
- **成功标准**：增量更新逻辑正确

## 阶段4：实盘测试（3-5天）

**目标**：在真实环境下验证功能和性能，风险最高

### 4.1 小规模实盘测试
- **测试内容**：收集主流币种1天的数据
- **币种范围**：BTC/USDT, ETH/USDT, BNB/USDT等5个主流币种
- **时间框架**：1h, 1d
- **用户参与**：验证数据质量和完整性

### 4.2 性能压力测试
- **测试内容**：收集100个币种30天的数据
- **性能指标**：收集速度、内存使用、错误率
- **成功标准**：在合理时间内完成收集，错误率<1%

### 4.3 长期稳定性测试
- **测试内容**：24小时连续运行
- **监控指标**：内存泄漏、连接稳定性、数据一致性
- **成功标准**：系统稳定运行，无内存泄漏

### 4.4 异常恢复测试
- **测试场景**：
  - 网络中断恢复
  - API限制处理
  - 磁盘空间不足
  - 数据异常处理
- **成功标准**：系统能优雅处理异常并恢复

### 4.5 用户验收测试
- **用户参与**：验证以下方面
  - 数据质量是否满足量化策略需求
  - 性能表现是否符合预期
  - 用户界面和文档是否清晰
  - 配置和使用是否便捷

## 测试环境准备

### 测试文件路径
scripts/data_collector/crypto/test_data/

### 真实API代理环境
export http_proxy=http://127.0.0.1:10808
export https_proxy=http://127.0.0.1:10808

export HTTP_PROXY=http://127.0.0.1:10808
export HTTPS_PROXY=http://127.0.0.1:10808

### 开发环境
项目根目录有询环境 .venv
```bash
source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock

# 设置测试数据目录
export CRYPTO_TEST_DATA_DIR="./test_data"
```

### 测试配置
```yaml
# test_config.yaml
collection:
  exchanges: ["binance", "okx"]
  timeframes: ["1h", "1d"]
  instruments: ["BTC/USDT", "ETH/USDT"]
  max_requests_per_minute: 60
  test_mode: true
```

## 测试执行命令

```bash
# 阶段1：基础组件测试
pytest tests/test_config_system.py -v
pytest tests/test_timeframe_conversion.py -v
pytest tests/test_field_definitions.py -v
pytest tests/test_validators_unit.py -v
pytest tests/test_storage_format.py -v

# 阶段2：核心组件测试
pytest tests/test_exchange_adapters.py -v
pytest tests/test_storage_manager.py -v
pytest tests/test_validator_integration.py -v
pytest tests/test_universe_manager.py -v
pytest tests/test_crypto_field_collector.py -v
pytest tests/test_calendar_instruments.py -v
pytest tests/test_perpetual_basic.py -v

# 阶段3：集成测试
pytest tests/test_exchange_connection.py -v
pytest tests/test_end_to_end.py -v
pytest tests/test_qlib_integration.py -v
pytest tests/test_cli_functions.py -v
pytest tests/test_incremental_update.py -v

# 阶段4：实盘测试
python tests/test_live_small_scale.py
python tests/test_performance_stress.py
python tests/test_long_term_stability.py
python tests/test_exception_recovery.py
```

## 成功标准

### 整体目标
- **功能完整性**：所有核心功能正常工作
- **数据质量**：收集的数据准确、完整、及时
- **性能表现**：满足实际使用需求
- **稳定性**：长期运行稳定，异常恢复能力强
- **用户满意度**：用户确认系统满足需求

### 量化指标
- 单元测试覆盖率 > 90%
- 集成测试通过率 = 100%
- 数据收集成功率 > 99%
- 系统可用性 > 99.5%
- 用户验收通过率 = 100%

## 风险管理

### 潜在风险
1. **API限制**：交易所API调用限制可能影响测试
2. **数据质量**：真实数据可能存在异常
3. **网络问题**：网络不稳定影响测试结果
4. **配置错误**：配置问题可能导致测试失败

### 缓解措施
1. 使用测试API密钥，控制请求频率
2. 准备多套测试数据，包括异常数据
3. 在多个网络环境下测试
4. 详细的配置验证和错误提示

## 测试报告

每个阶段完成后，生成测试报告包含：
- 测试执行情况
- 发现的问题和修复情况
- 性能指标
- 用户反馈
- 下一阶段建议

---

**注意**：如果任何阶段发现重大问题，应暂停后续测试，先修复问题并进行回归测试，确保修复不影响已验证的功能。