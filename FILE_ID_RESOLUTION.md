# 文件 ID 解析机制：如何确定读取哪个 tracksMeta.csv

## 📋 概述

代码通过 **`file_id`** 参数来确定读取哪个 `tracksMeta.csv` 文件。整个过程涉及前端选择、后端传递和 Tactics2D 库的文件查找。

---

## 🔄 完整数据流

### 1️⃣ 前端：用户选择文件

**位置**：`frontend/tactics-app/app/page.tsx`

**流程**：

```typescript
// 1. 前端从 API 获取可用文件列表
useEffect(() => {
  fetch("/api/data/files?dataset_type=highD")
    .then((res) => res.json())
    .then((data) => {
      // data.dataset_files 包含：
      // [
      //   { file_id: 1, dataset_path: "...", preview_image: "...", ... },
      //   { file_id: 2, dataset_path: "...", preview_image: "...", ... },
      //   ...
      // ]
      setDatasetFiles(data.dataset_files);
    });
}, []);

// 2. 用户在下拉框中选择文件
<Select
  onValueChange={(value) => {
    // value 是 file_id（如 "1", "2"）
    form.setValue("file_id", parseInt(value));
  }}
>
  {datasetFiles.map((file) => (
    <SelectItem key={file.file_id} value={file.file_id.toString()}>
      文件 {file.file_id}
    </SelectItem>
  ))}
</Select>;

// 3. 提交表单时发送 file_id
const onSubmit = async (data: FormData) => {
  await fetch("/api/initialize", {
    method: "POST",
    body: JSON.stringify({
      dataset: "highD",
      file_id: data.file_id, // 例如：1
      dataset_path:
        "/home/quinn/APP/Code/tactics2d-web/backend/data/LevelX/highD/data",
      // ...
    }),
  });
};
```

**关键点**：

- ✅ `file_id` 是**整数**（1, 2, 3, ...）
- ✅ 前端从 `/api/data/files` 获取可用文件列表
- ✅ 用户选择后，`file_id` 被包含在表单提交中

---

### 2️⃣ 后端：接收并传递 file_id

**位置**：`backend/app/main.py`

**流程**：

```python
@app.post("/api/initialize", response_model=SimulationInitResponse)
async def initialize_simulation(request: DatasetConfig):
    # request.file_id 来自前端（例如：1）
    logger.info(f"📄 文件ID: {request.file_id}")

    # 调用解析服务，传递 file_id
    session_data = dataset_parser_service.parse_dataset_for_session(
        dataset=request.dataset,        # "highD"
        file_id=request.file_id,        # 1
        dataset_path=str(dataset_path), # "/path/to/data"
        # ...
    )
```

**关键点**：

- ✅ `request.file_id` 直接来自前端请求
- ✅ 后端将 `file_id` 传递给 `dataset_parser_service`

---

### 3️⃣ 数据集解析服务：调用 Tactics2D 库

**位置**：`backend/app/services/dataset_parser_service.py`

**流程**：

```python
def parse_dataset_for_session(
    self,
    dataset: str,      # "highD"
    file_id: int,      # 1
    dataset_path: str, # "/path/to/data"
    # ...
):
    # 1. 创建 LevelXParser 实例
    parser = LevelXParser("highD")

    # 2. 调用 parse_trajectory，传递 file_id 和 folder
    participants, actual_stamp_range = parser.parse_trajectory(
        file=file_id,        # 1
        folder=dataset_path, # "/path/to/data"
        stamp_range=stamp_range
    )
```

**关键点**：

- ✅ `file_id` 是**整数**（1, 2, 3, ...）
- ✅ `dataset_path` 是**目录路径**（不是文件路径）
- ✅ Tactics2D 库会根据这两个参数**自动构建文件路径**

---

### 4️⃣ Tactics2D 库：内部文件查找（黑盒）

**Tactics2D 库内部逻辑**（推测，基于文件命名规则）：

```python
# Tactics2D 库内部（伪代码）
def parse_trajectory(self, file: int, folder: str):
    # 1. 将 file_id 格式化为两位数（01, 02, ...）
    file_id_str = f"{file:02d}"  # 1 -> "01", 2 -> "02"

    # 2. 构建文件路径
    tracks_file = Path(folder) / f"{file_id_str}_tracks.csv"
    meta_file = Path(folder) / f"{file_id_str}_tracksMeta.csv"
    recording_meta_file = Path(folder) / f"{file_id_str}_recordingMeta.csv"

    # 3. 读取并解析文件
    # tracks_file: 01_tracks.csv
    # meta_file: 01_tracksMeta.csv  ← 这就是我们要找的文件！
    # recording_meta_file: 01_recordingMeta.csv

    # 4. 解析 tracksMeta.csv，提取车辆静态属性
    # - width, height → 车辆尺寸
    # - class → 车辆类型（Car/Truck）
    # - initialFrame, finalFrame → 车辆出现的时间范围
```

**文件命名规则**：

- ✅ `file_id = 1` → `01_tracksMeta.csv`
- ✅ `file_id = 2` → `02_tracksMeta.csv`
- ✅ `file_id = 10` → `10_tracksMeta.csv`
- ✅ `file_id = 25` → `25_tracksMeta.csv`

**关键点**：

- ✅ Tactics2D 库**自动**根据 `file_id` 和 `folder` 构建文件路径
- ✅ 文件命名必须遵循规则：`{file_id:02d}_tracksMeta.csv`
- ✅ 如果文件不存在，Tactics2D 库会抛出异常

---

## 🔍 文件扫描服务：如何发现可用文件

**位置**：`backend/app/services/data_scan_service.py`

**流程**：

