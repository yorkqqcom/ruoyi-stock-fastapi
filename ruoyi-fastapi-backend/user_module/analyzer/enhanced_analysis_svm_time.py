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
        logging.FileHandler("enhanced_analysis.log"),
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

class DynamicQuantileTransformer(QuantileTransformer):
    def fit(self, X, y=None):
        if X.empty:
            logger.error("接收到的特征矩阵为空，列信息: %s", X.columns.tolist())
            raise ValueError("无法对空数据进行分位数转换，请检查上游数据处理流程")
        n_samples = X.shape[0]
        self.n_quantiles = min(max(self.n_quantiles, 1), n_samples)
        logger.debug(f"实际使用的分位数数量: {self.n_quantiles}")
        return super().fit(X, y)

    def transform(self, X):
        arr = super().transform(X)
        # 保持DataFrame格式
        return pd.DataFrame(arr, columns=X.columns, index=X.index)

class EnhancedFeatureEngineer(TransformerMixin, BaseEstimator):
    """增强版特征工程处理器"""
    REQUIRED_RAW_COLS = [
        "close",
        "high",
        "low",
        "volume",
        "turnover_rate",
        # "amplitude_pct",
        "change_pct",
        # "amount",
    ]

    def __init__(
            self,
            lookback_windows: List[int] = [3, 5, 10, 14, 20, 30, 60],
            fourier_components: int = 5,
            dynamic_feature_selection: bool = True
    ):
        self.lookback_windows = lookback_windows
        self.fourier_components = fourier_components
        self.dynamic_feature_selection = dynamic_feature_selection
        self.selected_features = [
            'day_of_week',
            'month',
            'is_month_end',
            'price_volume_div',
        ]
        # 配置技术指标参数
        self._init_ta_params()

    def _init_ta_params(self):
        """初始化技术指标参数"""
        self.ta_config = {
            "rsi": {"timeperiods": [6, 14, 28]},  # 多周期RSI
            "macd": {"fast": 12, "slow": 26, "signal": 9},
            "atr": {"timeperiod": 14},
            "obv": {"ma_period": 21}
        }

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):

        # 生成所有特征
        transformed_X = self.transform(X)

        """动态特征选择拟合"""
        if self.dynamic_feature_selection:
            self._perform_feature_selection(transformed_X, y)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """高效特征生成流程"""
        # 数据校验
        self._validate_input(X)
        # Ensure unique index
        if X.index.duplicated().any():
            X = X[~X.index.duplicated(keep='first')]
        # 提取所需数值列
        numeric_data = X[self.REQUIRED_RAW_COLS].copy()

        # 并行特征计算
        df = self._parallel_feature_generation(numeric_data)

        # 动态特征选择
        if self.dynamic_feature_selection and self.selected_features:
            df = df[self.REQUIRED_RAW_COLS + self.selected_features]

        # 确保列名唯一性
        final_cols = list(set(self.REQUIRED_RAW_COLS + (self.selected_features or [])))

        # 列名唯一性验证
        if len(final_cols) != len(set(final_cols)):
            duplicates = [item for item, count in collections.Counter(final_cols).items() if count > 1]
            raise ValueError(f"发现重复列名: {duplicates}")
        # 确保返回DataFrame并保留列名
        df = pd.DataFrame(df, columns=final_cols, index=X.index)

        df = df.ffill().fillna(0)
        df = df.replace([np.inf, -np.inf], 0)
        final_cols = sorted(list(set(self.REQUIRED_RAW_COLS + self.selected_features)))
        df = pd.DataFrame(df, columns=final_cols, index=X.index)
        return df


    def _validate_input(self, X: pd.DataFrame):
        """增强数据校验"""

        missing = [c for c in self.REQUIRED_RAW_COLS if c not in X.columns]
        if missing:
            logger.error("缺失必要列: %s", missing)
            raise ValueError(f"Missing required columns: {missing}")

        if X.isnull().values.any():
            logger.warning("输入数据包含缺失值，建议先进行预处理")

    def _parallel_feature_generation(self, df: pd.DataFrame) -> pd.DataFrame:

        """并行化特征生成（已修复）"""
        from sklearn.preprocessing import FunctionTransformer

        # 创建转换器列表
        transformers = [
            ('ta', FunctionTransformer(self._calculate_ta_features, validate=False)),
            ('temporal', FunctionTransformer(self._temporal_features, validate=False))
        ]

        # 并行执行
        results = Parallel(n_jobs=12, prefer="threads")(
            delayed(transformer.transform)(df.copy())
            for name, transformer in transformers
        )

        # 合并结果
        merged_df = pd.concat([df] + results, axis=1)

        # 添加其他特征
        merged_df["lyapunov"] = self._lyapunov_exponent_optimized(merged_df["close"].values)
        return self._cross_features(merged_df)

    def _calculate_ta_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """技术指标计算（返回新特征）"""
        new_features = pd.DataFrame(index=df.index)

        # 动量指标
        new_features["momentum"] = df["close"].pct_change(14)

        # 波动率指标
        for window in self.lookback_windows:
            col_name = f"volatility_{window}d"
            if col_name not in self.REQUIRED_RAW_COLS:
                new_features[col_name] = df["close"].pct_change().rolling(window).std()

        # Z-Score
        new_features["zscore"] = self._adaptive_zscore(df["close"])

        return new_features

    def _adaptive_zscore(self, series: pd.Series) -> pd.Series:
        """自适应Z-Score计算"""
        rolling_window = 20  # 原为14日
        rolling_mean = series.ewm(span=rolling_window).mean()
        rolling_std = series.ewm(span=rolling_window).std().replace(0, 1e-8)
        return (series - rolling_mean) / rolling_std


    def _temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """时间特征（返回新特征）"""
        new_features = pd.DataFrame(index=df.index)
        # 季节性特征
        if isinstance(df.index, pd.DatetimeIndex):
            new_features["day_of_week"] = df.index.dayofweek
            new_features["month"] = df.index.month
            new_features["is_month_end"] = df.index.is_month_end.astype(int)
            # 周数特征
            new_features["week_of_year"] = df.index.isocalendar().week
            new_features["week_of_month"] = (df.index.day - 1) // 7 + 1

        return new_features

    def _cross_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """交互特征生成"""
        # 量价背离指标
        df["price_volume_div"] = (
                df["close"].pct_change(5) -
                df["volume"].pct_change(5).replace(0, 1e-8)
        )

        # 波动率调整动量
        df["vol_adj_momentum"] = (
                df["momentum"] / df["volatility_14d"].replace(0, 1e-8)
        )

        return df

    def _lyapunov_exponent_optimized(self, series: np.ndarray) -> float:
        """优化版李雅普诺夫指数计算"""
        # 使用更高效的矩阵运算替代循环
        emb_dim = 5
        tau = 1
        n = len(series) - (emb_dim - 1) * tau

        if n < 10:
            return 0.0

        indices = np.arange(n)
        trajectory = series[indices[:, None] + np.arange(emb_dim) * tau]

        # 计算距离矩阵
        dists = np.abs(trajectory[:, None, :] - trajectory[None, :, :]).sum(axis=2)
        np.fill_diagonal(dists, np.inf)

        # 寻找最近邻
        min_indices = np.argmin(dists, axis=1)
        min_dists = dists[np.arange(len(dists)), min_indices]

        # 计算指数增长率
        with np.errstate(divide="ignore", invalid="ignore"):
            valid = (min_dists[:-1] > 1e-7) & (min_dists[1:] > 1e-7)
            if valid.sum() < 10:
                return 0.0
            return np.mean(np.log(min_dists[1:][valid] / min_dists[:-1][valid]))

    def _perform_feature_selection(self, X: pd.DataFrame, y: pd.Series):
        """基于交叉验证的混合特征选择方法"""

        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import KFold

        base_cols = self.REQUIRED_RAW_COLS
        # feature_cols = [col for col in X.columns if col not in base_cols]
        feature_cols = [col for col in X.columns if col not in base_cols]
        if not feature_cols:
            self.selected_features = []
            return

        self.selected_features = feature_cols
        if self.dynamic_feature_selection and self.selected_features:
            # 按字母顺序排序保证稳定性
            self.selected_features = sorted(self.selected_features)

    def _remove_correlated_features(self, X: pd.DataFrame, importances: np.ndarray,
                                    feature_names: List[str], threshold: float = 0.8) -> List[str]:
        """改进版高相关特征处理"""
        corr_matrix = X.corr().abs()
        features_to_keep = []

        # 按重要性降序处理特征
        sorted_indices = np.argsort(importances)[::-1]
        sorted_features = [feature_names[i] for i in sorted_indices if feature_names[i] in X.columns]

        for feature in sorted_features:
            add_feature = True
            # 检查与已选特征的相关性
            for kept in features_to_keep:
                if corr_matrix.loc[feature, kept] > threshold:
                    add_feature = False
                    break
            if add_feature:
                features_to_keep.append(feature)

        return features_to_keep

