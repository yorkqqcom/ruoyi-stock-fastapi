# Tushare数据下载模块

## 功能说明

本模块基于 RuoYi-Vue3-FastAPI 框架开发，提供了完整的 Tushare 数据下载功能，包括：

1. **接口配置管理**：通过界面配置 Tushare 接口参数
2. **下载任务管理**：创建和管理数据下载任务
3. **定时调度**：通过系统定时任务功能实现定时下载
4. **下载日志**：记录每次下载的执行情况和结果

## 目录结构

```
module_tushare/
├── controller/          # 控制器层
│   └── tushare_controller.py
├── dao/                # 数据访问层
│   └── tushare_dao.py
├── entity/             # 实体层
│   ├── do/            # 数据库实体
│   │   └── tushare_do.py
│   └── vo/            # 视图对象
│       └── tushare_vo.py
├── service/           # 服务层
│   └── tushare_service.py
└── task/              # 定时任务函数
    └── tushare_download_task.py
```

## 数据库表

1. **tushare_api_config** - Tushare接口配置表
2. **tushare_download_task** - 下载任务表
3. **tushare_download_log** - 下载日志表

## 安装步骤

### 1. 执行数据库脚本

根据使用的数据库类型，执行对应的 SQL 脚本：

- MySQL: `sql/tushare_mysql.sql`（表+菜单+运行表已合并）
- PostgreSQL: `sql/tushare_pg.sql`

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

设置 Tushare Token 环境变量：

```bash
export TUSHARE_TOKEN=your_tushare_token
```

或在 `.env` 文件中配置：

```
TUSHARE_TOKEN=your_tushare_token
```

### 4. 启动服务

```bash
python app.py --env=dev
```

## 使用说明

### 1. 配置接口

在"Tushare接口配置"页面添加接口配置：

- **接口名称**：接口的显示名称
- **接口代码**：Tushare Pro 接口代码（如：stock_basic）
- **接口参数**：JSON 格式的默认参数
- **数据字段**：JSON 格式，指定需要下载的字段列表（可选）

示例接口参数：
```json
{
  "exchange": "",
  "list_status": "L"
}
```

### 2. 创建下载任务

在"Tushare下载任务"页面创建下载任务：

- **任务名称**：任务的显示名称
- **接口配置**：选择已配置的接口
- **Cron表达式**：定时执行表达式（可选，如果需要在系统定时任务中配置）
- **开始日期/结束日期**：下载日期范围（YYYYMMDD格式）
- **任务参数**：JSON 格式，会覆盖接口默认参数
- **保存路径**：数据保存路径（默认：./data/tushare）
- **保存格式**：csv/excel/json

### 3. 配置定时任务

在系统"定时任务"页面创建定时任务：

- **任务名称**：任务名称
- **调用目标字符串**：`module_tushare.task.tushare_download_task.download_tushare_data_sync`
- **位置参数**：任务ID（如：1）
- **Cron表达式**：定时执行表达式

### 4. 查看下载日志

在"Tushare下载日志"页面查看每次下载的执行情况，包括：
- 下载日期
- 记录数
- 文件路径
- 执行状态
- 错误信息（如有）

## 注意事项

1. 确保已正确配置 Tushare Token
2. 保存路径需要有写入权限
3. 接口参数需要符合 Tushare Pro API 的要求
4. 日期格式统一使用 YYYYMMDD（如：20240123）

## 定时任务集成

下载任务可以通过系统定时任务功能进行调度。创建定时任务时：

- **调用目标**：`module_tushare.task.tushare_download_task.download_tushare_data_sync`
- **位置参数**：任务ID（整数）
- **关键字参数**：可选，`download_date`（YYYYMMDD格式）

示例：
- 位置参数：`1`（任务ID）
- 关键字参数：`{"download_date": "20240123"}`（可选）

## 前端页面

前端页面位于：
- `src/views/tushare/apiConfig/index.vue` - 接口配置管理
- `src/views/tushare/downloadTask/index.vue` - 下载任务管理
- `src/views/tushare/downloadLog/index.vue` - 下载日志查看

前端 API 文件位于：
- `src/api/tushare/apiConfig.js`
- `src/api/tushare/downloadTask.js`
- `src/api/tushare/downloadLog.js`

## 菜单配置

执行菜单配置 SQL 脚本：

- MySQL: `sql/tushare_menu.sql`
- PostgreSQL: `sql/tushare_menu-pg.sql`

或者通过系统"菜单管理"功能手动添加以下菜单：

### 主菜单
- **Tushare数据管理** (菜单类型：目录，路由：tushare)

### 二级菜单
1. **接口配置** (菜单类型：菜单，路由：tushare/apiConfig/index)
2. **下载任务** (菜单类型：菜单，路由：tushare/downloadTask/index)
3. **下载日志** (菜单类型：菜单，路由：tushare/downloadLog/index)

### 权限标识
- `tushare:apiConfig:list` - 接口配置列表
- `tushare:apiConfig:add` - 新增接口配置
- `tushare:apiConfig:edit` - 编辑接口配置
- `tushare:apiConfig:remove` - 删除接口配置
- `tushare:apiConfig:export` - 导出接口配置
- `tushare:apiConfig:changeStatus` - 修改接口配置状态
- `tushare:downloadTask:list` - 下载任务列表
- `tushare:downloadTask:add` - 新增下载任务
- `tushare:downloadTask:edit` - 编辑下载任务
- `tushare:downloadTask:remove` - 删除下载任务
- `tushare:downloadTask:changeStatus` - 修改下载任务状态
- `tushare:downloadLog:list` - 下载日志列表
- `tushare:downloadLog:remove` - 删除下载日志

## 开发说明

本模块采用与框架一致的目录结构，便于后续框架升级时的代码迁移。所有业务代码都在 `module_tushare` 目录下，不会与框架代码混淆。
