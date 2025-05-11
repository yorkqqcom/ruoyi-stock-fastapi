import logging
import asyncio
from typing import Dict, Union, Optional
from mcp.server.fastmcp import FastMCP
import akshare as ak
import pandas as pd
import sys

def add_stock_prefix(code):
    code_str = str(code).upper()
    # 检查是否已有前缀
    if code_str.startswith(('SH', 'SZ')):
        return code_str
    # 提取数字部分
    digits = ''.join([c for c in code_str if c.isdigit()])
    # 验证是否为6位数字
    if len(digits) != 6:
        return None
    first_char = digits[0]
    if first_char == '6':
        return f'SH{digits}'
    elif first_char in ['0', '3']:
        return f'SZ{digits}'
    else:
        return None
# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("akshare_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AKShare-MCP")

# 初始化FastMCP实例
mcp = FastMCP(
    "akshare-service",
    version="1.2.0",
    description="AKShare Financial Data Service",
    dependencies=["akshare>=1.10.0", "pandas"],
    env_vars={"CACHE_ENABLED": "true"},
    debug=False
)


# 公共工具函数
def handle_akshare_result(data: pd.DataFrame) -> Dict:
    '''处理AKShare返回结果'''
    if data.empty:
        return {"data": [], "metadata": {"item_count": 0}}

    return {
        "data": data.to_dict(orient='records'),
        "metadata": {
            "item_count": len(data),
            "columns": list(data.columns),
            "dtypes": dict(data.dtypes.astype(str))
        }
    }

# 东方财富网-个股-主营构成
@mcp.tool()
async def stock_zygc_em(
        symbol: str = None,
) -> Dict:
    """
    东方财富网-个股-主营构成
    输入参数：
    * symbol (str): symbol="SH688041"

    输出参数：
    * 股票代码 (object): -
    * 报告日期 (object): -
    * 分类类型 (object): -
    * 主营构成 (int64): -
    * 主营收入 (float64): 注意单位: 元
    * 收入比例 (float64): -
    * 主营成本 (float64): 注意单位: 元
    * 成本比例 (float64): -
    * 主营利润 (float64): 注意单位: 元
    * 利润比例 (float64): -
    * 毛利率 (float64): -

    接口示例：
    import akshare as ak

stock_zygc_em_df = ak.stock_zygc_em(symbol="SH688041")
print(stock_zygc_em_df)

    """
    try:
        # 参数预处理
        symbol = add_stock_prefix(symbol)
        params = {
            "symbol": symbol,
        }
        params = {k: v for k, v in params.items() if v is not None}

        # 调用AKShare接口（新增空参判断）
        if params:
            result = ak.stock_zygc_em(**params)
        else:
            result = ak.stock_zygc_em()
        result = result.head(20)
        # 结果处理
        if isinstance(result, pd.DataFrame):
            return handle_akshare_result(result)

        # 处理非DataFrame返回类型
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "type": type(result).__name__,
                "output_schema": [
                    {"name": "股票代码", "type": "object"},
                    {"name": "报告日期", "type": "object"},
                    {"name": "分类类型", "type": "object"},
                    {"name": "主营构成", "type": "int64"},
                    {"name": "主营收入", "type": "float64"},
                    {"name": "收入比例", "type": "float64"},
                    {"name": "主营成本", "type": "float64"},
                    {"name": "成本比例", "type": "float64"},
                    {"name": "主营利润", "type": "float64"},
                    {"name": "利润比例", "type": "float64"},
                    {"name": "毛利率", "type": "float64"},
                ]
            }
        }

    except Exception as e:
        logger.error(f"[stock_zygc_em] 接口错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "code": "AKSHARE_ERROR",
            "message": f"数据接口异常: {str(e)}"
        }

