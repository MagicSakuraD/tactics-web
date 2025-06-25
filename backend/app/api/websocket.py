import uuid
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.websocket_manager import connection_manager
import app.state as state  # 导入全局状态模块

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/simulation")
async def websocket_simulation_endpoint(websocket: WebSocket):
    """WebSocket端点：处理仿真数据流的启动和控制"""
    client_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, client_id)
    
    try:
        await connection_manager.send_personal_message({
            "type": "connected",
            "client_id": client_id,
            "message": "WebSocket connection established. Ready to start session stream."
        }, client_id)

        while True:
            message_data = await websocket.receive_json()
            message_type = message_data.get("type")

            if message_type == "start_session_stream":
                session_id = message_data.get("session_id")
                fps = message_data.get("fps", 10)# 默认帧率为25
                await handle_session_stream(client_id, session_id, fps)
            
            elif message_type == "ping":
                await connection_manager.send_personal_message({"type": "pong"}, client_id)
                
            else:
                logger.warning(f"Unknown message type from {client_id}: {message_type}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }, client_id)

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected.")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for {client_id}: {e}", exc_info=True)
        await connection_manager.send_personal_message({
            "type": "error",
            "message": f"An internal error occurred: {str(e)}"
        }, client_id)
    finally:
        connection_manager.disconnect(client_id)

async def handle_session_stream(client_id: str, session_id: str, fps: int):
    """处理单个会话的数据流传输"""
    if not session_id:
        await connection_manager.send_personal_message({
            "type": "error", "message": "session_id is required"
        }, client_id)
        return

    session = state.sessions.get(session_id)
    if not session:
        await connection_manager.send_personal_message({
            "type": "error", "session_id": session_id, "message": f"Session '{session_id}' not found on server."
        }, client_id)
        return

    trajectory_frames = session.get("trajectory_frames", {})
    frame_count = len(trajectory_frames)
    frame_interval = 1.0 / fps

    logger.info(f"🎬 Starting stream for session '{session_id}' to client {client_id}. Total frames: {frame_count}, FPS: {fps}")

    await connection_manager.send_personal_message({
        "type": "session_stream_started",
        "session_id": session_id,
        "total_frames": frame_count,
        "fps": fps
    }, client_id)

    # 按帧号（整数键）排序并流式传输
    sorted_frame_keys = sorted(trajectory_frames.keys())

    try:
        for frame_key in sorted_frame_keys:
            frame_data = trajectory_frames[frame_key]
            
            # 检查客户端是否仍然连接
            if client_id not in connection_manager.active_connections:
                logger.warning(f"⚠️ Client {client_id} disconnected during stream")
                return
            
            await connection_manager.send_personal_message({
                "type": "simulation_frame",
                "session_id": session_id,
                "frame_number": frame_key,
                "data": frame_data # data 包含 timestamp 和 vehicles
            }, client_id)
            
            await asyncio.sleep(frame_interval)

        await connection_manager.send_personal_message({
            "type": "session_stream_completed",
            "session_id": session_id,
            "message": "Stream completed."
        }, client_id)
        logger.info(f"✅ Stream completed for session '{session_id}'.")
        
    except Exception as e:
        logger.error(f"❌ Error during stream for session '{session_id}': {e}")
        await connection_manager.send_personal_message({
            "type": "error",
            "session_id": session_id,
            "message": f"Stream error: {str(e)}"
        }, client_id)

@router.get("/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    return connection_manager.get_stats()
