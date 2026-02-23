"""
JSON 请求体缓存中间件：在路由与依赖解析之前读 body 一次并回放，保证 FastAPI Body 参数与 Log 等后续读取得到同一份数据。
"""
import json

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class BodyCacheMiddleware(BaseHTTPMiddleware):
    """
    对 application/json 的 POST/PUT/PATCH 请求：读 body 一次，缓存到 request.state，并替换 receive 使后续读取得到同一份 body。
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_type = request.headers.get('Content-Type', '') or ''
        method = request.method.upper()
        if 'application/json' in content_type and method in ('POST', 'PUT', 'PATCH'):
            try:
                body_bytes = await request.body()
            except Exception:
                body_bytes = b''
            try:
                json_body = json.loads(body_bytes) if body_bytes else None
            except Exception:
                json_body = None
            try:
                request.state._cached_body_bytes = body_bytes
                request.state._cached_json_body = json_body if json_body is not None else {}
            except Exception:
                pass
            cached_bytes = body_bytes
            async def _receive():
                return {'type': 'http.request', 'body': cached_bytes, 'more_body': False}
            request.scope['receive'] = _receive
            if hasattr(request, '_receive'):
                request._receive = _receive
            if hasattr(request, '_body'):
                del request._body
            if hasattr(request, '_stream_consumed'):
                request._stream_consumed = False
        response = await call_next(request)
        return response


def add_body_cache_middleware(app: FastAPI) -> None:
    """
    添加 JSON body 缓存中间件（最后添加，最先执行，保证在路由与依赖解析前完成 body 读一次+回放）。
    """
    app.add_middleware(BodyCacheMiddleware)
