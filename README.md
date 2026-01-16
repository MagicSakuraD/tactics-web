# Tactics2D-Web 技术文档

## 项目简介

Tactics2D-Web 是一个基于 **FastAPI + Next.js + Three.js** 的交通轨迹可视化 Demo。  
**当前阶段项目目标只有一个：用 Three.js 可视化 highD（LevelX）数据集。**  
后端负责解析 OSM 地图与 highD 轨迹，并通过 WebSocket 流式推送帧数据；前端负责渲染与交互。

---

## 技术架构

### 后端技术栈

- **核心框架**：Python 3.8+, FastAPI 0.113+（异步 Web 框架，自动生成 OpenAPI 文档）
- **实时通信**：WebSocket（原生 WebSocket 支持，非 Socket.IO）
- **数据验证**：Pydantic 2.5+（类型安全的数据模型和验证）
- **性能优化**：orjson 3.9+（高性能 JSON 序列化，比标准库快 2-3 倍）
- **日志系统**：structlog 23.2+（结构化日志，便于调试和监控）
- **图像处理**：Pillow 10.0+（用于生成缩略图等）
- **核心算法**：Tactics2D 0.1+（轨迹数据解析和处理库）
- **HTTP 客户端**：httpx 0.26+（异步 HTTP 请求）

### 前端技术栈

- **核心框架**：Next.js 15.3.3（App Router，服务端渲染）
- **UI 库**：React 19.0.0（最新版本，支持并发特性）
- **类型系统**：TypeScript 5.x（完整类型支持）
- **3D 渲染**：
  - Three.js 0.177+（底层 3D 引擎）
  - @react-three/fiber 9.1+（React 化的 Three.js）
  - @react-three/drei 10.3+（Three.js 工具库）
- **样式方案**：TailwindCSS 4.x（原子化 CSS，支持 CSS Variables）
- **UI 组件库**：
  - shadcn/ui（基于 Radix UI 的可访问组件）
  - Radix UI（无障碍 UI 原语）
  - Lucide React（图标库）
- **表单处理**：React Hook Form 7.58+ + Zod 3.25+（类型安全的表单验证）
- **主题系统**：next-themes 0.4+（支持明暗主题切换）
- **通知系统**：Sonner 2.0+（优雅的 Toast 通知）

### 数据支持（当前范围）

- **地图格式**：OSM（OpenStreetMap）格式
- **轨迹数据集**：**仅 highD（LevelX）**（其它 LevelX：inD/rounD/exiD/uniD 暂不作为目标，README 不再承诺可用）

---

## 我需要用到哪些 Tactics2D Python API？

本项目为了实现 “highD 可视化”，在后端**只需要用到很少的 Tactics2D API**。你可以把 Tactics2D 当成“数据解析器”，不需要引入控制器/仿真环境等复杂模块。

### 必须用到（本项目核心依赖）

