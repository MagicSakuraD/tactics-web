# 📋 请求数据模型 - 定义客户端请求的数据结构
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum

class DatasetType(str, Enum):
    """支持的数据集类型"""
    HIGHD = "highD"
    IND = "inD"
    ROUND = "rounD"
    EXID = "exiD"
    UNID = "uniD"

class SimulationRequest(BaseModel):
    """创建仿真会话的请求"""
    dataset: DatasetType = Field(..., description="数据集类型")
    file_id: int = Field(..., ge=1, description="文件ID")
    name: Optional[str] = Field(None, description="仿真会话名称")
    description: Optional[str] = Field(None, description="仿真描述")

class TrajectoryParseRequest(BaseModel):
    """轨迹解析请求"""
    dataset: DatasetType = Field(..., description="数据集类型")
    file_id: int = Field(..., ge=1, description="文件ID")
    stamp_range: Optional[Tuple[int, int]] = Field(None, description="时间戳范围(毫秒)")
    participant_ids: Optional[List[int]] = Field(None, description="指定的参与者ID列表")

class SimulationControlRequest(BaseModel):
    """仿真控制请求"""
    action: str = Field(..., description="控制动作: start, pause, stop, reset")
    fps: Optional[int] = Field(None, ge=1, le=60, description="帧率设置")
    timestamp: Optional[int] = Field(None, description="跳转到指定时间戳")

class WebSocketMessage(BaseModel):
    """WebSocket消息格式"""
    type: str = Field(..., description="消息类型")
    session_id: Optional[str] = Field(None, description="会话ID")
    data: Optional[Dict[str, Any]] = Field(None, description="消息数据")
    timestamp: Optional[int] = Field(None, description="时间戳")

class ParticipantFilter(BaseModel):
    """参与者筛选条件"""
    vehicle_types: Optional[List[str]] = Field(None, description="车辆类型过滤")
    id_range: Optional[Tuple[int, int]] = Field(None, description="ID范围过滤")
    active_only: bool = Field(True, description="只显示活跃的参与者")

class VisualizationSettings(BaseModel):
    """可视化设置"""
    show_trajectories: bool = Field(True, description="显示轨迹")
    show_ids: bool = Field(True, description="显示ID")
    camera_follow: Optional[int] = Field(None, description="摄像机跟随的参与者ID")
    zoom_level: float = Field(1.0, ge=0.1, le=10.0, description="缩放级别")

# 新的数据集配置模型
class DatasetConfig(BaseModel):
    """完整的数据集配置"""
    dataset: str = Field(..., description="数据集类型")
    file_id: int = Field(..., ge=1, description="文件ID")
    dataset_path: str = Field(..., description="数据集路径")
    map_path: str = Field(..., description="地图文件路径")
    stamp_start: Optional[int] = Field(None, description="开始时间戳")
    stamp_end: Optional[int] = Field(None, description="结束时间戳")
    perception_range: float = Field(50.0, description="感知范围")
    frame_step: int = Field(40, description="帧步长")

class WebSocketCommand(BaseModel):
    """WebSocket命令"""
    type: str = Field(..., description="命令类型: start, pause, stop, seek")
    frame: Optional[int] = Field(None, description="目标帧(用于seek)")
    fps: Optional[int] = Field(None, description="播放帧率")
