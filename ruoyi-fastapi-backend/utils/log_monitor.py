# -- coding: utf-8 --
"""
日志监控和清理工具
用于监控日志文件大小、清理过期日志、优化日志性能
"""
import os
import time
import glob
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path


class LogMonitor:
    """
    日志监控器
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.max_retention_days = 7
        self.cleanup_threshold = 0.8  # 当磁盘使用率超过80%时清理
        
    def get_log_files(self) -> List[Path]:
        """获取所有日志文件"""
        if not self.log_dir.exists():
            return []
        
        log_files = []
        for pattern in ["*.log", "*.log.*"]:
            log_files.extend(self.log_dir.glob(pattern))
        
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def get_file_size(self, file_path: Path) -> int:
        """获取文件大小"""
        try:
            return file_path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0
    
    def is_file_old(self, file_path: Path, days: int = None) -> bool:
        """检查文件是否过期"""
        if days is None:
            days = self.max_retention_days
        
        try:
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            return datetime.now() - file_time > timedelta(days=days)
        except (OSError, FileNotFoundError):
            return True
    
    def cleanup_old_logs(self) -> Dict[str, Any]:
        """清理过期日志"""
        result = {
            "cleaned_files": [],
            "freed_space": 0,
            "errors": []
        }
        
        log_files = self.get_log_files()
        
        for log_file in log_files:
            try:
                if self.is_file_old(log_file):
                    file_size = self.get_file_size(log_file)
                    log_file.unlink()
                    result["cleaned_files"].append(str(log_file))
                    result["freed_space"] += file_size
            except Exception as e:
                result["errors"].append(f"清理文件 {log_file} 失败: {str(e)}")
        
        return result
    
    def compress_large_logs(self) -> Dict[str, Any]:
        """压缩大日志文件"""
        result = {
            "compressed_files": [],
            "errors": []
        }
        
        log_files = self.get_log_files()
        
        for log_file in log_files:
            try:
                if self.get_file_size(log_file) > self.max_file_size:
                    # 创建压缩文件
                    compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                    
                    # 使用gzip压缩
                    import gzip
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # 删除原文件
                    log_file.unlink()
                    result["compressed_files"].append(str(compressed_file))
                    
            except Exception as e:
                result["errors"].append(f"压缩文件 {log_file} 失败: {str(e)}")
        
        return result
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            stat = shutil.disk_usage(self.log_dir)
            return {
                "total": stat.total,
                "used": stat.used,
                "free": stat.free,
                "usage_percent": (stat.used / stat.total) * 100
            }
        except Exception as e:
            return {"error": str(e)}
    
    def should_cleanup(self) -> bool:
        """判断是否需要清理"""
        disk_usage = self.get_disk_usage()
        if "error" in disk_usage:
            return False
        
        return disk_usage["usage_percent"] > (self.cleanup_threshold * 100)
    
    def auto_cleanup(self) -> Dict[str, Any]:
        """自动清理日志"""
        result = {
            "action": "none",
            "details": {}
        }
        
        if self.should_cleanup():
            # 先清理过期文件
            cleanup_result = self.cleanup_old_logs()
            result["action"] = "cleanup"
            result["details"]["cleanup"] = cleanup_result
            
            # 如果清理后仍然需要空间，压缩大文件
            if self.should_cleanup():
                compress_result = self.compress_large_logs()
                result["action"] = "compress"
                result["details"]["compress"] = compress_result
        
        return result
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        log_files = self.get_log_files()
        
        total_size = sum(self.get_file_size(f) for f in log_files)
        file_count = len(log_files)
        
        return {
            "total_files": file_count,
            "total_size": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "oldest_file": min(log_files, key=lambda x: x.stat().st_mtime).name if log_files else None,
            "newest_file": max(log_files, key=lambda x: x.stat().st_mtime).name if log_files else None,
            "disk_usage": self.get_disk_usage()
        }


def setup_log_monitoring():
    """设置日志监控"""
    monitor = LogMonitor()
    
    # 执行自动清理
    cleanup_result = monitor.auto_cleanup()
    
    # 获取统计信息
    stats = monitor.get_log_stats()
    
    return {
        "cleanup_result": cleanup_result,
        "stats": stats
    }


if __name__ == "__main__":
    # 运行日志监控
    result = setup_log_monitoring()
    print("日志监控结果:")
    print(f"清理操作: {result['cleanup_result']['action']}")
    print(f"日志文件数量: {result['stats']['total_files']}")
    print(f"日志总大小: {result['stats']['total_size_mb']:.2f} MB")
    print(f"磁盘使用率: {result['stats']['disk_usage'].get('usage_percent', 0):.1f}%")
