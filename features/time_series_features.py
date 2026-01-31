#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间序列特征提取器
专门用于提取时间序列相关的特征，包括滞后特征、滑动窗口特征等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from utils.logger import setup_logger

logger = setup_logger()

class TimeSeriesFeatureExtractor:
    """时间序列特征提取器"""
    
    def __init__(self):
        self.lag_periods = [1, 2, 3, 5, 10, 20]  # 滞后特征周期
        self.window_sizes = [5, 10, 20, 50]  # 滑动窗口大小
        self.momentum_periods = [1, 3, 5, 10, 20]  # 动量特征周期
    
    def extract_all_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取所有时间序列特征"""
        try:
            features = {}
            
            # 滞后特征
            features.update(self.extract_lag_features(df))
            
            # 滑动窗口特征
            features.update(self.extract_window_features(df))
            
            # 动量特征
            features.update(self.extract_momentum_features(df))
            
            # 自相关特征
            features.update(self.extract_autocorrelation_features(df))
            
            # 季节性特征
            features.update(self.extract_seasonality_features(df))
            
            # 趋势分解特征
            features.update(self.extract_trend_decomposition_features(df))
            
            logger.info(f"提取时间序列特征成功: {len(features)}个特征")
            return features
            
        except Exception as e:
            logger.error(f"提取时间序列特征失败: {e}")
            return {}
    
    def extract_lag_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取滞后特征"""
        features = {}
        
        try:
            # 价格滞后特征
            for lag in self.lag_periods:
                features[f'close_lag_{lag}'] = df['close'].shift(lag)
                features[f'high_lag_{lag}'] = df['high'].shift(lag)
                features[f'low_lag_{lag}'] = df['low'].shift(lag)
                features[f'open_lag_{lag}'] = df['open'].shift(lag)
                
                # 价格变化率滞后
                features[f'close_change_lag_{lag}'] = df['close'].pct_change().shift(lag)
                features[f'high_change_lag_{lag}'] = df['high'].pct_change().shift(lag)
                features[f'low_change_lag_{lag}'] = df['low'].pct_change().shift(lag)
            
            # 成交量滞后特征
            if 'volume' in df.columns:
                for lag in self.lag_periods:
                    features[f'volume_lag_{lag}'] = df['volume'].shift(lag)
                    features[f'volume_change_lag_{lag}'] = df['volume'].pct_change().shift(lag)
            
            # 滞后特征比率
            for lag in self.lag_periods:
                features[f'close_ratio_lag_{lag}'] = df['close'] / (df['close'].shift(lag) + 1e-8)
                features[f'volume_ratio_lag_{lag}'] = df['volume'] / (df['volume'].shift(lag) + 1e-8) if 'volume' in df.columns else 0
            
            return features
            
        except Exception as e:
            logger.error(f"提取滞后特征失败: {e}")
            return {}
    
    def extract_window_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取滑动窗口特征"""
        features = {}
        
        try:
            for window in self.window_sizes:
                # 价格窗口特征
                features[f'close_mean_{window}'] = df['close'].rolling(window).mean()
                features[f'close_std_{window}'] = df['close'].rolling(window).std()
                features[f'close_min_{window}'] = df['close'].rolling(window).min()
                features[f'close_max_{window}'] = df['close'].rolling(window).max()
                features[f'close_median_{window}'] = df['close'].rolling(window).median()
                
                # 价格分位数特征
                features[f'close_q25_{window}'] = df['close'].rolling(window).quantile(0.25)
                features[f'close_q75_{window}'] = df['close'].rolling(window).quantile(0.75)
                features[f'close_iqr_{window}'] = features[f'close_q75_{window}'] - features[f'close_q25_{window}']
                
                # 价格位置特征
                features[f'close_position_{window}'] = (df['close'] - features[f'close_min_{window}']) / (features[f'close_max_{window}'] - features[f'close_min_{window}'] + 1e-8)
                
                # 波动率特征
                returns = df['close'].pct_change()
                features[f'volatility_{window}'] = returns.rolling(window).std()
                features[f'volatility_mean_{window}'] = features[f'volatility_{window}'].rolling(window).mean()
                
                # 偏度和峰度
                features[f'skewness_{window}'] = returns.rolling(window).skew()
                features[f'kurtosis_{window}'] = returns.rolling(window).kurt()
                
                # 成交量窗口特征
                if 'volume' in df.columns:
                    features[f'volume_mean_{window}'] = df['volume'].rolling(window).mean()
                    features[f'volume_std_{window}'] = df['volume'].rolling(window).std()
                    features[f'volume_max_{window}'] = df['volume'].rolling(window).max()
                    features[f'volume_min_{window}'] = df['volume'].rolling(window).min()
                    
                    # 成交量比率
                    features[f'volume_ratio_{window}'] = df['volume'] / (features[f'volume_mean_{window}'] + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"提取滑动窗口特征失败: {e}")
            return {}
    
    def extract_momentum_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取动量特征"""
        features = {}
        
        try:
            # 先计算所有价格动量特征
            momentum_features = {}
            for period in self.momentum_periods:
                # 价格动量
                momentum_features[f'price_momentum_{period}'] = df['close'] / (df['close'].shift(period) + 1e-8) - 1
                features[f'price_momentum_{period}'] = momentum_features[f'price_momentum_{period}']
                features[f'price_momentum_abs_{period}'] = np.abs(momentum_features[f'price_momentum_{period}'])
                
                # 成交量动量
                if 'volume' in df.columns:
                    features[f'volume_momentum_{period}'] = df['volume'] / (df['volume'].shift(period) + 1e-8) - 1
                    features[f'volume_momentum_abs_{period}'] = np.abs(features[f'volume_momentum_{period}'])
                
                # 价格变化的一致性
                price_changes = df['close'].pct_change()
                features[f'price_consistency_{period}'] = (price_changes > 0).rolling(period).sum() / period
                
                # 价格变化的连续性
                features[f'price_continuity_{period}'] = self._calculate_continuity(df['close'], period)
            
            # 计算价格加速度特征（动量的变化率）
            acceleration_periods = [3, 5, 10, 20]  # 根据报告中的缺失特征
            for period in acceleration_periods:
                if period in self.momentum_periods:
                    # 计算当前周期的动量
                    current_momentum = momentum_features[f'price_momentum_{period}']
                    # 计算前一个周期的动量（如果存在）
                    prev_period = period - 1
                    if prev_period in self.momentum_periods and f'price_momentum_{prev_period}' in momentum_features:
                        prev_momentum = momentum_features[f'price_momentum_{prev_period}']
                        features[f'price_acceleration_{period}'] = current_momentum - prev_momentum
                    else:
                        # 如果没有前一个周期，使用动量的变化率
                        features[f'price_acceleration_{period}'] = current_momentum.diff()
                else:
                    # 如果周期不在动量周期列表中，直接计算加速度
                    momentum = df['close'] / (df['close'].shift(period) + 1e-8) - 1
                    features[f'price_acceleration_{period}'] = momentum.diff()
            
            return features
            
        except Exception as e:
            logger.error(f"提取动量特征失败: {e}")
            return {}
    
    def extract_autocorrelation_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取自相关特征"""
        features = {}
        
        try:
            # 价格自相关
            returns = df['close'].pct_change().dropna()
            
            for lag in [1, 2, 3, 5, 10, 20]:
                if len(returns) > lag:
                    autocorr = returns.autocorr(lag=lag)
                    features[f'price_autocorr_{lag}'] = autocorr if not np.isnan(autocorr) else 0
                else:
                    features[f'price_autocorr_{lag}'] = 0
            
            # 成交量自相关
            if 'volume' in df.columns:
                volume_changes = df['volume'].pct_change().dropna()
                for lag in [1, 2, 3, 5, 10]:
                    if len(volume_changes) > lag:
                        autocorr = volume_changes.autocorr(lag=lag)
                        features[f'volume_autocorr_{lag}'] = autocorr if not np.isnan(autocorr) else 0
                    else:
                        features[f'volume_autocorr_{lag}'] = 0
            
            return features
            
        except Exception as e:
            logger.error(f"提取自相关特征失败: {e}")
            return {}
    
    def extract_seasonality_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取季节性特征"""
        features = {}
        
        try:
            # 基于日期的季节性特征
            if 'trade_date' in df.columns:
                df['day_of_week'] = pd.to_datetime(df['trade_date']).dt.dayofweek
                df['day_of_month'] = pd.to_datetime(df['trade_date']).dt.day
                df['month'] = pd.to_datetime(df['trade_date']).dt.month
                df['quarter'] = pd.to_datetime(df['trade_date']).dt.quarter
                # 获取一年中的第几周（ISO周数，范围1-53）
                df['week'] = pd.to_datetime(df['trade_date']).dt.isocalendar().week
                
                # 周期性特征
                features['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
                features['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
                features['day_of_month_sin'] = np.sin(2 * np.pi * df['day_of_month'] / 31)
                features['day_of_month_cos'] = np.cos(2 * np.pi * df['day_of_month'] / 31)
                features['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
                features['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
                features['quarter_sin'] = np.sin(2 * np.pi * df['quarter'] / 4)
                features['quarter_cos'] = np.cos(2 * np.pi * df['quarter'] / 4)
                # 周数周期性特征（一年约52-53周，使用52作为周期）
                features['week_sin'] = np.sin(2 * np.pi * df['week'] / 52)
                features['week_cos'] = np.cos(2 * np.pi * df['week'] / 52)
            
            # 价格周期性特征
            returns = df['close'].pct_change().dropna()
            if len(returns) > 20:
                # 使用FFT检测周期性
                fft = np.fft.fft(returns.values)
                freqs = np.fft.fftfreq(len(returns))
                
                # 主要频率成分
                dominant_freq_idx = np.argmax(np.abs(fft[1:len(fft)//2])) + 1
                features['dominant_frequency'] = freqs[dominant_freq_idx]
                features['dominant_amplitude'] = np.abs(fft[dominant_freq_idx])
            
            return features
            
        except Exception as e:
            logger.error(f"提取季节性特征失败: {e}")
            return {}
    
    def extract_trend_decomposition_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取趋势分解特征"""
        features = {}
        
        try:
            # 简单的趋势分解
            close = df['close'].dropna()
            if len(close) < 20:
                return features
            
            # 移动平均趋势
            ma_short = close.rolling(5).mean()
            ma_long = close.rolling(20).mean()
            
            features['trend_direction'] = np.where(ma_short > ma_long, 1, -1)
            features['trend_strength'] = np.abs(ma_short - ma_long) / (ma_long + 1e-8)
            
            # 趋势变化点检测
            trend_direction_series = pd.Series(features['trend_direction'], index=close.index)
            trend_changes = (trend_direction_series != trend_direction_series.shift(1)).astype(int)
            features['trend_change_frequency'] = trend_changes.rolling(20).sum()
            
            # 价格偏离趋势的程度
            features['price_deviation_from_trend'] = (close - ma_long) / (ma_long + 1e-8)
            
            # 趋势的稳定性
            features['trend_stability'] = 1 - features['trend_change_frequency'] / 20
            
            return features
            
        except Exception as e:
            logger.error(f"提取趋势分解特征失败: {e}")
            return {}
    
    def _calculate_continuity(self, series: pd.Series, period: int) -> pd.Series:
        """计算序列的连续性"""
        try:
            # 计算连续上涨或下跌的天数
            changes = series.pct_change()
            up_days = (changes > 0).astype(int)
            down_days = (changes < 0).astype(int)
            
            # 连续上涨天数
            up_continuity = up_days.groupby((up_days != up_days.shift()).cumsum()).cumsum()
            # 连续下跌天数
            down_continuity = down_days.groupby((down_days != down_days.shift()).cumsum()).cumsum()
            
            # 连续性指标（正值表示上涨连续性，负值表示下跌连续性）
            continuity = up_continuity - down_continuity
            
            return continuity.rolling(period).mean()
            
        except Exception as e:
            logger.error(f"计算连续性失败: {e}")
            return pd.Series(0, index=series.index)
    
    def get_feature_names(self) -> List[str]:
        """获取所有时间序列特征名称"""
        feature_names = []
        
        # 滞后特征
        for lag in self.lag_periods:
            feature_names.extend([
                f'close_lag_{lag}', f'high_lag_{lag}', f'low_lag_{lag}', f'open_lag_{lag}',
                f'close_change_lag_{lag}', f'high_change_lag_{lag}', f'low_change_lag_{lag}',
                f'close_ratio_lag_{lag}', f'volume_lag_{lag}', f'volume_change_lag_{lag}',
                f'volume_ratio_lag_{lag}'
            ])
        
        # 滑动窗口特征
        for window in self.window_sizes:
            feature_names.extend([
                f'close_mean_{window}', f'close_std_{window}', f'close_min_{window}', f'close_max_{window}',
                f'close_median_{window}', f'close_q25_{window}', f'close_q75_{window}', f'close_iqr_{window}',
                f'close_position_{window}', f'volatility_{window}', f'volatility_mean_{window}',
                f'skewness_{window}', f'kurtosis_{window}', f'volume_mean_{window}', f'volume_std_{window}',
                f'volume_max_{window}', f'volume_min_{window}', f'volume_ratio_{window}'
            ])
        
        # 动量特征
        for period in self.momentum_periods:
            feature_names.extend([
                f'price_momentum_{period}', f'price_momentum_abs_{period}',
                f'volume_momentum_{period}', f'volume_momentum_abs_{period}',
                f'price_consistency_{period}', f'price_continuity_{period}'
            ])
        
        # 价格加速度特征（独立计算）
        acceleration_periods = [3, 5, 10, 20]
        for period in acceleration_periods:
            feature_names.append(f'price_acceleration_{period}')
        
        # 自相关特征
        for lag in [1, 2, 3, 5, 10, 20]:
            feature_names.append(f'price_autocorr_{lag}')
        for lag in [1, 2, 3, 5, 10]:
            feature_names.append(f'volume_autocorr_{lag}')
        
        # 季节性特征
        feature_names.extend([
            'day_of_week_sin', 'day_of_week_cos', 'day_of_month_sin', 'day_of_month_cos',
            'month_sin', 'month_cos', 'quarter_sin', 'quarter_cos',
            'week_sin', 'week_cos',
            'dominant_frequency', 'dominant_amplitude'
        ])
        
        # 趋势分解特征
        feature_names.extend([
            'trend_direction', 'trend_strength', 'trend_change_frequency',
            'price_deviation_from_trend', 'trend_stability'
        ])
        
        return feature_names


class TimeSeriesFeatures:
    """时间序列特征增强"""

    @staticmethod
    def add_time_series_features(df: pd.DataFrame, column: str) -> pd.DataFrame:
        """为指定列添加时间序列特征"""

        if df is None or df.empty:
            logger.debug("时间序列增强收到空的DataFrame")
            return pd.DataFrame(index=df.index if df is not None else None)

        if column not in df.columns:
            logger.warning(f"时间序列增强未找到列: {column}")
            return pd.DataFrame(index=df.index)

        series = df[column].astype(float)
        features: Dict[str, pd.Series] = {}

        try:
            # 滞后特征
            for lag in [1, 3, 5, 10]:
                features[f'{column}_lag_{lag}'] = series.shift(lag)

            # 滚动统计特征
            windows = [5, 10, 20]
            for window in windows:
                rolling_series = series.rolling(window, min_periods=1)
                features[f'{column}_roll_mean_{window}'] = rolling_series.mean()
                features[f'{column}_roll_std_{window}'] = rolling_series.std().fillna(0.0)
                features[f'{column}_roll_skew_{window}'] = rolling_series.apply(
                    pd.Series.skew, raw=False
                ).fillna(0.0)

            # 变化率特征
            features[f'{column}_pct_change_1'] = series.pct_change().fillna(0.0)
            features[f'{column}_pct_change_5'] = series.pct_change(5).fillna(0.0)

            feature_df = pd.DataFrame(features, index=df.index)
            feature_df = feature_df.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            return feature_df

        except Exception as exc:
            logger.error(f"时间序列特征增强失败 {column}: {exc}")
            return pd.DataFrame(index=df.index)