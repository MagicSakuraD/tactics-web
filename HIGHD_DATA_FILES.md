# HighD 数据集文件说明

## 📁 文件结构

HighD 数据集每个场景（recording）包含 **3 个核心 CSV 文件**：

```
backend/data/LevelX/highD/data/
├── 01_tracks.csv          # 轨迹数据（每一帧每个车辆的状态）
├── 01_tracksMeta.csv      # 车辆元数据（每个车辆的静态属性）
└── 01_recordingMeta.csv   # 记录元数据（整个场景的统计信息）
```

---

## 📊 文件详细说明

### 1. `01_tracks.csv` - 轨迹数据（核心文件）

**作用**：存储每一帧每个车辆的位置、速度、加速度等动态数据。

**格式**：

```csv
frame,id,x,y,width,height,xVelocity,yVelocity,xAcceleration,yAcceleration,...
1,1,362.26,21.68,4.85,2.12,40.85,0.00,0.30,0.00,...
2,1,363.73,21.68,4.85,2.12,40.87,0.00,0.30,0.00,...
```

**关键字段**：

- `frame`: 帧号（时间戳，从 1 开始）
- `id`: 车辆 ID
- `x, y`: 车辆位置坐标（米）
- `width, height`: **注意**：在 tracks.csv 中，`width` 实际是车辆**长度**，`height` 实际是车辆**宽度**（highD 数据集的特殊命名）
- `xVelocity, yVelocity`: 速度分量（米/秒）
- `xAcceleration, yAcceleration`: 加速度分量（米/秒 ²）
- `laneId`: 车道 ID

**数据量**：非常大（348,752 行），包含所有车辆在所有帧的数据。

---

### 2. `01_tracksMeta.csv` - 车辆元数据

**作用**：存储每个车辆的静态属性（尺寸、类型、活动时间范围等）。

**格式**：

```csv
id,width,height,initialFrame,finalFrame,numFrames,class,drivingDirection,...
1,4.85,2.12,1,33,33,Car,2,...
2,4.24,1.92,1,130,130,Car,1,...
6,11.82,2.50,1,185,185,Truck,2,...
```

**关键字段**：

- `id`: 车辆 ID
- `width`: 车辆宽度（米）
- `height`: 车辆高度（米，垂直方向）
- `initialFrame, finalFrame`: 车辆首次和最后出现的帧号
- `numFrames`: 车辆出现的总帧数
- `class`: 车辆类型（`Car` 或 `Truck`）
- `drivingDirection`: 行驶方向（1 或 2）

**数据量**：较小（1,049 行），每个车辆一行。

**示例数据**：

- 车辆 1：轿车，4.85m 宽，2.12m 高，出现在帧 1-33
- 车辆 6：卡车，11.82m 宽，2.50m 高，出现在帧 1-185

---

### 3. `01_recordingMeta.csv` - 记录元数据

**作用**：存储整个场景（recording）的统计信息和元数据。

**格式**：

```csv
id,frameRate,locationId,speedLimit,month,weekDay,startTime,duration,totalDrivenDistance,totalDrivenTime,numVehicles,numCars,numTrucks,...
1,25,2,-1.00,09.2017,Tue,08:38,901.56,418549.19,13908.12,1047,863,184,...
```

**关键字段**：

- `frameRate`: 帧率（25 Hz，即每 40ms 一帧）
- `duration`: 记录时长（秒）
- `numVehicles`: 总车辆数（1047）
- `numCars`: 轿车数量（863）
- `numTrucks`: 卡车数量（184）
- `totalDrivenDistance`: 总行驶距离（米）
- `totalDrivenTime`: 总行驶时间（秒）

**数据量**：极小（3 行，包含表头和 1 行数据）。

---

## 🔧 代码中的使用方式

### ✅ 当前代码如何使用这些文件

#### 1. **通过 Tactics2D 库自动解析**

代码**不直接读取**这些 CSV 文件，而是通过 `Tactics2D` 库的 `LevelXParser` 来解析：

```python
# backend/app/services/dataset_parser_service.py:474
parser = LevelXParser("highD")
participants, actual_stamp_range = parser.parse_trajectory(
    file=file_id,           # 文件ID（如 1 表示 01_xxx.csv）
    folder=dataset_path,    # 数据集目录路径
    stamp_range=stamp_range # 可选的时间范围
)
```

**Tactics2D 库会自动**：

1. 读取 `{file_id}_tracks.csv` → 解析轨迹数据
2. 读取 `{file_id}_tracksMeta.csv` → 解析车辆元数据
3. 读取 `{file_id}_recordingMeta.csv` → 解析记录元数据（可选）

#### 2. **文件存在性检查**

`data_scan_service.py` 会检查这些文件是否存在：

```python
# backend/app/services/data_scan_service.py:111-123
for tracks_file in dataset_dir.glob("*_tracks.csv"):
    file_id = int(tracks_file.name.split("_")[0])

    # 检查相关文件是否存在
    meta_file = dataset_dir / f"{file_id_str}_tracksMeta.csv"
    recording_meta_file = dataset_dir / f"{file_id_str}_recordingMeta.csv"

    if meta_file.exists() and recording_meta_file.exists():
        # 文件完整，可以解析
```

