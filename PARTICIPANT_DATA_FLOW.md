# 参与者（Participants）数据流分析

## 📋 什么是"参与者"？

在交通仿真中，**参与者（Participants）** 指的是所有在道路上活动的实体：

- 🚗 **车辆（Vehicles）**：主要类型
- 🚶 **行人（Pedestrians）**：在某些数据集中存在
- 🚴 **骑行者（Cyclists）**：在某些数据集中存在

在你的项目中，**参与者 = 车辆**，因为 highD 数据集只包含车辆轨迹。

---

## 🔄 完整数据链路

### 阶段 1: 原始数据（CSV 文件）

**位置**：`backend/data/LevelX/highD/data/01_tracks.csv`

**格式**：

```csv
frame,id,x,y,width,height,xVelocity,yVelocity,xAcceleration,yAcceleration,...
1,1,362.26,21.68,4.85,2.12,40.85,0.00,0.30,0.00,...
2,1,363.73,21.68,4.85,2.12,40.87,0.00,0.30,0.00,...
```

**含义**：

- `id`: 参与者 ID（车辆编号）
- `frame`: 帧号（时间戳）
- `x, y`: 位置坐标
- `xVelocity, yVelocity`: 速度分量
- `heading`: 朝向角度（从其他字段计算）

---

### 阶段 2: Tactics2D 解析（Python 对象）

**函数**：`LevelXParser.parse_trajectory()`

**位置**：`backend/app/services/dataset_parser_service.py:255`

**代码**：

```python
participants, actual_stamp_range = parser.parse_trajectory(
    file=file_id,
    folder=dataset_path,
    stamp_range=stamp_range
)
```

**返回数据结构**：

```python
participants = {
    1: <Participant对象>,  # ID=1的车辆
    2: <Participant对象>,  # ID=2的车辆
    ...
}

# Participant对象包含：
# - trajectory: 轨迹数据
# - is_active(timestamp): 检查是否在某个时间戳活跃
# - get_state(timestamp): 获取某个时间戳的状态
```

**Participant 对象的状态（State）包含**：

- `x, y`: 位置
- `vx, vy`: 速度分量
- `heading`: 朝向
- `ax, ay`: 加速度（如果有）

---

### 阶段 3: 数据重构（转换为帧格式）

**函数**：`DatasetParserService._restructure_for_streaming()`

**位置**：`backend/app/services/dataset_parser_service.py:99`

**转换逻辑**：

```python
# 输入：以参与者为中心的数据
participants = {1: <Participant>, 2: <Participant>, ...}

# 输出：以帧为中心的数据
frames = {
    0: {
        "timestamp": 0,
        "vehicles": [
            {"id": 1, "x": 100.5, "y": 2.3, "vx": 15.2, "vy": 0.0, "heading": 0.5},
            {"id": 2, "x": 150.2, "y": 2.1, "vx": 12.8, "vy": 0.0, "heading": 0.5},
            ...
        ]
    },
    1: {
        "timestamp": 40,  # 40ms后
        "vehicles": [...]
    },
    ...
}
```

**关键步骤**：

1. **遍历时间戳**：从 `start_time` 到 `end_time`，每 `effective_step` ms 采样一次
2. **检查活跃状态**：`p_obj.is_active(timestamp)` - 判断车辆是否在该时间戳存在
3. **获取状态**：`state = get_state_method(timestamp)` - 获取车辆在该时间戳的状态
4. **提取属性**：从 `state` 对象提取 `x, y, vx, vy, heading`
5. **构建 JSON**：转换为前端需要的格式

**代码片段**：

```python
for timestamp in range(int(start_time), int(end_time), effective_step):
    frame_participants = []

    for p_id, p_obj in participants.items():
        if not p_obj.is_active(timestamp):
            continue  # 跳过不活跃的车辆

        state = get_state_method(timestamp)
        if state is None:
            continue

        frame_participants.append({
            "id": int(p_id),
            "x": round(float(state_attr_getter(state, 'x')), 3),
            "y": round(float(state_attr_getter(state, 'y')), 3),
            "vx": round(float(state_attr_getter(state, 'vx')), 3),
            "vy": round(float(state_attr_getter(state, 'vy')), 3),
            "heading": round(float(state_attr_getter(state, 'heading')), 3)
        })

    sampled_frames[frame_index] = {
        "timestamp": timestamp,
        "vehicles": frame_participants  # ← 这就是"参与者列表"
    }
```

