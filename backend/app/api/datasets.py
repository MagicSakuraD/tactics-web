# 🌐 数据集API - 数据集上传、列表、轨迹查询
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from ..models import (
    DatasetInfo, FileInfo, TrajectoryData, ApiResponse, 
    DatasetType, TrajectoryParseRequest
)
from ..services.dataset_service import dataset_service
from ..utils.helpers import create_success_response, create_error_response, Timer

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.get("/", response_model=List[DatasetInfo])
async def get_datasets():
    """获取可用的数据集列表"""
    try:
        with Timer() as timer:
            datasets = await dataset_service.get_available_datasets()
        
        return datasets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset}/files", response_model=List[FileInfo])
async def get_dataset_files(dataset: DatasetType):
    """获取指定数据集的文件列表"""
    try:
        with Timer() as timer:
            files = await dataset_service.get_dataset_files(dataset)
        
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{dataset}/files/{file_id}", response_model=dict)
async def get_file_info(dataset: DatasetType, file_id: int):
    """获取指定文件的详细信息"""
    try:
        # 这里可以扩展获取更详细的文件信息
        files = await dataset_service.get_dataset_files(dataset)
        file_info = next((f for f in files if f.file_id == file_id), None)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return create_success_response(file_info.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dataset}/parse", response_model=TrajectoryData)
async def parse_trajectory(dataset: DatasetType, request: TrajectoryParseRequest):
    """解析轨迹数据"""
    try:
        with Timer() as timer:
            trajectory_data = await dataset_service.parse_trajectory(
                dataset=request.dataset,
                file_id=request.file_id,
                stamp_range=request.stamp_range,
                participant_ids=request.participant_ids
            )
        
        return trajectory_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))