# 📊 响应数据模型 - 定义服务端响应的数据结构
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum

class StatusEnum(str, Enum):
    """状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    LOADING = "loading"
    READY = "ready"

class DatasetInfo(BaseModel):
    """数据集信息"""
    id: str = Field(..., description="数据集ID")
    name: str = Field(..., description="数据集名称")
    type: str = Field(..., description="数据集类型")
    file_count: int = Field(..., description="文件数量")
    total_size: int = Field(..., description="总大小(字节)")
    available: bool = Field(..., description="是否可用")

class FileInfo(BaseModel):
    """文件信息"""
    file_id: int = Field(..., description="文件ID")
    name: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小")
    location_id: int = Field(..., description="位置ID")
    duration_seconds: float = Field(..., description="时长(秒)")
    participant_count: Optional[int] = Field(None, description="参与者数量")

class ParticipantInfo(BaseModel):
    """参与者信息"""
    id: int = Field(..., description="参与者ID")
    type: str = Field(..., description="类型(Vehicle等)")
    active_time_range: Tuple[int, int] = Field(..., description="活跃时间范围")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="属性信息")

class SimulationSession(BaseModel):
    """仿真会话信息"""
    session_id: str = Field(..., description="会话ID")
    name: str = Field(..., description="会话名称")
    dataset: str = Field(..., description="数据集类型")
    file_id: int = Field(..., description="文件ID")
    status: StatusEnum = Field(..., description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    current_timestamp: int = Field(0, description="当前时间戳")
    total_duration: int = Field(..., description="总时长")
    fps: int = Field(25, description="当前帧率")

class TrajectoryData(BaseModel):
    """轨迹数据响应"""
    file_id: int = Field(..., description="文件ID")
    dataset: str = Field(..., description="数据集类型")
    timestamp_range: Tuple[int, int] = Field(..., description="时间戳范围")
    participants: List[ParticipantInfo] = Field(..., description="参与者列表")
    frame_data: Optional[Dict[str, Any]] = Field(None, description="帧数据")

class ApiResponse(BaseModel):
    """通用API响应格式"""
    status: StatusEnum = Field(..., description="响应状态")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")

class WebSocketResponse(BaseModel):
    """WebSocket响应格式"""
    type: str = Field(..., description="消息类型")
    session_id: str = Field(..., description="会话ID")
    data: Any = Field(..., description="响应数据")
    timestamp: int = Field(..., description="时间戳")
    status: StatusEnum = Field(StatusEnum.SUCCESS, description="状态")

class SystemStatus(BaseModel):
    """系统状态信息"""
    api_version: str = Field(..., description="API版本")
    tactics2d_available: bool = Field(..., description="Tactics2D是否可用")
    active_sessions: int = Field(..., description="活跃会话数")
    websocket_connections: int = Field(..., description="WebSocket连接数")
    uptime: str = Field(..., description="运行时间")
    memory_usage: Optional[str] = Field(None, description="内存使用情况")

# Three.js 可视化数据模型
class Vector3(BaseModel):
    """3D向量"""
    x: float
    y: float
    z: float = 0.0

class GeometryData(BaseModel):
    """几何体数据"""
    type: str = Field(..., description="几何体类型: LineString, Polygon等")
    coordinates: List[List[float]] = Field(..., description="坐标点数组")
    properties: Dict[str, Any] = Field(default_factory=dict, description="属性信息")

class VehicleData(BaseModel):
    """车辆数据"""
    id: int = Field(..., description="车辆ID")
    position: Vector3 = Field(..., description="位置")
    rotation: Vector3 = Field(default_factory=lambda: Vector3(x=0, y=0, z=0), description="旋转角度")
    velocity: Vector3 = Field(default_factory=lambda: Vector3(x=0, y=0, z=0), description="速度向量")
    dimensions: Vector3 = Field(..., description="尺寸(长宽高)")
    color: str = Field("#ff0000", description="颜色")
    type: str = Field("car", description="车辆类型")

class MapData(BaseModel):
    """地图数据"""
    roads: List[GeometryData] = Field(default_factory=list, description="道路几何")
    lanes: List[GeometryData] = Field(default_factory=list, description="车道几何")
    boundaries: List[GeometryData] = Field(default_factory=list, description="边界几何")
    boundaries_info: Dict[str, Any] = Field(default_factory=dict, description="地图边界信息")

class FrameData(BaseModel):
    """单帧数据"""
    frame: int = Field(..., description="帧号")
    timestamp: int = Field(..., description="时间戳(毫秒)")
    vehicles: List[VehicleData] = Field(default_factory=list, description="车辆数据")
    map_data: Optional[MapData] = Field(None, description="地图数据(仅首帧)")

class SimulationData(BaseModel):
    """仿真数据"""
    session_id: str = Field(..., description="会话ID")
    map_data: MapData = Field(..., description="完整地图数据")
    total_frames: int = Field(..., description="总帧数")
    frame_step: int = Field(..., description="帧步长")
    timestamp_range: Tuple[int, int] = Field(..., description="时间戳范围")
    participants_info: List[ParticipantInfo] = Field(..., description="参与者信息")

class SimulationInitResponse(BaseModel):
    """响应：仿真初始化"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="用户友好的消息")
    session_id: Optional[str] = Field(None, description="成功时创建的会话ID")
    map_data: Optional[MapData] = Field(None, description="成功时返回的地图数据")
    config: Optional[Dict[str, Any]] = Field(None, description="用于初始化的配置")
    error: Optional[str] = Field(None, description="失败时的错误详情")

class DatasetParseResponse(BaseModel):
    """数据集解析响应"""
    session_id: str = Field(..., description="会话ID")
    dataset: str = Field(..., description="数据集类型") 
    file_id: int = Field(..., description="文件ID")
    total_frames: int = Field(..., description="总帧数")
    participant_count: int = Field(..., description="参与者数量")
    duration_seconds: float = Field(..., description="总时长(秒)")
    timestamp_range: Tuple[int, int] = Field(..., description="时间戳范围")
    participants: List[ParticipantInfo] = Field(..., description="参与者列表")
    status: StatusEnum = Field(..., description="解析状态")
    message: str = Field("", description="状态消息")

class TrajectoryFrame(BaseModel):
    """单帧轨迹数据"""
    frame_number: int = Field(..., description="帧号")
    timestamp: int = Field(..., description="时间戳(毫秒)")
    vehicles: List[Dict[str, Any]] = Field(..., description="车辆数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class SessionInfoResponse(BaseModel):
    """会话信息响应"""
    success: bool = Field(..., description="操作是否成功")
    session_id: str = Field(..., description="会话ID")
    map_data: MapData = Field(..., description="地图数据")
    total_frames: int = Field(..., description="总帧数")
    frame_step: int = Field(..., description="帧步长")
    config: Dict[str, Any] = Field(..., description="仿真配置")
    created_at: float = Field(..., description="创建时间戳")
    participant_count: int = Field(0, description="参与者数量")
    message: str = Field("Session info retrieved successfully", description="状态消息")
