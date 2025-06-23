from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse
import os
import shutil
import time
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

# 导入WebSocket相关服务
from app.api.websocket import router as websocket_router
from app.config import settings

# 导入地图相关的工具
from app.utils.tactics2d_wrapper import tactics2d_wrapper
from app.utils.simple_formatter import data_formatter

# 设置日志
logger = logging.getLogger(__name__)

# 🚀 应用入口点
# 导入tactics2d
try:
    from tactics2d.dataset_parser import LevelXParser
    TACTICS2D_AVAILABLE = True
except ImportError as e:
    TACTICS2D_AVAILABLE = False
    IMPORT_ERROR = str(e)

app = FastAPI(
    title="Tactics2D Test API",
    description="测试tactics2d.dataset_parser.LevelXParser",
    version="0.1.0"
)

# 数据文件夹路径
DATA_FOLDER = Path(__file__).parent.parent / "data" / "LevelX" / "highD" / "data"

# 添加CORS中间件支持前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册WebSocket路由
app.include_router(websocket_router)

# 简化的数据模型 - MVP版本
class OSMUploadResponse(BaseModel):
    success: bool
    message: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None

# 数据集初始化请求模型
class DatasetInitRequest(BaseModel):
    dataset: str  # 数据集类型
    file_id: int  # 文件ID 
    dataset_path: str  # 数据集路径
    map_path: str  # OSM地图文件路径
    stamp_start: Optional[int] = None  # 起始时间戳
    stamp_end: Optional[int] = None  # 结束时间戳
    perception_range: int = 50  # 感知范围
    frame_step: int = 40  # 帧步长
    max_duration_ms: Optional[int] = None  # 最大持续时间（毫秒）

# 数据集初始化响应模型
class DatasetInitResponse(BaseModel):
    success: bool
    message: str
    config: Optional[dict] = None
    error: Optional[str] = None

# 全局变量存储当前地图状态
current_map = {
    "file_path": None,
    "parsed_data": None,
    "uploaded_at": None
}

@app.get("/")
async def root():
    return {
        "message": "Tactics2D Test API", 
        "tactics2d_available": TACTICS2D_AVAILABLE,
        "data_folder": str(DATA_FOLDER),
        "data_folder_exists": DATA_FOLDER.exists()
    }

@app.get("/check-tactics2d")
async def check_tactics2d():
    """检查tactics2d是否可用"""
    if not TACTICS2D_AVAILABLE:
        return {
            "available": False,
            "error": IMPORT_ERROR,
            "suggestion": "请运行: pip install tactics2d"
        }
    
    return {
        "available": True,
        "parser_class": str(LevelXParser),
        "message": "tactics2d.dataset_parser.LevelXParser 可用"
    }

@app.get("/list-data-files")
async def list_data_files():
    """列出可用的数据文件"""
    if not DATA_FOLDER.exists():
        raise HTTPException(status_code=404, detail=f"数据文件夹不存在: {DATA_FOLDER}")
    
    files = []
    for file in DATA_FOLDER.glob("*.csv"):
        files.append({
            "name": file.name,
            "size": file.stat().st_size,
            "type": "tracks" if "tracks" in file.name else "meta"
        })
    
    return {
        "data_folder": str(DATA_FOLDER),
        "total_files": len(files),
        "files": sorted(files, key=lambda x: x["name"])
    }

