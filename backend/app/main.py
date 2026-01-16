from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import uuid
import time
from pathlib import Path
from typing import Optional
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

# 配置日志 - 确保能在终端看到输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到终端
    ]
)

# 导入项目模块
from app.api.websocket import router as websocket_router
from app.config import settings
from app.services.map_service import map_service
from app.services.dataset_parser_service import dataset_parser_service
from app.services.data_scan_service import data_scan_service
from app.models.requests import DatasetConfig
from app.models.responses import (
    SimulationInitResponse, 
    MapData, 
    SessionInfoResponse,
    DataFilesResponse,
    MapFileInfo,
    DatasetFileInfo
)
from app.utils.simple_formatter import data_formatter
import app.state as state  # 导入全局状态模块
from fastapi.staticfiles import StaticFiles

# 设置日志
logger = logging.getLogger(__name__)

# 强制设置日志级别
logger.setLevel(logging.INFO)

# 测试日志输出
logger.info("🚀 Tactics2D Web API 启动中...")
logger.info("📝 日志系统已配置并正常工作")

# 🚀 应用入口点
# 检查Tactics2D库是否可用
try:
    from tactics2d.dataset_parser import LevelXParser
    TACTICS2D_AVAILABLE = True
except ImportError as e:
    TACTICS2D_AVAILABLE = False
    IMPORT_ERROR = str(e)

