from fastapi import APIRouter, Depends
from typing import Dict
from user_module.services.market_review_service import MarketReviewService
from utils.response_util import ResponseUtil
from module_admin.service.login_service import LoginService

router = APIRouter(prefix="/api/market", tags=["市场分析"])

@router.get("/daily-review")
async def get_daily_review():
    """
    获取每日复盘数据
    """
    try:
        data = await MarketReviewService.get_daily_review()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/index-data")
async def get_index_data():
    """
    获取大盘指数数据
    """
    try:
        data = await MarketReviewService.get_index_data()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/market-sentiment")
async def get_market_sentiment():
    """
    获取市场情绪数据
    """
    try:
        data = await MarketReviewService.get_market_sentiment()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/north-money")
async def get_north_money():
    """
    获取北向资金流向数据
    """
    try:
        data = await MarketReviewService.get_north_money_flow()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/fund-flow")
async def get_fund_flow():
    """
    获取大盘资金流向数据
    """
    try:
        data = await MarketReviewService.get_market_fund_flow()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/index-min-data")
async def get_index_min_data(symbol: str = "000001", period: str = "1"):
    """
    获取指数分时行情数据
    :param symbol: 指数代码，如"000001"表示上证指数
    :param period: 周期，可选值：'1', '5', '15', '30', '60'
    """
    try:
        data = await MarketReviewService.get_index_min_data(symbol=symbol, period=period)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/main-indices-min-data")
async def get_main_indices_min_data(period: str = "1"):
    """
    获取主要指数（上证指数、深证成指、创业板指）的分时行情数据
    :param period: 周期，可选值：'1', '5', '15', '30', '60'
    """
    try:
        # 获取三个主要指数的数据
        sh_data = await MarketReviewService.get_index_min_data(symbol="000001", period=period)
        sz_data = await MarketReviewService.get_index_min_data(symbol="399001", period=period)
        cyb_data = await MarketReviewService.get_index_min_data(symbol="399006", period=period)
        
        result = {
            "sh": sh_data,  # 上证指数
            "sz": sz_data,  # 深证成指
            "cyb": cyb_data  # 创业板指
        }
        
        return ResponseUtil.success(data=result)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/concept-board")
async def get_concept_board_data():
    """
    获取概念板块数据
    """
    try:
        data = await MarketReviewService.get_concept_board_data()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/sector-fund-flow")
async def get_sector_fund_flow():
    """
    获取板块资金流向数据
    """
    try:
        data = await MarketReviewService.get_sector_fund_flow()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/limit-stocks")
async def get_limit_up_down_stocks():
    """
    获取涨停跌停股票数据
    """
    try:
        data = await MarketReviewService.get_limit_up_down_stocks()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/lhb-data")
async def get_lhb_data():
    """
    获取龙虎榜数据
    """
    try:
        data = await MarketReviewService.get_lhb_data()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/market-analysis")
async def get_market_analysis():
    """
    获取市场分析数据（整合所有数据）
    """
    try:
        data = await MarketReviewService.get_market_analysis()
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e)) 