---

### 阶段 4: 会话存储（内存）

**位置**：`backend/app/state.py`

**存储结构**：

```python
state.sessions[session_id] = {
    "id": session_id,
    "config": {...},
    "map_data": {...},
    "trajectory_frames": {  # ← 存储所有帧数据
        0: {"timestamp": 0, "vehicles": [...]},
        1: {"timestamp": 40, "vehicles": [...]},
        ...
    },
    "total_frames": 1000,
    "participant_count": 50,  # ← 总参与者数量（所有帧中出现的唯一ID数）
    ...
}
```

---

### 阶段 5: WebSocket 传输

**函数**：`handle_session_stream()`

**位置**：`backend/app/api/websocket.py:55`

**传输逻辑**：

```python
for frame_key in sorted_frame_keys:
    frame_data = trajectory_frames[frame_key]
    # frame_data = {"timestamp": 0, "vehicles": [...]}

    await connection_manager.send_personal_message({
        "type": "simulation_frame",
        "session_id": session_id,
        "frame_number": frame_key,
        "data": frame_data  # ← 包含 vehicles 数组
    }, client_id)

    await asyncio.sleep(frame_interval)  # 控制帧率
```

**WebSocket 消息格式**：

```json
{
  "type": "simulation_frame",
  "session_id": "sid_abc123",
  "frame_number": 0,
  "data": {
    "timestamp": 0,
    "vehicles": [
      {
        "id": 1,
        "x": 100.5,
        "y": 2.3,
        "vx": 15.2,
        "vy": 0.0,
        "heading": 0.5
      },
      ...
    ]
  }
}
```

---

### 阶段 6: 前端接收（React Hook）

**函数**：`useWebSocket()`

**位置**：`frontend/tactics-app/hooks/useWebSocket.ts:52`

**接收逻辑**：

```typescript
wsRef.current.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === "simulation_frame") {
    setFrameData(message.data); // ← 设置帧数据
    // message.data = {timestamp: 0, vehicles: [...]}
  }
};
```

**状态更新**：

```typescript
// frontend/tactics-app/app/dashboard/page.tsx:106
useEffect(() => {
  if (frameData) {
    setCurrentFrame(frameData.frame_number || 0);
    setParticipantCount(frameData.vehicles?.length || 0); // ← 参与者数量
  }
}, [frameData]);
```

---

### 阶段 7: 3D 渲染（Three.js）

**组件**：`Vehicle`

**位置**：`frontend/tactics-app/app/dashboard/components/visualization.tsx:24`

**渲染逻辑**：

```typescript
{
  frameData &&
    frameData.vehicles &&
    frameData.vehicles.map((vehicle: VehicleData) => (
      <Vehicle key={vehicle.id} data={vehicle} />
    ));
}
```

**Vehicle 组件**：

```typescript
const Vehicle = ({ data }: { data: VehicleData }) => {
  // 位置转换：2D -> 3D
  const position: [number, number, number] = [
    data.x, // X坐标（沿道路方向）
    0.9, // Y坐标（车辆高度）
    data.y, // Z坐标（横向方向）
  ];

  // 旋转：根据heading角度
  const rotation: [number, number, number] = [
    0,
    data.heading, // 绕Y轴旋转（车辆朝向）
    0,
  ];

  // 颜色：根据速度
  const speed = Math.sqrt(data.vx ** 2 + data.vy ** 2);
  const color = speed > 15 ? "#ff4444" : speed > 8 ? "#ffaa44" : "#44aa44";

  return (
    <mesh position={position} rotation={rotation}>
      <boxGeometry args={[4.5, 1.8, 2.0]} />
      <meshStandardMaterial color={color} />
    </mesh>
  );
};
```

---

## 📊 数据流总结图

