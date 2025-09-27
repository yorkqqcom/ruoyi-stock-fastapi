# -- coding: utf-8 --
"""
简化的日志配置
完全避免trace_id字段问题
"""
import os
import sys
import time
import threading
from loguru import logger as _logger


class SimpleLogger:
    """
    简化的日志记录器，避免所有trace_id相关问题
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._setup_logging()
    
    def _setup_logging(self):
        """设置简化的日志配置"""
        # 移除所有现有处理器
        _logger.remove()
        
        # 控制台输出 - 最简格式
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
        
        # 文件输出 - 简化格式
        log_path = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(log_path):
            os.makedirs(log_path, exist_ok=True)
        
        log_file = os.path.join(log_path, f'{time.strftime("%Y-%m-%d")}_app.log')
        
        file_format = (
            '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
            '<level>{level: <8}</level> | '
            '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
            '<level>{message}</level>'
        )
        
        _logger.add(
            log_file,
            format=file_format,
            rotation="100 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            level="DEBUG",
            enqueue=True,
            catch=True,
            backtrace=True,
            diagnose=True
        )
    
    def info(self, message: str, *args, **kwargs):
        """记录信息日志"""
        try:
            with self._lock:
                _logger.info(message, *args, **kwargs)
        except Exception:
            try:
                print(f"[INFO] {message}", file=sys.stderr)
            except Exception:
                pass
    
    def debug(self, message: str, *args, **kwargs):
        """记录调试日志"""
        try:
            with self._lock:
                _logger.debug(message, *args, **kwargs)
        except Exception:
            try:
                print(f"[DEBUG] {message}", file=sys.stderr)
            except Exception:
                pass
    
    def warning(self, message: str, *args, **kwargs):
        """记录警告日志"""
        try:
            with self._lock:
                _logger.warning(message, *args, **kwargs)
        except Exception:
            try:
                print(f"[WARNING] {message}", file=sys.stderr)
            except Exception:
                pass
    
    def error(self, message: str, *args, **kwargs):
        """记录错误日志"""
        try:
            with self._lock:
                _logger.error(message, *args, **kwargs)
        except Exception:
            try:
                print(f"[ERROR] {message}", file=sys.stderr)
            except Exception:
                pass
    
    def exception(self, message: str, *args, **kwargs):
        """记录异常日志"""
        try:
            with self._lock:
                _logger.exception(message, *args, **kwargs)
        except Exception:
            try:
                print(f"[EXCEPTION] {message}", file=sys.stderr)
            except Exception:
                pass


# 创建简化的日志实例
simple_logger = SimpleLogger()
