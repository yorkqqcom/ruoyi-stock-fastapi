import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClusterMixin
from scipy.stats import wasserstein_distance
from typing import List, Dict, Tuple
import torch
from torch import nn
import torch.nn.functional as F

class WassersteinKMeans(BaseEstimator, ClusterMixin):
    def __init__(self, n_clusters: int = 3, max_iter: int = 100, epsilon: float = 0.01):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.epsilon = epsilon
        self.centroids = None
        self.labels_ = None
        
    def _compute_wasserstein_distance(self, X: np.ndarray, Y: np.ndarray) -> float:
        """计算两个分布之间的Wasserstein距离"""
        return wasserstein_distance(X, Y)
    
    def _compute_centroid(self, cluster_data: np.ndarray) -> np.ndarray:
        """计算聚类中心"""
        return np.mean(cluster_data, axis=0)
    
    def _assign_clusters(self, X: np.ndarray) -> np.ndarray:
        """将数据点分配到最近的聚类中心"""
        distances = np.zeros((len(X), self.n_clusters))
        for i in range(self.n_clusters):
            distances[:, i] = np.array([self._compute_wasserstein_distance(x, self.centroids[i]) 
                                      for x in X])
        return np.argmin(distances, axis=1)
    
    def fit(self, X: np.ndarray) -> 'WassersteinKMeans':
        """训练聚类模型"""
        # 初始化聚类中心
        indices = np.random.choice(len(X), self.n_clusters, replace=False)
        self.centroids = X[indices]
        
        for _ in range(self.max_iter):
            # 分配聚类
            labels = self._assign_clusters(X)
            
            # 更新聚类中心
            new_centroids = np.array([self._compute_centroid(X[labels == i]) 
                                    for i in range(self.n_clusters)])
            
            # 检查收敛
            if np.all(np.abs(new_centroids - self.centroids) < self.epsilon):
                break
                
            self.centroids = new_centroids
            
        self.labels_ = labels
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测新数据点的聚类标签"""
        return self._assign_clusters(X)

class MarketRegimeAnalyzer:
    def __init__(self, window_size: int = 30, stride: int = 5, n_clusters: int = 3):
        self.window_size = window_size
        self.stride = stride
        self.n_clusters = n_clusters
        self.clusterer = WassersteinKMeans(n_clusters=n_clusters)
        
    def detect_regime(self, returns_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """检测多只股票的市场机制"""
        all_regimes = {}
        all_features = []
        all_dates = []
        stock_symbols = []
        
        # 收集所有股票的特征
        for symbol, returns in returns_dict.items():
            # 确保returns是单列数据
            if isinstance(returns, pd.DataFrame):
                returns = returns.iloc[:, 0]
                
            # 收集所有窗口的特征
            for i in range(0, len(returns) - self.window_size, self.stride):
                window_data = returns.iloc[i:i+self.window_size]
                features = self._extract_features(window_data)
                all_features.append(features)
                all_dates.append(returns.index[i + self.window_size - 1])
                stock_symbols.append(symbol)
                
        # 将所有特征转换为二维数组
        X = np.array(all_features)
        
        # 聚类
        self.clusterer.fit(X)
        labels = self.clusterer.labels_
        
        # 为每只股票创建结果序列
        for symbol in returns_dict.keys():
            symbol_indices = [i for i, s in enumerate(stock_symbols) if s == symbol]
            symbol_dates = [all_dates[i] for i in symbol_indices]
            symbol_labels = [labels[i] for i in symbol_indices]
            all_regimes[symbol] = pd.Series(symbol_labels, index=symbol_dates)
            
        return all_regimes
    
    def _extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """提取市场特征"""
        # 确保数据是单列
        if isinstance(data, pd.DataFrame):
            data = data.iloc[:, 0]
            
        # 计算收益率
        returns = data.pct_change().dropna()
        
        # 提取固定数量的特征
        features = np.array([
            float(returns.mean()),      # 均值
            float(returns.std()),       # 标准差
            float(returns.skew()),      # 偏度
            float(returns.kurtosis()),  # 峰度
            float(returns.rolling(window=5).std().mean()),  # 平均波动率
            float(returns.rolling(window=5).std().std()),   # 波动率标准差
            float(returns.max()),       # 最大值
            float(returns.min()),       # 最小值
            float(returns.abs().mean()), # 平均绝对收益率
            float(returns.abs().std())   # 绝对收益率标准差
        ])
        
        return features
    
    def analyze_regime_transitions(self, regime_dict: Dict[str, pd.Series]) -> Dict:
        """分析多只股票的机制转换"""
        all_transitions = {}
        all_durations = {}
        all_matrices = {}
        
        for symbol, regime_series in regime_dict.items():
            transitions = []
            current_regime = regime_series.iloc[0]
            start_date = regime_series.index[0]
            
            for date, regime in regime_series.iloc[1:].items():
                if regime != current_regime:
                    transitions.append({
                        'from_regime': int(current_regime),
                        'to_regime': int(regime),
                        'date': date,
                        'duration': (date - start_date).days
                    })
                    current_regime = regime
                    start_date = date
                    
            all_transitions[symbol] = transitions
            all_durations[symbol] = self._calculate_regime_durations(regime_series)
            all_matrices[symbol] = self._calculate_transition_matrix(regime_series)
            
        return {
            'transitions': all_transitions,
            'regime_durations': all_durations,
            'transition_matrices': all_matrices
        }
    
    def _calculate_regime_durations(self, regime_series: pd.Series) -> Dict:
        """计算各机制的持续时间"""
        durations = {}
        current_regime = regime_series.iloc[0]
        start_date = regime_series.index[0]
        
        for date, regime in regime_series.iloc[1:].items():
            if regime != current_regime:
                if current_regime not in durations:
                    durations[current_regime] = []
                durations[current_regime].append((date - start_date).days)
                current_regime = regime
                start_date = date
                
        return {k: np.mean(v) for k, v in durations.items()}
    
    def _calculate_transition_matrix(self, regime_series: pd.Series) -> np.ndarray:
        """计算机制转换矩阵"""
        n_regimes = self.n_clusters
        matrix = np.zeros((n_regimes, n_regimes))
        
        for i in range(len(regime_series) - 1):
            from_regime = int(regime_series.iloc[i])
            to_regime = int(regime_series.iloc[i + 1])
            matrix[from_regime, to_regime] += 1
            
        # 归一化
        row_sums = matrix.sum(axis=1)
        matrix = matrix / row_sums[:, np.newaxis]
        
        return matrix 