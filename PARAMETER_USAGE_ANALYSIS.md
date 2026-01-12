# 高级参数使用情况分析

## 📊 参数使用情况总结

| 参数 | 前端定义 | 后端接收 | 后端使用 | 状态 |
|------|---------|---------|---------|------|
| `stamp_start` / `stamp_end` | ✅ | ✅ | ✅ | **有效** |
| `frame_step` | ✅ | ✅ | ✅ | **有效** |
| `perception_range` | ✅ | ✅ | ❌ | **安慰剂参数** |
| `max_duration_ms` | ✅ | ✅ | ⚠️ | **部分有效** |

---

## ✅ 有效参数

### 1. 时间戳范围 (`stamp_start`, `stamp_end`)

**使用情况**：✅ **完全有效**

**数据流**：
```
前端表单
  ↓
POST /api/simulation/initialize
  ↓
main.py:206: stamp_range=(request.stamp_start, request.stamp_end)
  ↓
dataset_parser_service.py:325: parser.parse_trajectory(stamp_range=stamp_range)
  ↓
Tactics2D库: 只解析指定时间范围内的数据
```

**作用**：
- ✅ 限制解析的时间范围
- ✅ 减少内存占用
- ✅ 加快解析速度
- ✅ 支持时间片段分析

**代码位置**：
- 接收：`backend/app/main.py:206`
- 使用：`backend/app/services/dataset_parser_service.py:325`

---

### 2. 帧步长 (`frame_step`)

**使用情况**：✅ **完全有效**

**数据流**：
```
前端表单: frame_step=5
  ↓
main.py:205: frame_step=request.frame_step
  ↓
dataset_parser_service.py:340: _restructure_for_streaming(..., frame_step, ...)
  ↓
dataset_parser_service.py:166: effective_step = BASE_TIME_STEP * frame_step
  ↓
实际采样间隔 = 40ms × 5 = 200ms（5倍速）
```

**作用**：
- ✅ 控制数据降采样率
- ✅ 减少传输数据量
- ✅ 降低前端渲染压力
- ✅ 支持不同精度的可视化

**代码位置**：
- 接收：`backend/app/main.py:205`
- 使用：`backend/app/services/dataset_parser_service.py:166`

**示例**：
- `frame_step=1`: 每40ms一帧（25Hz，全精度）
- `frame_step=5`: 每200ms一帧（5Hz，5倍速）
- `frame_step=10`: 每400ms一帧（2.5Hz，10倍速）

---

## ❌ 无效参数（安慰剂）

### 3. 感知范围 (`perception_range`)

**使用情况**：❌ **完全没有使用！**

**问题**：
- ✅ 前端有输入框（`page.tsx:522`）
- ✅ 后端接收了参数（`requests.py:70`）
- ❌ **后端代码中没有任何地方使用它！**

**搜索证据**：
```bash
# 后端代码中只有定义，没有使用
backend/app/models/requests.py:70: perception_range: float = Field(50.0, ...)
# 没有其他任何地方引用 perception_range
```

**应该做什么**：
`perception_range` 应该用于**空间裁剪（Spatial Culling）**，即：
- 只返回距离某个参考点（如地图中心）一定范围内的车辆
- 减少传输的数据量
- 提升渲染性能

**当前状态**：前端传了，后端接收了，但**完全忽略了**！

---

## ⚠️ 部分有效参数

### 4. 最大持续时间 (`max_duration_ms`)

**使用情况**：⚠️ **部分有效**

**问题**：
- ✅ 前端有输入框
- ✅ 后端接收了参数（`main.py:207`）
- ✅ `parse_dataset_for_session` 接收了参数（`dataset_parser_service.py:267`）
- ❌ **但没有传递给 `parse_trajectory`**（注释说移除了）
- ✅ 但在 `helpers.py` 中有 `validate_timestamp_range` 函数使用了它

**代码证据**：
```python
# dataset_parser_service.py:323
# 修正3: 移除不支持的 'max_duration_ms' 参数
participants, actual_stamp_range = parser.parse_trajectory(
    file=file_id,
    folder=dataset_path,
    stamp_range=stamp_range
    # max_duration_ms 被移除了！
)
```

**实际作用**：
- `helpers.py` 中的 `validate_timestamp_range` 函数会限制时间范围
- 但这个函数**没有被调用**！

**当前状态**：参数传递了，但**没有被实际使用**。

---

## 🔧 修复建议

### 优先级 1: 实现 `perception_range` 空间过滤

**位置**：`backend/app/services/dataset_parser_service.py:_restructure_for_streaming()`

**实现方案**：
```python
def _restructure_for_streaming(
    self, 
    participants: Dict[int, Any], 
    frame_step: int, 
    actual_stamp_range: Tuple[int, int] = None,
    perception_range: float = None,  # 新增参数
    reference_point: Tuple[float, float] = None  # 参考点（地图中心）
) -> Dict[int, List[Dict]]:
    # ...
    for timestamp in range(int(start_time), int(end_time), effective_step):
        frame_participants = []
        
        for p_id, p_obj in participants.items():
            # ... 获取状态 ...
            
            # 空间过滤：如果设置了perception_range，只保留范围内的车辆
            if perception_range and reference_point:
                x, y = state_attr_getter(state, 'x'), state_attr_getter(state, 'y')
                ref_x, ref_y = reference_point
                distance = math.sqrt((x - ref_x)**2 + (y - ref_y)**2)
                if distance > perception_range:
                    continue  # 跳过超出范围的车辆
            
            frame_participants.append({...})
```

**参考点计算**：
- 可以从地图数据中计算中心点
- 或者使用第一帧所有车辆的平均位置

---

### 优先级 2: 修复 `max_duration_ms`

**方案A：移除参数**（如果不需要）
- 从前端移除输入框
- 从后端模型移除字段

**方案B：实现时间范围限制**（如果需要）
```python
# 在 parse_dataset_for_session 中
if max_duration_ms and stamp_range:
    start, end = stamp_range
    if end - start > max_duration_ms:
        end = start + max_duration_ms
        stamp_range = (start, end)
        logger.info(f"时间范围已限制为 {max_duration_ms}ms")
```

---

## 📝 总结

### 当前状态

1. ✅ **`stamp_start` / `stamp_end`**：完全有效，正确使用
2. ✅ **`frame_step`**：完全有效，正确使用
3. ❌ **`perception_range`**：**安慰剂参数**，需要实现空间过滤
4. ⚠️ **`max_duration_ms`**：部分有效，需要修复或移除

### 建议

**短期**：
- 在前端表单中**禁用或隐藏** `perception_range` 输入框（如果暂时不实现）
- 或者添加提示："此功能暂未实现"

**长期**：
- 实现 `perception_range` 的空间过滤功能
- 修复或移除 `max_duration_ms` 参数

### 用户建议

**对于用户**：
- ✅ **`frame_step`**：根据需求选择
  - 流畅预览：`5-10`
  - 详细分析：`1`
- ✅ **`stamp_start` / `stamp_end`**：用于限制时间范围
- ❌ **`perception_range`**：**目前无效，可以忽略**
- ⚠️ **`max_duration_ms`**：**目前无效，可以忽略**
