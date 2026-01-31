#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版日志工具，仅为离线工具脚本提供最基本的日志能力。
"""

import logging
from typing import Optional

_LOGGER: Optional[logging.Logger] = None


def setup_logger(name: str = "feature_logger") -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    _LOGGER = logger
    return logger

