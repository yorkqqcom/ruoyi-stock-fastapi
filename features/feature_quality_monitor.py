#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特征质量监控模块
提供特征缺失、方差、异常值与漂移监控能力
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy import stats

from utils.logger import setup_logger

logger = setup_logger()


class FeatureQualityMonitor:
    """特征质量监控"""

    def evaluate_feature_quality(self, features: pd.DataFrame) -> Dict[str, Any]:
        """评估特征质量"""
        quality_report: Dict[str, Any] = {}

        if features is None or features.empty:
            logger.debug("特征质量评估收到空DataFrame")
            return quality_report

        extended_features = self._prepare_evaluation_window(features)
        numeric_features = extended_features.select_dtypes(include=[np.number])
        if numeric_features.empty:
            logger.debug("特征质量评估没有检测到数值特征")
            return quality_report

        for col in numeric_features.columns:
            series = numeric_features[col]
            valid_series = series.dropna()
            sample_size = len(valid_series)

            missing_rate = 1.0 - (sample_size / len(series)) if len(series) else 1.0
            variance = float(valid_series.var()) if sample_size > 1 else 0.0

            if sample_size > 1:
                q1 = valid_series.quantile(0.25)
                q3 = valid_series.quantile(0.75)
                iqr = q3 - q1
                if iqr == 0:
                    outlier_mask = pd.Series(False, index=valid_series.index)
                else:
                    lower = q1 - 1.5 * iqr
                    upper = q3 + 1.5 * iqr
                    outlier_mask = (valid_series < lower) | (valid_series > upper)
                outlier_rate = float(outlier_mask.mean()) if sample_size else 0.0
            else:
                outlier_rate = 0.0

            variance_flag = self._evaluate_variance_flag(valid_series)
            baseline_score = (1 - missing_rate) * variance_flag * (1 - outlier_rate)
            quality_score = max(0.0, min(1.0, baseline_score))

            quality_report[col] = {
                "missing_rate": float(missing_rate),
                "variance": variance,
                "outlier_rate": float(outlier_rate),
                "quality_score": float(quality_score),
                "sample_size": sample_size,
            }

        return quality_report

    def detect_feature_drift(
        self,
        current_features: pd.DataFrame,
        historical_features: pd.DataFrame,
    ) -> Dict[str, float]:
        """检测特征漂移"""

        drift_scores: Dict[str, float] = {}

        if current_features is None or current_features.empty:
            return drift_scores

        if historical_features is None or historical_features.empty:
            return drift_scores

        numeric_cols = set(current_features.select_dtypes(include=[np.number]).columns)
        numeric_cols &= set(historical_features.select_dtypes(include=[np.number]).columns)

        if not numeric_cols:
            return drift_scores

        for col in numeric_cols:
            cur_series = current_features[col].dropna()
            hist_series = historical_features[col].dropna()

            # 至少需要两个有效样本进行KS检验
            if len(cur_series) < 2 or len(hist_series) < 2:
                drift_scores[col] = 1.0
                continue

            try:
                ks_stat, p_value = stats.ks_2samp(cur_series, hist_series)
                drift_scores[col] = float(p_value)
            except Exception as exc:  # pragma: no cover - SciPy异常
                logger.warning(f"特征漂移检测失败 {col}: {exc}")
                drift_scores[col] = 1.0

        return drift_scores

    def _prepare_evaluation_window(self, features: pd.DataFrame, min_window: int = 5) -> pd.DataFrame:
        """
        针对质量评估准备时间窗口，将单行数据扩展为近 min_window 行历史，避免单样本导致方差恒为零。
        如果传入本身包含多行，则直接返回原数据。
        """
        if features.shape[0] >= min_window or "trade_date" not in features.columns:
            return features

        try:
            extended = features.sort_values("trade_date").tail(min_window)
            return extended.reset_index(drop=True)
        except Exception as exc:
            logger.warning(f"构建质量评估窗口失败，使用原始数据: {exc}")
            return features

    def _evaluate_variance_flag(self, series: pd.Series, min_samples: int = 5, min_variance: float = 1e-6) -> float:
        """
        对方差进行更稳健的判定：
        - 样本数小于 min_samples 时放宽约束，返回 1.0；
        - 对离散值进行出现频率判断，避免罕见事件被误判；
        - 其他情形按最小方差阈值判断。
        """
        valid_series = series.dropna()
        sample_size = len(valid_series)
        if sample_size == 0:
            return 0.0
        if sample_size < min_samples:
            return 1.0

        unique_values = valid_series.unique()
        if len(unique_values) <= 3:
            counts = valid_series.value_counts(normalize=True)
            dominant_ratio = counts.iloc[0]
            if dominant_ratio >= 0.999:
                return 0.2
            if dominant_ratio >= 0.95:
                return 0.5
            return 1.0

        variance = float(valid_series.var())
        return 1.0 if variance > min_variance else 0.0

