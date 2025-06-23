# 🛠️ 通用辅助函数
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def generate_session_id() -> str:
    """生成唯一的会话ID"""
    return str(uuid.uuid4())

def get_current_timestamp() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)

def format_duration(seconds: float) -> str:
    """格式化时长显示"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def format_file_size(bytes_size: int) -> str:
    """格式化文件大小显示"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

def get_system_stats() -> Dict[str, Any]:
    """获取系统统计信息"""
    try:
        import os
        return {
            "process_id": os.getpid(),
            "timestamp": datetime.now().isoformat(),
            "available": True
        }
    except Exception as e:
        logger.warning(f"获取系统统计信息失败: {e}")
        return {"available": False}

def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """安全除法，避免除零错误"""
    try:
        return a / b if b != 0 else default
    except (TypeError, ValueError):
        return default

def clamp(value: float, min_val: float, max_val: float) -> float:
    """将值限制在指定范围内"""
    return max(min_val, min(value, max_val))

def validate_timestamp_range(start: int, end: int, max_duration_ms: int = 300000) -> tuple[int, int]:
    """验证和修正时间戳范围"""
    if start >= end:
        raise ValueError("开始时间必须小于结束时间")
    
    if end - start > max_duration_ms:
        end = start + max_duration_ms
        logger.warning(f"时间范围太大，已限制为 {max_duration_ms}ms")
    
    return start, end

def create_error_response(message: str, error_type: str = "ValidationError") -> Dict[str, Any]:
    """创建标准错误响应"""
    return {
        "status": "error",
        "message": message,
        "error_type": error_type,
        "timestamp": datetime.now().isoformat()
    }

def create_success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建标准成功响应"""
    return {
        "status": "success",
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }

class Timer:
    """简单的计时器类"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
        return self
    
    def stop(self):
        """停止计时"""
        self.end_time = time.time()
        return self
    
    def elapsed(self) -> float:
        """获取经过的时间（秒）"""
        if self.start_time is None:
            return 0.0
        
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    def __enter__(self):
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        logger.debug(f"操作耗时: {self.elapsed():.3f}s")
