# 🌐 WebSocket管理器 - WebSocket连接池管理
import logging
import json
import asyncio
from typing import Dict, List, Set, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 会话订阅关系
        self.session_subscriptions: Dict[str, Set[str]] = {}
        # 连接会话映射
        self.connection_sessions: Dict[str, str] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # 清理会话订阅
        if client_id in self.connection_sessions:
            session_id = self.connection_sessions[client_id]
            self.unsubscribe_from_session(client_id, session_id)
            del self.connection_sessions[client_id]
            
        logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast_to_session(self, message: dict, session_id: str):
        """向会话中所有客户端广播"""
        if session_id in self.session_subscriptions:
            disconnected_clients = []
            
            for client_id in self.session_subscriptions[session_id]:
                if client_id in self.active_connections:
                    try:
                        await self.active_connections[client_id].send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"广播消息失败 {client_id}: {e}")
                        disconnected_clients.append(client_id)
                        
            # 清理失效连接
            for client_id in disconnected_clients:
                self.disconnect(client_id)
    
    async def broadcast_to_all(self, message: dict):
        """向所有连接的客户端广播消息"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"全体广播失败 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理失效连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def subscribe_to_session(self, client_id: str, session_id: str):
        """订阅会话"""
        if session_id not in self.session_subscriptions:
            self.session_subscriptions[session_id] = set()
            
        self.session_subscriptions[session_id].add(client_id)
        self.connection_sessions[client_id] = session_id
        logger.info(f"Client {client_id} subscribed to session {session_id}")
    
    def unsubscribe_from_session(self, client_id: str, session_id: str):
        """取消订阅会话"""
        if session_id in self.session_subscriptions:
            self.session_subscriptions[session_id].discard(client_id)
            if not self.session_subscriptions[session_id]:
                del self.session_subscriptions[session_id]
        
        if client_id in self.connection_sessions:
            del self.connection_sessions[client_id]
            
        logger.info(f"Client {client_id} unsubscribed from session {session_id}")
    
    async def handle_message(self, client_id: str, message_data: dict):
        """处理客户端消息"""
        message_type = message_data.get("type")
        
        if message_type == "subscribe":
            session_id = message_data.get("session_id")
            if session_id:
                self.subscribe_to_session(client_id, session_id)
                await self.send_personal_message({
                    "type": "subscribed",
                    "session_id": session_id
                }, client_id)
        
        elif message_type == "unsubscribe":
            session_id = message_data.get("session_id")
            if session_id:
                self.unsubscribe_from_session(client_id, session_id)
                await self.send_personal_message({
                    "type": "unsubscribed", 
                    "session_id": session_id
                }, client_id)
    
    def get_stats(self) -> dict:
        """获取连接统计"""
        return {
            "active_connections": len(self.active_connections),
            "active_sessions": len(self.session_subscriptions),
            "total_subscriptions": sum(len(subs) for subs in self.session_subscriptions.values())
        }

# 全局连接管理器实例
connection_manager = ConnectionManager()
