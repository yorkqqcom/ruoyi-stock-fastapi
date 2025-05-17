# Ruoyi-Stock-FastAPI v0.0.1

<p align="center">
	<img alt="logo" src="https://oscimg.oschina.net/oscnet/up-d3d0a9303e11d522a06cd263f3079027715.png">
</p>
<h1 align="center" style="margin: 30px 0 30px; font-weight: bold;">Ruoyi-Stock-FastAPI v0.0.1</h1>
<h4 align="center">Stock Market Analysis System Extended from RuoYi-Vue-FastAPI</h4>
<p align="center">
	<a href="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/stargazers"><img src="https://img.shields.io/github/stars/yorkqqcom/Ruoyi-Stock-FastAPI?style=social"></a>
	<a href="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI"><img src="https://img.shields.io/badge/RuoyiStockFastAPI-v1.0.0-brightgreen.svg"></a>
	<a href="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/main/LICENSE"><img src="https://img.shields.io/github/license/mashape/apistatus.svg"></a>
    <img src="https://img.shields.io/badge/python-≥3.9-blue">
    <img src="https://img.shields.io/badge/MySQL-≥5.7-blue">
</p>

## Platform Introduction

Ruoyi-Stock-FastAPI is a stock market analysis system extended from RuoYi-Vue-FastAPI v1.6.0, adding intelligent stock analysis capabilities to the original system. Core features include:

* Frontend inherits RuoYi-Vue's Vue + Element UI technology stack
* Backend uses FastAPI + SQLAlchemy architecture
* Integration with third-party stock market APIs for real-time data acquisition
* New stock historical data module
* Special thanks to:
  - Base framework: [RuoYi-Vue-FastAPI](https://gitee.com/insistence2022/Ruoyi-Vue-FastAPI)
  - Prototype project: [RuoYi-Vue](https://gitee.com/y_project/RuoYi-Vue)
  - Data support: [AKShare](https://github.com/akfamily/akshare) providing comprehensive historical data APIs

## Demo Screenshots
<table>
    <tr>
        <td><img src="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/master/demo-pictures/stock-1.png"/></td>
        <td><img src="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/master/demo-pictures/stock-2.png"/></td>
    </tr>
    <tr>
        <td><img src="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/master/demo-pictures/chat.png"/></td>
        <td><img src="https://github.com/yorkqqcom/Ruoyi-Stock-FastAPI/blob/master/demo-pictures/analysis.png"/></td>
    </tr>
</table>

## Main Features

### 1. Stock Market Analysis
* K-line Chart Display
  - Support for forward adjustment, backward adjustment, and no adjustment
  - Integration of MA5, MA10 and other technical indicators
  - Support for chart zooming and dragging

* Intelligent Analysis Features
  - Buy/sell signal analysis based on historical data
  - Multi-period backtesting indicator calculation
  - Display of key metrics like win rate and return rate
  - Visual trading signal marking

### 2. AI Intelligent Assistant
* Stock Analysis Reports
  - Automatic generation of individual stock analysis reports
  - Company fundamental analysis support
  - Main business analysis

* Intelligent Dialogue Function
  - Natural language interaction support
  - Stock-related Q&A
  - Technical indicator explanation
  - Investment strategy suggestions

### 3. MCP Server Service
* Data Collection Service
  - Real-time data collection based on AKShare
  - A-share market data support
  - Automatic data update and synchronization
  - Standardized data format processing

* User Configuration Management
  - Personalized settings storage
  - Query condition memory
  - Interface preference settings

## Technical Features

### Frontend Technology Stack
* Vue 2.x + Element UI
* ECharts chart library
* Markdown-it rendering engine
* DOMPurify secure rendering
* Highlight.js code highlighting

### Backend Technology Stack
* FastAPI framework
* SQLAlchemy ORM
* Redis caching
* MySQL database
* AKShare data interface

### MCP Server Technical Features
* Asynchronous Data Processing
  - Using asyncio for asynchronous operations
  - Support for concurrent data requests
  - Efficient data processing pipeline

## Project Development and Release

### Development Environment Requirements
* Python ≥ 3.9
* MySQL ≥ 5.7
* Node.js ≥ 12
* Redis ≥ 6.0

### Development Steps

#### Frontend
```bash
# Enter frontend directory
cd ruoyi-fastapi-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Backend
```bash
# Enter backend directory
cd ruoyi-fastapi-backend

# Install dependencies
pip3 install -r requirements.txt

# Configure environment
# Configure database and redis in .env.dev file

# Run SQL file
# 1. Create new database ruoyi-fastapi (default, can be modified)
# 2. Run ruoyi-fastapi.sql in sql folder using command or database tool

# Run backend
python3 app.py --env=dev
```

#### MCP Server
```bash
# Enter MCP Server directory
cd mcp-server

# Start service
python3 akshare_server
```

#### AI Environment Configuration
Create `ai.env` file in project root directory with following parameters:
```bash
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL=qwen-plus-latest
AI_API_KEY=your-key
```

### Access System
```bash
# Default credentials
Username: admin
Password: admin123
```

## Notes
1. Please ensure development environment meets minimum version requirements
2. First run requires proper database and Redis configuration
3. Recommended to use virtual environment for development
4. Pay attention to protecting sensitive information like API keys

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details. 