app = FastAPI(
    title="Tactics2D Web API",
    description="A web server to run and visualize Tactics2D simulations.",
    version="0.2.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册WebSocket路由
app.include_router(websocket_router)

# 静态文件服务 - 用于提供预览图
# 注意：这允许访问 data 目录下的文件，仅用于开发环境
if settings.DEBUG:
    try:
        # ⚠️ FastAPI 的 CORSMiddleware 不会自动应用到 mount 的子应用（StaticFiles）
        # 但 Three.js 贴图属于 WebGL 资源，跨域时必须有正确的 CORS 响应头，否则会加载失败并导致前端崩溃。
        static_app = StaticFiles(directory=str(settings.DATA_DIR))
        static_app = StarletteCORSMiddleware(
            static_app,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.mount("/static/data", static_app, name="data")
    except Exception as e:
        logger.warning(f"无法挂载静态文件服务: {e}")

@app.get("/api/data/files", response_model=DataFilesResponse)
async def get_data_files(dataset_type: Optional[str] = None):
    """
    获取可用的地图文件和数据集文件列表
    
    Args:
        dataset_type: 可选，指定数据集类型（如 "highD"），如果不指定则返回所有类型
        
    Returns:
        包含地图文件列表和数据集文件列表的响应
    """
    try:
        # 扫描地图文件
        map_files = data_scan_service.scan_map_files()
        map_info_list = [
            MapFileInfo(id=m.id, path=m.path, name=m.name)
            for m in map_files
        ]
        
        # 扫描数据集文件
        dataset_info_dict = {}
        
        if dataset_type:
            # 只扫描指定类型
            dataset_files = data_scan_service.scan_dataset_files(dataset_type)
            dataset_info_dict[dataset_type] = [
                DatasetFileInfo(
                    file_id=d.file_id,
                    dataset_path=d.dataset_path,
                    preview_image=f"/static/data/LevelX/{dataset_type}/data/{d.file_id:02d}_highway.png" if d.preview_image else None,
                    has_tracks=d.has_tracks,
                    has_meta=d.has_meta,
                    duration_ms=getattr(d, "duration_ms", None)
                )
                for d in dataset_files
            ]
        else:
            # 扫描所有支持的数据集类型
            for ds_type in settings.SUPPORTED_DATASETS:
                dataset_files = data_scan_service.scan_dataset_files(ds_type)
                dataset_info_dict[ds_type] = [
                    DatasetFileInfo(
                        file_id=d.file_id,
                        dataset_path=d.dataset_path,
                        preview_image=f"/static/data/LevelX/{ds_type}/data/{d.file_id:02d}_highway.png" if d.preview_image else None,
                        has_tracks=d.has_tracks,
                        has_meta=d.has_meta,
                        duration_ms=getattr(d, "duration_ms", None)
                    )
                    for d in dataset_files
                ]
        
        return DataFilesResponse(
            maps=map_info_list,
            datasets=dataset_info_dict
        )
    except Exception as e:
        logger.error(f"扫描数据文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"扫描数据文件失败: {e}")

@app.get("/")
async def root():
    return {
        "message": "Tactics2D Web API is running",
        "tactics2d_available": TACTICS2D_AVAILABLE,
        "version": app.version
    }

@app.post("/api/simulation/initialize", response_model=SimulationInitResponse)
async def initialize_simulation(request: DatasetConfig):
    """
    HTTP POST: 初始化一个新的仿真会话。
    1. 验证输入配置。
    2. 解析OSM地图文件。
    3. 解析轨迹数据集。
    4. 创建并存储会话状态。
    5. 返回会话ID和格式化的地图数据。
    """
    # 强制输出到终端 - 确保能看到
    print("🔥 FastAPI 收到了仿真初始化请求!")
    print(f"📥 请求数据: {request.dict()}")
    
    # 打印接收到的请求数据
    logger.info("=" * 80)
    logger.info("� 开始处理仿真初始化请求")
    logger.info(f"📥 接收到的请求数据: {request.dict()}")
    logger.info("=" * 80)

    # 验证地图和数据集文件路径
    map_path = Path(request.map_path)
    dataset_path = Path(request.dataset_path)
    if not map_path.exists():
        logger.error(f"❌ Map file not found: {map_path}")
        raise HTTPException(status_code=404, detail=f"Map file not found: {map_path}")
    if not dataset_path.exists():
        logger.error(f"❌ Dataset path not found: {dataset_path}")
        raise HTTPException(status_code=404, detail=f"Dataset path not found: {dataset_path}")

    # 解析地图
    try:
        logger.info(f"🗺️ Parsing OSM map: {map_path}")
        map_info = map_service.parse_osm_map_simple(str(map_path))
        formatted_map_data = data_formatter.format_map_data(map_info)
        
        # 获取地图的坐标缩放比例，用于统一车辆和地图的坐标系统
        coordinate_scale = map_info.get('metadata', {}).get('coordinate_scale', 1.0)
        logger.info(f"✅ Map parsed successfully. Found {len(formatted_map_data.get('lanes', []))} lanes.")
        logger.info(f"📏 地图坐标缩放比例: {coordinate_scale}")
    except Exception as e:
        logger.error(f"❌ Failed to parse map file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse map file: {e}")

    # 解析轨迹数据
    if not TACTICS2D_AVAILABLE:
        raise HTTPException(status_code=503, detail="Tactics2D library is not available on the server.")
    
    try:
        logger.info("🔄 开始解析轨迹数据...")
        logger.info(f"   📂 数据集类型: {request.dataset}")
        logger.info(f"   📄 文件ID: {request.file_id}")
        logger.info(f"   📍 数据路径: {dataset_path}")
        logger.info(f"   ⏱️ 帧步长: {request.frame_step}")
        
        # ⚠️ 修复：使用 is not None 而不是直接判断，因为 0 是有效值
        # 如果使用 if request.stamp_start，当 stamp_start = 0 时会被误判为 False
        has_time_range = request.stamp_start is not None and request.stamp_end is not None
        if has_time_range:
            logger.info(f"   🕐 时间范围: ({request.stamp_start}, {request.stamp_end})")
        else:
            logger.info(f"   🕐 时间范围: None (全部)")
        
        # 处理max_duration_ms：如果设置了时间范围，限制最大时长
        stamp_range = None
        if has_time_range:
            stamp_range = (request.stamp_start, request.stamp_end)
            # 如果设置了max_duration_ms，限制时间范围
            if request.max_duration_ms is not None and (request.stamp_end - request.stamp_start) > request.max_duration_ms:
                stamp_range = (request.stamp_start, request.stamp_start + request.max_duration_ms)
                logger.info(f"⏱️ 时间范围已限制为 {request.max_duration_ms}ms")
        
        session_data = dataset_parser_service.parse_dataset_for_session(
            dataset=request.dataset,
            file_id=request.file_id,
            dataset_path=str(dataset_path),
            frame_step=request.frame_step,
            stamp_range=stamp_range,
            max_duration_ms=request.max_duration_ms,
            perception_range=request.perception_range if request.perception_range and request.perception_range > 0 else None,
            coordinate_scale=coordinate_scale  # 传递地图的坐标缩放比例
        )
        
        # 详细记录解析结果
        logger.info("=" * 60)
        logger.info("📊 轨迹数据解析结果:")
        if session_data:
            logger.info(f"   ✅ 解析状态: 成功")
            logger.info(f"   🎬 总帧数: {session_data.get('total_frames', 0)}")
            logger.info(f"   👥 参与者数量: {session_data.get('participant_count', 0)}")
            logger.info(f"   📏 帧步长: {session_data.get('frame_step', 0)}")
            
            frames = session_data.get("frames", {})
            if frames:
                frame_keys = list(frames.keys())
                logger.info(f"   🔢 帧索引范围: {min(frame_keys)} 到 {max(frame_keys)}")
                # 显示前几帧的内容样例
                sample_frame_key = frame_keys[0] if frame_keys else None
                if sample_frame_key is not None:
                    sample_frame = frames[sample_frame_key]
                    vehicle_count = len(sample_frame.get('vehicles', []))
                    logger.info(f"   🚗 第一帧车辆数: {vehicle_count}")
                    if vehicle_count > 0:
                        first_vehicle = sample_frame['vehicles'][0]
                        logger.info(f"   📋 车辆样例: ID={first_vehicle.get('id')}, 位置=({first_vehicle.get('x'):.2f}, {first_vehicle.get('y'):.2f})")
            else:
                logger.warning("   ⚠️ 帧数据为空!")
        else:
            logger.error("   ❌ 解析状态: 失败 - session_data 为空")
        logger.info("=" * 60)
        
        if not session_data or not session_data.get("frames"):
            logger.warning("⚠️ 数据集解析没有产生任何帧数据!")
            raise HTTPException(status_code=404, detail="No trajectory data found for the given configuration.")
        
        logger.info(f"✅ 轨迹数据解析完成! 总帧数: {session_data.get('total_frames')}")

    except HTTPException:
        # 重新抛出HTTP异常，不要包装
        raise
    except Exception as e:
        logger.error(f"❌ 数据集解析时发生严重错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse dataset: {e}")

    # 创建并存储会话
    session_id = f"sid_{uuid.uuid4().hex[:8]}"
    
    # 存储会话数据
    state.sessions[session_id] = {
        "id": session_id,
        "config": request.dict(),
        "map_data": formatted_map_data,  # 存储地图数据以供后续获取
        "trajectory_frames": session_data.get("frames", {}),
        "total_frames": session_data.get("total_frames", 0),
        "frame_step": session_data.get("frame_step", request.frame_step),
        "participant_count": session_data.get("participant_count", 0),
        "created_at": time.time()
    }
    
    # 详细记录会话创建状态
    logger.info("=" * 60)
    logger.info("🎯 会话创建结果:")
    logger.info(f"   🆔 会话ID: {session_id}")
    logger.info(f"   📊 会话数据帧数: {len(session_data.get('frames', {}))}")
    logger.info(f"   💾 全局会话数量: {len(state.sessions)}")
    logger.info(f"   🕐 创建时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    logger.info("=" * 60)
    
    logger.info(f"✅ 会话 '{session_id}' 创建并存储成功!")

    # 返回成功响应
    response_data = {
        "success": True,
        "message": "Simulation session initialized successfully.",
        "session_id": session_id,
        "map_data": formatted_map_data,
        "config": request.dict()
    }
    
    # 记录最终响应状态
    logger.info("🚀 正在返回成功响应给前端:")
    logger.info(f"   ✅ 成功状态: {response_data['success']}")
    logger.info(f"   📨 消息: {response_data['message']}")
    logger.info(f"   🆔 会话ID: {response_data['session_id']}")
    logger.info(f"   🗺️ 地图数据大小: {len(str(formatted_map_data))} 字符")
    
    return SimulationInitResponse(**response_data)

@app.get("/api/simulation/session/{session_id}")
async def get_session_info(session_id: str):
    """
    HTTP GET: 获取指定会话的详细信息。
    包括地图数据、配置信息、轨迹元数据等。
    前端可以用这个API来获取会话相关的所有数据。
    """
    logger.info(f"🔍 获取会话信息请求: {session_id}")
    
    # 检查会话是否存在
    if session_id not in state.sessions:
        logger.error(f"❌ 会话不存在: {session_id}")
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    session_data = state.sessions[session_id]
    
    # 准备轨迹元数据
    trajectory_metadata = {
        "total_frames": session_data.get("total_frames", 0),
        "frame_step": session_data.get("frame_step", 1),
        "participant_count": session_data.get("participant_count", 0),
        "created_at": session_data.get("created_at", time.time())
    }
    
    # 准备响应数据
    response = {
        "success": True,
        "session_id": session_id,
        "map_data": session_data.get("map_data", {}),
        "trajectory_metadata": trajectory_metadata,
        "config": session_data.get("config", {}),
        "message": "Session info retrieved successfully"
    }
    
    logger.info(f"✅ 成功返回会话信息: {session_id}")
    logger.info(f"   📊 总帧数: {trajectory_metadata['total_frames']}")
    logger.info(f"   👥 参与者数: {trajectory_metadata['participant_count']}")
    logger.info(f"   🗺️ 地图数据大小: {len(str(response['map_data']))} 字符")
    
    return response

@app.get("/api/status")
async def get_status():
    """获取后端API和Tactics2D库的状态"""
    return {
        "status": "ok",
        "tactics2d_available": TACTICS2D_AVAILABLE,
        "import_error": IMPORT_ERROR if not TACTICS2D_AVAILABLE else None,
        "active_sessions": len(state.sessions)
    }