#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特征工程标准化工具
解决数值溢出问题，确保特征值在合理范围内
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger


class FeatureNormalizer:
    """特征标准化器"""
    
    def __init__(self):
        # 定义各种特征值的合理范围
        self.value_limits = {
            # OBV相关特征
            'obv': {'min': -1e8, 'max': 1e8, 'method': 'log_scale'},
            'obv_ma': {'min': -1e8, 'max': 1e8, 'method': 'log_scale'},
            'obv_ratio': {'min': 0.01, 'max': 100, 'method': 'clip'},
            
            # 比例特征
            'shadow_ratio': {'min': 0.01, 'max': 100, 'method': 'clip'},
            'pressure_ratio': {'min': 0.01, 'max': 100, 'method': 'clip'},
            'price_vwap_ratio': {'min': 0.01, 'max': 100, 'method': 'clip'},
            
            # 压力特征
            'buying_pressure': {'min': 0, 'max': 1, 'method': 'clip'},
            'selling_pressure': {'min': 0, 'max': 1, 'method': 'clip'},
            
            # 影线特征
            'upper_shadow': {'min': 0, 'max': 1, 'method': 'clip'},
            'lower_shadow': {'min': 0, 'max': 1, 'method': 'clip'},
            
            # 其他可能溢出的特征
            'volume_ratio': {'min': 0.01, 'max': 100, 'method': 'clip'},
            'price_change_ratio': {'min': -10, 'max': 10, 'method': 'clip'},
        }
        
        # 默认范围（对于未定义的特征）
        self.default_limits = {'min': -1e6, 'max': 1e6, 'method': 'clip'}
        
        logger.info("特征标准化器初始化完成")
        logger.info(f"定义了 {len(self.value_limits)} 个特征的限制范围")
    
    def normalize_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """标准化特征值"""
        normalized_features = {}
        
        for feature_name, feature_value in features.items():
            try:
                # 跳过非数值特征
                if not isinstance(feature_value, (int, float, np.number)):
                    normalized_features[feature_name] = feature_value
                    continue
                
                # 跳过NaN和无穷大值
                if np.isnan(feature_value) or np.isinf(feature_value):
                    normalized_features[feature_name] = 0.0
                    continue
                
                # 获取该特征的限制范围
                limits = self.value_limits.get(feature_name, self.default_limits)
                
                # 应用标准化方法
                normalized_value = self._apply_normalization(
                    feature_value, limits, feature_name
                )
                
                normalized_features[feature_name] = normalized_value
                
            except Exception as e:
                logger.warning(f"特征 {feature_name} 标准化失败: {e}")
                normalized_features[feature_name] = 0.0
        
        return normalized_features
    
    def _apply_normalization(self, value: float, limits: Dict[str, Any], 
                           feature_name: str) -> float:
        """应用具体的标准化方法"""
        method = limits.get('method', 'clip')
        min_val = limits.get('min', -1e6)
        max_val = limits.get('max', 1e6)
        
        if method == 'clip':
            return self._clip_value(value, min_val, max_val)
        elif method == 'log_scale':
            return self._log_scale_value(value, min_val, max_val)
        elif method == 'tanh_scale':
            return self._tanh_scale_value(value)
        else:
            return self._clip_value(value, min_val, max_val)
    
    def _clip_value(self, value: float, min_val: float, max_val: float) -> float:
        """简单截断方法"""
        return np.clip(value, min_val, max_val)
    
    def _log_scale_value(self, value: float, min_val: float, max_val: float) -> float:
        """对数缩放方法（适用于OBV等累积指标）"""
        if value == 0:
            return 0.0
        
        # 使用log1p避免log(0)的问题
        if value > 0:
            log_value = np.log1p(value)
        else:
            log_value = -np.log1p(-value)
        
        # 缩放到合理范围
        return np.clip(log_value, min_val, max_val)
    
    def _tanh_scale_value(self, value: float) -> float:
        """tanh缩放方法（压缩到[-1,1]）"""
        # 先缩放到合理范围，再应用tanh
        scaled_value = value / 1000000  # 根据实际情况调整缩放因子
        return np.tanh(scaled_value)
    
    def safe_divide(self, numerator: float, denominator: float, 
                   max_ratio: float = 100.0) -> float:
        """安全的除法运算，避免除零和溢出"""
        if abs(denominator) < 1e-8:
            return 1.0  # 避免除零
        
        ratio = numerator / denominator
        return np.clip(ratio, 0.01, max_ratio)
    
    def get_feature_statistics(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """获取特征统计信息"""
        stats = {
            'total_features': len(features),
            'normalized_features': 0,
            'clipped_features': 0,
            'log_scaled_features': 0,
            'out_of_range_features': []
        }
        
        for feature_name, feature_value in features.items():
            if not isinstance(feature_value, (int, float, np.number)):
                continue
            
            if np.isnan(feature_value) or np.isinf(feature_value):
                continue
            
            limits = self.value_limits.get(feature_name, self.default_limits)
            min_val = limits.get('min', -1e6)
            max_val = limits.get('max', 1e6)
            
            if feature_value < min_val or feature_value > max_val:
                stats['out_of_range_features'].append({
                    'name': feature_name,
                    'value': feature_value,
                    'min': min_val,
                    'max': max_val
                })
        
        return stats


def normalize_feature_values(features: Dict[str, Any]) -> Dict[str, Any]:
    """便捷的特征标准化函数"""
    normalizer = FeatureNormalizer()
    return normalizer.normalize_features(features)


def safe_ratio_calculation(numerator: float, denominator: float, 
                          max_ratio: float = 100.0) -> float:
    """安全的比例计算"""
    normalizer = FeatureNormalizer()
    return normalizer.safe_divide(numerator, denominator, max_ratio)