@app.get("/test-parser/{file_id}")
async def test_parser(file_id: int):
    """测试LevelXParser解析指定文件的基本功能"""
    if not TACTICS2D_AVAILABLE:
        raise HTTPException(status_code=500, detail="tactics2d不可用")
    
    if not DATA_FOLDER.exists():
        raise HTTPException(status_code=404, detail=f"数据文件夹不存在: {DATA_FOLDER}")
    
    try:
        # 初始化解析器
        parser = LevelXParser("highD")
        
        # 获取时间范围 - 确保转换为 Python int
        stamp_range = parser.get_stamp_range(file_id, str(DATA_FOLDER))
        stamp_range = (int(stamp_range[0]), int(stamp_range[1]))  # 转换 numpy.int64 -> int
        
        # 获取位置信息 - 确保转换为 Python int
        location_id = parser.get_location(file_id, str(DATA_FOLDER))
        location_id = int(location_id)  # 转换 numpy.int64 -> int
        
        # 解析轨迹数据（只解析很短的时间段来测试）
        test_duration = 200  # 200毫秒
        test_stamp_range = (stamp_range[0], min(stamp_range[0] + test_duration, stamp_range[1]))
        
        participants, actual_range = parser.parse_trajectory(
            file_id, 
            str(DATA_FOLDER), 
            stamp_range=test_stamp_range
        )
        
        # 确保 actual_range 也是 Python int
        actual_range = (int(actual_range[0]), int(actual_range[1]))
        
        # 分析participants数据结构
        participant_count = len(participants)
        participant_info = {}
        
        if participants:
            # 获取第一个参与者的详细信息
            first_key = list(participants.keys())[0]
            # 确保 key 是 JSON 可序列化的
            if hasattr(first_key, 'item'):  # 如果是 numpy 类型
                first_key = first_key.item()
            else:
                first_key = int(first_key)
                
            first_participant = participants[list(participants.keys())[0]]
            
            # 安全地获取属性信息，避免序列化问题
            safe_attributes = []
            for attr in dir(first_participant):
                if not attr.startswith('_') and len(safe_attributes) < 15:  # 限制数量
                    try:
                        value = getattr(first_participant, attr)
                        # 只记录简单类型的属性，并确保类型安全
                        if isinstance(value, (int, float, str, bool)):
                            safe_attributes.append({
                                "name": attr,
                                "type": str(type(value).__name__),
                                "value": str(value)[:100]  # 限制长度
                            })
                        elif isinstance(value, (list, tuple)):
                            safe_attributes.append({
                                "name": attr,
                                "type": str(type(value).__name__),
                                "value": f"length_{len(value)}"
                            })
                        else:
                            safe_attributes.append({
                                "name": attr,
                                "type": str(type(value).__name__),
                                "value": "complex_object"
                            })
                    except Exception:
                        safe_attributes.append({
                            "name": attr,
                            "type": "unknown",
                            "value": "access_error"
                        })
            
            participant_info = {
                "sample_participant_id": first_key,
                "participant_type": type(first_participant).__name__,
                "total_attributes": len(safe_attributes),
                "attributes": safe_attributes,
                "str_representation": str(first_participant)[:300] + "..." if len(str(first_participant)) > 300 else str(first_participant)
            }
        
        # 确保所有participant IDs都是JSON可序列化的
        participant_ids_safe = []
        for pid in list(participants.keys())[:10]:
            if hasattr(pid, 'item'):  # numpy类型
                participant_ids_safe.append(pid.item())
            else:
                participant_ids_safe.append(int(pid))
        
        return {
            "success": True,
            "file_id": file_id,
            "parser_dataset": "highD",
            "location_id": location_id,
            "timestamp_info": {
                "full_range_ms": stamp_range,
                "full_duration_ms": stamp_range[1] - stamp_range[0],
                "test_range_ms": test_stamp_range,
                "actual_parsed_range_ms": actual_range
            },
            "participant_analysis": {
                "total_participants": participant_count,
                "participant_ids": participant_ids_safe,
                "sample_participant": participant_info
            }
        }
        
    except Exception as e:
        # 详细的错误信息，帮助调试
        import traceback
        return {
            "success": False,
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()[-1000:]  # 最后1000字符
            },
            "test_context": {
                "file_id": file_id,
                "data_folder": str(DATA_FOLDER),
                "tactics2d_available": TACTICS2D_AVAILABLE
            }
        }

