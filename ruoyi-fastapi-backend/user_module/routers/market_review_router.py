from fastapi import APIRouter, Depends, Request
from typing import Dict
from user_module.services.market_review_service import MarketReviewService
from utils.response_util import ResponseUtil
from module_admin.service.login_service import LoginService

router = APIRouter(prefix="/api/market", tags=["市场分析"])

@router.get("/daily-review")
async def get_daily_review(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_daily_review(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/index-data")
async def get_index_data(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_index_data(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/market-sentiment")
async def get_market_sentiment(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_market_sentiment(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/north-money")
async def get_north_money(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_north_money_flow(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/fund-flow")
async def get_fund_flow(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_market_fund_flow(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/index-min-data")
async def get_index_min_data(request: Request, symbol: str = "000001", period: str = "1"):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_index_min_data(redis, symbol=symbol, period=period)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/main-indices-min-data")
async def get_main_indices_min_data(request: Request, period: str = "1"):
    try:
        redis = request.app.state.redis
        sh_data = await MarketReviewService.get_index_min_data(redis, symbol="000001", period=period)
        sz_data = await MarketReviewService.get_index_min_data(redis, symbol="399001", period=period)
        cyb_data = await MarketReviewService.get_index_min_data(redis, symbol="399006", period=period)
        result = {
            "sh": sh_data,
            "sz": sz_data,
            "cyb": cyb_data
        }
        return ResponseUtil.success(data=result)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/concept-board")
async def get_concept_board_data(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_concept_board_data(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/sector-fund-flow")
async def get_sector_fund_flow(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_sector_fund_flow(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/limit-stocks")
async def get_limit_up_down_stocks(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_limit_up_down_stocks(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/lhb-data")
async def get_lhb_data(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_lhb_data(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/market-analysis")
async def get_market_analysis(request: Request):
    try:
        redis = request.app.state.redis
        data = await MarketReviewService.get_market_analysis(redis)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e)) 