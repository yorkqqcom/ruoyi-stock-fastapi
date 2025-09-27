# -- coding: utf-8 --
from typing import Dict, List
from fastapi import APIRouter, Body, Query
import time

from user_module.schemas.ede import EDERequest
from user_module.services.akshare_dispatcher import AkshareDispatcher
from user_module.services.ede_config_service import EDEConfigService
from user_module.services.ede_cache_service import get_cache_service, cached
from utils.response_util import ResponseUtil
from utils.log_util import logger


router = APIRouter(prefix="/api/stock/ede", tags=["EDE 动态数据"])


def validate_required_params(config: Dict, params: Dict) -> Dict:
    """
    验证配置中的必需参数是否都已提供
    
    Args:
        config: 指标配置
        params: 用户提供的参数
        
    Returns:
        Dict: 验证结果，包含valid字段和missing_params字段
    """
    if not config.get("akshare", {}).get("params"):
        return {"valid": True, "missing_params": []}
    
    akshare_params = config["akshare"]["params"]
    missing_params = []
    
    for param_key, param_config in akshare_params.items():
        if param_config.get("required", False):
            param_value = params.get(param_key)
            if param_value is None or param_value == "":
                missing_params.append({
                    "key": param_key,
                    "title": param_config.get("title", param_key),
                    "type": param_config.get("type", "string"),
                    "description": param_config.get("description", ""),
                    "options": param_config.get("options", [])
                })
    
    return {
        "valid": len(missing_params) == 0,
        "missing_params": missing_params
    }


# 配置将通过EDEConfigService动态加载
def get_ede_config_registry() -> Dict[str, Dict]:
    """获取EDE配置注册表"""
    return EDEConfigService.get_config()


@router.post("/dynamic")
async def ede_dynamic(request: EDERequest = Body(...)) -> Dict:
    """动态获取EDE数据"""
    start_time = time.time()
    logger.info(
        f"[EDE] 动态请求开始 | key={request.key} | 控制={request.control} | 参数keys={list((request.params or {}).keys())[:10]}"
    )
    config_registry = get_ede_config_registry()
    cfg = config_registry.get(request.key)
    if not cfg:
        logger.warning(f"[EDE] 动态请求配置未找到 | key={request.key}")
        return ResponseUtil.error(msg=f"找不到配置: {request.key}")

    # 验证必需参数
    validation_result = validate_required_params(cfg, request.params or {})
    if not validation_result["valid"]:
        logger.warning(
            f"[EDE] 动态请求参数校验失败 | key={request.key} | 缺失参数数={len(validation_result['missing_params'])}"
        )
        return ResponseUtil.error(
            msg="参数验证失败", 
            data={
                "missing_params": validation_result["missing_params"],
                "config": cfg
            }
        )

    rows = await AkshareDispatcher.dispatch(
        cfg,
        request.params or {},
        (request.control and request.control.dict()) or None,
        request.key,
    )
    duration = time.time() - start_time
    row_count = len(rows) if rows else 0
    sample_fields = list(rows[0].keys())[:6] if rows else []
    logger.info(
        f"[EDE] 动态请求完成 | key={request.key} | 行数={row_count} | 耗时={duration:.3f}s | 示例字段={sample_fields}"
    )
    return ResponseUtil.success(data={"rows": rows, "total": row_count, "config": cfg})