@app.get("/test-all-files")
async def test_all_files():
    """测试多个数据文件的基本信息（不进行完整解析）"""
    if not TACTICS2D_AVAILABLE:
        raise HTTPException(status_code=500, detail="tactics2d不可用")
    
    if not DATA_FOLDER.exists():
        raise HTTPException(status_code=404, detail=f"数据文件夹不存在: {DATA_FOLDER}")
    
    # 查找所有tracks文件
    track_files = []
    for file in DATA_FOLDER.glob("*_tracks.csv"):
        try:
            file_id = int(file.name.split("_")[0])
            track_files.append(file_id)
        except ValueError:
            continue
    
    results = []
    # 只测试前3个文件，避免长时间等待
    for file_id in sorted(track_files)[:3]:
        try:
            parser = LevelXParser("highD")
            
            # 只获取基本信息，不解析轨迹数据
            stamp_range = parser.get_stamp_range(file_id, str(DATA_FOLDER))
            location_id = parser.get_location(file_id, str(DATA_FOLDER))
            
            # 确保类型安全
            stamp_range = (int(stamp_range[0]), int(stamp_range[1]))
            location_id = int(location_id)
            
            results.append({
                "file_id": file_id,
                "location_id": location_id,
                "timestamp_range": stamp_range,
                "duration_seconds": float((stamp_range[1] - stamp_range[0]) / 1000.0),
                "success": True,
                "error": None
            })
            
        except Exception as e:
            results.append({
                "file_id": file_id,
                "location_id": None,
                "timestamp_range": None,
                "duration_seconds": None,
                "success": False,
                "error": str(e)
            })
    
    return {
        "summary": {
            "total_files_found": len(track_files),
            "files_tested": len(results),
            "successful_tests": len([r for r in results if r["success"]]),
            "failed_tests": len([r for r in results if not r["success"]])
        },
        "available_file_ids": sorted(track_files),
        "test_results": results
    }

# 新增：简单测试接口，只检查基本功能
@app.get("/quick-test")
async def quick_test():
    """快速测试LevelXParser基本功能"""
    if not TACTICS2D_AVAILABLE:
        return {"error": "tactics2d未安装或导入失败"}
    
    try:
        # 测试解析器初始化
        parser = LevelXParser("highD")
        
        # 检查数据文件夹
        if not DATA_FOLDER.exists():
            return {
                "parser_init": "success",
                "data_folder": "missing",
                "message": f"数据文件夹不存在: {DATA_FOLDER}"
            }
        
        # 检查第一个文件
        first_file = list(DATA_FOLDER.glob("01_tracks.csv"))
        if not first_file:
            return {
                "parser_init": "success", 
                "data_folder": "exists",
                "first_file": "missing",
                "message": "找不到01_tracks.csv文件"
            }
        
        # 尝试获取基本信息
        stamp_range = parser.get_stamp_range(1, str(DATA_FOLDER))
        location_id = parser.get_location(1, str(DATA_FOLDER))
        
        # 确保类型安全 - 转换 numpy 类型为 Python 原生类型
        stamp_range = (int(stamp_range[0]), int(stamp_range[1]))
        location_id = int(location_id)
        
        return {
            "parser_init": "success",
            "data_folder": "exists", 
            "first_file": "exists",
            "basic_parsing": "success",
            "sample_data": {
                "location_id": location_id,
                "timestamp_range": stamp_range,
                "duration_seconds": float((stamp_range[1] - stamp_range[0]) / 1000.0)
            }
        }
        
    except Exception as e:
        return {
            "parser_init": "unknown",
            "error": str(e),
            "error_type": type(e).__name__
        }

# 🚀 MVP功能：OSM文件上传和解析
@app.post("/api/upload-osm")
async def upload_osm_file(file: UploadFile = File(...)):
    """上传OSM文件 - MVP核心功能"""
    try:
        # 验证文件类型
        if not file.filename.endswith('.osm'):
            return OSMUploadResponse(
                success=False,
                message="只支持.osm格式的文件"
            )
        
        # 创建上传目录
        upload_dir = Path("/home/quinn/APP/Code/tactics2d-web/backend/data/uploaded_maps")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        # 更新全局地图状态
        from datetime import datetime
        current_map.update({
            "file_path": str(file_path),
            "parsed_data": None,  # 将在WebSocket中解析
            "uploaded_at": datetime.now().isoformat()
        })
        
        print(f"🗺️ [UPLOAD] OSM文件上传成功: {file_path}")
        print(f"📊 [UPLOAD] 文件大小: {file_size} bytes")
        
        return OSMUploadResponse(
            success=True,
            message=f"OSM文件 '{file.filename}' 上传成功",
            file_path=str(file_path),
            file_size=file_size
        )
        
    except Exception as e:
        print(f"❌ [UPLOAD] 文件上传失败: {e}")
        return OSMUploadResponse(
            success=False,
            message=f"文件上传失败: {str(e)}"
        )

