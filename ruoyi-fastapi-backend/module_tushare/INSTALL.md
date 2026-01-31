# Tushare数据下载模块安装指南

## 完整安装步骤

### 1. 执行数据库脚本

#### MySQL 版本
```sql
source sql/tushare_mysql.sql;
```

#### PostgreSQL 版本
```sql
\i sql/tushare_pg.sql
```

### 2. 安装 Python 依赖

```bash
cd ruoyi-fastapi-backend
pip install -r requirements.txt
```

### 3. 配置环境变量

在 `.env` 文件中添加或设置：

```env
TUSHARE_TOKEN=your_tushare_token_here
```

或者在系统环境变量中设置：

```bash
export TUSHARE_TOKEN=your_tushare_token_here
```

### 4. 启动后端服务

```bash
python app.py --env=dev
```

### 5. 启动前端服务

```bash
cd ruoyi-fastapi-frontend
npm install
npm run dev
```

### 6. 配置角色权限

登录系统后，在"系统管理" -> "角色管理"中，为相应角色分配以下菜单权限：

- Tushare数据管理（主菜单）
  - 接口配置
  - 下载任务
  - 下载日志

## 使用流程

### 第一步：配置接口

1. 进入"Tushare数据管理" -> "接口配置"
2. 点击"新增"按钮
3. 填写接口信息：
   - **接口名称**：如"股票基本信息"
   - **接口代码**：如"stock_basic"
   - **接口参数**：JSON格式，如 `{"exchange": "", "list_status": "L"}`
   - **数据字段**：可选，JSON数组格式，如 `["ts_code", "symbol", "name"]`
4. 保存配置

### 第二步：创建下载任务

1. 进入"Tushare数据管理" -> "下载任务"
2. 点击"新增"按钮
3. 填写任务信息：
   - **任务名称**：如"每日股票数据下载"
   - **接口配置**：选择已配置的接口
   - **开始日期/结束日期**：可选，留空则下载当日数据
   - **保存路径**：如"./data/tushare"
   - **保存格式**：选择 CSV/Excel/JSON
4. 保存任务

### 第三步：配置定时任务（可选）

1. 进入"系统监控" -> "定时任务"
2. 点击"新增"按钮
3. 填写任务信息：
   - **任务名称**：如"Tushare数据下载-股票基本信息"
   - **调用目标字符串**：`module_tushare.task.tushare_download_task.download_tushare_data_sync`
   - **位置参数**：任务ID（如：1）
   - **Cron表达式**：如 `0 0 9 * * ?`（每天9点执行）
4. 保存并启用任务

### 第四步：查看下载日志

1. 进入"Tushare数据管理" -> "下载日志"
2. 查看每次下载的执行情况
3. 可以查看详细的执行信息，包括记录数、文件路径、错误信息等

## 常见问题

### 1. TUSHARE_TOKEN 未设置

**错误信息**：`TUSHARE_TOKEN环境变量未设置`

**解决方法**：在 `.env` 文件中设置 `TUSHARE_TOKEN` 环境变量

### 2. 接口代码不存在

**错误信息**：`接口 xxx 不存在`

**解决方法**：检查接口代码是否正确，参考 Tushare Pro API 文档

### 3. JSON 格式错误

**错误信息**：`接口参数必须是有效的JSON格式`

**解决方法**：检查 JSON 格式是否正确，可以使用在线 JSON 验证工具

### 4. 保存路径无权限

**错误信息**：权限错误

**解决方法**：确保保存路径有写入权限，或使用相对路径

## 注意事项

1. **Token 获取**：需要到 Tushare 官网注册并获取 Token
2. **接口参数**：不同接口的参数不同，请参考 Tushare Pro API 文档
3. **日期格式**：统一使用 YYYYMMDD 格式（如：20240123）
4. **数据量**：注意 Tushare 的积分限制，避免频繁调用
5. **文件路径**：建议使用相对路径，便于管理

## 测试建议

1. 先创建一个简单的接口配置（如：stock_basic）
2. 创建下载任务，不设置定时，手动测试
3. 检查下载的文件是否正确
4. 查看下载日志，确认执行成功
5. 再配置定时任务进行自动化下载
