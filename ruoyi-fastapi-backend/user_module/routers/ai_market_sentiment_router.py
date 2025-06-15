from fastapi import APIRouter, Depends
from typing import Dict
from user_module.services.ai_market_sentiment_service import AIMarketSentimentService
from utils.response_util import ResponseUtil
from module_admin.service.login_service import LoginService

router = APIRouter(prefix="/api/ai-market", tags=["AI市场情绪分析"])

@router.get("/sentiment-analysis")
async def get_sentiment_analysis(symbol: str = "sh000001"):
    """
    获取AI市场情绪分析数据
    """
    try:
        data = await AIMarketSentimentService.get_sentiment_analysis(symbol)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/prediction")
async def get_market_prediction(symbol: str = "sh000001"):
    """
    获取市场预测数据
    """
    try:
        data = await AIMarketSentimentService.get_market_prediction(symbol)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/news-analysis")
async def get_news_analysis(symbol: str = "sh000001"):
    """
    获取新闻分析数据
    """
    try:
        data = await AIMarketSentimentService.get_news_analysis(symbol)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/technical-indicators")
async def get_technical_indicators(symbol: str = "sh000001"):
    """
    获取技术指标分析数据
    """
    try:
        data = await AIMarketSentimentService.get_technical_indicators(symbol)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.get("/mean-reversion")
async def get_mean_reversion_analysis(symbol: str = "sh000001"):
    """
    获取均值回归分析数据
    """
    try:
        data = await AIMarketSentimentService.get_mean_reversion_analysis(symbol)
        return ResponseUtil.success(data=data)
    except Exception as e:
        return ResponseUtil.error(msg=str(e)) 