- **`tactics2d.dataset_parser.LevelXParser`**：读取 highD 的轨迹数据

  - 我们用到的方法：`parse_trajectory(file, folder, stamp_range=None, ids=None)`
  - 说明：它会根据 `file` 自动读取 `%02d_tracks.csv` 和 `%02d_tracksMeta.csv`。
  - 官方文档：[`LevelXParser` API](https://tactics2d.readthedocs.io/en/latest/api/dataset_parser/#tactics2d.dataset_parser.LevelXParser)

- **`tactics2d.map.parser.OSMParser`**：读取 OSM 地图（供前端画道路/车道线）
  - 目前在 `backend/app/services/map_service.py` 中使用（通过 `parser.parse(...)` 解析 XML）。

### 可能会用到（可选）

- **`LevelXParser.get_stamp_range(file, folder)`**：获取数据文件的时间范围（ms）

  - 当前我们主要依赖 `parse_trajectory` 返回的 `actual_stamp_range`，但你也可以用它做 UI 默认值/预检查。

- **`LevelXParser.get_location(file, folder)`**：读取 `%02d_recordingMeta.csv` 的 locationId
  - 目前业务逻辑未使用，仅在你需要“按场景/地点做过滤或展示”时才值得接入。

### 你用不到（可以忽略）

- **`tactics2d.controller.*`**：控制器相关（例如轨迹跟踪、控制策略）

  - 本项目当前不做闭环控制/车辆动力学控制，因此不需要。
  - 文档入口：[`tactics2d.controller` API](https://tactics2d.readthedocs.io/en/latest/api/controller/)

- **`tactics2d.envs.*` / `tactics2d.physics.*` / `tactics2d.sensor.*` / `tactics2d.traffic.*`**：仿真环境/物理/传感器/交通规则

  - 本项目目标是“回放并渲染 highD 数据”，不是构建完整仿真器，因此可以全部不碰。

- **`tactics2d.geometry.*` / `tactics2d.interpolator.*` / `tactics2d.participant.*`**：高级几何/插值/参与者模型
  - 这些会被 `LevelXParser` 和 `OSMParser` 在内部间接使用，但我们不需要在业务层直接调用它们。

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Next.js)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  主页组件    │  │  仪表盘组件  │  │  可视化组件  │     │
│  │  (Form)      │  │  (Dashboard) │  │  (Three.js)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐   │
│  │         React Hook Form + Zod 验证                 │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐   │
│  │         WebSocket Hook (useWebSocket)              │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    后端 (FastAPI)                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  REST API    │  │  WebSocket   │  │  会话管理    │     │
│  │  Endpoints   │  │  Endpoint    │  │  (State)     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐   │
│  │             服务层 (Services)                        │   │
│  │  • MapService (地图解析)                            │   │
│  │  • DatasetParserService (轨迹解析)                  │   │
│  │  • WebSocketManager (连接管理)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐   │
│  │             工具层 (Utils)                           │   │
│  │  • SimpleFormatter (数据格式化)                     │   │
│  │  • Tactics2DWrapper (算法库封装)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐   │
│  │         Tactics2D 核心库 + 数据文件                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 主要功能

### 核心功能（当前范围）

- ✅ **地图解析与可视化**：支持 OSM 格式地图文件解析，自动提取道路、车道、边界等要素
- ✅ **轨迹数据解析**：解析 **highD（LevelX）** 轨迹数据并流式推送
- ✅ **仿真会话管理**：基于 UUID 的会话系统，支持多用户并发访问
- ✅ **WebSocket 实时推送**：低延迟的帧数据流式传输，支持可配置帧率（FPS）
- ✅ **Three.js 3D 渲染**：
  - 动态车辆渲染（**Car 为红色系，Truck 为蓝色系**；并根据速度有深浅变化）
  - 道路/车道线可视化（纯几何 mesh：路面为平面，标线为细长方块段 `InstancedMesh`）
  - 可交互的相机控制（OrbitControls：默认俯视，旋转锁定，仅平移 + 缩放）
  - 响应式场景适配
- ✅ **参数配置**：
  - 帧步长（frame_step）控制
  - 时间范围筛选（stamp_start, stamp_end）
  - 最大仿真时长限制
  - 参与者筛选（可扩展）
- ✅ **播放控制**：当前仅支持“开始一次流式播放”（暂停/停止/重播属于后续扩展）

### 用户体验特性

- 🎨 **现代化 UI**：基于 shadcn/ui 的组件系统，支持明暗主题切换
- 📱 **响应式设计**：适配桌面和移动设备
- 🔔 **实时反馈**：Toast 通知系统，操作状态实时提示
- 🎯 **类型安全**：前后端完整的 TypeScript/Pydantic 类型定义
- 📊 **结构化日志**：后端使用 structlog，便于问题排查

---

## 快速部署

### 环境要求

- **后端**：Python 3.8+
- **前端**：Node.js 18+（推荐 20+）
- **系统**：Linux / macOS / Windows（推荐 Linux）

### 1. 克隆项目

```bash
git clone https://github.com/your-org/tactics2d-web.git
cd tactics2d-web
```

### 2. 后端部署

#### 2.1 安装依赖

**方法一：使用 uv（推荐，更快）**

```bash
cd backend

# 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境（默认创建在 .venv 目录）
uv venv
# 或指定目录名
uv venv venv

# 激活虚拟环境（根据实际创建的目录名选择）
source venv/bin/activate      # 如果使用 uv venv venv
# 或
source .venv/bin/activate     # 如果使用 uv venv（默认）
# Windows: venv\Scripts\activate 或 .venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt
```

**方法二：使用标准 venv**

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**注意**：

- 如果使用标准 venv 时遇到 `ensurepip is not available` 错误（常见于 Debian/Ubuntu），请先安装 `python3-venv` 包：
  ```bash
  sudo apt install python3-venv  # 或 python3.12-venv（根据 Python 版本）
  ```
- 如果 `tactics2d` 库安装失败，请参考 [Tactics2D 官方文档](https://github.com/your-org/tactics2d) 进行安装。

#### 2.2 配置数据路径

在 `backend/app/config.py` 中可以自定义数据路径，或使用默认路径：

- **地图文件（OSM）**：`backend/data/highD_map/`
- **轨迹数据集**：`backend/data/LevelX/highD/data/`

确保数据文件具有正确的读取权限。

#### 2.3 启动 FastAPI 服务

**开发模式**（自动重载）：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**生产模式**：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

服务启动后，访问：

- API 文档：http://localhost:8000/docs（Swagger UI）
- 备用文档：http://localhost:8000/redoc（ReDoc）
- 健康检查：http://localhost:8000/api/status

### 3. 前端部署

#### 3.1 安装依赖

```bash
cd frontend/tactics-app
npm install
# 或使用 yarn/pnpm
yarn install
# pnpm install
```

#### 3.2 配置环境变量（可选）

创建 `.env.local` 文件（如果后端地址不是默认值）：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

#### 3.3 启动开发服务器

```bash
npm run dev
# 或
yarn dev
# pnpm dev
```

#### 3.4 构建生产版本

```bash
npm run build
npm start
```

#### 3.5 访问页面

浏览器打开 [http://localhost:3000](http://localhost:3000)

---

## 使用说明

### 1. 初始化仿真会话

在主页（`/`）填写以下参数：

- **地图路径**：OSM 文件的绝对路径，例如 `/path/to/backend/data/highD_map/highD_1.osm`
- **数据集路径**：轨迹数据目录的绝对路径，例如 `/path/to/backend/data/LevelX/highD/data`
- **数据集类型**：选择数据集格式（highD/inD/rounD/exiD/uniD）
- **文件 ID**：数据集文件编号（如 highD 的 `01`, `02` 等）
- **帧步长**：每隔多少帧采样一次（默认 1，即每帧都采样）
- **时间范围**（可选）：起始和结束时间戳，用于筛选特定时间段
- **最大时长**（可选）：限制仿真总时长（毫秒）

点击"初始化仿真"后，系统会：

1. 验证文件路径
2. 解析 OSM 地图文件
3. 解析轨迹数据集
4. 创建会话并返回会话 ID 和地图数据

### 2. 进入仪表盘

初始化成功后，自动跳转到仪表盘页面（`/dashboard`），或手动访问：

```
http://localhost:3000/dashboard?session_id=<会话ID>
```

### 3. 可视化控制

在仪表盘页面：

- **3D 场景**：默认俯视（top-down）。鼠标拖拽为**平移**，滚轮缩放；当前版本锁定旋转（避免视角混乱）
- **侧边栏控制**：
  - 播放/暂停按钮
  - 帧率（FPS）滑块
  - 帧步长调整
  - 参与者筛选（可扩展）
- **实时数据**：显示当前帧数、总帧数、参与者数量等信息

### 4. WebSocket 通信

系统使用 WebSocket 进行实时数据传输：

- **连接地址**：`ws://localhost:8000/ws/simulation`
- **消息格式**：JSON
- **主要消息类型**：
  - `start_session_stream`：开始流式传输
  - `simulation_frame`：帧数据（`frame_number` 在消息顶层，`data` 内含 `{ timestamp, vehicles }`）
  - `session_stream_completed`：流传输完成
  - `error`：错误信息

---

## API 文档

### REST API

#### 初始化仿真会话

```http
POST /api/simulation/initialize
Content-Type: application/json

{
  "map_path": "/path/to/map.osm",
  "dataset_path": "/path/to/dataset",
  "dataset": "highD",
  "file_id": "01",
  "frame_step": 1,
  "stamp_start": null,
  "stamp_end": null,
  "max_duration_ms": null
}
```

**响应**：

```json
{
  "success": true,
  "message": "Simulation session initialized successfully.",
  "session_id": "sid_abc12345",
  "map_data": { ... },
  "config": { ... }
}
```

#### 获取会话信息

```http
GET /api/simulation/session/{session_id}
```

#### 健康检查

```http
GET /api/status
```

### WebSocket API

#### 连接

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/simulation");
```

#### 启动流传输

```json
{
  "type": "start_session_stream",
  "session_id": "sid_abc12345",
  "fps": 25
}
```

#### 接收帧数据

```json
{
  "type": "simulation_frame",
  "session_id": "sid_abc12345",
  "frame_number": 0,
  "data": {
    "timestamp": 0,
    "vehicles": [
      {
        "id": 1,
        "x": 100.5,
        "y": 2.3,
        "vx": 15.2,
        "vy": 0.1,
        "heading": 0.5
      }
    ]
  }
}
```

---

## 常见问题

### 后端问题

**Q: 地图/数据集路径找不到？**  
A: 请确保：

- 路径填写为服务器本地**绝对路径**
- 文件权限正确（`chmod 644` 或 `755`）
- 路径中不包含 `~` 符号（使用完整路径）

**Q: Tactics2D 库导入失败？**  
A:

- 检查 `tactics2d` 是否已正确安装：`pip list | grep tactics2d`
- 查看后端启动日志中的错误信息
- 参考 [Tactics2D 安装文档](https://github.com/your-org/tactics2d)

**Q: WebSocket 连接失败？**  
A: 检查：

- 后端服务是否正常启动（访问 `http://localhost:8000/api/status`）
- 端口 8000 是否被占用：`lsof -i :8000`（Linux/macOS）
- 防火墙是否阻止了 WebSocket 连接
- 浏览器控制台是否有 CORS 错误

**Q: 解析数据集时内存占用过高？**  
A:

- 减小 `frame_step` 值（增加采样间隔）
- 使用 `stamp_start` 和 `stamp_end` 限制时间范围
- 设置 `max_duration_ms` 限制最大时长

### 前端问题

**Q: 地图或车辆显示比例不对？**  
A:

- 检查地图坐标系和车辆坐标系的映射关系
- 查看 `backend/app/utils/simple_formatter.py` 中的坐标转换逻辑
- 查看 `frontend/tactics-app/app/dashboard/components/visualization.tsx` 中的渲染逻辑
- 可能需要调整车辆尺寸或地图缩放参数

**Q: 车辆与道路出现固定偏移（offset）？**  
A: 当前版本可能存在地图（OSM）与 highD 轨迹（米制）原点不一致的问题。为保证画面稳定，前端会在**首次收到车辆数据**时计算一次偏移量并将其应用到车辆坐标上（使车辆“贴回”道路）。这属于临时策略，长期应在后端统一坐标系并输出一致的局部坐标。

**Q: Three.js 场景不显示？**  
A:

- 检查浏览器控制台是否有 WebGL 错误
- 确认浏览器支持 WebGL 2.0
- 检查 WebSocket 是否正常连接并接收数据
- 查看网络面板确认地图数据是否加载成功

**Q: 主题切换不生效？**  
A:

- 检查 `next-themes` 是否正确配置
- 查看浏览器控制台是否有相关错误
- 清除浏览器缓存后重试

---

## 进阶功能（开发计划）

### 短期计划

- [ ] 支持进度条拖动和帧跳转
- [ ] 支持导出当前帧为 PNG 图片
- [ ] 支持参与者筛选（按 ID、类型等）
- [ ] 优化大数据集的内存占用

### 中期计划（仅围绕 highD 可视化）

- [ ] 支持导出仿真视频（MP4）
- [ ] （可选）接入 `*_tracksMeta.csv` 的 `class` 字段，修复 Truck/Car 类型统计与渲染
- [ ] 支持自定义车辆模型和地图样式
- [ ] 添加性能监控和统计面板

### 长期计划

- [ ] 支持多会话并发管理
- [ ] 支持数据集的增量加载
- [ ] 支持轨迹预测和回放对比
- [ ] 支持云端部署和容器化

---

## 目录结构

```
tactics2d-web/
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 应用入口
│   │   ├── config.py                 # 配置管理
│   │   ├── state.py                  # 全局状态（会话存储）
│   │   ├── api/                      # API 路由
│   │   │   ├── __init__.py
│   │   │   └── websocket.py          # WebSocket 端点
│   │   ├── models/                   # 数据模型
│   │   │   ├── requests.py           # 请求模型（Pydantic）
│   │   │   └── responses.py          # 响应模型（Pydantic）
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── map_service.py        # 地图解析服务
│   │   │   ├── dataset_parser_service.py  # 轨迹解析服务
│   │   │   └── websocket_manager.py  # WebSocket 连接管理
│   │   └── utils/                    # 工具函数
│   │       ├── simple_formatter.py   # 数据格式化
│   │       ├── tactics2d_wrapper.py  # Tactics2D 封装
│   │       └── helpers.py            # 辅助函数
│   └── data/                         # 数据目录
│       ├── highD_map/                # OSM 地图文件
│       └── LevelX/                   # 轨迹数据集
│           └── highD/
│               └── data/
│   └── requirements.txt              # Python 依赖
│
├── frontend/                         # 前端应用
│   └── tactics-app/                  # Next.js 项目
│       ├── app/                      # App Router 目录
│       │   ├── layout.tsx            # 根布局
│       │   ├── page.tsx              # 主页（初始化表单）
│       │   ├── dashboard/            # 仪表盘页面
│       │   │   ├── page.tsx          # 仪表盘主页面
│       │   │   └── components/
│       │   │       └── visualization.tsx  # Three.js 可视化组件
│       │   └── globals.css           # 全局样式
│       ├── components/               # React 组件
│       │   ├── ui/                   # shadcn/ui 组件
│       │   ├── app-sidebar.tsx       # 侧边栏
│       │   ├── theme-provider.tsx    # 主题提供者
│       │   └── ...
│       ├── hooks/                    # React Hooks
│       │   ├── useWebSocket.ts       # WebSocket Hook
│       │   └── use-mobile.ts         # 移动端检测
│       ├── lib/                      # 工具库
│       │   └── utils.ts              # 通用工具函数
│       ├── public/                   # 静态资源
│       ├── package.json              # Node.js 依赖
│       ├── tsconfig.json             # TypeScript 配置
│       ├── tailwind.config.ts        # TailwindCSS 配置
│       └── next.config.ts            # Next.js 配置
│
└── README.md                         # 项目文档
```

---

## 开发指南

### 后端开发

#### 添加新的 API 端点

1. 在 `app/models/requests.py` 中定义请求模型
2. 在 `app/models/responses.py` 中定义响应模型
3. 在 `app/main.py` 中添加路由处理函数
4. 如需复杂业务逻辑，在 `app/services/` 中创建服务类

#### 添加新的数据集格式支持

1. 在 `app/services/dataset_parser_service.py` 中添加解析逻辑
2. 在 `app/config.py` 的 `SUPPORTED_DATASETS` 中添加新格式
3. 更新前端的数据集选择器

### 前端开发

#### 添加新的页面

1. 在 `app/` 目录下创建新的路由目录
2. 添加 `page.tsx` 文件
3. 如需共享组件，放在 `components/` 目录

#### 添加新的 UI 组件

使用 shadcn/ui CLI 添加组件：

```bash
npx shadcn@latest add [component-name]
```

或手动在 `components/ui/` 目录下创建。

### 调试技巧

- **后端日志**：查看终端输出的结构化日志，使用 `structlog` 的 JSON 格式便于分析
- **前端调试**：使用 React DevTools 和浏览器开发者工具
- **WebSocket 调试**：在浏览器 Network 面板查看 WebSocket 消息
- **Three.js 调试**：使用 `@react-three/drei` 的 `Stats` 组件显示性能指标

---

## 性能优化建议

### 后端优化

- 使用 `orjson` 替代标准库 `json`（已集成）
- 对于大数据集，考虑使用数据库存储会话数据而非内存
- 实现数据缓存机制，避免重复解析
- 使用异步 I/O 处理文件读取

### 前端优化

- 使用 Next.js 的 Image 组件优化图片加载
- 实现虚拟滚动（如果列表很长）
- 使用 React.memo 优化组件渲染
- 考虑使用 Web Workers 处理大量数据计算

---

## 安全注意事项

- ⚠️ **路径验证**：确保用户输入的文件路径经过验证，防止路径遍历攻击
- ⚠️ **CORS 配置**：生产环境应限制 CORS 允许的源
- ⚠️ **会话管理**：考虑添加会话过期机制，避免内存泄漏
- ⚠️ **文件大小限制**：限制上传或解析的文件大小
- ⚠️ **错误信息**：生产环境应隐藏详细的错误堆栈信息

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

---

## 许可证

[在此添加许可证信息]

---

## 联系与支持

- **项目主页**：https://github.com/your-org/tactics2d-web
- **问题反馈**：https://github.com/your-org/tactics2d-web/issues
- **文档**：https://github.com/your-org/tactics2d-web/wiki

如有问题或建议，请提交 Issue 或联系项目维护者。

---

## 致谢

- [Tactics2D](https://github.com/your-org/tactics2d) - 核心算法库
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [Next.js](https://nextjs.org/) - React 全栈框架
- [Three.js](https://threejs.org/) - 3D 图形库
- [shadcn/ui](https://ui.shadcn.com/) - 优秀的 UI 组件库

---

**最后更新**：2026 年

⚠️ 已知问题：当前版本在解析 `backend/data/LevelX/highD/data` 的 highD 数据时，**车辆类型（Truck/Car）可能无法从 tactics2d Participant 直接获得**，导致统计/渲染可能全部显示为 Car。后续计划通过直接读取 `*_tracksMeta.csv` 的 `class` 字段做 id→ 类型映射来修复。

⚠️ 已知问题：地图与轨迹坐标系对齐目前仍是“经验型”方案（前端对车辆应用一次性 offset）。如果你希望**严格物理对齐**（每个 file_id 都正确对齐、没有人为平移），需要在后端实现稳定的坐标投影/原点定义，并把该原点同时应用到 OSM 与轨迹数据上。
