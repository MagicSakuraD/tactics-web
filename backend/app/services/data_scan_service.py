# data_scan_service.py - 数据扫描服务
# 扫描可用的地图文件和数据集文件，提供给前端选择

import logging
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class MapFileInfo:
    """地图文件信息"""
    id: str  # 文件名（不含扩展名），如 "highD_1"
    path: str  # 完整路径
    name: str  # 显示名称

@dataclass
class DatasetFileInfo:
    """数据集文件信息"""
    file_id: int  # 文件ID（从文件名提取）
    dataset_path: str  # 数据集目录路径
    preview_image: Optional[str] = None  # 预览图路径（如果存在）
    has_tracks: bool = False  # 是否有轨迹文件
    has_meta: bool = False  # 是否有元数据文件

class DataScanService:
    """数据扫描服务 - 扫描可用的地图和数据集文件"""
    
    def __init__(self):
        self._map_cache: Optional[List[MapFileInfo]] = None
        self._dataset_cache: Dict[str, List[DatasetFileInfo]] = {}
    
    def scan_map_files(self, force_refresh: bool = False) -> List[MapFileInfo]:
        """
        扫描可用的地图文件（OSM格式）
        
        Args:
            force_refresh: 强制刷新缓存
            
        Returns:
            地图文件信息列表
        """
        if self._map_cache is not None and not force_refresh:
            return self._map_cache
        
        map_files = []
        map_dir = settings.DATA_DIR / "highD_map"
        
        if not map_dir.exists():
            logger.warning(f"地图目录不存在: {map_dir}")
            return []
        
        # 扫描所有 .osm 文件
        for osm_file in map_dir.glob("*.osm"):
            try:
                file_id = osm_file.stem  # 例如 "highD_1"
                map_files.append(MapFileInfo(
                    id=file_id,
                    path=str(osm_file.absolute()),
                    name=f"{file_id.replace('_', ' ').title()}"  # "HighD 1"
                ))
            except Exception as e:
                logger.warning(f"扫描地图文件失败 {osm_file}: {e}")
        
        # 按文件名排序
        map_files.sort(key=lambda x: x.id)
        self._map_cache = map_files
        
        logger.info(f"扫描到 {len(map_files)} 个地图文件")
        return map_files
    
    def scan_dataset_files(
        self, 
        dataset_type: str = "highD", 
        force_refresh: bool = False
    ) -> List[DatasetFileInfo]:
        """
        扫描指定数据集类型的可用文件
        
        Args:
            dataset_type: 数据集类型（highD, inD等）
            force_refresh: 强制刷新缓存
            
        Returns:
            数据集文件信息列表
        """
        cache_key = dataset_type.lower()
        
        if cache_key in self._dataset_cache and not force_refresh:
            return self._dataset_cache[cache_key]
        
        dataset_files = []
        
        # 根据数据集类型确定目录
        if dataset_type.lower() == "highd":
            dataset_dir = settings.HIGHD_DATA_DIR
        else:
            # 其他数据集类型
            dataset_dir = settings.LEVELX_DATA_DIR / dataset_type.lower() / "data"
        
        if not dataset_dir.exists():
            logger.warning(f"数据集目录不存在: {dataset_dir}")
            return []
        
        # 扫描所有可能的文件ID（从 tracks.csv 文件名提取）
        seen_ids = set()
        
        for tracks_file in dataset_dir.glob("*_tracks.csv"):
            try:
                # 提取文件ID：例如 "01_tracks.csv" -> 1
                file_id_str = tracks_file.name.split("_")[0]
                file_id = int(file_id_str)
                
                if file_id in seen_ids:
                    continue
                seen_ids.add(file_id)
                
                # 检查相关文件是否存在
                meta_file = dataset_dir / f"{file_id_str}_tracksMeta.csv"
                recording_meta_file = dataset_dir / f"{file_id_str}_recordingMeta.csv"
                preview_image = dataset_dir / f"{file_id_str}_highway.png"
                
                dataset_files.append(DatasetFileInfo(
                    file_id=file_id,
                    dataset_path=str(dataset_dir.absolute()),
                    preview_image=str(preview_image.absolute()) if preview_image.exists() else None,
                    has_tracks=True,
                    has_meta=meta_file.exists() and recording_meta_file.exists()
                ))
            except (ValueError, IndexError) as e:
                logger.warning(f"解析数据集文件名失败 {tracks_file}: {e}")
                continue
        
        # 按文件ID排序
        dataset_files.sort(key=lambda x: x.file_id)
        self._dataset_cache[cache_key] = dataset_files
        
        logger.info(f"扫描到 {len(dataset_files)} 个 {dataset_type} 数据集文件")
        return dataset_files
    
    def get_preview_image_path(
        self, 
        dataset_type: str, 
        file_id: int
    ) -> Optional[str]:
        """
        获取数据集预览图路径
        
        Args:
            dataset_type: 数据集类型
            file_id: 文件ID
            
        Returns:
            预览图路径，如果不存在则返回None
        """
        if dataset_type.lower() == "highd":
            dataset_dir = settings.HIGHD_DATA_DIR
        else:
            dataset_dir = settings.LEVELX_DATA_DIR / dataset_type.lower() / "data"
        
        preview_image = dataset_dir / f"{file_id:02d}_highway.png"
        
        if preview_image.exists():
            return str(preview_image.absolute())
        
        return None
    
    def clear_cache(self):
        """清除缓存"""
        self._map_cache = None
        self._dataset_cache.clear()
        logger.info("数据扫描缓存已清除")

# 全局服务实例
data_scan_service = DataScanService()
