from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Optional
from datetime import datetime
from ..services.market_sentiment_analysis_service import MarketSentimentAnalysisService
from ..schemas.response import ResponseBase

router = APIRouter(prefix="/api/market/sentiment", tags=["市场情绪分析"])

@router.get("/train", response_model=ResponseBase)
async def train_model(
    stock_code: str,
    start_date: str,
    end_date: str,
    service: MarketSentimentAnalysisService = Depends()
) -> Dict:
    """
    训练LSTM模型
    :param stock_code: 股票代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param service: 市场情绪分析服务
    :return: 训练结果
    """
    try:
        result = service.train_model(stock_code, start_date, end_date)
        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['message'])
        return ResponseBase(code=200, msg="模型训练成功", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predict", response_model=ResponseBase)
async def predict_stock_price(
    stock_code: str,
    days: Optional[int] = 5,
    service: MarketSentimentAnalysisService = Depends()
) -> Dict:
    """
    预测股票价格
    :param stock_code: 股票代码
    :param days: 预测天数
    :param service: 市场情绪分析服务
    :return: 预测结果
    """
    try:
        result = await service.predict_stock_price(stock_code, days)
        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['message'])
        return ResponseBase(code=200, msg="预测成功", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis", response_model=ResponseBase)
async def analyze_market_sentiment(
    service: MarketSentimentAnalysisService = Depends()
) -> Dict:
    """
    分析市场情绪
    :param service: 市场情绪分析服务
    :return: 市场情绪分析结果
    """
    try:
        result = await service.analyze_market_sentiment()
        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['message'])
        return ResponseBase(code=200, msg="分析成功", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 