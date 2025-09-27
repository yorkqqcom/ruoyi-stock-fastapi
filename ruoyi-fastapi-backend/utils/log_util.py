import os
import sys
import time
import threading
import functools
from loguru import logger as _logger
from typing import Dict, Callable, Any
from middlewares.trace_middleware import TraceCtx


class LoggerInitializer:
    def __init__(self):
        self.log_path = os.path.join(os.getcwd(), 'logs')
        self.__ensure_log_directory_exists()
        self.log_path_error = os.path.join(self.log_path, f'{time.strftime("%Y-%m-%d")}_error.log')
        self._lock = threading.Lock()

    def __ensure_log_directory_exists(self):
        """
        确保日志目录存在，如果不存在则创建
        """
        if not os.path.exists(self.log_path):
            os.mkdir(self.log_path)

    @staticmethod
    def __filter(log: Dict):
        """
        自定义日志过滤器，添加trace_id
        """
        try:
            trace_id = TraceCtx.get_id()
            if trace_id:
                log['trace_id'] = trace_id
            else:
                log['trace_id'] = 'no-trace'
        except Exception:
            log['trace_id'] = 'no-trace'
        return log

    def _safe_log_rotation(self, sink):
        """
        安全的日志轮转处理，避免Windows文件权限错误
        """
        try:
            # 检查文件是否被其他进程占用
            if hasattr(sink, '_file') and sink._file:
                try:
                    # 尝试刷新缓冲区
                    sink._file.flush()
                except (OSError, IOError):
                    # 如果文件被占用，跳过轮转
                    return False
            return True
        except Exception:
            return False

    def init_log(self):
        """
        初始化日志配置 - 优化版本
        """
        # 自定义日志格式 - 简化版本，避免trace_id字段问题
        format_str = (
            '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
            '<level>{level: <8}</level> | '
            '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
            '<level>{message}</level>'
        )
        
        # 控制台格式 - 更简洁
        console_format = (
            '<green>{time:HH:mm:ss.SSS}</green> | '
            '<level>{level: <5}</level> | '
            '<cyan>{name}</cyan> - '
            '<level>{message}</level>'
        )
        
        _logger.remove()
        
        # 控制台输出 - 使用更简洁的格式，不使用filter避免trace_id问题
        _logger.add(
            sys.stderr, 
            format=console_format, 
            enqueue=True,
            level="INFO",
            catch=True
        )
        
        # 文件输出 - 优化轮转策略，不使用filter避免trace_id问题
        _logger.add(
            self.log_path_error,
            format=format_str,
            rotation="100 MB",  # 增大轮转阈值
            retention="7 days",  # 保留7天
            encoding='utf-8',
            enqueue=True,
            compression='zip',
            level="DEBUG",  # 文件记录更详细的日志
            catch=True,  # 捕获日志处理异常
            backtrace=True,  # 启用回溯
            diagnose=True,  # 启用诊断
        )

        return _logger


class SafeLogger:
    """
    安全的日志记录器，处理日志错误和异常
    """
    
    def __init__(self, logger_instance):
        self.logger = logger_instance
        self._lock = threading.Lock()
    
    def _safe_log(self, level: str, message: str, *args, **kwargs):
        """
        安全的日志记录，捕获并处理日志错误
        """
        try:
            with self._lock:
                log_func = getattr(self.logger, level.lower(), None)
                if log_func:
                    log_func(message, *args, **kwargs)
        except (OSError, IOError, PermissionError) as e:
            # 如果日志记录失败，尝试输出到stderr
            try:
                print(f"[LOG_ERROR] {level}: {message}", file=sys.stderr)
            except Exception:
                pass  # 如果连stderr都失败，静默忽略
        except Exception as e:
            # 其他异常也静默处理
            pass
    
    def info(self, message: str, *args, **kwargs):
        self._safe_log("INFO", message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        self._safe_log("DEBUG", message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        self._safe_log("WARNING", message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self._safe_log("ERROR", message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        self._safe_log("EXCEPTION", message, *args, **kwargs)


def log_performance(func: Callable) -> Callable:
    """
    性能日志装饰器，记录函数执行时间
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            if execution_time > 1.0:  # 只记录超过1秒的执行时间
                logger.info(f"{func.__name__} 执行耗时: {execution_time:.2f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {str(e)}")
            raise
    return wrapper


# 使用简化的日志配置，完全避免trace_id问题
try:
    from utils.log_simple import simple_logger
    logger = simple_logger
except ImportError:
    # 如果简化配置不可用，使用默认配置
    log_initializer = LoggerInitializer()
    _raw_logger = log_initializer.init_log()
    logger = SafeLogger(_raw_logger)
