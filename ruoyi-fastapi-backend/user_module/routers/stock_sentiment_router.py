from fastapi import APIRouter, Depends, Body
from typing import Dict, List
from user_module.analyzer.market_clustering import MarketRegimeAnalyzer
from user_module.analyzer.data_preprocessor import MarketDataPreprocessor
from user_module.analyzer.strategy_engine import StrategyEngine
from user_module.services.stock_hist_service import StockHistService
from utils.response_util import ResponseUtil
import pandas as pd
import numpy as np

router = APIRouter(prefix="/api/stock", tags=["市场情绪分析"])

@router.post("/sentiment")
async def analyze_market_sentiment(
    symbol: str = Body(...),
    start_date: str = Body(...),
    end_date: str = Body(...),
    params: Dict = Body(...)
):
    """分析市场情绪"""
    try:
        # 获取历史数据
        df = await StockHistService.get_stock_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust='hfq'
        )
        
        # 数据预处理
        preprocessor = MarketDataPreprocessor()
        processed_data = preprocessor.preprocess_data(df)
        
        # 市场机制分析
        analyzer = MarketRegimeAnalyzer(
            window_size=params.get('windowSize', 30),
            stride=5,
            n_clusters=params.get('nClusters', 3)
        )
        
        # 检测市场机制
        regime_series = analyzer.detect_regime(processed_data['raw_returns'])
        
        # 分析机制转换
        regime_analysis = analyzer.analyze_regime_transitions(regime_series)
        
        # 生成交易信号
        strategy_engine = StrategyEngine()
        signals = strategy_engine.generate_regime_signals(regime_analysis)
        
        # 确保波动率是标量值
        volatility = processed_data['volatility']
        if isinstance(volatility, (pd.Series, np.ndarray)):
            volatility = float(volatility.iloc[-1] if len(volatility) > 0 else 0.0)
        else:
            volatility = float(volatility)
            
        # 生成波动率信号
        vol_signals = strategy_engine.generate_volatility_signals(volatility)
        
        # 合并信号
        all_signals = strategy_engine.combine_signals([signals, vol_signals])
        
        # 提取特征用于聚类可视化
        features = analyzer._extract_features(processed_data['raw_returns'])
        
        # 确保相关性数据是列表格式且没有NaN值
        correlation_data = processed_data['correlation']
        if isinstance(correlation_data, pd.DataFrame):
            correlation_labels = correlation_data.columns.tolist()
            correlation_values = correlation_data.fillna(0.0).values.tolist()
        else:
            correlation_labels = []
            correlation_values = []
        
        # 确保特征数据是有效的数值
        features = analyzer._extract_features(processed_data['raw_returns'])
        features = np.nan_to_num(features, nan=0.0)
        
        return ResponseUtil.success(data={
            'regimes': [
                {
                    'id': i,
                    'name': f'机制 {i+1}',
                    'type': 'normal',
                    'volatility': float(np.nan_to_num(volatility, nan=0.0)),
                    'correlation': {
                        'labels': correlation_labels,
                        'data': correlation_values
                    }
                }
                for i in range(len(regime_series.unique()))
            ],
            'signals': all_signals,
            'clusters': [
                {
                    'x': float(features[0]),  # 均值
                    'y': float(features[1]),  # 标准差
                    'z': float(features[4])   # 平均波动率
                }
            ]
        })
        
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.post("/regime")
async def get_market_regime(
    symbol: str = Body(...),
    start_date: str = Body(...),
    end_date: str = Body(...)
):
    """获取市场机制分析"""
    try:
        # 获取历史数据
        df = await StockHistService.get_stock_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust='qfq'
        )
        
        # 数据预处理
        preprocessor = MarketDataPreprocessor()
        processed_data = preprocessor.preprocess_data(df)
        
        # 市场机制分析
        analyzer = MarketRegimeAnalyzer()
        regime_series = analyzer.detect_regime(processed_data['raw_returns'])
        regime_analysis = analyzer.analyze_regime_transitions(regime_series)
        
        return ResponseUtil.success(data=regime_analysis)
        
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.post("/signals")
async def get_trading_signals(
    symbol: str = Body(...),
    start_date: str = Body(...),
    end_date: str = Body(...)
):
    """获取交易信号"""
    try:
        # 获取历史数据
        df = await StockHistService.get_stock_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust='qfq'
        )
        
        # 数据预处理
        preprocessor = MarketDataPreprocessor()
        processed_data = preprocessor.preprocess_data(df)
        
        # 生成信号
        strategy_engine = StrategyEngine()
        signals = strategy_engine.generate_volatility_signals(
            processed_data['features']['volatility']
        )
        
        return ResponseUtil.success(data=signals)
        
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.post("/transitions")
async def get_regime_transitions(
    symbol: str = Body(...),
    start_date: str = Body(...),
    end_date: str = Body(...)
):
    """获取机制转换历史"""
    try:
        # 获取历史数据
        df = await StockHistService.get_stock_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust='qfq'
        )
        
        # 数据预处理
        preprocessor = MarketDataPreprocessor()
        processed_data = preprocessor.preprocess_data(df)
        
        # 市场机制分析
        analyzer = MarketRegimeAnalyzer()
        regime_series = analyzer.detect_regime(processed_data['raw_returns'])
        regime_analysis = analyzer.analyze_regime_transitions(regime_series)
        
        return ResponseUtil.success(data=regime_analysis['transitions'])
        
    except Exception as e:
        return ResponseUtil.error(msg=str(e))

@router.post("/correlation")
async def get_correlation_analysis(
    symbol: str = Body(...),
    start_date: str = Body(...),
    end_date: str = Body(...)
):
    """获取相关性分析"""
    try:
        # 获取历史数据
        df = await StockHistService.get_stock_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust='qfq'
        )
        
        # 数据预处理
        preprocessor = MarketDataPreprocessor()
        processed_data = preprocessor.preprocess_data(df)
        
        return ResponseUtil.success(data={
            'correlation_matrix': processed_data['correlation'].to_dict(),
            'features': processed_data['features']
        })
        
    except Exception as e:
        return ResponseUtil.error(msg=str(e)) 