---

## 📈 数据流转换过程

### 阶段 1: CSV 文件 → Tactics2D 对象

```
01_tracks.csv          →  Participant.trajectory (轨迹数据)
01_tracksMeta.csv      →  Participant.width, length, type (静态属性)
01_recordingMeta.csv   →  (元数据，用于验证)
```

### 阶段 2: Tactics2D 对象 → 帧格式数据

```python
# dataset_parser_service.py:_restructure_for_streaming()
for timestamp in range(start_time, end_time, effective_step):
    for p_id, p_obj in participants.items():
        state = p_obj.get_state(timestamp)  # 从轨迹数据获取状态
        # 提取：
        # - x, y (位置)
        # - vx, vy (速度)
        # - heading (朝向)
        # - width, length, type (从 tracksMeta 获取)
```

### 阶段 3: 帧格式数据 → 前端 JSON

```json
{
  "frames": {
    "0": {
      "timestamp": 0,
      "vehicles": [
        {
          "id": 1,
          "x": 362.26,
          "y": 21.68,
          "vx": 40.85,
          "vy": 0.0,
          "heading": 0.0,
          "length": 4.85,
          "width": 2.12,
          "type": "Car"
        }
      ]
    }
  }
}
```

---

## ⚠️ 重要注意事项

### 1. **字段命名混淆**

HighD 数据集的 `tracks.csv` 中：

- `width` 列 → **实际是车辆长度**
- `height` 列 → **实际是车辆宽度**

但 `tracksMeta.csv` 中：

- `width` → **正确的车辆宽度**
- `height` → **正确的车辆高度**

**代码处理**：

```python
# dataset_parser_service.py:354-361
# 智能推断：如果length不存在，尝试从其他属性推断
if (vehicle_length is None or vehicle_length == 2.0) and vehicle_width and vehicle_width > 3.0:
    # width看起来像长度（>3米），可能是highD的特殊映射
    vehicle_length = vehicle_width
    vehicle_width = vehicle_height_attr if vehicle_height_attr < 3.0 else 2.0
```

### 2. **文件命名规则**

所有文件必须遵循命名规则：

- `{file_id:02d}_tracks.csv`（如 `01_tracks.csv`）
- `{file_id:02d}_tracksMeta.csv`（如 `01_tracksMeta.csv`）
- `{file_id:02d}_recordingMeta.csv`（如 `01_recordingMeta.csv`）

`file_id` 必须是**两位数**（01, 02, ..., 99）。

### 3. **数据量**

- `tracks.csv`: **348,752 行**（非常大）
- `tracksMeta.csv`: **1,049 行**（较小）
- `recordingMeta.csv`: **3 行**（很小）

解析 `tracks.csv` 是性能瓶颈，Tactics2D 库会进行优化。

---

## 🔍 如何验证文件是否正确使用

### 1. **检查日志**

启动后端后，查看日志：

```
🚀 开始解析数据集: highD, 文件ID: 1, 路径: /path/to/data
✅ 成功从tactics2d解析了 1047 个参与者
🕐 实际时间戳范围: (0, 22539)
📊 参与者详细统计:
   👥 总参与者数: 1047
   🚗 参与者类型分布:
      • Car: 863 个 (82.4%)
      • Truck: 184 个 (17.6%)
```

### 2. **检查文件完整性**

使用 `data_scan_service` 的 API：

```bash
GET /api/data/files?dataset_type=highD
```

返回：

```json
{
  "dataset_files": [
    {
      "file_id": 1,
      "has_tracks": true,
      "has_meta": true // tracksMeta 和 recordingMeta 都存在
    }
  ]
}
```

---

## 📚 参考资料

- [HighD 数据集官方文档](https://www.highd-dataset.com/)
- [Tactics2D LevelXParser 文档](https://tactics2d.readthedocs.io/en/latest/api/dataset_parser/)

---

## ✅ 总结

| 文件                | 作用                               | 代码使用方式                                            | 数据量     |
| ------------------- | ---------------------------------- | ------------------------------------------------------- | ---------- |
| `tracks.csv`        | 轨迹数据（每一帧每个车辆的状态）   | 通过 `LevelXParser.parse_trajectory()` 自动解析         | 348,752 行 |
| `tracksMeta.csv`    | 车辆元数据（尺寸、类型、时间范围） | 通过 `LevelXParser.parse_trajectory()` 自动解析         | 1,049 行   |
| `recordingMeta.csv` | 记录元数据（场景统计信息）         | 通过 `LevelXParser.parse_trajectory()` 自动解析（可选） | 3 行       |

**关键点**：

- ✅ 代码**不直接读取**CSV 文件，而是通过 Tactics2D 库
- ✅ Tactics2D 库会自动处理文件命名和格式
- ✅ 只需要提供 `file_id` 和 `dataset_path`，库会自动找到对应的文件
- ✅ 文件必须遵循命名规则：`{file_id:02d}_xxx.csv`
