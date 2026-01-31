#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互特征构造器
专门负责量价、波动率等特征之间的交互项生成
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from utils.logger import setup_logger

logger = setup_logger()


class InteractionFeatures:
    """特征交互项"""

    DEFAULT_FEATURE_NAMES = [
        "volume_price_trend",
        "vol_volume_ratio",
    ]

    @staticmethod
    def create_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
        """创建特征交互项"""
        if df is None or df.empty:
            logger.debug("交互特征构造器收到空的DataFrame，返回空结果")
            return pd.DataFrame(index=df.index if df is not None else None)

        interactions: Dict[str, pd.Series] = {}

        try:
            # 量价交互特征
            if {"volume", "close"}.issubset(df.columns):
                close_pct_change = df["close"].pct_change().fillna(0.0)
                interactions["volume_price_trend"] = (
                    df["volume"].fillna(0.0) * close_pct_change
                )

            # 波动率-成交量交互
            if {"volatility", "volume"}.issubset(df.columns):
                rolling_volume_mean = (
                    df["volume"].rolling(20, min_periods=1).mean().replace(0, np.nan)
                )
                interactions["vol_volume_ratio"] = (
                    df["volatility"].fillna(0.0) / rolling_volume_mean
                ).replace([np.inf, -np.inf], np.nan)

            if not interactions:
                return pd.DataFrame(index=df.index)

            interaction_df = pd.DataFrame(interactions, index=df.index)
            interaction_df = interaction_df.fillna(0.0)
            return interaction_df

        except Exception as exc:  # pragma: no cover - 记录异常
            logger.error(f"生成交互特征失败: {exc}")
            return pd.DataFrame(index=df.index)

    @classmethod
    def get_feature_names(cls) -> List[str]:
        """返回交互特征名称列表"""
        return cls.DEFAULT_FEATURE_NAMES[:]