class EnhancedMarketAnalyzer:
    """增强版市场分析系统"""

    def __init__(self, symbol: str = "600000"):
        self.symbol = symbol
        self._data_versions = {}  # 数据版本控制
        # 初始化上海证券交易所日历
        self.exchange = mcal.get_calendar('SSE')  # 新增代码
        self.selected_features = []  # 初始化为空列表
        self.holding_period = 5



        # 特征工程管道（修改此处使用DynamicQuantileTransformer）
        self.feature_pipe = Pipeline([
            ("features", EnhancedFeatureEngineer()),
            ("scaler", DynamicQuantileTransformer(n_quantiles=1000))  # 使用动态调整的Transformer
        ])

        # 分层集成模型
        self.model = self._build_ensemble_model()

        # # 风险控制模块
        # from .risk_management import RiskManager  # 假设有独立风险模块
        # self.risk_manager = RiskManager(**self.config["risk_params"])

    def _build_ensemble_model(self) -> Pipeline:
        """构建包含特征工程和分层集成模型的总管道"""
        feature_pipe = Pipeline([
            ("features", EnhancedFeatureEngineer()),
            ("scaler", DynamicQuantileTransformer(n_quantiles=1000))
        ])


        base_models = [
            ('svm', SVC(
                        probability=True,
                        kernel='rbf',
                        class_weight='balanced',
                        cache_size=1000
            ))
        ]
        # 元学习器
        meta_model = LogisticRegression(class_weight='balanced', solver='liblinear')

        # 分层集成模型
        stacking_model = StackingClassifier(
            estimators=base_models,
            final_estimator=meta_model,
            stack_method='predict_proba',
            passthrough=True,
            n_jobs=-1  # 启用并行
        )

        # 总管道：特征工程 + 集成模型
        model_pipeline = Pipeline([
            ('feature_pipe', feature_pipe),
            ('stacking_model', stacking_model)
        ])

        return model_pipeline

    def fetch_market_data(self, refresh: bool = False) -> pd.DataFrame:
        """
        完整版市场数据获取方法（适配表结构）

        参数:
            refresh: 是否强制刷新缓存

        返回:
            处理后的标准化数据，包含字段：
            ['date', 'concept', 'open', 'close', 'high', 'low',
             'pct_change', 'price_change', 'volume', 'turnover',
             'amplitude', 'turnover_rate']
        """
        cache_key = f"{self.symbol}_market_data"

        try:
            # 原始数据查询
            raw_df = self._execute_market_query()

            logger.info(f"获取原始数据 {self.symbol} 行数: {len(raw_df)}")
            if raw_df.empty:
                logger.error("获取的原始数据为空，请检查数据源或股票代码")
                raise ValueError("原始数据为空，无法继续处理")
            raw_df = raw_df[~raw_df.index.duplicated(keep='first')]
            # 数据版本控制
            self._data_versions['raw'] = raw_df.copy()

            # 预处理流程
            processed_df = (
                raw_df
                .pipe(self._sanitize_price_data)
                .pipe(self._handle_missing_values)
                .pipe(self._calculate_derived_metrics)
                .pipe(self._filter_abnormal_records)
                .pipe(lambda df: df[~df.index.duplicated(keep='first')])  # 确保索引唯一
                .asfreq('D')  # 转换为每日频率，可能引入NaN
                .pipe(lambda df: raw_df.ffill().bfill())  # 新增：填充缺失日期
                .sort_index()
            )

            if processed_df.empty:
                logger.error("处理后的数据为空，请检查过滤条件")
                raise ValueError("数据预处理后为空，无法继续分析")
            # 数据完整性验证
            self._validate_market_data(processed_df)

            # 更新缓存
            self._update_data_cache(cache_key, processed_df)

            # 存储处理版本
            self._data_versions['processed'] = processed_df.copy()



            return processed_df

        except Exception as e:
            logger.error(f"数据获取失败 [股票: {self.symbol}]")
            logger.error("错误详情：%s", str(e))

            # 尝试返回最近缓存
            if hasattr(self, '_data_cache') and cache_key in self._data_cache:
                logger.warning("返回最近有效缓存数据")
                return self._data_cache[cache_key].copy()
            raise


    def _calculate_bollinger_band(self, close_series: pd.Series,
                                 window: int = 20,
                                 num_std: int = 2) -> pd.Series:
        """计算布林带指标 (返回带宽)"""
        rolling_mean = close_series.rolling(window).mean()
        rolling_std = close_series.rolling(window).std()
        upper_band = rolling_mean + (rolling_std * num_std)
        lower_band = rolling_mean - (rolling_std * num_std)
        return (upper_band - lower_band) / rolling_mean  # 标准化带宽


    def _execute_market_query(self) -> pd.DataFrame:

        # 计算5年前的日期（基于当前系统时间）
        start_date = datetime.datetime.now() - relativedelta(years=5)
        # end_date = datetime.datetime.now() - datetime.timedelta(days=5)
        end_date = datetime.datetime.now()
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        try:
            df = ak.stock_zh_a_hist(
                symbol=self.symbol,
                period='daily',
                start_date=start_date_str,
                end_date=end_date_str,
                adjust='hfq'
            )
            df = df.rename(columns=FIELD_MAPPING["stock_zh_a_hist"])
            # 新增代码：设置日期索引
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.sort_index()  # 确保按日期排序
            return df


        except Exception as e:
            logger.error("数据查询失败")
            raise


    def _sanitize_price_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """价格数据清洗"""
        # 确保价格合理性
        df['high'] = df[['high', 'close']].max(axis=1)
        df['low'] = df[['low', 'close']].min(axis=1)

        # 处理零值
        price_cols = ['open', 'high', 'low', 'close']
        df[price_cols] = df[price_cols].replace(0, np.nan)

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """智能缺失值处理"""

        # 价格字段前向填充
        price_cols = ['open', 'high', 'low', 'close']
        df[price_cols] = df[price_cols].ffill().bfill()

        # 量能字段零值填充
        df['volume'] = df['volume'].fillna(0)
        df['turnover_rate'] = df['turnover_rate'].fillna(0)

        # 百分数字段均值填充
        pct_cols = ['change_pct', 'amplitude_pct', 'turnover_rate']
        # df[pct_cols] = df[pct_cols].fillna(df[pct_cols].mean())
        for col in pct_cols:
            if df[col].isna().all():
                df[col] = 0  # 全NaN时填充0
            else:
                df[col].fillna(df[col].mean(), inplace=True)

        return df

    def _calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算衍生指标"""
        # 波动率调整指标
        df['volatility_5d'] = df['close'].pct_change().rolling(5).std()

        # 量价背离指标
        df['volume_price_divergence'] = (
                df['volume'].pct_change(5) -
                df['close'].pct_change(5)
        )

        return df

    def _filter_abnormal_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """异常记录过滤"""
        # 价格异常过滤
        price_cond = (
                (df['high'] < df['low']) |
                (df['open'] > df['high']) |
                (df['close'] < df['low'])
        )

        # 量能异常过滤
        volume_cond = df['volume'] < 0

        # 振幅异常过滤
        amplitude_cond = df['amplitude_pct'].abs() > 30
        filtered_df = df[~(price_cond | volume_cond | amplitude_cond)]
        logger.info(f"过滤后剩余数据行数: {len(filtered_df)}")
        return filtered_df


    def _validate_market_data(self, df: pd.DataFrame):
        """数据完整性验证"""
        # 验证索引是否为DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.error("数据索引类型错误，实际类型为: %s", type(df.index))
            raise ValueError("数据必须包含日期时间索引(DatetimeIndex)")
        if df.index.duplicated().any():
            raise ValueError("Duplicate dates found in index")
        # 验证索引是否单调递增
        if not df.index.is_monotonic_increasing:
            logger.warning("数据索引未按时间排序，正在重新排序...")
            df.sort_index(inplace=True)

    def _update_data_cache(self, key: str, data: pd.DataFrame):
        """带自动清理的缓存更新"""
        if not hasattr(self, '_data_cache'):
            self._data_cache = {}

        # 保留最近3个概念的数据
        if len(self._data_cache) >= 3:
            oldest_key = min(self._data_cache.keys(), key=lambda k: self._data_cache[k]['timestamp'])
            del self._data_cache[oldest_key]

        self._data_cache[key] = {
            'data': data.copy(),
            'timestamp': datetime.datetime.now()
        }

    def _early_stopping(self, patience: int = 5):
        """贝叶斯优化早停回调"""
        from skopt.callbacks import DeltaYStopper
        return DeltaYStopper(
            delta=0.001,  # 目标函数改善小于0.1%时停止
            n_best=patience  # 连续patience次无改善则停止
        )

    def optimize_model(self, n_iter: int = 50, cv_splits: int = 5) -> dict:
        """
        基于贝叶斯优化的模型参数调优

        参数:
            n_iter: 优化迭代次数
            cv_splits: 时间序列交叉验证分割数

        返回:
            包含最佳参数和交叉验证结果的字典
        """
        try:
            # 获取预处理数据
            df = self.fetch_market_data()
            logger.info(f"数据列: {df.columns.tolist()}")
            # 准备特征矩阵和目标变量
            X, y = self._prepare_training_data(df)

            # 配置贝叶斯搜索空间
            search_spaces = self._get_search_spaces()

            # 创建时间序列交叉验证
            tscv = TimeSeriesSplit(n_splits=cv_splits)

            # 定义评估指标
            scoring = {
                'roc_auc': 'roc_auc',
                'precision': make_scorer(precision_score, zero_division=0),
                'recall': make_scorer(recall_score, zero_division=0),
                'f1': 'f1',
                'balanced_accuracy': 'balanced_accuracy'
            }
            # 初始化贝叶斯优化器
            bayes_cv = BayesSearchCV(
                estimator=self.model,
                search_spaces=search_spaces,
                n_iter=n_iter,
                cv=tscv,
                scoring=scoring,
                refit='roc_auc',
                random_state=42,
                n_jobs=16
            )

            # 5. 早停机制
            from sklearn.exceptions import ConvergenceWarning
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=ConvergenceWarning)
                bayes_cv.fit(X, y,
                             callback=[self._early_stopping(10)])  # 新增早停回调

            # 在bayes_cv.fit之后添加
            best_params = bayes_cv.best_params_

            # 校验权重策略一致性
            if ('stacking_model__svm__class_weight' in best_params and
                    best_params['stacking_model__svm__class_weight'] is None and
                    best_params['stacking_model__xgb__scale_pos_weight'] > 1):
                logger.warning("检测到冲突的样本权重策略，自动修正SVM权重")
                best_params['stacking_model__svm__class_weight'] = 'balanced'
                self.model.set_params(**best_params)

            # 保存最佳模型
            self.model = bayes_cv.best_estimator_
            self._log_optimization_results(bayes_cv)
            
            # 返回完整的交叉验证结果
            cv_results = {
                'best_params': best_params,
                'mean_test_roc_auc': float(bayes_cv.cv_results_['mean_test_roc_auc'][bayes_cv.best_index_]),
                'mean_test_precision': float(bayes_cv.cv_results_['mean_test_precision'][bayes_cv.best_index_]),
                'mean_test_recall': float(bayes_cv.cv_results_['mean_test_recall'][bayes_cv.best_index_]),
                'mean_test_f1': float(bayes_cv.cv_results_['mean_test_f1'][bayes_cv.best_index_]),
                'mean_test_balanced_accuracy': float(bayes_cv.cv_results_['mean_test_balanced_accuracy'][bayes_cv.best_index_])
            }

            return cv_results

        except ValueError as ve:
            logger.error(f"数据准备错误: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"参数优化失败: {str(e)}")
            raise

    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        # 确保数据按日期升序排列
        df = df.sort_index(ascending=True)

        # 生成未来5天收益率
        df['future_5d_return'] = (df['close'].shift(-5) - df['close']) / df['close']


        # 移除无法计算未来收益的最近5天数据，而不是全部删除
        # 保留至少足够的数据用于训练
        required_min_samples = 50  # 根据需求调整最小样本数
        df_clean = df.iloc[:-5] if len(df) > 5 else df.dropna(subset=['future_5d_return'])

        if len(df_clean) < required_min_samples:
            logger.error("生成目标变量后有效数据不足，剩余行数: %d", len(df_clean))
            raise ValueError("有效数据不足，无法生成目标变量")

        y = (df_clean['future_5d_return'] > 0).astype(int)
        X_clean = df_clean.drop(columns=['future_5d_return'])

        # 特征处理
        try:
            X = self.feature_pipe.fit_transform(X_clean, y)
        except ValueError as ve:
            logger.error(f"特征处理失败: {str(ve)}")
            raise

        # 过滤无效样本
        valid_samples = X.notnull().all(axis=1)
        X_final = X[valid_samples]
        y_final = y[valid_samples]

        if X_final.empty or y_final.empty:
            logger.error("清洗后的特征数据为空")
            raise ValueError("清洗后的特征数据为空")

        return X_final, y_final

    def _generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成高级量化特征"""
        # 基础特征
        features = pd.DataFrame({
            'open': df['open'],
            'close': df['close'],
            'high': df['high'],
            'low': df['low'],
            'volume': df['volume'],
            'turnover': df['turnover']
        })

        # 技术指标
        features['bollinger_band'] = self._calculate_bollinger_band(df['close'])

        # 波动率特征
        features['volatility_5d'] = df['close'].pct_change().rolling(5).std()
        features['volatility_20d'] = df['close'].pct_change().rolling(20).std()

        # 量价关系
        features['volume_price_divergence'] = (
                df['volume'].pct_change(5) -
                df['close'].pct_change(5)
        )

        # # 时间序列特征
        # features['day_of_week'] = df['date'].dt.dayofweek
        # features['month'] = df['date'].dt.month

        return features

    def _get_search_spaces(self) -> list:
        """定义分层参数搜索空间"""
        return [{
            # SVM参数空间
            'stacking_model__svm__C': Real(0.1, 100, prior='log-uniform'),
            'stacking_model__svm__gamma': Real(1e-5, 1, prior='log-uniform'),
            'stacking_model__svm__kernel': ['rbf', 'sigmoid', 'poly'],

            # 元学习器参数空间
            # 'stacking_model__final_estimator__n_estimators': Integer(50, 200),
            'stacking_model__final_estimator__class_weight': ['balanced', None],
            'stacking_model__final_estimator__C': Real(0.1, 10, prior='log-uniform'),

        }]


    def _log_optimization_results(self, optimizer: BayesSearchCV):
        """增强版优化结果日志记录"""
        # 基础信息记录
        total_duration = pd.Timedelta(seconds=np.sum(optimizer.cv_results_['mean_fit_time']))
        logger.info("\n\n=== 模型优化分析报告 ===")
        logger.info(f"优化时间: (耗时: {total_duration})")

        # 训练数据信息
        X, y = self._prepare_training_data(self.fetch_market_data())
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

        # 参数重要性分析（基于分数变化）
        logger.info("\n[参数敏感度分析]")
        param_importance = {}
        for i, params in enumerate(cv_results['params']):
            for param, value in params.items():
                delta = cv_results['mean_test_balanced_accuracy'][i] - np.mean(
                    cv_results['mean_test_balanced_accuracy'])
                param_importance.setdefault(param, []).append(delta)

        importance_table = []
        for param, deltas in param_importance.items():
            impact = np.mean(deltas)
            importance_table.append((param, impact))

        importance_table.sort(key=lambda x: abs(x[1]), reverse=True)
        for param, impact in importance_table[:5]:
            logger.info(f"{param:40} : {impact:+.4f} (对准确率影响)")

            # 特征重要性记录
        try:
            logger.info("\n[特征重要性 TOP10]")
            stacking_model = optimizer.best_estimator_.named_steps['stacking_model']
            final_estimator = stacking_model.final_estimator_

            # 获取特征名称
            if hasattr(stacking_model, 'get_feature_names_out'):
                feature_names = stacking_model.get_feature_names_out()
            else:
                # 手动构造特征名称（假设基模型为二分类）
                base_models = stacking_model.estimators_
                feature_names = []
                for name, model in base_models:
                    # 假设每个基模型输出2个概率
                    feature_names.extend([f"{name}_proba_0", f"{name}_proba_1"])
                if stacking_model.passthrough:
                    # 添加原始特征名称
                    feature_engineer = self.feature_pipe.named_steps['features']
                    original_features = feature_engineer.REQUIRED_RAW_COLS + (feature_engineer.selected_features or [])
                    feature_names.extend(original_features)

            # 获取特征重要性（兼容不同模型类型）
            if hasattr(final_estimator, 'feature_importances_'):
                importances = final_estimator.feature_importances_
            elif hasattr(final_estimator, 'coef_'):
                # 对逻辑回归等线性模型，取系数绝对值均值
                importances = np.mean(np.abs(final_estimator.coef_), axis=0)
            else:
                raise AttributeError("Final estimator has no feature importances or coefficients")

            # 创建特征重要性DataFrame
            feature_importances = pd.DataFrame({
                'feature': feature_names,
                'importance': importances
            }).sort_values('importance', ascending=False)

            # 记录前10个重要特征
            for idx, row in feature_importances.head(10).iterrows():
                logger.info(f"{row['feature']:30} : {row['importance']:.4f}")

        except Exception as e:
            logger.warning("特征重要性提取失败: %s", str(e))

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

    def generate_trading_signals(self, confidence_threshold: float = 0.68) -> pd.DataFrame:
        """
        生成交易信号，包含完整的信号生成流程

        参数:
            confidence_threshold: 模型预测置信度阈值，默认0.68

        返回:
            包含交易信号的DataFrame
        """
        try:
            # 1. 获取市场数据
            df = self.fetch_market_data(refresh=True)

            # 验证数据完整性
            required_cols = self.feature_pipe.named_steps['features'].REQUIRED_RAW_COLS
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                raise ValueError(f"缺失必要数据列: {missing}")
            if df.empty:
                logger.warning("市场数据为空，无法生成信号")
                return pd.DataFrame()

            # 2. 特征工程处理
            X = self.feature_pipe.transform(df)

            # 确保X是DataFrame格式
            if isinstance(X, np.ndarray):
                feature_engineer = self.feature_pipe.named_steps['features']
                columns = feature_engineer.REQUIRED_RAW_COLS + (feature_engineer.selected_features or [])
                X = pd.DataFrame(X, columns=columns, index=df.index)

            # 3. 模型预测
            proba = self.model.predict_proba(X)[:, 1]  # 上涨概率
            predictions = (proba >= confidence_threshold).astype(int)

            # 4. 生成基础信号
            signals = self._generate_raw_signals(df, proba, predictions)
            if signals.empty:
                logger.warning("生成的交易信号为空")
                return pd.DataFrame()

            # 5. 信号增强处理
            signals = self._enhance_signals(signals, df)

            # 6. 应用风险控制
            signals = self._apply_risk_management(signals, df)

            # 7. 技术指标确认
            signals = self._add_technical_confirmations(signals, df)

            # 8. 信号验证
            signals = self._validate_signals(signals)

            # 9. 信号质量评估
            signals = self._evaluate_signal_quality(signals, df)

            # # 10. 保存信号
            # if not signals.empty:
            #     self._save_signals(signals)

            return signals

        except Exception as e:
            logger.error(f"信号生成失败: {str(e)}")
            raise

    def _evaluate_signal_quality(self, signals: pd.DataFrame, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        评估信号质量并过滤低质量信号

        参数:
            signals: 交易信号DataFrame
            market_data: 市场数据DataFrame

        返回:
            过滤后的高质量信号DataFrame
        """
        if signals.empty:
            return signals

        # 1. 计算信号质量指标
        signals['signal_quality'] = 0.0

        # 2. 基于技术指标的质量评估
        if 'RSI' in market_data.columns:
            rsi = market_data['RSI']
            signals.loc[signals['signal_type'] == 'BUY', 'signal_quality'] += (
                                                                                      (rsi > 30) & (rsi < 70)
                                                                              # RSI在合理区间
                                                                              ).astype(float) * 0.2

        # 3. 基于成交量的质量评估
        volume_ma = market_data['volume'].rolling(20).mean()
        signals.loc[signals['signal_type'] == 'BUY', 'signal_quality'] += (
                                                                                  market_data['volume'] > volume_ma
                                                                          # 成交量大于20日均量
                                                                          ).astype(float) * 0.2

        # 4. 基于趋势的质量评估
        price_ma = market_data['close'].rolling(20).mean()
        signals.loc[signals['signal_type'] == 'BUY', 'signal_quality'] += (
                                                                                  market_data['close'] > price_ma
                                                                          # 价格在20日均线上方
                                                                          ).astype(float) * 0.2

        # 5. 基于波动率的质量评估
        volatility = market_data['close'].pct_change().rolling(20).std()
        signals.loc[signals['signal_type'] == 'BUY', 'signal_quality'] += (
                                                                                  volatility < volatility.rolling(
                                                                              20).mean()  # 波动率低于平均水平
                                                                          ).astype(float) * 0.2

        # 6. 基于换手率的质量评估
        turnover_ma = market_data['turnover_rate'].rolling(20).mean()
        signals.loc[signals['signal_type'] == 'BUY', 'signal_quality'] += (
                                                                                  market_data[
                                                                                      'turnover_rate'] > turnover_ma
                                                                          # 换手率高于平均水平
                                                                          ).astype(float) * 0.2

        # 7. 过滤低质量信号
        quality_threshold = 0.0  # 质量阈值
        signals = signals[signals['signal_quality'] >= quality_threshold]

        # 8. 记录信号质量统计
        if not signals.empty:
            logger.info(f"信号质量统计:")
            logger.info(f"平均质量分数: {signals['signal_quality'].mean():.2f}")
            logger.info(f"高质量信号数量: {len(signals)}")
            logger.info(f"最高质量分数: {signals['signal_quality'].max():.2f}")
            logger.info(f"最低质量分数: {signals['signal_quality'].min():.2f}")

        return signals

    def _generate_raw_signals(self, df: pd.DataFrame, proba: np.ndarray, predictions: np.ndarray) -> pd.DataFrame:
        """
        生成基础交易信号框架

        参数:
            df: 市场数据DataFrame
            proba: 模型预测概率
            predictions: 模型预测结果

        返回:
            包含基础信号的DataFrame
        """
        # 验证必要的列是否存在
        required_columns = ['close', 'low', 'high', 'volume', 'turnover_rate']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"数据缺少必要的列: {missing_columns}")
            raise ValueError(f"数据缺少必要的列: {missing_columns}")

        # 检查输入数据是否为空
        if df.empty or len(proba) == 0 or len(predictions) == 0:
            logger.warning("生成信号时输入数据为空")
            return pd.DataFrame()

        # 初始化信号DataFrame
        signals = pd.DataFrame({
            'date': df.index,
            'close_price': df['close'],
            'low': df['low'],
            'high': df['high'],
            'prediction': predictions,
            'confidence': proba,
            'signal_type': 'HOLD',
            'position_size': 0.0,
            'stop_loss': None,
            'take_profit': None,
            'holding_period': 5
        }, index=df.index)

        # 计算技术指标
        # 1. 移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()

        # 2. 成交量指标
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma10'] = df['volume'].rolling(window=10).mean()
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()

        # 3. 换手率指标
        df['turnover_ma5'] = df['turnover_rate'].rolling(window=5).mean()
        df['turnover_ma10'] = df['turnover_rate'].rolling(window=10).mean()
        df['turnover_ma20'] = df['turnover_rate'].rolling(window=20).mean()

        # 4. 波动率指标
        # 检查输入数据是否为空
        if df.empty or len(proba) == 0 or len(predictions) == 0:
            logger.warning("生成信号时输入数据为空")
            return pd.DataFrame()

        # 验证换手率数据
        if df['turnover_rate'].isnull().any():
            logger.warning("换手率数据存在空值，将使用0填充")
            df['turnover_rate'] = df['turnover_rate'].fillna(0)

        # 计算换手率相关指标
        turnover_ma3 = df['turnover_rate'].rolling(3, min_periods=1).mean()
        turnover_ma5 = df['turnover_rate'].rolling(5, min_periods=1).mean()
        turnover_ma10 = df['turnover_rate'].rolling(10, min_periods=1).mean()
        turnover_ma20 = df['turnover_rate'].rolling(20, min_periods=1).mean()

        # 计算换手率变化率
        turnover_change = df['turnover_rate'].pct_change()
        turnover_change_ma3 = turnover_change.rolling(3, min_periods=1).mean()
        turnover_change_ma5 = turnover_change.rolling(5, min_periods=1).mean()

        # 计算换手率标准差
        turnover_std = df['turnover_rate'].rolling(20, min_periods=1).std()

        # 计算换手率相对强度
        turnover_rs = df['turnover_rate'] / turnover_ma20.replace(0, 1e-8)  # 避免除以0

        # 优化买入信号条件
        volume_ma = df['volume'].rolling(5, min_periods=1).mean()
        trend_cond = df['close'] > df['close'].rolling(20).mean()
        volatility_cond = df['close'].pct_change().rolling(20).std() < 0.03

        # 换手率条件
        turnover_cond1 = df['turnover_rate'] > turnover_ma3  # 当前换手率高于3日均线
        turnover_cond2 = turnover_rs > 1  # 换手率相对强度大于1.0
        turnover_cond3 = turnover_change_ma3 > 0  # 换手率变化趋势向上
        turnover_cond4 = df['turnover_rate'] > turnover_std  # 当前换手率高于标准差

        # # 综合买入条件
        buy_mask = (
                (predictions == 1) &
                turnover_cond1 &  # 换手率条件1
                turnover_cond2 &  # 换手率条件2
                turnover_cond3 &  # 换手率条件3
                turnover_cond4  # 换手率条件4
        )  # 模型预测为上涨
        # buy_mask = (
        #     (predictions == 1) &  # 模型预测为上涨
        #     (df['volume'] > volume_ma) &  # 成交量大于5日均量
        #     trend_cond &  # 价格趋势向上
        #     volatility_cond &  # 波动率适中
        #     turnover_cond1 &  # 换手率条件1
        #     turnover_cond2 &  # 换手率条件2
        #     turnover_cond3 &  # 换手率条件3
        #     turnover_cond4  # 换手率条件4
        # )

        # 根据换手率动态调整仓位
        signals.loc[buy_mask, 'signal_type'] = 'BUY'
        signals.loc[buy_mask, 'position_size'] = np.clip(
            turnover_rs[buy_mask] * 0.2,  # 基础仓位系数
            0.1,  # 最小仓位
            0.5  # 最大仓位
        )

        # 调试输出
        logger.info(f"预测为1的数量: {sum(predictions == 1)}")
        logger.info(f"成交量高于5日均线的数量: {sum(df['volume'] > volume_ma)}")
        logger.info(f"价格高于20日均线的数量: {sum(trend_cond)}")
        logger.info(f"波动率低于3%的数量: {sum(volatility_cond)}")
        logger.info(f"换手率高于3日均线的数量: {sum(turnover_cond1)}")
        logger.info(f"换手率相对强度大于1的数量: {sum(turnover_cond2)}")
        logger.info(f"换手率变化趋势向上的数量: {sum(turnover_cond3)}")
        logger.info(f"换手率高于标准差的数量: {sum(turnover_cond4)}")
        logger.info(f"满足所有买入条件的数量: {sum(buy_mask)}")

        return signals

    def _enhance_signals(self, signals: pd.DataFrame, market_data: pd.DataFrame) -> pd.DataFrame:
        """信号增强逻辑"""
        return signals


    def _apply_risk_management(self, signals: pd.DataFrame, market_data: pd.DataFrame) -> pd.DataFrame:
        """应用风险控制规则"""
        # 1. 确保数据对齐
        market_data = market_data.copy()
        signals = signals.copy()

        # 3. 合并信号和市场数据
        # signals = signals.join(market_data[['ATR']], how='left')
        # signals['ATR'] = signals['ATR'].fillna(0)

        # 4. 改进的止损逻辑 - 跟踪最高价和回撤
        buy_mask = signals['signal_type'] == 'BUY'

        # 初始化跟踪列
        signals['highest_since_entry'] = np.nan
        signals['current_drawdown'] = np.nan

        # 跟踪持仓状态
        in_position = False
        entry_price = 0
        highest_price = 0

        for i in range(len(signals)):
            if buy_mask.iloc[i] and not in_position:
                # 新买入信号
                entry_price = signals['close_price'].iloc[i]
                highest_price = entry_price
                in_position = True
                signals.loc[signals.index[i], 'highest_since_entry'] = entry_price
                signals.loc[signals.index[i], 'current_drawdown'] = 0
            elif in_position:
                # 更新持仓期间的最高价和回撤
                current_price = signals['close_price'].iloc[i]
                highest_price = max(highest_price, current_price)
                current_drawdown = (highest_price - current_price) / highest_price

                signals.loc[signals.index[i], 'highest_since_entry'] = highest_price
                signals.loc[signals.index[i], 'current_drawdown'] = current_drawdown


        # 5. 设置止盈和固定止损
        signals.loc[buy_mask, 'stop_loss'] = (
                signals.loc[buy_mask, 'close_price'] * 0.95  # 固定5%止损
        )
        signals.loc[buy_mask, 'take_profit'] = (
                signals.loc[buy_mask, 'close_price'] * 1.10  # 固定10%止盈
        )

        # 6. 设置时间止损
        signals.loc[buy_mask, 'time_stop'] = (
                signals.loc[buy_mask].index + pd.Timedelta(days=self.holding_period)
        )

        return signals

    def _validate_signals(self, signals: pd.DataFrame) -> pd.DataFrame:
        """增强版信号验证，包含SELL信号检查"""
        # 原有验证逻辑
        if signals.empty:
            logger.warning("信号验证后数据为空，可能由于日期过滤")
            return signals

        # 新增SELL信号验证
        if 'signal_type' in signals.columns:
            # 检查每个SELL信号是否有对应的BUY信号
            buy_dates = signals[signals['signal_type'] == 'BUY'].index
            sell_dates = signals[signals['signal_type'] == 'SELL'].index

            # 确保SELL信号在BUY信号之后
            for sell_date in sell_dates:
                prev_buys = buy_dates[buy_dates < sell_date]
                if len(prev_buys) == 0:
                    logger.warning(f"发现无效SELL信号: {sell_date} 没有对应的BUY信号")
                    signals.loc[sell_date, 'signal_type'] = 'HOLD'

        # 新增：验证止损止盈值合理性
        if 'stop_loss' in signals.columns and 'take_profit' in signals.columns:
            invalid_stops = signals['stop_loss'] >= signals['close_price']
            invalid_takes = signals['take_profit'] <= signals['close_price']

            if invalid_stops.any():
                logger.warning(f"发现{invalid_stops.sum()}个无效止损设置(止损≥当前价)")
                signals.loc[invalid_stops, 'stop_loss'] = signals.loc[invalid_stops, 'close_price'] * 0.95

            if invalid_takes.any():
                logger.warning(f"发现{invalid_takes.sum()}个无效止盈设置(止盈≤当前价)")
                signals.loc[invalid_takes, 'take_profit'] = signals.loc[invalid_takes, 'close_price'] * 1.05

        return signals

    def _add_technical_confirmations(self, signals: pd.DataFrame, market_data: pd.DataFrame) -> pd.DataFrame:
        """技术指标确认"""
        # 新增：空信号直接返回
        if signals.empty:
            return signals

         # 新增：索引对齐处理
        aligned_data = market_data.reindex(signals.index)


        return signals

    def _get_next_trading_day(self, current_date):
        # 确保 current_date 是 pandas Timestamp 对象
        if not isinstance(current_date, pd.Timestamp):
            current_date = pd.Timestamp(current_date)

        # 确保所有时间戳都是 tz-naive 或都是 tz-aware
        # 这里我们选择将所有时间戳转为 tz-naive
        if current_date.tz is not None:
            current_date = current_date.tz_localize(None)

        # 获取交易日历范围（过去5年到未来1年）
        start_date = current_date - pd.Timedelta(days=365 * 5)
        end_date = current_date + pd.Timedelta(days=365)

        # 获取交易日历
        trading_days = self.exchange.valid_days(start_date=start_date, end_date=end_date)

        # 找到下一个交易日
        for day in trading_days:
            # 确保 day 也是 tz-naive
            if isinstance(day, pd.Timestamp) and day.tz is not None:
                day = day.tz_localize(None)

            if day > current_date:
                return day
        return None

    def backtest_strategy(self,
                          initial_capital: float = 1e6,
                          transaction_cost: float = 0.001,
                          slippage: float = 0.005,
                          risk_free_rate: float = 0.01,
                          holding_period: int = 5) -> dict:
        """
        执行策略回测，评估策略表现（优化版）

        参数:
            initial_capital: 初始资金
            transaction_cost: 交易成本（手续费）
            slippage: 滑点
            risk_free_rate: 无风险利率
            holding_period: 持有期
        """
        self.holding_period = holding_period
        try:
            # 1. 获取交易信号
            signals = self.generate_trading_signals()
            if signals.empty:
                logger.warning("没有生成有效交易信号，无法回测")
                return {}

            # 2. 获取市场数据
            market_data = self.fetch_market_data()

            # 3. 初始化回测变量
            portfolio_value = initial_capital
            position = 0  # 当前持仓数量
            entry_price = 0  # 当前持仓成本价
            entry_date = None  # 记录买入日期
            highest_price = 0  # 持仓期间最高价
            trades = []  # 交易记录
            active_positions = []  # 跟踪所有活跃持仓
            daily_returns = []  # 每日收益率
            max_drawdown = 0  # 最大回撤
            peak_value = initial_capital  # 峰值资金

            # 准备结果DataFrame
            results = pd.DataFrame(index=signals.index)
            results['signal'] = signals['signal_type']
            results['close'] = market_data['close']
            results['portfolio_value'] = portfolio_value
            results['position'] = 0
            results['returns'] = 0.0
            results['drawdown'] = 0.0

            # 4. 执行回测
            in_position = False  # 初始化持仓状态

            for i, (date, row) in enumerate(signals.iterrows()):
                current_price = market_data.loc[date, 'close']

                # 更新峰值和回撤
                if portfolio_value > peak_value:
                    peak_value = portfolio_value
                current_drawdown = (peak_value - portfolio_value) / peak_value
                max_drawdown = max(max_drawdown, current_drawdown)
                results.loc[date, 'drawdown'] = current_drawdown

                # 处理现有持仓
                positions_to_close = []

                # 处理回撤止损
                if in_position:
                    # 更新最高价和当前回撤
                    highest_price = max(highest_price, current_price)
                    current_drawdown = (highest_price - current_price) / highest_price

                    # 动态止损：基于ATR的止损
                    atr = market_data.loc[date, 'ATR'] if 'ATR' in market_data.columns else 0
                    dynamic_stop_level = 0.05 + (atr / current_price) if current_price > 0 else 0.05

                    # 检查止损条件
                    if current_drawdown >= dynamic_stop_level:
                        # 执行止损
                        sell_price = current_price * (1 - slippage)
                        trade_value = position * sell_price * (1 - transaction_cost)
                        portfolio_value += trade_value

                        trades.append({
                            'date': date,
                            'type': 'SELL',
                            'shares': position,
                            'price': sell_price,
                            'cost': trade_value,
                            'exit_reason': 'stop_loss',
                            'holding_days': (date - entry_date).days,
                            'entry_price': entry_price,
                            'profit_pct': (sell_price - entry_price) / entry_price
                        })

                        position = 0
                        in_position = False
                        highest_price = 0
                        continue

                # 处理持有期结束的仓位
                for pos in active_positions:
                    holding_days = (date - pos['entry_date']).days
                    if holding_days >= pos['holding_period']:
                        positions_to_close.append(pos)

                # 平仓达到持有期的仓位
                for pos in positions_to_close:
                    sell_price = current_price * (1 - slippage)
                    trade_value = pos['shares'] * sell_price * (1 - transaction_cost)
                    portfolio_value += trade_value

                    trades.append({
                        'date': date,
                        'type': 'SELL',
                        'shares': pos['shares'],
                        'price': sell_price,
                        'cost': trade_value,
                        'exit_reason': 'time_stop',
                        'holding_days': pos['holding_period'],
                        'entry_price': pos['entry_price'],
                        'profit_pct': (sell_price - pos['entry_price']) / pos['entry_price']
                    })

                    active_positions.remove(pos)
                    if not active_positions:
                        in_position = False

                # 执行新信号
                if row['signal_type'] == 'BUY' and not in_position:
                    position_size = row['position_size']
                    max_investment = portfolio_value * position_size

                    # 获取下一个交易日
                    next_trading_day = self._get_next_trading_day(date)
                    if next_trading_day is None or next_trading_day not in market_data.index:
                        continue

                    # 使用下一个交易日的收盘价买入
                    buy_price = market_data.loc[next_trading_day, 'close'] * (1 + slippage)
                    shares = int(max_investment / buy_price)

                    if shares > 0:
                        # 执行买入
                        trade_cost = shares * buy_price * (1 + transaction_cost)
                        portfolio_value -= trade_cost

                        # 记录新持仓
                        new_position = {
                            'entry_date': next_trading_day,
                            'shares': shares,
                            'entry_price': buy_price,
                            'holding_period': row['holding_period']
                        }
                        active_positions.append(new_position)
                        in_position = True
                        entry_price = buy_price
                        entry_date = next_trading_day
                        highest_price = buy_price

                        trades.append({
                            'date': next_trading_day,
                            'type': 'BUY',
                            'shares': shares,
                            'price': buy_price,
                            'cost': trade_cost,
                            'exit_reason': None,
                            'holding_days': 0
                        })

                # 更新每日组合价值
                current_position_value = sum(pos['shares'] * current_price for pos in active_positions)
                results.loc[date, 'portfolio_value'] = portfolio_value + current_position_value
                results.loc[date, 'position'] = sum(pos['shares'] for pos in active_positions)

                # 计算日收益率
                if i > 0:
                    prev_value = results.iloc[i - 1]['portfolio_value']
                    curr_value = results.loc[date, 'portfolio_value']
                    daily_return = (curr_value - prev_value) / prev_value
                    results.loc[date, 'returns'] = daily_return
                    daily_returns.append(daily_return)

            if len(trades) < 1:
                return {}

            # 5. 计算绩效指标
            performance = self._calculate_performance(results, risk_free_rate, trades)
            print('performance',performance)
            # 6. 生成分析报告
            analysis_report = self._generate_analysis_report(
                performance=performance,
                trades=trades,
                signals=signals,
                results_df=results
            )

            return {
                'performance': performance,
                'trades': pd.DataFrame(trades),
                'portfolio': results,
                'charts': '',
                'analysis_report': analysis_report,
                'backtest_id': 1,
            }

        except Exception as e:
            logger.error(f"回测执行失败: {str(e)}", exc_info=True)
            raise

    def _generate_analysis_report(self, performance: dict, trades: list,
                                  signals: pd.DataFrame, results_df: pd.DataFrame) -> str:
        """生成详细的文字分析报告"""
        try:
            # 1. 数据验证
            if not performance or not trades:
                return "无法生成报告：缺少必要的性能数据或交易记录"

            # 2. 转换交易记录为DataFrame
            trade_df = pd.DataFrame(trades)
            
            # 3. 计算关键指标
            metrics = self._calculate_key_metrics(performance, trade_df, signals)
            
            # 4. 生成报告主体
            report = self._generate_report_sections(metrics)
            
            # 5. 添加策略评估
            report += self._evaluate_strategy_performance(metrics)
            
            # 6. 添加改进建议
            report += self._generate_improvement_suggestions(metrics)
            
            return report
            
        except Exception as e:
            logger.error(f"生成分析报告时出错: {str(e)}")
            return "报告生成失败，请检查数据完整性"

    def _calculate_performance(self, results_df: pd.DataFrame, risk_free_rate: float, trades: list) -> dict:
        """综合绩效指标计算（优化合并版）"""
        if results_df.empty or 'portfolio_value' not in results_df.columns:
            return {}

        performance = {}
        trade_df = pd.DataFrame(trades)

        # ================== 基础指标计算 ==================
        # 交易统计指标
        buy_signals = len(trade_df[trade_df['type'] == 'BUY'])
        complete_trades = min(
            len(trade_df[trade_df['type'] == 'BUY']),
            len(trade_df[trade_df['type'] == 'SELL'])
        )
        performance.update({
            'buy_signals': buy_signals,
            'complete_trades': complete_trades,
            'execution_rate': complete_trades / buy_signals if buy_signals > 0 else 0
        })

        # 收益指标
        total_return = results_df['portfolio_value'].iloc[-1] / results_df['portfolio_value'].iloc[0] - 1
        daily_returns = results_df['portfolio_value'].pct_change().dropna()
        annualized_return = (1 + total_return) ** (252 / len(daily_returns)) - 1  # 修正年化计算方式

        # 风险指标
        cumulative_value = results_df['portfolio_value']
        drawdown = (cumulative_value / cumulative_value.cummax()) - 1
        max_drawdown = drawdown.min()
        annualized_volatility = daily_returns.std() * np.sqrt(252)

        # ================== 滚动窗口指标计算 ==================
        holding_periods = [5, 10, 20]
        for period in holding_periods:

            # 计算窗口期的年化收益率和波动率
            period_returns = cumulative_value.pct_change(period).dropna()
            if not period_returns.empty:
                annualized_return_period = (1 + period_returns.mean())  ** (252 / period) - 1
                annualized_volatility_period = period_returns.std() * np.sqrt(252 / period)
                sharpe_ratio = (annualized_return_period - risk_free_rate) / annualized_volatility_period if annualized_volatility_period != 0 else 0

                performance.update({
                    f'annualized_return_{period}_day': annualized_return_period,
                    f'sharpe_ratio_{period}_day': sharpe_ratio,
                })

            # 滚动最大回撤
            rolling_dd = cumulative_value.rolling(period).apply(
                lambda x: (x / x.cummax() - 1).min(), raw=False
            )
            performance[f'max_drawdown_{period}_day'] = rolling_dd.min()

            # 窗口收益率计算（修正使用pct_change）
            period_returns = cumulative_value.pct_change(period).dropna()
            if not period_returns.empty:
                # Sortino Ratio计算（修正下行波动率年化）
                downside_returns = period_returns[period_returns < 0]
                downside_volatility = downside_returns.std() * np.sqrt(252 / period) if len(downside_returns) > 0 else 0
                sortino = (
                                      period_returns.mean() * 252 / period - risk_free_rate) / downside_volatility if downside_volatility != 0 else 0

                # Calmar Ratio计算（修正年化收益率）
                annualized_return_period = (1 + period_returns.mean()) ** (252 / period) - 1
                calmar = annualized_return_period / abs(performance[f'max_drawdown_{period}_day']) if performance[
                                                                                                          f'max_drawdown_{period}_day'] != 0 else 0

                # 盈亏比计算（修正窗口计算方式）
                win_rate = (period_returns > 0).mean()
                # 生成交易配对并计算win_rate2
                buy_trades = trade_df[trade_df['type'] == 'BUY']
                valid_trades = 0
                winning_trades = 0
                for idx, buy_trade in buy_trades.iterrows():
                    # 获取买入日期和价格
                    buy_date = buy_trade['date']  # 确保字段名与实际数据一致
                    buy_price = buy_trade['price']
                    # 确认买入日期存在于数据中
                    if buy_date not in results_df.index:
                        continue
                    # 计算卖出日期（第period个交易日）
                    buy_pos = results_df.index.get_loc(buy_date)
                    sell_pos = buy_pos + period
                    if sell_pos >= len(results_df):
                        continue  # 超出数据范围则跳过
                    # sell_date = results_df.index[sell_pos]
                    # 获取卖出价格（假设使用收盘价）
                    sell_price = results_df.iloc[sell_pos]['close']
                    # 统计胜率
                    if sell_price > buy_price:
                        winning_trades += 1
                    valid_trades += 1
                # 计算该周期的胜率
                win_rate2 = winning_trades / valid_trades if valid_trades > 0 else 0.0

                avg_win = period_returns[period_returns > 0].mean()
                avg_loss = period_returns[period_returns <= 0].mean()
                profit_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

                performance.update({
                    f'sortino_ratio_{period}_day': sortino,
                    f'calmar_ratio_{period}_day': calmar,
                    f'profit_ratio_{period}_day': profit_ratio,
                    f'avg_return_{period}_day': period_returns.mean(),
                    f'win_rate_{period}_day': win_rate,
                    f'win_rate2_{period}_day': win_rate2,
                    f'volatility_{period}_day': period_returns.std() * np.sqrt(252 / period)
                })
            else:
                performance.update({f'{k}_{period}_day': 0 for k in [
                    'sortino_ratio', 'calmar_ratio', 'profit_ratio', 'avg_return', 'win_rate', 'volatility'
                ]})

        # ================== 全局风险指标 ==================
        # Sortino/Calmar/Profit Ratio（全局）
        downside_returns = daily_returns[daily_returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        performance.update({
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': (
                                        annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility != 0 else 0,
            'sortino_ratio': (
                                         annualized_return - risk_free_rate) / downside_volatility if downside_volatility != 0 else 0,
            'calmar_ratio': annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0,
            'annualized_volatility': annualized_volatility
        })

        # ================== 交易分析指标 ==================
        if not trade_df.empty:
            # 持仓时间计算
            sell_trades = trade_df[trade_df['type'] == 'SELL']
            hold_times = sell_trades['holding_days'].values if 'holding_days' in sell_trades.columns else np.array([])

            # 盈亏比计算（全局）
            profits = [sell.price / buy.price - 1
                       for buy, sell in zip(trade_df[trade_df['type'] == 'BUY'].iloc[:complete_trades].itertuples(),
                                            trade_df[trade_df['type'] == 'SELL'].iloc[:complete_trades].itertuples())]
            if profits:
                win_rate = sum(np.array(profits) > 0) / len(profits)
                avg_win = np.mean([p for p in profits if p > 0]) if any(p > 0 for p in profits) else 0
                avg_loss = np.mean([p for p in profits if p <= 0]) if any(p <= 0 for p in profits) else 0
                performance.update({
                    'win_rate': win_rate,
                    'profit_ratio': abs(avg_win / avg_loss) if avg_loss != 0 else np.inf,
                    'avg_hold_time': np.mean(hold_times) if hold_times.size > 0 else 0,
                    'positive_days': (daily_returns > 0).sum(),
                    'negative_days': (daily_returns <= 0).sum()
                })

        # 日期相关字段
        performance.update({
            'start_date': results_df.index[0].strftime('%Y-%m-%d'),
            'end_date': results_df.index[-1].strftime('%Y-%m-%d'),
            'trading_days': len(results_df)
        })

        return performance

    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float) -> float:
        """计算Sortino比率"""
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252)
        excess_return = returns.mean() * 252 - risk_free_rate
        return excess_return / downside_volatility

    def _calculate_key_metrics(self, performance: dict, trade_df: pd.DataFrame, signals: pd.DataFrame) -> dict:
        """计算关键指标"""
        metrics = {}
        
        # 1. 基础交易统计
        metrics['total_trades'] = len(trade_df[trade_df['type'] == 'BUY'])
        metrics['winning_trades'] = len(trade_df[trade_df['profit_pct'] > 0])
        metrics['win_rate'] = metrics['winning_trades'] / metrics['total_trades'] if metrics['total_trades'] > 0 else 0
        
        # 2. 收益指标
        metrics['total_return'] = performance.get('total_return', 0)
        metrics['annualized_return'] = performance.get('annualized_return', 0)
        
        # 3. 风险指标
        metrics['max_drawdown'] = performance.get('max_drawdown', 0)
        metrics['sharpe_ratio'] = performance.get('sharpe_ratio', 0)
        
        # 4. 交易质量指标
        metrics['avg_hold_time'] = performance.get('avg_hold_time', 0)
        metrics['profit_factor'] = self._calculate_profit_factor(trade_df)
        
        return metrics

    def _generate_report_sections(self, metrics: dict) -> str:
        """生成报告各个部分"""
        report = []
        
        # 1. 基本信息
        report.append("=== 策略回测分析报告 ===")
        report.append("\n一、基本信息")
        report.append(f"- 回测期间: {metrics.get('start_date', 'N/A')} 至 {metrics.get('end_date', 'N/A')}")
        report.append(f"- 总交易次数: {metrics['total_trades']}")
        report.append(f"- 胜率: {metrics['win_rate']:.2%}")
        
        # 2. 收益分析
        report.append("\n二、收益分析")
        report.append(f"- 总收益率: {metrics['total_return']:.2%}")
        report.append(f"- 年化收益率: {metrics['annualized_return']:.2%}")
        
        # 3. 风险分析
        report.append("\n三、风险分析")
        report.append(f"- 最大回撤: {metrics['max_drawdown']:.2%}")
        report.append(f"- 夏普比率: {metrics['sharpe_ratio']:.2f}")
        
        return "\n".join(report)

    def _evaluate_strategy_performance(self, metrics: dict) -> str:
        """评估策略表现"""
        evaluation = []
        
        # 1. 收益评估
        if metrics['annualized_return'] > 0.15:
            evaluation.append("★ 收益表现优秀")
        elif metrics['annualized_return'] > 0.1:
            evaluation.append("★ 收益表现良好")
        else:
            evaluation.append("★ 收益表现一般")
        
        # 2. 风险评估
        if metrics['max_drawdown'] < 0.1:
            evaluation.append("★ 风险控制优秀")
        elif metrics['max_drawdown'] < 0.2:
            evaluation.append("★ 风险控制良好")
        else:
            evaluation.append("★ 风险控制需要改进")
        
        return "\n".join(evaluation)

    def _generate_improvement_suggestions(self, metrics: dict) -> str:
        """生成改进建议"""
        suggestions = []
        
        # 1. 收益相关建议
        if metrics['annualized_return'] < 0.1:
            suggestions.append("- 考虑优化选股策略，提高收益潜力")
        
        # 2. 风险相关建议
        if metrics['max_drawdown'] > 0.2:
            suggestions.append("- 加强风险控制，降低最大回撤")
        
        # 3. 交易质量建议
        if metrics['win_rate'] < 0.4:
            suggestions.append("- 提高信号质量，增加胜率")
        
        return "\n".join(suggestions)

    def _calculate_profit_factor(self, trade_df: pd.DataFrame) -> float:
        """
        计算盈亏比
        
        参数:
            trade_df: 交易记录DataFrame
            
        返回:
            float: 盈亏比
        """
        if trade_df.empty:
            return 0.0
            
        # 分离盈利和亏损交易
        profitable_trades = trade_df[trade_df['profit_pct'] > 0]
        losing_trades = trade_df[trade_df['profit_pct'] <= 0]
        
        # 计算总盈利和总亏损
        total_profit = profitable_trades['profit_pct'].sum() if not profitable_trades.empty else 0
        total_loss = abs(losing_trades['profit_pct'].sum()) if not losing_trades.empty else 0
        
        # 计算盈亏比
        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0
            
        return total_profit / total_loss

class EnhancedMarketAnalyzerWithLoader(EnhancedMarketAnalyzer):
    def load_model(self):
        model_path = f"models/{self.symbol}_optimized_model.pkl"
        saved_data = joblib.load(model_path)

        # 恢复模型
        self.model = saved_data['model']

        # 恢复特征工程状态
        fe = self.feature_pipe.named_steps['features']
        fe.selected_features = saved_data['feature_engineer_state']['selected_features']
        fe.lookback_windows = saved_data['feature_engineer_state']['lookback_windows']
        fe.ta_config = saved_data['feature_engineer_state']['ta_config']

        # 恢复scaler状态
        scaler = self.feature_pipe.named_steps['scaler']
        if 'quantiles_' in saved_data['data_stats']:
            scaler.quantiles_ = saved_data['data_stats']['quantiles_']
            scaler.references_ = saved_data['data_stats']['references_']
        else:
            scaler.mean_ = saved_data['data_stats']['mean_']
            scaler.scale_ = saved_data['data_stats']['scale_']



if __name__ == "__main__":

    symbol = '600519'

    # try:
    # 示例使用
    analyzer = EnhancedMarketAnalyzer(symbol)

    # 数据获取与预处理
    data = analyzer.fetch_market_data()

    # 模型训练与优化
    analyzer.optimize_model(n_iter=1)


    report = analyzer.backtest_strategy(holding_period=3)
    print(report)
    # except Exception as e:
    #     # 记录错误日志
    #     error_msg = f"{symbol} 分析失败: {str(e)}"
    #     print(error_msg)
    #     with open("analysis_error.log", "a") as f:
    #         f.write(f"{pd.Timestamp.now()} {error_msg}\n")




