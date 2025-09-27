# -- coding: utf-8 --
"""
EDE缓存服务
提供数据缓存、配置缓存等功能，提升API响应速度
"""

import json
import hashlib
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps
import asyncio
import aiofiles

try:
    import redis
    from redis.asyncio import Redis
except ImportError:
    redis = None
    Redis = None

from config.get_redis import get_redis_client
from utils.log_util import logger


class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理date和datetime对象"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


class EDECacheService:
    """EDE缓存服务类 - 遵循ruoyi-vue-fastapi框架标准"""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client
        self.memory_cache: Dict[str, Dict] = {}
        self.cache_ttl = {
            'config': 3600,  # 配置缓存1小时
            'data': 300,     # 数据缓存5分钟
            'stock_list': 1800,  # 股票列表缓存30分钟
        }
        
    @classmethod
    async def create(cls, redis_client: Optional[Redis] = None):
        """创建缓存服务实例"""
        if redis_client is None:
            try:
                redis_client = await get_redis_client()
                logger.info("EDE缓存服务Redis连接初始化成功")
            except Exception as e:
                logger.warning(f"EDE缓存服务Redis连接初始化失败，将使用内存缓存: {e}")
                redis_client = None
        
        return cls(redis_client)
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数序列化为字符串
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False, cls=CustomJSONEncoder)
        # 生成MD5哈希
        hash_key = hashlib.md5(key_str.encode('utf-8')).hexdigest()
        return f"ede:{prefix}:{hash_key}"
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        try:
            # 优先从Redis获取
            if self.redis_client:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    return json.loads(cached_data)
            
            # 从内存缓存获取
            if key in self.memory_cache:
                cache_item = self.memory_cache[key]
                if time.time() - cache_item['timestamp'] < cache_item['ttl']:
                    return cache_item['data']
                else:
                    # 过期则删除
                    del self.memory_cache[key]
            
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    async def set_cache(self, key: str, data: Any, ttl: int = 300) -> bool:
        """设置缓存数据"""
        try:
            # 处理 JSONResponse 对象
            if hasattr(data, 'body') and hasattr(data, 'status_code'):
                # 如果是 FastAPI Response 对象，提取其内容
                try:
                    import json as json_lib
                    if hasattr(data, 'body'):
                        # 对于 JSONResponse，尝试解析其 body
                        if isinstance(data.body, bytes):
                            content = json_lib.loads(data.body.decode('utf-8'))
                        else:
                            content = data.body
                    else:
                        content = data
                except Exception:
                    # 如果无法解析，记录警告并跳过缓存
                    logger.warning(f"无法序列化响应对象到缓存: {type(data)}")
                    return False
            else:
                content = data
            
            # 优先存储到Redis
            if self.redis_client:
                await self.redis_client.setex(key, ttl, json.dumps(content, ensure_ascii=False, cls=CustomJSONEncoder))
                return True
            
            # 存储到内存缓存
            self.memory_cache[key] = {
                'data': content,
                'timestamp': time.time(),
                'ttl': ttl
            }
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    async def delete_cache(self, key: str) -> bool:
        """删除缓存"""
        try:
            # 删除Redis缓存
            if self.redis_client:
                await self.redis_client.delete(key)
            
            # 删除内存缓存
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    async def get_cached_data(self, prefix: str, ttl: int, *args, **kwargs) -> Optional[Any]:
        """获取缓存的数据"""
        key = self._generate_cache_key(prefix, *args, **kwargs)
        return await self.get_cache(key)
    
    async def set_cached_data(self, prefix: str, data: Any, ttl: int, *args, **kwargs) -> bool:
        """设置缓存的数据"""
        key = self._generate_cache_key(prefix, *args, **kwargs)
        return await self.set_cache(key, data, ttl)
    
    async def cache_akshare_data(self, method_name: str, params: Dict, data: List[Dict], config_key: str = None) -> bool:
        """缓存akshare数据"""
        # 包含配置key以确保不同配置的缓存不冲突
        if config_key:
            cache_key = f"akshare_data:{config_key}:{method_name}"
        else:
            cache_key = f"akshare_data:{method_name}"
        ttl = self.cache_ttl['data']
        return await self.set_cached_data(cache_key, data, ttl, **params)
    
    async def get_cached_akshare_data(self, method_name: str, params: Dict, config_key: str = None) -> Optional[List[Dict]]:
        """获取缓存的akshare数据"""
        # 包含配置key以确保不同配置的缓存不冲突
        if config_key:
            cache_key = f"akshare_data:{config_key}:{method_name}"
        else:
            cache_key = f"akshare_data:{method_name}"
        return await self.get_cached_data(cache_key, self.cache_ttl['data'], **params)
    
    async def cache_stock_list(self, data: List[Dict]) -> bool:
        """缓存股票列表"""
        return await self.set_cache("ede:stock_list", data, self.cache_ttl['stock_list'])
    
    async def get_cached_stock_list(self) -> Optional[List[Dict]]:
        """获取缓存的股票列表"""
        return await self.get_cache("ede:stock_list")
    
    async def cache_config(self, config_key: str, config_data: Dict) -> bool:
        """缓存配置数据"""
        cache_key = f"ede:config:{config_key}"
        return await self.set_cache(cache_key, config_data, self.cache_ttl['config'])
    
    async def get_cached_config(self, config_key: str) -> Optional[Dict]:
        """获取缓存的配置数据"""
        cache_key = f"ede:config:{config_key}"
        return await self.get_cache(cache_key)
    
    async def clear_all_cache(self) -> bool:
        """清空所有缓存"""
        try:
            # 清空Redis缓存
            if self.redis_client:
                keys = await self.redis_client.keys("ede:*")
                if keys:
                    await self.redis_client.delete(*keys)
            
            # 清空内存缓存
            self.memory_cache.clear()
            
            logger.info("所有缓存已清空")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        memory_cache_count = len(self.memory_cache)
        memory_cache_size = sum(
            len(str(item['data'])) for item in self.memory_cache.values()
        )
        
        return {
            'memory_cache_count': memory_cache_count,
            'memory_cache_size': memory_cache_size,
            'redis_connected': self.redis_client is not None,
            'cache_ttl': self.cache_ttl
        }


