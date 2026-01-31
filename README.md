<h1 align="center" style="margin: 30px 0 30px; font-weight: bold;">RuoYi-Vue3-Stock</h1>
<h4 align="center">基于RuoYi-Vue3+FastAPI的股票数据管理系统</h4>
<p align="center">
    <img alt="node version" src="https://img.shields.io/badge/node-≥18-blue">
    <img alt="python version" src="https://img.shields.io/badge/python-≥3.9-blue">
    <img alt="mysql version" src="https://img.shields.io/badge/MySQL-≥5.7-blue">
</p>

## 项目简介

本项目基于 [RuoYi-Vue3-FastAPI](https://github.com/insistence/RuoYi-Vue3-FastAPI) 框架开发，专注于股票数据管理。

**技术栈：**
- 前端：Vue3 + Element Plus
- 后端：FastAPI + SQLAlchemy + MySQL/PostgreSQL + Redis
- 认证：OAuth2 & JWT

**核心功能：**
- 系统管理：用户、角色、菜单、部门、岗位、字典、参数等基础功能
- 监控管理：操作日志、登录日志、在线用户、定时任务、服务监控、缓存监控
- 开发工具：代码生成、系统接口、表单构建
- **Tushare数据管理**：接口配置、下载任务、下载日志（新增）

## 新增功能

### Tushare数据下载模块

提供完整的 Tushare Pro 数据下载功能：

- **接口配置管理**：通过界面配置 Tushare 接口参数
- **下载任务管理**：创建和管理数据下载任务，支持定时调度
- **下载日志**：记录每次下载的执行情况和结果

详细使用说明请参考：[module_tushare/README.md](ruoyi-fastapi-backend/module_tushare/README.md)

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
cd RuoYi-Vue3-Stock
```

#### 2. 后端配置

```bash
cd ruoyi-fastapi-backend

# 安装依赖（根据数据库类型选择）
pip install -r requirements.txt        # MySQL
# 或
pip install -r requirements-pg.txt     # PostgreSQL

# 配置环境变量
# 编辑 .env.dev 文件，配置数据库和 Redis 连接信息
# 如需使用 Tushare 功能，添加：TUSHARE_TOKEN=your_token

# 初始化数据库
# 1. 创建数据库 ruoyi-fastapi（可修改）
# 2. 执行 SQL 脚本：
#    - MySQL: sql/ruoyi-fastapi.sql
#    - PostgreSQL: sql/ruoyi-fastapi-pg.sql
# 3. 如需使用 Tushare 模块，执行（表+菜单+运行表已合并）：
#    - MySQL: sql/tushare_mysql.sql
#    - PostgreSQL: sql/tushare_pg.sql

# 启动后端
python app.py --env=dev
```

#### 3. 前端配置

```bash
cd ruoyi-fastapi-frontend

# 安装依赖
npm install --registry=https://registry.npmmirror.com

# 启动服务
npm run dev
```

#### 4. 访问系统

- 访问地址：http://localhost:80
- 默认账号：`admin`
- 默认密码：`admin123`

### Docker 部署

```bash
# MySQL 版本
docker compose -f docker-compose.my.yml up -d --build

# PostgreSQL 版本
docker compose -f docker-compose.pg.yml up -d --build
```

> ⚠️ **注意：** 默认未配置数据持久化，请根据需要配置或备份数据

### Tushare 模块使用

1. 配置 Tushare Token（在 `.env.dev` 中设置 `TUSHARE_TOKEN`）
2. 执行 Tushare 相关 SQL 脚本（见安装步骤）
3. 登录系统后，在"Tushare数据管理"菜单中配置接口和下载任务

详细说明请参考：[module_tushare/README.md](ruoyi-fastapi-backend/module_tushare/README.md)

## 项目结构

```
RuoYi-Vue3-Stock/
├── ruoyi-fastapi-backend/      # 后端项目
│   ├── module_admin/           # 系统管理模块
│   ├── module_tushare/         # Tushare数据管理模块（新增）
│   ├── module_generator/       # 代码生成模块
│   └── sql/                    # 数据库脚本
├── ruoyi-fastapi-frontend/     # 前端项目
└── ruoyi-fastapi-test/         # 测试套件
```

## 相关链接

- 原框架项目：[RuoYi-Vue3-FastAPI](https://github.com/insistence/RuoYi-Vue3-FastAPI)
- 前端基础：[RuoYi-Vue3](https://github.com/yangzongzhuan/RuoYi-Vue3)
