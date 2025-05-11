# Ruoyi-Stock-FastAPI v0.0.1

<p align="center">
	<img alt="logo" src="https://oscimg.oschina.net/oscnet/up-d3d0a9303e11d522a06cd263f3079027715.png">
</p>
<h1 align="center" style="margin: 30px 0 30px; font-weight: bold;">Ruoyi-Stock-FastAPI v0.0.1</h1>
<h4 align="center">基于RuoYi-Vue-FastAPI扩展的股票行情管理系统</h4>
<p align="center">
	<a href="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/stargazers"><img src="https://img.shields.io/github/stars/yorkqqcom/Ruoyi-Stock-FastAPI?style=social"></a>
	<a href="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI"><img src="https://img.shields.io/badge/RuoyiStockFastAPI-v1.0.0-brightgreen.svg"></a>
	<a href="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/main/LICENSE"><img src="https://img.shields.io/github/license/mashape/apistatus.svg"></a>
    <img src="https://img.shields.io/badge/python-≥3.9-blue">
    <img src="https://img.shields.io/badge/MySQL-≥5.7-blue">
</p>

## 平台简介

Ruoyi-Stock-FastAPI 是基于 RuoYi-Vue-FastAPI v1.6.0 扩展的股票行情分析系统，在原系统基础上新增股票智能分析功能。核心特性如下：

* 前端继承 RuoYi-Vue 的 Vue + Element UI 技术栈
* 后端采用 FastAPI + SQLAlchemy 架构
* 整合第三方股票行情API实现实时数据获取
* 新增股票历史行情功能模块
* 特别鸣谢：
  - 基础框架：[RuoYi-Vue-FastAPI](https://gitee.com/insistence2022/RuoYi-Vue-FastAPI)
  - 原型项目：[RuoYi-Vue](https://gitee.com/y_project/RuoYi-Vue)
  - 数据支持：[AKShare](https://github.com/akfamily/akshare) 提供全量历史数据接口

## 主要功能

### 1. 股票行情分析
* K线图表展示
  - 支持前复权、后复权、不复权切换
  - 集成MA5、MA10等技术指标
  - 支持图表缩放和拖动

* 智能分析功能
  - 基于历史数据的买卖信号分析
  - 多周期回测指标计算
  - 胜率、收益率等关键指标展示
  - 可视化交易信号标记

### 2. AI 智能助手
* 股票分析报告
  - 自动生成个股分析报告
  - 支持公司基本面分析
  - 主营业务分析

* 智能对话功能
  - 支持自然语言交互
  - 股票相关问答
  - 技术指标解释
  - 投资策略建议

### 3. MCP Server 服务
* 数据采集服务
  - 基于 AKShare 的实时数据采集
  - 支持 A 股数据
  - 自动数据更新和同步
  - 数据格式标准化处理


* 用户配置管理
  - 个性化设置保存
  - 查询条件记忆
  - 界面偏好设置

## 技术特点

### 前端技术栈
* Vue 2.x + Element UI
* ECharts 图表库
* Markdown-it 渲染引擎
* DOMPurify 安全渲染
* Highlight.js 代码高亮

### 后端技术栈
* FastAPI 框架
* SQLAlchemy ORM
* Redis 缓存
* MySQL 数据库
* AKShare 数据接口

### MCP Server 技术特点
* 异步数据处理
  - 使用 asyncio 实现异步操作
  - 支持并发数据请求
  - 高效的数据处理流程


## 项目开发及发布相关

### 开发环境要求
* Python ≥ 3.9
* MySQL ≥ 5.7
* Node.js ≥ 12
* Redis ≥ 6.0

### 开发步骤

#### 前端
```bash
# 进入前端目录
cd ruoyi-fastapi-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 后端
```bash
# 进入后端目录
cd ruoyi-fastapi-backend

# 安装依赖
pip3 install -r requirements.txt

# 配置环境
# 在.env.dev文件中配置开发环境的数据库和redis

# 运行sql文件
# 1.新建数据库ruoyi-fastapi(默认，可修改)
# 2.使用命令或数据库连接工具运行sql文件夹下的ruoyi-fastapi.sql

# 运行后端
python3 app.py --env=dev
```

#### MCP Server
```bash
# 进入MCP Server目录
cd mcp-server

# 启动服务
python3 akshare_server
```

#### AI 环境配置
在项目根目录创建 `ai.env` 文件，配置以下参数：

BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL=qwen-plus-latest
AI_API_KEY=your-key

### 访问系统
```bash
# 默认账号密码
账号：admin
密码：admin123
```

## 演示图
<table>
    <tr>
        <td><img src="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/master/demo-pictures/stock-1.png"/></td>
        <td><img src="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/master/demo-pictures/stock-2.png"/></td>
    </tr>
</table>

## 注意事项
1. 请确保开发环境满足最低版本要求
2. 首次运行需要正确配置数据库和Redis
3. 建议使用虚拟环境进行开发
4. 注意保护API密钥等敏感信息

## 许可证
本项目采用 MIT 许可证，详情请参见 [LICENSE](LICENSE) 文件。