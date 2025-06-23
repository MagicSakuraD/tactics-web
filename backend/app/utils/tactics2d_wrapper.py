# 🛠️ Tactics2D包装器 - 封装tactics2d库的复杂操作
import logging
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from pathlib import Path

from ..config import settings

# 尝试导入 tactics2d 相关模块
try:
    from tactics2d.dataset_parser import LevelXParser
    from tactics2d.map.parser import OSMParser
    # 移除BEVCamera导入，因为新架构不需要
    TACTICS2D_AVAILABLE = True
except ImportError as e:
    TACTICS2D_AVAILABLE = False
    logging.warning(f"Tactics2D库不可用: {e}")

logger = logging.getLogger(__name__)

class Tactics2DWrapper:
    """Tactics2D库的高级封装"""
    
    def __init__(self):
        self.parsers: Dict[str, Any] = {}
        self.cameras: Dict[str, Any] = {}
        
    def is_available(self) -> bool:
        """检查Tactics2D是否可用"""
        return TACTICS2D_AVAILABLE
    
    def safe_convert_numpy(self, value: Any) -> Any:
        """安全地转换numpy类型为Python原生类型"""
        if hasattr(value, 'item'):  # numpy scalar
            return value.item()
        elif isinstance(value, np.ndarray):
            return value.tolist()
        elif isinstance(value, (list, tuple)):
            return [self.safe_convert_numpy(v) for v in value]
        elif isinstance(value, dict):
            return {k: self.safe_convert_numpy(v) for k, v in value.items()}
        else:
            return value
    
    def get_parser(self, dataset: str):
        """获取数据集解析器"""
        if not TACTICS2D_AVAILABLE:
            raise RuntimeError("Tactics2D不可用")
            
        if dataset not in self.parsers:
            if dataset.lower() == "highd":
                self.parsers[dataset] = LevelXParser("highD")
            else:
                raise ValueError(f"不支持的数据集: {dataset}")
                
        return self.parsers[dataset]
    
    def parse_trajectory_for_threejs(self, 
                                   dataset: str, 
                                   file_id: int, 
                                   data_folder: str,
                                   max_duration_ms: int = 2000) -> Dict[str, Any]:
        """专为Three.js优化的轨迹数据解析"""
        try:
            parser = self.get_parser(dataset)
            
            # 获取完整时间范围
            full_range = parser.get_stamp_range(file_id, data_folder)
            start_time = int(full_range[0])
            end_time = min(int(full_range[1]), start_time + max_duration_ms)
            
            # 解析轨迹
            participants, actual_range = parser.parse_trajectory(
                file_id, 
                data_folder, 
                stamp_range=(start_time, end_time)
            )
            
            # 提取轨迹时序数据
            trajectory_frames = {}
            frame_timestamps = list(range(start_time, end_time, 40))  # 25fps
            
            for timestamp in frame_timestamps:
                frame_data = {}
                for pid, participant in participants.items():
                    if participant.is_active(timestamp):
                        # 获取该时间戳的状态
                        position = participant.get_position(timestamp)
                        velocity = participant.get_velocity(timestamp) if hasattr(participant, 'get_velocity') else [0, 0]
                        heading = participant.get_heading(timestamp) if hasattr(participant, 'get_heading') else 0
                        
                        frame_data[str(pid)] = {
                            "id": self.safe_convert_numpy(pid),
                            "position": self.safe_convert_numpy(position),
                            "velocity": self.safe_convert_numpy(velocity),
                            "heading": self.safe_convert_numpy(heading),
                            "type": getattr(participant, 'driven_mode', 'car'),
                            "attributes": self._extract_safe_attributes(participant)
                        }
                
                trajectory_frames[str(timestamp)] = frame_data
            
            return {
                "frames": trajectory_frames,
                "timestamps": self.safe_convert_numpy(frame_timestamps),
                "participants_meta": {
                    str(pid): {
                        "id": self.safe_convert_numpy(pid),
                        "type": getattr(p, 'driven_mode', 'car'),
                        "attributes": self._extract_safe_attributes(p)
                    }
                    for pid, p in participants.items()
                },
                "duration_ms": end_time - start_time,
                "frame_count": len(frame_timestamps)
            }
            
        except Exception as e:
            logger.error(f"解析Three.js轨迹数据出错: {e}")
            raise
        """安全地解析轨迹数据（限制时长）"""
        try:
            parser = self.get_parser(dataset)
            
            # 获取完整时间范围
            full_range = parser.get_stamp_range(file_id, data_folder)
            start_time = int(full_range[0])
            end_time = min(int(full_range[1]), start_time + max_duration_ms)
            
            # 解析轨迹
            participants, actual_range = parser.parse_trajectory(
                file_id, 
                data_folder, 
                stamp_range=(start_time, end_time)
            )
            
            # 安全转换数据
            safe_participants = {}
            for pid, participant in participants.items():
                safe_pid = self.safe_convert_numpy(pid)
                safe_participants[safe_pid] = {
                    "type": type(participant).__name__,
                    "id": safe_pid,
                    "attributes": self._extract_safe_attributes(participant)
                }
            
            return {
                "participants": safe_participants,
                "timestamp_range": self.safe_convert_numpy(actual_range),
                "participant_count": len(safe_participants),
                "duration_ms": end_time - start_time
            }
            
        except Exception as e:
            logger.error(f"解析轨迹数据出错: {e}")
            raise
    
    def _extract_safe_attributes(self, participant: Any) -> Dict[str, Any]:
        """安全地提取参与者属性"""
        safe_attrs = {}
        
        # 常见的有用属性
        useful_attrs = [
            'id_', 'driven_mode', 'color', 'length', 'width', 'height',
            'front_overhang', 'rear_overhang'
        ]
        
        for attr_name in useful_attrs:
            try:
                if hasattr(participant, attr_name):
                    value = getattr(participant, attr_name)
                    safe_attrs[attr_name] = self.safe_convert_numpy(value)
            except Exception as e:
                logger.warning(f"提取属性 {attr_name} 失败: {e}")
                continue
                
        return safe_attrs
    
    def get_file_basic_info(self, dataset: str, file_id: int, data_folder: str) -> Dict[str, Any]:
        """获取文件基本信息"""
        try:
            parser = self.get_parser(dataset)
            
            stamp_range = parser.get_stamp_range(file_id, data_folder)
            location_id = parser.get_location(file_id, data_folder)
            
            return {
                "file_id": file_id,
                "location_id": self.safe_convert_numpy(location_id),
                "timestamp_range": self.safe_convert_numpy(stamp_range),
                "duration_seconds": float((int(stamp_range[1]) - int(stamp_range[0])) / 1000.0)
            }
            
        except Exception as e:
            logger.error(f"获取文件信息出错: {e}")
            raise

    def parse_osm_map_simple(self, osm_file_path: str, map_config: Optional[Dict] = None) -> Dict[str, Any]:
        """解析OSM地图文件 - 使用官方API优先，回退到tactics2d解析"""
        if not TACTICS2D_AVAILABLE:
            raise RuntimeError("Tactics2D不可用")
        
        # 验证文件路径
        if not Path(osm_file_path).exists():
            raise FileNotFoundError(f"OSM文件不存在: {osm_file_path}")
        
        logger.info(f"开始解析OSM地图: {osm_file_path}")
        
        # 定义解析方法优先级列表 - 简化为两种方法
        parse_methods = [
            ("官方OSMParser API", self.parse_osm_map_with_official_method),
            ("tactics2d回退", self._parse_osm_with_tactics2d_fallback)
        ]
        
        # 按优先级尝试解析方法
        for method_name, method_func in parse_methods:
            try:
                logger.info(f"尝试{method_name}解析OSM文件")
                if method_name == "tactics2d回退":
                    map_data = method_func(osm_file_path, map_config)
                else:
                    map_data = method_func(osm_file_path)
                logger.info(f"{method_name}解析成功")
                return map_data
            except Exception as e:
                logger.warning(f"{method_name}解析失败: {e}")
                continue
        
        # 所有方法都失败
        raise RuntimeError("所有OSM解析方法都失败")
    
    def _parse_osm_with_tactics2d_fallback(self, osm_file_path: str, map_config: Optional[Dict] = None) -> Dict[str, Any]:
        """tactics2d回退解析方法"""
        processed_file_path = None
        try:
            # 预处理文件
            processed_file_path = self._preprocess_osm_file(osm_file_path)
            
            # 创建OSM解析器
            osm_parser = OSMParser()
            map_obj = osm_parser.parse(processed_file_path, map_config or {})
            
            logger.info("tactics2d解析完成，开始提取数据")
            return self._extract_map_data_from_tactics2d_object(map_obj)
            
        finally:
            # 清理临时文件
            if processed_file_path and processed_file_path != osm_file_path:
                try:
                    import os
                    if os.path.exists(processed_file_path):
                        os.unlink(processed_file_path)
                        logger.info(f"已清理临时文件: {processed_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"清理临时文件失败: {cleanup_error}")

    def _extract_map_data_from_tactics2d_object(self, map_obj) -> Dict[str, Any]:
        """从tactics2d解析对象中提取地图数据 - 统一的数据提取逻辑"""
        map_data = {
            "boundary": {},
            "roads": [],
            "lanes": [],
            "boundaries": [],
            "areas": []
        }
        
        # 安全地提取边界信息
        try:
            if hasattr(map_obj, 'boundary') and map_obj.boundary is not None:
                boundary_tuple = map_obj.boundary
                # 转换边界格式 (min_x, max_x, min_y, max_y)
                map_data["boundary"] = {
                    "min_x": float(boundary_tuple[0]),
                    "max_x": float(boundary_tuple[1]), 
                    "min_y": float(boundary_tuple[2]),
                    "max_y": float(boundary_tuple[3]),
                    "center_x": (boundary_tuple[0] + boundary_tuple[1]) / 2,
                    "center_y": (boundary_tuple[2] + boundary_tuple[3]) / 2,
                    "width": boundary_tuple[1] - boundary_tuple[0],
                    "height": boundary_tuple[3] - boundary_tuple[2]
                }
                logger.info(f"提取边界信息: {map_data['boundary']}")
        except Exception as e:
            logger.warning(f"提取边界信息失败: {e}")
        
        # 处理roadlines（道路线）- 修复属性名
        self._extract_road_lines(map_obj, map_data)
        
        # 处理lanes（车道）
        self._extract_lanes_from_official_api(map_obj, map_data)
        
        # 安全地处理区域
        self._extract_areas(map_obj, map_data)
        
        # 输出统计信息
        logger.info(f"tactics2d解析完成:")
        logger.info(f"  - 道路: {len(map_data['roads'])}")
        logger.info(f"  - 车道: {len(map_data['lanes'])}")
        logger.info(f"  - 边界: {len(map_data['boundaries'])}")
        logger.info(f"  - 区域: {len(map_data['areas'])}")
        
        return map_data
    
    def _extract_roadlines_from_official_api(self, map_obj, map_data: Dict[str, Any]):
        """从官方API的roadlines提取数据"""
        try:
            if hasattr(map_obj, 'roadlines') and map_obj.roadlines:
                logger.info(f"找到 {len(map_obj.roadlines)} 条道路线")
                
                for roadline_id, roadline in map_obj.roadlines.items():
                    try:
                        # 提取基本属性
                        road_id = getattr(roadline, 'id_', roadline_id)
                        road_type = getattr(roadline, 'type_', 'unknown')
                        road_subtype = getattr(roadline, 'subtype', 'unknown')
                        
                        # 提取坐标数据
                        coordinates = []
                        if hasattr(roadline, 'geometry') and roadline.geometry:
                            # 从geometry获取坐标
                            geometry = roadline.geometry
                            if hasattr(geometry, 'coordinates'):
                                coordinates = self.safe_convert_numpy(geometry.coordinates)
                            elif hasattr(geometry, 'coords'):
                                coords_list = geometry.coords
                                coordinates = [[coord[0], coord[1]] for coord in coords_list]
                        
                        # 提取宽度信息
                        width = self.safe_convert_numpy(getattr(roadline, 'width', 0.5))
                        
                        road_data = {
                            "id": str(road_id),
                            "type": str(road_type),
                            "subtype": str(road_subtype),
                            "coordinates": coordinates,
                            "width": float(width) if isinstance(width, (int, float)) else 0.5
                        }
                        
                        # 根据类型分类存储 - roadlines通常是边界线
                        if road_type in ['line_thin', 'line_thick'] or 'line' in road_type:
                            map_data["boundaries"].append(road_data)
                            logger.debug(f"添加边界线: {road_id} ({road_subtype})")
                        else:
                            map_data["roads"].append(road_data)
                            
                    except Exception as e:
                        logger.warning(f"处理道路线 {roadline_id} 失败: {e}")
                        continue
        except Exception as e:
            logger.warning(f"处理道路线数据失败: {e}")
    
    def _extract_lanes_from_official_api(self, map_obj, map_data: Dict[str, Any]):
        """从官方API的lanes提取数据"""
        try:
            if hasattr(map_obj, 'lanes') and map_obj.lanes:
                logger.info(f"找到 {len(map_obj.lanes)} 个车道")
                
                for lane_id, lane in map_obj.lanes.items():
                    try:
                        # 提取基本属性
                        lane_id_str = getattr(lane, 'id_', lane_id)
                        lane_type = getattr(lane, 'type_', 'lane')
                        lane_subtype = getattr(lane, 'subtype', 'highway')
                        
                        # 提取坐标数据
                        coordinates = []
                        if hasattr(lane, 'geometry') and lane.geometry:
                            geometry = lane.geometry
                            if hasattr(geometry, 'coordinates'):
                                coordinates = self.safe_convert_numpy(geometry.coordinates)
                            elif hasattr(geometry, 'coords'):
                                coords_list = geometry.coords
                                coordinates = [[coord[0], coord[1]] for coord in coords_list]
                        
                        # 计算车道宽度（从左右边界）
                        width = 3.5  # 默认车道宽度
                        
                        lane_data = {
                            "id": str(lane_id_str),
                            "type": str(lane_type),
                            "subtype": str(lane_subtype),
                            "coordinates": coordinates,
                            "width": width
                        }
                        
                        map_data["lanes"].append(lane_data)
                        logger.debug(f"添加车道: {lane_id_str} ({lane_subtype})")
                            
                    except Exception as e:
                        logger.warning(f"处理车道 {lane_id} 失败: {e}")
                        continue
        except Exception as e:
            logger.warning(f"处理车道数据失败: {e}")
    
    def _extract_road_lines(self, map_obj, map_data: Dict[str, Any]):
        """提取道路线数据的统一方法 - 兼容不同的属性名"""
        try:
            # 尝试官方API的roadlines属性
            if hasattr(map_obj, 'roadlines') and map_obj.roadlines:
                self._extract_roadlines_from_official_api(map_obj, map_data)
                return
            
            # 兼容其他可能的属性名
            if hasattr(map_obj, 'road_lines'):
                logger.info(f"找到 {len(map_obj.road_lines)} 条道路线")
                
                for i, road_line in enumerate(map_obj.road_lines):
                    try:
                        # 提取基本属性
                        road_id = getattr(road_line, 'id_', f'road_{i}')
                        road_type = getattr(road_line, 'type_', 'unknown')
                        road_subtype = getattr(road_line, 'subtype', 'unknown')
                        
                        # 提取坐标数据
                        coordinates = self._extract_coordinates_from_road_line(road_line)
                        
                        # 提取宽度信息
                        width = self.safe_convert_numpy(getattr(road_line, 'width', 3.5))
                        
                        road_data = {
                            "id": str(road_id),
                            "type": str(road_type),
                            "subtype": str(road_subtype),
                            "coordinates": coordinates,
                            "width": float(width) if isinstance(width, (int, float)) else 3.5
                        }
                        
                        # 根据类型分类存储
                        self._classify_and_store_road_data(road_data, map_data)
                            
                    except Exception as e:
                        logger.warning(f"处理道路线 {i} 失败: {e}")
                        continue
        except Exception as e:
            logger.warning(f"处理道路线数据失败: {e}")
    
    def _extract_coordinates_from_road_line(self, road_line) -> List:
        """从道路线对象提取坐标数据"""
        coordinates = []
        
        # 优先从center_line获取
        if hasattr(road_line, 'center_line'):
            center_line = road_line.center_line
            if hasattr(center_line, 'coordinates'):
                coordinates = self.safe_convert_numpy(center_line.coordinates)
            elif hasattr(center_line, 'coords'):
                coordinates = self.safe_convert_numpy(center_line.coords)
        
        # 如果没有center_line，尝试直接获取coordinates
        if not coordinates and hasattr(road_line, 'coordinates'):
            coordinates = self.safe_convert_numpy(road_line.coordinates)
        
        return coordinates
    
    def _classify_and_store_road_data(self, road_data: Dict[str, Any], map_data: Dict[str, Any]):
        """根据道路类型分类存储道路数据"""
        type_lower = road_data["type"].lower()
        if 'lane' in type_lower:
            map_data["lanes"].append(road_data)
        elif 'boundary' in type_lower:
            map_data["boundaries"].append(road_data)
        else:
            map_data["roads"].append(road_data)
    
    def _extract_areas(self, map_obj, map_data: Dict[str, Any]):
        """提取区域数据的统一方法"""
        try:
            if hasattr(map_obj, 'areas'):
                logger.info(f"找到 {len(map_obj.areas)} 个区域")
                
                for i, area in enumerate(map_obj.areas):
                    try:
                        area_id = getattr(area, 'id_', f'area_{i}')
                        area_type = getattr(area, 'type_', 'unknown')
                        
                        # 提取区域坐标
                        coordinates = []
                        if hasattr(area, 'geometry') and hasattr(area.geometry, 'coordinates'):
                            coordinates = self.safe_convert_numpy(area.geometry.coordinates)
                        elif hasattr(area, 'coordinates'):
                            coordinates = self.safe_convert_numpy(area.coordinates)
                        
                        area_data = {
                            "id": str(area_id),
                            "type": str(area_type),
                            "coordinates": coordinates
                        }
                        map_data["areas"].append(area_data)
                        
                    except Exception as e:
                        logger.warning(f"处理区域 {i} 失败: {e}")
                        continue
        except Exception as e:
            logger.warning(f"处理区域数据失败: {e}")

    def _preprocess_osm_file(self, osm_file_path: str) -> str:
        """预处理OSM文件，添加缺失的边界信息"""
        import xml.etree.ElementTree as ET
        import tempfile
        
        try:
            # 解析原始OSM文件
            tree = ET.parse(osm_file_path)
            root = tree.getroot()
            
            # 检查是否已有bounds标签
            if root.find('bounds') is not None:
                logger.info("OSM文件已有边界信息，无需预处理")
                return osm_file_path
            
            # 从所有节点中计算边界
            nodes = root.findall('node')
            if not nodes:
                logger.warning("OSM文件中没有找到节点，使用默认边界")
                min_lat, max_lat = -0.001, 0.001
                min_lon, max_lon = -0.001, 0.007
            else:
                latitudes = []
                longitudes = []
                
                for node in nodes:
                    try:
                        lat = float(node.get('lat', 0))
                        lon = float(node.get('lon', 0))
                        latitudes.append(lat)
                        longitudes.append(lon)
                    except (ValueError, TypeError):
                        continue
                
                if latitudes and longitudes:
                    min_lat, max_lat = min(latitudes), max(latitudes)
                    min_lon, max_lon = min(longitudes), max(longitudes)
                    
                    # 添加一些边距以确保所有点都在边界内
                    lat_margin = (max_lat - min_lat) * 0.1 + 0.0001
                    lon_margin = (max_lon - min_lon) * 0.1 + 0.0001
                    
                    min_lat -= lat_margin
                    max_lat += lat_margin
                    min_lon -= lon_margin
                    max_lon += lon_margin
                else:
                    min_lat, max_lat = -0.001, 0.001
                    min_lon, max_lon = -0.001, 0.007
            
            logger.info(f"计算出的边界: lat({min_lat:.6f}, {max_lat:.6f}), lon({min_lon:.6f}, {max_lon:.6f})")
            
            # 创建bounds元素
            bounds = ET.Element('bounds', {
                'minlat': f"{min_lat:.8f}",
                'minlon': f"{min_lon:.8f}",
                'maxlat': f"{max_lat:.8f}",
                'maxlon': f"{max_lon:.8f}"
            })
            
            # 在第一个子元素前插入bounds
            root.insert(0, bounds)
            
            # 创建临时文件保存修改后的OSM
            temp_fd, temp_path = tempfile.mkstemp(suffix='.osm', prefix='processed_')
            try:
                with open(temp_path, 'wb') as f:
                    tree.write(f, encoding='utf-8', xml_declaration=True)
                logger.info(f"预处理后的OSM文件保存到: {temp_path}")
                return temp_path
            finally:
                import os
                os.close(temp_fd)  # 关闭文件描述符
                
        except Exception as e:
            logger.error(f"预处理OSM文件失败: {e}")
            # 如果预处理失败，返回原始文件路径
            return osm_file_path

    def parse_osm_map_with_official_method(self, osm_file_path: str) -> Dict[str, Any]:
        """使用官方示例的方法解析OSM地图 - 使用正确的API调用方式"""
        if not TACTICS2D_AVAILABLE:
            raise RuntimeError("Tactics2D不可用")
        
        try:
            # 1. 先解析XML文件获取根元素
            import xml.etree.ElementTree as ET
            tree = ET.parse(osm_file_path)
            xml_root = tree.getroot()
            logger.info(f"解析XML文件: {xml_root.tag}, 属性: {xml_root.attrib}")
            
            # 2. 加载官方配置文件
            import json
            import pkg_resources
            
            config_path = pkg_resources.resource_filename('tactics2d', 'dataset_parser/map.config')
            with open(config_path, 'r') as f:
                config_content = f.read()
                # 移除JSON中的注释（// 开头的行）
                config_lines = []
                for line in config_content.split('\n'):
                    if not line.strip().startswith('//'):
                        config_lines.append(line)
                clean_config = '\n'.join(config_lines)
                HIGHD_MAP_CONFIG = json.loads(clean_config)
            
            # 3. 从文件名提取配置
            file_name = Path(osm_file_path).stem  # 例如: "highD_2"
            
            if file_name in HIGHD_MAP_CONFIG:
                map_config = HIGHD_MAP_CONFIG[file_name]
                logger.info(f"使用官方配置: {file_name}")
                
                # 提取投影规则和GPS原点
                project_rule = map_config.get('project_rule', {})
                gps_origin = tuple(map_config.get('gps_origin', [0.0, 0.0]))
                
                logger.info(f"GPS原点: {gps_origin}")
                logger.info(f"投影规则: {project_rule}")
            else:
                logger.warning(f"未找到官方配置 {file_name}，使用默认配置")
                map_config = {}
                project_rule = {}
                gps_origin = (0.0, 0.0)
            
            # 4. 使用正确的官方API调用方式
            map_parser = OSMParser(lanelet2=True)
            # ✅ 正确方式：parser.parse(xml_root_element, project_rule, gps_origin, configs)
            map_obj = map_parser.parse(xml_root, project_rule, gps_origin, map_config)
            
            logger.info("官方方法解析完成，开始提取数据")
            
            # 使用统一的数据提取方法
            return self._extract_map_data_from_tactics2d_object(map_obj)
            
        except Exception as e:
            logger.error(f"官方方法解析失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise

# 全局包装器实例
tactics2d_wrapper = Tactics2DWrapper()
