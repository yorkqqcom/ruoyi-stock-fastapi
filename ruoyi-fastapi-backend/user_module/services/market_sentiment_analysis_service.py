import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM, Dropout
import matplotlib.pyplot as plt
import akshare as ak
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List, Tuple, Optional
import redis
import hashlib

# Redis配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None

# 缓存过期时间（秒）
CACHE_EXPIRE = {
    'stock_prediction': 3600,  # 1小时
    'market_sentiment': 3600,  # 1小时
    'news_analysis': 3600,  # 1小时
}

# 初始化Redis连接
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
except Exception as e:
    print(f"Redis连接失败: {str(e)}")
    redis_client = None

class MarketSentimentAnalysisService:
    def __init__(self):
        self.model_path = "models/lstm_model.h5"
        self.scaler_path = "models/scaler.pkl"
        self.ensure_model_directory()

    def ensure_model_directory(self):
        """确保模型目录存在"""
        os.makedirs("models", exist_ok=True)

    @staticmethod
    def _get_cache_key(method_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        args_str = str(args) + str(sorted(kwargs.items()))
        return f"market_sentiment:{method_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

    @staticmethod
    def _get_cache(method_name: str, *args, **kwargs) -> Dict:
        """从缓存获取数据"""
        if redis_client is None:
            return None
            
        cache_key = MarketSentimentAnalysisService._get_cache_key(method_name, *args, **kwargs)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _set_cache(method_name: str, data: Dict, *args, **kwargs) -> None:
        """设置缓存数据"""
        if redis_client is None:
            return
            
        cache_key = MarketSentimentAnalysisService._get_cache_key(method_name, *args, **kwargs)
        expire_time = CACHE_EXPIRE.get(method_name, 3600)
        
        try:
            redis_client.setex(
                cache_key,
                expire_time,
                json.dumps(data)
            )
        except Exception as e:
            print(f"设置缓存失败: {str(e)}")

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """特征工程"""
        features = data.copy()
        
        # 计算技术指标
        # RSI
        delta = features['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        features['RSI'] = 100 - (100 / (1 + rs))
        
        # 移动平均线
        features['SMA20'] = features['close'].rolling(window=20).mean()
        features['EMA20'] = features['close'].ewm(span=20, adjust=False).mean()
        
        # 布林带
        features['MA20'] = features['close'].rolling(window=20).mean()
        features['20dSTD'] = features['close'].rolling(window=20).std()
        features['Upper_Band'] = features['MA20'] + (features['20dSTD'] * 2)
        features['Lower_Band'] = features['MA20'] - (features['20dSTD'] * 2)
        
        # 删除含有NaN的行
        features = features.dropna()
        return features

    def build_lstm_model(self, input_shape: Tuple[int, int]) -> Sequential:
        """构建LSTM模型"""
        model = Sequential([
            LSTM(units=50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(units=50),
            Dropout(0.2),
            Dense(units=1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def train_model(self, stock_code: str, start_date: str, end_date: str) -> Dict:
        """训练模型"""
        try:
            # 获取股票数据
            stock_data = ak.stock_zh_a_hist(symbol=stock_code, start_date=start_date, end_date=end_date)
            
            # 准备特征
            features = self.prepare_features(stock_data)
            
            # 准备训练数据
            X = features.iloc[:, 1:].values
            y = features.iloc[:, 0].values
            
            # 数据归一化
            scaler = MinMaxScaler(feature_range=(0, 1))
            X_scaled = scaler.fit_transform(X)
            
            # 重塑数据为LSTM所需的形状
            X_reshaped = np.reshape(X_scaled, (X_scaled.shape[0], 1, X_scaled.shape[1]))
            
            # 分割训练集和测试集
            split = int(0.8 * len(X))
            X_train, X_test = X_reshaped[:split], X_reshaped[split:]
            y_train, y_test = y[:split], y[split:]
            
            # 构建和训练模型
            model = self.build_lstm_model((X_train.shape[1], X_train.shape[2]))
            history = model.fit(
                X_train, y_train,
                epochs=100,
                batch_size=32,
                validation_data=(X_test, y_test),
                verbose=0
            )
            
            # 保存模型和scaler
            model.save(self.model_path)
            np.save(self.scaler_path, scaler)
            
            # 进行预测
            predictions = model.predict(X_test)
            predictions_rescaled = scaler.inverse_transform(predictions)
            
            # 计算准确率
            accuracy = self.calculate_accuracy(predictions_rescaled, y_test)
            
            return {
                'status': 'success',
                'accuracy': accuracy,
                'message': '模型训练完成'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'模型训练失败: {str(e)}'
            }

    def calculate_accuracy(self, predictions: np.ndarray, actual: np.ndarray, threshold: float = 0.02) -> float:
        """计算预测准确率"""
        correct = 0
        total = 0
        
        for i in range(len(predictions)-1):
            if abs(predictions[i] - actual[i]) >= threshold:
                total += 1
                if (predictions[i] > actual[i] and actual[i+1] > actual[i]) or \
                   (predictions[i] < actual[i] and actual[i+1] < actual[i]):
                    correct += 1
        
        return correct / total if total > 0 else 0

    async def predict_stock_price(self, stock_code: str, days: int = 5) -> Dict:
        """预测股票价格"""
        try:
            # 检查缓存
            cache_key = f"{stock_code}_{days}"
            cached_result = self._get_cache('stock_prediction', cache_key)
            if cached_result:
                return cached_result
            
            # 获取历史数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            stock_data = ak.stock_zh_a_hist(symbol=stock_code, start_date=start_date, end_date=end_date)
            
            # 准备特征
            features = self.prepare_features(stock_data)
            
            # 加载模型和scaler
            if not os.path.exists(self.model_path):
                return {
                    'status': 'error',
                    'message': '模型未训练'
                }
            
            model = load_model(self.model_path)
            scaler = np.load(self.scaler_path, allow_pickle=True).item()
            
            # 准备预测数据
            X = features.iloc[:, 1:].values
            X_scaled = scaler.transform(X)
            X_reshaped = np.reshape(X_scaled, (X_scaled.shape[0], 1, X_scaled.shape[1]))
            
            # 进行预测
            predictions = model.predict(X_reshaped)
            predictions_rescaled = scaler.inverse_transform(predictions)
            
            # 计算预测结果
            last_price = features['close'].iloc[-1]
            predicted_prices = predictions_rescaled[-days:].flatten()
            price_changes = [(price - last_price) / last_price * 100 for price in predicted_prices]
            
            result = {
                'status': 'success',
                'stock_code': stock_code,
                'last_price': float(last_price),
                'predictions': [float(price) for price in predicted_prices],
                'price_changes': [float(change) for change in price_changes],
                'dates': [(datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(days)]
            }
            
            # 设置缓存
            self._set_cache('stock_prediction', result, cache_key)
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'预测失败: {str(e)}'
            }

    async def analyze_market_sentiment(self) -> Dict:
        """分析市场情绪"""
        try:
            # 检查缓存
            cached_result = self._get_cache('market_sentiment')
            if cached_result:
                return cached_result
            
            # 获取市场数据
            index_data = ak.stock_zh_index_daily_em(symbol="sh000001")
            fund_flow = ak.stock_individual_fund_flow_rank(indicator="今日")
            north_money = ak.stock_hsgt_fund_flow_summary_em()
            
            # 分析市场情绪
            sentiment_score = 0
            
            # 分析指数趋势
            if not index_data.empty:
                ma5 = index_data['close'].rolling(window=5).mean()
                ma20 = index_data['close'].rolling(window=20).mean()
                if ma5.iloc[-1] > ma20.iloc[-1]:
                    sentiment_score += 1
                else:
                    sentiment_score -= 1
            
            # 分析资金流向
            if not fund_flow.empty:
                net_inflow = fund_flow['主力净流入-净额'].sum()
                if net_inflow > 0:
                    sentiment_score += 1
                else:
                    sentiment_score -= 1
            
            # 分析北向资金
            if not north_money.empty:
                north_net = north_money['成交净买额'].sum()
                if north_net > 0:
                    sentiment_score += 1
                else:
                    sentiment_score -= 1
            
            # 确定市场情绪
            if sentiment_score > 0:
                sentiment = "看多"
            elif sentiment_score < 0:
                sentiment = "看空"
            else:
                sentiment = "中性"
            
            result = {
                'status': 'success',
                'sentiment_score': sentiment_score,
                'sentiment': sentiment,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 设置缓存
            self._set_cache('market_sentiment', result)
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'市场情绪分析失败: {str(e)}'
            } 