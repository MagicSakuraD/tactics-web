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
                        "x": float(position[0]),  # X坐标保持不变
                        "y": 0.9,  # 车辆高度的一半，让车辆"站"在地面上
                        "z": float(position[1])  # Y坐标映射到Z轴，不取负号以匹配地图坐标系
                    },
                    "velocity": {
                        "x": float(velocity[0]) if len(velocity) > 0 else 0.0,
                        "y": 0.0,
                        "z": float(velocity[1]) if len(velocity) > 1 else 0.0  # 不取负号
                    },
                    "rotation": {
                        "x": 0.0,
                        "y": float(heading),  # 绕Y轴旋转（车辆朝向）
                        "z": 0.0
                    },
                    "dimensions": {
                        "x": 4.5,  # 车辆长度
                        "y": 1.8,  # 车辆高度
                        "z": 2.0   # 车辆宽度
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
        
        # 处理车道数据 - 新格式包含coordinates字段
        for lane in map_info.get("lanes", []):
            try:
                coords = lane.get("coordinates", [])
                # 如果没有coordinates，尝试使用centerline
                if not coords:
                    centerline = lane.get("centerline", [])
                    if centerline and len(centerline) > 1:
                        coords = [[c[0], 0.0, c[1]] if len(c) >= 2 else [0, 0, 0] for c in centerline]
                
                if coords and len(coords) > 1:
                    lanes.append({
                        "type": "LineString",
                        "coordinates": coords,
                        "properties": {
                            "id": str(lane.get("id", "unknown")),
                            "width": 3.5,
                            "color": "#ffff00",  # 黄色车道线
                            "dashed": lane.get("subtype", "") == "dashed"
                        }
                    })
            except Exception as e:
                logger.warning(f"处理车道数据失败: {e}")
                continue
        
        # 处理边界/道路线数据 - 新格式包含coordinates字段
        for boundary in map_info.get("boundaries", []):
            try:
                coords = boundary.get("coordinates", [])
                # 如果没有coordinates，尝试使用points
                if not coords:
                    points = boundary.get("points", [])
                    if points and len(points) > 1:
                        coords = [[p[0], 0.0, -p[1]] if len(p) >= 2 else [0, 0, 0] for p in points]
                
                if coords and len(coords) > 1:
                    # 根据类型决定颜色
                    boundary_type = boundary.get("type", "")
                    subtype = boundary.get("subtype", "solid")
                    
                    color = "#ffffff"  # 默认白色
                    if "lane" in boundary_type.lower():
                        color = "#ffff00"  # 黄色车道线
                    elif subtype == "dashed":
                        color = "#888888"  # 灰色虚线
                    
                    boundaries.append({
                        "type": "LineString",
                        "coordinates": coords,
                        "properties": {
                            "id": str(boundary.get("id", "unknown")),
                            "color": color,
                            "width": 2.0,
                            "dashed": subtype == "dashed"
                        }
                    })
            except Exception as e:
                logger.warning(f"处理边界数据失败: {e}")
                continue
        
        # 处理道路数据（如果有的话）
        for road in map_info.get("roads", []):
            try:
                coords = road.get("coordinates", [])
                if coords and len(coords) > 1:
                    roads.append({
                        "type": "LineString",
                        "coordinates": coords,
                        "properties": {
                            "id": str(road.get("id", "unknown")),
                            "width": 8.0,
                            "color": "#666666"  # 灰色道路
                        }
                    })
            except Exception as e:
                logger.warning(f"处理道路数据失败: {e}")
                continue
        
        # 如果没有任何几何数据，创建一个基本的网格参考
        if not roads and not lanes and not boundaries:
            logger.warning("没有找到地图几何数据，创建基本参考网格")
            # 创建基本参考线
            boundaries.append({
                "type": "LineString",
                "coordinates": [[-50, 0, 0], [50, 0, 0]],  # X轴参考线
                "properties": {
                    "id": "reference_x",
                    "color": "#444444",
                    "width": 1.0
                }
            })
            boundaries.append({
                "type": "LineString", 
                "coordinates": [[0, 0, -50], [0, 0, 50]],  # Z轴参考线
                "properties": {
                    "id": "reference_z",
                    "color": "#444444",
                    "width": 1.0
                }
            })
        
        result = {
            "type": "map_data",
            "roads": roads,
            "lanes": lanes,
            "boundaries": boundaries,
            "metadata": {
                "bounds": map_info.get("boundary", {}),
                "scale": map_info.get("metadata", {}).get("coordinate_scale", 100000),  # 使用正确的默认值
                "units": "meters",
                "total_elements": len(roads) + len(lanes) + len(boundaries),
                "has_geometry": len(roads) + len(lanes) + len(boundaries) > 0,
                "source": "enhanced_osm_parser"
            }
        }
        
        logger.info(f"格式化地图数据完成: roads={len(roads)}, lanes={len(lanes)}, boundaries={len(boundaries)}")
        return result
    
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
