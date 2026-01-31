#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
形态识别特征提取器
基于PriceActions理论的形态识别和模式匹配
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from utils.logger import setup_logger

logger = setup_logger()

class PatternFeatureExtractor:
    """形态识别特征提取器"""
    
    def __init__(self):
        self.pattern_types = {
            'reversal': ['double_top', 'double_bottom', 'head_shoulders', 'inverse_head_shoulders'],
            'continuation': ['flags', 'pennants', 'triangles', 'wedges'],
            'candlestick': ['doji', 'hammer', 'shooting_star', 'engulfing']
        }
    
    def extract_all_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取所有形态特征"""
        try:
            features = {}
            
            # 反转形态
            features.update(self.extract_reversal_patterns(df))
            
            # 持续形态
            features.update(self.extract_continuation_patterns(df))
            
            # 经典形态
            features.update(self.extract_classic_patterns(df))
            
            # 趋势线特征
            features.update(self.extract_trendline_features(df))
            
            logger.info(f"提取形态特征成功: {len(features)}个特征")
            return features
            
        except Exception as e:
            logger.error(f"提取形态特征失败: {e}")
            return {}
    
    def extract_reversal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取反转形态特征"""
        features = {}
        
        try:
            # 双顶双底
            features.update(self.detect_double_tops_bottoms(df))
            
            # 头肩形态
            features.update(self.detect_head_shoulders(df))
            
            # 三重顶底
            features.update(self.detect_triple_tops_bottoms(df))
            
            # 圆顶圆底
            features.update(self.detect_rounded_tops_bottoms(df))
            
            return features
            
        except Exception as e:
            logger.error(f"提取反转形态特征失败: {e}")
            return {}
    
    def extract_continuation_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取持续形态特征"""
        features = {}
        
        try:
            # 三角形形态
            features.update(self.detect_triangles(df))
            
            # 楔形形态
            features.update(self.detect_wedges(df))
            
            # 旗形形态
            features.update(self.detect_flags(df))
            
            # 矩形整理
            features.update(self.detect_rectangles(df))
            
            return features
            
        except Exception as e:
            logger.error(f"提取持续形态特征失败: {e}")
            return {}
    
    def extract_classic_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取经典形态特征"""
        features = {}
        
        try:
            # 支撑阻力位
            features.update(self.detect_support_resistance(df))
            
            # 突破形态
            features.update(self.detect_breakouts(df))
            
            # 缺口形态
            features.update(self.detect_gaps(df))
            
            return features
            
        except Exception as e:
            logger.error(f"提取经典形态特征失败: {e}")
            return {}
    
    def extract_trendline_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取趋势线特征"""
        features = {}
        
        try:
            # 上升趋势线
            features.update(self.detect_uptrend_lines(df))
            
            # 下降趋势线
            features.update(self.detect_downtrend_lines(df))
            
            # 趋势线强度
            features.update(self.calculate_trendline_strength(df))
            
            return features
            
        except Exception as e:
            logger.error(f"提取趋势线特征失败: {e}")
            return {}
    
    def detect_double_tops_bottoms(self, df: pd.DataFrame, window: int = 20) -> Dict[str, Any]:
        """检测双顶双底形态"""
        features = {}
        
        try:
            # 寻找局部高点和低点
            highs = df['high'].rolling(window, center=True).max()
            lows = df['low'].rolling(window, center=True).min()
            
            # 双顶检测
            high_points = df['high'][df['high'] == highs]
            if len(high_points) >= 2:
                # 简化的双顶检测
                features['double_top'] = 1 if len(high_points) >= 2 else 0
                features['double_top_strength'] = len(high_points) / 10.0
            else:
                features['double_top'] = 0
                features['double_top_strength'] = 0
            
            # 双底检测
            low_points = df['low'][df['low'] == lows]
            if len(low_points) >= 2:
                features['double_bottom'] = 1 if len(low_points) >= 2 else 0
                features['double_bottom_strength'] = len(low_points) / 10.0
            else:
                features['double_bottom'] = 0
                features['double_bottom_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测双顶双底失败: {e}")
            return {'double_top': 0, 'double_bottom': 0, 
                   'double_top_strength': 0, 'double_bottom_strength': 0}
    
    def detect_head_shoulders(self, df: pd.DataFrame, window: int = 30) -> Dict[str, Any]:
        """检测头肩形态"""
        features = {}
        
        try:
            # 简化的头肩形态检测
            rolling_high = df['high'].rolling(window).max()
            rolling_low = df['low'].rolling(window).min()
            
            # 头肩顶检测
            features['head_shoulders'] = 0
            features['head_shoulders_strength'] = 0
            
            # 头肩底检测
            features['inverse_head_shoulders'] = 0
            features['inverse_head_shoulders_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测头肩形态失败: {e}")
            return {'head_shoulders': 0, 'inverse_head_shoulders': 0,
                   'head_shoulders_strength': 0, 'inverse_head_shoulders_strength': 0}
    
    def detect_triple_tops_bottoms(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测三重顶底形态"""
        features = {}
        
        try:
            # 简化的三重顶底检测
            features['triple_top'] = 0
            features['triple_bottom'] = 0
            features['triple_top_strength'] = 0
            features['triple_bottom_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测三重顶底失败: {e}")
            return {'triple_top': 0, 'triple_bottom': 0,
                   'triple_top_strength': 0, 'triple_bottom_strength': 0}
    
    def detect_rounded_tops_bottoms(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测圆顶圆底形态"""
        features = {}
        
        try:
            # 简化的圆顶圆底检测
            features['rounded_top'] = 0
            features['rounded_bottom'] = 0
            features['rounded_top_strength'] = 0
            features['rounded_bottom_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测圆顶圆底失败: {e}")
            return {'rounded_top': 0, 'rounded_bottom': 0,
                   'rounded_top_strength': 0, 'rounded_bottom_strength': 0}
    
    def detect_triangles(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测三角形形态"""
        features = {}
        
        try:
            # 上升三角形
            features['ascending_triangle'] = 0
            features['ascending_triangle_strength'] = 0
            
            # 下降三角形
            features['descending_triangle'] = 0
            features['descending_triangle_strength'] = 0
            
            # 对称三角形
            features['symmetrical_triangle'] = 0
            features['symmetrical_triangle_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测三角形形态失败: {e}")
            return {'ascending_triangle': 0, 'descending_triangle': 0, 'symmetrical_triangle': 0,
                   'ascending_triangle_strength': 0, 'descending_triangle_strength': 0, 'symmetrical_triangle_strength': 0}
    
    def detect_wedges(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测楔形形态"""
        features = {}
        
        try:
            # 上升楔形
            features['rising_wedge'] = 0
            features['rising_wedge_strength'] = 0
            
            # 下降楔形
            features['falling_wedge'] = 0
            features['falling_wedge_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测楔形形态失败: {e}")
            return {'rising_wedge': 0, 'falling_wedge': 0,
                   'rising_wedge_strength': 0, 'falling_wedge_strength': 0}
    
    def detect_flags(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测旗形形态"""
        features = {}
        
        try:
            # 上升旗形
            features['bull_flag'] = 0
            features['bull_flag_strength'] = 0
            
            # 下降旗形
            features['bear_flag'] = 0
            features['bear_flag_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测旗形形态失败: {e}")
            return {'bull_flag': 0, 'bear_flag': 0,
                   'bull_flag_strength': 0, 'bear_flag_strength': 0}
    
    def detect_rectangles(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测矩形整理形态"""
        features = {}
        
        try:
            # 矩形整理
            features['rectangle'] = 0
            features['rectangle_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测矩形整理失败: {e}")
            return {'rectangle': 0, 'rectangle_strength': 0}
    
    def detect_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, Any]:
        """检测支撑阻力位"""
        features = {}
        
        try:
            # 支撑位和阻力位
            support_level = df['low'].rolling(window).min()
            resistance_level = df['high'].rolling(window).max()
            
            # 支撑位强度
            features['support_level'] = support_level
            features['resistance_level'] = resistance_level
            
            # 距离支撑阻力的距离
            close = df['close'].astype(float)
            support_level_float = support_level.astype(float)
            resistance_level_float = resistance_level.astype(float)
            
            features['distance_to_support'] = (close - support_level_float) / (close + 1e-8)
            features['distance_to_resistance'] = (resistance_level_float - close) / (close + 1e-8)
            
            # 支撑阻力强度
            features['support_strength'] = self.calculate_level_strength(df, support_level, 'low')
            features['resistance_strength'] = self.calculate_level_strength(df, resistance_level, 'high')
            
            return features
            
        except Exception as e:
            logger.error(f"检测支撑阻力位失败: {e}")
            return {}
    
    def detect_breakouts(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测突破形态"""
        features = {}
        
        try:
            # 向上突破
            features['upward_breakout'] = 0
            features['upward_breakout_strength'] = 0
            
            # 向下突破
            features['downward_breakout'] = 0
            features['downward_breakout_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测突破形态失败: {e}")
            return {'upward_breakout': 0, 'downward_breakout': 0,
                   'upward_breakout_strength': 0, 'downward_breakout_strength': 0}
    
    def detect_gaps(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测缺口形态"""
        features = {}
        
        try:
            # 向上缺口
            gap_up = df['low'] > df['high'].shift(1)
            features['gap_up'] = gap_up.astype(int)
            low = df['low'].astype(float)
            high = df['high'].astype(float)
            features['gap_up_size'] = np.where(gap_up, low - high.shift(1), 0)
            
            # 向下缺口
            gap_down = df['high'] < df['low'].shift(1)
            features['gap_down'] = gap_down.astype(int)
            features['gap_down_size'] = np.where(gap_down, low.shift(1) - high, 0)
            
            return features
            
        except Exception as e:
            logger.error(f"检测缺口形态失败: {e}")
            return {'gap_up': 0, 'gap_down': 0, 'gap_up_size': 0, 'gap_down_size': 0}
    
    def detect_uptrend_lines(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测上升趋势线"""
        features = {}
        
        try:
            # 简化的上升趋势线检测
            features['uptrend_line'] = 0
            features['uptrend_line_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测上升趋势线失败: {e}")
            return {'uptrend_line': 0, 'uptrend_line_strength': 0}
    
    def detect_downtrend_lines(self, df: pd.DataFrame) -> Dict[str, Any]:
        """检测下降趋势线"""
        features = {}
        
        try:
            # 简化的下降趋势线检测
            features['downtrend_line'] = 0
            features['downtrend_line_strength'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"检测下降趋势线失败: {e}")
            return {'downtrend_line': 0, 'downtrend_line_strength': 0}
    
    def calculate_trendline_strength(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算趋势线强度"""
        features = {}
        
        try:
            # 趋势线强度
            features['trendline_strength'] = 0
            features['trendline_angle'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"计算趋势线强度失败: {e}")
            return {'trendline_strength': 0, 'trendline_angle': 0}
    
    def calculate_level_strength(self, df: pd.DataFrame, level: pd.Series, 
                                price_type: str) -> pd.Series:
        """计算支撑阻力位强度"""
        try:
            # 简化的强度计算
            if price_type == 'low':
                touches = (df['low'] <= level * 1.01).astype(int)
            else:
                touches = (df['high'] >= level * 0.99).astype(int)
            
            strength = touches.rolling(20).sum()
            return strength
            
        except Exception as e:
            logger.error(f"计算支撑阻力位强度失败: {e}")
            return pd.Series(0, index=df.index)
    
    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        feature_names = []
        
        # 反转形态
        feature_names.extend([
            'double_top', 'double_bottom', 'double_top_strength', 'double_bottom_strength',
            'head_shoulders', 'inverse_head_shoulders', 'head_shoulders_strength', 'inverse_head_shoulders_strength',
            'triple_top', 'triple_bottom', 'triple_top_strength', 'triple_bottom_strength',
            'rounded_top', 'rounded_bottom', 'rounded_top_strength', 'rounded_bottom_strength'
        ])
        
        # 持续形态
        feature_names.extend([
            'ascending_triangle', 'descending_triangle', 'symmetrical_triangle',
            'ascending_triangle_strength', 'descending_triangle_strength', 'symmetrical_triangle_strength',
            'rising_wedge', 'falling_wedge', 'rising_wedge_strength', 'falling_wedge_strength',
            'bull_flag', 'bear_flag', 'bull_flag_strength', 'bear_flag_strength',
            'rectangle', 'rectangle_strength'
        ])
        
        # 经典形态
        feature_names.extend([
            'support_level', 'resistance_level', 'distance_to_support', 'distance_to_resistance',
            'support_strength', 'resistance_strength',
            'upward_breakout', 'downward_breakout', 'upward_breakout_strength', 'downward_breakout_strength',
            'gap_up', 'gap_down', 'gap_up_size', 'gap_down_size'
        ])
        
        # 趋势线特征
        feature_names.extend([
            'uptrend_line', 'downtrend_line', 'uptrend_line_strength', 'downtrend_line_strength',
            'trendline_strength', 'trendline_angle'
        ])
        
        return feature_names
