import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
import math

try:
    from tactics2d.map.parser import OSMParser
    TACTICS2D_AVAILABLE = True
except ImportError as e:
    TACTICS2D_AVAILABLE = False
    logging.warning(f"Tactics2D库不可用: {e}")

# 尝试导入numpy用于数值计算（可选）
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("NumPy不可用，将使用纯Python实现插值")

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

    def _determine_coordinate_scale(self, sample_coords: List[Tuple[float, float]]) -> float:
        """
        智能确定坐标缩放比例
        
        通过分析样本坐标的大小来判断：
        - 如果坐标很小（< 1），可能是经纬度，需要较大的缩放
        - 如果坐标较大（> 100），可能是米为单位，需要较小的缩放或无需缩放
        
        Args:
            sample_coords: 样本坐标列表
            
        Returns:
            合适的缩放比例
        """
        if not sample_coords:
            return 1.0
        
        # 计算坐标的典型范围
        try:
            x_values = [abs(float(c[0])) for c in sample_coords[:100]]  # 只检查前100个点
            y_values = [abs(float(c[1])) for c in sample_coords[:100]]
            
            max_x = max(x_values) if x_values else 1.0
            max_y = max(y_values) if y_values else 1.0
            max_coord = max(max_x, max_y)
            
            # 判断坐标单位
            if max_coord < 0.01:
                # 很可能是经纬度（度数），需要大幅缩放
                # 粗略估算：1度纬度 ≈ 111km，所以需要放大到米级别
                # 但考虑到Three.js场景，我们使用一个合理的缩放
                scale = 111000  # 将度转换为米（近似）
                logger.info(f"检测到经纬度坐标（最大值={max_coord:.6f}），使用缩放比例: {scale}")
            elif max_coord < 1.0:
                # 可能是归一化的坐标或很小的米值
                scale = 1000  # 放大1000倍
                logger.info(f"检测到小数值坐标（最大值={max_coord:.3f}），使用缩放比例: {scale}")
            elif max_coord < 100.0:
                # 可能是米为单位，但数值较小
                scale = 1.0  # 不缩放
                logger.info(f"检测到米单位坐标（最大值={max_coord:.2f}），不进行缩放")
            else:
                # 已经是较大的数值，可能是厘米或其他单位
                scale = 0.01  # 缩小100倍（假设是厘米）
                logger.info(f"检测到大数值坐标（最大值={max_coord:.2f}），使用缩放比例: {scale}")
            
            return scale
        except Exception as e:
            logger.warning(f"无法确定坐标缩放比例: {e}，使用默认值1.0")
            return 1.0

    def _extract_map_data(self, map_obj) -> Dict[str, Any]:
        """
        从官方OSMParser对象提取标准化地图数据
        
        注意：这里同时使用OSMParser和手动XML解析的原因：
        - OSMParser可能无法完全解析Lanelet2格式的relation关系
        - 需要手动从XML中提取lanelet关系并关联左右边界
        - 这是一种"增强解析"策略，确保不丢失关键数据
        """
        lanes = []
        boundaries = []
        roads = []
        
        # 先收集一些样本坐标用于确定缩放比例
        sample_coords = []
        
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
                        # 计算中心线（使用改进的基于弧长的算法）
                        coords = self._calculate_centerline_from_boundaries(left_way, right_way)
                        
                        if coords and len(coords) >= 2:
                            # 收集样本坐标
                            sample_coords.extend(coords[:10])  # 只取前10个点作为样本
                            lanes.append({
                                'id': f"lane_{rel_id}",
                                'coordinates': coords,  # 先不缩放，后面统一处理
                                'type': 'lane',
                                'subtype': getattr(relation, 'subtype', 'highway').lower() if getattr(relation, 'subtype', 'highway') is not None else 'highway',
                                'width': 3.5  # 标准车道宽度
                            })
        
        # 1. 提取道路线
        if hasattr(map_obj, 'roadlines'):
            for line_id, line in map_obj.roadlines.items():
                coords = []
                if hasattr(line, 'geometry') and line.geometry:
                    if hasattr(line.geometry, 'coords'):
                        coords = list(line.geometry.coords)
                if coords and len(coords) >= 2:
                    # 收集样本坐标
                    sample_coords.extend(coords[:10])
                    
                    type_value = getattr(line, 'type_', 'unknown')
                    line_type = type_value.lower() if type_value is not None else 'unknown'
                    subtype_value = getattr(line, 'subtype', 'unknown')
                    subtype = subtype_value.lower() if subtype_value is not None else 'unknown'
                    
                    # 尝试从 custom_tags 获取更多信息
                    custom_tags = getattr(line, 'custom_tags', {}) or {}
                    tag_type = custom_tags.get('type', '').lower() if custom_tags.get('type') else ''
                    tag_subtype = custom_tags.get('subtype', '').lower() if custom_tags.get('subtype') else ''
                    
                    # 改进的类型判断：使用更全面的标签匹配
                    # Lanelet2标准标签：type可以是 'line_thin', 'line_thick', 'curbstone', 'virtual', 'road_border' 等
                    # subtype可以是 'solid', 'dashed', 'dotted' 等
                    lane_keywords = ['lane', 'road', 'highway', 'motorway', 'driving', 'traffic']
                    boundary_keywords = ['border', 'curb', 'barrier', 'fence', 'wall', 'guard_rail']
                    
                    # 检查是否是车道相关
                    is_lane = any(
                        keyword in kw 
                        for keyword in lane_keywords
                        for kw in [line_type, subtype, tag_type, tag_subtype] 
                        if kw
                    )
                    
                    # 检查是否是边界
                    is_boundary = any(
                        keyword in kw 
                        for keyword in boundary_keywords
                        for kw in [line_type, subtype, tag_type, tag_subtype] 
                        if kw
                    )
                    
                    # 如果既不是车道也不是边界，根据type判断
                    if not is_lane and not is_boundary:
                        # line_thin, line_thick 通常是车道标记
                        if 'line' in line_type:
                            is_lane = True
                    
                    width = float(self.safe_convert_numpy(getattr(line, 'width', 0.5)) or 0.5)
                    line_data = {
                        'id': f"line_{line_id}",
                        'coordinates': coords,  # 先不缩放
                        'type': 'boundary' if is_boundary else ('lane' if is_lane else 'line'),
                        'subtype': line_type,
                        'width': width
                    }
                    
                    if is_lane:
                        lanes.append(line_data)
                    elif is_boundary:
                        boundaries.append(line_data)
                    else:
                        boundaries.append(line_data)  # 未知类型默认作为边界
                    
                    # 将所有线路添加到道路列表，用于显示
                    road_data = {
                        'id': f"road_{line_id}",
                        'coordinates': coords,  # 先不缩放
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
                    sample_coords.extend(coords[:10])
                    boundary_data = {
                        'id': f"boundary_{bound_id}",
                        'coordinates': coords,  # 先不缩放
                        'type': 'boundary'
                    }
                    boundaries.append(boundary_data)
        
        # 3. 确定坐标缩放比例（基于样本坐标）
        coordinate_scale = self._determine_coordinate_scale(sample_coords)
        
        # 4. 应用缩放并转换为Three.js格式 [x, y, z]
        def apply_coordinate_transform(coords_list):
            """将坐标列表转换为Three.js格式并应用缩放"""
            return [
                [float(x) * coordinate_scale, 0.0, float(y) * coordinate_scale] 
                for x, y in coords_list
            ]
        
        # 对所有几何数据应用变换
        for lane in lanes:
            lane['coordinates'] = apply_coordinate_transform(lane['coordinates'])
        
        for road in roads:
            road['coordinates'] = apply_coordinate_transform(road['coordinates'])
        
        for boundary in boundaries:
            boundary['coordinates'] = apply_coordinate_transform(boundary['coordinates'])
        
        # 5. 元数据
        metadata = {
            'num_lanes': len(lanes),
            'num_boundaries': len(boundaries),
            'num_roads': len(roads),
            'parser_type': 'official_osmparser_enhanced',
            'has_geometry': len(lanes) > 0 or len(boundaries) > 0 or len(roads) > 0,
            'coordinate_scale': coordinate_scale,
            'coordinate_unit': 'meters' if coordinate_scale <= 1.0 else 'degrees_to_meters'
        }
        
        return {
            'lanes': lanes,
            'roads': roads,
            'boundaries': boundaries,
            'metadata': metadata
        }

    def _calculate_arc_length(self, coords: List[Tuple[float, float]]) -> List[float]:
        """
        计算坐标序列的累积弧长
        
        Args:
            coords: 坐标列表 [(x1, y1), (x2, y2), ...]
            
        Returns:
            累积弧长列表 [0, s1, s2, ...]，其中s_i是从起点到第i个点的距离
        """
        if not coords or len(coords) < 2:
            return [0.0]
        
        arc_lengths = [0.0]
        for i in range(1, len(coords)):
            try:
                x1, y1 = float(coords[i-1][0]), float(coords[i-1][1])
                x2, y2 = float(coords[i][0]), float(coords[i][1])
                dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                arc_lengths.append(arc_lengths[-1] + dist)
            except (ValueError, TypeError, IndexError):
                # 如果某个点无效，使用前一个弧长值
                arc_lengths.append(arc_lengths[-1])
        
        return arc_lengths
    
    def _interpolate_point_by_arc_length(
        self, 
        coords: List[Tuple[float, float]], 
        arc_lengths: List[float], 
        target_length: float
    ) -> Optional[Tuple[float, float]]:
        """
        根据目标弧长在坐标序列中插值一个点
        
        Args:
            coords: 原始坐标列表
            arc_lengths: 对应的累积弧长列表
            target_length: 目标弧长
            
        Returns:
            插值得到的坐标点 (x, y)，如果超出范围则返回None
        """
        if not coords or not arc_lengths or len(coords) != len(arc_lengths):
            return None
        
        total_length = arc_lengths[-1]
        if total_length == 0:
            # 所有点重合，返回第一个点
            return coords[0] if coords else None
        
        # 限制目标弧长在有效范围内
        target_length = max(0.0, min(target_length, total_length))
        
        # 找到目标弧长所在区间
        for i in range(len(arc_lengths) - 1):
            if arc_lengths[i] <= target_length <= arc_lengths[i + 1]:
                # 线性插值
                t = (target_length - arc_lengths[i]) / (arc_lengths[i + 1] - arc_lengths[i]) if arc_lengths[i + 1] > arc_lengths[i] else 0.0
                x1, y1 = float(coords[i][0]), float(coords[i][1])
                x2, y2 = float(coords[i + 1][0]), float(coords[i + 1][1])
                x = x1 + t * (x2 - x1)
                y = y1 + t * (y2 - y1)
                return (x, y)
        
        # 如果超出范围，返回最后一个点
        return coords[-1] if coords else None
    
    def _resample_line_uniformly(
        self, 
        coords: List[Tuple[float, float]], 
        num_points: int
    ) -> List[Tuple[float, float]]:
        """
        将一条线重采样为指定数量的均匀分布点（基于弧长）
        
        Args:
            coords: 原始坐标列表
            num_points: 目标点数
            
        Returns:
            重采样后的坐标列表
        """
        if not coords:
            return []
        
        if len(coords) <= 1:
            return coords
        
        if num_points <= 1:
            return [coords[0]] if coords else []
        
        # 计算累积弧长
        arc_lengths = self._calculate_arc_length(coords)
        total_length = arc_lengths[-1]
        
        if total_length == 0:
            # 所有点重合
            return [coords[0]] * num_points
        
        # 在总弧长上均匀采样
        resampled = []
        for i in range(num_points):
            target_length = (i / (num_points - 1)) * total_length if num_points > 1 else 0.0
            point = self._interpolate_point_by_arc_length(coords, arc_lengths, target_length)
            if point:
                resampled.append(point)
        
        return resampled if resampled else coords
    
    def _calculate_centerline_from_boundaries(self, left_way, right_way):
        """
        从左右边界计算中心线坐标（改进版：基于弧长对齐）
        
        这个方法解决了原始实现中的关键问题：
        1. 左右边界点数可能不同
        2. 直接对应索引会导致几何错位
        3. 通过弧长归一化对齐，确保中心线几何正确
        
        Args:
            left_way: 左侧边界线对象
            right_way: 右侧边界线对象
            
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
        
        # 清理和验证坐标格式
        def normalize_coords(coords):
            """将坐标转换为统一的 (x, y) 元组格式"""
            normalized = []
            for coord in coords:
                try:
                    if isinstance(coord, tuple) and len(coord) >= 2:
                        normalized.append((float(coord[0]), float(coord[1])))
                    elif isinstance(coord, (list, tuple)) and len(coord) >= 2:
                        normalized.append((float(coord[0]), float(coord[1])))
                    else:
                        logger.warning(f"跳过无效坐标: {coord}")
                except (ValueError, TypeError, IndexError):
                    logger.warning(f"无法解析坐标: {coord}")
                    continue
            return normalized
        
        left_coords = normalize_coords(left_coords)
        right_coords = normalize_coords(right_coords)
        
        if not left_coords or not right_coords:
            logger.warning("坐标规范化后为空")
            return None
        
        # 计算左右边界的总弧长
        left_arc_lengths = self._calculate_arc_length(left_coords)
        right_arc_lengths = self._calculate_arc_length(right_coords)
        left_total_length = left_arc_lengths[-1]
        right_total_length = right_arc_lengths[-1]
        
        # 确定重采样点数：使用较长边界的点数，但至少保证一定密度
        max_points = max(len(left_coords), len(right_coords))
        # 根据总弧长调整采样点数，确保采样密度合理（每米至少1个点，最多1000个点）
        avg_length = (left_total_length + right_total_length) / 2.0
        target_points = max(max_points, min(int(avg_length * 2) + 1, 1000))
        
        # 对左右边界进行基于弧长的均匀重采样
        left_resampled = self._resample_line_uniformly(left_coords, target_points)
        right_resampled = self._resample_line_uniformly(right_coords, target_points)
        
        # 现在左右边界点数相同，可以安全地计算中点
        centerline = []
        min_length = min(len(left_resampled), len(right_resampled))
        
        for i in range(min_length):
            try:
                lx, ly = left_resampled[i]
                rx, ry = right_resampled[i]
                cx = (lx + rx) / 2.0
                cy = (ly + ry) / 2.0
                centerline.append((cx, cy))
            except (ValueError, TypeError, IndexError):
                logger.warning(f"计算中心点失败: 左侧={left_resampled[i] if i < len(left_resampled) else 'N/A'}, 右侧={right_resampled[i] if i < len(right_resampled) else 'N/A'}")
                continue
        
        if not centerline:
            logger.warning("中心线计算后为空")
            return None
        
        logger.debug(f"中心线计算完成: 原始点数(左={len(left_coords)}, 右={len(right_coords)}), 重采样后={min_length}, 中心线点数={len(centerline)}")
        
        return centerline

    def _enhance_map_with_xml_data(self, map_obj, xml_root):
        """
        直接从 XML 中提取 lanelet 关系，并增强 map_obj
        
        为什么需要这个"增强解析"？
        - Tactics2D的OSMParser可能无法完全解析Lanelet2格式的所有relation关系
        - Lanelet2使用relation来定义车道（lanelet），包含left和right边界引用
        - 手动解析确保不丢失关键的lanelet结构信息
        - 这是一种"防御性编程"策略，确保数据完整性
        
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