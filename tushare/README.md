# Tushare 数据同步系统

## 项目概述

这是一个基于 Tushare API 的股票数据同步系统，用于自动化获取、存储和管理中国A股市场的各类金融数据。系统采用模块化设计，支持定时任务调度、数据质量检查、特征提取等功能。

## 系统架构

```
tushare/
├── 1-init/                    # 初始化配置
│   └── stock.env              # 环境配置文件
├── config/                    # 配置模块
│   ├── __init__.py
│   └── settings.py            # 系统配置
├── models/                    # 数据模型
│   ├── base.py               # 基础模型类
│   ├── stock_basic.py        # 股票基础信息
│   ├── daily_quote.py         # 日线行情数据
│   ├── moneyflow.py          # 资金流向数据
│   ├── adj_factor.py         # 复权因子
│   ├── adjusted_quote.py     # 复权行情
│   └── trade_cal.py          # 交易日历
├── dao/                       # 数据访问层
│   ├── database.py           # 数据库管理
│   ├── stock_basic_dao.py    # 股票基础信息DAO
│   ├── daily_quote_dao.py    # 日线行情DAO
│   ├── moneyflow_dao.py      # 资金流向DAO
│   ├── adj_factor_dao.py     # 复权因子DAO
│   ├── adjusted_quote_dao.py # 复权行情DAO
│   └── trade_cal_dao.py      # 交易日历DAO
├── services/                  # 业务服务层
│   ├── tushare_service.py    # Tushare API服务
│   ├── stock_basic_service.py # 股票基础信息服务
│   ├── daily_quote_service.py # 日线行情服务
│   ├── moneyflow_service.py  # 资金流向服务
│   ├── adj_factor_service.py # 复权因子服务
│   ├── adjusted_quote_service.py # 复权行情服务
│   └── trade_cal_service.py  # 交易日历服务
└── scripts/                   # 脚本工具
    ├── enhanced_scheduler.py # 增强版调度器
    ├── daily_data_sync.py    # 日常数据同步
    ├── data_sync_coordinator.py # 数据同步协调器
    ├── stock_basic_sync.py   # 股票基础信息同步
    ├── daily_adj_factor_sync.py # 复权因子同步
    └── sync_moneyflow_daily.py # 资金流向同步
```

## 核心功能

### 1. 数据同步功能

- **股票基础信息同步**: 获取所有A股股票的基本信息，包括代码、名称、行业、上市状态等
- **日线行情同步**: 获取股票的开盘价、收盘价、最高价、最低价、成交量等日线数据
- **资金流向同步**: 获取个股的资金流向数据，包括大单、中单、小单的买卖情况
- **复权数据同步**: 获取前复权、后复权的行情数据
- **交易日历同步**: 维护交易日历，确保只在交易日进行数据同步

### 2. 定时任务调度

- **早晨同步** (08:30): 完整数据同步，包括所有数据类型
- **下午同步** (18:30): 快速数据同步，主要更新当日数据
- **特征提取** (23:00): 基于同步的数据进行特征计算
- **周度维护** (周日22:00): 系统维护和数据清理

### 3. 数据质量控制

- **API频率限制处理**: 自动处理Tushare API的频率限制
- **数据完整性检查**: 确保数据的完整性和一致性
- **错误重试机制**: 支持自动重试和错误恢复
- **数据质量报告**: 生成数据质量统计报告

## 数据模型

### 股票基础信息 (StockBasic)
- `ts_code`: TS股票代码
- `symbol`: 股票代码
- `name`: 股票名称
- `area`: 地域
- `industry`: 所属行业
- `market`: 市场类型
- `exchange`: 交易所代码
- `list_status`: 上市状态
- `list_date`: 上市日期

### 日线行情 (DailyQuote)
- `ts_code`: 股票代码
- `trade_date`: 交易日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `vol`: 成交量
- `amount`: 成交额
- `pct_chg`: 涨跌幅

### 资金流向 (MoneyFlow)
- `ts_code`: 股票代码
- `trade_date`: 交易日期
- `buy_sm_vol`: 小单买入量
- `buy_sm_amount`: 小单买入金额
- `buy_lg_vol`: 大单买入量
- `buy_lg_amount`: 大单买入金额
- `net_mf_amount`: 净流入额

## 配置说明