```
CSV文件 (01_tracks.csv)
    ↓
LevelXParser.parse_trajectory()
    ↓
participants = {1: <Participant>, 2: <Participant>, ...}
    ↓
_restructure_for_streaming()
    ↓
frames = {
    0: {"timestamp": 0, "vehicles": [...]},
    1: {"timestamp": 40, "vehicles": [...]},
    ...
}
    ↓
state.sessions[session_id]["trajectory_frames"] = frames
    ↓
WebSocket: handle_session_stream()
    ↓
发送消息: {"type": "simulation_frame", "data": frame_data}
    ↓
前端: useWebSocket() 接收
    ↓
setFrameData(message.data)
    ↓
useEffect 更新: setParticipantCount(frameData.vehicles?.length)
    ↓
Three.js 渲染: frameData.vehicles.map(vehicle => <Vehicle />)
```

---

## 🎯 关键函数总结

| 阶段         | 函数/方法                         | 位置                           | 作用                           |
| ------------ | --------------------------------- | ------------------------------ | ------------------------------ |
| **解析**     | `LevelXParser.parse_trajectory()` | Tactics2D 库                   | 从 CSV 解析为 Participant 对象 |
| **转换**     | `_restructure_for_streaming()`    | `dataset_parser_service.py:99` | 转换为帧格式                   |
| **检查**     | `p_obj.is_active(timestamp)`      | Tactics2D 库                   | 检查参与者是否活跃             |
| **获取状态** | `get_state_method(timestamp)`     | Tactics2D 库                   | 获取参与者状态                 |
| **存储**     | `state.sessions[session_id]`      | `state.py`                     | 存储帧数据                     |
| **传输**     | `handle_session_stream()`         | `websocket.py:55`              | WebSocket 流式传输             |
| **接收**     | `useWebSocket()`                  | `useWebSocket.ts:28`           | 前端接收数据                   |
| **渲染**     | `<Vehicle>` 组件                  | `visualization.tsx:24`         | Three.js 3D 渲染               |

---

## 💡 参与者信息的来源

### 1. **位置信息（x, y）**

- **来源**：CSV 文件的 `x, y` 列
- **函数**：`state_attr_getter(state, 'x')`, `state_attr_getter(state, 'y')`
- **单位**：米（经过坐标缩放）

### 2. **速度信息（vx, vy）**

- **来源**：CSV 文件的 `xVelocity, yVelocity` 列
- **函数**：`state_attr_getter(state, 'vx')`, `state_attr_getter(state, 'vy')`
- **单位**：米/秒

### 3. **朝向信息（heading）**

- **来源**：从速度向量计算，或 CSV 的 `heading` 列
- **函数**：`state_attr_getter(state, 'heading')`
- **单位**：弧度

### 4. **参与者数量**

- **来源**：`frameData.vehicles.length`
- **位置**：`dashboard/page.tsx:109`
- **含义**：当前帧中活跃的参与者数量

### 5. **参与者 ID**

- **来源**：CSV 文件的 `id` 列
- **存储**：`vehicle.id`
- **用途**：唯一标识每辆车

---

## 🎨 UI 显示

### 左侧边栏显示

- **"参与者 0"**：显示 `frameData.vehicles.length`
- **含义**：当前帧中活跃的车辆数量
- **更新**：每收到一帧数据就更新

### 3D 场景显示

- **每个参与者**：渲染为一个 3D 盒子（车辆）
- **颜色**：根据速度变化（绿色=慢，黄色=中，红色=快）
- **位置**：根据 `x, y` 坐标
- **朝向**：根据 `heading` 角度

---

## ✅ 总结

**参与者的完整生命周期**：

1. 📄 **CSV 文件** → 原始轨迹数据
2. 🔧 **Tactics2D 解析** → Python 对象（Participant）
3. 🔄 **数据重构** → 帧格式（vehicles 数组）
4. 💾 **会话存储** → 内存中的 frames 字典
5. 📡 **WebSocket 传输** → 实时流式发送
6. 🎨 **前端渲染** → Three.js 3D 可视化

**关键点**：

- 参与者 = 车辆（在你的项目中）
- 每帧数据包含该时间戳所有活跃的参与者
- 参与者信息（位置、速度、朝向）来自 CSV 文件
- 前端通过 `frameData.vehicles.length` 获取参与者数量
