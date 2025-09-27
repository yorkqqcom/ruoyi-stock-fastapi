# -- coding: utf-8 --
from __future__ import annotations

from typing import Any, Dict, List, Optional
import asyncio
import time

try:
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover
    ak = None  # 延迟到运行时检查

import pandas as pd  # type: ignore
import numpy as np  # type: ignore

from user_module.services.ede_cache_service import get_cache_service
from utils.log_util import logger, log_performance


class AkshareDispatcher:
    """根据配置动态调用 akshare，并按字段映射输出统一结构。"""
    
    # 类级别的字段映射缓存
    _field_mapping_cache: Dict[str, Dict[str, str]] = {}

    @staticmethod
    def _clean_nan_values(data: Any) -> Any:
        """
        递归清理数据中的nan值，确保JSON序列化兼容
        
        Args:
            data: 需要清理的数据
            
        Returns:
            清理后的数据
        """
        if isinstance(data, dict):
            return {k: AkshareDispatcher._clean_nan_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AkshareDispatcher._clean_nan_values(item) for item in data]
        elif isinstance(data, pd.Series):
            return data.replace({pd.NA: None, pd.NaT: None}).where(pd.notnull(data), None).tolist()
        elif isinstance(data, (np.floating, float)) and (np.isnan(data) or np.isinf(data)):
            return None
        elif isinstance(data, (np.integer, int)) and np.isnan(data):
            return None
        else:
            return data

    @staticmethod
    @log_performance
    async def dispatch(config: Dict[str, Any], params: Dict[str, Any], control: Optional[Dict[str, Any]] = None, config_key: str = None) -> List[Dict[str, Any]]:
        if ak is None:
            raise RuntimeError("akshare 未安装或导入失败")

        method_name: str = config.get("akshare", {}).get("method")
        if not method_name:
            raise ValueError("配置缺少 akshare.method")

        # 检查缓存
        try:
            cache_service = await get_cache_service()
            cached_data = await cache_service.get_cached_akshare_data(method_name, params, config_key)
            if cached_data is not None:
                logger.info(f"使用缓存数据: {config_key or method_name}")
                # 应用个股代码过滤
                if control and control.get("filter_symbols"):
                    return AkshareDispatcher._apply_symbol_filter(cached_data, control["filter_symbols"])
                return cached_data
        except Exception as e:
            logger.warning(f"获取缓存失败: {e}")

        ak_params_def: Dict[str, Any] = config.get("akshare", {}).get("params", {})
        # 组装 akshare 入参（默认值与透传）
        call_kwargs: Dict[str, Any] = {}
        for name, meta in ak_params_def.items():
            if name in params and params[name] is not None:
                call_kwargs[name] = params[name]
            elif "default" in meta:
                call_kwargs[name] = meta["default"]

        # 容错：透传额外参数
        for k, v in params.items():
            if k not in call_kwargs and v is not None:
                call_kwargs[k] = v

        # 调用 akshare（同步转异步）
        df: pd.DataFrame = await asyncio.to_thread(AkshareDispatcher._invoke_akshare, method_name, call_kwargs)

        # 统一为列表字典
        if df is None:
            return []
        if isinstance(df, pd.DataFrame):
            # 处理DataFrame中的nan值，将其替换为None以确保JSON序列化兼容
            df_cleaned = df.replace({pd.NA: None, pd.NaT: None})
            df_cleaned = df_cleaned.where(pd.notnull(df_cleaned), None)
            records: List[Dict[str, Any]] = df_cleaned.to_dict(orient="records")
        else:
            # 某些接口可能返回列表/字典
            if isinstance(df, list):
                records = list(df)
            elif isinstance(df, dict):
                records = [df]
            else:
                records = []
        
        # 递归清理所有记录中的nan值
        records = AkshareDispatcher._clean_nan_values(records)

        # 字段映射与重命名 - 使用优化的方法
        field_map: Dict[str, str] = config.get("mapping", {}).get("fields", {}) or {}
        logger.debug(f"字段映射配置: {field_map}")
        
        if field_map:
            records = AkshareDispatcher._optimized_field_mapping(records, field_map, config_key or method_name)
        else:
            logger.warning("字段映射配置为空，保留原始数据")

        # 缓存原始数据（不包含个股过滤）
        try:
            cache_service = await get_cache_service()
            await cache_service.cache_akshare_data(method_name, params, records, config_key)
            logger.info(f"数据已缓存: {config_key or method_name}")
        except Exception as e:
            logger.warning(f"缓存数据失败: {e}")

        # 个股代码过滤
        if control and control.get("filter_symbols"):
            records = AkshareDispatcher._apply_symbol_filter(records, control["filter_symbols"])

        # 简单转换：日期/数值（如配置需要，可扩展）
        # 略，保留原样，前端按需格式化

        return records

    @staticmethod
    def _apply_symbol_filter(records: List[Dict[str, Any]], filter_symbols: List[str]) -> List[Dict[str, Any]]:
        """应用个股代码过滤"""
        if not isinstance(filter_symbols, list) or not filter_symbols:
            return records
        
        # 尝试多种可能的股票代码字段名
        symbol_fields = ["symbol", "股票代码", "code", "stock_code", "ts_code"]
        filtered_records = []
        
        for record in records:
            # 查找股票代码字段
            symbol_value = None
            for field in symbol_fields:
                if field in record and record[field]:
                    symbol_value = str(record[field]).strip()
                    break
            
            # 如果找到股票代码且在被过滤列表中，则保留
            if symbol_value and symbol_value in filter_symbols:
                filtered_records.append(record)
        
        return filtered_records

    @staticmethod
    def _invoke_akshare(method_name: str, kwargs: Dict[str, Any]):
        func = getattr(ak, method_name, None)
        if func is None:
            raise AttributeError(f"akshare 不存在方法: {method_name}")
        return func(**kwargs)
    
    @staticmethod
    @log_performance
    def _optimized_field_mapping(records: List[Dict[str, Any]], field_map: Dict[str, str], config_key: str = None) -> List[Dict[str, Any]]:
        """
        优化的字段映射方法，使用缓存和批量处理
        """
        if not field_map or not records:
            return records
            
        # 使用缓存机制避免重复计算
        cache_key = f"{config_key}_field_mapping" if config_key else "default_field_mapping"
        if cache_key not in AkshareDispatcher._field_mapping_cache:
            # 预编译字段映射，只保留存在的字段
            optimized_field_map = {src: dst for src, dst in field_map.items() if any(src in row for row in records)}
            AkshareDispatcher._field_mapping_cache[cache_key] = optimized_field_map

            # 统计缺失与可用字段，增强可诊断性日志
            present_src_fields = list(optimized_field_map.keys())
            missing_src_fields = [src for src in field_map.keys() if src not in present_src_fields]
            # 提取样例记录中出现的字段（截断避免过长日志）
            sample_keys = []
            try:
                # 收集最多前3条记录的键并去重
                collected = []
                for r in records[:3]:
                    collected.extend(list(r.keys()))
                # 去重并截断
                sample_keys = list(dict.fromkeys(collected))[:30]
            except Exception:
                sample_keys = []

            logger.debug(
                "字段映射缓存已构建 | config_key=%s | 映射数=%d | 缺失数=%d | 缺失示例=%s | 样例可用键=%s",
                config_key,
                len(optimized_field_map),
                len(missing_src_fields),
                missing_src_fields[:10],
                sample_keys
            )
        else:
            optimized_field_map = AkshareDispatcher._field_mapping_cache[cache_key]
            logger.debug("使用缓存的字段映射 | config_key=%s | 映射数=%d", config_key, len(optimized_field_map))
        
        if not optimized_field_map:
            # 统计诊断信息，帮助快速定位
            requested_fields = list(field_map.keys()) if field_map else []
            sample_keys = []
            try:
                collected = []
                for r in records[:3]:
                    collected.extend(list(r.keys()))
                sample_keys = list(dict.fromkeys(collected))[:30]
            except Exception:
                sample_keys = []

            logger.warning(
                "未找到可映射字段，已保留原始数据 | config_key=%s | 请求字段数=%d | 请求字段示例=%s | 样例可用键=%s | 记录数=%d",
                config_key,
                len(requested_fields),
                requested_fields[:10],
                sample_keys,
                len(records)
            )
            return records
            
        # 使用字典推导式批量处理，避免嵌套循环
        remapped = []
        mapped_count = 0
        
        for row in records:
            # 使用字典推导式一次性完成所有字段映射
            new_row = {dst: row[src] for src, dst in optimized_field_map.items() if src in row}
            
            # 保留未映射的原始字段
            for key, value in row.items():
                if key not in optimized_field_map:
                    new_row[key] = value
            
            remapped.append(new_row)
            mapped_count += 1
        
        # 统计未映射字段数，便于排查遗漏
        requested_fields = set(field_map.keys()) if field_map else set()
        mapped_fields = set(optimized_field_map.keys())
        missing_count = len(requested_fields - mapped_fields)
        logger.info(
            "字段映射完成 | config_key=%s | 记录数=%d | 映射字段数=%d | 未映射字段数=%d",
            config_key,
            mapped_count,
            len(optimized_field_map),
            missing_count
        )
        return remapped


