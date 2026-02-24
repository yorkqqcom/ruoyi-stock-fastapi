<h1 align="center" style="margin: 30px 0 30px; font-weight: bold;">RuoYi-Vue3-Stock</h1>
<h4 align="center">基于 RuoYi-Vue3 + FastAPI 的股票数据与量化因子管理系统</h4>
<p align="center">
    <img alt="node version" src="https://img.shields.io/badge/node-≥18-blue">
    <img alt="python version" src="https://img.shields.io/badge/python-≥3.9-blue">
    <img alt="mysql version" src="https://img.shields.io/badge/MySQL-≥5.7-blue">
    <img alt="postgresql" src="https://img.shields.io/badge/PostgreSQL-支持-blue">
</p>

## 项目简介

本项目基于 [RuoYi-Vue3-FastAPI](https://github.com/insistence/RuoYi-Vue3-FastAPI) 框架开发，在若依后台与 Tushare 数据管理基础上，扩展了**因子计算、特征工程与模型训练**能力，形成完整的股票数据与量化研究链路。

**技术栈：**
- 前端：Vue3 + Element Plus + Ant Design Vue + Vite
- 后端：FastAPI + SQLAlchemy + MySQL/PostgreSQL + Redis
- 认证：OAuth2 & JWT
- 量化：Pandas、scikit-learn、特征工程引擎（PriceAction/技术/形态/市场/时序/资金流等）

**核心功能：**
- **系统管理**：用户、角色、菜单、部门、岗位、字典、参数等基础功能
- **监控管理**：操作日志、登录日志、在线用户、定时任务、服务监控、缓存监控
- **开发工具**：代码生成、系统接口、表单构建
- **Tushare 数据管理**：接口配置、下载任务、下载日志
- **因子与模型**：因子定义、因子计算任务、因子值查询、模型训练任务、训练结果、模型预测（新增）
- **回测管理**：基于预测结果或在线模型的回测任务管理、回测结果指标、交易明细与日度净值，可串联数据下载 → 因子 → 模型 → 回测的完整链路

## 快速开始

### 环境要求

- Node.js ≥ 18
- Python ≥ 3.9
- MySQL ≥ 5.7 或 PostgreSQL
- Redis

### 安装步骤

#### 1. 克隆项目

```bash
git clone <项目地址>
cd ruoyi-stock-fastapi
```

#### 2. 后端配置

```bash
cd ruoyi-fastapi-backend

# 安装依赖（根据数据库类型选择）
pip install -r requirements.txt        # MySQL（含 asyncmy）
# 或
pip install -r requirements-pg.txt     # PostgreSQL（含 asyncpg）

# 配置环境变量：编辑 .env.dev，配置数据库与 Redis；使用 Tushare 时设置 TUSHARE_TOKEN

# 初始化数据库（按顺序执行）
# 1）基础库
#    MySQL: sql/ruoyi-fastapi.sql
#    PostgreSQL: sql/ruoyi-fastapi-pg.sql
# 2）Tushare 模块（表+菜单）
#    MySQL: sql/tushare_mysql.sql
#    PostgreSQL: sql/tushare_pg.sql
# 3）因子模块（因子定义、计算任务等）
#    MySQL: sql/factor_mysql.sql
#    PostgreSQL: sql/factor_pg.sql
# 4）模型训练模块（训练任务、结果、预测等）
#    MySQL: sql/model_train_mysql.sql
#    PostgreSQL: sql/model_train_pg.sql
# 5）回测模块（回测任务、结果、交易明细、日度净值 + 菜单）
#    MySQL: sql/backtest_mysql.sql
#    PostgreSQL: sql/backtest_pg.sql

# 启动后端（--env 可选：dev / prod / dockermy / dockerpg）
python app.py --env=dev
```

#### 3. 前端配置

```bash
cd ruoyi-fastapi-frontend

npm install 
npm run dev
```

#### 4. 访问系统

- 访问地址：http://localhost:80（或前端 dev 端口，默认后端端口 9099）
- 默认账号：`admin`
- 默认密码：`admin123`

### 后端环境变量（.env.dev 等）

| 类别 | 变量示例 | 说明 |
|------|----------|------|
| 应用 | `APP_PORT`、`APP_RELOAD` | 端口默认 9099，开发可开热重载 |
| 数据库 | `DB_TYPE`、`DB_HOST`、`DB_PORT`、`DB_USERNAME`、`DB_PASSWORD`、`DB_DATABASE` | MySQL 填 `mysql`，PostgreSQL 填 `postgresql` |
| Redis | `REDIS_HOST`、`REDIS_PORT`、`REDIS_PASSWORD` | 会话与缓存 |
| Tushare | `TUSHARE_TOKEN` | 使用 Tushare 数据管理时必填 |

## 功能说明

### Tushare 数据管理

- 在 `.env.dev` 中配置 `TUSHARE_TOKEN`，执行 `sql/tushare_mysql.sql` 或 `sql/tushare_pg.sql`。
- 登录后通过「Tushare 数据管理」菜单配置接口与下载任务。  

### 因子与模型训练

- **因子定义**：可在后台维护，或使用项目根目录下 `tools/generate_factor_sql.py` 根据 `features/` 中的特征生成 `factor_definition` 的 SQL（输出到 `ruoyi-fastapi-backend/sql/factor_definition_auto.sql`），再按需合并到 factor 相关脚本。
- **因子计算**：依赖已落地的行情/因子数据表（如 Tushare 下载结果），通过「因子管理」相关菜单配置计算任务与查看因子值、计算日志。
- **模型训练与预测**：需先有 `factor_value` 等数据，再在「模型管理」中创建训练任务、查看结果、执行预测。  

### 回测管理

- 在执行完回测相关 SQL（`sql/backtest_mysql.sql` 或 `sql/backtest_pg.sql`）后，系统会自动创建回测相关表（任务、结果、交易明细、日度净值）及「回测管理」菜单。
- 在前端「回测管理」中，可以：
  - 创建回测任务：选择信号来源（离线预测表 / 在线模型）、回测区间、标的列表、初始资金、仓位、手续费与买卖阈值等；
  - 异步执行回测：任务统一管理执行状态与进度，支持失败原因记录；
  - 查看回测结果：包括总收益、年化收益率、最大回撤、夏普、交易次数以及完整净值曲线；
  - 查看交易明细与日度净值：支持按任务 ID 回看每一笔交易和每天的账户净值，用于复盘与诊断策略表现。


## 注意事项

- **数据库**：首次运行前需按顺序执行 `sql/` 下对应脚本（基础库 → Tushare → 因子 → 模型训练），MySQL 与 PostgreSQL 勿混用同一套脚本。

## 许可证

本项目采用 [MIT License](LICENSE)。

## 相关链接

- 原框架项目：[RuoYi-Vue3-FastAPI](https://github.com/insistence/RuoYi-Vue3-FastAPI)
- 前端基础：[RuoYi-Vue3](https://github.com/yangzongzhuan/RuoYi-Vue3)
