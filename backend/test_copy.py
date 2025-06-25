@app.get("/test-parser/{file_id}")
async def test_parser(file_id: int):
    """测试LevelXParser解析指定文件的基本功能"""
    if not TACTICS2D_AVAILABLE:
        raise HTTPException(status_code=500, detail="tactics2d不可用")
    
    if not DATA_FOLDER.exists():
        raise HTTPException(status_code=404, detail=f"数据文件夹不存在: {DATA_FOLDER}")
    
    try:
        # 初始化解析器
        parser = LevelXParser("highD")
        
        # 获取时间范围 - 确保转换为 Python int
        stamp_range = parser.get_stamp_range(file_id, str(DATA_FOLDER))
        stamp_range = (int(stamp_range[0]), int(stamp_range[1]))  # 转换 numpy.int64 -> int
        
        # 获取位置信息 - 确保转换为 Python int
        location_id = parser.get_location(file_id, str(DATA_FOLDER))
        location_id = int(location_id)  # 转换 numpy.int64 -> int
        
        # 解析轨迹数据（只解析很短的时间段来测试）
        test_duration = 200  # 200毫秒
        test_stamp_range = (stamp_range[0], min(stamp_range[0] + test_duration, stamp_range[1]))
        
        participants, actual_range = parser.parse_trajectory(
            file_id, 
            str(DATA_FOLDER), 
            stamp_range=test_stamp_range
        )
        
        # 确保 actual_range 也是 Python int
        actual_range = (int(actual_range[0]), int(actual_range[1]))
        
        # 分析participants数据结构
        participant_count = len(participants)
        participant_info = {}
        
        if participants:
            # 获取第一个参与者的详细信息
            first_key = list(participants.keys())[0]
            # 确保 key 是 JSON 可序列化的
            if hasattr(first_key, 'item'):  # 如果是 numpy 类型
                first_key = first_key.item()
            else:
                first_key = int(first_key)
                
            first_participant = participants[list(participants.keys())[0]]
            
            # 安全地获取属性信息，避免序列化问题
            safe_attributes = []
            for attr in dir(first_participant):
                if not attr.startswith('_') and len(safe_attributes) < 15:  # 限制数量
                    try:
                        value = getattr(first_participant, attr)
                        # 只记录简单类型的属性，并确保类型安全
                        if isinstance(value, (int, float, str, bool)):
                            safe_attributes.append({
                                "name": attr,
                                "type": str(type(value).__name__),
                                "value": str(value)[:100]  # 限制长度
                            })
                        elif isinstance(value, (list, tuple)):
                            safe_attributes.append({
                                "name": attr,
                                "type": str(type(value).__name__),
                                "value": f"length_{len(value)}"
                            })
                        else:
                            safe_attributes.append({
                                "name": attr,
                                "type": str(type(value).__name__),
                                "value": "complex_object"
                            })
                    except Exception:
                        safe_attributes.append({
                            "name": attr,
                            "type": "unknown",
                            "value": "access_error"
                        })
            
            participant_info = {
                "sample_participant_id": first_key,
                "participant_type": type(first_participant).__name__,
                "total_attributes": len(safe_attributes),
                "attributes": safe_attributes,
                "str_representation": str(first_participant)[:300] + "..." if len(str(first_participant)) > 300 else str(first_participant)
            }
        
        # 确保所有participant IDs都是JSON可序列化的
        participant_ids_safe = []
        for pid in list(participants.keys())[:10]:
            if hasattr(pid, 'item'):  # numpy类型
                participant_ids_safe.append(pid.item())
            else:
                participant_ids_safe.append(int(pid))
        
        return {
            "success": True,
            "file_id": file_id,
            "parser_dataset": "highD",
            "location_id": location_id,
            "timestamp_info": {
                "full_range_ms": stamp_range,
                "full_duration_ms": stamp_range[1] - stamp_range[0],
                "test_range_ms": test_stamp_range,
                "actual_parsed_range_ms": actual_range
            },
            "participant_analysis": {
                "total_participants": participant_count,
                "participant_ids": participant_ids_safe,
                "sample_participant": participant_info
            }
        }
        
    except Exception as e:
        # 详细的错误信息，帮助调试
        import traceback
        return {
            "success": False,
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()[-1000:]  # 最后1000字符
            },
            "test_context": {
                "file_id": file_id,
                "data_folder": str(DATA_FOLDER),
                "tactics2d_available": TACTICS2D_AVAILABLE
            }
        }