# 东方财富网-数据中心-研究报告-个股研报
@mcp.tool()
async def stock_research_report_em(
        symbol: str = None,
) -> Dict:
    """
    东方财富网-数据中心-研究报告-个股研报
    输入参数：
    * symbol (str): symbol="000001"

    输出参数：
    * 序号 (int64): -
    * 股票代码 (object): -
    * 股票简称 (object): -
    * 报告名称 (object): -
    * 东财评级 (object): -
    * 机构 (object): -
    * 近一月个股研报数 (int64): -
    * 2024-盈利预测-收益 (float64): -
    * 2024-盈利预测-市盈率 (float64): -
    * 2025-盈利预测-收益 (float64): -
    * 2025-盈利预测-市盈率 (float64): -
    * 2026-盈利预测-收益 (float64): -
    * 2026-盈利预测-市盈率 (float64): -
    * 行业 (object): -
    * 日期 (object): -
    * 报告PDF链接 (object): -

    接口示例：
    import akshare as ak

stock_research_report_em_df = ak.stock_research_report_em(symbol="000001")
print(stock_research_report_em_df)

    """
    try:
        # 参数预处理
        params = {
            "symbol": symbol,
        }
        params = {k: v for k, v in params.items() if v is not None}

        # 调用AKShare接口（新增空参判断）
        if params:
            result = ak.stock_research_report_em(**params)
        else:
            result = ak.stock_research_report_em()
        result = result.head(10)
        # 结果处理
        if isinstance(result, pd.DataFrame):
            return handle_akshare_result(result)

        # 处理非DataFrame返回类型
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "type": type(result).__name__,
                "output_schema": [
                    {"name": "序号", "type": "int64"},
                    {"name": "股票代码", "type": "object"},
                    {"name": "股票简称", "type": "object"},
                    {"name": "报告名称", "type": "object"},
                    {"name": "东财评级", "type": "object"},
                    {"name": "机构", "type": "object"},
                    {"name": "近一月个股研报数", "type": "int64"},
                    {"name": "2024-盈利预测-收益", "type": "float64"},
                    {"name": "2024-盈利预测-市盈率", "type": "float64"},
                    {"name": "2025-盈利预测-收益", "type": "float64"},
                    {"name": "2025-盈利预测-市盈率", "type": "float64"},
                    {"name": "2026-盈利预测-收益", "type": "float64"},
                    {"name": "2026-盈利预测-市盈率", "type": "float64"},
                    {"name": "行业", "type": "object"},
                    {"name": "日期", "type": "object"},
                    {"name": "报告PDF链接", "type": "object"},
                ]
            }
        }

    except Exception as e:
        logger.error(f"[stock_research_report_em] 接口错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "code": "AKSHARE_ERROR",
            "message": f"数据接口异常: {str(e)}"
        }
async def run_server():
    """启动服务"""
    logger.info("Starting AKShare MCP service...")
    try:
        await mcp.run_sse_async()
    except Exception as e:
        logger.critical(f"服务启动失败: {str(e)}")
        raise

# 同花顺-公司大事-股东持股变动
@mcp.tool()
async def stock_shareholder_change_ths(
        symbol: str = None,
) -> Dict:
    """
    同花顺-公司大事-股东持股变动
    输入参数：
    * symbol (str): symbol="688981"

    输出参数：
    * 公告日期 (object): -
    * 变动股东 (object): -
    * 变动数量 (object): 注意单位: 股
    * 交易均价 (object): 注意单位: 元
    * 剩余股份总数 (object): 注意单位: 股
    * 变动期间 (object): -
    * 变动途径 (object): -

    接口示例：
    import akshare as ak

stock_shareholder_change_ths_df = ak.stock_shareholder_change_ths(symbol="688981")
print(stock_shareholder_change_ths_df)

    """
    try:
        # 参数预处理
        params = {
            "symbol": symbol,
        }
        params = {k: v for k, v in params.items() if v is not None}

        # 调用AKShare接口（新增空参判断）
        if params:
            result = ak.stock_shareholder_change_ths(**params)
        else:
            result = ak.stock_shareholder_change_ths()
        result = result.head(10)
        # 结果处理
        if isinstance(result, pd.DataFrame):
            return handle_akshare_result(result)

        # 处理非DataFrame返回类型
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "type": type(result).__name__,
                "output_schema": [
                    {"name": "公告日期", "type": "object"},
                    {"name": "变动股东", "type": "object"},
                    {"name": "变动数量", "type": "object"},
                    {"name": "交易均价", "type": "object"},
                    {"name": "剩余股份总数", "type": "object"},
                    {"name": "变动期间", "type": "object"},
                    {"name": "变动途径", "type": "object"},
                ]
            }
        }

    except Exception as e:
        logger.error(f"[stock_shareholder_change_ths] 接口错误: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "code": "AKSHARE_ERROR",
            "message": f"数据接口异常: {str(e)}"
        }

if __name__ == "__main__":
    asyncio.run(run_server())