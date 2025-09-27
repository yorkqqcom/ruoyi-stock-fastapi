# -- coding: utf-8 --
"""
日志配置优化模块
提供更好的日志管理和性能优化
"""
import os
import sys
import time
import threading
from typing import Dict, Any, Optional
from loguru import logger as _logger
from middlewares.trace_middleware import TraceCtx


class OptimizedLogger:
    """
    优化的日志记录器
    - 减少I/O操作
    - 智能日志级别控制
    - 批量日志处理
    """
    
    def __init__(self):
        self._log_buffer = []
        self._buffer_lock = threading.Lock()
        self._last_flush = time.time()
        self._buffer_size = 100  # 缓冲区大小
        self._flush_interval = 5  # 刷新间隔（秒）
        
    def _should_log(self, level: str, module: str = None) -> bool:
        """
        智能判断是否应该记录日志
        """
        # 根据模块和级别进行过滤
        if module == "akshare_dispatcher":
            # 对于akshare_dispatcher，只记录重要信息
            return level in ["ERROR", "WARNING", "INFO"]
        return True
    
    def _batch_log(self, level: str, message: str, *args, **kwargs):
        """
        批量日志处理，减少I/O操作
        """
        with self._buffer_lock:
            self._log_buffer.append({
                'level': level,
                'message': message,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            
            # 检查是否需要刷新缓冲区
            current_time = time.time()
            should_flush = (
                len(self._log_buffer) >= self._buffer_size or
                (current_time - self._last_flush) >= self._flush_interval
            )
            
            if should_flush:
                self._flush_buffer()
    
    def _flush_buffer(self):
        """
        刷新日志缓冲区
        """
        if not self._log_buffer:
            return
            
        try:
            for log_entry in self._log_buffer:
                level = log_entry['level']
                message = log_entry['message']
                args = log_entry['args']
                kwargs = log_entry['kwargs']
                
                # 获取对应的日志函数
                log_func = getattr(_logger, level.lower(), None)
                if log_func:
                    log_func(message, *args, **kwargs)
        except Exception as e:
            # 如果批量日志失败，尝试单独记录
            try:
                print(f"[BATCH_LOG_ERROR] {e}", file=sys.stderr)
            except Exception:
                pass
        finally:
            self._log_buffer.clear()
            self._last_flush = time.time()
    
    def info(self, message: str, *args, **kwargs):
        if self._should_log("INFO"):
            self._batch_log("INFO", message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        if self._should_log("DEBUG"):
            self._batch_log("DEBUG", message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        if self._should_log("WARNING"):
            self._batch_log("WARNING", message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        if self._should_log("ERROR"):
            self._batch_log("ERROR", message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        if self._should_log("EXCEPTION"):
            self._batch_log("EXCEPTION", message, *args, **kwargs)


class LogConfigManager:
    """
    日志配置管理器
    """
    
    def __init__(self):
        self.log_path = os.path.join(os.getcwd(), 'logs')
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path, exist_ok=True)
    
    def setup_optimized_logging(self) -> _logger:
        """
        设置优化的日志配置
        """
        # 移除默认处理器
        _logger.remove()
        
        # 控制台输出 - 简化格式
        console_format = (
            '<green>{time:HH:mm:ss.SSS}</green> | '
            '<level>{level: <5}</level> | '
            '<cyan>{name}</cyan> - '
            '<level>{message}</level>'
        )
        
        _logger.add(
            sys.stderr,
            format=console_format,
            level="INFO",
            enqueue=True,
            catch=True
        )
        
        # 文件输出 - 优化配置
        log_file = os.path.join(self.log_path, f'{time.strftime("%Y-%m-%d")}_app.log')
        
        _logger.add(
            log_file,
            format=(
                '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
                '<level>{level: <8}</level> | '
                '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
                '<level>{message}</level>'
            ),
            rotation="200 MB",  # 增大轮转阈值
            retention="10 days",  # 保留10天
            compression="zip",
            encoding="utf-8",
            level="DEBUG",
            enqueue=True,
            catch=True,
            backtrace=True,
            diagnose=True
        )
        
        return _logger


# 创建优化的日志实例
log_config_manager = LogConfigManager()
optimized_logger = OptimizedLogger()
