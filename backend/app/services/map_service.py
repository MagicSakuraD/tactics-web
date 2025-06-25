import logging
from typing import Dict, Any, Optional
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from tactics2d.map.parser import OSMParser
    TACTICS2D_AVAILABLE = True
except ImportError as e:
    TACTICS2D_AVAILABLE = False
    logging.warning(f"Tactics2D库不可用: {e}")

logger = logging.getLogger(__name__)

class MapService:
    """OSM地图解析服务 - 只用官方OSMParser API"""
    def __init__(self):
        self.cached_maps: Dict[str, Dict[str, Any]] = {}

    def is_available(self) -> bool:
        return TACTICS2D_AVAILABLE

    def safe_convert_numpy(self, value: Any) -> Any:
        try:
            import numpy as np
            if hasattr(value, 'item'):
                return value.item()
            elif isinstance(value, np.ndarray):
                return value.tolist()
            elif isinstance(value, (list, tuple)):
                return [self.safe_convert_numpy(v) for v in value]
            elif isinstance(value, dict):
                return {k: self.safe_convert_numpy(v) for k, v in value.items()}
            else:
                return value
        except ImportError:
            return value

    def parse_osm_map_simple(self, osm_file_path: str, map_config: Optional[Dict] = None, debug: bool = False) -> Dict[str, Any]:
        if not TACTICS2D_AVAILABLE:
            raise RuntimeError("Tactics2D不可用")
        if not Path(osm_file_path).exists():
            raise FileNotFoundError(f"OSM文件不存在: {osm_file_path}")
        if osm_file_path in self.cached_maps and not debug:
            return self.cached_maps[osm_file_path]
        logger.info(f"解析OSM地图: {osm_file_path}")

        # 正确的API调用方式
        tree = ET.parse(osm_file_path)
        xml_root = tree.getroot()
        parser = OSMParser()
        project_rule = {}
        gps_origin = (0.0, 0.0)
        configs = map_config or {}
        map_obj = parser.parse(xml_root, project_rule, gps_origin, configs)
        
        # 增强解析：直接从XML中提取lanelet关系
        self._enhance_map_with_xml_data(map_obj, xml_root)
        
        if debug:
            # 调试输出
            self._debug_map_object(map_obj)

        map_data = self._extract_map_data(map_obj)
        self.cached_maps[osm_file_path] = map_data
        return map_data

    def _extract_map_data(self, map_obj) -> Dict[str, Any]:
        """
        从官方OSMParser对象提取标准化地图数据
        """
        COORDINATE_SCALE = 1000
        lanes = []
        boundaries = []
        roads = []
        
        # 处理关系（可能是车道）
        if hasattr(map_obj, 'relations'):
            for rel_id, relation in map_obj.relations.items():
                if hasattr(relation, 'type_') and relation.type_ == 'lanelet':
                    # 这是一个车道关系，从它的成员中提取中心线
                    left_way = None
                    right_way = None
                    
                    if hasattr(relation, 'left') and relation.left:
                        left_way = relation.left
                    if hasattr(relation, 'right') and relation.right:
                        right_way = relation.right
                    
                    if left_way and right_way:
                        # 计算中心线（左右边界的平均）
                        coords = self._calculate_centerline_from_boundaries(left_way, right_way)
                        
                        if coords and len(coords) >= 2:
                            threejs_coords = [[float(x)*COORDINATE_SCALE, 0.0, float(-y)*COORDINATE_SCALE] for x, y in coords]
                            lane_data = {
                                'id': f"lane_{rel_id}",
                                'coordinates': threejs_coords,
                                'type': 'lane',
                                'subtype': getattr(relation, 'subtype', 'highway').lower() if getattr(relation, 'subtype', 'highway') is not None else 'highway',
                                'width': 3.5  # 标准车道宽度
                            }
                            lanes.append(lane_data)
        
        # 1. 提取道路线
        if hasattr(map_obj, 'roadlines'):
            for line_id, line in map_obj.roadlines.items():
                coords = []
                if hasattr(line, 'geometry') and line.geometry:
                    if hasattr(line.geometry, 'coords'):
                        coords = list(line.geometry.coords)
                if coords and len(coords) >= 2:
                    threejs_coords = [[float(x)*COORDINATE_SCALE, 0.0, float(-y)*COORDINATE_SCALE] for x, y in coords]
                    type_value = getattr(line, 'type_', 'unknown')
                    line_type = type_value.lower() if type_value is not None else 'unknown'
                    subtype_value = getattr(line, 'subtype', 'unknown')
                    subtype = subtype_value.lower() if subtype_value is not None else 'unknown'
                    
                    # 尝试从 custom_tags 获取更多信息
                    custom_tags = getattr(line, 'custom_tags', {}) or {}
                    tag_type = custom_tags.get('type', '').lower() if custom_tags.get('type') else ''
                    tag_subtype = custom_tags.get('subtype', '').lower() if custom_tags.get('subtype') else ''
                    
                    # 合并所有类型信息来判断线条类型
                    is_lane = any(keyword in kw for keyword in ['lane', 'road', 'highway', 'motorway'] 
                                   for kw in [line_type, subtype, tag_type, tag_subtype] if kw)
                    
                    width = float(self.safe_convert_numpy(getattr(line, 'width', 0.5)) or 0.5)
                    line_data = {
                        'id': f"line_{line_id}",
                        'coordinates': threejs_coords,
                        'type': 'line' if not is_lane else 'lane',
                        'subtype': line_type,
                        'width': width
                    }
                    
                    if is_lane:
                        lanes.append(line_data)
                    else:
                        boundaries.append(line_data)
                    
                    # 将所有线路添加到道路列表，用于显示
                    road_data = {
                        'id': f"road_{line_id}",
                        'coordinates': threejs_coords,
                        'type': 'road',
                        'subtype': line_type,
                        'width': width
                    }
                    roads.append(road_data)
        
        # 2. 提取边界
        if hasattr(map_obj, 'boundaries'):
            for bound_id, boundary in map_obj.boundaries.items():
                coords = []
                if hasattr(boundary, 'geometry') and boundary.geometry:
                    if hasattr(boundary.geometry, 'coords'):
                        coords = list(boundary.geometry.coords)
                if coords and len(coords) >= 2:
                    threejs_coords = [[float(x)*COORDINATE_SCALE, 0.0, float(-y)*COORDINATE_SCALE] for x, y in coords]
                    boundary_data = {
                        'id': f"boundary_{bound_id}",
                        'coordinates': threejs_coords,
                        'type': 'boundary'
                    }
                    boundaries.append(boundary_data)
        
        # 3. 元数据
        metadata = {
            'num_lanes': len(lanes),
            'num_boundaries': len(boundaries),
            'num_roads': len(roads),
            'parser_type': 'official_osmparser',
            'has_geometry': len(lanes) > 0 or len(boundaries) > 0 or len(roads) > 0,
            'coordinate_scale': COORDINATE_SCALE
        }
        
        return {
            'lanes': lanes,
            'roads': roads,
            'boundaries': boundaries,
            'metadata': metadata
        }

    def _calculate_centerline_from_boundaries(self, left_way, right_way):
        """
        从左右边界计算中心线坐标
        
        Args:
            left_way: 左侧边界线
            right_way: 右侧边界线
            
        Returns:
            list: 中心线坐标列表 [(x1, y1), (x2, y2), ...]
        """
        left_coords = []
        right_coords = []
        
        # 提取左侧边界坐标
        if hasattr(left_way, 'geometry') and left_way.geometry:
            if hasattr(left_way.geometry, 'coords'):
                left_coords = list(left_way.geometry.coords)
            elif hasattr(left_way.geometry, 'shape'):
                left_coords = left_way.geometry.shape
        elif hasattr(left_way, 'shape'):
            left_coords = left_way.shape
        
        # 提取右侧边界坐标
        if hasattr(right_way, 'geometry') and right_way.geometry:
            if hasattr(right_way.geometry, 'coords'):
                right_coords = list(right_way.geometry.coords)
            elif hasattr(right_way.geometry, 'shape'):
                right_coords = right_way.geometry.shape
        elif hasattr(right_way, 'shape'):
            right_coords = right_way.shape
        
        # 检查坐标是否有效
        if not left_coords or not right_coords:
            logger.warning(f"无法提取边界坐标: 左侧={bool(left_coords)}, 右侧={bool(right_coords)}")
            return None
        
        # 确保坐标点数量一致，否则进行插值
        min_length = min(len(left_coords), len(right_coords))
        if len(left_coords) != len(right_coords):
            logger.debug(f"边界坐标点数不一致: 左侧={len(left_coords)}, 右侧={len(right_coords)}")
        
        # 计算中心线
        centerline = []
        for i in range(min_length):
            if i < len(left_coords) and i < len(right_coords):
                # 如果坐标是元组，直接使用
                if isinstance(left_coords[i], tuple) and isinstance(right_coords[i], tuple):
                    lx, ly = left_coords[i]
                    rx, ry = right_coords[i]
                # 否则尝试当作列表访问
                else:
                    try:
                        lx, ly = left_coords[i][0], left_coords[i][1]
                        rx, ry = right_coords[i][0], right_coords[i][1]
                    except (TypeError, IndexError):
                        logger.warning(f"无法解析坐标: 左侧={left_coords[i]}, 右侧={right_coords[i]}")
                        continue
                
                # 计算中心点
                try:
                    cx = (float(lx) + float(rx)) / 2.0
                    cy = (float(ly) + float(ry)) / 2.0
                    centerline.append((cx, cy))
                except (ValueError, TypeError):
                    logger.warning(f"坐标计算错误: 左侧=({lx},{ly}), 右侧=({rx},{ry})")
                    continue
        
        return centerline

    def _enhance_map_with_xml_data(self, map_obj, xml_root):
        """
        直接从 XML 中提取 lanelet 关系，并增强 map_obj
        
        Args:
            map_obj: OSMParser 解析后的地图对象
            xml_root: XML 根元素
        """
        if not hasattr(map_obj, 'relations'):
            map_obj.relations = {}
            
        # 从 XML 中提取 lanelet 关系
        for rel_element in xml_root.findall(".//relation"):
            rel_id = rel_element.get('id')
            if not rel_id:
                continue
                
            # 检查是否是 lanelet 类型的关系
            rel_type = None
            rel_subtype = None
            for tag in rel_element.findall("./tag"):
                if tag.get('k') == 'type' and tag.get('v') == 'lanelet':
                    rel_type = 'lanelet'
                if tag.get('k') == 'subtype':
                    rel_subtype = tag.get('v')
            
            if rel_type != 'lanelet':
                continue
                
            # 创建关系对象
            class RelationObj:
                pass
                
            relation = RelationObj()
            relation.id_ = rel_id
            relation.type_ = 'lanelet'
            relation.subtype = rel_subtype
            
            # 提取左右边界
            left_ref = None
            right_ref = None
            for member in rel_element.findall("./member"):
                if member.get('type') == 'way':
                    role = member.get('role')
                    ref = member.get('ref')
                    if role == 'left':
                        left_ref = ref
                    elif role == 'right':
                        right_ref = ref
            
            # 找到对应的边界线
            if left_ref and left_ref in map_obj.roadlines:
                relation.left = map_obj.roadlines[left_ref]
            if right_ref and right_ref in map_obj.roadlines:
                relation.right = map_obj.roadlines[right_ref]
                
            # 保存关系
            map_obj.relations[rel_id] = relation
            
        # 调试输出
        logger.debug(f"增强解析完成: 提取了 {len(map_obj.relations)} 个关系")

    def _debug_map_object(self, map_obj):
        """
        调试输出地图对象的详细信息
        """
        print("\n======== MAP OBJECT DEBUG INFO ========")
        
        # 检查基本属性
        for attr in ['nodes', 'roadlines', 'lanes', 'areas', 'relations', 'regulations']:
            if hasattr(map_obj, attr):
                items = getattr(map_obj, attr)
                count = len(items) if items else 0
                print(f"{attr}: {count} 项")
                logger.debug(f"{attr}: {count} 项")
        
        # 检查关系详情
        if hasattr(map_obj, 'relations') and map_obj.relations:
            print("\n关系类型分析:")
            logger.debug("关系类型分析:")
            relation_types = {}
            for rel_id, relation in map_obj.relations.items():
                rel_type = getattr(relation, 'type_', 'unknown')
                if rel_type not in relation_types:
                    relation_types[rel_type] = 0
                relation_types[rel_type] += 1
                
                # 仅打印第一个关系的详细信息作为示例
                if relation_types[rel_type] == 1:
                    print(f"\n{rel_type} 关系示例 (ID: {rel_id}):")
                    logger.debug(f"{rel_type} 关系示例 (ID: {rel_id}):")
                    for attr in dir(relation):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(relation, attr)
                                if not callable(value):
                                    print(f"  - {attr}: {value}")
                                    logger.debug(f"  - {attr}: {value}")
                            except:
                                pass
            
            print("\n关系类型统计:")
            logger.debug("关系类型统计:")
            for rel_type, count in relation_types.items():
                print(f"  - {rel_type}: {count} 个")
                logger.debug(f"  - {rel_type}: {count} 个")
                
        # 检查车道线详情
        if hasattr(map_obj, 'roadlines') and map_obj.roadlines:
            print("\n车道线类型分析:")
            logger.debug("车道线类型分析:")
            roadline_types = {}
            for line_id, line in map_obj.roadlines.items():
                line_type = getattr(line, 'type_', 'unknown')
                line_subtype = getattr(line, 'subtype', 'unknown')
                type_key = f"{line_type}:{line_subtype}"
                if type_key not in roadline_types:
                    roadline_types[type_key] = 0
                roadline_types[type_key] += 1
                
                # 仅打印第一种类型的详细信息作为示例
                if roadline_types[type_key] == 1:
                    print(f"\n{type_key} 车道线示例 (ID: {line_id}):")
                    logger.debug(f"{type_key} 车道线示例 (ID: {line_id}):")
                    for attr in dir(line):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(line, attr)
                                if not callable(value):
                                    print(f"  - {attr}: {value}")
                                    logger.debug(f"  - {attr}: {value}")
                            except:
                                pass
            
            print("\n车道线类型统计:")
            logger.debug("车道线类型统计:")
            for type_key, count in roadline_types.items():
                print(f"  - {type_key}: {count} 个")
                logger.debug(f"  - {type_key}: {count} 个")
        
        print("\n===================================\n")

# 全局地图服务实例
map_service = MapService()