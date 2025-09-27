# -*- coding: utf-8 -*-
"""
EDE模块性能优化配置
"""

# 字段映射缓存配置
FIELD_MAPPING_CACHE_CONFIG = {
    "max_cache_size": 100,  # 最大缓存条目数
    "cache_ttl": 3600,      # 缓存生存时间（秒）
    "enable_precompilation": True,  # 启用预编译优化
}

# 数据处理性能配置
DATA_PROCESSING_CONFIG = {
    "batch_size": 1000,     # 批处理大小
    "enable_parallel_processing": True,  # 启用并行处理
    "max_workers": 4,       # 最大工作线程数
    "memory_threshold": 100 * 1024 * 1024,  # 内存阈值（100MB）
}

# 日志性能配置
LOG_PERFORMANCE_CONFIG = {
    "enable_performance_logging": True,
    "log_slow_operations": True,
    "slow_operation_threshold": 1.0,  # 慢操作阈值（秒）
    "enable_field_mapping_stats": True,
}

# 缓存策略配置
CACHE_STRATEGY_CONFIG = {
    "enable_field_mapping_cache": True,
    "enable_data_preprocessing_cache": True,
    "cache_compression": True,
    "cache_serialization": "json",  # json, pickle, msgpack
}

# 前端性能配置
FRONTEND_PERFORMANCE_CONFIG = {
    "enable_virtual_scrolling": True,
    "virtual_scroll_threshold": 1000,  # 虚拟滚动阈值
    "enable_field_name_optimization": True,
    "enable_batch_field_matching": True,
}

# 性能监控配置
PERFORMANCE_MONITORING_CONFIG = {
    "enable_metrics_collection": True,
    "metrics_retention_days": 7,
    "enable_alerting": True,
    "performance_alert_threshold": 5.0,  # 性能告警阈值（秒）
}
