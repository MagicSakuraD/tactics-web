# 🎯 简化数据格式化器 - 新架构专用
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SimpleDataFormatter:
    """简化的数据格式化器 - 只做最基本的数据清理和格式化"""
    
    @staticmethod
    def format_trajectory_frame(participants_data: Dict[str, Any], timestamp: int, frame_number: int) -> Dict[str, Any]:
        """格式化单帧轨迹数据为前端可用格式"""
        vehicles = []
        
        for pid, participant in participants_data.items():
            # 提取基础数据
            position = participant.get("position", [0, 0])
            velocity = participant.get("velocity", [0, 0])
            heading = participant.get("heading", 0)
            vehicle_type = participant.get("type", "car")
            
            # 确保数据格式正确
            if len(position) >= 2:
                vehicle_data = {
                    "id": int(pid) if str(pid).isdigit() else hash(str(pid)) % 10000,
                    "position": {
                        "x": float(position[0]),
                        "y": 0.0,  # Three.js会处理Y轴
                        "z": float(-position[1])  # 转换坐标系
                    },
                    "velocity": {
                        "x": float(velocity[0]) if len(velocity) > 0 else 0.0,
                        "y": 0.0,
                        "z": float(-velocity[1]) if len(velocity) > 1 else 0.0
                    },
                    "rotation": {
                        "x": 0.0,
                        "y": float(heading),
                        "z": 0.0
                    },
                    "dimensions": {
                        "x": 4.5,  # 默认车辆尺寸
                        "y": 1.8,
                        "z": 2.0
                    },
                    "color": SimpleDataFormatter._get_vehicle_color(vehicle_type),
                    "type": vehicle_type
                }
                vehicles.append(vehicle_data)
        
        return {
            "type": "simulation_frame",
            "frame": frame_number,
            "timestamp": timestamp,
            "vehicles": vehicles
        }
    
    @staticmethod
    def format_map_data(map_info: Dict[str, Any]) -> Dict[str, Any]:
        """格式化地图数据为前端可用格式"""
        roads = []
        lanes = []
        boundaries = []
        
        # 安全地处理道路
        for road in map_info.get("roads", []):
            try:
                coords = road.get("coordinates", [])
                if coords and len(coords) > 1:  # 至少需要2个点
                    threejs_coords = []
                    for c in coords:
                        if isinstance(c, (list, tuple)) and len(c) >= 2:
                            threejs_coords.append([float(c[0]), 0.0, float(-c[1])])
                    
                    if threejs_coords:
                        roads.append({
                            "type": "LineString",
                            "coordinates": threejs_coords,
                            "properties": {
                                "id": str(road.get("id", "unknown")),
                                "width": float(road.get("width", 8.0)),
                                "color": "#666666"
                            }
                        })
            except Exception as e:
                logger.warning(f"处理道路数据失败: {e}")
                continue
        
        # 安全地处理车道
        for lane in map_info.get("lanes", []):
            try:
                coords = lane.get("coordinates", [])
                if coords and len(coords) > 1:
                    threejs_coords = []
                    for c in coords:
                        if isinstance(c, (list, tuple)) and len(c) >= 2:
                            threejs_coords.append([float(c[0]), 0.0, float(-c[1])])
                    
                    if threejs_coords:
                        lanes.append({
                            "type": "LineString",
                            "coordinates": threejs_coords,
                            "properties": {
                                "id": str(lane.get("id", "unknown")),
                                "width": float(lane.get("width", 3.5)),
                                "color": "#ffff00",
                                "dashed": lane.get("subtype", "") == "dashed"
                            }
                        })
            except Exception as e:
                logger.warning(f"处理车道数据失败: {e}")
                continue
        
        # 安全地处理边界
        for boundary in map_info.get("boundaries", []):
            try:
                coords = boundary.get("coordinates", [])
                if coords and len(coords) > 1:
                    threejs_coords = []
                    for c in coords:
                        if isinstance(c, (list, tuple)) and len(c) >= 2:
                            threejs_coords.append([float(c[0]), 0.0, float(-c[1])])
                    
                    if threejs_coords:
                        boundaries.append({
                            "type": "LineString",
                            "coordinates": threejs_coords,
                            "properties": {
                                "id": str(boundary.get("id", "unknown")),
                                "width": float(boundary.get("width", 0.5)),
                                "color": "#ff0000"
                            }
                        })
            except Exception as e:
                logger.warning(f"处理边界数据失败: {e}")
                continue
        
        return {
            "type": "map_data",
            "roads": roads,
            "lanes": lanes,
            "boundaries": boundaries,
            "metadata": {
                "bounds": map_info.get("boundary", {}),
                "scale": 1.0,
                "units": "meters",
                "total_elements": len(roads) + len(lanes) + len(boundaries)
            }
        }
    
    @staticmethod
    def create_websocket_message(data: Dict[str, Any], session_id: str = "default") -> Dict[str, Any]:
        """创建WebSocket消息格式"""
        return {
            "type": data.get("type", "unknown"),
            "session_id": session_id,
            "data": data,
            "timestamp": data.get("timestamp"),
            "status": "success"
        }
    
    @staticmethod
    def _get_vehicle_color(vehicle_type: str) -> str:
        """根据车辆类型返回颜色"""
        color_map = {
            "car": "#3B82F6",      # 蓝色
            "truck": "#EF4444",    # 红色
            "bus": "#F59E0B",      # 橙色
            "motorcycle": "#10B981", # 绿色
            "bicycle": "#8B5CF6",  # 紫色
            "pedestrian": "#F97316" # 橙红色
        }
        return color_map.get(vehicle_type.lower(), "#666666")

# 全局实例
data_formatter = SimpleDataFormatter()
