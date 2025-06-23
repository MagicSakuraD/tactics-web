# ⚙️ 配置管理 - 集中管理所有配置参数
from pathlib import Path
from typing import Optional
import os

class Settings:
    """应用配置类"""
    
    # 基础配置
    APP_NAME: str = "Tactics2D Web API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # 服务器配置
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # 数据路径配置
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LEVELX_DATA_DIR: Path = DATA_DIR / "LevelX"
    HIGHD_DATA_DIR: Path = LEVELX_DATA_DIR / "highD" / "data"
    
    # Tactics2D配置
    SUPPORTED_DATASETS = ["highD", "inD", "rounD", "exiD", "uniD"]
    DEFAULT_DATASET = "highD"
    
    # WebSocket配置
    MAX_CONNECTIONS: int = 100
    PING_INTERVAL: int = 30
    
    # 仿真配置
    MAX_SIMULATION_DURATION: int = 3600  # 最大仿真时长(秒)
    DEFAULT_FPS: int = 25  # 默认帧率
    MAX_FPS: int = 60  # 最大帧率
    
    # CORS配置
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    @property
    def database_url(self) -> Optional[str]:
        """数据库连接URL (如果需要的话)"""
        return os.getenv("DATABASE_URL")
    
    def ensure_data_dirs(self):
        """确保数据目录存在"""
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LEVELX_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.HIGHD_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 全局配置实例
settings = Settings()