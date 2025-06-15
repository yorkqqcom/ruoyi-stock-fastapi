import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Union
from sklearn.preprocessing import StandardScaler
from scipy import stats
from scipy.stats import wasserstein_distance
from sklearn.cluster import KMeans

class MarketDataPreprocessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.n_clusters = 3
        self.window_size = 30
        self.distance_metric = 'wasserstein'
        
    def preprocess_data(self, data: pd.DataFrame) -> Dict:
        """预处理市场数据"""
        # 数据清洗
        cleaned_data = self._clean_data(data)
        
        # 计算收益率
        returns = self._calculate_returns(cleaned_data)
        
        # 提取特征
        features = self._extract_features(returns)
        
        # 计算相关性
        correlation = self._calculate_correlation(returns)
        
        # 计算分布特征
        distribution_features = self._calculate_distribution_features(returns)
        
        # 确保volatility是标量值
        volatility = float(returns.std())
        
        return {
            'raw_returns': returns,
            'volatility': volatility,
            'correlation': correlation,
            'distribution_features': distribution_features,
            'cleaned_data': cleaned_data
        }
    
    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        # 删除重复数据
        data = data.drop_duplicates()
        
        # 处理缺失值
        data = data.fillna(method='ffill')
        
        # 处理异常值
        for column in data.select_dtypes(include=[np.number]).columns:
            z_scores = np.abs(stats.zscore(data[column]))
            data = data[z_scores < 3]  # 删除3个标准差以外的值
            
        return data
    
    def _calculate_returns(self, data: pd.DataFrame) -> pd.Series:
        """计算收益率"""
        # 只对数值列计算收益率
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return pd.Series([0.0], index=data.index)
            
        # 如果只有一列，直接返回该列的收益率
        if len(numeric_cols) == 1:
            returns = data[numeric_cols[0]].pct_change()
            return returns.fillna(0.0)
            
        # 如果有多列，计算第一列的收益率
        returns = data[numeric_cols[0]].pct_change()
        return returns.fillna(0.0)
    
    def _extract_features(self, returns: pd.Series) -> np.ndarray:
        """提取市场特征"""
        # 确保returns是Series类型
        if not isinstance(returns, pd.Series):
            returns = pd.Series(returns)
            
        # 替换NaN值
        returns = returns.fillna(0.0)
        
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
        
        # 替换任何可能的NaN值
        return np.nan_to_num(features, nan=0.0)
    
    def _calculate_correlation(self, returns: pd.Series) -> pd.DataFrame:
        """计算相关性矩阵"""
        # 确保returns是Series类型
        if not isinstance(returns, pd.Series):
            returns = pd.Series(returns)
            
        # 替换NaN值
        returns = returns.fillna(0.0)
            
        # 对于单列数据，创建自相关矩阵
        if len(returns.shape) == 1:
            # 创建滞后序列
            lags = pd.DataFrame({
                'returns': returns,
                'returns_lag1': returns.shift(1),
                'returns_lag2': returns.shift(2),
                'returns_lag3': returns.shift(3),
                'returns_lag4': returns.shift(4)
            }).fillna(0.0)
            
            # 计算相关性矩阵
            corr_matrix = lags.corr()
            return corr_matrix.fillna(0.0)
            
        # 对于多列数据，直接计算相关性
        corr_matrix = returns.corr()
        return corr_matrix.fillna(0.0)
    
    def _calculate_distribution_features(self, returns: pd.DataFrame) -> Dict:
        """计算分布特征"""
        features = {}
        
        # 确保returns是单列数据
        if isinstance(returns, pd.DataFrame):
            returns = returns.iloc[:, 0]
        
        # 计算MMD特征
        features['mmd'] = float(self._calculate_mmd(returns))
        
        # 计算分位数特征
        quantiles = returns.quantile([0.25, 0.5, 0.75])
        features['quantiles'] = {
            'q25': float(quantiles[0.25]),
            'q50': float(quantiles[0.5]),
            'q75': float(quantiles[0.75])
        }
        
        # 计算极值特征
        features['max_drawdown'] = float(self._calculate_max_drawdown(returns))
        features['max_upside'] = float(self._calculate_max_upside(returns))
        
        return features
    
    def _calculate_mmd(self, returns: pd.DataFrame) -> float:
        """计算最大均值差异（MMD）"""
        # 使用RBF核函数
        def rbf_kernel(x, y, gamma=1.0):
            return np.exp(-gamma * np.sum((x - y) ** 2))
        
        # 计算MMD统计量
        n = len(returns)
        mmd = 0
        
        for i in range(n):
            for j in range(n):
                mmd += rbf_kernel(returns.iloc[i], returns.iloc[j])
                
        mmd = mmd / (n * n)
        return mmd
    
    def _calculate_max_drawdown(self, returns: pd.DataFrame) -> float:
        """计算最大回撤"""
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = cumulative_returns / rolling_max - 1
        return drawdowns.min().min()
    
    def _calculate_max_upside(self, returns: pd.DataFrame) -> float:
        """计算最大上涨"""
        cumulative_returns = (1 + returns).cumprod()
        rolling_min = cumulative_returns.expanding().min()
        upsides = cumulative_returns / rolling_min - 1
        return upsides.max().max()
    
    def normalize_features(self, features: Dict) -> Dict:
        """标准化特征"""
        normalized_features = {}
        
        for key, value in features.items():
            if isinstance(value, (pd.Series, pd.DataFrame)):
                normalized_features[key] = pd.DataFrame(
                    self.scaler.fit_transform(value),
                    index=value.index,
                    columns=value.columns
                )
            elif isinstance(value, np.ndarray):
                normalized_features[key] = self.scaler.fit_transform(value)
            else:
                normalized_features[key] = value
                
        return normalized_features

    def _calculate_wasserstein_distance(self, x: np.ndarray, y: np.ndarray) -> float:
        """计算两个分布之间的 Wasserstein 距离"""
        return wasserstein_distance(x, y)

    def _calculate_mmd_distance(self, x: np.ndarray, y: np.ndarray) -> float:
        """计算最大均值差异 (MMD)"""
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        return abs(x_mean - y_mean)

    def _calculate_distance_matrix(self, data: np.ndarray) -> np.ndarray:
        """计算距离矩阵"""
        n_samples = len(data)
        distance_matrix = np.zeros((n_samples, n_samples))
        
        for i in range(n_samples):
            for j in range(i+1, n_samples):
                if self.distance_metric == 'wasserstein':
                    dist = self._calculate_wasserstein_distance(data[i], data[j])
                else:  # mmd
                    dist = self._calculate_mmd_distance(data[i], data[j])
                distance_matrix[i, j] = distance_matrix[j, i] = dist
                
        return distance_matrix

    def _find_optimal_clusters(self, data: np.ndarray, max_clusters: int = 5) -> int:
        """使用肘部法则找到最佳聚类数"""
        inertias = []
        k_range = range(1, max_clusters + 1)
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42)
            kmeans.fit(data)
            inertias.append(kmeans.inertia_)
            
        # 计算拐点
        deltas = np.diff(inertias)
        optimal_k = np.argmax(deltas) + 1
        
        return optimal_k

    def analyze_market_regimes(self, returns: pd.Series) -> Dict:
        """分析市场机制"""
        # 计算滚动窗口特征
        windows = []
        for i in range(len(returns) - self.window_size + 1):
            window = returns.iloc[i:i+self.window_size].values
            windows.append(window)
            
        windows = np.array(windows)
        
        # 计算距离矩阵
        distance_matrix = self._calculate_distance_matrix(windows)
        
        # 找到最佳聚类数
        optimal_k = self._find_optimal_clusters(distance_matrix)
        self.n_clusters = optimal_k
        
        # 应用聚类
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42)
        labels = kmeans.fit_predict(distance_matrix)
        
        # 分析每个机制的特征
        regimes = []
        for i in range(self.n_clusters):
            regime_data = returns[labels == i]
            regime = {
                'id': i,
                'type': self._determine_regime_type(regime_data),
                'volatility': float(regime_data.std()),
                'mean_return': float(regime_data.mean()),
                'correlation': self._calculate_correlation(regime_data),
                'start_date': regime_data.index[0].strftime('%Y-%m-%d'),
                'end_date': regime_data.index[-1].strftime('%Y-%m-%d')
            }
            regimes.append(regime)
            
        return {
            'regimes': regimes,
            'labels': labels.tolist(),
            'optimal_clusters': optimal_k
        }

    def _determine_regime_type(self, data: pd.Series) -> str:
        """确定市场机制类型"""
        mean_return = data.mean()
        volatility = data.std()
        
        if volatility > 0.02:  # 高波动
            return 'high_volatility'
        elif mean_return > 0.001:  # 上升趋势
            return 'uptrend'
        elif mean_return < -0.001:  # 下降趋势
            return 'downtrend'
        else:  # 震荡
            return 'sideways'

    def extract_features(self, data: pd.Series) -> np.ndarray:
        """提取特征"""
        features = []
        
        # 基本统计特征
        features.extend([
            data.mean(),
            data.std(),
            data.skew(),
            data.kurtosis()
        ])
        
        # 波动率特征
        volatility = data.rolling(window=20).std()
        features.extend([
            volatility.mean(),
            volatility.std(),
            volatility.max()
        ])
        
        # 趋势特征
        returns = data.pct_change()
        features.extend([
            returns.mean(),
            returns.std(),
            returns.skew()
        ])
        
        return np.array(features)

    def generate_trading_signals(self, data: pd.Series, regimes: List[Dict]) -> List[Dict]:
        """生成交易信号"""
        signals = []
        current_regime = None
        
        for i in range(len(data)):
            # 确定当前机制
            for regime in regimes:
                if regime['start_date'] <= data.index[i].strftime('%Y-%m-%d') <= regime['end_date']:
                    current_regime = regime
                    break
            
            if current_regime:
                # 基于机制生成信号
                signal = self._generate_signal(data.iloc[i], current_regime)
                if signal:
                    signals.append({
                        'date': data.index[i].strftime('%Y-%m-%d'),
                        'type': signal['type'],
                        'confidence': signal['confidence'],
                        'description': signal['description']
                    })
        
        return signals

    def _generate_signal(self, current_data: float, regime: Dict) -> Dict:
        """生成单个交易信号"""
        if regime['type'] == 'high_volatility':
            return {
                'type': 'HIGH_VOLATILITY',
                'confidence': 0.8,
                'description': '市场波动较大，建议控制仓位，设置严格止损'
            }
        elif regime['type'] == 'uptrend':
            return {
                'type': 'BUY_SPREAD',
                'confidence': 0.7,
                'description': '市场处于上升趋势，可以考虑逢低买入'
            }
        elif regime['type'] == 'downtrend':
            return {
                'type': 'SELL_SPREAD',
                'confidence': 0.7,
                'description': '市场处于下降趋势，建议观望或减仓'
            }
        else:  # sideways
            return {
                'type': 'REGIME_CHANGE',
                'confidence': 0.6,
                'description': '市场处于震荡期，建议高抛低吸'
            } 