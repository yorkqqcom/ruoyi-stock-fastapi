import json
import hashlib
from typing import Callable, Awaitable, Any

# 构建缓存key
def build_cache_key(module: str, method: str, *args, **kwargs) -> str:
    args_str = str(args) + str(sorted(kwargs.items()))
    md5 = hashlib.md5(args_str.encode()).hexdigest()
    return f"{module}:{method}:{md5}"

# 异步缓存获取
async def cache_get(redis, key: str, fallback_func: Callable[[], Awaitable[Any]], expire: int = 300):
    if redis is None:
        # redis不可用，直接查数据
        return await fallback_func()
    try:
        cached = await redis.get(key)
        if cached:
            return json.loads(cached)
        # 未命中，查数据
        data = await fallback_func()
        await redis.setex(key, expire, json.dumps(data))
        return data
    except Exception as e:
        # 记录日志可选
        return await fallback_func() 