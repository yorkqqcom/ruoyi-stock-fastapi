#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流特征提取器
基于PriceActions理论的资金流向和主力资金特征计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from utils.logger import setup_logger

logger = setup_logger()

class MoneyFlowFeatureExtractor:
    """资金流特征提取器"""
    
    def __init__(self):
        self.feature_categories = {
            'basic_moneyflow': ['net_inflow', 'net_inflow_ratio', 'inflow_strength'],
            'main_force': ['main_force_ratio', 'main_force_buy_ratio', 'main_force_sell_ratio'],
            'retail': ['retail_ratio', 'retail_buy_ratio', 'retail_sell_ratio'],
            'fund_structure': ['fund_structure_balance', 'fund_flow_direction', 'fund_flow_consistency']
        }
    
    def _get_scalar_value(self, data, key, default=0):
        """获取标量值的辅助函数"""
        try:
            # 如果是DataFrame，使用列访问方式
            if isinstance(data, pd.DataFrame):
                if key in data.columns:
                    value = data[key].iloc[0] if len(data) > 0 else default
                    # 处理NaN和None值
                    if pd.isna(value) or value is None:
                        return float(default)
                    return float(value)
                else:
                    return float(default)
            # 如果是字典或其他类型
            value = data.get(key, default)
            if value is None:
                return float(default)
            if hasattr(value, 'iloc'):
                # pandas Series
                if len(value) > 0:
                    val = value.iloc[-1]
                    if pd.isna(val) or val is None:
                        return float(default)
                    return float(val)
                else:
                    return float(default)
            # 标量值
            if pd.isna(value) if hasattr(pd, 'isna') else (value is None):
                return float(default)
            return float(value)
        except Exception as e:
            logger.warning(f"获取标量值失败 key={key}, error={e}")
            return float(default)
    
    def extract_all_features(self, df: pd.DataFrame, moneyflow_data: pd.DataFrame) -> Dict[str, Any]:
        """提取所有资金流特征"""
        try:
            features = {}
            
            # 基础资金流特征
            features.update(self.extract_basic_moneyflow_features(moneyflow_data))
            
            # 主力资金特征
            features.update(self.extract_main_force_features(moneyflow_data))
            
            # 散户资金特征
            features.update(self.extract_retail_features(moneyflow_data))
            
            # 资金结构特征
            features.update(self.extract_fund_structure_features(moneyflow_data))
            
            # 资金流向趋势特征
            features.update(self.extract_moneyflow_trend_features(moneyflow_data))
            
            # 资金流向异常特征
            features.update(self.extract_moneyflow_anomaly_features(moneyflow_data))
            
            logger.info(f"提取资金流特征成功: {len(features)}个特征")
            return features
            
        except Exception as e:
            logger.error(f"提取资金流特征失败: {e}")
            return {}
    
    def extract_basic_moneyflow_features(self, moneyflow_data: pd.DataFrame) -> Dict[str, Any]:
        """提取基础资金流特征"""
        features = {}
        
        try:
            if moneyflow_data.empty:
                return {}
            
            # 净流入金额
            features['net_inflow_amount'] = self._get_scalar_value(moneyflow_data, 'net_mf_amount', 0)
            
            # 净流入量
            features['net_inflow_volume'] = self._get_scalar_value(moneyflow_data, 'net_mf_vol', 0)
            
            # 净流入比例（相对于总成交额）
            total_amount = self._calculate_total_amount(moneyflow_data)
            if total_amount > 0:
                features['net_inflow_ratio'] = features['net_inflow_amount'] / total_amount
            else:
                features['net_inflow_ratio'] = 0
            
            # 流入强度
            avg_amount = self._calculate_average_amount(moneyflow_data)
            if avg_amount > 0:
                features['inflow_strength'] = abs(features['net_inflow_amount']) / avg_amount
            else:
                features['inflow_strength'] = 0
            
            # 资金流向方向
            features['fund_flow_direction'] = 1 if features['net_inflow_amount'] > 0 else -1 if features['net_inflow_amount'] < 0 else 0
            
            # 资金流向强度
            features['fund_flow_intensity'] = abs(features['net_inflow_ratio'])
            
            return features
            
        except Exception as e:
            logger.error(f"提取基础资金流特征失败: {e}")
            return {}
    
    def extract_main_force_features(self, moneyflow_data: pd.DataFrame) -> Dict[str, Any]:
        """提取主力资金特征"""
        features = {}
        
        try:
            if moneyflow_data.empty:
                return {}
            
            # 计算主力资金数据（大单 + 特大单）
            main_force_buy_amount = self._get_scalar_value(moneyflow_data, 'buy_lg_amount', 0) + self._get_scalar_value(moneyflow_data, 'buy_elg_amount', 0)
            main_force_sell_amount = self._get_scalar_value(moneyflow_data, 'sell_lg_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_elg_amount', 0)
            main_force_buy_vol = self._get_scalar_value(moneyflow_data, 'buy_lg_vol', 0) + self._get_scalar_value(moneyflow_data, 'buy_elg_vol', 0)
            main_force_sell_vol = self._get_scalar_value(moneyflow_data, 'sell_lg_vol', 0) + self._get_scalar_value(moneyflow_data, 'sell_elg_vol', 0)
            
            # 主力资金总成交额
            main_force_total_amount = main_force_buy_amount + main_force_sell_amount
            total_amount = self._calculate_total_amount(moneyflow_data)
            
            # 主力资金比例
            if total_amount > 0:
                features['main_force_ratio'] = main_force_total_amount / total_amount
            else:
                features['main_force_ratio'] = 0
            
            # 主力买入比例
            if main_force_total_amount > 0:
                features['main_force_buy_ratio'] = main_force_buy_amount / main_force_total_amount
            else:
                features['main_force_buy_ratio'] = 0
            
            # 主力卖出比例
            if main_force_total_amount > 0:
                features['main_force_sell_ratio'] = main_force_sell_amount / main_force_total_amount
            else:
                features['main_force_sell_ratio'] = 0
            
            # 主力净流入
            main_force_net_amount = main_force_buy_amount - main_force_sell_amount
            features['main_force_net_amount'] = main_force_net_amount
            
            # 主力净流入比例
            if main_force_total_amount > 0:
                features['main_force_net_ratio'] = main_force_net_amount / main_force_total_amount
            else:
                features['main_force_net_ratio'] = 0
            
            # 主力资金强度
            features['main_force_strength'] = abs(features['main_force_net_ratio'])
            
            # 主力资金方向
            features['main_force_direction'] = 1 if main_force_net_amount > 0 else -1 if main_force_net_amount < 0 else 0
            
            return features
            
        except Exception as e:
            logger.error(f"提取主力资金特征失败: {e}")
            return {}
    
    def extract_retail_features(self, moneyflow_data: pd.DataFrame) -> Dict[str, Any]:
        """提取散户资金特征"""
        features = {}
        
        try:
            if moneyflow_data.empty:
                return {}
            
            # 计算散户资金数据（小单）
            retail_buy_amount = self._get_scalar_value(moneyflow_data, 'buy_sm_amount', 0)
            retail_sell_amount = self._get_scalar_value(moneyflow_data, 'sell_sm_amount', 0)
            retail_buy_vol = self._get_scalar_value(moneyflow_data, 'buy_sm_vol', 0)
            retail_sell_vol = self._get_scalar_value(moneyflow_data, 'sell_sm_vol', 0)
            
            # 散户资金总成交额
            retail_total_amount = retail_buy_amount + retail_sell_amount
            total_amount = self._calculate_total_amount(moneyflow_data)
            
            # 散户资金比例
            if total_amount > 0:
                features['retail_ratio'] = retail_total_amount / total_amount
            else:
                features['retail_ratio'] = 0
            
            # 散户买入比例
            if retail_total_amount > 0:
                features['retail_buy_ratio'] = retail_buy_amount / retail_total_amount
            else:
                features['retail_buy_ratio'] = 0
            
            # 散户卖出比例
            if retail_total_amount > 0:
                features['retail_sell_ratio'] = retail_sell_amount / retail_total_amount
            else:
                features['retail_sell_ratio'] = 0
            
            # 散户净流入
            retail_net_amount = retail_buy_amount - retail_sell_amount
            features['retail_net_amount'] = retail_net_amount
            
            # 散户净流入比例
            if retail_total_amount > 0:
                features['retail_net_ratio'] = retail_net_amount / retail_total_amount
            else:
                features['retail_net_ratio'] = 0
            
            # 散户资金强度
            features['retail_strength'] = abs(features['retail_net_ratio'])
            
            # 散户资金方向
            features['retail_direction'] = 1 if retail_net_amount > 0 else -1 if retail_net_amount < 0 else 0
            
            return features
            
        except Exception as e:
            logger.error(f"提取散户资金特征失败: {e}")
            return {}
    
    def extract_fund_structure_features(self, moneyflow_data: pd.DataFrame) -> Dict[str, Any]:
        """提取资金结构特征"""
        features = {}
        
        try:
            if moneyflow_data.empty:
                return {}
            
            # 计算各类资金比例
            total_amount = self._calculate_total_amount(moneyflow_data)
            
            if total_amount > 0:
                # 小单比例
                small_amount = self._get_scalar_value(moneyflow_data, 'buy_sm_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_sm_amount', 0)
                small_ratio = small_amount / total_amount
                
                # 中单比例
                medium_amount = self._get_scalar_value(moneyflow_data, 'buy_md_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_md_amount', 0)
                medium_ratio = medium_amount / total_amount
                
                # 大单比例
                large_amount = self._get_scalar_value(moneyflow_data, 'buy_lg_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_lg_amount', 0)
                large_ratio = large_amount / total_amount
                
                # 特大单比例
                extra_large_amount = self._get_scalar_value(moneyflow_data, 'buy_elg_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_elg_amount', 0)
                extra_large_ratio = extra_large_amount / total_amount
                
                # 主力资金比例（大单 + 特大单）
                main_force_ratio = large_ratio + extra_large_ratio
                
                # 散户资金比例（小单）
                retail_ratio = small_ratio
                
                # 资金结构平衡度
                features['fund_structure_balance'] = main_force_ratio - retail_ratio
                
                # 资金结构集中度
                features['fund_concentration'] = max(small_ratio, medium_ratio, large_ratio, extra_large_ratio)
                
                # 资金结构分散度
                ratios = [small_ratio, medium_ratio, large_ratio, extra_large_ratio]
                features['fund_dispersion'] = 1 - max(ratios)
                
                # 主力资金主导度
                features['main_force_dominance'] = main_force_ratio / (main_force_ratio + retail_ratio + 1e-8)
                
            else:
                features['fund_structure_balance'] = 0
                features['fund_concentration'] = 0
                features['fund_dispersion'] = 1
                features['main_force_dominance'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"提取资金结构特征失败: {e}")
            return {}
    
    def extract_moneyflow_trend_features(self, moneyflow_data: pd.DataFrame) -> Dict[str, Any]:
        """提取资金流向趋势特征"""
        features = {}
        
        try:
            if moneyflow_data.empty:
                return {}
            
            # 净流入趋势
            net_inflow = self._get_scalar_value(moneyflow_data, 'net_mf_amount', 0)
            features['net_inflow_trend'] = 1 if net_inflow > 0 else -1 if net_inflow < 0 else 0
            
            # 主力资金趋势
            main_force_net = self._get_scalar_value(moneyflow_data, 'buy_lg_amount', 0) + self._get_scalar_value(moneyflow_data, 'buy_elg_amount', 0) - \
                           self._get_scalar_value(moneyflow_data, 'sell_lg_amount', 0) - self._get_scalar_value(moneyflow_data, 'sell_elg_amount', 0)
            features['main_force_trend'] = 1 if main_force_net > 0 else -1 if main_force_net < 0 else 0
            
            # 散户资金趋势
            retail_net = self._get_scalar_value(moneyflow_data, 'buy_sm_amount', 0) - self._get_scalar_value(moneyflow_data, 'sell_sm_amount', 0)
            features['retail_trend'] = 1 if retail_net > 0 else -1 if retail_net < 0 else 0
            
            # 资金流向一致性
            if features['net_inflow_trend'] == features['main_force_trend']:
                features['fund_flow_consistency'] = 1
            else:
                features['fund_flow_consistency'] = 0
            
            # 主力散户博弈
            if features['main_force_trend'] != features['retail_trend']:
                features['main_retail_game'] = 1
            else:
                features['main_retail_game'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"提取资金流向趋势特征失败: {e}")
            return {}
    
    def extract_moneyflow_anomaly_features(self, moneyflow_data: pd.DataFrame) -> Dict[str, Any]:
        """提取资金流向异常特征"""
        features = {}
        
        try:
            if moneyflow_data.empty:
                return {}
            
            # 计算各类资金数据
            total_amount = self._calculate_total_amount(moneyflow_data)
            net_inflow = self._get_scalar_value(moneyflow_data, 'net_mf_amount', 0)
            
            # 异常净流入
            if total_amount > 0:
                net_inflow_ratio = abs(net_inflow) / total_amount
                features['abnormal_net_inflow'] = 1 if net_inflow_ratio > 0.1 else 0
            else:
                features['abnormal_net_inflow'] = 0
            
            # 主力资金异常
            main_force_ratio = self._calculate_main_force_ratio(moneyflow_data)
            features['abnormal_main_force'] = 1 if main_force_ratio > 0.5 else 0
            
            # 散户资金异常
            retail_ratio = self._calculate_retail_ratio(moneyflow_data)
            features['abnormal_retail'] = 1 if retail_ratio > 0.5 else 0
            
            # 资金流向异常
            if abs(net_inflow) > total_amount * 0.2:
                features['abnormal_fund_flow'] = 1
            else:
                features['abnormal_fund_flow'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"提取资金流向异常特征失败: {e}")
            return {}
    
    def _calculate_total_amount(self, moneyflow_data: pd.DataFrame) -> float:
        """计算总成交额"""
        try:
            total = 0
            for col in ['buy_sm_amount', 'sell_sm_amount', 'buy_md_amount', 'sell_md_amount', 
                       'buy_lg_amount', 'sell_lg_amount', 'buy_elg_amount', 'sell_elg_amount']:
                value = self._get_scalar_value(moneyflow_data, col, 0)
                total += value
            return total
        except:
            return 0
    
    def _calculate_average_amount(self, moneyflow_data: pd.DataFrame) -> float:
        """计算平均成交额（简化计算）"""
        try:
            total = self._calculate_total_amount(moneyflow_data)
            return total / 8  # 8个资金类别
        except:
            return 0
    
    def _calculate_main_force_ratio(self, moneyflow_data: pd.DataFrame) -> float:
        """计算主力资金比例"""
        try:
            main_force_amount = self._get_scalar_value(moneyflow_data, 'buy_lg_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_lg_amount', 0) + \
                              self._get_scalar_value(moneyflow_data, 'buy_elg_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_elg_amount', 0)
            total_amount = self._calculate_total_amount(moneyflow_data)
            return main_force_amount / (total_amount + 1e-8)
        except:
            return 0
    
    def _calculate_retail_ratio(self, moneyflow_data: pd.DataFrame) -> float:
        """计算散户资金比例"""
        try:
            retail_amount = self._get_scalar_value(moneyflow_data, 'buy_sm_amount', 0) + self._get_scalar_value(moneyflow_data, 'sell_sm_amount', 0)
            total_amount = self._calculate_total_amount(moneyflow_data)
            return retail_amount / (total_amount + 1e-8)
        except:
            return 0
    
    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        feature_names = []
        
        # 基础资金流特征
        feature_names.extend([
            'net_inflow_amount', 'net_inflow_volume', 'net_inflow_ratio',
            'inflow_strength', 'fund_flow_direction', 'fund_flow_intensity'
        ])
        
        # 主力资金特征
        feature_names.extend([
            'main_force_ratio', 'main_force_buy_ratio', 'main_force_sell_ratio',
            'main_force_net_amount', 'main_force_net_ratio', 'main_force_strength',
            'main_force_direction'
        ])
        
        # 散户资金特征
        feature_names.extend([
            'retail_ratio', 'retail_buy_ratio', 'retail_sell_ratio',
            'retail_net_amount', 'retail_net_ratio', 'retail_strength',
            'retail_direction'
        ])
        
        # 资金结构特征
        feature_names.extend([
            'fund_structure_balance', 'fund_concentration', 'fund_dispersion',
            'main_force_dominance'
        ])
        
        # 资金流向趋势特征
        feature_names.extend([
            'net_inflow_trend', 'main_force_trend', 'retail_trend',
            'fund_flow_consistency', 'main_retail_game'
        ])
        
        # 资金流向异常特征
        feature_names.extend([
            'abnormal_net_inflow', 'abnormal_main_force', 'abnormal_retail',
            'abnormal_fund_flow'
        ])
        
        return feature_names
