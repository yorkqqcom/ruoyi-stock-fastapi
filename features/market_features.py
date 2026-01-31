#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场特征提取器
基于PriceActions理论的市场环境和情绪特征
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from utils.logger import setup_logger

logger = setup_logger()

class MarketFeatureExtractor:
    """市场特征提取器"""
    
    def __init__(self):
        self.market_phases = ['trending', 'ranging', 'breaking']
        self.volatility_regimes = ['low', 'medium', 'high']
    
    def extract_all_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取所有市场特征"""
        try:
            features = {}
            
            # 市场阶段特征
            features.update(self.extract_market_phase_features(df))
            
            # 波动率特征
            features.update(self.extract_volatility_features(df))
            
            # 成交量特征
            features.update(self.extract_volume_features(df))
            
            # 市场情绪特征
            features.update(self.extract_sentiment_features(df))
            
            # 流动性特征
            features.update(self.extract_liquidity_features(df))
            
            logger.info(f"提取市场特征成功: {len(features)}个特征")
            return features
            
        except Exception as e:
            logger.error(f"提取市场特征失败: {e}")
            return {}
    
    def extract_market_phase_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取市场阶段特征"""
        features = {}
        
        try:
            # 市场阶段识别
            features.update(self.identify_market_phase(df))
            
            # 趋势强度
            features.update(self.calculate_trend_strength(df))
            
            # 市场稳定性
            features.update(self.calculate_market_stability(df))
            
            return features
            
        except Exception as e:
            logger.error(f"提取市场阶段特征失败: {e}")
            return {}
    
    def identify_market_phase(self, df: pd.DataFrame) -> Dict[str, Any]:
        """识别市场阶段"""
        features = {}
        
        try:
            # 计算趋势强度
            short_ma = df['close'].rolling(20).mean()
            long_ma = df['close'].rolling(50).mean()
            trend_strength = np.abs(short_ma - long_ma) / (long_ma + 1e-8)
            
            # 计算波动率
            returns = df['close'].pct_change()
            volatility = returns.rolling(20).std()
            
            # 市场阶段判断
            features['market_phase_trending'] = np.where(trend_strength > 0.02, 1, 0)
            features['market_phase_ranging'] = np.where(
                (trend_strength <= 0.02) & (volatility > 0.03), 1, 0
            )
            features['market_phase_breaking'] = np.where(
                (trend_strength <= 0.02) & (volatility <= 0.03), 1, 0
            )
            
            # 阶段强度
            features['phase_strength'] = trend_strength
            
            return features
            
        except Exception as e:
            logger.error(f"识别市场阶段失败: {e}")
            return {'market_phase_trending': 0, 'market_phase_ranging': 0, 
                   'market_phase_breaking': 0, 'phase_strength': 0}
    
    def calculate_trend_strength(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算趋势强度"""
        features = {}
        
        try:
            # 多时间框架趋势强度
            for period in [5, 10, 20, 50]:
                ma = df['close'].rolling(period).mean()
                trend_strength = np.abs(ma - ma.shift(1)) / (ma.shift(1) + 1e-8)
                features[f'trend_strength_{period}'] = trend_strength
            
            # 趋势一致性
            for period in [5, 10, 20, 50]:
                ma = df['close'].rolling(period).mean()
                trend_direction = np.where(ma > ma.shift(1), 1, -1)
                # 确保trend_direction是pandas Series
                if isinstance(trend_direction, np.ndarray):
                    trend_direction = pd.Series(trend_direction, index=df.index)
                features[f'trend_consistency_{period}'] = trend_direction.rolling(period).mean()
            
            # 趋势持续性
            for period in [5, 10, 20, 50]:
                ma = df['close'].rolling(period).mean()
                trend_persistence = (ma > ma.shift(1)).astype(int).rolling(period).sum() / period
                features[f'trend_persistence_{period}'] = trend_persistence
            
            return features
            
        except Exception as e:
            logger.error(f"计算趋势强度失败: {e}")
            return {}
    
    def calculate_market_stability(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算市场稳定性"""
        features = {}
        
        try:
            # 价格稳定性
            price_std = df['close'].rolling(20).std()
            price_mean = df['close'].rolling(20).mean()
            features['price_stability'] = 1 / (price_std / (price_mean + 1e-8) + 1e-8)
            
            # 成交量稳定性
            if 'volume' in df.columns:
                volume_std = df['volume'].rolling(20).std()
                volume_mean = df['volume'].rolling(20).mean()
                features['volume_stability'] = 1 / (volume_std / (volume_mean + 1e-8) + 1e-8)
            else:
                features['volume_stability'] = 0
            
            # 波动率稳定性
            returns = df['close'].pct_change()
            vol_std = returns.rolling(20).std()
            vol_mean = returns.rolling(20).std().rolling(20).mean()
            features['volatility_stability'] = 1 / (vol_std / (vol_mean + 1e-8) + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"计算市场稳定性失败: {e}")
            return {}
    
    def extract_volatility_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取波动率特征"""
        features = {}
        
        try:
            # 历史波动率
            returns = df['close'].pct_change()
            for period in [5, 10, 20, 50]:
                vol = returns.rolling(period).std()
                features[f'volatility_{period}'] = vol
                features[f'volatility_ratio_{period}'] = vol / (vol.rolling(period).mean() + 1e-8)
            
            # 波动率制度
            vol_20 = returns.rolling(20).std()
            vol_50 = returns.rolling(50).std()
            vol_regime = np.where(vol_20 < vol_50 * 0.8, 0,  # 低波动
                                 np.where(vol_20 > vol_50 * 1.2, 2, 1))  # 高波动, 中等波动
            
            features['volatility_regime_low'] = (vol_regime == 0).astype(int)
            features['volatility_regime_medium'] = (vol_regime == 1).astype(int)
            features['volatility_regime_high'] = (vol_regime == 2).astype(int)
            
            # 波动率趋势
            features['volatility_trend'] = vol_20 - vol_50
            features['volatility_acceleration'] = vol_20.diff()
            
            return features
            
        except Exception as e:
            logger.error(f"提取波动率特征失败: {e}")
            return {}
    
    def extract_volume_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取成交量特征"""
        features = {}
        
        try:
            # 检查是否有volume列
            if 'volume' not in df.columns:
                logger.warning("数据中缺少volume列，跳过成交量特征提取")
                return {}
            
            # 成交量趋势
            for period in [5, 10, 20, 50]:
                vol_ma = df['volume'].rolling(period).mean()
                features[f'volume_trend_{period}'] = df['volume'] / (vol_ma + 1e-8)
                features[f'volume_ma_{period}'] = vol_ma
            
            # 成交量异常
            vol_mean = df['volume'].rolling(20).mean()
            vol_std = df['volume'].rolling(20).std()
            features['volume_spike'] = np.where(
                df['volume'] > vol_mean + 2 * vol_std, 1, 0
            )
            features['volume_drop'] = np.where(
                df['volume'] < vol_mean - 2 * vol_std, 1, 0
            )
            
            # 成交量分布
            features['volume_distribution'] = vol_std / (vol_mean + 1e-8)
            
            # 成交量价格关系
            close = df['close'].astype(float)
            volume = df['volume'].astype(float)
            features['volume_price_correlation'] = volume.rolling(20).corr(close)
            features['volume_price_ratio'] = volume / (close + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"提取成交量特征失败: {e}")
            return {}
    
    def extract_sentiment_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取市场情绪特征"""
        features = {}
        
        try:
            # 价格情绪
            features.update(self.calculate_price_sentiment(df))
            
            # 成交量情绪
            features.update(self.calculate_volume_sentiment(df))
            
            # 波动率情绪
            features.update(self.calculate_volatility_sentiment(df))
            
            return features
            
        except Exception as e:
            logger.error(f"提取市场情绪特征失败: {e}")
            return {}
    
    def calculate_price_sentiment(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算价格情绪"""
        features = {}
        
        try:
            # 价格动量
            close = df['close'].astype(float)
            for period in [1, 3, 5, 10]:
                momentum = close / close.shift(period) - 1
                features[f'price_momentum_{period}'] = momentum
            
            # 价格情绪指标
            price_change = df['close'].pct_change()
            features['positive_sentiment'] = (price_change > 0).astype(int).rolling(20).mean()
            features['negative_sentiment'] = (price_change < 0).astype(int).rolling(20).mean()
            
            # 情绪强度
            features['sentiment_strength'] = np.abs(price_change).rolling(20).mean()
            
            return features
            
        except Exception as e:
            logger.error(f"计算价格情绪失败: {e}")
            return {}
    
    def calculate_volume_sentiment(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算成交量情绪"""
        features = {}
        
        try:
            # 检查是否有volume列
            if 'volume' not in df.columns:
                logger.warning("数据中缺少volume列，跳过成交量情绪计算")
                return {}
            
            # 成交量情绪
            vol_change = df['volume'].pct_change()
            features['volume_sentiment_positive'] = (vol_change > 0).astype(int).rolling(20).mean()
            features['volume_sentiment_negative'] = (vol_change < 0).astype(int).rolling(20).mean()
            
            # 成交量情绪强度
            features['volume_sentiment_strength'] = np.abs(vol_change).rolling(20).mean()
            
            return features
            
        except Exception as e:
            logger.error(f"计算成交量情绪失败: {e}")
            return {}
    
    def calculate_volatility_sentiment(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算波动率情绪"""
        features = {}
        
        try:
            # 波动率情绪
            returns = df['close'].pct_change()
            vol = returns.rolling(20).std()
            vol_change = vol.pct_change()
            
            features['volatility_sentiment_positive'] = (vol_change > 0).astype(int).rolling(20).mean()
            features['volatility_sentiment_negative'] = (vol_change < 0).astype(int).rolling(20).mean()
            
            # 波动率情绪强度
            features['volatility_sentiment_strength'] = np.abs(vol_change).rolling(20).mean()
            
            return features
            
        except Exception as e:
            logger.error(f"计算波动率情绪失败: {e}")
            return {}
    
    def extract_liquidity_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取流动性特征"""
        features = {}
        
        try:
            # 检查是否有volume列
            if 'volume' not in df.columns:
                logger.warning("数据中缺少volume列，跳过流动性特征提取")
                return {}
            
            # 流动性指标
            close = df['close'].astype(float)
            volume = df['volume'].astype(float)
            features['liquidity_ratio'] = volume / (close + 1e-8)
            features['liquidity_trend'] = features['liquidity_ratio'].rolling(20).mean()
            
            # 流动性稳定性
            liquidity_std = features['liquidity_ratio'].rolling(20).std()
            liquidity_mean = features['liquidity_ratio'].rolling(20).mean()
            features['liquidity_stability'] = 1 / (liquidity_std / (liquidity_mean + 1e-8) + 1e-8)
            
            # 流动性风险
            features['liquidity_risk'] = 1 / (features['liquidity_ratio'] + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"提取流动性特征失败: {e}")
            return {}
    
    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        feature_names = []
        
        # 市场阶段特征
        feature_names.extend([
            'market_phase_trending', 'market_phase_ranging', 'market_phase_breaking', 'phase_strength'
        ])
        
        # 趋势强度特征
        for period in [5, 10, 20, 50]:
            feature_names.extend([
                f'trend_strength_{period}', f'trend_consistency_{period}', f'trend_persistence_{period}'
            ])
        
        # 市场稳定性特征
        feature_names.extend([
            'price_stability', 'volume_stability', 'volatility_stability'
        ])
        
        # 波动率特征
        for period in [5, 10, 20, 50]:
            feature_names.extend([
                f'volatility_{period}', f'volatility_ratio_{period}'
            ])
        
        feature_names.extend([
            'volatility_regime_low', 'volatility_regime_medium', 'volatility_regime_high',
            'volatility_trend', 'volatility_acceleration'
        ])
        
        # 成交量特征
        for period in [5, 10, 20, 50]:
            feature_names.extend([
                f'volume_trend_{period}', f'volume_ma_{period}'
            ])
        
        feature_names.extend([
            'volume_spike', 'volume_drop', 'volume_distribution',
            'volume_price_correlation', 'volume_price_ratio'
        ])
        
        # 市场情绪特征
        for period in [1, 3, 5, 10]:
            feature_names.append(f'price_momentum_{period}')
        
        feature_names.extend([
            'positive_sentiment', 'negative_sentiment', 'sentiment_strength',
            'volume_sentiment_positive', 'volume_sentiment_negative', 'volume_sentiment_strength',
            'volatility_sentiment_positive', 'volatility_sentiment_negative', 'volatility_sentiment_strength'
        ])
        
        # 流动性特征
        feature_names.extend([
            'liquidity_ratio', 'liquidity_trend', 'liquidity_stability', 'liquidity_risk'
        ])
        
        # 活跃特征
        feature_names.extend([
            'active_feature_1',  # 当日涨幅排名前10%（按主板、创业板、科创板区分）
            'active_feature_2'   # 当日涨幅超过3%
        ])
        
        return feature_names