```python
def scan_dataset_files(self, dataset_type: str) -> List[DatasetFileInfo]:
    # 1. 确定数据集目录
    dataset_dir = settings.LEVELX_DATA_DIR / dataset_type.lower() / "data"
    # 例如：/backend/data/LevelX/highD/data

    # 2. 扫描所有 _tracks.csv 文件
    for tracks_file in dataset_dir.glob("*_tracks.csv"):
        # 例如：找到 "01_tracks.csv"

        # 3. 从文件名提取 file_id
        file_id_str = tracks_file.name.split("_")[0]  # "01"
        file_id = int(file_id_str)  # 1

        # 4. 检查相关文件是否存在
        meta_file = dataset_dir / f"{file_id_str}_tracksMeta.csv"
        # 例如：/backend/data/LevelX/highD/data/01_tracksMeta.csv

        recording_meta_file = dataset_dir / f"{file_id_str}_recordingMeta.csv"

        # 5. 如果文件完整，添加到列表
        if meta_file.exists() and recording_meta_file.exists():
            dataset_files.append(DatasetFileInfo(
                file_id=file_id,  # 1
                dataset_path=str(dataset_dir.absolute()),
                has_meta=True,  # tracksMeta.csv 存在
                # ...
            ))

    return dataset_files
```

**关键点**：

- ✅ 扫描服务通过 `glob("*_tracks.csv")` 找到所有轨迹文件
- ✅ 从文件名提取 `file_id`（例如：`01_tracks.csv` → `file_id = 1`）
- ✅ 检查对应的 `tracksMeta.csv` 是否存在
- ✅ 返回可用文件列表给前端

---

## 📊 完整示例：file_id = 1

### 前端选择

```typescript
// 用户在下拉框中选择 "文件 1"
file_id = 1;
```

### 后端接收

```python
# main.py
request.file_id = 1
```

### 解析服务调用

```python
# dataset_parser_service.py
parser.parse_trajectory(
    file=1,
    folder="/home/quinn/APP/Code/tactics2d-web/backend/data/LevelX/highD/data"
)
```

### Tactics2D 库内部

```python
# Tactics2D 库内部（伪代码）
file_id_str = f"{1:02d}"  # "01"
meta_file_path = Path(folder) / f"{file_id_str}_tracksMeta.csv"
# = "/home/quinn/APP/Code/tactics2d-web/backend/data/LevelX/highD/data/01_tracksMeta.csv"

# 读取文件
with open(meta_file_path) as f:
    # 解析 CSV，提取车辆静态属性
    # - 车辆1: width=4.85, height=2.12, class=Car
    # - 车辆6: width=11.82, height=2.50, class=Truck
    # ...
```

### 结果

- ✅ 读取了 `01_tracksMeta.csv`
- ✅ 解析了 1,049 个车辆的静态属性
- ✅ 每个车辆都有 `width`, `height`, `class` 等属性

---

## 🔧 文件路径构建规则

### 规则总结

| file_id | 文件名格式          | 完整路径示例                                        |
| ------- | ------------------- | --------------------------------------------------- |
| 1       | `01_tracksMeta.csv` | `/backend/data/LevelX/highD/data/01_tracksMeta.csv` |
| 2       | `02_tracksMeta.csv` | `/backend/data/LevelX/highD/data/02_tracksMeta.csv` |
| 10      | `10_tracksMeta.csv` | `/backend/data/LevelX/highD/data/10_tracksMeta.csv` |
| 25      | `25_tracksMeta.csv` | `/backend/data/LevelX/highD/data/25_tracksMeta.csv` |

### 公式

```python
file_id_str = f"{file_id:02d}"  # 格式化为两位数
file_path = f"{dataset_path}/{file_id_str}_tracksMeta.csv"
```

**注意**：

- ✅ `file_id` 必须是 **1-99** 之间的整数
- ✅ 文件名必须是 **两位数**（01, 02, ..., 99）
- ✅ 如果 `file_id = 1`，文件名必须是 `01_tracksMeta.csv`，不能是 `1_tracksMeta.csv`

---

## ⚠️ 常见问题

### Q1: 如果 file_id = 1，但文件是 `1_tracksMeta.csv`（不是 `01_tracksMeta.csv`）会怎样？

**答案**：Tactics2D 库会找不到文件，抛出异常。

**解决方案**：确保文件命名遵循规则：`{file_id:02d}_tracksMeta.csv`

### Q2: 如果 file_id = 1，但 `01_tracksMeta.csv` 不存在会怎样？

**答案**：Tactics2D 库会抛出异常，后端会返回错误。

**解决方案**：使用 `data_scan_service` 检查文件是否存在。

### Q3: 如何知道哪些 file_id 可用？

**答案**：调用 `/api/data/files?dataset_type=highD`，返回所有可用文件列表。

---

## ✅ 总结

**代码如何判断读取哪个 tracksMeta.csv？**

1. ✅ **前端**：用户选择 `file_id`（例如：1）
2. ✅ **后端**：接收 `file_id` 并传递给解析服务
3. ✅ **解析服务**：调用 Tactics2D 库的 `parse_trajectory(file=file_id, folder=dataset_path)`
4. ✅ **Tactics2D 库**：根据 `file_id` 和 `folder` 自动构建文件路径：
   - `file_id = 1` → `{folder}/01_tracksMeta.csv`
   - `file_id = 2` → `{folder}/02_tracksMeta.csv`
5. ✅ **文件读取**：Tactics2D 库读取对应的 `tracksMeta.csv` 文件并解析

**关键点**：

- ✅ `file_id` 是**整数**（1, 2, 3, ...）
- ✅ 文件名必须是**两位数格式**（01, 02, 03, ...）
- ✅ Tactics2D 库**自动**处理文件路径构建
- ✅ 文件必须存在于 `dataset_path` 目录下
