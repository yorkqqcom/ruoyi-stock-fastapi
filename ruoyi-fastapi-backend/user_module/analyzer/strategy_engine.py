import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from statsmodels.tsa.stattools import coint
from scipy import stats

class StrategyEngine:
    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold
        
    def generate_pairs_trading_signal(self, cluster_data: Dict) -> List[Dict]:
        """生成配对交易信号"""
        signals = []
        
        for cluster in cluster_data['clusters']:
            stocks = cluster['members']
            # 寻找协整对
            pairs = self._find_cointegrated_pairs(stocks)
            
            # 分析价差
            for pair in pairs:
                spread_signals = self._analyze_spread(pair)
                signals.extend(spread_signals)
                
        return signals
    
    def _find_cointegrated_pairs(self, stocks: pd.DataFrame) -> List[Tuple]:
        """寻找协整对"""
        n = len(stocks.columns)
        pairs = []
        
        for i in range(n):
            for j in range(i+1, n):
                stock1 = stocks.iloc[:, i]
                stock2 = stocks.iloc[:, j]
                
                # 计算协整性
                score, pvalue, _ = coint(stock1, stock2)
                
                if pvalue < self.threshold:
                    pairs.append((stock1, stock2, pvalue))
                    
        return pairs
    
    def _analyze_spread(self, pair: Tuple) -> List[Dict]:
        """分析价差"""
        stock1, stock2, pvalue = pair
        
        # 计算价差
        spread = stock1 - stock2
        
        # 计算价差的统计特征
        mean = spread.mean()
        std = spread.std()
        
        # 生成信号
        signals = []
        
        # 计算z-score
        z_score = (spread - mean) / std
        
        # 生成交易信号
        for i in range(len(spread)):
            if z_score.iloc[i] > 2:  # 价差过大，做空价差
                signals.append({
                    'date': spread.index[i],
                    'type': 'SELL_SPREAD',
                    'stock1': stock1.name,
                    'stock2': stock2.name,
                    'z_score': z_score.iloc[i],
                    'confidence': 1 - pvalue
                })
            elif z_score.iloc[i] < -2:  # 价差过小，做多价差
                signals.append({
                    'date': spread.index[i],
                    'type': 'BUY_SPREAD',
                    'stock1': stock1.name,
                    'stock2': stock2.name,
                    'z_score': z_score.iloc[i],
                    'confidence': 1 - pvalue
                })
                
        return signals
    
    def generate_regime_signals(self, regime_data: Dict) -> List[Dict]:
        """生成机制转换信号"""
        signals = []
        
        # 分析机制转换
        transitions = regime_data['transitions']
        transition_matrix = regime_data['transition_matrix']
        
        for transition in transitions:
            from_regime = transition['from_regime']
            to_regime = transition['to_regime']
            date = transition['date']
            
            # 计算转换概率
            prob = transition_matrix[from_regime, to_regime]
            
            if prob > 0.7:  # 高概率转换
                signals.append({
                    'date': date,
                    'type': 'REGIME_CHANGE',
                    'from_regime': from_regime,
                    'to_regime': to_regime,
                    'probability': prob,
                    'duration': transition['duration']
                })
                
        return signals
    
    def generate_volatility_signals(self, volatility: float) -> List[Dict]:
        """生成波动率信号"""
        signals = []
        
        # 使用固定的阈值
        vol_low = 0.01  # 1% 的低波动率阈值
        vol_high = 0.03  # 3% 的高波动率阈值
        
        # 生成信号
        if volatility > vol_high:  # 高波动率
            signals.append({
                'date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'type': 'HIGH_VOLATILITY',
                'value': float(volatility),
                'threshold': float(vol_high)
            })
        elif volatility < vol_low:  # 低波动率
            signals.append({
                'date': pd.Timestamp.now().strftime('%Y-%m-%d'),
                'type': 'LOW_VOLATILITY',
                'value': float(volatility),
                'threshold': float(vol_low)
            })
                
        return signals
    
    def combine_signals(self, signals_list: List[List[Dict]]) -> List[Dict]:
        """合并多个信号源"""
        all_signals = []
        
        for signals in signals_list:
            all_signals.extend(signals)
            
        # 按日期排序
        all_signals.sort(key=lambda x: x['date'])
        
        # 合并同一天的信号
        combined_signals = []
        current_date = None
        current_signals = []
        
        for signal in all_signals:
            if signal['date'] != current_date:
                if current_signals:
                    combined_signals.append({
                        'date': current_date,
                        'signals': current_signals
                    })
                current_date = signal['date']
                current_signals = [signal]
            else:
                current_signals.append(signal)
                
        if current_signals:
            combined_signals.append({
                'date': current_date,
                'signals': current_signals
            })
            
        return combined_signals 