import uuid
import logging
import asyncio
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from ..services.websocket_manager import connection_manager
from ..models.requests import DatasetType
from ..utils.simple_formatter import data_formatter
from ..utils.tactics2d_wrapper import tactics2d_wrapper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/simulation")
async def websocket_simulation_endpoint(websocket: WebSocket):
    """WebSocket端点：仿真数据流"""
    
    # 生成唯一客户端ID
    client_id = str(uuid.uuid4())
    
    try:
        # 建立连接
        await connection_manager.connect(websocket, client_id)
        
        # 发送连接确认
        await connection_manager.send_personal_message({
            "type": "connected",
            "client_id": client_id,
            "message": "WebSocket connection established"
        }, client_id)
        
        # 处理消息循环
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_json()
                await handle_simulation_message(client_id, data)
                
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": str(e)
                }, client_id)
                
    except Exception as e:
        logger.error(f"WebSocket connection error for {client_id}: {e}")
    finally:
        # 清理连接
        connection_manager.disconnect(client_id)

async def handle_simulation_message(client_id: str, message_data: dict):
    """处理仿真相关的WebSocket消息"""
    
    message_type = message_data.get("type")
    
    if message_type == "ping":
        # 心跳检测
        await connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": message_data.get("timestamp")
        }, client_id)
        
    elif message_type == "get_frame":
        # 获取单帧Three.js数据
        frame = message_data.get("frame", 0)
        session_id = message_data.get("session_id")
        
        # 生成Three.js兼容的帧数据
        mock_participants = {
            f"vehicle_{i}": {
                "id": i,
                "type": "car",
                "position": [[i * 10 + frame, frame * 2, 0]],
                "velocity": [[2.0, 1.0, 0]],
                "rotation": [[0, 0, frame * 0.1]]
            }
            for i in range(5)
        }
        
        frame_data = data_formatter.format_trajectory_frame(
            participants_data=mock_participants,
            timestamp=frame * 40,  # 假设40ms间隔
            frame_number=frame
        )
        
        await connection_manager.send_personal_message({
            "type": "frame_data",
            "session_id": session_id,
            "data": frame_data,
            "status": "success"
        }, client_id)
        
    # 🚀 MVP核心功能：解析上传的OSM文件
    elif message_type == "parse_uploaded_osm":
        session_id = message_data.get("session_id", "default")
        
        try:
            # 从main.py导入当前地图状态
            from ..main import current_map
            
            if not current_map["file_path"]:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "session_id": session_id,
                    "message": "没有找到上传的OSM文件，请先上传文件"
                }, client_id)
                return
            
            osm_file_path = current_map["file_path"]
            print(f"🗺️  [WebSocket] 开始解析上传的OSM文件: {osm_file_path}")
            
            if tactics2d_wrapper.is_available():
                # 使用Tactics2D解析上传的OSM文件
                map_info = tactics2d_wrapper.parse_osm_map_simple(osm_file_path)
                
                # 打印解析结果
                print(f"📊 [WebSocket] 上传文件解析统计:")
                print(f"   - 道路数量: {len(map_info.get('roads', []))}")
                print(f"   - 车道数量: {len(map_info.get('lanes', []))}")
                print(f"   - 边界数量: {len(map_info.get('boundaries', []))}")
                
                # 格式化为前端数据
                map_data = data_formatter.format_map_data(map_info)
                
                # 保存解析结果到全局状态
                current_map["parsed_data"] = map_data
                
                print(f"🎯 [WebSocket] 上传文件格式化完成:")
                print(f"   - roads: {len(map_data.get('roads', []))}")
                print(f"   - lanes: {len(map_data.get('lanes', []))}")
                print(f"   - boundaries: {len(map_data.get('boundaries', []))}")
                print(f"📤 [WebSocket] 发送解析数据到前端 (大小: {len(str(map_data))} 字符)")
                
                await connection_manager.send_personal_message({
                    "type": "map_data",
                    "session_id": session_id,
                    "data": map_data,
                    "status": "success",
                    "message": f"上传的OSM文件解析成功",
                    "source": "uploaded_file",
                    "file_path": osm_file_path
                }, client_id)
                
            else:
                await connection_manager.send_personal_message({
                    "type": "error", 
                    "session_id": session_id,
                    "message": "Tactics2D不可用，无法解析OSM文件"
                }, client_id)
                
        except Exception as e:
            logger.error(f"解析上传OSM文件失败: {e}")
            await connection_manager.send_personal_message({
                "type": "error",
                "session_id": session_id,
                "message": f"OSM文件解析失败: {str(e)}"
            }, client_id)
        
    # 注意：地图数据现在通过 HTTP API (/api/map) 获取，不再通过WebSocket传输
    # 这样可以利用HTTP缓存机制，减少WebSocket连接压力
        
    elif message_type == "start_stream":
        # 开始数据流传输
        session_id = message_data.get("session_id", "default")
        fps = message_data.get("fps", 10)
        
        await connection_manager.send_personal_message({
            "type": "stream_started",
            "session_id": session_id,
            "message": "Three.js data streaming started"
        }, client_id)
        
        try:
            if tactics2d_wrapper.is_available():
                # 使用真实的轨迹数据
                data_folder = "/home/quinn/APP/Code/tactics2d-web/backend/data/LevelX/highD/data"
                
                if Path(data_folder).exists():
                    # 解析真实轨迹数据（专为Three.js优化）
                    print(f"🚗 开始解析真实轨迹数据: {data_folder}")
                    trajectory_data = tactics2d_wrapper.parse_trajectory_for_threejs(
                        "highD", 1, data_folder, max_duration_ms=2000
                    )
                    
                    frames = trajectory_data["frames"]
                    timestamps = trajectory_data["timestamps"]
                    
                    print(f"📊 轨迹数据统计:")
                    print(f"   - 总帧数: {len(timestamps)}")
                    print(f"   - 时间范围: {timestamps[0] if timestamps else 0} - {timestamps[-1] if timestamps else 0}")
                    print(f"   - 第一帧车辆数: {len(frames.get(str(timestamps[0]), {})) if timestamps else 0}")
                    
                    # 流式传输优化后的数据
                    for i, timestamp in enumerate(timestamps):
                        frame_participants = frames.get(str(timestamp), {})
                        
                        # 准备简化的轨迹数据格式
                        participants_data = {}
                        for pid, participant_data in frame_participants.items():
                            participants_data[pid] = {
                                "position": participant_data["position"],
                                "velocity": participant_data["velocity"],
                                "heading": participant_data.get("heading", 0),
                                "type": participant_data.get("type", "car")
                            }
                        
                        frame_data = data_formatter.format_trajectory_frame(
                            participants_data=participants_data,
                            timestamp=timestamp,
                            frame_number=i
                        )
                        
                        # 打印每10帧的数据信息
                        if i % 10 == 0:
                            print(f"📤 发送第 {i+1}/{len(timestamps)} 帧:")
                            print(f"   - 时间戳: {timestamp}")
                            print(f"   - 车辆数: {len(frame_data.get('vehicles', []))}")
                            if frame_data.get('vehicles'):
                                sample_vehicle = frame_data['vehicles'][0]
                                print(f"   - 示例车辆位置: {sample_vehicle.get('position')}")
                                print(f"   - 示例车辆速度: {sample_vehicle.get('velocity')}")
                        
                        message = data_formatter.create_websocket_message(frame_data, session_id)
                        await connection_manager.send_personal_message(message, client_id)
                        
                        await asyncio.sleep(1.0 / fps)
                    
                    await connection_manager.send_personal_message({
                        "type": "stream_completed",
                        "session_id": session_id,
                        "message": f"真实数据流完成，共传输 {len(timestamps)} 帧"
                    }, client_id)
                    
                else:
                    # 数据文件夹不存在，使用模拟数据
                    for frame in range(20):
                        mock_participants = {}
                        for i in range(3):
                            mock_participants[str(i)] = {
                                "position": [i * 8 + frame * 2, i * 2 + frame * 0.5],
                                "velocity": [2.0 + i * 0.5, 1.0],
                                "heading": frame * 0.05 + i * 0.1,
                                "type": ["car", "truck", "bus"][i % 3]
                            }
                        
                        frame_data = data_formatter.format_trajectory_frame(
                            participants_data=mock_participants,
                            timestamp=frame * (1000 // fps),
                            frame_number=frame
                        )
                        
                        message = data_formatter.create_websocket_message(frame_data, session_id)
                        await connection_manager.send_personal_message(message, client_id)
                        
                        await asyncio.sleep(1.0 / fps)
                        
                    await connection_manager.send_personal_message({
                        "type": "stream_completed",
                        "session_id": session_id,
                        "message": "模拟数据流完成（真实数据文件未找到）"
                    }, client_id)
            else:
                # Tactics2D不可用，使用基础模拟数据
                for frame in range(10):
                    mock_participants = {}
                    for i in range(2):
                        mock_participants[str(i)] = {
                            "position": [i * 10 + frame * 2, 0],
                            "velocity": [2.0, 0],
                            "heading": 0,
                            "type": "car"
                        }
                    
                    frame_data = data_formatter.format_trajectory_frame(
                        participants_data=mock_participants,
                        timestamp=frame * (1000 // fps),
                        frame_number=frame
                    )
                    
                    message = data_formatter.create_websocket_message(frame_data, session_id)
                    await connection_manager.send_personal_message(message, client_id)
                    
                    await asyncio.sleep(1.0 / fps)
                    
                await connection_manager.send_personal_message({
                    "type": "stream_completed",
                    "session_id": session_id,
                    "message": "基础模拟数据流完成（Tactics2D不可用）"
                }, client_id)
                
        except Exception as e:
            logger.error(f"数据流传输失败: {e}")
            await connection_manager.send_personal_message({
                "type": "error",
                "session_id": session_id,
                "message": f"数据流传输失败: {str(e)}"
            }, client_id)
        
    elif message_type == "start_session_stream":
        # 开始会话数据流传输
        session_id = message_data.get("session_id")
        fps = message_data.get("fps", 25)
        
        if not session_id:
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "缺少session_id参数"
            }, client_id)
            return
        
        try:
            # 从main.py的app.state获取会话数据
            from ..main import app
            
            if not hasattr(app.state, 'sessions') or session_id not in app.state.sessions:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "session_id": session_id,
                    "message": f"会话 {session_id} 不存在"
                }, client_id)
                return
            
            session = app.state.sessions[session_id]
            trajectory_frames = session["trajectory_frames"]
            frame_count = len(trajectory_frames)
            
            logger.info(f"🎬 开始流式传输会话数据: {session_id}, 共{frame_count}帧")
            
            await connection_manager.send_personal_message({
                "type": "session_stream_started",
                "session_id": session_id,
                "total_frames": frame_count,
                "message": f"开始传输会话数据，共{frame_count}帧"
            }, client_id)
            
            # 流式传输帧数据
            frame_interval = 1.0 / fps  # 秒
            
            for frame_number in range(frame_count):
                frame_key = str(frame_number)
                if frame_key in trajectory_frames:
                    frame_data = trajectory_frames[frame_key]
                    
                    # 发送帧数据
                    await connection_manager.send_personal_message({
                        "type": "simulation_frame",
                        "session_id": session_id,
                        "data": frame_data
                    }, client_id)
                    
                    # 控制帧率
                    await asyncio.sleep(frame_interval)
                    
                    # 打印进度
                    if frame_number % 25 == 0:  # 每25帧打印一次
                        logger.info(f"📡 传输进度: {frame_number}/{frame_count}")
            
            # 流传输完成
            await connection_manager.send_personal_message({
                "type": "session_stream_completed",
                "session_id": session_id,
                "message": "会话数据流传输完成"
            }, client_id)
            
        except Exception as e:
            logger.error(f"会话数据流传输失败: {e}")
            await connection_manager.send_personal_message({
                "type": "error",
                "session_id": session_id,
                "message": f"数据流传输失败: {str(e)}"
            }, client_id)
        
    else:
        logger.warning(f"Unknown message type: {message_type}")

@router.get("/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    return connection_manager.get_stats()
