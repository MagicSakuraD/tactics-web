# 车辆数据来源分析

## 📊 数据来源总结

### ✅ 车辆长度和宽度：来自 `tracksMeta.csv`（静态数据）

**数据流**：

```
tracksMeta.csv (01_tracksMeta.csv)
├── 车辆1: width=4.85, height=2.12, class=Car
├── 车辆6: width=11.82, height=2.50, class=Truck
└── ...
    ↓
Tactics2D LevelXParser.parse_trajectory()
    ↓
Participant对象
├── .width = 4.85 (实际是车长)
├── .height = 2.12 (实际是车宽)
└── .class = "Car"
    ↓
dataset_parser_service.py (智能修正)
├── vehicle_length = 4.85 (大值)
├── vehicle_width = 2.12 (小值)
└── vehicle_type = "Car"
    ↓
后端发送给前端 (JSON)
{
  "length": 4.85 * coordinate_scale,
  "width": 2.12 * coordinate_scale,
  "type": "Car"
}
    ↓
前端 visualization.tsx
├── vehicleLength = data.length || 4.5
├── vehicleWidth = data.width || 2.0
└── vehicleHeight = data.type === "Truck" ? 3.5 : 1.8
```

**特点**：

- ✅ **静态数据**：每辆车的长度和宽度在整个仿真过程中**不会变化**
- ✅ **来自 tracksMeta.csv**：每个车辆 ID 对应一行数据
- ✅ **每辆车不同**：车辆 1 长度 4.85m，车辆 6 长度 11.82m（卡车）

---

### ✅ 车辆速度：来自 `tracks.csv`（动态数据）

**数据流**：

```
tracks.csv (01_tracks.csv)
├── 帧1, 车辆1: xVelocity=40.85, yVelocity=0.00
├── 帧2, 车辆1: xVelocity=40.87, yVelocity=0.00
├── 帧3, 车辆1: xVelocity=40.88, yVelocity=0.00
└── ...
    ↓
Tactics2D LevelXParser.parse_trajectory()
    ↓
State对象 (每一帧)
├── .vx = 40.85 (X方向速度)
└── .vy = 0.00 (Y方向速度)
    ↓
dataset_parser_service.py
├── vx = state.vx
└── vy = state.vy
    ↓
后端发送给前端 (JSON，每一帧)
{
  "vx": 40.85,
  "vy": 0.00
}
    ↓
前端 visualization.tsx
speed = Math.sqrt(data.vx ** 2 + data.vy ** 2)
color = speed > 15 ? "#ff4444" : speed > 8 ? "#ffaa44" : "#44aa44"
```

**特点**：

- ✅ **动态数据**：每辆车的速度在每一帧都**可能变化**
- ✅ **来自 tracks.csv**：每一帧都有新的速度值
- ✅ **实时更新**：前端根据速度实时改变车辆颜色

---

### ✅ 车辆类型：来自 `tracksMeta.csv`（静态数据）

**数据流**：

```
tracksMeta.csv
├── 车辆1: class=Car
├── 车辆6: class=Truck
└── ...
    ↓
Participant对象
└── .class = "Car" 或 "Truck"
    ↓
后端发送给前端
{
  "type": "Car" 或 "Truck"
}
    ↓
前端 visualization.tsx
vehicleHeight = data.type === "Truck" ? 3.5 : 1.8
color = data.type === "Truck" ? "#666666" : "#ff4444"
```

**特点**：

- ✅ **静态数据**：每辆车的类型在整个仿真过程中**不会变化**
- ✅ **影响渲染**：卡车更高（3.5m），轿车更矮（1.8m）
- ✅ **影响颜色**：卡车是灰色系，轿车是彩色系

---

## 📋 数据对比表

| 数据项                 | 来源文件         | 数据性质 | 更新频率 | 示例值                                       |
| ---------------------- | ---------------- | -------- | -------- | -------------------------------------------- |
| **车辆长度**           | `tracksMeta.csv` | 静态     | 不变化   | 车辆 1: 4.85m, 车辆 6: 11.82m                |
| **车辆宽度**           | `tracksMeta.csv` | 静态     | 不变化   | 车辆 1: 2.12m, 车辆 6: 2.50m                 |
| **车辆类型**           | `tracksMeta.csv` | 静态     | 不变化   | 车辆 1: Car, 车辆 6: Truck                   |
| **车辆位置 (x, y)**    | `tracks.csv`     | 动态     | 每帧更新 | 帧 1: (362.26, 21.68), 帧 2: (363.73, 21.68) |
| **车辆速度 (vx, vy)**  | `tracks.csv`     | 动态     | 每帧更新 | 帧 1: (40.85, 0.00), 帧 2: (40.87, 0.00)     |
| **车辆朝向 (heading)** | `tracks.csv`     | 动态     | 每帧更新 | 从速度向量计算                               |