@app.get("/api/current-map")
async def get_current_map():
    """获取当前地图状态"""
    if current_map["file_path"]:
        return {
            "success": True,
            "has_map": True,
            "file_path": current_map["file_path"],
            "uploaded_at": current_map["uploaded_at"],
            "parsed": current_map["parsed_data"] is not None
        }
    else:
        return {
            "success": True,
            "has_map": False,
            "message": "未上传地图文件"
        }

@app.get("/api/map")
async def get_map_data():
    """HTTP API: 获取地图数据 - 使用真实OSM解析或模拟数据"""
    
    try:
        # 检查是否有已上传的地图
        if current_map["file_path"] and Path(current_map["file_path"]).exists():
            print(f"🗺️  [HTTP] 使用真实OSM地图: {current_map['file_path']}")
            
            # 如果已经解析过，直接返回缓存数据
            if current_map["parsed_data"]:
                map_data = data_formatter.format_map_data(current_map["parsed_data"])
                print(f"📤 [HTTP] 返回缓存的地图数据")
                return {
                    "success": True,
                    "source": "cached_osm",
                    "data": map_data,
                    "file_path": current_map["file_path"]
                }
            
            # 尝试解析OSM地图
            try:
                print(f"🔄 [HTTP] 开始解析OSM地图")
                map_info = tactics2d_wrapper.parse_osm_map_simple(current_map["file_path"])
                current_map["parsed_data"] = map_info
                
                map_data = data_formatter.format_map_data(map_info)
                
                print(f"✅ [HTTP] OSM地图解析成功:")
                print(f"   - roads: {len(map_data.get('roads', []))}")
                print(f"   - lanes: {len(map_data.get('lanes', []))}")
                print(f"   - boundaries: {len(map_data.get('boundaries', []))}")
                
                return {
                    "success": True,
                    "source": "real_osm",
                    "data": map_data,
                    "file_path": current_map["file_path"],
                    "metadata": {
                        "roads_count": len(map_data.get('roads', [])),
                        "lanes_count": len(map_data.get('lanes', [])),
                        "boundaries_count": len(map_data.get('boundaries', []))
                    }
                }
                
            except Exception as osm_error:
                print(f"❌ [HTTP] OSM地图解析失败，回退到模拟数据: {osm_error}")
                # 解析失败时回退到模拟数据
        
        # 使用模拟数据（没有地图文件或解析失败时）
        print(f"🗺️  [HTTP] 使用模拟地图数据进行测试")
        
        mock_map_info = {
            "roads": [
                {
                    "id": "highway_main",
                    "coordinates": [[0, 0], [100, 0], [200, 5], [300, 0]],
                    "width": 12.0
                }
            ],
            "lanes": [
                {
                    "id": "lane_1",
                    "coordinates": [[0, -3], [100, -3], [200, 2], [300, -3]],
                    "width": 3.5,
                    "subtype": "solid"
                },
                {
                    "id": "lane_2", 
                    "coordinates": [[0, 3], [100, 3], [200, 8], [300, 3]],
                    "width": 3.5,
                    "subtype": "dashed"
                }
            ],
            "boundaries": [
                {
                    "id": "left_boundary",
                    "coordinates": [[0, -6], [100, -6], [200, -1], [300, -6]]
                },
                {
                    "id": "right_boundary", 
                    "coordinates": [[0, 6], [100, 6], [200, 11], [300, 6]]
                }
            ]
        }
        
        map_data = data_formatter.format_map_data(mock_map_info)
        
        print(f"📊 [HTTP] 模拟地图数据统计:")
        print(f"   - roads: {len(map_data.get('roads', []))}")
        print(f"   - lanes: {len(map_data.get('lanes', []))}")
        print(f"   - boundaries: {len(map_data.get('boundaries', []))}")
        print(f"📤 [HTTP] 返回模拟地图数据")
        
        return {
            "success": True,
            "source": "mock_data",
            "data": map_data,
            "metadata": {
                "roads_count": len(map_data.get('roads', [])),
                "lanes_count": len(map_data.get('lanes', [])),
                "boundaries_count": len(map_data.get('boundaries', []))
            }
        }
            
    except Exception as e:
        print(f"❌ [HTTP] 地图数据获取失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "source": "error"
        }

