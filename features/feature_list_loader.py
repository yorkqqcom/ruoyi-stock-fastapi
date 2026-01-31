#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特征列表加载器
用于加载和解析特征配置文件
"""

import os
from pathlib import Path
from typing import List, Set, Optional
from utils.logger import setup_logger

logger = setup_logger()


def load_feature_list_from_file(file_path: str) -> Set[str]:
    """
    从文件加载特征列表
    
    Args:
        file_path: 特征配置文件路径
        
    Returns:
        特征名称集合（格式：category__feature_name）
    """
    feature_set = set()
    
    # 解析文件路径
    if not os.path.isabs(file_path):
        # 相对路径，从项目根目录查找
        project_root = Path(__file__).parent.parent.parent
        file_path = project_root / file_path
    else:
        file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"特征配置文件不存在: {file_path}")
        return feature_set
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                raw = line.strip()
                # 跳过空行和注释行
                if not raw or raw.startswith('#'):
                    continue
                
                # 支持格式: category__feature_name 或 category,feature_name
                if '__' in raw:
                    parts = raw.split('__', 1)
                    if len(parts) == 2 and all(parts):
                        category = parts[0].strip()
                        feature_name = parts[1].strip()
                        feature_key = f"{category}__{feature_name}"
                        feature_set.add(feature_key)
                elif ',' in raw:
                    parts = raw.split(',', 1)
                    if len(parts) == 2 and all(parts):
                        category = parts[0].strip()
                        feature_name = parts[1].strip()
                        feature_key = f"{category}__{feature_name}"
                        feature_set.add(feature_key)
                else:
                    logger.warning(f"无法解析特征配置行，需使用 'category__feature' 或 'category,feature' 形式: {raw}")
        
        logger.info(f"从 {file_path} 加载了 {len(feature_set)} 个特征")
        return feature_set
        
    except Exception as e:
        logger.error(f"加载特征配置文件失败: {e}")
        return feature_set


def normalize_feature_name(feature_name: str, category: str) -> str:
    """
    规范化特征名称，生成完整的特征键
    
    Args:
        feature_name: 原始特征名称（可能包含或不包含前缀）
        category: 特征类别
        
    Returns:
        规范化后的特征键（格式：category__feature_name）
    """
    # 如果特征名已经包含类别前缀，直接返回
    if feature_name.startswith(f"{category}_"):
        return f"{category}__{feature_name}"
    else:
        # 添加类别前缀
        return f"{category}__{category}_{feature_name}"


def should_include_feature(feature_key: str, allowed_features: Optional[Set[str]] = None) -> bool:
    """
    判断是否应该包含某个特征
    
    Args:
        feature_key: 特征键（格式：category__feature_name）
        allowed_features: 允许的特征集合，如果为None则包含所有特征
        
    Returns:
        是否应该包含该特征
    """
    if allowed_features is None:
        return True
    
    return feature_key in allowed_features


def get_default_feature_list_path() -> str:
    """
    获取默认的特征列表文件路径
    
    Returns:
        默认特征列表文件路径
    """
    project_root = Path(__file__).parent.parent.parent
    return str(project_root / "config" / "train" / "featurelist_balanced_90pct_293.txt")