---

## 🔍 验证方法

### 1. 验证车辆长度和宽度是否变化

**方法**：检查同一车辆在不同帧的数据

```javascript
// 前端控制台
console.log("车辆1在不同帧的尺寸：");
frameData.forEach((frame, idx) => {
  const vehicle1 = frame.vehicles.find((v) => v.id === 1);
  if (vehicle1) {
    console.log(`帧${idx}: length=${vehicle1.length}, width=${vehicle1.width}`);
  }
});
```

**预期结果**：

- ✅ 车辆 1 在所有帧中的 `length` 应该都是 **4.85**（或 4.85 \* coordinate_scale）
- ✅ 车辆 1 在所有帧中的 `width` 应该都是 **2.12**（或 2.12 \* coordinate_scale）
- ✅ 车辆 6（卡车）在所有帧中的 `length` 应该都是 **11.82**
- ✅ 车辆 6（卡车）在所有帧中的 `width` 应该都是 **2.50**

### 2. 验证速度是否变化

**方法**：检查同一车辆在不同帧的速度

```javascript
// 前端控制台
console.log("车辆1在不同帧的速度：");
frameData.forEach((frame, idx) => {
  const vehicle1 = frame.vehicles.find((v) => v.id === 1);
  if (vehicle1) {
    const speed = Math.sqrt(vehicle1.vx ** 2 + vehicle1.vy ** 2);
    console.log(
      `帧${idx}: vx=${vehicle1.vx}, vy=${vehicle1.vy}, speed=${speed.toFixed(
        2
      )}`
    );
  }
});
```

**预期结果**：

- ✅ 车辆 1 在不同帧中的 `vx` 和 `vy` **会变化**
- ✅ 根据 `tracks.csv`，车辆 1 在帧 1 的速度是 40.85 m/s，帧 2 是 40.87 m/s
- ✅ 前端车辆颜色会根据速度实时变化

---

## ⚠️ 重要注意事项

### 1. **尺寸数据是静态的**

- 每辆车的 `length` 和 `width` 在整个仿真过程中**不会变化**
- 这些数据来自 `tracksMeta.csv`，每个车辆 ID 只有一行数据
- 如果前端看到同一车辆在不同帧的尺寸不同，说明后端解析有问题

### 2. **速度数据是动态的**

- 每辆车的 `vx` 和 `vy` 在每一帧都**可能变化**
- 这些数据来自 `tracks.csv`，每一帧都有新的速度值
- 前端根据速度计算颜色，所以车辆颜色会实时变化

### 3. **类型数据是静态的**

- 每辆车的 `type`（Car/Truck）在整个仿真过程中**不会变化**
- 这些数据来自 `tracksMeta.csv` 的 `class` 字段
- 如果前端看到同一车辆在不同帧的类型不同，说明后端解析有问题

---

## ✅ 总结

**回答你的问题**：

1. **车辆长度是否根据 tracksMeta.csv 变化？**

   - ✅ **是的**！每辆车的长度来自 `tracksMeta.csv` 的 `width` 列（实际是车长）
   - ✅ 不同车辆有不同的长度（车辆 1: 4.85m, 车辆 6: 11.82m）
   - ✅ 但同一车辆在所有帧中的长度**不会变化**（静态数据）

2. **速度是否变化？**

   - ✅ **是的**！速度来自 `tracks.csv` 的 `xVelocity` 和 `yVelocity` 列
   - ✅ 每一帧的速度**都会变化**（动态数据）
   - ✅ 前端根据速度实时改变车辆颜色

3. **车辆宽度是否变化？**
   - ✅ **不变化**！宽度来自 `tracksMeta.csv` 的 `height` 列（实际是车宽）
   - ✅ 不同车辆有不同的宽度（车辆 1: 2.12m, 车辆 6: 2.50m）
   - ✅ 但同一车辆在所有帧中的宽度**不会变化**（静态数据）