@app.post("/api/simulation/initialize")
async def initialize_simulation(request: DatasetInitRequest):
    """初始化仿真数据处理 - 处理前端表单提交的OSM和数据集配置"""
    try:
        print(f"🚀 [INIT] 收到仿真初始化请求")
        print(f"   - 数据集类型: {request.dataset}")
        print(f"   - 文件ID: {request.file_id}")
        print(f"   - 数据集路径: {request.dataset_path}")
        print(f"   - 地图文件路径: {request.map_path}")
        print(f"   - 感知范围: {request.perception_range}m")
        print(f"   - 帧步长: {request.frame_step}")
        
        # 验证OSM地图文件是否存在
        if not Path(request.map_path).exists():
            print(f"❌ [INIT] OSM地图文件不存在: {request.map_path}")
            return DatasetInitResponse(
                success=False,
                message=f"OSM地图文件不存在: {request.map_path}",
                error="file_not_found"
            )
        
        # 验证数据集路径是否存在
        if not Path(request.dataset_path).exists():
            print(f"❌ [INIT] 数据集路径不存在: {request.dataset_path}")
            return DatasetInitResponse(
                success=False,
                message=f"数据集路径不存在: {request.dataset_path}",
                error="dataset_path_not_found"
            )
        
        # 更新全局地图状态
        current_map["file_path"] = request.map_path
        current_map["uploaded_at"] = "now"
        current_map["parsed_data"] = None  # 标记需要重新解析
        
        # 验证Tactics2D是否可用
        if not tactics2d_wrapper.is_available():
            print(f"⚠️  [INIT] Tactics2D不可用，仅能提供基础功能")
            return DatasetInitResponse(
                success=True,
                message="配置已保存，但Tactics2D不可用，仅提供基础可视化功能",
                config={
                    "dataset": request.dataset,
                    "file_id": request.file_id,
                    "map_path": request.map_path,
                    "dataset_path": request.dataset_path,
                    "tactics2d_available": False
                }
            )
        
        # 尝试解析OSM地图
        try:
            print(f"🗺️  [INIT] 开始解析OSM地图: {request.map_path}")
            map_info = tactics2d_wrapper.parse_osm_map_simple(request.map_path)
            current_map["parsed_data"] = map_info
            
            print(f"✅ [INIT] OSM地图解析成功:")
            print(f"   - 道路数量: {len(map_info.get('roads', []))}")
            print(f"   - 车道数量: {len(map_info.get('lanes', []))}")
            print(f"   - 边界数量: {len(map_info.get('boundaries', []))}")
            
        except Exception as e:
            print(f"❌ [INIT] OSM地图解析失败: {e}")
            return DatasetInitResponse(
                success=False,
                message=f"OSM地图解析失败: {str(e)}",
                error="osm_parse_error"
            )
        
        # 尝试初始化数据集解析器（如果可用）
        try:
            from tactics2d.dataset_parser import LevelXParser
            parser = LevelXParser(request.dataset)
            
            # 验证文件ID是否有效
            stamp_range = parser.get_stamp_range(request.file_id, request.dataset_path)
            print(f"📊 [INIT] 数据集验证成功:")
            print(f"   - 时间戳范围: {stamp_range}")
            
        except Exception as e:
            print(f"⚠️  [INIT] 数据集解析器初始化失败: {e}")
            # 不返回错误，因为地图已经成功解析
        
        # 成功响应
        success_config = {
            "dataset": request.dataset,
            "file_id": request.file_id,
            "map_path": request.map_path,
            "dataset_path": request.dataset_path,
            "perception_range": request.perception_range,
            "frame_step": request.frame_step,
            "stamp_start": request.stamp_start,
            "stamp_end": request.stamp_end,
            "tactics2d_available": True,
            "map_parsed": True
        }
        
        print(f"✅ [INIT] 仿真初始化完成")
        
        return DatasetInitResponse(
            success=True,
            message="数据集和地图配置成功，可以开始可视化",
            config=success_config
        )
        
    except Exception as e:
        print(f"❌ [INIT] 仿真初始化失败: {e}")
        return DatasetInitResponse(
            success=False,
            message=f"仿真初始化失败: {str(e)}",
            error="initialization_error"
        )

