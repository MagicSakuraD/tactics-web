# 🔧 数据集处理服务 - 数据集解析和管理的核心逻辑
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor
import asyncio

from ..config import settings
from ..models import DatasetInfo, FileInfo, ParticipantInfo, TrajectoryData, DatasetType

# 尝试导入 tactics2d
try:
    from tactics2d.dataset_parser import LevelXParser
    TACTICS2D_AVAILABLE = True
except ImportError as e:
    TACTICS2D_AVAILABLE = False
    logging.warning(f"Tactics2D不可用: {e}")

logger = logging.getLogger(__name__)

class DatasetService:
    """数据集服务类"""
    
    def __init__(self):
        self.parsers: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def get_available_datasets(self) -> List[DatasetInfo]:
        """获取可用的数据集列表"""
        datasets = []
        
        # 检查 highD 数据集
        if settings.HIGHD_DATA_DIR.exists():
            file_count = len(list(settings.HIGHD_DATA_DIR.glob("*_tracks.csv")))
            total_size = sum(f.stat().st_size for f in settings.HIGHD_DATA_DIR.glob("*.csv"))
            
            datasets.append(DatasetInfo(
                id="highD",
                name="highD Dataset",
                type="LevelX",
                file_count=file_count,
                total_size=total_size,
                available=file_count > 0 and TACTICS2D_AVAILABLE
            ))
        
        return datasets
    
    async def get_dataset_files(self, dataset: DatasetType) -> List[FileInfo]:
        """获取数据集中的文件列表"""
        if not TACTICS2D_AVAILABLE:
            raise ValueError("Tactics2D不可用")
            
        if dataset == DatasetType.HIGHD:
            return await self._get_highd_files()
        else:
            raise ValueError(f"暂不支持数据集: {dataset}")
    
    async def _get_highd_files(self) -> List[FileInfo]:
        """获取 highD 数据集文件列表"""
        files = []
        parser = self._get_parser("highD")
        
        # 在线程池中执行，避免阻塞主线程
        loop = asyncio.get_event_loop()
        
        for file_path in settings.HIGHD_DATA_DIR.glob("*_tracks.csv"):
            try:
                file_id = int(file_path.stem.split("_")[0])
                
                # 异步获取文件信息
                stamp_range = await loop.run_in_executor(
                    self.executor, 
                    parser.get_stamp_range, 
                    file_id, 
                    str(settings.HIGHD_DATA_DIR)
                )
                
                location_id = await loop.run_in_executor(
                    self.executor,
                    parser.get_location,
                    file_id,
                    str(settings.HIGHD_DATA_DIR)
                )
                
                files.append(FileInfo(
                    file_id=file_id,
                    name=file_path.name,
                    size=file_path.stat().st_size,
                    location_id=int(location_id),
                    duration_seconds=float((int(stamp_range[1]) - int(stamp_range[0])) / 1000.0)
                ))
                
            except Exception as e:
                logger.warning(f"处理文件 {file_path} 时出错: {e}")
                continue
        
        return sorted(files, key=lambda x: x.file_id)
    
    async def parse_trajectory(self, 
                             dataset: DatasetType, 
                             file_id: int,
                             stamp_range: Optional[Tuple[int, int]] = None,
                             participant_ids: Optional[List[int]] = None) -> TrajectoryData:
        """解析轨迹数据"""
        if not TACTICS2D_AVAILABLE:
            raise ValueError("Tactics2D不可用")
            
        parser = self._get_parser(dataset.value)
        data_folder = self._get_data_folder(dataset)
        
        loop = asyncio.get_event_loop()
        
        # 异步解析轨迹
        participants, actual_range = await loop.run_in_executor(
            self.executor,
            parser.parse_trajectory,
            file_id,
            str(data_folder),
            stamp_range,
            participant_ids
        )
        
        # 转换为响应格式
        participant_list = []
        for pid, participant in participants.items():
            # 安全地转换参与者ID
            safe_pid = int(pid.item()) if hasattr(pid, 'item') else int(pid)
            
            participant_list.append(ParticipantInfo(
                id=safe_pid,
                type=type(participant).__name__,
                active_time_range=(int(actual_range[0]), int(actual_range[1])),
                attributes={
                    "driven_mode": getattr(participant, 'driven_mode', None),
                    "color": getattr(participant, 'color', None)
                }
            ))
        
        return TrajectoryData(
            file_id=file_id,
            dataset=dataset.value,
            timestamp_range=(int(actual_range[0]), int(actual_range[1])),
            participants=participant_list
        )
    
    def _get_parser(self, dataset: str):
        """获取解析器实例"""
        if dataset not in self.parsers:
            if dataset == "highD":
                self.parsers[dataset] = LevelXParser("highD")
            else:
                raise ValueError(f"不支持的数据集: {dataset}")
        
        return self.parsers[dataset]
    
    def _get_data_folder(self, dataset: DatasetType) -> Path:
        """获取数据集文件夹路径"""
        if dataset == DatasetType.HIGHD:
            return settings.HIGHD_DATA_DIR
        else:
            raise ValueError(f"不支持的数据集: {dataset}")

# 全局数据集服务实例
dataset_service = DatasetService()