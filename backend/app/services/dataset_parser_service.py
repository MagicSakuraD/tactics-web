# dataset_parser_service.py - 数据集解析服务

# 📊 数据集解析服务 - 专门处理LevelX等数据集的解析
import logging
import math
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import csv
from pathlib import Path

# 设置日志
logger = logging.getLogger(__name__)

# 尝试导入tactics2d
try:
    from tactics2d.dataset_parser import LevelXParser
    TACTICS2D_AVAILABLE = True
    logger.info("✅ Tactics2D库已成功导入")
except ImportError:
    TACTICS2D_AVAILABLE = False
    logger.warning("⚠️ Tactics2D库未找到，部分功能将不可用")

class DatasetParserService:
    """
    封装了与tactics2d库的交互，并提供了将数据转换为
    前端渲染所需格式的核心功能。
    """

    def is_available(self) -> bool:
        """检查tactics2d库是否成功导入"""
        return TACTICS2D_AVAILABLE

    def _log_participant_statistics(self, participants: Dict[int, Any]):
        """
        统计并打印参与者的详细信息，包括类型、尺寸分布等
        
        Args:
            participants: 参与者字典
        """
        if not participants:
            logger.warning("⚠️ 参与者字典为空，无法统计")
            return
        
        # 统计不同类型
        type_counts = {}
        type_details = {}  # 存储每种类型的详细信息
        
        # 尺寸统计
        length_stats = {'min': float('inf'), 'max': 0.0, 'sum': 0.0, 'count': 0}
        width_stats = {'min': float('inf'), 'max': 0.0, 'sum': 0.0, 'count': 0}
        
        # 获取属性访问器
        try:
            sample_participant = next(iter(participants.values()))
            _, _, participant_attr_getter = self._detect_participant_api(sample_participant)
        except Exception as e:
            logger.warning(f"⚠️ 无法检测参与者API，跳过详细统计: {e}")
            return
        
        # 尝试从 highD 的 tracksMeta.csv 读取类型映射（比依赖 Participant.class/type 更可靠）
        meta_type_by_id: Dict[int, str] = {}
        try:
            # participant 的 trajectory 里不会带 file_id/dataset_path，因此这里只能在调用方传入；
            # 这里保持兼容：如果外部未设置，将依赖 Participant 的字段兜底
            meta_type_by_id = getattr(self, "_last_highd_meta_type_by_id", {}) or {}
        except Exception:
            meta_type_by_id = {}

        # 遍历所有参与者进行统计
        for p_id, p_obj in participants.items():
            try:
                # 获取类型
                # 注意：tracksMeta.csv 的字段名是 'class'，不是 'type'
                vehicle_type = meta_type_by_id.get(int(p_id))
                vehicle_type_class = participant_attr_getter(p_obj, 'class')
                vehicle_type_type = participant_attr_getter(p_obj, 'type')
                vehicle_type = vehicle_type or vehicle_type_class or vehicle_type_type
                
                # 调试日志：记录前几个参与者的类型获取情况（包括Truck）
                if p_id <= 5 or (vehicle_type_class and vehicle_type_class != 'Car'):
                    logger.debug(f"🔍 参与者 {p_id}: class={vehicle_type_class}, type={vehicle_type_type}, 最终={vehicle_type}")
                
                # 如果获取失败，使用默认值
                if not vehicle_type:
                    vehicle_type = 'Car'  # 默认值
                    if p_id <= 5:
                        logger.debug(f"⚠️ 参与者 {p_id} 无法获取类型，使用默认值 'Car'")
                else:
                    vehicle_type = str(vehicle_type).strip()  # 转换为字符串并去除空格
                
                # 验证类型值是否合理（Car 或 Truck）
                if vehicle_type not in ['Car', 'Truck']:
                    # 如果类型不在预期范围内，记录警告并使用默认值
                    logger.warning(f"⚠️ 参与者 {p_id} 的类型 '{vehicle_type}' 不在预期范围内（应为 Car 或 Truck），使用默认值 'Car'")
                    vehicle_type = 'Car'
                
                # 统计类型数量
                if vehicle_type not in type_counts:
                    type_counts[vehicle_type] = 0
                    type_details[vehicle_type] = {
                        'ids': [],
                        'lengths': [],
                        'widths': []
                    }
                type_counts[vehicle_type] += 1
                type_details[vehicle_type]['ids'].append(int(p_id))
                
                # 获取尺寸
                # ✅ 以 tactics2d Participant 的规范字段为准：length/width（highD 原始 CSV 的命名反直觉，但 tactics2d 已做归一）
                vehicle_length = participant_attr_getter(p_obj, 'length')
                vehicle_width = participant_attr_getter(p_obj, 'width')

                # 兜底：如果某些数据集/版本没有 length/width，则尝试从 width/height 推断（长 > 宽）
                if (vehicle_length is None or vehicle_width is None) and hasattr(p_obj, 'height'):
                    raw_a = getattr(p_obj, 'width', None)
                    raw_b = getattr(p_obj, 'height', None)
                    try:
                        val_a = float(raw_a) if raw_a is not None else 0.0
                        val_b = float(raw_b) if raw_b is not None else 0.0
                        if val_a > 0 and val_b > 0:
                            vehicle_length = max(val_a, val_b)
                            vehicle_width = min(val_a, val_b)
                    except Exception:
                        pass

                # 最终兜底默认值
                if not vehicle_length or float(vehicle_length) < 1.0:
                    vehicle_length = 4.5  # 默认轿车长度
                if not vehicle_width or float(vehicle_width) < 0.5:
                    vehicle_width = 2.0  # 默认轿车宽度
                
                vehicle_height_attr = None  # tracksMeta.csv 没有真正的"高度"字段
                
                vehicle_length = float(vehicle_length)
                vehicle_width = float(vehicle_width)
                
                # 更新尺寸统计
                length_stats['min'] = min(length_stats['min'], vehicle_length)
                length_stats['max'] = max(length_stats['max'], vehicle_length)
                length_stats['sum'] += vehicle_length
                length_stats['count'] += 1
                
                width_stats['min'] = min(width_stats['min'], vehicle_width)
                width_stats['max'] = max(width_stats['max'], vehicle_width)
                width_stats['sum'] += vehicle_width
                width_stats['count'] += 1
                
                # 记录到类型详情
                type_details[vehicle_type]['lengths'].append(vehicle_length)
                type_details[vehicle_type]['widths'].append(vehicle_width)
                
            except Exception as e:
                logger.debug(f"⚠️ 统计参与者 {p_id} 时出错: {e}")
                continue
        
        # 打印统计信息
        logger.info("=" * 60)
        logger.info("📊 参与者详细统计:")
        logger.info(f"   👥 总参与者数: {len(participants)}")
        
        # 按类型统计
        logger.info("   🚗 参与者类型分布:")
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        for vehicle_type, count in sorted_types:
            percentage = (count / len(participants)) * 100
            logger.info(f"      • {vehicle_type}: {count} 个 ({percentage:.1f}%)")
            
            # 显示该类型的尺寸范围
            if vehicle_type in type_details:
                lengths = type_details[vehicle_type]['lengths']
                widths = type_details[vehicle_type]['widths']
                if lengths and widths:
                    avg_length = sum(lengths) / len(lengths)
                    avg_width = sum(widths) / len(widths)
                    min_length = min(lengths)
                    max_length = max(lengths)
                    min_width = min(widths)
                    max_width = max(widths)
                    logger.info(f"        尺寸范围: 长度 {min_length:.2f}-{max_length:.2f}m (平均 {avg_length:.2f}m), "
                              f"宽度 {min_width:.2f}-{max_width:.2f}m (平均 {avg_width:.2f}m)")
        
        # 整体尺寸统计
        if length_stats['count'] > 0:
            avg_length = length_stats['sum'] / length_stats['count']
            avg_width = width_stats['sum'] / width_stats['count']
            logger.info("   📏 整体尺寸统计:")
            logger.info(f"      长度范围: {length_stats['min']:.2f} - {length_stats['max']:.2f}m (平均 {avg_length:.2f}m)")
            logger.info(f"      宽度范围: {width_stats['min']:.2f} - {width_stats['max']:.2f}m (平均 {avg_width:.2f}m)")
        
        logger.info("=" * 60)

    def _detect_participant_api(self, sample_participant: Any) -> tuple:
        """
        检测Participant对象的API接口，避免在循环中反复检查
        
        Args:
            sample_participant: 一个样本参与者对象
            
        Returns:
            (get_state_method, state_attr_getter, participant_attr_getter) 元组
            - get_state_method: 获取状态的方法（callable）
            - state_attr_getter: 从state对象获取属性的函数
            - participant_attr_getter: 从participant对象获取静态属性的函数
        """
        # 检测获取状态的方法
        # ⚠️ 重要：不能直接返回 sample_participant.get_state...（它是“绑定方法”）
        # 否则在循环里会错误地对所有参与者都读取同一个 sample_participant 的状态，导致“没有车/车都重叠”等严重问题。
        if hasattr(sample_participant, 'get_state_at_timestamp'):
            def get_state_method(participant, timestamp):
                return participant.get_state_at_timestamp(timestamp)
        elif hasattr(sample_participant, 'get_state'):
            def get_state_method(participant, timestamp):
                return participant.get_state(timestamp)
        else:
            raise AttributeError("Participant对象缺少get_state方法")
        
        # 检测State对象的属性名称（只检测一次）
        if not hasattr(sample_participant, 'is_active'):
            raise AttributeError("Participant对象缺少is_active方法")
        
        # 获取一个样本state来检测属性
        # 尝试获取第一个可能的时间戳的状态
        sample_state = None
        detection_error = None
        try:
            # 尝试获取一个状态来检测属性结构
            if hasattr(sample_participant, 'trajectory'):
                traj = sample_participant.trajectory
                if hasattr(traj, 'stamps') and traj.stamps:
                    sample_timestamp = traj.stamps[0]
                    sample_state = get_state_method(sample_participant, sample_timestamp)
                    if sample_state is None:
                        detection_error = "get_state_method返回None"
                else:
                    detection_error = "trajectory.stamps为空或不存在"
            else:
                detection_error = "Participant对象没有trajectory属性"
        except Exception as e:
            detection_error = f"获取样本状态时出错: {str(e)}"
            logger.debug(f"State属性检测详细错误: {e}", exc_info=True)
        
        if sample_state is None:
            # 如果无法获取样本，使用默认属性名（Tactics2D标准）
            # 这通常是可以接受的，因为Tactics2D的标准属性就是 x, y, vx, vy, heading
            logger.info(f"ℹ️ 使用默认State属性名 (x, y, vx, vy, heading). 原因: {detection_error or '无法获取样本状态'}")
            def attr_getter(state, attr_name):
                return getattr(state, attr_name, 0.0)
        else:
            # 检测实际属性名
            state_attrs = {}
            for standard_name in ['x', 'y', 'vx', 'vy', 'heading']:
                # 尝试标准名称
                if hasattr(sample_state, standard_name):
                    state_attrs[standard_name] = standard_name
                # 尝试替代名称
                elif standard_name == 'x' and hasattr(sample_state, 'position_x'):
                    state_attrs[standard_name] = 'position_x'
                elif standard_name == 'y' and hasattr(sample_state, 'position_y'):
                    state_attrs[standard_name] = 'position_y'
                elif standard_name == 'vx' and hasattr(sample_state, 'velocity_x'):
                    state_attrs[standard_name] = 'velocity_x'
                elif standard_name == 'vy' and hasattr(sample_state, 'velocity_y'):
                    state_attrs[standard_name] = 'velocity_y'
                elif standard_name == 'heading' and hasattr(sample_state, 'orientation'):
                    state_attrs[standard_name] = 'orientation'
                else:
                    state_attrs[standard_name] = standard_name  # 使用默认值0.0
            
            def attr_getter(state, attr_name):
                actual_attr = state_attrs.get(attr_name, attr_name)
                return getattr(state, actual_attr, 0.0)
        
        # 检测Participant对象的静态属性（width, height, type等）
        # 这些属性通常不会变化，可以从participant对象直接获取
        debug_dump_flag = {'logged': False}  # 仅在首次缺失时打印一次详细信息，避免刷屏

        def participant_attr_getter(participant, attr_name):
            """从Participant对象获取静态属性"""
            # 尝试多种可能的属性名
            # 注意：tracksMeta.csv 的字段名是 'class'，不是 'type'
            possible_names = {
                'width': ['width', 'w', 'vehicle_width'],
                'height': ['height', 'h', 'vehicle_height', 'length'],  # 注意：highD的height实际是车宽（与“长度/宽度”命名容易混淆）
                'length': ['length', 'l', 'vehicle_length'],
                # type & class 字段常见的重命名：type_, class_
                'type': ['type', 'type_', 'class', 'class_', 'vehicle_type', 'vehicle_class'],  # type 可以尝试 class
                'class': ['class', 'class_', 'type', 'type_', 'vehicle_class', 'vehicle_type']  # class 优先尝试 'class'，因为这是CSV的实际字段名
            }
            
            # 获取可能的属性名列表
            candidates = possible_names.get(attr_name, [attr_name])
            
            for candidate in candidates:
                if hasattr(participant, candidate):
                    value = getattr(participant, candidate)
                    # 如果是字符串，直接返回
                    if isinstance(value, str):
                        return value
                    # 如果是数值，转换为float
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return value

            # 检查 custom_tags 字段（Tactics2D 可能把类型放在这里）
            try:
                if hasattr(participant, "custom_tags"):
                    tags = getattr(participant, "custom_tags")
                    if isinstance(tags, dict):
                        # 优先匹配 attr_name，其次匹配 'class'/'type'
                        if attr_name in tags:
                            return tags[attr_name]
                        if attr_name == 'class' and 'class' in tags:
                            return tags['class']
                        if attr_name == 'type' and 'type' in tags:
                            return tags['type']
            except Exception:
                pass

            # 如果仍然找不到，打印一次调试信息，帮助定位真实字段名
            if attr_name in ('class', 'type') and not debug_dump_flag['logged']:
                try:
                    debug_dump_flag['logged'] = True
                    attrs = dir(participant)
                    attr_keys = list(getattr(participant, "__dict__", {}).keys())
                    logger.info(f"🔍 未找到属性 '{attr_name}'，打印Participant调试信息用于排查字段映射问题")
                    logger.info(f"   dir(participant): {attrs}")
                    logger.info(f"   participant.__dict__.keys(): {attr_keys}")
                    if hasattr(participant, "custom_tags"):
                        logger.info(f"   participant.custom_tags: {getattr(participant, 'custom_tags')}")
                except Exception:
                    pass
            
            # 如果都没找到，返回默认值
            # ⚠️ 重要：'type' 和 'class' 不设置默认值，返回 None
            # 这样可以区分"找不到属性"和"属性值为默认值"的情况
            # 调用者需要根据实际情况处理 None 值（例如，如果找不到 class，再使用默认值 'Car'）
            defaults = {
                'width': 2.0,
                'height': 1.8,
                'length': 4.5,
                # 'type' 和 'class' 不设置默认值，返回 None
            }
            return defaults.get(attr_name, None)
        
        return get_state_method, attr_getter, participant_attr_getter

    def _load_highd_tracks_meta_type_map(self, dataset_path: str, file_id: int) -> Dict[int, str]:
        """
        直接读取 highD 的 %02d_tracksMeta.csv，提取 id→class(Car/Truck) 映射。
        这是目前最可靠的车辆类型来源（tactics2d Participant 往往不暴露 class/type）。
        """
        try:
            meta_path = Path(dataset_path) / f"{int(file_id):02d}_tracksMeta.csv"
            if not meta_path.exists():
                logger.warning(f"⚠️ tracksMeta.csv 不存在，无法建立类型映射: {meta_path}")
                return {}

            type_by_id: Dict[int, str] = {}
            with meta_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        rid = int(row.get("id", "").strip())
                    except Exception:
                        continue
                    cls = (row.get("class") or "").strip()
                    if cls in ("Car", "Truck"):
                        type_by_id[rid] = cls

            if type_by_id:
                # 给统计/重构阶段复用（避免改大量函数签名）
                self._last_highd_meta_type_by_id = type_by_id
                logger.info(f"✅ 从 tracksMeta.csv 建立类型映射: {len(type_by_id)} 条")
            else:
                logger.warning("⚠️ tracksMeta.csv 中未解析出任何有效 class 字段（Car/Truck）")

            return type_by_id
        except Exception as e:
            logger.warning(f"⚠️ 读取 tracksMeta.csv 建立类型映射失败: {e}")
            return {}

    def _restructure_for_streaming(
        self, 
        participants: Dict[int, Any], 
        frame_step: int, 
        actual_stamp_range: Tuple[int, int] = None,
        perception_range: Optional[float] = None,
        reference_point: Optional[Tuple[float, float]] = None,
        coordinate_scale: float = 1.0
    ) -> Dict[int, List[Dict]]:
        """
        优化后的数据重构方法：直接按步长采样，避免无效计算。
        
        性能优化：
        1. 直接按effective_step跳跃循环，只计算需要的帧
        2. 预先检测API接口，避免循环中反复hasattr/getattr
        3. 移除多余的排序操作（range本身有序，字典保持插入顺序）
        
        Args:
            participants: tactics2d的parse_trajectory返回的原始参与者字典
            frame_step: 数据处理的帧间隔步长（前端播放速度倍数）
            actual_stamp_range: 实际的时间戳范围（来自parse_trajectory返回值）
            perception_range: (可选) 感知范围（米），用于空间裁剪
            reference_point: (可选) 参考点坐标 (x, y)，用于计算距离
            coordinate_scale: (可选) 坐标缩放比例，用于与地图坐标系统匹配（默认1.0）
            
        Returns:
            一个以帧号为键（从0开始），值为该帧所有车辆状态列表的字典
        """
        if not participants or not actual_stamp_range:
            return {}
        
        start_time, end_time = actual_stamp_range
        
        # LevelX数据集（highD等）的采样频率是25Hz，即每40ms一帧
        # 参考：https://tactics2d.readthedocs.io/en/latest/api/dataset_parser/
        BASE_TIME_STEP = 40  # 毫秒
        
        # 计算实际采样间隔：基础间隔 × 帧步长
        # 例如 frame_step=5 时，每200ms采样一次（5倍速播放）
        effective_step = BASE_TIME_STEP * frame_step
        
        logger.info(f"🔄 优化重构: {len(participants)} 个参与者, 时间范围 {start_time}-{end_time}ms")
        logger.info(f"   采样间隔: {effective_step}ms (基础: {BASE_TIME_STEP}ms × 步长: {frame_step})")
        
        # 预先检测API接口（只检测一次，不在循环中重复检查）
        try:
            sample_participant = next(iter(participants.values()))
            get_state_method, state_attr_getter, participant_attr_getter = self._detect_participant_api(sample_participant)
            logger.debug("✅ API检测完成: get_state方法=per-participant wrapper")
        except Exception as e:
            logger.error(f"❌ API检测失败: {e}")
            return {}
        
        sampled_frames = {}
        frame_index = 0  # 前端需要的连续帧号（从0开始）
        
        # 直接按effective_step跳跃循环，只计算需要的帧
        # Python 3.7+ 字典保持插入顺序，无需额外排序
        # 尝试从 highD 的 tracksMeta.csv 读取类型映射（如果上层已加载）
        meta_type_by_id: Dict[int, str] = {}
        try:
            meta_type_by_id = getattr(self, "_last_highd_meta_type_by_id", {}) or {}
        except Exception:
            meta_type_by_id = {}

        for timestamp in range(int(start_time), int(end_time), effective_step):
            frame_participants = []
            
            for p_id, p_obj in participants.items():
                try:
                    # 快速检查活跃状态（已确认有is_active方法）
                    if not p_obj.is_active(timestamp):
                        continue
                    
                    # 获取状态（已确认方法存在）
                    state = get_state_method(p_obj, timestamp)
                    if state is None:
                        continue
                    
                    # 提取静态属性（尺寸和类型）- 这些属性不会随时间变化
                    # ✅ 以 tactics2d Participant 的规范字段为准：length/width
                    # 说明：highD 原始 CSV 的 width/height 命名确实“反直觉”，但 tactics2d 已归一为 length/width。
                    
                    # 获取车辆类型：优先使用 tracksMeta.csv 的 class 映射，其次尝试 Participant 字段
                    vehicle_type = meta_type_by_id.get(int(p_id))
                    vehicle_type = vehicle_type or participant_attr_getter(p_obj, 'class') or participant_attr_getter(p_obj, 'type')
                    if not vehicle_type:
                        vehicle_type = 'Car'  # 默认值
                    else:
                        vehicle_type = str(vehicle_type).strip()
                        # 验证类型值
                        if vehicle_type not in ['Car', 'Truck']:
                            vehicle_type = 'Car'  # 如果类型异常，使用默认值
                    
                    vehicle_length = participant_attr_getter(p_obj, 'length')
                    vehicle_width = participant_attr_getter(p_obj, 'width')

                    # 兜底：如果缺失 length/width，尝试用 width/height 推断（长 > 宽）
                    if (vehicle_length is None or vehicle_width is None) and hasattr(p_obj, 'height'):
                        raw_a = getattr(p_obj, 'width', None)
                        raw_b = getattr(p_obj, 'height', None)
                        try:
                            val_a = float(raw_a) if raw_a is not None else 0.0
                            val_b = float(raw_b) if raw_b is not None else 0.0
                            if val_a > 0 and val_b > 0:
                                vehicle_length = max(val_a, val_b)
                                vehicle_width = min(val_a, val_b)
                        except Exception:
                            pass
                    
                    # 3. 兜底默认值（防止异常数据）
                    if not vehicle_length or vehicle_length < 1.0:
                        vehicle_length = 4.5  # 默认轿车长度
                    if not vehicle_width or vehicle_width < 0.5:
                        vehicle_width = 2.0  # 默认轿车宽度
                    
                    # 获取原始坐标（未缩放）
                    x_raw = float(state_attr_getter(state, 'x'))
                    y_raw = float(state_attr_getter(state, 'y'))
                    
                    # 空间过滤：如果设置了perception_range，只保留范围内的车辆
                    # 注意：过滤使用原始坐标（米），因为perception_range也是以米为单位
                    if perception_range and reference_point:
                        ref_x, ref_y = reference_point
                        distance = math.sqrt((x_raw - ref_x)**2 + (y_raw - ref_y)**2)
                        if distance > perception_range:
                            continue  # 跳过超出感知范围的车辆
                    
                    # ✅ 车辆轨迹在 highD 中本身就是米制坐标；不要再乘 coordinate_scale（该参数用于地图度→米的缩放）
                    x_scaled = x_raw
                    y_scaled = y_raw
                    
                    # 直接使用预检测的属性访问器（避免getattr开销）
                    frame_participants.append({
                        "id": int(p_id),
                        "x": round(x_scaled, 3),  # 应用缩放后的坐标
                        "y": round(y_scaled, 3),  # 应用缩放后的坐标
                        "vx": round(float(state_attr_getter(state, 'vx')), 3),  # 速度通常不需要缩放
                        "vy": round(float(state_attr_getter(state, 'vy')), 3),  # 速度通常不需要缩放
                        "heading": round(float(state_attr_getter(state, 'heading')), 3),
                        # 新增：车辆尺寸和类型信息（highD：单位米）
                        "length": round(float(vehicle_length), 2) if vehicle_length else 4.5,
                        "width": round(float(vehicle_width), 2) if vehicle_width else 2.0,
                        "type": str(vehicle_type) if vehicle_type else "Car"
                    })
                    
                except Exception as participant_error:
                    # 只在调试模式下记录详细错误
                    logger.debug(f"⚠️ 参与者 {p_id} 在时间戳 {timestamp} 时出错: {participant_error}")
                    continue
            
            # 无论这一帧有没有车，都创建帧（保持帧索引连续）
            # 前端播放器需要连续的帧号
            sampled_frames[frame_index] = {
                "timestamp": timestamp,
                "vehicles": frame_participants
            }
            frame_index += 1
        
        if not sampled_frames:
            logger.warning("⚠️ 数据重构后没有生成任何帧")
            return {}
        
        logger.info(f"✅ 重构完成: 生成 {len(sampled_frames)} 帧 (直接采样，无浪费计算)")
        return sampled_frames

    def parse_dataset_for_session(
        self,
        dataset: str,
        file_id: int,
        dataset_path: str,
        frame_step: int,
        stamp_range: Tuple[int, int] = None,
        max_duration_ms: int = None,
        perception_range: Optional[float] = None,
        coordinate_scale: float = 1.0
    ) -> Dict[str, Any]:
        """
        解析指定的数据集文件，并为WebSocket会话准备数据。

        Args:
            dataset: 数据集类型 (例如, "levelx")。
            file_id: 数据集文件ID。
            dataset_path: 数据集文件所在的目录。
            frame_step: 帧间隔。
            stamp_range: (可选) 时间戳范围。
            max_duration_ms: (可选) 最大持续时间。
            perception_range: (可选) 感知范围（米）。
            coordinate_scale: (可选) 坐标缩放比例，用于与地图坐标系统匹配（默认1.0）。

        Returns:
            一个包含重构后帧数据的字典，如果失败则为空字典。
        """
        if not self.is_available():
            logger.error("❌ Tactics2D库不可用，无法解析数据集")
            return {}

        # 路径验证：检查 dataset_path 是否存在
        dataset_dir = Path(dataset_path)
        if not dataset_dir.exists():
            logger.error(f"❌ 数据集路径不存在: {dataset_path}")
            return {}
        if not dataset_dir.is_dir():
            logger.error(f"❌ 数据集路径不是目录: {dataset_path}")
            return {}

        logger.info(f"🚀 开始解析数据集: {dataset}, 文件ID: {file_id}, 路径: {dataset_path}")

        try:
            # 根据用户要求，目前只处理 highD 数据集
            # LevelXParser 构造函数需要正确的数据集名称（大小写敏感）
            # 文档：https://tactics2d.readthedocs.io/en/latest/api/dataset_parser/
            # LevelX系列包括：highD, inD, rounD, exiD, uniD
            dataset_lower = dataset.lower()
            if dataset_lower == 'highd':
                # 确保使用正确的大小写格式（highD）
                parser = LevelXParser("highD")
            elif dataset_lower in ['ind', 'round', 'exid', 'unid']:
                # 支持其他LevelX数据集
                dataset_name_map = {
                    'ind': 'inD',
                    'round': 'rounD',
                    'exid': 'exiD',
                    'unid': 'uniD'
                }
                parser = LevelXParser(dataset_name_map[dataset_lower])
            else:
                logger.error(f"不支持的数据集类型: {dataset}. LevelXParser支持: highD, inD, rounD, exiD, uniD")
                return {}

            # 调用tactics2d的解析功能
            # 修正2: parse_trajectory 需要明确传递 file 和 folder 参数
            # 修正3: 移除不支持的 'max_duration_ms' 参数
            # 修正4: parse_trajectory 返回一个元组 (participants, actual_stamp_range)，需要解包
            participants, actual_stamp_range = parser.parse_trajectory(
                file=file_id,
                folder=dataset_path,
                stamp_range=stamp_range
            )

            # 记录空 participants
            if not participants:
                logger.warning(f"⚠️ 解析完成，但未从文件 {file_id} 中提取到任何参与者数据")
                return {}

            logger.info(f"✅ 成功从tactics2d解析了 {len(participants)} 个参与者")
            logger.info(f"🕐 实际时间戳范围: {actual_stamp_range}")

            # easy fix: highD 类型映射直接从 tracksMeta.csv 读取
            if dataset_lower == "highd":
                self._load_highd_tracks_meta_type_map(dataset_path=dataset_path, file_id=file_id)
            
            # 统计参与者详细信息
            self._log_participant_statistics(participants)

            # 计算参考点（用于perception_range空间过滤）
            # 如果设置了perception_range，需要计算一个参考点（使用第一帧所有参与者的平均位置）
            reference_point = None
            if perception_range and perception_range > 0:
                try:
                    # 获取第一个参与者的第一个时间戳
                    sample_participant = next(iter(participants.values()))
                    get_state_method = None
                    # 复用统一的 API 检测逻辑（返回 per-participant wrapper）
                    try:
                        get_state_method, _, _ = self._detect_participant_api(sample_participant)
                    except Exception:
                        get_state_method = None
                    
                    if get_state_method and hasattr(sample_participant, 'trajectory'):
                        traj = sample_participant.trajectory
                        if hasattr(traj, 'stamps') and traj.stamps:
                            first_timestamp = traj.stamps[0]
                            # 获取所有参与者在第一帧的位置，计算中心点
                            positions = []
                            for p_obj in participants.values():
                                if p_obj.is_active(first_timestamp):
                                    state = get_state_method(p_obj, first_timestamp)
                                    if state:
                                        try:
                                            x = getattr(state, 'x', None) or getattr(state, 'position_x', 0)
                                            y = getattr(state, 'y', None) or getattr(state, 'position_y', 0)
                                            positions.append((float(x), float(y)))
                                        except:
                                            pass
                            if positions:
                                ref_x = sum(p[0] for p in positions) / len(positions)
                                ref_y = sum(p[1] for p in positions) / len(positions)
                                reference_point = (ref_x, ref_y)
                                logger.info(f"📍 计算参考点: ({ref_x:.2f}, {ref_y:.2f}), 感知范围: {perception_range}米")
                except Exception as e:
                    logger.warning(f"⚠️ 无法计算参考点，将禁用空间过滤: {e}")

            # 重构数据以进行流式传输，传递实际时间戳范围
            restructured_frames = self._restructure_for_streaming(
                participants, 
                frame_step, 
                actual_stamp_range,
                perception_range=perception_range,
                reference_point=reference_point,
                coordinate_scale=coordinate_scale  # 使用传入的坐标缩放比例
            )
            
            # 记录空 frames
            if not restructured_frames:
                logger.warning("⚠️ 数据重构后生成的帧数为0")
                return {}
            
            return {
                "frames": restructured_frames,
                "total_frames": len(restructured_frames),
                "participant_count": len(participants),
                "frame_step": frame_step,
            }

        except Exception as e:
            logger.error(f"❌ 在解析数据集时发生严重错误: {e}", exc_info=True)
            return {}

# 创建一个单例，方便在其他地方直接导入使用
dataset_parser_service = DatasetParserService()