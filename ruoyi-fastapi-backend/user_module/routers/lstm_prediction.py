# -*- coding: utf-8 -*-
"""
LSTM股票预测路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import pandas as pd
import akshare as ak
from datetime import datetime

from user_module.services.lstm_prediction_service import LSTMPredictionService

router = APIRouter(prefix="/api/stock/lstm", tags=["LSTM股票预测"])

# 全局LSTM服务实例（用于保持模型状态）
lstm_services = {}
# 记录每个股票的训练配置（包括复权类型）
lstm_configs = {}


class LSTMTrainRequest(BaseModel):
    """LSTM训练请求 v7"""
    symbol: str = Field(..., description="股票代码")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    adjust_type: str = Field(default="hfq", description="复权类型: qfq=前复权, hfq=后复权, normal=不复权")
    lookback_options: List[int] = Field(default=[30, 45, 60], description="回顾窗口选项（v7默认：中期窗口）")
    epochs: int = Field(default=150, ge=50, le=500, description="训练轮次（v7默认：150）")
    batch_size: int = Field(default=32, ge=8, le=128, description="批次大小（v7默认：32）")
    learning_rate: float = Field(default=0.0005, ge=0.0001, le=0.01, description="学习率（v7默认：0.0005）")
    test_size: float = Field(default=0.15, ge=0.05, le=0.3, description="测试集比例（v7默认：0.15）")
    validation_split: float = Field(default=0.2, ge=0.1, le=0.3, description="验证集比例")
    use_sample_weights: bool = Field(default=True, description="是否使用样本权重")
    sample_weight_decay: float = Field(default=0.997, ge=0.990, le=0.999, description="样本权重衰减率（v7默认：0.997）")
    selected_features: Optional[List[str]] = Field(default=None, description="选择的特征列表")
    # v7新增参数
    l2_reg: float = Field(default=0.001, ge=0, le=0.01, description="L2正则化系数")
    dropout_rate: float = Field(default=0.4, ge=0.2, le=0.6, description="Dropout率")
    use_directional_loss: bool = Field(default=True, description="是否使用方向感知损失")
    direction_alpha: float = Field(default=0.5, ge=0.1, le=0.9, description="方向损失权重")


class LSTMPredictRequest(BaseModel):
    """LSTM预测请求"""
    symbol: str = Field(..., description="股票代码")
    future_steps: int = Field(default=20, ge=5, le=60, description="预测未来天数")


class LSTMFeaturesResponse(BaseModel):
    """特征列表响应"""
    data: Dict[str, List[Dict[str, Any]]]


@router.get("/features", response_model=LSTMFeaturesResponse, summary="获取可用的训练因子列表")
async def get_lstm_features():
    """
    获取LSTM训练可用的因子列表
    
    Returns:
        特征列表，按类别分组
    """
    try:
        features = LSTMPredictionService.get_available_features()
        return {"data": features}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取特征列表失败: {str(e)}")


@router.post("/train", summary="训练LSTM模型")
async def train_lstm_model(request: LSTMTrainRequest):
    """
    训练LSTM股票预测模型
    
    Args:
        request: 训练请求参数
        
    Returns:
        训练结果
    """
    try:
        # 获取股票数据
        print(f"开始获取股票数据: {request.symbol}")
        # 使用请求中指定的复权类型
        adjust_map = {
            'qfq': 'qfq',
            'hfq': 'hfq', 
            'normal': ''
        }
        adjust = adjust_map.get(request.adjust_type, 'hfq')
        
        df = ak.stock_zh_a_hist(
            symbol=request.symbol,
            period="daily",
            start_date=request.start_date.replace('-', ''),
            end_date=request.end_date.replace('-', ''),
            adjust=adjust
        )
        
        if df is None or len(df) == 0:
            raise HTTPException(status_code=404, detail="未找到股票数据")
        
        # 重命名列（akshare返回的列名是中文）
        column_map = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        }
        df = df.rename(columns=column_map)
        
        # 创建LSTM服务实例
        lstm_service = LSTMPredictionService()
        
        # 准备训练配置（v7参数）
        config = {
            'lookback_options': request.lookback_options,
            'epochs': request.epochs,
            'batch_size': request.batch_size,
            'learning_rate': request.learning_rate,
            'test_size': request.test_size,
            'validation_split': request.validation_split,
            'use_sample_weights': request.use_sample_weights,
            'sample_weight_decay': request.sample_weight_decay,
            'selected_features': request.selected_features,
            # v7新增参数
            'l2_reg': request.l2_reg,
            'dropout_rate': request.dropout_rate,
            'use_directional_loss': request.use_directional_loss,
            'direction_alpha': request.direction_alpha
        }
        
        print(f"开始训练LSTM模型...")
        print(f"  数据范围: {request.start_date} 至 {request.end_date}")
        print(f"  数据条数: {len(df)}")
        print(f"  训练配置: {config}")
        
        # 训练模型
        result = lstm_service.train(df, config)
        
        # 保存服务实例和配置（用于后续预测）
        lstm_services[request.symbol] = lstm_service
        lstm_configs[request.symbol] = {
            'adjust_type': request.adjust_type,
            'start_date': request.start_date,
            'end_date': request.end_date
        }
        
        print(f"模型训练完成！")
        print(f"  复权类型: {request.adjust_type}")
        print(f"  最佳回顾窗口: {result['best_lookback']}天")
        print(f"  R² Score: {result['r2_score']:.4f}")
        
        return {
            "code": 200,
            "msg": "训练成功",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"模型训练失败: {str(e)}")


@router.post("/predict", summary="预测未来走势")
async def predict_future_prices(request: LSTMPredictRequest):
    """
    使用训练好的LSTM模型预测未来价格
    
    Args:
        request: 预测请求参数
        
    Returns:
        预测结果
    """
    try:
        # 检查是否已训练模型
        if request.symbol not in lstm_services:
            raise HTTPException(
                status_code=400, 
                detail="该股票尚未训练模型，请先调用 /train 接口训练模型"
            )
        
        lstm_service = lstm_services[request.symbol]
        
        # 获取训练时使用的复权类型
        config = lstm_configs.get(request.symbol, {})
        adjust_type = config.get('adjust_type', 'hfq')
        
        # 使用与训练时相同的复权类型
        adjust_map = {
            'qfq': 'qfq',
            'hfq': 'hfq',
            'normal': ''
        }
        adjust = adjust_map.get(adjust_type, 'hfq')
        
        # 获取最新数据用于预测
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - pd.Timedelta(days=365)).strftime('%Y%m%d')
        
        print(f"获取最新数据用于预测: {request.symbol} (复权类型: {adjust_type})")
        df = ak.stock_zh_a_hist(
            symbol=request.symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
        
        if df is None or len(df) == 0:
            raise HTTPException(status_code=404, detail="未找到股票数据")
        
        # 重命名列
        column_map = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        }
        df = df.rename(columns=column_map)
        
        print(f"开始预测未来{request.future_steps}天...")
        
        # 预测
        result = lstm_service.predict_future(df, future_steps=request.future_steps)
        
        print(f"预测完成！")
        print(f"  当前价格: {result['current_price']:.2f}")
        print(f"  预测趋势: {result['trend']}")
        
        return {
            "code": 200,
            "msg": "预测成功",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"预测失败: {str(e)}")


@router.get("/model-info/{symbol}", summary="获取模型信息")
async def get_model_info(symbol: str):
    """
    获取指定股票的模型训练信息
    
    Args:
        symbol: 股票代码
        
    Returns:
        模型信息
    """
    try:
        if symbol not in lstm_services:
            return {
                "code": 200,
                "msg": "成功",
                "data": {
                    "trained": False,
                    "message": "该股票尚未训练模型"
                }
            }
        
        lstm_service = lstm_services[symbol]
        
        return {
            "code": 200,
            "msg": "成功",
            "data": {
                "trained": True,
                "best_lookback": lstm_service.best_lookback,
                "feature_count": len(lstm_service.feature_columns),
                "features": lstm_service.feature_columns
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")