# 全局缓存服务实例
cache_service = None


async def get_cache_service() -> EDECacheService:
    """获取缓存服务实例 - 遵循ruoyi-vue-fastapi框架标准"""
    global cache_service
    if cache_service is None:
        cache_service = await EDECacheService.create()
    return cache_service


def cached(prefix: str, ttl: int = 300):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取缓存服务实例
            service = await get_cache_service()
            
            # 生成缓存键
            cache_key = service._generate_cache_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = await service.get_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                # 如果缓存的是字典数据，需要重新构造 JSONResponse
                if isinstance(cached_result, dict):
                    from utils.response_util import ResponseUtil
                    return ResponseUtil.success(data=cached_result)
                return cached_result
            
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 缓存结果 - 只缓存数据内容，不缓存 Response 对象
            if hasattr(result, 'body') and hasattr(result, 'status_code'):
                # 如果是 Response 对象，提取其内容进行缓存
                try:
                    import json as json_lib
                    if isinstance(result.body, bytes):
                        content = json_lib.loads(result.body.decode('utf-8'))
                    else:
                        content = result.body
                    await service.set_cache(cache_key, content, ttl)
                    logger.debug(f"响应内容已缓存: {cache_key}")
                except Exception as e:
                    logger.warning(f"无法缓存响应内容: {e}")
            else:
                # 普通数据直接缓存
                await service.set_cache(cache_key, result, ttl)
                logger.debug(f"结果已缓存: {cache_key}")
            
            return result
        return wrapper
    return decorator


async def init_cache_service():
    """初始化缓存服务"""
    await get_cache_service()
    logger.info("EDE缓存服务初始化完成")
