# -*- coding: utf-8 -*-
"""
LSTM股票预测服务 - 优化版 v7
支持训练因子配置和训练参数配置

v7 核心改进：
1. 解决过拟合：L2正则化 + 更高Dropout + 简化架构
2. 方向感知损失：真正学习价格变化趋势
3. 优化特征工程：聚焦核心特征 + 新增关键特征
4. 增强训练策略：更严格的测试 + 更保守的Early Stopping
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
import warnings
warnings.filterwarnings('ignore')

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, LSTM, Dropout, Bidirectional
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.regularizers import l2
    from tensorflow.keras import backend as K
except ImportError:
    from keras.models import Sequential
    from keras.layers import Dense, LSTM, Dropout, Bidirectional
    from keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from keras.optimizers import Adam
    from keras.regularizers import l2
    from keras import backend as K


class LSTMPredictionService:
    """LSTM股票预测服务"""
    
    def __init__(self):
        self.model = None
        self.scalers = {}
        self.close_scaler = None
        self.open_scaler = None  # 添加开盘价标准化器
        self.best_lookback = None
        self.feature_columns = []
        self.train_config = {}
        
    @staticmethod
    def directional_mse_loss(alpha=0.5):
        """
        v7新增：方向感知损失函数
        不仅预测绝对价格，更要预测变化趋势
        
        Args:
            alpha: 方向损失权重，0-1之间（默认0.5表示同等权重）
        """
        def loss(y_true, y_pred):
            # 1. 基础MSE损失
            mse_loss = K.mean(K.square(y_true - y_pred))
            
            # 2. 方向损失（关键改进）
            # 计算batch内相邻样本的变化方向
            y_true_diff = y_true[1:] - y_true[:-1]  # 真实变化
            y_pred_diff = y_pred[1:] - y_pred[:-1]  # 预测变化
            
            # 直接惩罚方向差异
            direction_penalty = K.mean(K.square(y_true_diff - y_pred_diff))
            
            # 组合损失
            total_loss = (1 - alpha) * mse_loss + alpha * direction_penalty
            return total_loss
        
        return loss
    
    @staticmethod
    def calculate_direction_accuracy(y_true, y_pred):
        """
        v7新增：计算方向准确率
        
        Args:
            y_true: 真实值数组
            y_pred: 预测值数组
            
        Returns:
            方向准确率（百分比）
        """
        if len(y_true) < 2:
            return 0.0
        
        # 计算真实变化方向
        true_direction = np.sign(np.diff(y_true.flatten()))
        # 计算预测变化方向
        pred_direction = np.sign(np.diff(y_pred.flatten()))
        
        # 计算方向一致的比例
        correct = np.sum(true_direction == pred_direction)
        total = len(true_direction)
        
        return (correct / total) * 100 if total > 0 else 0.0
        
    def add_date_features(self, df):
        """添加日期相关特征"""
        df = df.copy()
        df['day_of_week'] = df.index.dayofweek
        df['month'] = df.index.month
        df['quarter'] = df.index.quarter
        df['day_of_year'] = df.index.dayofyear
        df['is_month_start'] = (df.index.day <= 5).astype(int)
        df['is_month_end'] = (df.index.day >= 25).astype(int)
        df['is_monday'] = (df.index.dayofweek == 0).astype(int)
        df['is_friday'] = (df.index.dayofweek == 4).astype(int)
        return df
    
    def count_consecutive_days(self, series):
        """计算连续上涨/下跌天数"""
        result = []
        count = 0
        for i in range(len(series)):
            if i == 0:
                result.append(0)
            else:
                diff = series.iloc[i] - series.iloc[i-1]
                if diff > 0:
                    count = max(0, count) + 1
                elif diff < 0:
                    count = min(0, count) - 1
                else:
                    count = 0
                result.append(count)
        return pd.Series(result, index=series.index)
    
    def prepare_features(self, df, selected_features=None):
        """
        准备特征数据
        
        Args:
            df: 原始DataFrame，需包含 date, close, open, high, low, volume 列
            selected_features: 选择的特征列表，None表示使用全部特征
            
        Returns:
            处理后的DataFrame
        """
        # 确保日期索引
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        else:
            df.index = pd.to_datetime(df.index)
        
        # 基础特征映射
        feature_map = {
            'close': 'close',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'volume': 'volume'
        }
        
        # 初始化数据
        data = pd.DataFrame(index=df.index)
        
        # 添加基础特征
        basic_features = ['close', 'open', 'high', 'low', 'volume']
        for feature in basic_features:
            if selected_features is None or feature in selected_features:
                if feature in df.columns:
                    data[feature] = df[feature]
        
        # 添加日期特征
        date_features_map = {
            'day_of_week': 'day_of_week',
            'month': 'month',
            'quarter': 'quarter',
            'day_of_year': 'day_of_year',
            'is_month_start': 'is_month_start',
            'is_month_end': 'is_month_end',
            'is_monday': 'is_monday',
            'is_friday': 'is_friday'
        }
        
        if selected_features is None or any(f in selected_features for f in date_features_map.keys()):
            date_df = self.add_date_features(pd.DataFrame(index=df.index))
            for feature_key, col_name in date_features_map.items():
                if selected_features is None or feature_key in selected_features:
                    data[col_name] = date_df[col_name]
        
        # 计算技术指标
        if 'close' in data.columns:
            # 移动平均线
            if selected_features is None or 'ma5' in selected_features:
                data['ma5'] = data['close'].rolling(window=5).mean()
            if selected_features is None or 'ma10' in selected_features:
                data['ma10'] = data['close'].rolling(window=10).mean()
            if selected_features is None or 'ma20' in selected_features:
                data['ma20'] = data['close'].rolling(window=20).mean()
            
            # 波动率
            if selected_features is None or 'volatility' in selected_features:
                data['volatility'] = data['close'].rolling(window=10).std()
            
            # RSI
            if selected_features is None or 'rsi' in selected_features:
                delta = data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                data['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            if selected_features is None or 'macd' in selected_features or 'macd_signal' in selected_features:
                exp1 = data['close'].ewm(span=12, adjust=False).mean()
                exp2 = data['close'].ewm(span=26, adjust=False).mean()
                if selected_features is None or 'macd' in selected_features:
                    data['macd'] = exp1 - exp2
                if selected_features is None or 'macd_signal' in selected_features:
                    data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean() if 'macd' in data.columns else (exp1 - exp2).ewm(span=9, adjust=False).mean()
            
            # 布林带
            if selected_features is None or any(f in selected_features for f in ['bb_middle', 'bb_upper', 'bb_lower']):
                bb_middle = data['close'].rolling(window=20).mean()
                bb_std = data['close'].rolling(window=20).std()
                if selected_features is None or 'bb_middle' in selected_features:
                    data['bb_middle'] = bb_middle
                if selected_features is None or 'bb_upper' in selected_features:
                    data['bb_upper'] = bb_middle + (bb_std * 2)
                if selected_features is None or 'bb_lower' in selected_features:
                    data['bb_lower'] = bb_middle - (bb_std * 2)
            
            # 价格动量
            if selected_features is None or 'momentum' in selected_features:
                data['momentum'] = data['close'].diff(5)
            
            # 价格变化率
            if selected_features is None or 'price_change' in selected_features:
                data['price_change'] = data['close'].pct_change()
            if selected_features is None or 'price_change_5d' in selected_features:
                data['price_change_5d'] = data['close'].pct_change(5)
        
        # 成交量变化率
        if 'volume' in data.columns:
            if selected_features is None or 'volume_change' in selected_features:
                data['volume_change'] = data['volume'].pct_change()
        
        # 市场强度指标
        if 'close' in data.columns:
            if selected_features is None or 'price_accel' in selected_features:
                data['price_accel'] = data['close'].diff().diff()
            
            if selected_features is None or 'consecutive_days' in selected_features:
                data['consecutive_days'] = self.count_consecutive_days(data['close'])
        
        if 'high' in data.columns and 'low' in data.columns:
            if selected_features is None or 'high_low_ratio' in selected_features:
                data['high_low_ratio'] = data['high'] / data['low']
        
        if 'close' in data.columns and 'high' in data.columns:
            if selected_features is None or 'close_high_ratio' in selected_features:
                data['close_high_ratio'] = data['close'] / data['high']
        
        if 'volume' in data.columns and 'close' in data.columns:
            if selected_features is None or 'volume_price' in selected_features:
                data['volume_price'] = data['volume'] * data['close']
            
            if selected_features is None or 'volume_ratio' in selected_features:
                volume_ma5 = data['volume'].rolling(window=5).mean()
                data['volume_ratio'] = data['volume'] / volume_ma5
        
        # v7新增：关键特征
        if 'close' in data.columns:
            # 3日动量（更短期）
            if selected_features is None or 'momentum_3d' in selected_features:
                data['momentum_3d'] = data['close'].diff(3)
            
            # 价格加速度（3日）
            if selected_features is None or 'price_accel_3d' in selected_features:
                if 'momentum_3d' in data.columns or (selected_features is None):
                    momentum_3d = data.get('momentum_3d', data['close'].diff(3))
                    data['price_accel_3d'] = momentum_3d.diff(3)
            
            # MA60（长期趋势）
            if selected_features is None or 'ma60' in selected_features:
                data['ma60'] = data['close'].rolling(window=60).mean()
            
            # 均线交叉信号
            if 'ma5' in data.columns and 'ma10' in data.columns:
                if selected_features is None or 'ma5_ma10_cross' in selected_features:
                    data['ma5_ma10_cross'] = (data['ma5'] - data['ma10']) / data['ma10']
            
            # 长期趋势位置
            if selected_features is None or 'close_ma60_ratio' in selected_features:
                ma60 = data.get('ma60', data['close'].rolling(window=60).mean())
                data['close_ma60_ratio'] = data['close'] / ma60
        
        # 删除NaN值
        data = data.dropna()
        
        self.feature_columns = data.columns.tolist()
        return data
    
    def create_sample_weights(self, n_samples, decay_rate=0.995):
        """创建样本权重，让近期数据权重更大"""
        weights = np.array([decay_rate ** (n_samples - i - 1) for i in range(n_samples)])
        weights = weights / weights.sum() * n_samples
        return weights
    
    def create_sequences(self, data, lookback):
        """创建时间序列数据 - 同时预测开盘价和收盘价"""
        x, y = [], []
        for i in range(lookback, len(data)):
            x.append(data[i - lookback:i])
            # 预测开盘价(第1列)和收盘价(第0列)
            y.append([data[i, 1], data[i, 0]])  # [open, close]
        return np.array(x), np.array(y)
    
    def build_model(self, lookback_days, n_features, learning_rate=0.0005, l2_reg=0.001, 
                    dropout_rate=0.4, use_directional_loss=True, direction_alpha=0.5):
        """
        构建LSTM模型 v7 - 双输出（开盘价+收盘价）
        
        v7架构改进：
        - 减少模型复杂度（80->60节点）
        - 增加L2正则化（防止过拟合）
        - 提高Dropout率（0.3 -> 0.4）
        - 简化架构（去掉LSTM第三层）
        - 使用方向感知损失函数
        """
        model = Sequential([
            # 第一层：双向LSTM(80) + L2正则化
            Bidirectional(
                LSTM(80, return_sequences=True,
                     kernel_regularizer=l2(l2_reg),
                     recurrent_regularizer=l2(l2_reg)),
                input_shape=(lookback_days, n_features)
            ),
            Dropout(dropout_rate),  # v7: 0.4（原0.3）
            
            # 第二层：双向LSTM(60) + L2正则化
            Bidirectional(
                LSTM(60, return_sequences=False,
                     kernel_regularizer=l2(l2_reg),
                     recurrent_regularizer=l2(l2_reg))
            ),
            Dropout(dropout_rate),  # v7: 0.4（原0.3）
            
            # 全连接层
            Dense(30, activation='relu', kernel_regularizer=l2(l2_reg)),
            Dropout(0.3),
            Dense(2)  # 输出2个值：开盘价和收盘价
        ])
        
        optimizer = Adam(learning_rate=learning_rate)
        
        # 选择损失函数
        if use_directional_loss:
            loss_fn = self.directional_mse_loss(alpha=direction_alpha)
            print(f"  使用方向感知损失函数（alpha={direction_alpha}）")
        else:
            loss_fn = 'mse'
            print("  使用标准MSE损失函数")
        
        model.compile(optimizer=optimizer, loss=loss_fn, metrics=['mae'])
        
        return model
    
    def evaluate_model(self, y_true, y_pred):
        """
        评估模型性能 v7
        新增：方向准确率、综合评分
        """
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mae = mean_absolute_error(y_true, y_pred)
        mape = mean_absolute_percentage_error(y_true, y_pred) * 100
        r2 = r2_score(y_true, y_pred)
        
        # v7新增：方向准确率
        direction_accuracy = self.calculate_direction_accuracy(y_true, y_pred)
        
        return {
            'rmse': float(rmse),
            'mae': float(mae),
            'mape': float(mape),
            'r2_score': float(r2),
            'direction_accuracy': float(direction_accuracy)  # v7新增
        }
    
    def train(self, df, config):
        """
        训练LSTM模型
        
        Args:
            df: 原始数据DataFrame
            config: 训练配置字典
                - lookback_options: 回顾窗口选项列表
                - epochs: 训练轮次
                - batch_size: 批次大小
                - learning_rate: 学习率
                - test_size: 测试集比例
                - validation_split: 验证集比例
                - use_sample_weights: 是否使用样本权重
                - sample_weight_decay: 样本权重衰减率
                - selected_features: 选择的特征列表
                
        Returns:
            训练结果字典
        """
        self.train_config = config
        
        # 准备特征
        data = self.prepare_features(df, config.get('selected_features'))
        
        # 数据标准化（先划分再标准化，避免数据泄露）
        training_data_len = int(len(data) * (1 - config.get('test_size', 0.1)))
        train_data_raw = data.iloc[:training_data_len].copy()
        test_data_raw = data.iloc[training_data_len:].copy()
        
        # 分别标准化每个特征
        self.scalers = {}
        train_scaled = np.zeros(train_data_raw.shape)
        test_scaled = np.zeros(test_data_raw.shape)
        
        for i, col in enumerate(data.columns):
            scaler = MinMaxScaler(feature_range=(0, 1))
            train_scaled[:, i] = scaler.fit_transform(train_data_raw[[col]]).flatten()
            test_scaled[:, i] = scaler.transform(test_data_raw[[col]]).flatten()
            self.scalers[col] = scaler
        
        # 保存收盘价和开盘价的scaler
        self.close_scaler = self.scalers[data.columns[0]]  # close
        self.open_scaler = self.scalers[data.columns[1]]   # open
        
        # 合并数据
        scaled_data = np.vstack([train_scaled, test_scaled])
        
        # 尝试不同的lookback_days
        best_r2 = -np.inf
        best_lookback = None
        best_model = None
        best_metrics = None
        
        lookback_options = config.get('lookback_options', [30, 60])
        
        for lookback_days in lookback_options:
            print(f"\n正在测试 lookback_days = {lookback_days}")
            
            # 准备数据
            train_data = scaled_data[:training_data_len]
            test_data = scaled_data[training_data_len - lookback_days:]
            
            # 创建序列
            x_train, y_train = self.create_sequences(train_data, lookback_days)
            x_test, y_test_scaled = self.create_sequences(test_data, lookback_days)
            
            # 反归一化测试集真实值（双输出：开盘价和收盘价）
            y_test_open = self.open_scaler.inverse_transform(y_test_scaled[:, 0].reshape(-1, 1)).flatten()
            y_test_close = self.close_scaler.inverse_transform(y_test_scaled[:, 1].reshape(-1, 1)).flatten()
            y_test = np.column_stack([y_test_open, y_test_close])
            
            # 创建样本权重
            sample_weights = None
            if config.get('use_sample_weights', False):
                sample_weights = self.create_sample_weights(
                    len(x_train), 
                    decay_rate=config.get('sample_weight_decay', 0.9985)
                )
            
            # 构建模型（v7参数）
            model = self.build_model(
                lookback_days, 
                data.shape[1],
                learning_rate=config.get('learning_rate', 0.0005),  # v7: 降低学习率
                l2_reg=config.get('l2_reg', 0.001),  # v7: L2正则化
                dropout_rate=config.get('dropout_rate', 0.4),  # v7: 更高dropout
                use_directional_loss=config.get('use_directional_loss', True),  # v7: 方向感知损失
                direction_alpha=config.get('direction_alpha', 0.5)  # v7: 方向损失权重
            )
            
            # 回调函数（v7：更保守的Early Stopping）
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=25,  # v7: 从30降至25，更早停止
                    restore_best_weights=True,
                    verbose=0
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=12,  # v7: 从15降至12
                    min_lr=0.00001,
                    verbose=0
                )
            ]
            
            # 划分训练集和验证集
            x_train_split, x_val, y_train_split, y_val = train_test_split(
                x_train, y_train,
                test_size=config.get('validation_split', 0.2),
                random_state=42,
                shuffle=False
            )
            
            # 如果使用样本权重，也要相应划分
            train_weights_split = None
            if sample_weights is not None:
                train_weights_split = sample_weights[:len(x_train_split)]
            
            # 训练模型
            print(f'开始训练...')
            history = model.fit(
                x_train_split, y_train_split,
                batch_size=config.get('batch_size', 16),
                epochs=config.get('epochs', 200),
                validation_data=(x_val, y_val),
                callbacks=callbacks,
                sample_weight=train_weights_split,
                verbose=0
            )
            
            # 预测（双输出）
            predictions_scaled = model.predict(x_test, verbose=0)
            pred_open = self.open_scaler.inverse_transform(predictions_scaled[:, 0].reshape(-1, 1)).flatten()
            pred_close = self.close_scaler.inverse_transform(predictions_scaled[:, 1].reshape(-1, 1)).flatten()
            predictions = np.column_stack([pred_open, pred_close])
            
            # 评估
            metrics = self.evaluate_model(y_test, predictions)
            
            # v7新增：计算过拟合程度
            # 在训练集上评估
            train_pred_scaled = model.predict(x_train, verbose=0)
            train_pred_open = self.open_scaler.inverse_transform(train_pred_scaled[:, 0].reshape(-1, 1)).flatten()
            train_pred_close = self.close_scaler.inverse_transform(train_pred_scaled[:, 1].reshape(-1, 1)).flatten()
            train_predictions = np.column_stack([train_pred_open, train_pred_close])
            train_r2 = r2_score(self.open_scaler.inverse_transform(y_train[:, 0].reshape(-1, 1)).flatten(), train_pred_open)
            
            # 过拟合惩罚 = max(0, train_r2 - test_r2)
            overfit_penalty = max(0, train_r2 - metrics['r2_score'])
            
            # v7新增：综合评分机制
            # 综合评分 = 0.4 * R² + 0.4 * (方向准确率/100) - 0.2 * 过拟合惩罚
            direction_score = metrics['direction_accuracy'] / 100
            综合评分 = 0.4 * metrics['r2_score'] + 0.4 * direction_score - 0.2 * overfit_penalty
            
            print(f'RMSE: {metrics["rmse"]:.2f}, MAE: {metrics["mae"]:.2f}, '
                  f'MAPE: {metrics["mape"]:.2f}%, R²: {metrics["r2_score"]:.4f}')
            print(f'方向准确率: {metrics["direction_accuracy"]:.2f}%, '
                  f'过拟合惩罚: {overfit_penalty:.4f}, 综合评分: {综合评分:.4f}')
            
            # 保存最佳模型（使用综合评分）
            if 综合评分 > best_r2:
                best_r2 = 综合评分
                best_lookback = lookback_days
                best_model = model
                best_metrics = metrics
                best_metrics['composite_score'] = 综合评分
                best_metrics['overfit_penalty'] = overfit_penalty
                print(f">> 这是目前最佳的配置！")
        
        # 使用最佳配置重新训练最终模型（使用全量数据）
        print(f"\n使用最佳配置 (lookback={best_lookback}) 重新训练最终模型...")
        x_full, y_full = self.create_sequences(scaled_data, best_lookback)
        
        # 创建样本权重
        sample_weights_full = None
        if config.get('use_sample_weights', False):
            sample_weights_full = self.create_sample_weights(
                len(x_full),
                decay_rate=config.get('sample_weight_decay', 0.9985)
            )
        
        # 划分训练/验证集
        x_train_full, x_val_full, y_train_full, y_val_full = train_test_split(
            x_full, y_full,
            test_size=0.1,
            random_state=42,
            shuffle=False
        )
        
        train_weights_full = None
        if sample_weights_full is not None:
            train_weights_full = sample_weights_full[:len(x_train_full)]
        
        # 构建最终模型（v7参数）
        final_model = self.build_model(
            best_lookback,
            data.shape[1],
            learning_rate=config.get('learning_rate', 0.0005),  # v7: 降低学习率
            l2_reg=config.get('l2_reg', 0.001),  # v7: L2正则化
            dropout_rate=config.get('dropout_rate', 0.4),  # v7: 更高dropout
            use_directional_loss=config.get('use_directional_loss', True),  # v7: 方向感知损失
            direction_alpha=config.get('direction_alpha', 0.5)  # v7: 方向损失权重
        )
        
        # 回调函数（v7：更保守的Early Stopping）
        callbacks_final = [
            EarlyStopping(
                monitor='val_loss',
                patience=30,  # v7: 从40降至30
                restore_best_weights=True,
                verbose=0
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=15,  # v7: 从20降至15
                min_lr=0.00001,
                verbose=0
            )
        ]
        
        # 训练最终模型
        print('训练最终模型...')
        final_history = final_model.fit(
            x_train_full, y_train_full,
            batch_size=config.get('batch_size', 16),
            epochs=config.get('epochs', 200),
            validation_data=(x_val_full, y_val_full),
            callbacks=callbacks_final,
            sample_weight=train_weights_full,
            verbose=0
        )
        
        # 保存最终模型
        self.model = final_model
        self.best_lookback = best_lookback
        
        final_train_loss = final_history.history['loss'][-1]
        final_val_loss = final_history.history['val_loss'][-1]
        final_epochs = len(final_history.history['loss'])
        
        print(f'\n最终模型训练完成！')
        print(f'  训练轮次: {final_epochs} epochs')
        print(f'  最终训练损失: {final_train_loss:.6f}')
        print(f'  最终验证损失: {final_val_loss:.6f}')
        
        return {
            'success': True,
            'best_lookback': int(best_lookback),
            'r2_score': float(best_r2),
            'metrics': best_metrics,
            'training_epochs': int(final_epochs),
            'final_train_loss': float(final_train_loss),
            'final_val_loss': float(final_val_loss),
            'feature_count': len(self.feature_columns)
        }
    
    def predict_future(self, df, future_steps=20):
        """
        预测未来价格
        
        Args:
            df: 原始数据DataFrame
            future_steps: 预测未来天数
            
        Returns:
            预测结果字典
        """
        if self.model is None or self.best_lookback is None:
            raise ValueError("模型尚未训练，请先调用 train() 方法")
        
        # 准备特征
        data = self.prepare_features(df, self.train_config.get('selected_features'))
        
        # 标准化数据
        scaled_data = np.zeros(data.shape)
        for i, col in enumerate(data.columns):
            if col in self.scalers:
                scaled_data[:, i] = self.scalers[col].transform(data[[col]]).flatten()
        
        # 准备最后lookback_days的数据
        last_sequence = scaled_data[-self.best_lookback:].reshape(1, self.best_lookback, data.shape[1])
        
        # 预测未来价格（双输出：开盘价和收盘价）
        future_predictions_open = []
        future_predictions_close = []
        current_price = data['close'].iloc[-1]
        
        for i in range(future_steps):
            # 预测下一天（返回[open, close]）
            next_pred_scaled = self.model.predict(last_sequence, verbose=0)
            next_pred_open = self.open_scaler.inverse_transform(next_pred_scaled[:, 0].reshape(-1, 1))[0][0]
            next_pred_close = self.close_scaler.inverse_transform(next_pred_scaled[:, 1].reshape(-1, 1))[0][0]
            
            future_predictions_open.append(next_pred_open)
            future_predictions_close.append(next_pred_close)
            
            # 更新序列
            next_scaled = np.zeros((1, 1, data.shape[1]))
            # 更新收盘价和开盘价
            next_scaled[0, 0, 0] = next_pred_scaled[0, 1]  # close
            next_scaled[0, 0, 1] = next_pred_scaled[0, 0]  # open
            
            # 其他特征使用前一天的值（简化处理）
            for j in range(2, data.shape[1]):
                next_scaled[0, 0, j] = last_sequence[0, -1, j]
            
            # 滚动窗口
            last_sequence = np.concatenate([last_sequence[:, 1:, :], next_scaled], axis=1)
        
        # 生成未来日期（跳过周末）
        last_date = data.index[-1]
        future_dates = []
        current_date = last_date
        while len(future_dates) < future_steps:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # 周一到周五
                future_dates.append(current_date.strftime('%Y-%m-%d'))
        
        # 计算涨跌幅（基于收盘价）
        predictions_list = []
        for i, (date, pred_open, pred_close) in enumerate(zip(future_dates, future_predictions_open, future_predictions_close)):
            if i == 0:
                daily_change = pred_close - current_price
                daily_change_pct = (daily_change / current_price) * 100
            else:
                daily_change = pred_close - future_predictions_close[i-1]
                daily_change_pct = (daily_change / future_predictions_close[i-1]) * 100
            
            total_change = pred_close - current_price
            total_change_pct = (total_change / current_price) * 100
            
            # 简单的置信度估计（距离越远置信度越低）
            confidence = max(0.5, 0.9 - (i * 0.02))
            
            # 估算最高价和最低价（基于预测的开盘价和收盘价）
            daily_volatility = abs(pred_close - pred_open) * 0.5
            pred_high = max(pred_open, pred_close) + daily_volatility
            pred_low = min(pred_open, pred_close) - daily_volatility
            
            predictions_list.append({
                'date': date,
                'predicted_open': float(pred_open),
                'predicted_close': float(pred_close),
                'predicted_high': float(pred_high),
                'predicted_low': float(pred_low),
                'predicted_price': float(pred_close),  # 保留兼容性
                'daily_change': float(daily_change),
                'daily_change_pct': float(daily_change_pct),
                'total_change': float(total_change),
                'total_change_pct': float(total_change_pct),
                'confidence': float(confidence)
            })
        
        # 判断趋势（基于收盘价）
        trend = 'up' if future_predictions_close[-1] > current_price else 'down'
        
        return {
            'success': True,
            'predictions': predictions_list,
            'trend': trend,
            'current_price': float(current_price),
            'last_date': last_date.strftime('%Y-%m-%d')
        }
    
    @staticmethod
    def get_available_features():
        """获取可用的训练因子列表 v7"""
        return {
            '基础特征': [
                {'key': 'close', 'name': '收盘价', 'description': '每日收盘价格', 'recommended': True},
                {'key': 'open', 'name': '开盘价', 'description': '每日开盘价格', 'recommended': True},
                {'key': 'high', 'name': '最高价', 'description': '每日最高价格', 'recommended': True},
                {'key': 'low', 'name': '最低价', 'description': '每日最低价格', 'recommended': True},
                {'key': 'volume', 'name': '成交量', 'description': '每日成交量', 'recommended': True}
            ],
            '技术指标': [
                {'key': 'ma5', 'name': 'MA5', 'description': '5日移动平均线', 'recommended': True},
                {'key': 'ma10', 'name': 'MA10', 'description': '10日移动平均线', 'recommended': True},
                {'key': 'ma20', 'name': 'MA20', 'description': '20日移动平均线', 'recommended': True},
                {'key': 'ma60', 'name': 'MA60', 'description': '60日移动平均线（v7新增）', 'recommended': True},
                {'key': 'volatility', 'name': '波动率', 'description': '10日价格标准差', 'recommended': False},
                {'key': 'rsi', 'name': 'RSI', 'description': '相对强弱指标(14日)', 'recommended': False},
                {'key': 'macd', 'name': 'MACD', 'description': 'MACD指标', 'recommended': False},
                {'key': 'macd_signal', 'name': 'MACD信号线', 'description': 'MACD信号线', 'recommended': False},
                {'key': 'bb_middle', 'name': '布林中轨', 'description': '20日移动平均线', 'recommended': False},
                {'key': 'bb_upper', 'name': '布林上轨', 'description': '中轨 + 2倍标准差', 'recommended': False},
                {'key': 'bb_lower', 'name': '布林下轨', 'description': '中轨 - 2倍标准差', 'recommended': False},
                {'key': 'momentum', 'name': '动量', 'description': '5日价格动量', 'recommended': False},
                {'key': 'momentum_3d', 'name': '3日动量', 'description': '3日价格动量（v7新增）', 'recommended': False}
            ],
            '市场强度特征': [
                {'key': 'price_accel', 'name': '价格加速度', 'description': '价格变化的加速度', 'recommended': False},
                {'key': 'price_accel_3d', 'name': '3日价格加速度', 'description': '3日价格加速度（v7新增）', 'recommended': False},
                {'key': 'volume_ratio', 'name': '量比', 'description': '当日成交量/5日均量', 'recommended': False},
                {'key': 'consecutive_days', 'name': '连续涨跌天数', 'description': '连续上涨或下跌的天数', 'recommended': False},
                {'key': 'high_low_ratio', 'name': '日内波动幅度', 'description': '最高价/最低价', 'recommended': False},
                {'key': 'close_high_ratio', 'name': '收盘位置', 'description': '收盘价/最高价', 'recommended': False},
                {'key': 'volume_price', 'name': '成交金额', 'description': '成交量 * 收盘价', 'recommended': False},
                {'key': 'ma5_ma10_cross', 'name': 'MA5/MA10交叉', 'description': '(MA5-MA10)/MA10（v7新增）', 'recommended': True},
                {'key': 'close_ma60_ratio', 'name': '价格/MA60', 'description': '收盘价/MA60（v7新增）', 'recommended': True}
            ],
            '价格变化特征': [
                {'key': 'price_change', 'name': '日涨跌幅', 'description': '当日价格变化百分比', 'recommended': False},
                {'key': 'price_change_5d', 'name': '5日涨跌幅', 'description': '5日价格变化百分比', 'recommended': False},
                {'key': 'volume_change', 'name': '成交量变化率', 'description': '成交量日变化百分比', 'recommended': False}
            ],
            '日期特征': [
                {'key': 'day_of_week', 'name': '星期几', 'description': '0=周一, 6=周日', 'recommended': False},
                {'key': 'month', 'name': '月份', 'description': '1-12月', 'recommended': False},
                {'key': 'quarter', 'name': '季度', 'description': '1-4季度', 'recommended': False},
                {'key': 'day_of_year', 'name': '年中第几天', 'description': '1-365/366', 'recommended': False},
                {'key': 'is_month_start', 'name': '是否月初', 'description': '1-5日为月初', 'recommended': False},
                {'key': 'is_month_end', 'name': '是否月末', 'description': '25日以后为月末', 'recommended': False},
                {'key': 'is_monday', 'name': '是否周一', 'description': '1=周一, 0=其他', 'recommended': False},
                {'key': 'is_friday', 'name': '是否周五', 'description': '1=周五, 0=其他', 'recommended': False}
            ]
        }

