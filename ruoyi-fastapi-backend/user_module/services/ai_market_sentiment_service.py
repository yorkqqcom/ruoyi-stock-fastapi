import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import redis
import json
import hashlib
import akshare as ak
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout, BatchNormalization
import tensorflow as tf
import matplotlib.pyplot as plt
import io
import base64
import time

# Redis配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None

# 缓存过期时间（秒）
CACHE_EXPIRE = {
    'sentiment_analysis': 300,  # 5分钟
    'market_prediction': 300,  # 5分钟
    'news_analysis': 300,  # 5分钟
    'technical_indicators': 300,  # 5分钟
    'mean_reversion': 300,  # 5分钟
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

class AIMarketSentimentService:
    @staticmethod
    def _get_cache_key(method_name: str, *args, **kwargs) -> str:
        """
        生成缓存键
        """
        args_str = str(args) + str(sorted(kwargs.items()))
        return f"ai_market_sentiment:{method_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

    @staticmethod
    def _get_cache(method_name: str, *args, **kwargs) -> Dict:
        """
        从缓存获取数据
        """
        if redis_client is None:
            return None
            
        cache_key = AIMarketSentimentService._get_cache_key(method_name, *args, **kwargs)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _set_cache(method_name: str, data: Dict, *args, **kwargs) -> None:
        """
        设置缓存数据
        """
        if redis_client is None:
            return
            
        cache_key = AIMarketSentimentService._get_cache_key(method_name, *args, **kwargs)
        expire_time = CACHE_EXPIRE.get(method_name, 300)
        
        try:
            redis_client.setex(
                cache_key,
                expire_time,
                json.dumps(data)
            )
        except Exception as e:
            print(f"设置缓存失败: {str(e)}")

    @staticmethod
    def _prepare_features(data: pd.DataFrame, time_granularity: str = '1d') -> Tuple[pd.DataFrame, pd.Series]:
        """
        准备特征数据，删除冗余指标，添加对数收益率
        """
        # 打印输入数据的列名，用于调试
        print("输入数据的列名:", data.columns.tolist())
        
        # 定义中文列名到英文列名的映射
        column_mapping = {
            '股票代码': 'symbol',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '换手率': 'turnover_rate'
        }
        
        # 重命名列
        data = data.rename(columns=column_mapping)
        
        features = pd.DataFrame(index=data.index)
        
        # 1. 基础价格特征
        features['close'] = data['close']
        features['open'] = data['open']
        features['high'] = data['high']
        features['low'] = data['low']
        features['volume'] = data['volume']
        
        # 2. 计算对数收益率作为目标变量
        features['target'] = np.log(features['close'] / features['close'].shift(1))
        
        # 3. 移动平均线 - 只保留SMA
        features['SMA20'] = features['close'].rolling(window=20).mean()
        features['SMA60'] = features['close'].rolling(window=60).mean()
        
        # 4. 波动率指标
        features['volatility_20d'] = features['close'].pct_change().rolling(window=20).std()
        features['volatility_60d'] = features['close'].pct_change().rolling(window=60).std()
        
        # 5. 成交量指标
        features['Volume_MA5'] = features['volume'].rolling(window=5).mean()
        features['Volume_MA20'] = features['volume'].rolling(window=20).mean()
        features['volume_ratio'] = features['volume'] / features['Volume_MA20']
        
        # 6. 价格动量指标
        features['momentum_1d'] = features['close'].pct_change()
        features['momentum_5d'] = features['close'].pct_change(5)
        features['momentum_20d'] = features['close'].pct_change(20)
        
        # 7. 价格位置指标
        features['price_position_20d'] = (features['close'] - features['SMA20']) / features['SMA20']
        features['price_position_60d'] = (features['close'] - features['SMA60']) / features['SMA60']
        
        # 8. 波动率比率
        features['volatility_ratio'] = features['volatility_20d'] / features['volatility_60d']
        
        # 9. RSI指标计算
        delta = features['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['RSI'] = 100 - (100 / (1 + rs))
        
        # 10. MACD指标计算
        exp1 = features['close'].ewm(span=12, adjust=False).mean()
        exp2 = features['close'].ewm(span=26, adjust=False).mean()
        features['MACD'] = exp1 - exp2
        features['Signal_Line'] = features['MACD'].ewm(span=9, adjust=False).mean()
        features['MACD_Hist'] = features['MACD'] - features['Signal_Line']
        
        # 11. ATR指标计算
        tr1 = features['high'] - features['low']
        tr2 = abs(features['high'] - features['close'].shift(1))
        tr3 = abs(features['low'] - features['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        features['ATR'] = tr.rolling(window=14).mean()
        
        # 12. 布林带指标
        features['MA20'] = features['close'].rolling(window=20).mean()
        features['20dSTD'] = features['close'].rolling(window=20).std()
        features['Upper_Band'] = features['MA20'] + (features['20dSTD'] * 2)
        features['Lower_Band'] = features['MA20'] - (features['20dSTD'] * 2)
        
        # 13. 时间特征
        if isinstance(data.index, pd.DatetimeIndex):
            features['day_of_week'] = data.index.dayofweek
            features['month'] = data.index.month
        
        # 14. 填充缺失值
        features = features.fillna(method='ffill').fillna(0)
        
        return features, features['target']

    @staticmethod
    def _build_lstm_model(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> Tuple[tf.keras.Model, MinMaxScaler, MinMaxScaler, np.ndarray, np.ndarray]:
        """
        构建简化版LSTM模型，并添加性能监控
        """
        import time
        start_time = time.time()
        
        # 创建两个scaler，一个用于特征，一个用于目标值
        feature_scaler = MinMaxScaler(feature_range=(0, 1))
        target_scaler = MinMaxScaler(feature_range=(0, 1))
        
        # 标准化特征数据
        X_train_scaled = feature_scaler.fit_transform(X_train)
        X_test_scaled = feature_scaler.transform(X_test)
        
        # 标准化目标数据
        y_train_scaled = target_scaler.fit_transform(y_train.reshape(-1, 1))
        y_test_scaled = target_scaler.transform(y_test.reshape(-1, 1))
        
        # 使用60天的时间步长
        time_steps = 60
        
        # 创建序列数据
        def create_sequences(data, time_steps):
            X, y = [], []
            for i in range(len(data) - time_steps):
                X.append(data[i:(i + time_steps)])
                y.append(data[i + time_steps, 0])
            return np.array(X), np.array(y)
        
        # 创建训练和测试序列
        X_train_seq, y_train_seq = create_sequences(X_train_scaled, time_steps)
        X_test_seq, y_test_seq = create_sequences(X_test_scaled, time_steps)
        
        # 构建简化版LSTM模型
        model = Sequential([
            LSTM(units=50, input_shape=(time_steps, X_train_seq.shape[2])),
            Dense(1)
        ])
        
        # 使用Adam优化器
        optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
        
        # 编译模型
        model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=['mae']
        )
        
        # 添加早停机制
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        # 添加训练时间监控
        class TimeMonitor(tf.keras.callbacks.Callback):
            def on_train_begin(self, logs=None):
                self.train_start_time = time.time()
            
            def on_train_end(self, logs=None):
                self.train_time = time.time() - self.train_start_time
                print(f"\n训练时间: {self.train_time:.2f} 秒")
        
        time_monitor = TimeMonitor()
        
        # 训练模型
        history = model.fit(
            X_train_seq, y_train_seq,
            epochs=100,
            batch_size=32,
            validation_data=(X_test_seq, y_test_seq),
            callbacks=[early_stopping, time_monitor],
            verbose=1
        )
        
        # 进行预测并还原
        predictions = model.predict(X_test_seq)
        predictions_rescaled = target_scaler.inverse_transform(predictions)
        predictions_rescaled = predictions_rescaled.flatten()
        
        # 计算预测稳定性指标
        prediction_std = np.std(predictions_rescaled)
        prediction_range = np.ptp(predictions_rescaled)
        
        # 计算预测准确率
        mae = np.mean(np.abs(predictions_rescaled - y_test[time_steps:]))
        mse = np.mean((predictions_rescaled - y_test[time_steps:]) ** 2)
        rmse = np.sqrt(mse)
        
        # 计算方向准确率
        actual_direction = np.sign(np.diff(y_test[time_steps:]))
        pred_direction = np.sign(np.diff(predictions_rescaled))
        direction_accuracy = np.mean(actual_direction == pred_direction) * 100
        
        # 打印评估指标
        print("\n模型评估指标:")
        print(f"预测标准差: {prediction_std:.4f}")
        print(f"预测范围: {prediction_range:.4f}")
        print(f"平均绝对误差 (MAE): {mae:.4f}")
        print(f"均方根误差 (RMSE): {rmse:.4f}")
        print(f"方向准确率: {direction_accuracy:.2f}%")
        
        # 计算总运行时间
        total_time = time.time() - start_time
        print(f"总运行时间: {total_time:.2f} 秒")
        
        return model, feature_scaler, target_scaler, X_test_seq, predictions_rescaled

    @staticmethod
    def _mean_reversion_strategy(predictions: np.ndarray, actual_prices: np.ndarray, threshold: float = 0.02) -> np.ndarray:
        """
        均值回归交易策略（修复数组真值问题）
        """
        # 确保输入是一维数组
        predictions = predictions.flatten()
        actual_prices = actual_prices.flatten()
        
        # 确保两个数组长度相同
        min_length = min(len(predictions), len(actual_prices))
        predictions = predictions[:min_length]
        actual_prices = actual_prices[:min_length]
        
        deviation = predictions - actual_prices
        decisions = []
        
        for dev in deviation:
            # 使用显式的元素级比较
            if abs(dev) >= threshold:
                if dev > 0:
                    decisions.append(1)  # 买入信号
                else:
                    decisions.append(-1)  # 卖出信号
            else:
                decisions.append(0)  # 不交易
                
        return np.array(decisions)

    @staticmethod
    async def get_sentiment_analysis(symbol: str = "sh000001") -> Dict:
        """
        获取AI市场情绪分析数据
        """
        # 尝试从缓存获取数据
        cached_data = AIMarketSentimentService._get_cache('sentiment_analysis', symbol)
        if cached_data is not None:
            return cached_data

        try:
            # 获取股票数据
            if symbol.startswith(('sh', 'sz')):
                df = ak.stock_zh_index_daily_em(symbol=symbol,adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            
            if df.empty:
                return {
                    'sentiment_score': 0,
                    'market_trend': 'neutral',
                    'confidence': 0,
                    'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # 计算技术指标
            features, target = AIMarketSentimentService._prepare_features(df)
            
            # 准备训练数据
            X = features.values
            y = target.values
            
            # 验证数据
            if len(X) < 60:  # 确保有足够的数据进行训练
                return {
                    'sentiment_score': 0,
                    'market_trend': 'neutral',
                    'confidence': 0,
                    'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': '历史数据不足，至少需要60个交易日的数据'
                }
            
            # 检查数据有效性
            if np.isnan(X).any() or np.isnan(y).any():
                print("警告：数据中存在NaN值，进行填充...")
                X = np.nan_to_num(X, nan=0.0)
                y = np.nan_to_num(y, nan=0.0)
            
            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # 验证训练集和测试集
            if len(X_train) < 60 or len(X_test) < 60:
                return {
                    'sentiment_score': 0,
                    'market_trend': 'neutral',
                    'confidence': 0,
                    'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': '训练集或测试集数据不足'
                }
            
            try:
                # 构建和训练模型
                model, feature_scaler, target_scaler, X_test_reshaped, predictions_rescaled = AIMarketSentimentService._build_lstm_model(X_train, y_train, X_test, y_test)
            except Exception as e:
                print(f"模型训练失败: {str(e)}")
                return {
                    'sentiment_score': 0,
                    'market_trend': 'neutral',
                    'confidence': 0,
                    'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': f'模型训练失败: {str(e)}'
                }
            
            # 确保 predictions_rescaled 是一维数组
            if predictions_rescaled.ndim > 1:
                predictions_rescaled = predictions_rescaled.flatten()
            
            # === 修复开始 ===
            # 获取与 _build_lstm_model 中相同的 time_steps 值
            time_steps = 60
            
            # 调整 y_test 长度以匹配预测值
            if len(y_test) > time_steps:
                y_test_adjusted = y_test[time_steps:]
            else:
                y_test_adjusted = y_test  # 后备方案
            
            # 应用均值回归策略（使用调整后的 y_test）
            trading_decisions = AIMarketSentimentService._mean_reversion_strategy(
                predictions_rescaled, 
                y_test_adjusted
            )
            # === 修复结束 ===
            
            # 计算策略准确率（使用调整后的 y_test）
            correct_decisions = sum(1 for i in range(len(trading_decisions)-1) if
                (trading_decisions[i] == 1 and y_test_adjusted[i+1] > y_test_adjusted[i]) or
                (trading_decisions[i] == -1 and y_test_adjusted[i+1] < y_test_adjusted[i]))
            
            total_trades = sum(1 for decision in trading_decisions if decision != 0)
            accuracy = correct_decisions / total_trades if total_trades > 0 else 0
            
            # 计算市场情绪得分
            sentiment_score = accuracy * 100
            
            # 确定市场趋势
            if sentiment_score > 60:
                market_trend = 'bullish'
            elif sentiment_score < 40:
                market_trend = 'bearish'
            else:
                market_trend = 'neutral'
            
            result = {
                'sentiment_score': round(sentiment_score, 2),
                'market_trend': market_trend,
                'confidence': round(accuracy * 100, 2),
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 设置缓存
            AIMarketSentimentService._set_cache('sentiment_analysis', result, symbol)
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"获取市场情绪分析数据失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return {
                'sentiment_score': 0,
                'market_trend': 'neutral',
                'confidence': 0,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    @staticmethod
    def _calculate_prediction_accuracy(predictions: np.ndarray, actual: np.ndarray) -> Dict:
        """计算预测准确率"""
        try:
            print("\n开始计算预测准确率...")
            print(f"预测值形状: {predictions.shape}")
            print(f"实际值形状: {actual.shape}")
            
            # 确保数据是一维数组
            predictions = predictions.flatten()
            actual = actual.flatten()
            
            # 检查数据有效性
            if len(predictions) == 0 or len(actual) == 0:
                print("错误：预测值或实际值为空")
                return {
                    'accuracy': 0.0,
                    'direction_accuracy': 0.0,
                    'rmse': 0.0,
                    'mae': 0.0,
                    'r2': 0.0,
                    'relative_error': 0.0,
                    'bias': 0.0
                }
                
            if len(predictions) != len(actual):
                print(f"错误：预测值和实际值长度不匹配 ({len(predictions)} vs {len(actual)})")
                return {
                    'accuracy': 0.0,
                    'direction_accuracy': 0.0,
                    'rmse': 0.0,
                    'mae': 0.0,
                    'r2': 0.0,
                    'relative_error': 0.0,
                    'bias': 0.0
                }
            
            # 移除无效值
            valid_mask = ~(np.isnan(predictions) | np.isnan(actual) | np.isinf(predictions) | np.isinf(actual))
            predictions = predictions[valid_mask]
            actual = actual[valid_mask]
            
            if len(predictions) == 0:
                print("错误：处理后没有有效数据")
                return {
                    'accuracy': 0.0,
                    'direction_accuracy': 0.0,
                    'rmse': 0.0,
                    'mae': 0.0,
                    'r2': 0.0,
                    'relative_error': 0.0,
                    'bias': 0.0
                }
            
            print(f"有效数据点数量: {len(predictions)}")
            
            # 计算相对误差
            print("\n计算相对误差...")
            relative_error = float(np.mean(np.abs(predictions - actual) / (np.abs(actual) + 1e-10)))
            print(f"相对误差: {relative_error:.4f}")
            
            # 计算方向准确率
            print("\n计算方向准确率...")
            pred_changes = np.diff(predictions)
            actual_changes = np.diff(actual)
            print(f"预测变化值范围: [{pred_changes.min():.4f}, {pred_changes.max():.4f}]")
            print(f"实际变化值范围: [{actual_changes.min():.4f}, {actual_changes.max():.4f}]")
            
            # 使用更宽松的方向判断标准
            direction_correct = np.sum(np.sign(pred_changes) == np.sign(actual_changes))
            direction_accuracy = float(direction_correct / len(pred_changes) if len(pred_changes) > 0 else 0)
            print(f"方向准确率: {direction_accuracy:.4f}")
            
            # 计算RMSE
            print("\n计算RMSE...")
            rmse = float(np.sqrt(np.mean((predictions - actual) ** 2)))
            print(f"RMSE: {rmse:.4f}")
            
            # 计算MAE
            print("\n计算MAE...")
            mae = float(np.mean(np.abs(predictions - actual)))
            print(f"MAE: {mae:.4f}")
            
            # 计算R²
            print("\n计算R²...")
            ss_total = np.sum((actual - np.mean(actual)) ** 2)
            ss_residual = np.sum((actual - predictions) ** 2)
            r2 = float(1 - (ss_residual / (ss_total + 1e-10)))
            print(f"R²: {r2:.4f}")
            
            # 计算预测偏差
            print("\n计算预测偏差...")
            bias = float(np.mean(predictions - actual))
            print(f"预测偏差: {bias:.4f}")
            
            # 计算综合评分
            print("\n计算综合评分...")
            
            # 归一化各个指标
            normalized_relative_error = 1 - min(relative_error, 1.0)  # 相对误差越小越好
            normalized_direction = direction_accuracy  # 方向准确率越大越好
            normalized_rmse = 1 - min(rmse / (np.std(actual) + 1e-10), 1.0)  # RMSE越小越好
            normalized_mae = 1 - min(mae / (np.std(actual) + 1e-10), 1.0)  # MAE越小越好
            normalized_r2 = max(0, min(r2, 1.0))  # R²越大越好，限制在[0,1]范围内
            normalized_bias = 1 - min(abs(bias) / (np.std(actual) + 1e-10), 1.0)  # 偏差越小越好
            
            print("\n归一化后的指标值:")
            print(f"relative_error: {normalized_relative_error:.4f}")
            print(f"direction: {normalized_direction:.4f}")
            print(f"rmse: {normalized_rmse:.4f}")
            print(f"mae: {normalized_mae:.4f}")
            print(f"r2: {normalized_r2:.4f}")
            print(f"bias: {normalized_bias:.4f}")
            
            # 计算加权平均分数
            weights = {
                'relative_error': 0.2,
                'direction': 0.3,
                'rmse': 0.15,
                'mae': 0.15,
                'r2': 0.1,
                'bias': 0.1
            }
            
            final_score = float((
                normalized_relative_error * weights['relative_error'] +
                normalized_direction * weights['direction'] +
                normalized_rmse * weights['rmse'] +
                normalized_mae * weights['mae'] +
                normalized_r2 * weights['r2'] +
                normalized_bias * weights['bias']
            ) * 100)
            
            print("\n最终计算结果:")
            print(f"方向准确率: {direction_accuracy*100:.2f}%")
            print(f"RMSE: {rmse:.4f}")
            print(f"MAE: {mae:.4f}")
            print(f"R²: {r2:.4f}")
            print(f"相对误差: {relative_error:.4f}")
            print(f"预测偏差: {bias:.4f}")
            print(f"综合准确率: {final_score:.2f}%")
            print(f"预测置信度: {final_score:.2f}%")
            
            return {
                'accuracy': float(final_score),
                'direction_accuracy': float(direction_accuracy * 100),
                'rmse': float(rmse),
                'mae': float(mae),
                'r2': float(r2),
                'relative_error': float(relative_error),
                'bias': float(bias)
            }
            
        except Exception as e:
            print(f"计算预测准确率时发生错误: {str(e)}")
            return {
                'accuracy': 0.0,
                'direction_accuracy': 0.0,
                'rmse': 0.0,
                'mae': 0.0,
                'r2': 0.0,
                'relative_error': 0.0,
                'bias': 0.0
            }

    @staticmethod
    def _generate_future_features(last_features: pd.Series, last_date: pd.Timestamp, future_dates: pd.DatetimeIndex) -> pd.DataFrame:
        """
        生成未来特征数据，基于前一天的预测动态更新
        """
        future_features = pd.DataFrame()
        last_valid_data = last_features.copy()
        
        for i, date in enumerate(future_dates):
            # 创建新行（复制并更新时间特征）
            new_row = last_valid_data.copy()
            
            # 更新关键价格特征（基于随机波动假设）
            if i == 0:
                new_row['open'] = last_valid_data['close']  # 开盘价=昨日收盘
            else:
                new_row['open'] = future_features['close'].iloc[-1]  # 开盘价=前日预测收盘
            
            # 价格波动范围（±3%）
            price_change = np.random.uniform(-0.03, 0.03)
            new_row['close'] = new_row['open'] * (1 + price_change)
            new_row['high'] = max(new_row['open'], new_row['close']) * 1.015
            new_row['low'] = min(new_row['open'], new_row['close']) * 0.985
            
            # 更新成交量（基于历史平均值的随机波动）
            volume_change = np.random.uniform(-0.2, 0.2)
            new_row['volume'] = last_valid_data['volume'] * (1 + volume_change)
            
            # 更新技术指标
            # 1. 价格动量指标
            new_row['momentum_1d'] = new_row['close'] / last_valid_data['close'] - 1
            new_row['momentum_5d'] = new_row['close'] / last_valid_data['close'] - 1  # 简化处理
            new_row['momentum_20d'] = new_row['close'] / last_valid_data['close'] - 1  # 简化处理
            
            # 2. 趋势指标
            new_row['MA20'] = (last_valid_data['MA20'] * 19 + new_row['close']) / 20
            new_row['SMA20'] = new_row['MA20']
            
            # 3. 波动率指标
            new_row['20dSTD'] = last_valid_data['20dSTD'] * 0.95  # 假设波动率略微下降
            new_row['Upper_Band'] = new_row['MA20'] + (new_row['20dSTD'] * 2)
            new_row['Lower_Band'] = new_row['MA20'] - (new_row['20dSTD'] * 2)
            
            # 4. 成交量指标
            new_row['Volume_MA5'] = (last_valid_data['Volume_MA5'] * 4 + new_row['volume']) / 5
            new_row['Volume_MA20'] = (last_valid_data['Volume_MA20'] * 19 + new_row['volume']) / 20
            new_row['volume_ratio'] = new_row['volume'] / new_row['Volume_MA20']
            
            # 5. 组合指标
            new_row['volatility_ratio'] = new_row['20dSTD'] / last_valid_data['20dSTD']
            
            # 6. 时间特征
            new_row['day_of_week'] = date.dayofweek
            new_row['month'] = date.month
            
            # 添加到未来特征DataFrame
            future_features = pd.concat([future_features, new_row.to_frame().T])
            last_valid_data = new_row.copy()
        
        return future_features

    @staticmethod
    def _add_price_volatility(predictions: np.ndarray, base_price: float, volatility: float = 0.02) -> np.ndarray:
        """
        为预测值添加随机波动
        """
        return np.array([base_price * (1 + np.random.uniform(-volatility, volatility)) 
                        for _ in predictions])

    @staticmethod
    def _sanitize_float(value: float) -> float:
        """
        处理特殊浮点数值，确保返回JSON兼容的值
        """
        try:
            # 如果输入是字典或列表，返回0.0
            if isinstance(value, (dict, list)):
                return 0.0
                
            # 转换为float类型
            value = float(value)
            
            # 处理 NaN 和无穷大
            if pd.isna(value) or np.isnan(value) or np.isinf(value):
                return 0.0
                
            # 确保返回值在合理范围内
            if abs(value) < 1e-10:
                return 0.0001 if value >= 0 else -0.0001
            elif abs(value) > 1e10:  # 防止数值过大
                return 1e10 if value > 0 else -1e10
                
            return value
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _sanitize_dict(data: Dict) -> Dict:
        """
        递归处理字典中的所有浮点数值
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = AIMarketSentimentService._sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [AIMarketSentimentService._sanitize_dict(item) if isinstance(item, dict)
                             else AIMarketSentimentService._sanitize_float(item) if isinstance(item, (float, np.float32, np.float64))
                             else item for item in value]
            elif isinstance(value, (float, np.float32, np.float64)):
                result[key] = AIMarketSentimentService._sanitize_float(value)
            elif isinstance(value, np.ndarray):
                result[key] = AIMarketSentimentService._sanitize_float(value.tolist())
            else:
                result[key] = value
        return result

    @staticmethod
    async def get_market_prediction(symbol: str = "sh000001") -> Dict:
        try:
            print(f"\n开始获取市场预测数据，股票代码: {symbol}")
            
            # 尝试从缓存获取数据
            cached_data = AIMarketSentimentService._get_cache('market_prediction', symbol)
            if cached_data is not None:
                print("从缓存获取数据成功")
                return cached_data

            try:
                # 获取日线数据
                print(f"开始获取股票数据...")
                if symbol.startswith(('sh', 'sz')):
                    df = ak.stock_zh_index_daily_em(symbol=symbol)
                else:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                
                print(f"获取到的数据形状: {df.shape}")
                print(f"数据列名: {df.columns.tolist()}")
                
                # 添加数据验证
                if df is None or df.empty:
                    print("错误: 获取到的数据为空")
                    return {
                        'error': '无法获取股票数据',
                        'historical': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'future': {
                            'predictions': [],
                            'dates': [],
                            'confidence': 0
                        },
                        'minute_5': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'minute_15': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'minute_60': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'prediction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                
                if len(df) < 30:
                    print(f"错误: 历史数据不足30天，当前数据量: {len(df)}")
                    return {
                        'error': '历史数据不足30天，无法进行准确预测',
                        'historical': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'future': {
                            'predictions': [],
                            'dates': [],
                            'confidence': 0
                        },
                        'minute_5': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'minute_15': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'minute_60': {
                            'predictions': [],
                            'actual_prices': [],
                            'dates': [],
                            'accuracy': 0
                        },
                        'prediction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                # 确保日期列是datetime类型
                print("处理日期列...")
                date_column = None
                for col in ['日期', 'date', 'trade_date']:
                    if col in df.columns:
                        date_column = col
                        break

                if date_column:
                    df[date_column] = pd.to_datetime(df[date_column])
                    df.set_index(date_column, inplace=True)
                else:
                    if not isinstance(df.index, pd.DatetimeIndex):
                        df.index = pd.to_datetime(df.index)

                # 定义中文列名到英文列名的映射
                column_mapping = {
                    '股票代码': 'symbol',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'change_percent',
                    '涨跌额': 'change_amount',
                    '换手率': 'turnover_rate'
                }
                
                # 重命名列
                df = df.rename(columns=column_mapping)
                print(f"重命名后的列名: {df.columns.tolist()}")

                # 只保留最近6个月的数据
                print("过滤数据到最近12个月...")
                months_ago = pd.Timestamp.now() - pd.DateOffset(months=12)
                df = df[df.index >= months_ago]
                print(f"过滤后的数据量: {len(df)}")

                # 计算技术指标
                print("开始计算技术指标...")
                features, target = AIMarketSentimentService._prepare_features(df)
                print(f"技术指标计算完成，特征数量: {len(features.columns)}")
                
                # 准备训练数据
                print("准备训练数据...")
                X = features.values
                y = target.values
                print(f"特征数据形状: {X.shape}")
                print(f"目标数据形状: {y.shape}")
                
                # 使用全部数据训练模型
                print("开始数据标准化...")
                feature_scaler = MinMaxScaler(feature_range=(0, 1))
                target_scaler = MinMaxScaler(feature_range=(0, 1))
                X_scaled = feature_scaler.fit_transform(X)
                y_scaled = target_scaler.fit_transform(y.reshape(-1, 1))
                X_reshaped = np.reshape(X_scaled, (X_scaled.shape[0], 1, X_scaled.shape[1]))
                print(f"标准化后的数据形状: {X_reshaped.shape}")

                # 构建和训练模型
                print("开始构建和训练模型...")
                model, feature_scaler, target_scaler, X_test_reshaped, predictions_rescaled = AIMarketSentimentService._build_lstm_model(X_scaled, y, X_scaled, y)
                print("模型训练完成")

                # 修改预测价格的计算方式
                historical_predictions = model.predict(X_reshaped)
                historical_predictions = target_scaler.inverse_transform(historical_predictions)
                historical_predictions = historical_predictions.flatten()
                
                print("\n验证历史预测数据:")
                print(f"预测值范围: {min(historical_predictions)} - {max(historical_predictions)}")
                print(f"预测值均值: {np.mean(historical_predictions)}")
                print(f"预测值标准差: {np.std(historical_predictions)}")
                
                # 使用前一交易日的价格作为基准进行预测
                historical_price_predictions = []
                for i in range(1, len(df)):  # 从第二个点开始
                    prev_price = float(df['close'].iloc[i-1])
                    pred_return = historical_predictions[i-1]  # 使用对应的预测收益率

                    # 计算预测价格
                    pred_price = prev_price * (1 + pred_return)
                    historical_price_predictions.append(pred_price)
                
                # 转换为numpy数组
                historical_price_predictions = np.array(historical_price_predictions)
                
                print("\n验证转换后的价格:")
                print(f"价格范围: {min(historical_price_predictions)} - {max(historical_price_predictions)}")
                print(f"价格均值: {np.mean(historical_price_predictions)}")
                print(f"价格标准差: {np.std(historical_price_predictions)}")
                print(f"实际价格范围: {min(df['close'].values[1:])} - {max(df['close'].values[1:])}")
                
                # 计算历史预测准确率（使用实际价格从第二个点开始）
                historical_accuracy = AIMarketSentimentService._calculate_prediction_accuracy(
                    historical_price_predictions,
                    df['close'].values[1:]  # 使用从第二个点开始的实际价格
                )
                print(f"\n历史预测准确率: {historical_accuracy}")

                # 创建未来时间窗口
                print("生成未来预测...")
                last_date = df.index[-1]
                future_dates = pd.date_range(
                    start=last_date + pd.Timedelta(days=1),
                    periods=5,
                    freq='B'  # 工作日频率
                )
                
                # 验证未来日期
                current_date = datetime.now()
                future_dates = future_dates[future_dates <= current_date + pd.Timedelta(days=5)]
                
                # 确保日期格式正确
                future_dates = [d.strftime('%Y-%m-%d') for d in future_dates]
                historical_dates = [d.strftime('%Y-%m-%d') for d in df.index]
                
                print(f"未来预测日期: {future_dates}")

                # 准备未来特征数据
                print("准备未来特征数据...")
                last_features = features.iloc[-1]
                future_features = AIMarketSentimentService._generate_future_features(
                    last_features,
                    pd.Timestamp(last_date),
                    pd.DatetimeIndex(future_dates)
                )

                print(f"未来特征数据形状: {future_features.shape}")
                print(f"未来特征列名: {future_features.columns.tolist()}")

                # 准备未来预测数据
                print("开始预测未来价格...")
                future_X = future_features.values

                # 验证特征维度
                print(f"历史特征数量: {feature_scaler.n_features_in_}")
                print(f"未来特征数量: {future_X.shape[1]}")

                if future_X.shape[1] != feature_scaler.n_features_in_:
                    print(f"警告: 特征维度不匹配，进行修复")
                    # 自动修复：如果特征数量不一致，填充缺失特征
                    diff = feature_scaler.n_features_in_ - future_X.shape[1]
                    if diff > 0:
                        print(f"警告: 未来数据缺少{diff}个特征，使用中位数填充")
                        fill_values = np.median(X, axis=0)[-diff:]
                        future_X = np.hstack([future_X, np.tile(fill_values, (future_X.shape[0], 1))])
                    else:
                        print(f"警告: 未来数据多出{-diff}个特征，截取前{feature_scaler.n_features_in_}个")
                        future_X = future_X[:, :feature_scaler.n_features_in_]

                future_X_scaled = feature_scaler.transform(future_X)
                future_X_reshaped = np.reshape(future_X_scaled, (future_X_scaled.shape[0], 1, future_X_scaled.shape[1]))

                # 预测未来价格
                future_predictions = model.predict(future_X_reshaped)
                # 反标准化未来预测结果
                future_predictions = target_scaler.inverse_transform(future_predictions)
                future_predictions = future_predictions.flatten()

                # 使用新的转换函数，确保价格不为0
                last_price = float(df['close'].iloc[-1])
                if last_price < 0.0001:
                    last_price = 0.0001
                future_price_predictions = AIMarketSentimentService._convert_returns_to_prices(
                    future_predictions,
                    last_price
                )

                print(f"预测完成，预测结果数量: {len(future_predictions)}")

                # 获取分时数据预测
                print("获取分时数据预测...")
                minute_5_data = await AIMarketSentimentService._get_minute_prediction(symbol, '5')
                minute_15_data = await AIMarketSentimentService._get_minute_prediction(symbol, '15')
                minute_60_data = await AIMarketSentimentService._get_minute_prediction(symbol, '60')
                print("分时数据预测完成")

                # 计算日线预测的置信度指标
                recent_predictions = model.predict(X_reshaped[-100:])
                recent_predictions = target_scaler.inverse_transform(recent_predictions)
                recent_actual = y[-100:]
                confidence_metrics = AIMarketSentimentService._calculate_prediction_accuracy(
                    recent_predictions.flatten(),
                    recent_actual
                )

                # 准备返回数据
                result = {
                    'historical': {
                        'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in historical_price_predictions],
                        'actual_prices': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in df['close'].values.tolist()],
                        'dates': historical_dates,
                        'accuracy': float(historical_accuracy.get('accuracy', 0.0))
                    },
                    'future': {
                        'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in future_price_predictions],
                        'dates': future_dates,
                        'confidence': {
                            'accuracy': float(historical_accuracy.get('accuracy', 0.0)),
                            'direction_accuracy': float(historical_accuracy.get('direction_accuracy', 0.0)),
                            'rmse': float(historical_accuracy.get('rmse', 0.0)),
                            'mae': float(historical_accuracy.get('mae', 0.0)),
                            'r2': float(historical_accuracy.get('r2', 0.0)),
                            'relative_error': float(historical_accuracy.get('relative_error', 0.0)),
                            'bias': float(historical_accuracy.get('bias', 0.0))
                        }
                    },
                    'minute_5': {
                        'historical': {
                            'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in minute_5_data.get('predictions', [])],
                            'actual_prices': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in minute_5_data.get('actual_prices', [])],
                            'dates': minute_5_data.get('dates', []),
                            'accuracy': float(minute_5_data.get('accuracy', 0.0))
                        },
                        'future': {
                            'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                                            minute_5_data.get('future_predictions', [])],
                            'dates': minute_5_data.get('future_dates'),
                            'confidence': {
                                'accuracy': float(minute_5_data.get('confidence').get('accuracy', 0.0)),
                                'direction_accuracy': float(minute_5_data.get('confidence').get('direction_accuracy', 0.0)),
                                'rmse': float(minute_5_data.get('confidence').get('rmse', 0.0)),
                                'mae': float(minute_5_data.get('confidence').get('mae', 0.0)),
                                'r2': float(minute_5_data.get('confidence').get('r2', 0.0)),
                                'relative_error': float(minute_5_data.get('confidence').get('relative_error', 0.0)),
                                'bias': float(minute_5_data.get('confidence').get('bias', 0.0))
                            }
                        },
                    },
                    # {
                    #     'dates': df.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                    #     'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                    #                     historical_price_predictions],
                    #     'actual_prices': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                    #                       df['close'].values],
                    #     'future_dates': [date.strftime('%Y-%m-%d %H:%M:%S') for date in future_dates],
                    #     'future_predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                    #                            future_predictions],
                    #     'confidence': {
                    #         'accuracy': float(confidence.get('accuracy', 0.0)),
                    #         'direction_accuracy': float(confidence.get('direction_accuracy', 0.0)),
                    #         'rmse': float(confidence.get('rmse', 0.0)),
                    #         'mae': float(confidence.get('mae', 0.0)),
                    #         'r2': float(confidence.get('r2', 0.0)),
                    #         'relative_error': float(confidence.get('relative_error', 0.0)),
                    #         'bias': float(confidence.get('bias', 0.0))
                    #     }

                    'minute_15': {
                        'historical': {
                            'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                                            minute_15_data.get('predictions', [])],
                            'actual_prices': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                                              minute_15_data.get('actual_prices', [])],
                            'dates': minute_15_data.get('dates', []),
                            'accuracy': float(minute_15_data.get('accuracy', 0.0))
                        },
                        'future': {
                            'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                                            minute_15_data.get('future_predictions')],
                            'dates': minute_15_data.get('future_dates'),
                            'confidence': {
                                'accuracy': float(minute_15_data.get('confidence').get('accuracy', 0.0)),
                                'direction_accuracy': float(
                                    minute_15_data.get('confidence').get('direction_accuracy', 0.0)),
                                'rmse': float(minute_15_data.get('confidence').get('rmse', 0.0)),
                                'mae': float(minute_15_data.get('confidence').get('mae', 0.0)),
                                'r2': float(minute_15_data.get('confidence').get('r2', 0.0)),
                                'relative_error': float(minute_15_data.get('confidence').get('relative_error', 0.0)),
                                'bias': float(minute_15_data.get('confidence').get('bias', 0.0))
                            }
                        },
                    },
                    'minute_60': {
                        'historical': {
                            'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                                            minute_60_data.get('predictions', [])],
                            'actual_prices': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                                              minute_60_data.get('actual_prices', [])],
                            'dates': minute_60_data.get('dates', []),
                            'accuracy': float(minute_60_data.get('accuracy', 0.0))
                        },
                        'future': {
                            'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in
                                            minute_60_data.get('future_predictions')],
                            'dates': minute_60_data.get('future_dates'),
                            'confidence': {
                                'accuracy': float(minute_60_data.get('confidence').get('accuracy', 0.0)),
                                'direction_accuracy': float(
                                    minute_60_data.get('confidence').get('direction_accuracy', 0.0)),
                                'rmse': float(minute_60_data.get('confidence').get('rmse', 0.0)),
                                'mae': float(minute_60_data.get('confidence').get('mae', 0.0)),
                                'r2': float(minute_60_data.get('confidence').get('r2', 0.0)),
                                'relative_error': float(minute_60_data.get('confidence').get('relative_error', 0.0)),
                                'bias': float(minute_60_data.get('confidence').get('bias', 0.0))
                            }
                        },
                    },
                    'prediction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                # 确保所有数据都是可序列化的
                result = AIMarketSentimentService._sanitize_dict(result)

                # 缓存结果
                AIMarketSentimentService._set_cache('market_prediction', result, symbol)
                return result

            except Exception as e:
                print(f"处理数据时出错: {str(e)}")
                print(f"错误类型: {type(e).__name__}")
                import traceback
                print(f"错误堆栈: {traceback.format_exc()}")
                return {
                    'error': f'处理数据时出错: {str(e)}',
                    'historical': {
                        'predictions': [0.0001],
                        'actual_prices': [0.0001],
                        'dates': [],
                        'accuracy': 0.0
                    },
                    'future': {
                        'predictions': [0.0001],
                        'dates': [],
                        'confidence': {
                            'accuracy': 0.0,
                            'direction_accuracy': 0.0,
                            'rmse': 0.0,
                            'mae': 0.0,
                            'r2': 0.0,
                            'relative_error': 0.0,
                            'bias': 0.0
                        }
                    },
                    'minute_5': {
                        'predictions': [0.0001],
                        'actual_prices': [0.0001],
                        'dates': [],
                        'accuracy': 0.0
                    },
                    'minute_15': {
                        'predictions': [0.0001],
                        'actual_prices': [0.0001],
                        'dates': [],
                        'accuracy': 0.0
                    },
                    'minute_60': {
                        'predictions': [0.0001],
                        'actual_prices': [0.0001],
                        'dates': [],
                        'accuracy': 0.0
                    },
                    'prediction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

        except Exception as e:
            print(f"获取市场预测数据失败: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                'error': f'获取市场预测数据失败: {str(e)}',
                'historical': {
                    'predictions': [0.0001],
                    'actual_prices': [0.0001],
                    'dates': [],
                    'accuracy': 0.0
                },
                'future': {
                    'predictions': [0.0001],
                    'dates': [],
                    'confidence': {
                        'accuracy': 0.0,
                        'direction_accuracy': 0.0,
                        'rmse': 0.0,
                        'mae': 0.0,
                        'r2': 0.0,
                        'relative_error': 0.0,
                        'bias': 0.0
                    }
                },
                'minute_5': {
                    'predictions': [0.0001],
                    'actual_prices': [0.0001],
                    'dates': [],
                    'accuracy': 0.0
                },
                'minute_15': {
                    'predictions': [0.0001],
                    'actual_prices': [0.0001],
                    'dates': [],
                    'accuracy': 0.0
                },
                'minute_60': {
                    'predictions': [0.0001],
                    'actual_prices': [0.0001],
                    'dates': [],
                    'accuracy': 0.0
                },
                'prediction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    @staticmethod
    async def _get_minute_prediction(symbol: str, period: str) -> Dict:
        try:
            print(f"\n{'='*50}")
            print(f"开始获取{period}分钟预测数据，股票代码: {symbol}")
            print(f"{'='*50}")

            # 检查是否为交易时间
            is_trading_time = AIMarketSentimentService._is_trading_time()
            print(f"当前是否为交易时间: {is_trading_time}")

            # 获取交易时间范围
            start_date, end_date = AIMarketSentimentService._get_trading_time_range(period)
            print(f"获取数据的时间范围: {start_date} 到 {end_date}")

            # 获取分时数据
            try:
                print(f"\n尝试获取{period}分钟数据...")
                if symbol.startswith(('sh', 'sz')):
                    print(f"检测到指数代码: {symbol}")
                    df = ak.stock_zh_a_hist_min_em(
                        symbol=symbol[2:],
                        start_date=start_date,
                        end_date=end_date,
                        period=period,
                        adjust=""
                    )
                else:
                    print(f"检测到股票代码: {symbol}")
                    df = ak.stock_zh_a_hist_min_em(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        period=period,
                        adjust=""
                    )

                if df is None or df.empty:
                    print(f"警告: 获取{period}分钟数据返回空")
                    return {
                        'historical': {
                            'dates': [],
                            'predictions': [],
                            'actual_prices': []
                        },
                        'future': {
                            'dates': [],
                            'predictions': [],
                            'confidence': {
                                'accuracy': 0,
                                'direction_accuracy': 0,
                                'rmse': 0,
                                'mae': 0,
                                'r2': 0,
                                'relative_error': 0,
                                'bias': 0
                            }
                        }
                    }

                print(f"成功获取到{period}分钟数据:")
                print(f"数据形状: {df.shape}")
                print(f"列名: {df.columns.tolist()}")
                print(f"数据示例:\n{df.head()}")

            except Exception as e:
                print(f"获取{period}分钟数据失败:")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                return {
                    'historical': {
                        'dates': [],
                        'predictions': [],
                        'actual_prices': []
                    },
                    'future': {
                        'dates': [],
                        'predictions': [],
                        'confidence': {
                            'accuracy': 0,
                            'direction_accuracy': 0,
                            'rmse': 0,
                            'mae': 0,
                            'r2': 0,
                            'relative_error': 0,
                            'bias': 0
                        }
                    }
                }

            # 重命名列以匹配我们的处理逻辑
            print("\n开始处理数据列名...")
            column_mapping = {
                '时间': 'time',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '均价': 'avg_price',
                '涨跌幅': 'change_percent',
                '涨跌额': 'change_amount',
                '振幅': 'amplitude',
                '换手率': 'turnover_rate'
            }
            df = df.rename(columns=column_mapping)

            # 确保时间列是datetime类型
            try:
                print("\n处理时间列...")
                df['time'] = pd.to_datetime(df['time'])
                df.set_index('time', inplace=True)
                print(f"时间列处理完成，数据量: {len(df)}")
                print(f"时间范围: {df.index.min()} 到 {df.index.max()}")
            except Exception as e:
                print(f"处理{period}分钟时间数据失败:")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                return {
                    'historical': {
                        'dates': [],
                        'predictions': [],
                        'actual_prices': []
                    },
                    'future': {
                        'dates': [],
                        'predictions': [],
                        'confidence': {
                            'accuracy': 0,
                            'direction_accuracy': 0,
                            'rmse': 0,
                            'mae': 0,
                            'r2': 0,
                            'relative_error': 0,
                            'bias': 0
                        }
                    }
                }

            # 检查数据中是否存在空值
            print("\n检查数据空值...")
            null_counts = df.isnull().sum()
            print(f"各列空值数量:\n{null_counts}")
            if df.isnull().any().any():
                print("发现空值，进行填充...")
                df = df.fillna(method='ffill').fillna(method='bfill')
                print("空值填充完成")

            # 计算技术指标
            try:
                print("\n开始计算技术指标...")
                features, target = AIMarketSentimentService._prepare_features(df)
                print(f"技术指标计算完成:")
                print(f"特征数量: {len(features.columns)}")
                print(f"特征列名: {features.columns.tolist()}")
            except Exception as e:
                print(f"计算{period}分钟技术指标失败:")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                return {
                    'historical': {
                        'dates': [],
                        'predictions': [],
                        'actual_prices': []
                    },
                    'future': {
                        'dates': [],
                        'predictions': [],
                        'confidence': {
                            'accuracy': 0,
                            'direction_accuracy': 0,
                            'rmse': 0,
                            'mae': 0,
                            'r2': 0,
                            'relative_error': 0,
                            'bias': 0
                        }
                    }
                }

            # 准备训练数据
            print("\n准备训练数据...")
            X = features.values
            y = target.values
            print(f"特征数据形状: {X.shape}")
            print(f"目标数据形状: {y.shape}")

            if len(X) < 30:  # 确保有足够的数据进行训练
                print(f"错误: {period}分钟数据量不足，至少需要30个数据点")
                return {
                    'historical': {
                        'dates': [],
                        'predictions': [],
                        'actual_prices': []
                    },
                    'future': {
                        'dates': [],
                        'predictions': [],
                        'confidence': {
                            'accuracy': 0,
                            'direction_accuracy': 0,
                            'rmse': 0,
                            'mae': 0,
                            'r2': 0,
                            'relative_error': 0,
                            'bias': 0
                        }
                    }
                }

            # 使用全部数据训练模型
            print("\n开始数据标准化...")
            feature_scaler = MinMaxScaler(feature_range=(0, 1))
            target_scaler = MinMaxScaler(feature_range=(0, 1))
            X_scaled = feature_scaler.fit_transform(X)
            y_scaled = target_scaler.fit_transform(y.reshape(-1, 1))
            X_reshaped = np.reshape(X_scaled, (X_scaled.shape[0], 1, X_scaled.shape[1]))
            print(f"标准化后的数据形状: {X_reshaped.shape}")

            # 构建和训练模型
            print("\n开始构建和训练模型...")
            model, feature_scaler, target_scaler, X_test_reshaped, predictions_rescaled = AIMarketSentimentService._build_lstm_model(X_scaled, y, X_scaled, y)
            print("模型训练完成")

            # 修改预测价格的计算方式
            historical_predictions = model.predict(X_reshaped)
            historical_predictions = target_scaler.inverse_transform(historical_predictions)
            historical_predictions = historical_predictions.flatten()

            print("\n验证历史预测数据:")
            print(f"预测值范围: {min(historical_predictions)} - {max(historical_predictions)}")
            print(f"预测值均值: {np.mean(historical_predictions)}")
            print(f"预测值标准差: {np.std(historical_predictions)}")

            # 使用前一交易日的价格作为基准进行预测
            historical_price_predictions = []
            for i in range(1, len(df)):  # 从第二个点开始
                prev_price = float(df['close'].iloc[i - 1])
                pred_return = historical_predictions[i - 1]  # 使用对应的预测收益率

                # 计算预测价格
                pred_price = prev_price * (1 + pred_return)
                historical_price_predictions.append(pred_price)
            confidence = AIMarketSentimentService._calculate_prediction_accuracy(
                np.array(historical_price_predictions),
                df['close'].values[1:] )

            # 创建未来时间窗口
            print("\n开始生成未来预测...")
            # 生成未来时间点
            last_time = df.index[-1]
            print(f"最后一个数据时间点: {last_time}")

            # 计算当前时间
            current_time = pd.Timestamp.now()
            print(f"当前时间: {current_time}")

            # 根据不同的时间周期设置不同的预测数量
            if period == '5':
                future_periods = 48  # 预测未来10个5分钟（2小时）
                future_dates = pd.date_range(
                    start=last_time + pd.Timedelta(minutes=5),
                    periods=future_periods,
                    freq='5min'
                )
            elif period == '15':
                future_periods = 32  # 预测未来10个15分钟（4小时）
                future_dates = pd.date_range(
                    start=last_time + pd.Timedelta(minutes=15),
                    periods=future_periods,
                    freq='15min'
                )
            else:  # 60分钟
                future_periods = 16  # 预测未来8个60分钟（8小时）
                future_dates = pd.date_range(
                    start=last_time + pd.Timedelta(hours=1),
                    periods=future_periods,
                    freq='1H'
                )

            print(f"生成的原始未来时间点数量: {len(future_dates)}")
            if len(future_dates) > 0:
                print(f"原始未来时间范围: {future_dates[0]} 到 {future_dates[-1]}")

            # 调整未来时间点，确保都在交易时间内且不重复
            future_dates = AIMarketSentimentService._adjust_future_dates(future_dates,period)

            print(f"调整后的未来时间点数量: {len(future_dates)}")
            if len(future_dates) > 0:
                print(f"调整后的未来时间范围: {future_dates[0]} 到 {future_dates[-1]}")

                # 打印每个时间点的详细信息
                print("\n未来时间点详细信息:")
                for i, date in enumerate(future_dates):
                    print(f"时间点 {i+1}: {date}, 是否在交易时间: {AIMarketSentimentService._is_valid_trading_time(date)}")

            # 准备未来特征数据
            print("\n准备未来特征数据...")
            last_features = features.iloc[-1]
            future_features = AIMarketSentimentService._generate_future_features(
                    last_features,
                    pd.Timestamp(last_time),
                    pd.DatetimeIndex(future_dates)
                )

            print(f"未来特征数据形状: {future_features.shape}")
            print(f"未来特征列名: {future_features.columns.tolist()}")

            # 确保特征顺序一致
            future_features = future_features[features.columns]

            # 准备未来预测数据
            print("\n开始预测未来价格...")
            future_X = future_features.values

            # 验证特征维度
            print(f"历史特征数量: {feature_scaler.n_features_in_}")
            print(f"未来特征数量: {future_X.shape[1]}")
            if future_X.shape[1] != feature_scaler.n_features_in_:
                print(f"警告: 特征维度不匹配，进行修复")
                # 自动修复：如果特征数量不一致，填充缺失特征
                diff = feature_scaler.n_features_in_ - future_X.shape[1]
                if diff > 0:
                    print(f"警告: 未来数据缺少{diff}个特征，使用中位数填充")
                    fill_values = np.median(X, axis=0)[-diff:]
                    future_X = np.hstack([future_X, np.tile(fill_values, (future_X.shape[0], 1))])
                else:
                    print(f"警告: 未来数据多出{-diff}个特征，截取前{feature_scaler.n_features_in_}个")
                    future_X = future_X[:, :feature_scaler.n_features_in_]
            future_X_scaled = feature_scaler.transform(future_X)
            future_X_reshaped = np.reshape(future_X_scaled, (future_X_scaled.shape[0], 1, future_X_scaled.shape[1]))

            # 预测未来价格
            future_predictions = model.predict(future_X_reshaped)
            print('future_predictions:',future_predictions)
            future_predictions = target_scaler.inverse_transform(future_predictions)
            future_predictions = future_predictions.flatten()

            # 使用新的转换函数，确保价格不为0
            last_price = float(df['close'].iloc[len(df) - 1])

            if last_price < 0.0001:
                last_price = 0.0001

            # 在预测未来价格之前添加历史收益率分析
            mean_return = 0
            std_return = 0
            min_return = 0
            max_return = 0
            try:
                # 计算历史实际收益率的统计指标
                actual_returns = df['close'].pct_change().dropna().values
                if len(actual_returns) > 0:
                    mean_return = np.mean(actual_returns)
                    std_return = np.std(actual_returns)
                    min_return = np.min(actual_returns)
                    max_return = np.max(actual_returns)

                    # 使用1%和99%分位数作为安全边界
                    q1 = np.percentile(actual_returns, 1)
                    q99 = np.percentile(actual_returns, 99)
                else:
                    # 默认安全边界（当历史数据不足时）
                    mean_return, std_return, min_return, max_return = 0, 0.01, -0.05, 0.05
                    q1, q99 = -0.03, 0.03

                print(f"历史收益率统计: 均值={mean_return:.6f}, 标准差={std_return:.6f}")
                print(f"历史收益率范围: [{min_return:.6f}, {max_return:.6f}]")
                print(f"使用安全边界: [{q1:.6f}, {q99:.6f}]")

            except Exception as e:
                print(f"计算历史收益率统计失败: {str(e)}")
                # 设置保守的默认边界
                q1, q99 = -0.03, 0.03

            # 修改未来价格预测部分
            future_price_predictions = []
            previous_price = last_price
            cumulative_factor = 1.0  # 累积变化因子
            smoothing_factor = 0.7  # 平滑因子（新预测值权重）

            for i, prediction in enumerate(future_predictions):
                try:
                    # 应用安全边界限制
                    clipped_prediction = np.clip(prediction, q1, q99)

                    # 计算平均变化率平滑后的收益率
                    if i == 0:
                        smoothed_return = clipped_prediction
                    else:
                        # 结合历史平均变化率进行平滑
                        smoothed_return = (smoothing_factor * clipped_prediction +
                                           (1 - smoothing_factor) * mean_return)

                    # 计算理论价格变化
                    theoretical_price = previous_price * (1 + smoothed_return)

                    # 应用边界保护（防止价格突破历史波动范围）
                    price_change = theoretical_price - previous_price
                    max_allowed_change = previous_price * max_return
                    min_allowed_change = previous_price * min_return

                    bounded_change = np.clip(
                        price_change,
                        min_allowed_change,
                        max_allowed_change
                    )

                    predicted_price = previous_price + bounded_change

                    # 绝对价格保护（防止负价格）
                    predicted_price = max(predicted_price, 0.0001)

                    # 更新追踪变量
                    future_price_predictions.append(predicted_price)
                    previous_price = predicted_price
                    cumulative_factor *= (1 + smoothed_return)

                    print(f"预测步 {i + 1}: 原始收益={prediction:.6f}, "
                          f"截断后={clipped_prediction:.6f}, "
                          f"平滑后={smoothed_return:.6f}, "
                          f"最终价格={predicted_price:.6f}")

                except Exception as e:
                    print(f"第 {i + 1} 步预测异常: {str(e)}")
                    # 异常时使用保守预测
                    predicted_price = previous_price * (1 + mean_return)
                    future_price_predictions.append(max(predicted_price, 0.0001))
                    previous_price = predicted_price

            future_price_predictions = np.array(future_price_predictions)
            print('last_price', future_price_predictions, future_predictions, last_price)


            print(f"预测完成，预测结果数量: {len(future_predictions)}")
            # 计算预测置信度
            print("\n计算预测置信度...")
            recent_predictions = model.predict(X_reshaped[-100:])
            recent_predictions = target_scaler.inverse_transform(recent_predictions)
            recent_actual = y[-100:]
            # confidence = AIMarketSentimentService._calculate_prediction_accuracy(recent_predictions.flatten(), recent_actual)
            # print(f"预测置信度: {confidence}%")

            print(f"\n{period}分钟预测完成，生成预测数据")
            print(f"{'='*50}\n")
            
            # 准备返回数据
            result = {
                'dates': df.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                'predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in historical_price_predictions],
                'actual_prices': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in df['close'].values],
                'future_dates': [date.strftime('%Y-%m-%d %H:%M:%S') for date in future_dates],
                'future_predictions': [max(AIMarketSentimentService._sanitize_float(x), 0.0001) for x in future_price_predictions],
                'confidence': {
                    'accuracy': float(confidence.get('accuracy', 0.0)),
                    'direction_accuracy': float(confidence.get('direction_accuracy', 0.0)),
                    'rmse': float(confidence.get('rmse', 0.0)),
                    'mae': float(confidence.get('mae', 0.0)),
                    'r2': float(confidence.get('r2', 0.0)),
                    'relative_error': float(confidence.get('relative_error', 0.0)),
                    'bias': float(confidence.get('bias', 0.0))
                }
            }
            
            return result


        except Exception as e:
            print(f"\n获取{period}分钟预测数据失败:")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print(f"{'='*50}\n")
            return {
                'dates': [],
                'predictions': [],
                'actual_prices': [],
                'future_dates': [],
                'future_predictions': [],
                'confidence': {
                    'accuracy': 0,
                    'direction_accuracy': 0,
                    'rmse': 0,
                    'mae': 0,
                    'r2': 0,
                    'relative_error': 0,
                    'bias': 0
                }
            }

    @staticmethod
    async def get_news_analysis(symbol: str = "sh000001") -> Dict:
        """
        获取新闻分析数据（按发布时间降序排序）
        """
        # 尝试从缓存获取数据
        cached_data = AIMarketSentimentService._get_cache('news_analysis', symbol)
        if cached_data is not None:
            return cached_data

        try:
            # 获取财经新闻数据
            news_df = ak.stock_news_em()

            if news_df.empty:
                return {
                    'news_list': [],
                    'sentiment_distribution': {
                        'positive': 0,
                        'neutral': 0,
                        'negative': 0
                    },
                    'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            # ==== 按发布时间排序 ====
            # 1. 确保存在时间列
            if '发布时间' not in news_df.columns:
                # 尝试用其他可能的时间列
                if 'publish_time' in news_df.columns:
                    news_df.rename(columns={'publish_time': '发布时间'}, inplace=True)
                else:
                    news_df['发布时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 2. 转换为时间对象并降序排序（最新在前）
            try:
                # 保存原始字符串时间
                news_df['发布时间_str'] = news_df['发布时间'].astype(str)
                # 转换为datetime对象
                news_df['发布时间'] = pd.to_datetime(news_df['发布时间'], errors='coerce')
                # 降序排序（最新在前）
                sorted_df = news_df.sort_values('发布时间', ascending=False)
                news_df = sorted_df
            except Exception as time_err:
                print(f"时间排序处理异常，使用原始顺序: {str(time_err)}")
            # ===== 结束排序处理 =====

            # 情感分析关键词
            positive_keywords = ['上涨', '利好', '增长', '突破', '创新高']
            negative_keywords = ['下跌', '利空', '下滑', '跌破', '创新低']

            sentiment_counts = {
                'positive': 0,
                'neutral': 0,
                'negative': 0
            }

            news_list = []
            for _, row in news_df.iterrows():
                # 获取标题、内容和发布时间
                title = row.get('新闻标题', row.get('title', ''))
                content = row.get('新闻内容', row.get('content', ''))

                # 处理发布时间
                publish_time = row.get('发布时间_str', '')
                if not publish_time:
                    publish_time = row.get('发布时间', '')
                    if isinstance(publish_time, pd.Timestamp):
                        publish_time = publish_time.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        publish_time = str(publish_time)

                # 情感分析
                sentiment = 'neutral'
                for keyword in positive_keywords:
                    if keyword in title or keyword in content:
                        sentiment = 'positive'
                        break

                if sentiment == 'neutral':
                    for keyword in negative_keywords:
                        if keyword in title or keyword in content:
                            sentiment = 'negative'
                            break

                sentiment_counts[sentiment] += 1

                news_list.append({
                    'title': title,
                    'content': content,
                    'sentiment': sentiment,
                    'publish_time': publish_time
                })

            result = {
                'news_list': news_list,  # 已按时间排序
                'sentiment_distribution': sentiment_counts,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 设置缓存
            AIMarketSentimentService._set_cache('news_analysis', result, symbol)
            return result

        except Exception as e:
            import traceback
            print(f"获取新闻分析数据失败: {str(e)}")
            traceback.print_exc()
            return {
                'news_list': [],
                'sentiment_distribution': {
                    'positive': 0,
                    'neutral': 0,
                    'negative': 0
                },
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    @staticmethod
    async def get_technical_indicators(symbol: str = "sh000001") -> Dict:
        """
        获取技术指标分析数据
        """
        print(f"\n{'='*50}")
        print(f"开始获取技术指标分析数据，股票代码: {symbol}")
        print(f"{'='*50}")
        
        # 尝试从缓存获取数据
        cached_data = AIMarketSentimentService._get_cache('technical_indicators', symbol)
        if cached_data is not None:
            print("从缓存获取数据成功")
            return cached_data

        try:
            print("\n1. 获取股票数据...")
            # 获取股票数据
            if symbol.startswith(('sh', 'sz')):
                print(f"获取指数数据: {symbol}")
                df = ak.stock_zh_index_daily_em(symbol=symbol)
            else:
                print(f"获取股票数据: {symbol}")
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            
            print(f"获取到的数据形状: {df.shape}")
            print(f"数据列名: {df.columns.tolist()}")
            
            if df.empty:
                print("错误: 获取到的数据为空")
                return {
                    'indicators': {},
                    'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            print("\n2. 计算技术指标...")
            # 计算技术指标
            features, target = AIMarketSentimentService._prepare_features(df)
            
            print(f"特征数据形状: {features.shape}")
            print(f"特征列名: {features.columns.tolist()}")
            
            # 获取最新特征数据和目标值（收盘价）
            latest_features = features.iloc[-1]
            latest_close = target.iloc[-1]  # 使用目标值中的收盘价
            
            print("\n3. 计算各个技术指标...")
            
            # RSI指标
            print("\n3.1 RSI指标计算:")
            rsi_value = latest_features['RSI']
            print(f"RSI值: {rsi_value:.2f}")
            rsi_signal = 'neutral'
            if rsi_value > 70:
                rsi_signal = 'overbought'
                print("RSI信号: 超买")
            elif rsi_value < 30:
                rsi_signal = 'oversold'
                print("RSI信号: 超卖")
            else:
                print("RSI信号: 中性")
            
            # MACD指标
            print("\n3.2 MACD指标计算:")
            macd_value = latest_features['MACD']
            signal_line = latest_features['Signal_Line']
            macd_hist = latest_features['MACD_Hist']
            print(f"MACD值: {macd_value:.2f}")
            print(f"信号线: {signal_line:.2f}")
            print(f"MACD柱状图: {macd_hist:.2f}")
            
            # ATR指标
            print("\n3.3 ATR指标计算:")
            atr_value = latest_features['ATR']
            print(f"ATR值: {atr_value:.2f}")
            
            # 布林带指标
            print("\n3.4 布林带指标计算:")
            upper_band = latest_features['Upper_Band']
            middle_band = latest_features['MA20']
            lower_band = latest_features['Lower_Band']
            print(f"上轨: {upper_band:.2f}")
            print(f"中轨: {middle_band:.2f}")
            print(f"下轨: {lower_band:.2f}")
            
            bb_signal = 'neutral'
            if latest_close > upper_band:
                bb_signal = 'overbought'
                print("布林带信号: 超买")
            elif latest_close < lower_band:
                bb_signal = 'oversold'
                print("布林带信号: 超卖")
            else:
                print("布林带信号: 中性")
            
            # 成交量比率
            print("\n3.5 成交量比率计算:")
            volume_ratio = latest_features['volume_ratio']
            print(f"成交量比率: {volume_ratio:.2f}")
            
            # 价格动量
            print("\n3.6 价格动量计算:")
            momentum = latest_features['momentum_1d']
            print(f"价格动量: {momentum:.2f}")
            
            # 移动平均线信号
            print("\n3.7 移动平均线信号计算:")
            ma_signal = 'neutral'
            if latest_close > middle_band:
                ma_signal = 'bullish'
                print("移动平均线信号: 看涨")
            elif latest_close < middle_band:
                ma_signal = 'bearish'
                print("移动平均线信号: 看跌")
            else:
                print("移动平均线信号: 中性")
            
            result = {
                'indicators': {
                    'close_price': round(latest_close, 2),
                    'RSI': {
                        'value': round(rsi_value, 2),
                        'signal': rsi_signal
                    },
                    'MACD': {
                        'value': round(macd_value, 2),
                        'signal_line': round(signal_line, 2),
                        'histogram': round(macd_hist, 2),
                        'signal': 'neutral'  # 根据MACD值判断信号
                    },
                    'ATR': {
                        'value': round(atr_value, 2)
                    },
                    'Bollinger_Bands': {
                        'upper': round(upper_band, 2),
                        'middle': round(middle_band, 2),
                        'lower': round(lower_band, 2),
                        'signal': bb_signal
                    },
                    'Volume_Ratio': {
                        'value': round(volume_ratio, 2)
                    },
                    'Momentum': {
                        'value': round(momentum, 2)
                    },
                    'Moving_Averages': {
                        'SMA20': round(middle_band, 2),
                        'signal': ma_signal
                    }
                },
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print("\n4. 生成最终结果:")
            print(f"结果包含的指标数量: {len(result['indicators'])}")
            
            # 设置缓存
            print("\n5. 设置缓存...")
            AIMarketSentimentService._set_cache('technical_indicators', result, symbol)
            print("缓存设置完成：",result)
            
            return result
            
        except Exception as e:
            print(f"\n错误: 获取技术指标分析数据失败:")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                'indicators': {},
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    @staticmethod
    async def get_mean_reversion_analysis(symbol: str = "sh000001") -> Dict:
        """
        获取均值回归分析数据
        """
        # 尝试从缓存获取数据
        cached_data = AIMarketSentimentService._get_cache('mean_reversion', symbol)
        if cached_data is not None:
            return cached_data

        try:
            # 获取股票数据
            if symbol.startswith(('sh', 'sz')):
                df = ak.stock_zh_index_daily_em(symbol=symbol)
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="")
            
            if df.empty:
                return {
                    'mean_reversion_signals': [],
                    'trading_opportunities': [],
                    'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            # 确保日期列是datetime类型
            print("处理日期列...")
            date_column = None
            for col in ['日期', 'date', 'trade_date']:
                if col in df.columns:
                    date_column = col
                    break

            if date_column:
                df[date_column] = pd.to_datetime(df[date_column])
                df.set_index(date_column, inplace=True)
            else:
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
            # 列名映射
            column_mapping = {
                '日期': 'date',
                '股票代码': 'symbol',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude_pct',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amt',
                '换手率': 'turnover_rate'
            }
            
            # 重命名列
            df = df.rename(columns=column_mapping)
            
            # 确保必要的列存在
            if 'close' not in df.columns:
                raise ValueError("无法找到收盘价数据列")
            # 只保留最近6个月的数据
            print("过滤数据到最近12个月...")
            months_ago = pd.Timestamp.now() - pd.DateOffset(months=36)
            df = df[df.index >= months_ago]
            print(f"过滤后的数据量: {len(df)}")
            # 确保日期列是datetime类型
            date_column = None
            for col in ['日期', 'date', 'trade_date']:
                if col in df.columns:
                    date_column = col
                    break

            if date_column:
                df[date_column] = pd.to_datetime(df[date_column])
                df.set_index(date_column, inplace=True)
            else:
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)

            # 计算技术指标
            features, target = AIMarketSentimentService._prepare_features(df)
            
            # 准备训练数据
            X = features.values
            y = target.values
            
            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]
            
            # 获取测试集的日期
            test_dates = df.index[split:].strftime('%Y-%m-%d').tolist()
            # print(f"测试集日期: {test_dates}")
            
            # 构建和训练模型
            model, feature_scaler, target_scaler, X_test_reshaped, predictions_rescaled = AIMarketSentimentService._build_lstm_model(X_train, y_train, X_test, y_test)
            
            # 进行预测
            predictions = model.predict(X_test_reshaped)
            predictions_rescaled = predictions.flatten()
            
            # 应用均值回归策略
            trading_decisions = AIMarketSentimentService._mean_reversion_strategy(predictions_rescaled, y_test)
            
            # 生成交易信号
            mean_reversion_signals = []
            trading_opportunities = []
            # print('trading_decisions:',len(trading_decisions),len(df),int(0.8 * len(X)))
            for i in range(len(trading_decisions)):
                if trading_decisions[i] != 0:
                    prev_price = float(df['close'].iloc[ int(0.8 * len(X)) + i - 1])
                    # print('prev_price=',prev_price)
                    date_str = test_dates[i]
                    current_price =prev_price * (1 + float(target_scaler.inverse_transform([[y_test[i]]])[0][0])/100)
                    predicted_price =prev_price * ( 1 + float(target_scaler.inverse_transform([[predictions_rescaled[i]]])[0][0])/100)

                    signal = {
                        'date': date_str,
                        'price': current_price,
                        'predicted_price': predicted_price,
                        'signal': 'buy' if trading_decisions[i] == 1 else 'sell',
                        'deviation': float(predicted_price - current_price)
                    }
                    mean_reversion_signals.append(signal)
                    
                    # 检查后续价格变动
                    if i < len(trading_decisions) - 1:
                        next_price = float(df['close'].iloc[int(0.8 * len(X)) + i]) * (1+float(target_scaler.inverse_transform([[y_test[i+1]]])[0][0])/100)
                        price_change = next_price - current_price
                        buy_price = current_price
                        sell_price = next_price

                        if signal['signal'] == 'sell':
                            buy_price = next_price
                            sell_price = current_price

                        if (trading_decisions[i] == 1 and price_change > 0) or \
                           (trading_decisions[i] == -1 and price_change < 0):
                            trading_opportunities.append({
                                'date': date_str,
                                'signal': signal['signal'],
                                'buy_price': float(buy_price),
                                'sell_price': float(sell_price),
                                'expected_return': float(abs(price_change)),
                                'return_rate': float(abs(price_change) / current_price * 100)
                            })
            
            result = {
                'mean_reversion_signals': [{
                    'date': signal['date'],
                    'price': AIMarketSentimentService._sanitize_float(signal['price']),
                    'predicted_price': AIMarketSentimentService._sanitize_float(signal['predicted_price']),
                    'signal': signal['signal'],
                    'deviation': AIMarketSentimentService._sanitize_float(signal['deviation'])
                } for signal in mean_reversion_signals],
                'trading_opportunities': [{
                    'date': opp['date'],
                    'signal': opp['signal'],
                    'buy_price': AIMarketSentimentService._sanitize_float(opp['buy_price']),
                    'sell_price': AIMarketSentimentService._sanitize_float(opp['sell_price']),
                    'expected_return': AIMarketSentimentService._sanitize_float(opp['expected_return']),
                    'return_rate': AIMarketSentimentService._sanitize_float(opp['return_rate'])
                } for opp in trading_opportunities],
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 设置缓存
            AIMarketSentimentService._set_cache('mean_reversion', result, symbol)
            
            return result
            
        except Exception as e:
            print(f"获取均值回归分析数据失败: {str(e)}")
            return {
                'mean_reversion_signals': [],
                'trading_opportunities': [],
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            } 

    @staticmethod
    def _convert_returns_to_prices(returns: np.ndarray, initial_price: float) -> np.ndarray:
        """
        将收益率转换为价格序列，使用动态波动率控制
        """
        prices = np.zeros_like(returns)
        current_price = initial_price
        
        # 计算历史波动率
        historical_volatility = np.std(returns) if len(returns) > 0 else 0.02

        for i, ret in enumerate(returns):
            # 确保收益率不为0
            if abs(ret) < 1e-10:
                ret = 0.0001 if ret >= 0 else -0.0001
                
            # 使用动态波动率控制
            max_volatility = historical_volatility * 3  # 允许3倍历史波动率
            if abs(ret) > max_volatility:
                ret = max_volatility if ret > 0 else -max_volatility

            # 计算下一个价格
            next_price = current_price * (1 + ret)
            
            # 确保价格为正
            if next_price <= 0:
                next_price = current_price * 0.999  # 允许小幅下跌
                
            prices[i] = next_price
            current_price = next_price
            
        return prices

    @staticmethod
    def _sanitize_float(value: float) -> float:
        """
        处理特殊浮点数值，确保返回JSON兼容的值
        """
        try:
            # 如果输入是字典或列表，返回0.0
            if isinstance(value, (dict, list)):
                return 0.0
                
            # 转换为float类型
            value = float(value)
            
            # 处理 NaN 和无穷大
            if pd.isna(value) or np.isnan(value) or np.isinf(value):
                return 0.0
                
            # 确保返回值在合理范围内
            if abs(value) < 1e-10:
                return 0.0001 if value >= 0 else -0.0001
            elif abs(value) > 1e10:  # 防止数值过大
                return 1e10 if value > 0 else -1e10
                
            return value
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _sanitize_dict(data: Dict) -> Dict:
        """
        递归处理字典中的所有浮点数值
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = AIMarketSentimentService._sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [AIMarketSentimentService._sanitize_dict(item) if isinstance(item, dict)
                             else AIMarketSentimentService._sanitize_float(item) if isinstance(item, (float, np.float32, np.float64))
                             else item for item in value]
            elif isinstance(value, (float, np.float32, np.float64)):
                result[key] = AIMarketSentimentService._sanitize_float(value)
            elif isinstance(value, np.ndarray):
                result[key] = AIMarketSentimentService._sanitize_float(value.tolist())
            else:
                result[key] = value
        return result

    @staticmethod
    def _is_trading_time() -> bool:
        """
        检查当前是否为交易时间
        """
        now = datetime.now()
        current_time = now.strftime('%H:%M:%S')
        
        # 检查是否为工作日
        if now.weekday() >= 5:  # 周六日
            return False
            
        # 检查是否在交易时间段内
        morning_start = '09:30:00'
        morning_end = '11:30:00'
        afternoon_start = '13:00:00'
        afternoon_end = '15:00:00'
        
        return (morning_start <= current_time <= morning_end) or (afternoon_start <= current_time <= afternoon_end)

    @staticmethod
    def _get_last_trading_day() -> datetime:
        """
        获取最近一个交易日
        """
        now = datetime.now()
        current_time = now.strftime('%H:%M:%S')
        
        # 如果是交易时间，返回当前日期
        if AIMarketSentimentService._is_trading_time():
            return now
            
        # 如果是非交易时间，获取最近一个交易日
        if now.weekday() >= 5:  # 周六日
            days_to_subtract = now.weekday() - 4  # 周五是4
            return now - timedelta(days=days_to_subtract)
        elif current_time < '09:30:00':  # 早盘前
            return now - timedelta(days=1)
        else:  # 收盘后
            return now

    @staticmethod
    def _get_trading_time_range(period: str = '60', include_future: bool = False) -> Tuple[str, str]:
        """
        获取交易时间范围
        参数:
            period: 时间周期，可选值：'5'(5分钟), '15'(15分钟), '60'(60分钟)
            include_future: 是否包含未来时间范围
        返回: (开始时间, 结束时间) 格式为 'YYYY-MM-DD HH:MM:SS'
        说明：
        1. 60分钟数据：
           - 历史数据：最近120个交易日（约6个月）
           - 未来预测：未来10个交易日
        2. 15分钟数据：
           - 历史数据：最近90个交易日（约4.5个月）
           - 未来预测：未来5个交易日
        3. 5分钟数据：
           - 历史数据：最近30个交易日（约1.5个月）
           - 未来预测：未来2个交易日
        """
        now = datetime.now()
        last_trading_day = AIMarketSentimentService._get_last_trading_day()

        # 根据时间周期设置历史数据范围
        period_configs = {
            '60': {'history_days': 120, 'future_days': 5},
            '15': {'history_days': 30, 'future_days': 3},
            '5': {'history_days': 5, 'future_days': 1}
        }

        config = period_configs.get(period, period_configs[str(period)])  # 默认使用15分钟配置

        # 计算历史数据开始时间
        start_date = (now - timedelta(days=config['history_days'])).strftime('%Y-%m-%d')

        # 计算结束时间
        if include_future:
            # 计算未来时间范围
            future_days = config['future_days']
            end_date = (now + timedelta(days=future_days)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            # 使用当前时间或最近交易日收盘时间
            if not AIMarketSentimentService._is_trading_time():
                end_date = last_trading_day.strftime('%Y-%m-%d 15:00:00')
            else:
                end_date = now.strftime('%Y-%m-%d %H:%M:%S')

        # 确保时间范围的合理性
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')

        if end_dt < start_dt:
            raise ValueError(f"结束时间 {end_date} 早于开始时间 {start_date}")

        # 检查时间范围是否过大
        max_days = config['history_days'] + (config['future_days'] if include_future else 0)
        if (end_dt - start_dt).days > max_days:
            print(f"警告: 时间范围超过建议的最大天数 {max_days} 天")

        return start_date, end_date

    @staticmethod
    def _get_optimal_period(symbol: str) -> str:
        """
        根据历史数据选择最优的时间周期
        """
        periods = ['5', '15', '60']
        accuracies = {}
        
        for period in periods:
            try:
                # 获取历史数据
                start_date, end_date = AIMarketSentimentService._get_trading_time_range()
                df = ak.stock_zh_a_hist_min_em(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    period=period,
                    adjust=""
                )
                
                if df is not None and not df.empty:
                    # 重命名列以匹配我们的处理逻辑
                    column_mapping = {
                        '时间': 'time',
                        '开盘': 'open',
                        '最高': 'high',
                        '最低': 'low',
                        '收盘': 'close',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '均价': 'avg_price',
                        '涨跌幅': 'change_percent',
                        '涨跌额': 'change_amount',
                        '振幅': 'amplitude',
                        '换手率': 'turnover_rate'
                    }
                    df = df.rename(columns=column_mapping)
                    
                    # 计算技术指标
                    features, target = AIMarketSentimentService._prepare_features(df)
                    
                    # 使用简单的移动平均作为预测准确度的指标
                    df['MA5'] = df['close'].rolling(window=5).mean()
                    df['MA10'] = df['close'].rolling(window=10).mean()
                    
                    # 计算预测准确度
                    accuracy = 1 - abs(df['MA5'] - df['MA10']).mean() / df['close'].mean()
                    accuracies[period] = accuracy
            except Exception as e:
                print(f"计算{period}分钟周期准确度时出错: {str(e)}")
                continue
        
        # 返回准确度最高的周期
        if accuracies:
            return max(accuracies.items(), key=lambda x: x[1])[0]
        return '15'  # 默认返回15分钟周期

    @staticmethod
    def _is_valid_trading_time(date: pd.Timestamp) -> bool:
        """
        检查给定日期是否为交易时间
        参数:
            date: 要检查的时间戳
        返回:
            bool: 是否为有效的交易时间
        """
        # 检查是否为工作日
        if date.weekday() >= 5:  # 周六日
            return False

        # 获取时间部分
        time_str = date.strftime('%H:%M:%S')

        # 检查是否在交易时段内
        morning_start = '09:30:00'
        morning_end = '11:30:00'
        afternoon_start = '13:00:00'
        afternoon_end = '15:00:00'

        return (morning_start <= time_str <= morning_end) or (afternoon_start <= time_str <= afternoon_end)

    @staticmethod
    def _adjust_trading_time(date: pd.Timestamp) -> pd.Timestamp:
        """
        调整超出交易时间的时间点到下一个交易日的对应时间段
        参数:
            date: 需要调整的时间戳
        返回:
            调整后的时间戳
        """
        time_str = date.strftime('%H:%M:%S')
        morning_start = '09:30:00'
        morning_end = '11:30:00'
        afternoon_start = '13:00:00'
        afternoon_end = '15:00:00'

        # 如果时间在交易时间内，直接返回
        if ((morning_start <= time_str <= morning_end) or
            (afternoon_start <= time_str <= afternoon_end)):
            return date

        # 计算下一个交易日
        next_day = date + pd.Timedelta(days=1)
        while next_day.weekday() >= 5:  # 跳过周末
            next_day = next_day + pd.Timedelta(days=1)

        # 根据原时间点所在的时间段，转换到下一个交易日的对应时间段
        if time_str < morning_start:  # 早盘前
            return next_day.replace(hour=9, minute=30, second=0)
        elif morning_end < time_str < afternoon_start:  # 午休时间
            return next_day.replace(hour=13, minute=0, second=0)
        else:  # 收盘后
            return next_day.replace(hour=9, minute=30, second=0)

    @staticmethod
    def _adjust_future_dates(future_dates: List[pd.Timestamp],period:int) -> List[pd.Timestamp]:
        """
        调整未来预测时间点，确保所有时间点都在交易时间内且不重复
        参数:
            future_dates: 原始未来时间点列表
        返回:
            调整后的时间点列表
        """
        print("\n开始调整未来时间点...")
        print(f"原始时间点数量: {len(future_dates)}")

        adjusted_dates = []
        used_times = set()  # 用于记录已使用的时间点

        for date in future_dates:
            print(f"\n处理时间点: {date}")

            # 调整时间点
            adjusted_date = AIMarketSentimentService._adjust_trading_time(date)
            print(f"调整后的时间点: {adjusted_date}")

            # 如果调整后的时间点已存在，继续向后调整
            attempts = 0
            max_attempts = 50  # 最大尝试次数

            while adjusted_date in used_times and attempts < max_attempts:
                if adjusted_date.hour == 11 and adjusted_date.minute == 30:
                    adjusted_date  = adjusted_date + pd.Timedelta(minutes=(90 - int(period)))
                adjusted_date = adjusted_date + pd.Timedelta(minutes=int(period))
                # 如果超出当天交易时间，调整到下一个交易日
                if not AIMarketSentimentService._is_valid_trading_time(adjusted_date):
                    print(f"超出交易时间，调整到下一个交易日")
                    adjusted_date = AIMarketSentimentService._adjust_trading_time(adjusted_date)
                attempts += 1

            if attempts >= max_attempts:
                print(f"警告: 达到最大尝试次数，跳过此时间点")
                continue

            if AIMarketSentimentService._is_valid_trading_time(adjusted_date):
                print(f"添加有效时间点: {adjusted_date}")
                used_times.add(adjusted_date)
                adjusted_dates.append(adjusted_date)
            else:
                print(f"警告: 调整后的时间点 {adjusted_date} 不在交易时间内，跳过")

        print(f"\n调整完成，最终时间点数量: {len(adjusted_dates)}")
        return adjusted_dates