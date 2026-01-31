#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格行为特征提取器
基于PriceActions理论的价格行为特征计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from utils.logger import setup_logger

logger = setup_logger()

# 尝试导入talib，如果失败则使用替代方案
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib未安装，将使用替代方案")

class PriceActionFeatureExtractor:
    """价格行为特征提取器"""
    
    def __init__(self):
        self.feature_categories = {
            'candle_patterns': ['doji', 'hammer', 'shooting_star', 'engulfing', 'harami'],
            'body_analysis': ['body_size', 'body_ratio', 'shadow_ratio'],
            'pressure_analysis': ['buying_pressure', 'selling_pressure', 'pressure_ratio']
        }
    
    def extract_all_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取所有价格行为特征"""
        try:
            features = {}
            
            # 基础价格行为特征
            features.update(self.extract_candle_features(df))
            features.update(self.extract_body_features(df))
            features.update(self.extract_pressure_features(df))
            features.update(self.extract_shadow_features(df))
            features.update(self.extract_position_features(df))
            
            # 趋势特征
            features.update(self.extract_trend_features(df))
            
            # 回调特征
            features.update(self.extract_pullback_features(df))
            
            # 支撑阻力特征
            features.update(self.extract_support_resistance_features(df))
            
            logger.info(f"提取价格行为特征成功: {len(features)}个特征")
            return features
            
        except Exception as e:
            logger.error(f"提取价格行为特征失败: {e}")
            return {}
    
    def extract_candle_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取K线形态特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            open_price = df['open'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            close = df['close'].astype(float)
            
            if TALIB_AVAILABLE:
                # 使用TA-Lib识别经典K线形态
                features['doji'] = talib.CDLDOJI(open_price, high, low, close)
                features['hammer'] = talib.CDLHAMMER(open_price, high, low, close)
                features['shooting_star'] = talib.CDLSHOOTINGSTAR(open_price, high, low, close)
                features['engulfing'] = talib.CDLENGULFING(open_price, high, low, close)
                features['harami'] = talib.CDLHARAMI(open_price, high, low, close)
            else:
                # 使用替代方案
                features['doji'] = self._detect_doji(df)
                features['hammer'] = self._detect_hammer(df)
                features['shooting_star'] = self._detect_shooting_star(df)
                features['engulfing'] = self._detect_engulfing(df)
                features['harami'] = self._detect_harami(df)
            
            # 计算形态强度
            features['pattern_strength'] = np.abs(features['doji']) + np.abs(features['hammer']) + \
                                         np.abs(features['shooting_star']) + np.abs(features['engulfing'])
            
            return features
            
        except Exception as e:
            logger.error(f"提取K线形态特征失败: {e}")
            return {}
    
    def extract_body_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取K线实体特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            close = df['close'].astype(float)
            open_price = df['open'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            
            # 实体大小
            body_size = np.abs(close - open_price)
            features['body_size'] = body_size / (open_price + 1e-8)
            
            # 实体比例
            total_range = high - low
            features['body_ratio'] = body_size / (total_range + 1e-8)
            
            # 实体方向
            features['body_direction'] = np.where(close > open_price, 1, -1)
            
            # 实体强度
            features['body_strength'] = body_size / (open_price + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"提取K线实体特征失败: {e}")
            return {}
    
    def extract_pressure_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取买压卖压特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            close = df['close'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            
            # 买压计算
            buying_pressure = (close - low) / (high - low + 1e-8)
            features['buying_pressure'] = buying_pressure
            
            # 卖压计算
            selling_pressure = (high - close) / (high - low + 1e-8)
            features['selling_pressure'] = selling_pressure
            
            # 压力比例 - 安全计算
            if isinstance(selling_pressure, (int, float)) and selling_pressure > 1e-8:
                pressure_ratio = buying_pressure / selling_pressure
                features['pressure_ratio'] = np.clip(pressure_ratio, 0.01, 100)
            else:
                features['pressure_ratio'] = 1.0
            
            # 压力强度
            features['pressure_strength'] = np.abs(buying_pressure - selling_pressure)
            
            # 压力平衡
            features['pressure_balance'] = np.where(
                buying_pressure > selling_pressure, 1, 
                np.where(buying_pressure < selling_pressure, -1, 0)
            )
            
            return features
            
        except Exception as e:
            logger.error(f"提取买压卖压特征失败: {e}")
            return {}
    
    def extract_shadow_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取影线特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            close = df['close'].astype(float)
            open_price = df['open'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            
            # 上影线
            upper_shadow = high - np.maximum(open_price, close)
            features['upper_shadow'] = upper_shadow / (high - low + 1e-8)
            
            # 下影线
            lower_shadow = np.minimum(open_price, close) - low
            features['lower_shadow'] = lower_shadow / (high - low + 1e-8)
            
            # 影线比例 - 安全计算
            if isinstance(features['lower_shadow'], (int, float)) and features['lower_shadow'] > 1e-8:
                shadow_ratio = features['upper_shadow'] / features['lower_shadow']
                features['shadow_ratio'] = np.clip(shadow_ratio, 0.01, 100)
            else:
                features['shadow_ratio'] = 1.0
            
            # 影线强度
            features['shadow_strength'] = features['upper_shadow'] + features['lower_shadow']
            
            # 影线平衡
            features['shadow_balance'] = features['upper_shadow'] - features['lower_shadow']
            
            return features
            
        except Exception as e:
            logger.error(f"提取影线特征失败: {e}")
            return {}
    
    def extract_position_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取价格位置特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            close = df['close'].astype(float)
            open_price = df['open'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            
            # 收盘价位置
            features['close_position'] = (close - low) / (high - low + 1e-8)
            
            # 开盘价位置
            features['open_position'] = (open_price - low) / (high - low + 1e-8)
            
            # 价格中心位置
            price_center = (high + low) / 2
            features['center_position'] = (close - price_center) / (high - low + 1e-8)
            
            # 价格偏离度
            features['price_deviation'] = np.abs(close - price_center) / (high - low + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"提取价格位置特征失败: {e}")
            return {}
    
    def extract_trend_features(self, df: pd.DataFrame, periods: List[int] = [5, 10, 20, 50]) -> Dict[str, Any]:
        """提取趋势特征"""
        features = {}
        
        try:
            for period in periods:
                # 趋势方向
                ma = df['close'].rolling(period).mean()
                features[f'trend_direction_{period}'] = np.where(ma > ma.shift(1), 1, -1)
                
                # 趋势强度
                features[f'trend_strength_{period}'] = np.abs(ma - ma.shift(1)) / (ma.shift(1) + 1e-8)
                
                # 趋势一致性
                trend_consistency = df['close'].rolling(period).apply(
                    lambda x: len(x[x > x.shift(1)]) / len(x) if len(x) > 1 else 0.5
                )
                features[f'trend_consistency_{period}'] = trend_consistency
                
                # 趋势斜率
                features[f'trend_slope_{period}'] = (ma - ma.shift(period)) / period
                
            return features
            
        except Exception as e:
            logger.error(f"提取趋势特征失败: {e}")
            return {}
    
    def extract_pullback_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取回调特征"""
        features = {}
        
        try:
            # 回调深度
            rolling_high = df['high'].rolling(20).max()
            features['pullback_depth'] = (rolling_high - df['close']) / (rolling_high + 1e-8)
            
            # 回调强度
            close = df['close'].astype(float)
            features['pullback_strength'] = (close - close.shift(1)) / (close.shift(1) + 1e-8)
            
            # 回调持续时间
            price_change = df['close'].diff()
            pullback_periods = (price_change < 0).astype(int)
            features['pullback_duration'] = pullback_periods.groupby(
                (pullback_periods != pullback_periods.shift()).cumsum()
            ).cumsum()
            
            return features
            
        except Exception as e:
            logger.error(f"提取回调特征失败: {e}")
            return {}
    
    def extract_support_resistance_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取支撑阻力特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            close = df['close'].astype(float)
            
            # 支撑位和阻力位
            support_level = df['low'].rolling(20).min()
            resistance_level = df['high'].rolling(20).max()
            
            # 距离支撑阻力的距离
            features['distance_to_support'] = (close - support_level) / (close + 1e-8)
            features['distance_to_resistance'] = (resistance_level - close) / (close + 1e-8)
            
            # 突破概率
            features['breakout_probability'] = 1 / (1 + features['distance_to_resistance'])
            
            # 支撑阻力强度
            features['support_strength'] = support_level
            features['resistance_strength'] = resistance_level
            
            # 价格位置
            features['price_position'] = (df['close'] - support_level) / (resistance_level - support_level + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"提取支撑阻力特征失败: {e}")
            return {}
    
    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        feature_names = []
        
        # 基础特征
        feature_names.extend([
            'doji', 'hammer', 'shooting_star', 'engulfing', 'harami',
            'pattern_strength',  # K线形态强度
            'body_size', 'body_ratio', 'body_direction', 'body_strength',
            'buying_pressure', 'selling_pressure', 'pressure_ratio', 'pressure_strength',
            'pressure_balance',  # 压力平衡
            'upper_shadow', 'lower_shadow', 'shadow_ratio', 'shadow_strength',
            'shadow_balance',  # 影线平衡
            'close_position', 'open_position', 'center_position', 'price_deviation'
        ])
        
        # 趋势特征
        for period in [5, 10, 20, 50]:
            feature_names.extend([
                f'trend_direction_{period}', f'trend_strength_{period}',
                f'trend_consistency_{period}', f'trend_slope_{period}'
            ])
        
        # 回调特征
        feature_names.extend([
            'pullback_depth', 'pullback_strength', 'pullback_duration'
        ])
        
        # 支撑阻力特征
        feature_names.extend([
            'distance_to_support', 'distance_to_resistance', 'breakout_probability',
            'support_strength', 'resistance_strength', 'price_position'
        ])
        
        return feature_names
    
    def _detect_doji(self, df: pd.DataFrame) -> pd.Series:
        """检测十字星形态（替代方案）"""
        body_size = np.abs(df['close'] - df['open'])
        total_range = df['high'] - df['low']
        doji_ratio = body_size / (total_range + 1e-8)
        return (doji_ratio < 0.1).astype(int)
    
    def _detect_hammer(self, df: pd.DataFrame) -> pd.Series:
        """检测锤子形态（替代方案）"""
        body_size = np.abs(df['close'] - df['open'])
        lower_shadow = np.minimum(df['open'], df['close']) - df['low']
        upper_shadow = df['high'] - np.maximum(df['open'], df['close'])
        total_range = df['high'] - df['low']
        
        # 锤子条件：下影线长，上影线短，实体小
        hammer_condition = (
            (lower_shadow > 2 * body_size) &
            (upper_shadow < body_size) &
            (body_size > 0) &
            (total_range > 0)
        )
        return hammer_condition.astype(int)
    
    def _detect_shooting_star(self, df: pd.DataFrame) -> pd.Series:
        """检测流星形态（替代方案）"""
        body_size = np.abs(df['close'] - df['open'])
        lower_shadow = np.minimum(df['open'], df['close']) - df['low']
        upper_shadow = df['high'] - np.maximum(df['open'], df['close'])
        total_range = df['high'] - df['low']
        
        # 流星条件：上影线长，下影线短，实体小
        shooting_star_condition = (
            (upper_shadow > 2 * body_size) &
            (lower_shadow < body_size) &
            (body_size > 0) &
            (total_range > 0)
        )
        return shooting_star_condition.astype(int)
    
    def _detect_engulfing(self, df: pd.DataFrame) -> pd.Series:
        """检测吞没形态（替代方案）"""
        prev_open = df['open'].shift(1)
        prev_close = df['close'].shift(1)
        
        # 前一根K线实体
        prev_body = np.abs(prev_close - prev_open)
        # 当前K线实体
        curr_body = np.abs(df['close'] - df['open'])
        
        # 吞没条件：当前实体完全包含前一根实体
        engulfing_condition = (
            (curr_body > prev_body) &
            (df['close'] > prev_close) &  # 看涨吞没
            (df['open'] < prev_open)
        ) | (
            (curr_body > prev_body) &
            (df['close'] < prev_close) &  # 看跌吞没
            (df['open'] > prev_open)
        )
        return engulfing_condition.astype(int)
    
    def _detect_harami(self, df: pd.DataFrame) -> pd.Series:
        """检测孕线形态（替代方案）"""
        prev_open = df['open'].shift(1)
        prev_close = df['close'].shift(1)
        
        # 前一根K线实体
        prev_body = np.abs(prev_close - prev_open)
        # 当前K线实体
        curr_body = np.abs(df['close'] - df['open'])
        
        # 孕线条件：当前实体被前一根实体包含
        harami_condition = (
            (curr_body < prev_body) &
            (df['close'] < prev_close) &  # 看涨孕线
            (df['open'] > prev_open)
        ) | (
            (curr_body < prev_body) &
            (df['close'] > prev_close) &  # 看跌孕线
            (df['open'] < prev_open)
        )
        return harami_condition.astype(int)
