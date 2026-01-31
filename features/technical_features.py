#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标特征提取器
基于PriceActions理论的技术指标计算
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

class TechnicalFeatureExtractor:
    """技术指标特征提取器"""
    
    def __init__(self):
        self.ma_periods = [5, 10, 20, 50, 100]
        self.rsi_periods = [6, 14, 21]
        self.macd_params = [(12, 26, 9), (5, 35, 5)]
    
    def extract_all_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取所有技术指标特征"""
        try:
            features = {}
            
            # 移动平均线特征
            features.update(self.extract_moving_average_features(df))
            
            # 震荡指标特征
            features.update(self.extract_oscillator_features(df))
            
            # 成交量指标特征
            features.update(self.extract_volume_features(df))
            
            # 波动率指标特征
            features.update(self.extract_volatility_features(df))
            
            # 动量指标特征
            features.update(self.extract_momentum_features(df))
            
            logger.info(f"提取技术指标特征成功: {len(features)}个特征")
            return features
            
        except Exception as e:
            logger.error(f"提取技术指标特征失败: {e}")
            return {}
    
    def extract_moving_average_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取移动平均线特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            close = df['close'].astype(float)
            
            for period in self.ma_periods:
                if TALIB_AVAILABLE:
                    # 简单移动平均线
                    sma = talib.SMA(close, timeperiod=period)
                    features[f'sma_{period}'] = sma
                    
                    # 指数移动平均线
                    ema = talib.EMA(close, timeperiod=period)
                    features[f'ema_{period}'] = ema
                else:
                    # 使用pandas计算移动平均线
                    sma = close.rolling(period).mean()
                    features[f'sma_{period}'] = sma
                    
                    # 指数移动平均线
                    ema = close.ewm(span=period).mean()
                    features[f'ema_{period}'] = ema
                
                # 价格与均线的关系
                features[f'price_sma_ratio_{period}'] = close / (sma + 1e-8)
                features[f'price_ema_ratio_{period}'] = close / (ema + 1e-8)
                
                # 均线斜率
                features[f'sma_slope_{period}'] = (sma - sma.shift(1)) / (sma.shift(1) + 1e-8)
                features[f'ema_slope_{period}'] = (ema - ema.shift(1)) / (ema.shift(1) + 1e-8)
            
            # 均线交叉特征
            features.update(self.extract_ma_crossover_features(df))
            
            return features
            
        except Exception as e:
            logger.error(f"提取移动平均线特征失败: {e}")
            return {}
    
    def extract_ma_crossover_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取均线交叉特征"""
        features = {}
        
        try:
            close = df['close'].astype(float)
            
            if TALIB_AVAILABLE:
                # 短期和长期均线
                sma_5 = talib.SMA(close, timeperiod=5)
                sma_10 = talib.SMA(close, timeperiod=10)
                sma_20 = talib.SMA(close, timeperiod=20)
                sma_50 = talib.SMA(close, timeperiod=50)
            else:
                # 使用pandas计算移动平均线
                sma_5 = close.rolling(5).mean()
                sma_10 = close.rolling(10).mean()
                sma_20 = close.rolling(20).mean()
                sma_50 = close.rolling(50).mean()
            
            # 金叉死叉
            features['golden_cross_5_10'] = np.where(sma_5 > sma_10, 1, 0)
            features['death_cross_5_10'] = np.where(sma_5 < sma_10, 1, 0)
            features['golden_cross_10_20'] = np.where(sma_10 > sma_20, 1, 0)
            features['death_cross_10_20'] = np.where(sma_10 < sma_20, 1, 0)
            features['golden_cross_20_50'] = np.where(sma_20 > sma_50, 1, 0)
            features['death_cross_20_50'] = np.where(sma_20 < sma_50, 1, 0)
            
            # 均线排列
            features['ma_alignment_bullish'] = np.where(
                (sma_5 > sma_10) & (sma_10 > sma_20) & (sma_20 > sma_50), 1, 0
            )
            features['ma_alignment_bearish'] = np.where(
                (sma_5 < sma_10) & (sma_10 < sma_20) & (sma_20 < sma_50), 1, 0
            )
            
            return features
            
        except Exception as e:
            logger.error(f"提取均线交叉特征失败: {e}")
            return {}
    
    def extract_oscillator_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取震荡指标特征"""
        features = {}
        
        try:
            close = df['close'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            
            # RSI指标
            for period in self.rsi_periods:
                if TALIB_AVAILABLE:
                    rsi = talib.RSI(close, timeperiod=period)
                else:
                    rsi = self._calculate_rsi(close, period)
                features[f'rsi_{period}'] = rsi
                
                # RSI超买超卖
                features[f'rsi_overbought_{period}'] = np.where(rsi > 70, 1, 0)
                features[f'rsi_oversold_{period}'] = np.where(rsi < 30, 1, 0)
                
                # RSI背离
                features[f'rsi_divergence_{period}'] = self.detect_rsi_divergence(close, rsi)
            
            # MACD指标
            for fast, slow, signal in self.macd_params:
                if TALIB_AVAILABLE:
                    macd, macd_signal, macd_hist = talib.MACD(close, 
                                                            fastperiod=fast, 
                                                            slowperiod=slow, 
                                                            signalperiod=signal)
                else:
                    macd, macd_signal, macd_hist = self._calculate_macd(close, fast, slow, signal)
                features[f'macd_{fast}_{slow}_{signal}'] = macd
                features[f'macd_signal_{fast}_{slow}_{signal}'] = macd_signal
                features[f'macd_hist_{fast}_{slow}_{signal}'] = macd_hist
                
                # MACD交叉
                features[f'macd_cross_{fast}_{slow}_{signal}'] = np.where(
                    macd > macd_signal, 1, 0
                )
            
            # 随机指标
            if TALIB_AVAILABLE:
                stoch_k, stoch_d = talib.STOCH(high, low, close)
            else:
                stoch_k, stoch_d = self._calculate_stochastic(high, low, close)
            features['stoch_k'] = stoch_k
            features['stoch_d'] = stoch_d
            features['stoch_cross'] = np.where(stoch_k > stoch_d, 1, 0)
            
            # 威廉指标
            if TALIB_AVAILABLE:
                willr = talib.WILLR(high, low, close)
            else:
                willr = self._calculate_williams_r(high, low, close)
            features['willr'] = willr
            features['willr_oversold'] = np.where(willr < -80, 1, 0)
            features['willr_overbought'] = np.where(willr > -20, 1, 0)
            
            return features
            
        except Exception as e:
            logger.error(f"提取震荡指标特征失败: {e}")
            return {}
    
    def extract_volume_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取成交量指标特征"""
        features = {}
        
        try:
            # 检查是否有volume列
            if 'volume' not in df.columns:
                logger.warning("数据中缺少volume列，跳过成交量特征提取")
                return {}
            
            # 成交量移动平均
            for period in [5, 10, 20, 50]:
                vol_ma = df['volume'].rolling(period).mean()
                features[f'volume_ma_{period}'] = vol_ma
                features[f'volume_ratio_{period}'] = df['volume'] / (vol_ma + 1e-8)
            
            # 成交量价格关系
            features['volume_price_correlation'] = df['volume'].rolling(20).corr(df['close'])
            
            # 成交量异常
            vol_mean = df['volume'].rolling(20).mean()
            vol_std = df['volume'].rolling(20).std()
            features['volume_spike'] = np.where(
                df['volume'] > vol_mean + 2 * vol_std, 1, 0
            )
            features['volume_drop'] = np.where(
                df['volume'] < vol_mean - 2 * vol_std, 1, 0
            )
            
            # OBV指标 - 应用标准化
            obv = talib.OBV(df['close'], df['volume'])
            obv_ma = obv.rolling(20).mean()
            
            # 使用对数缩放处理OBV累积值
            if obv is not None and not obv.empty:
                features['obv'] = np.log1p(np.abs(obv)) * np.sign(obv)
            else:
                features['obv'] = 0
                
            if obv_ma is not None and not obv_ma.empty:
                features['obv_ma'] = np.log1p(np.abs(obv_ma)) * np.sign(obv_ma)
            else:
                features['obv_ma'] = 0
            
            # 安全的比例计算
            if obv_ma is not None and not obv_ma.empty and obv_ma.abs().max() > 1e-8:
                obv_ratio = obv / obv_ma
                features['obv_ratio'] = np.clip(obv_ratio, 0.01, 100)
            else:
                features['obv_ratio'] = 1.0
            
            # 成交量加权平均价格
            close = df['close'].astype(float)
            volume = df['volume'].astype(float)
            vwap = (close * volume).rolling(20).sum() / volume.rolling(20).sum()
            features['vwap'] = vwap
            # 安全的VWAP比例计算
            if vwap is not None and not vwap.empty and vwap.abs().max() > 1e-8:
                price_vwap_ratio = close / vwap
                features['price_vwap_ratio'] = np.clip(price_vwap_ratio, 0.01, 100)
            else:
                features['price_vwap_ratio'] = 1.0
            
            return features
            
        except Exception as e:
            logger.error(f"提取成交量指标特征失败: {e}")
            return {}
    
    def extract_volatility_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取波动率指标特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            close = df['close'].astype(float)
            
            # ATR指标
            if TALIB_AVAILABLE:
                atr = talib.ATR(high, low, close)
            else:
                atr = self._calculate_atr(high, low, close)
            features['atr'] = atr
            features['atr_ratio'] = atr / (close + 1e-8)
            
            # 布林带
            if TALIB_AVAILABLE:
                bb_upper, bb_middle, bb_lower = talib.BBANDS(close)
            else:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close)
            features['bb_upper'] = bb_upper
            features['bb_middle'] = bb_middle
            features['bb_lower'] = bb_lower
            features['bb_width'] = (bb_upper - bb_lower) / (bb_middle + 1e-8)
            features['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower + 1e-8)
            
            # 历史波动率
            returns = close.pct_change()
            features['volatility_20'] = returns.rolling(20).std()
            features['volatility_50'] = returns.rolling(50).std()
            
            # 波动率比率
            features['volatility_ratio'] = features['volatility_20'].astype(float) / (features['volatility_50'].astype(float) + 1e-8)
            
            return features
            
        except Exception as e:
            logger.error(f"提取波动率指标特征失败: {e}")
            return {}
    
    def extract_momentum_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取动量指标特征"""
        features = {}
        
        try:
            # 确保数据类型为float
            close = df['close'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            
            # 动量指标
            for period in [5, 10, 20, 50]:
                if TALIB_AVAILABLE:
                    momentum = talib.MOM(close, timeperiod=period)
                else:
                    momentum = close - close.shift(period)
                features[f'momentum_{period}'] = momentum
                features[f'momentum_ratio_{period}'] = momentum / (close + 1e-8)
            
            # ROC指标
            for period in [5, 10, 20, 50]:
                if TALIB_AVAILABLE:
                    roc = talib.ROC(close, timeperiod=period)
                else:
                    roc = (close / close.shift(period) - 1) * 100
                features[f'roc_{period}'] = roc
            
            # CCI指标
            if TALIB_AVAILABLE:
                cci = talib.CCI(high, low, close)
            else:
                cci = self._calculate_cci(high, low, close)
            features['cci'] = cci
            features['cci_overbought'] = np.where(cci > 100, 1, 0)
            features['cci_oversold'] = np.where(cci < -100, 1, 0)
            
            # ADX指标
            if TALIB_AVAILABLE:
                adx = talib.ADX(high, low, close)
            else:
                adx = self._calculate_adx(high, low, close)
            features['adx'] = adx
            features['adx_strong_trend'] = np.where(adx > 25, 1, 0)
            features['adx_weak_trend'] = np.where(adx < 20, 1, 0)
            
            return features
            
        except Exception as e:
            logger.error(f"提取动量指标特征失败: {e}")
            return {}
    
    def detect_rsi_divergence(self, prices: pd.Series, rsi: pd.Series, 
                            window: int = 20) -> pd.Series:
        """检测RSI背离"""
        try:
            # 简化的背离检测
            price_high = prices.rolling(window).max()
            price_low = prices.rolling(window).min()
            rsi_high = rsi.rolling(window).max()
            rsi_low = rsi.rolling(window).min()
            
            # 顶背离：价格创新高，RSI不创新高
            top_divergence = np.where(
                (prices == price_high) & (rsi < rsi_high.shift(1)), 1, 0
            )
            
            # 底背离：价格创新低，RSI不创新低
            bottom_divergence = np.where(
                (prices == price_low) & (rsi > rsi_low.shift(1)), 1, 0
            )
            
            return pd.Series(top_divergence + bottom_divergence, index=prices.index)
            
        except Exception as e:
            logger.error(f"检测RSI背离失败: {e}")
            return pd.Series(0, index=prices.index)
    
    def _calculate_rsi(self, close: pd.Series, period: int) -> pd.Series:
        """计算RSI指标（替代方案）"""
        try:
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return pd.Series(50, index=close.index)
    
    def _calculate_macd(self, close: pd.Series, fast: int, slow: int, signal: int) -> tuple:
        """计算MACD指标（替代方案）"""
        try:
            ema_fast = close.ewm(span=fast).mean()
            ema_slow = close.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal).mean()
            macd_hist = macd - macd_signal
            return macd, macd_signal, macd_hist
        except:
            return pd.Series(0, index=close.index), pd.Series(0, index=close.index), pd.Series(0, index=close.index)
    
    def _calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> tuple:
        """计算随机指标（替代方案）"""
        try:
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(window=d_period).mean()
            return k_percent, d_percent
        except:
            return pd.Series(50, index=close.index), pd.Series(50, index=close.index)
    
    def _calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """计算威廉指标（替代方案）"""
        try:
            highest_high = high.rolling(window=period).max()
            lowest_low = low.rolling(window=period).min()
            willr = -100 * ((highest_high - close) / (highest_high - lowest_low))
            return willr
        except:
            return pd.Series(-50, index=close.index)
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """计算ATR指标（替代方案）"""
        try:
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            return atr
        except:
            return pd.Series(0, index=close.index)
    
    def _calculate_bollinger_bands(self, close: pd.Series, period: int = 20, std_dev: float = 2) -> tuple:
        """计算布林带（替代方案）"""
        try:
            bb_middle = close.rolling(window=period).mean()
            bb_std = close.rolling(window=period).std()
            bb_upper = bb_middle + (bb_std * std_dev)
            bb_lower = bb_middle - (bb_std * std_dev)
            return bb_upper, bb_middle, bb_lower
        except:
            return pd.Series(close), pd.Series(close), pd.Series(close)
    
    def _calculate_cci(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """计算CCI指标（替代方案）"""
        try:
            typical_price = (high + low + close) / 3
            sma = typical_price.rolling(window=period).mean()
            mean_deviation = typical_price.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
            cci = (typical_price - sma) / (0.015 * mean_deviation)
            return cci
        except:
            return pd.Series(0, index=close.index)
    
    def _calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """计算ADX指标（替代方案）"""
        try:
            # 简化的ADX计算
            tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            
            # 简化的方向性移动
            dm_plus = np.where((high.diff() > low.diff().abs()) & (high.diff() > 0), high.diff(), 0)
            dm_minus = np.where((low.diff().abs() > high.diff()) & (low.diff() < 0), low.diff().abs(), 0)
            
            di_plus = 100 * pd.Series(dm_plus, index=close.index).rolling(window=period).mean() / atr
            di_minus = 100 * pd.Series(dm_minus, index=close.index).rolling(window=period).mean() / atr
            
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            adx = dx.rolling(window=period).mean()
            
            return adx
        except:
            return pd.Series(25, index=close.index)
    
    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        feature_names = []
        
        # 移动平均线特征
        for period in self.ma_periods:
            feature_names.extend([
                f'sma_{period}', f'ema_{period}',
                f'price_sma_ratio_{period}', f'price_ema_ratio_{period}',
                f'sma_slope_{period}', f'ema_slope_{period}'
            ])
        
        # 均线交叉特征
        feature_names.extend([
            'golden_cross_5_10', 'death_cross_5_10',
            'golden_cross_10_20', 'death_cross_10_20',
            'golden_cross_20_50', 'death_cross_20_50',
            'ma_alignment_bullish', 'ma_alignment_bearish'
        ])
        
        # 震荡指标特征
        for period in self.rsi_periods:
            feature_names.extend([
                f'rsi_{period}', f'rsi_overbought_{period}',
                f'rsi_oversold_{period}', f'rsi_divergence_{period}'
            ])
        
        # MACD特征
        for fast, slow, signal in self.macd_params:
            feature_names.extend([
                f'macd_{fast}_{slow}_{signal}', f'macd_signal_{fast}_{slow}_{signal}',
                f'macd_hist_{fast}_{slow}_{signal}', f'macd_cross_{fast}_{slow}_{signal}'
            ])
        
        # 其他震荡指标
        feature_names.extend([
            'stoch_k', 'stoch_d', 'stoch_cross',
            'willr', 'willr_oversold', 'willr_overbought'
        ])
        
        # 成交量特征
        for period in [5, 10, 20, 50]:
            feature_names.extend([
                f'volume_ma_{period}', f'volume_ratio_{period}'
            ])
        
        feature_names.extend([
            'volume_price_correlation', 'volume_spike', 'volume_drop',
            'obv', 'obv_ma', 'obv_ratio', 'vwap', 'price_vwap_ratio'
        ])
        
        # 波动率特征
        feature_names.extend([
            'atr', 'atr_ratio', 'bb_upper', 'bb_middle', 'bb_lower',
            'bb_width', 'bb_position', 'volatility_20', 'volatility_50',
            'volatility_ratio'
        ])
        
        # 动量特征
        for period in [5, 10, 20, 50]:
            feature_names.extend([
                f'momentum_{period}', f'momentum_ratio_{period}',
                f'roc_{period}'
            ])
        
        feature_names.extend([
            'cci', 'cci_overbought', 'cci_oversold',
            'adx', 'adx_strong_trend', 'adx_weak_trend'
        ])
        
        return feature_names