@app.post("/api/dataset/parse")
async def parse_dataset(request: DatasetInitRequest):
    """解析数据集并创建仿真会话"""
    try:
        logger.info(f"🚀 开始解析数据集: {request.dataset}, 文件ID: {request.file_id}")
        
        # 验证数据集路径
        if not Path(request.dataset_path).exists():
            raise HTTPException(
                status_code=404, 
                detail=f"数据集路径不存在: {request.dataset_path}"
            )
        
        # 验证Tactics2D可用性
        if not tactics2d_wrapper.is_available():
            raise HTTPException(
                status_code=500,
                detail="Tactics2D库不可用，无法解析数据集"
            )
        
        # 设置解析参数
        max_duration_ms = getattr(request, 'max_duration_ms', 5000)  # 默认5秒
        
        # 解析数据集
        session_data = tactics2d_wrapper.parse_dataset_for_session(
            dataset=request.dataset,
            file_id=request.file_id,
            data_folder=request.dataset_path,
            max_duration_ms=max_duration_ms
        )
        
        # 生成会话ID
        session_id = f"session_{request.dataset}_{request.file_id}_{int(time.time())}"
        
        # 构建响应数据
        response_data = {
            "session_id": session_id,
            "dataset": request.dataset,
            "file_id": request.file_id,
            "total_frames": session_data["session_data"]["total_frames"],
            "participant_count": session_data["session_data"]["participant_count"],
            "duration_seconds": session_data["session_data"]["duration_seconds"],
            "timestamp_range": session_data["session_data"]["timestamp_range"],
            "participants": session_data["session_data"]["participants"],
            "status": "success",
            "message": f"成功解析数据集，共{session_data['session_data']['participant_count']}个参与者"
        }
        
        # 将轨迹数据存储到全局状态（实际项目中应该用数据库或缓存）
        # 这里简化存储到全局变量
        if not hasattr(app.state, 'sessions'):
            app.state.sessions = {}
        
        app.state.sessions[session_id] = {
            "session_data": session_data["session_data"],
            "trajectory_frames": session_data["trajectory_frames"],
            "created_at": time.time()
        }
        
        logger.info(f"✅ 数据集解析完成，会话ID: {session_id}")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ 数据集解析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    if not hasattr(app.state, 'sessions') or session_id not in app.state.sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session = app.state.sessions[session_id]
    return {
        "session_id": session_id,
        "session_data": session["session_data"],
        "created_at": session["created_at"],
        "frame_count": len(session["trajectory_frames"])
    }

@app.get("/api/session/{session_id}/frame/{frame_number}")
async def get_session_frame(session_id: str, frame_number: int):
    """获取会话的指定帧数据"""
    if not hasattr(app.state, 'sessions') or session_id not in app.state.sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session = app.state.sessions[session_id]
    frame_key = str(frame_number)
    
    if frame_key not in session["trajectory_frames"]:
        raise HTTPException(status_code=404, detail=f"帧 {frame_number} 不存在")
    
    return session["trajectory_frames"][frame_key]