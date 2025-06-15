# -*- coding: utf-8 -*-
import collections
import datetime
import logging
import akshare as ak
import warnings
from typing import Dict, List, Optional, Tuple, Union
import pandas_market_calendars as mcal
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import (GradientBoostingClassifier, HistGradientBoostingClassifier,
                              StackingClassifier, RandomForestClassifier)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import make_scorer, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, QuantileTransformer
from sklearn.svm import SVC
from skopt import BayesSearchCV
from skopt.space import Real, Integer
from dateutil.relativedelta import relativedelta
from joblib import Parallel, delayed
from joblib import Memory

warnings.filterwarnings("ignore", category=UserWarning,
                       message="n_quantiles.*is greater than the total number of samples")
memory = Memory(location='./cache', verbose=0)

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("enhanced_analysis_optimized.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")

# 扩展字段映射配置
FIELD_MAPPING = {
    "stock_zh_a_hist": {
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
}

class TimeSeriesFeatureEngineer(TransformerMixin, BaseEstimator):
    """时间序列特征工程处理器，避免未来函数偏差"""
    
    def __init__(self, lookback_windows: List[int] = [3, 5, 10, 14, 20, 30, 60]):
        self.lookback_windows = lookback_windows
        self.selected_features = []
        self._feature_names = None
        self._column_mapping = {
            'close': 'close',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'volume': 'volume',
            'turnover_rate': 'turnover_rate',
            'amplitude_pct': 'amplitude_pct'
        }
        
    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):
        """拟合特征工程器，确保不使用未来数据"""
        # 保存原始列名
        if isinstance(X, pd.DataFrame):
            self._column_mapping = {col: col for col in X.columns}
            # 预先计算特征名称
            features = self._generate_features(X)
            self._feature_names = features.columns.tolist()
        else:
            # 如果是numpy数组，使用默认特征名称
            self._feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        return self
        
    def _generate_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """生成特征，严格使用历史数据"""
        features = pd.DataFrame(index=X.index)
        
        # 1. 基础价格特征
        for col in ['close', 'open', 'high', 'low', 'volume']:
            if col in X.columns:
                features[col] = X[col]
            elif col in self._column_mapping and self._column_mapping[col] in X.columns:
                features[col] = X[self._column_mapping[col]]
                
        # 2. 价格变化率
        if 'close' in features.columns:
            features['returns'] = features['close'].pct_change()
        
        # 3. 移动平均特征
        for window in self.lookback_windows:
            # 价格移动平均
            if 'close' in features.columns:
                features[f'ma_{window}'] = features['close'].rolling(window=window, min_periods=1).mean()
            # 成交量移动平均
            if 'volume' in features.columns:
                features[f'volume_ma_{window}'] = features['volume'].rolling(window=window, min_periods=1).mean()
            
        # 4. 波动率特征
        if 'returns' in features.columns:
            for window in self.lookback_windows:
                features[f'volatility_{window}'] = features['returns'].rolling(window=window, min_periods=1).std()
            
        # 5. 动量特征
        if 'returns' in features.columns:
            features['momentum_1d'] = features['returns']
        if 'close' in features.columns:
            features['momentum_5d'] = features['close'].pct_change(5)
            features['momentum_10d'] = features['close'].pct_change(10)
        
        # 6. 波动率比率
        if 'volatility_5d' in features.columns and 'volatility_20d' in features.columns:
            features['volatility_ratio'] = (
                features['volatility_5d'] / features['volatility_20d'].replace(0, 1e-8)
            )
        
        # 7. 成交量特征
        if 'volume' in features.columns and 'volume_ma_20' in features.columns:
            features['volume_ratio'] = features['volume'] / features['volume_ma_20'].replace(0, 1e-8)
        
        # 8. 价格位置特征
        for window in [20, 60]:
            if 'close' in features.columns and f'ma_{window}' in features.columns:
                features[f'price_position_{window}'] = (
                    (features['close'] - features[f'ma_{window}']) / features[f'ma_{window}'].replace(0, 1e-8)
                )
            
        # 9. 时间特征
        if isinstance(X.index, pd.DatetimeIndex):
            features['day_of_week'] = X.index.dayofweek
            features['month'] = X.index.month
            features['is_month_end'] = X.index.is_month_end.astype(int)
            
        # 10. 换手率特征
        if 'turnover_rate' in X.columns:
            features['turnover_rate'] = X['turnover_rate']
            features['turnover_ma_5'] = X['turnover_rate'].rolling(5, min_periods=1).mean()
            features['turnover_ma_20'] = X['turnover_rate'].rolling(20, min_periods=1).mean()
            if 'turnover_ma_20' in features.columns:
                features['turnover_ratio'] = X['turnover_rate'] / features['turnover_ma_20'].replace(0, 1e-8)
            
        # 11. 振幅特征
        if 'amplitude_pct' in X.columns:
            features['amplitude_pct'] = X['amplitude_pct']
            features['amplitude_ma_5'] = X['amplitude_pct'].rolling(5, min_periods=1).mean()
            features['amplitude_ma_20'] = X['amplitude_pct'].rolling(20, min_periods=1).mean()
            
        # 12. 填充缺失值
        features = features.fillna(method='ffill').fillna(0)
        
        # 13. 移除原始价格和成交量列（避免信息泄露）
        columns_to_drop = ['close', 'open', 'high', 'low', 'volume']
        features = features.drop(columns=[col for col in columns_to_drop if col in features.columns])
        
        # 确保至少有一个特征
        if features.shape[1] == 0:
            # 如果没有生成任何特征，至少保留一个基础特征
            if 'returns' in features.columns:
                features = pd.DataFrame({'returns': features['returns']}, index=features.index)
            else:
                raise ValueError("无法生成任何有效特征，请检查输入数据")
            
        return features
        
    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """转换数据，使用已训练的特征工程器"""
        if isinstance(X, np.ndarray):
            if self._feature_names is None:
                raise ValueError("特征名称未初始化，请先调用fit方法")
            # 创建临时DataFrame用于特征生成
            temp_df = pd.DataFrame(X, columns=self._feature_names)
            # 确保列名与训练时一致
            temp_df = temp_df.rename(columns=dict(zip(self._feature_names, ['close', 'open', 'high', 'low', 'volume', 'turnover_rate', 'amplitude_pct'])))
            features = self._generate_features(temp_df)
        else:
            features = self._generate_features(X)
            
        # 确保特征数量与训练时一致
        if self._feature_names is not None:
            missing_cols = set(self._feature_names) - set(features.columns)
            if missing_cols:
                for col in missing_cols:
                    features[col] = 0
            features = features[self._feature_names]
            
        return features.values
        
    def get_feature_names(self) -> List[str]:
        """获取特征名称"""
        if self._feature_names is None:
            raise ValueError("特征名称未初始化，请先调用fit方法")
        return self._feature_names.copy()