@router.post("/multi-config-dynamic")
async def ede_multi_config_dynamic(request: Dict = Body(...)) -> Dict:
    """多配置混合数据提取"""
    try:
        overall_start = time.time()
        config_registry = get_ede_config_registry()
        config_requests = request.get("configs", [])
        filter_symbols = request.get("filter_symbols", [])
        logger.info(
            f"[EDE] 多配置请求开始 | configs={len(config_requests)} | 过滤标的数={len(filter_symbols) if filter_symbols else 0}"
        )
        
        if not config_requests:
            return ResponseUtil.error(msg="请提供至少一个配置请求")
        
        results = []
        all_rows = []
        
        # 并行处理多个配置
        import asyncio
        tasks = []
        
        for config_req in config_requests:
            config_key = config_req.get("key")
            params = config_req.get("params", {})
            
            if not config_key:
                continue
                
            cfg = config_registry.get(config_key)
            if not cfg:
                logger.warning(f"找不到配置: {config_key}")
                continue
            
            # 验证必需参数
            validation_result = validate_required_params(cfg, params)
            if not validation_result["valid"]:
                logger.warning(f"配置 {config_key} 参数验证失败: {validation_result['missing_params']}")
                continue
            
            # 创建控制参数，包含个股过滤
            control = {
                "paginate": False,
                "filter_symbols": filter_symbols if filter_symbols else None
            }
            
            # 添加任务
            task = AkshareDispatcher.dispatch(cfg, params, control, config_key)
            tasks.append((config_key, task))
        
        # 等待所有任务完成
        for config_key, task in tasks:
            try:
                logger.info(f"[EDE] 开始处理配置 | key={config_key}")
                rows = await task
                logger.info(f"[EDE] 配置完成 | key={config_key} | 行数={len(rows) if rows else 0}")
                
                # 如果返回了数据，记录第一行的字段名
                if rows and len(rows) > 0:
                    first_row_fields = list(rows[0].keys())
                    logger.debug(f"[EDE] 配置字段示例 | key={config_key} | 字段={first_row_fields[:5]}...")
                
                if rows:
                    # 为每行数据添加配置标识和字段前缀
                    for row in rows:
                        row["_config_key"] = config_key
                        row["_config_name"] = config_registry.get(config_key, {}).get("name", config_key)
                        
                        # 为每个字段添加配置前缀，避免字段名冲突
                        # 但保留基础字段（symbol, name等）的原始名称，确保前端能正确提取
                        prefixed_row = {}
                        for field_name, field_value in row.items():
                            if field_name.startswith("_"):
                                # 保留配置标识字段
                                prefixed_row[field_name] = field_value
                            elif field_name in ['symbol', 'name', 'code', 'stock_code', 'ts_code']:
                                # 保留基础字段的原始名称，同时添加带前缀的副本
                                prefixed_row[field_name] = field_value
                                prefixed_row[f"{config_key}_{field_name}"] = field_value
                            else:
                                # 为其他数据字段添加配置前缀
                                prefixed_row[f"{config_key}_{field_name}"] = field_value
                        
                        # 更新行数据
                        row.clear()
                        row.update(prefixed_row)
                    
                    results.append({
                        "config_key": config_key,
                        "config_name": config_registry.get(config_key, {}).get("name", config_key),
                        "rows": rows,
                        "count": len(rows)
                    })
                    all_rows.extend(rows)
                else:
                    logger.warning(f"[EDE] 配置无数据返回 | key={config_key}")
                    # 即使没有数据，也添加一个空的结果记录
                    results.append({
                        "config_key": config_key,
                        "config_name": config_registry.get(config_key, {}).get("name", config_key),
                        "rows": [],
                        "count": 0
                    })
            except Exception as e:
                logger.error(f"[EDE] 处理配置出错 | key={config_key} | err={e}")
                import traceback
                logger.error(f"[EDE] 详细错误: {traceback.format_exc()}")
                # 即使出错，也添加一个错误的结果记录
                results.append({
                    "config_key": config_key,
                    "config_name": config_registry.get(config_key, {}).get("name", config_key),
                    "rows": [],
                    "count": 0,
                    "error": str(e),
                    "error_details": traceback.format_exc()
                })
                continue
        
        total_duration = time.time() - overall_start
        logger.info(
            f"[EDE] 多配置请求完成 | 配置数={len(results)} | 总行数={len(all_rows)} | 耗时={total_duration:.3f}s"
        )
        return ResponseUtil.success(data={
            "results": results,
            "all_rows": all_rows,
            "total": len(all_rows),
            "config_count": len(results)
        })
        
    except Exception as e:
        logger.error(f"[EDE] 多配置数据提取失败 | err={e}")
        return ResponseUtil.error(msg=f"多配置数据提取失败: {str(e)}")


@router.post("/validate-params")
async def validate_params(request: EDERequest = Body(...)) -> Dict:
    """验证指标参数配置"""
    config_registry = get_ede_config_registry()
    cfg = config_registry.get(request.key)
    if not cfg:
        logger.warning(f"[EDE] 参数校验配置未找到 | key={request.key}")
        return ResponseUtil.error(msg=f"找不到配置: {request.key}")
    
    validation_result = validate_required_params(cfg, request.params or {})
    logger.info(
        f"[EDE] 参数校验完成 | key={request.key} | 是否通过={validation_result['valid']} | 缺失数={len(validation_result['missing_params'])}"
    )
    return ResponseUtil.success(data=validation_result)