### 环境配置 (1-init/stock.env)

```bash
# Tushare配置
TUSHARE_TOKEN=your_token_here

# 数据库连接配置
DB_DRIVER=mysql+pymysql
DB_USER=tushare
DB_PASSWORD=tushare
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=tushare
DB_CHARSET=utf8

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/tushare_data.log

# 数据更新配置
BATCH_SIZE=1000
MAX_RETRY=3
RETRY_DELAY=60
```

## 使用方法

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp 1-init/stock.env.example 1-init/stock.env
# 编辑 stock.env 文件，填入你的 Tushare token
```

### 2. 数据库初始化

```bash
# 创建数据库表
python -c "from dao.database import db_manager; db_manager.create_tables()"
```

### 3. 手动数据同步

```bash
# 同步股票基础信息
python scripts/stock_basic_sync.py

# 同步日线数据
python scripts/daily_data_sync.py

# 同步资金流向数据
python scripts/sync_moneyflow_daily.py
```

### 4. 启动定时任务

```bash
# 启动增强版调度器
python scripts/enhanced_scheduler.py --action start

# 查看调度器状态
python scripts/enhanced_scheduler.py --action status

# 查看任务历史
python scripts/enhanced_scheduler.py --action history --days 7
```

### 5. 数据同步协调器

```bash
# 设置数据同步完成标志
python scripts/data_sync_coordinator.py --action set_completed --date 2024-01-01

# 检查数据就绪状态
python scripts/data_sync_coordinator.py --action check_ready --date 2024-01-01

# 获取同步状态
python scripts/data_sync_coordinator.py --action get_status --date 2024-01-01
```

## API 使用示例

### 获取股票基础信息

```python
from services.stock_basic_service import StockBasicService
from dao.database import db_manager

# 创建服务实例
service = StockBasicService()

# 获取数据库会话
with db_manager.get_session() as session:
    # 同步所有股票基础信息
    count = service.sync_all_stock_basic(session)
    print(f"同步了 {count} 条股票基础信息")
```

### 获取日线行情数据

```python
from services.daily_quote_service import DailyQuoteService
from dao.database import db_manager

service = DailyQuoteService()

with db_manager.get_session() as session:
    # 同步指定日期的日线数据
    count = service.sync_daily_quotes_by_date('20240101', session)
    print(f"同步了 {count} 条日线数据")
```

### 获取资金流向数据

```python
from services.moneyflow_service import MoneyFlowService
from dao.database import db_manager

service = MoneyFlowService()

with db_manager.get_session() as session:
    # 同步指定日期的资金流向数据
    count = service.sync_moneyflow_by_date('20240101', session)
    print(f"同步了 {count} 条资金流向数据")
```

## 系统特性

### 1. 高可用性
- 支持数据库连接池管理
- 自动重试机制
- 错误恢复能力

### 2. 性能优化
- 批量数据插入
- 数据库索引优化
- 内存使用优化

### 3. 监控和日志
- 详细的日志记录
- 任务执行历史
- 数据质量监控

### 4. 扩展性
- 模块化设计
- 易于添加新的数据源
- 支持自定义数据处理逻辑

## 注意事项

1. **API限制**: Tushare API有访问频率限制，系统已内置处理机制
2. **数据量**: 全量数据同步可能需要较长时间，建议分批进行
3. **存储空间**: 确保数据库有足够的存储空间
4. **网络连接**: 需要稳定的网络连接访问Tushare API

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置是否正确
   - 确认数据库服务是否启动
   - 验证用户权限

2. **API访问失败**
   - 检查Tushare token是否有效
   - 确认网络连接正常
   - 查看API访问频率是否超限

3. **数据同步失败**
   - 检查日志文件获取详细错误信息
   - 确认目标日期是否为交易日
   - 验证数据格式是否正确

## 开发指南

### 添加新的数据源

1. 在 `models/` 目录下创建新的数据模型
2. 在 `dao/` 目录下创建对应的DAO类
3. 在 `services/` 目录下创建业务服务类
4. 在 `scripts/` 目录下创建同步脚本

### 自定义数据处理

1. 继承基础服务类
2. 重写数据处理方法
3. 添加自定义验证逻辑
4. 更新配置文件

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 使用本系统前请确保已获得 Tushare 的有效 API token，并遵守相关使用条款。