class TimeSeriesMarketAnalyzer:
    """优化版市场分析器，避免未来函数偏差"""
    
    def __init__(self, symbol: str = "600000"):
        self.symbol = symbol
        self.exchange = mcal.get_calendar('SSE')
        self.holding_period = 5
        
        # 特征工程管道
        self.feature_pipe = Pipeline([
            ("features", TimeSeriesFeatureEngineer()),
            ("scaler", QuantileTransformer(n_quantiles=1000))
        ])
        
        # 模型
        self.model = self._build_model()
        
    def _build_model(self) -> Pipeline:
        """构建时间序列模型"""
        base_models = [
            ('svm', SVC(
                probability=True,
                kernel='rbf',
                class_weight='balanced',
                cache_size=500
            ))
        ]
        
        meta_model = LogisticRegression(class_weight='balanced', solver='liblinear')
        
        stacking_model = StackingClassifier(
            estimators=base_models,
            final_estimator=meta_model,
            stack_method='predict_proba',
            passthrough=True,
            n_jobs=1  # 修改为单线程以避免并行问题
        )
        
        return Pipeline([
            ('feature_pipe', self.feature_pipe),
            ('stacking_model', stacking_model)
        ])
        
    def fetch_market_data(self, refresh: bool = False) -> pd.DataFrame:
        """获取市场数据，确保时间序列完整性"""
        try:
            # 获取原始数据
            start_date = datetime.datetime.now() - relativedelta(years=3)
            end_date = datetime.datetime.now()
            
            df = ak.stock_zh_a_hist(
                symbol=self.symbol,
                period='daily',
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust='hfq'
            )
            
            # 重命名列
            df = df.rename(columns=FIELD_MAPPING["stock_zh_a_hist"])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 确保时间序列完整性
            df = df.sort_index()
            df = df.asfreq('D')
            
            # 填充缺失值
            df = df.fillna(method='ffill')
            
            return df
            
        except Exception as e:
            logger.error(f"数据获取失败: {str(e)}")
            raise
            
    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """准备训练数据，避免未来函数偏差"""
        # 确保数据按时间排序
        df = df.sort_index()
        
        # 生成未来收益率（避免使用未来数据）
        df['future_return'] = df['close'].shift(-self.holding_period) / df['close'] - 1
        
        # 移除无法计算未来收益的数据
        df = df.iloc[:-self.holding_period]
        
        # 生成目标变量
        y = (df['future_return'] > 0).astype(int)
        X = df.drop(columns=['future_return'])
        
        # 特征处理
        X = self.feature_pipe.fit_transform(X)
        
        return X, y
        
    def _log_optimization_results(self, optimizer: BayesSearchCV):
        """增强版优化结果日志记录"""
        # 基础信息记录
        total_duration = pd.Timedelta(seconds=np.sum(optimizer.cv_results_['mean_fit_time']))
        logger.info("\n\n=== 模型优化分析报告 ===")
        logger.info(f"优化时间: (耗时: {total_duration})")

        # 训练数据信息
        X, y = self.prepare_training_data(self.fetch_market_data())
        logger.info("\n[数据统计]")
        logger.info(f"样本总数: {X.shape[0]} | 特征维度: {X.shape[1]}")
        logger.info(f"正负样本比: {np.round(np.mean(y) * 100, 1)}% 上涨 vs {np.round((1 - np.mean(y)) * 100, 1)}% 下跌")

        # 最佳参数记录
        logger.info("\n[最佳参数组合]")
        param_table = "\n".join([f"{k:40} : {v}" for k, v in optimizer.best_params_.items()])
        logger.info(param_table)

        # 交叉验证结果分析
        cv_results = optimizer.cv_results_
        metrics = {
            'roc_auc': ('AUC-ROC', '{:.3f}'),
            'precision': ('精确率', '{:.2%}'),
            'recall': ('召回率', '{:.2%}')
        }

        logger.info("\n[交叉验证统计]")
        for metric, (name, fmt) in metrics.items():
            scores = cv_results[f'mean_test_{metric}']
            logger.info(f"{name:8} : {fmt.format(np.mean(scores))} ± {fmt.format(np.std(scores))}")

        # 参数重要性分析
        logger.info("\n[参数敏感度分析]")
        param_importance = {}
        for i, params in enumerate(cv_results['params']):
            for param, value in params.items():
                delta = cv_results['mean_test_roc_auc'][i] - np.mean(cv_results['mean_test_roc_auc'])
                param_importance.setdefault(param, []).append(delta)

        importance_table = []
        for param, deltas in param_importance.items():
            impact = np.mean(deltas)
            importance_table.append((param, impact))

        importance_table.sort(key=lambda x: abs(x[1]), reverse=True)
        for param, impact in importance_table[:5]:
            logger.info(f"{param:40} : {impact:+.4f} (对AUC-ROC影响)")

        # 关键指标评估
        logger.info("\n[关键风险指标]")
        logger.info("AUC-ROC基线值: {:.3f}".format(
            np.mean(cv_results['mean_test_roc_auc'])
        ))

        # 打印优化警告
        if np.mean(cv_results['mean_test_precision']) < 0.55:
            logger.warning("\n 精确率低于阈值(55%)，建议检查类别不平衡问题")
        if np.std(cv_results['mean_test_recall']) > 0.1:
            logger.warning(" 召回率波动较大，模型稳定性需提升")
        
    def optimize_model(self, n_iter: int = 50, cv_splits: int = 5) -> dict:
        """优化模型参数，使用时间序列交叉验证"""
        try:
            # 获取数据
            df = self.fetch_market_data()
            X, y = self.prepare_training_data(df)
            
            # 时间序列交叉验证
            tscv = TimeSeriesSplit(n_splits=cv_splits, test_size=30)
            
            # 定义评估指标
            scoring = {
                'roc_auc': 'roc_auc',
                'precision': make_scorer(precision_score, zero_division=0),
                'recall': make_scorer(recall_score, zero_division=0)
            }
            
            # 参数搜索空间
            search_spaces = [{
                'stacking_model__svm__C': Real(0.1, 100, prior='log-uniform'),
                'stacking_model__svm__gamma': Real(1e-5, 1, prior='log-uniform'),
                'stacking_model__svm__kernel': ['rbf', 'sigmoid'],
                'stacking_model__final_estimator__C': Real(0.1, 10, prior='log-uniform')
            }]
            
            # 贝叶斯优化
            bayes_cv = BayesSearchCV(
                estimator=self.model,
                search_spaces=search_spaces,
                n_iter=n_iter,
                cv=tscv,
                scoring=scoring,
                refit='roc_auc',
                random_state=42,
                n_jobs=1  # 修改为单线程以避免并行问题
            )
            
            # 训练模型
            bayes_cv.fit(X, y)
            
            # 记录优化结果
            self._log_optimization_results(bayes_cv)
            
            # 更新模型
            self.model = bayes_cv.best_estimator_
            
            # 返回优化结果
            return {
                'best_params': bayes_cv.best_params_,
                'best_score': bayes_cv.best_score_,
                'cv_results': bayes_cv.cv_results_
            }
            
        except Exception as e:
            logger.error(f"模型优化失败: {str(e)}")
            raise
            
    def generate_trading_signals(self, confidence_threshold: float = 0.6) -> pd.DataFrame:
        """生成交易信号，确保不使用未来数据"""
        try:
            # 获取市场数据
            df = self.fetch_market_data()
            
            # 特征处理
            X = self.feature_pipe.transform(df)
            
            # 模型预测
            proba = self.model.predict_proba(X)[:, 1]
            predictions = (proba >= confidence_threshold).astype(int)
            
            # 生成信号
            signals = pd.DataFrame({
                'date': df.index,
                'close_price': df['close'],
                'open': df['open'],
                'high': df['high'],
                'low': df['low'],
                'volume': df['volume'],
                'prediction': predictions,
                'confidence': proba,
                'signal_type': 'HOLD'
            }, index=df.index)
            
            # 设置买入信号
            signals.loc[predictions == 1, 'signal_type'] = 'BUY'
            
            # 添加风险控制
            signals = self._apply_risk_management(signals, df)
            
            return signals
            
        except Exception as e:
            logger.error(f"信号生成失败: {str(e)}")
            raise
            
    def _apply_risk_management(self, signals: pd.DataFrame, market_data: pd.DataFrame) -> pd.DataFrame:
        """应用风险控制，使用历史数据"""
        # 计算波动率
        volatility = market_data['close'].pct_change().rolling(20).std()
        
        # 设置止损
        signals['stop_loss'] = signals['close_price'] * 0.95
        
        # 根据波动率调整仓位
        signals['position_size'] = 0.5 * (1 - volatility)
        
        return signals
        
    def _calculate_performance(self, trades: List[dict], initial_capital: float) -> dict:
        """计算策略绩效"""
        if not trades:
            return {
                'total_return': 0.0,
                'win_rate': 0.0,
                'total_trades': 0
            }
            
        trade_df = pd.DataFrame(trades)
        
        # 计算收益
        total_return = (trade_df['price'].iloc[-1] * trade_df['shares'].iloc[-1] - initial_capital) / initial_capital
        
        # 计算胜率
        winning_trades = len(trade_df[trade_df['type'] == 'SELL'])
        total_trades = len(trade_df[trade_df['type'] == 'BUY'])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': total_trades
        }
        
    def backtest_strategy(self, initial_capital: float = 1e6, holding_period: int = None) -> dict:
        """回测策略，确保时间序列完整性"""
        try:
            # 如果提供了holding_period，更新实例变量
            if holding_period is not None:
                self.holding_period = holding_period
                
            # 获取信号
            signals = self.generate_trading_signals()
            
            # 初始化回测变量
            portfolio_value = initial_capital
            position = 0
            trades = []
            
            # 按时间顺序遍历信号
            for date, signal in signals.iterrows():
                if signal['signal_type'] == 'BUY' and position == 0:
                    # 买入
                    position = portfolio_value * signal['position_size'] / signal['close_price']
                    portfolio_value -= position * signal['close_price']
                    trades.append({
                        'date': date,
                        'type': 'BUY',
                        'price': signal['close_price'],
                        'shares': position
                    })
                elif position > 0 and signal['close_price'] <= signal['stop_loss']:
                    # 止损
                    portfolio_value += position * signal['close_price']
                    trades.append({
                        'date': date,
                        'type': 'SELL',
                        'price': signal['close_price'],
                        'shares': position
                    })
                    position = 0
                    
            # 计算绩效
            performance = self._calculate_performance(trades, initial_capital)
            
            # 记录回测结果
            logger.info("\n=== 策略回测报告 ===")
            logger.info(f"初始资金: {initial_capital:,.2f}")
            logger.info(f"最终资金: {portfolio_value:,.2f}")
            logger.info(f"总收益率: {performance.get('total_return', 0.0):.2%}")
            logger.info(f"胜率: {performance.get('win_rate', 0.0):.2%}")
            logger.info(f"总交易次数: {performance.get('total_trades', 0)}")
            
            return {
                'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
                'performance': performance
            }
            
        except Exception as e:
            logger.error(f"回测失败: {str(e)}")
            raise

if __name__ == "__main__":
    # 示例使用
    symbol = '600519'
    analyzer = TimeSeriesMarketAnalyzer(symbol)
    
    # 优化模型
    optimization_results = analyzer.optimize_model(n_iter=10)
    print("优化结果:", optimization_results)
    
    # 回测策略
    backtest_results = analyzer.backtest_strategy()
    print("回测结果:", backtest_results) 