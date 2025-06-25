# dataset_parser_service.py - 数据集解析服务

# 📊 数据集解析服务 - 专门处理LevelX等数据集的解析
import logging
from typing import Dict, Any, List, Tuple
from collections import defaultdict

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

    def _restructure_for_streaming(self, participants: Dict[int, Any], frame_step: int, actual_stamp_range: Tuple[int, int] = None) -> Dict[int, List[Dict]]:
        """
        将tactics2d返回的 "以参与者为中心" 的数据重构为 "以帧为中心" 的数据。
        这是将数据适配到前端渲染的关键步骤。

        Args:
            participants: tactics2d的parse_trajectory返回的原始参与者字典。
            frame_step: 数据处理的帧间隔步长。
            actual_stamp_range: 实际的时间戳范围（来自parse_trajectory返回值）

        Returns:
            一个以帧号为键，值为该帧所有车辆状态列表的字典。
        """
        frames = defaultdict(list)
        if not participants:
            return {}

        logger.info(f"🔄 开始重构数据结构，共 {len(participants)} 个参与者...")
        
        # 添加一个标志，确保我们只打印一次调试信息
        debug_info_printed = False

        # 根据官方文档，使用全局时间范围来迭代，而不是单个轨迹的时间范围
        if not actual_stamp_range:
            logger.error("❌ 缺少实际时间戳范围，无法重构数据")
            return {}
            
        start_time, end_time = actual_stamp_range
        logger.info(f"🕐 使用时间范围: {start_time}ms 到 {end_time}ms")
        
        # 按时间间隔采样（每40ms，对应25Hz）
        time_step = 40  # 毫秒
        processed_count = 0
        
        for timestamp in range(int(start_time), int(end_time), time_step):
            frame_participants = []
            
            for p_id, p_obj in participants.items():
                # --- 调试日志（只打印一次）---
                if not debug_info_printed:
                    logger.info("=================================================")
                    logger.info(f"🔍 DEBUG: Inspecting Participant object structure for participant ID: {p_id}")
                    logger.info(f"   - Object Type: {type(p_obj)}")
                    logger.info(f"   - Object Representation: {p_obj}")
                    logger.info(f"   - Object Attributes (using dir()): {dir(p_obj)}")
                    if hasattr(p_obj, '__dict__'):
                        logger.info(f"   - Object __dict__: {p_obj.__dict__}")
                    if hasattr(p_obj, 'trajectory'):
                        logger.info(f"   - Trajectory Type: {type(p_obj.trajectory)}")
                        logger.info(f"   - Trajectory Attributes: {dir(p_obj.trajectory)}")
                    logger.info("=================================================")
                    debug_info_printed = True
                # --- 结束调试 ---
                
                # 检查参与者在此时间戳是否活跃
                try:
                    if not hasattr(p_obj, 'is_active'):
                        logger.warning(f"⚠️ 参与者 {p_id} 缺少 is_active 方法")
                        continue
                        
                    if not p_obj.is_active(timestamp):
                        continue
                    
                    # 尝试获取特定时间戳的状态
                    state = None
                    if hasattr(p_obj, 'get_state_at_timestamp'):
                        state = p_obj.get_state_at_timestamp(timestamp)
                    elif hasattr(p_obj, 'get_state'):
                        state = p_obj.get_state(timestamp)
                    else:
                        logger.warning(f"⚠️ 参与者 {p_id} 缺少获取状态的方法")
                        continue
                    
                    if state is None:
                        continue

                    frame_participants.append({
                        "id": int(p_id),
                        "x": float(getattr(state, 'x', getattr(state, 'position_x', 0.0))),
                        "y": float(getattr(state, 'y', getattr(state, 'position_y', 0.0))),
                        "vx": float(getattr(state, 'vx', getattr(state, 'velocity_x', 0.0))),
                        "vy": float(getattr(state, 'vy', getattr(state, 'velocity_y', 0.0))),
                        "heading": float(getattr(state, 'heading', getattr(state, 'orientation', 0.0)))
                    })
                    
                except Exception as participant_error:
                    logger.warning(f"⚠️ 处理参与者 {p_id} 在时间戳 {timestamp} 时出错: {participant_error}")
                    continue
            
            # 如果这一帧有参与者，则添加到结果中
            if frame_participants:
                frames[timestamp] = frame_participants
                processed_count += 1
        
        if not frames:
            logger.warning("⚠️ 数据重构后没有生成任何帧")
            return {}

        logger.info(f"✅ 成功处理了 {processed_count} 个时间戳的数据")

        # 按帧步长进行抽样
        sorted_frames = sorted(frames.items())
        sampled_frames = {}
        
        # 我们需要一个新的、从0开始的帧索引
        new_frame_index = 0
        for i in range(0, len(sorted_frames), frame_step):
            original_frame_number, frame_data = sorted_frames[i]
            sampled_frames[new_frame_index] = {
                "timestamp": original_frame_number,
                "vehicles": frame_data
            }
            new_frame_index += 1

        logger.info(f"✅ 数据重构和抽样完成，从 {len(frames)} 帧抽样为 {len(sampled_frames)} 帧 (步长: {frame_step})")
        return sampled_frames

    def parse_dataset_for_session(
        self,
        dataset: str,
        file_id: int,
        dataset_path: str,
        frame_step: int,
        stamp_range: Tuple[int, int] = None,
        max_duration_ms: int = None
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

        Returns:
            一个包含重构后帧数据的字典，如果失败则为空字典。
        """
        if not self.is_available():
            logger.error("❌ Tactics2D库不可用，无法解析数据集")
            return {}

        # 路径验证：检查 dataset_path 是否存在
        from pathlib import Path
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
            if dataset.lower() == 'highd':
                # 修正1: LevelXParser的构造函数需要数据集的 *名称* (e.g., "highD")
                parser = LevelXParser(dataset)
            else:
                logger.error(f"不支持的数据集类型: {dataset}. 目前只支持 'highD'.")
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

            # 记录每个参与者的轨迹解析状态
            if participants:
                first_p = next(iter(participants.values()))
                logger.info(f"🔍 示例参与者信息: 类型={type(first_p)}, 属性={list(dir(first_p))}")

            # 重构数据以进行流式传输，传递实际时间戳范围
            restructured_frames = self._restructure_for_streaming(participants, frame_step, actual_stamp_range)
            
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