@router.get("/configs")
@cached("configs", 3600)  # 缓存1小时
async def get_available_configs() -> Dict:
    """获取所有可用的指标配置列表"""
    start = time.time()
    config_registry = get_ede_config_registry()
    configs = []
    for key, config in config_registry.items():
        configs.append({
            "key": key,
            "name": config.get("name", key),
            "category": config.get("category", "其他"),
            "description": config.get("description", ""),
            "form_fields": config.get("ui", {}).get("form", []),
            "available_columns": [col["field"] for col in config.get("ui", {}).get("columns", [])]
        })
    
    # 按分类分组
    categories = {}
    for config in configs:
        category = config["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(config)
    
    logger.info(
        f"[EDE] 配置列表 | 总数={len(configs)} | 分类数={len(categories)} | 耗时={time.time()-start:.3f}s"
    )
    return ResponseUtil.success(data={
        "configs": configs,
        "categories": categories,
        "total": len(configs)
    })


@router.get("/metric-tree")
async def get_metric_tree() -> Dict:
    """获取指标树结构"""
    start = time.time()
    config_registry = get_ede_config_registry()
    
    # 构建树形结构
    tree_data = []
    categories = {}
    
    # 按分类组织配置
    for key, config in config_registry.items():
        category = config.get("category", "其他")
        if category not in categories:
            categories[category] = []
        
        # 构建该配置的指标子节点
        columns = config.get("ui", {}).get("columns", [])
        children = []
        
        for col in columns:
            # 排除日期字段和基础信息字段
            excluded_fields = ["date", "symbol", "name", "index"]
            if col.get("field") and col["field"] not in excluded_fields:
                children.append({
                    "label": col.get("label", col["field"]),
                    "key": f"{key}:{col['field']}",
                    "configKey": key,
                    "field": col["field"],
                    "width": col.get("width", 120),
                    "align": col.get("align", "left")
                })
        
        categories[category].append({
            "label": config.get("name", key),
            "key": key,
            "children": children,
            "description": config.get("description", "")
        })
    
    # 构建最终的树形结构
    for category_name, configs in categories.items():
        if configs:  # 只添加有配置的分类
            tree_data.append({
                "label": category_name,
                "key": f"category_{category_name}",
                "children": configs
            })
    
    logger.info(
        f"[EDE] 指标树构建完成 | 分类数={len(categories)} | 节点数={sum(len(c['children']) for c in tree_data)} | 耗时={time.time()-start:.3f}s"
    )
    return ResponseUtil.success(data={
        "tree": tree_data,
        "total": len(config_registry)
    })


@router.get("/config/{config_key}")
async def get_config_detail(config_key: str) -> Dict:
    """获取指定配置的详细信息"""
    config_registry = get_ede_config_registry()
    cfg = config_registry.get(config_key)
    if not cfg:
        logger.warning(f"[EDE] 配置详情未找到 | key={config_key}")
        return ResponseUtil.error(msg=f"找不到配置: {config_key}")
    logger.info(f"[EDE] 配置详情获取成功 | key={config_key}")
    return ResponseUtil.success(data={"config": cfg})


@router.post("/reload-config")
async def reload_config() -> Dict:
    """重新加载配置文件"""
    try:
        logger.info("[EDE] 重新加载配置开始")
        config_registry = EDEConfigService.reload_config()
        # 清空相关缓存
        cache_service = await get_cache_service()
        await cache_service.clear_all_cache()
        logger.info(f"[EDE] 重新加载配置完成 | 新配置数={len(config_registry)} | 已清空缓存")
        return ResponseUtil.success(data={
            "message": "配置重新加载成功",
            "config_count": len(config_registry)
        })
    except Exception as e:
        logger.error(f"[EDE] 重新加载配置失败 | err={e}")
        return ResponseUtil.error(msg=f"重新加载配置失败: {str(e)}")


@router.post("/clear-cache")
async def clear_cache() -> Dict:
    """清空所有缓存"""
    try:
        cache_service = await get_cache_service()
        await cache_service.clear_all_cache()
        logger.info("[EDE] 缓存清空成功")
        return ResponseUtil.success(data={"message": "缓存清空成功"})
    except Exception as e:
        logger.error(f"[EDE] 清空缓存失败 | err={e}")
        return ResponseUtil.error(msg=f"清空缓存失败: {str(e)}")


@router.get("/cache-stats")
async def get_cache_stats() -> Dict:
    """获取缓存统计信息"""
    try:
        cache_service = await get_cache_service()
        stats = cache_service.get_cache_stats()
        logger.info(
            f"[EDE] 缓存统计 | keys={list(stats.keys()) if isinstance(stats, dict) else 'n/a'}"
        )
        return ResponseUtil.success(data=stats)
    except Exception as e:
        logger.error(f"[EDE] 获取缓存统计失败 | err={e}")
        return ResponseUtil.error(msg=f"获取缓存统计失败: {str(e)}")