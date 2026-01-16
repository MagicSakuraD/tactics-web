"use client";

import React, { useLayoutEffect, useMemo, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, GizmoHelper, GizmoViewport } from "@react-three/drei";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

// === Box segment lines (InstancedMesh) ===
type Coord3 = [number, number, number];

function polylineToSegments(coords: Coord3[]) {
  const segments: Array<{ mid: THREE.Vector3; angle: number; len: number }> =
    [];
  for (let i = 0; i < coords.length - 1; i++) {
    const ax = coords[i][0];
    const az = coords[i][2];
    const bx = coords[i + 1][0];
    const bz = coords[i + 1][2];
    const dx = bx - ax;
    const dz = bz - az;
    const len = Math.sqrt(dx * dx + dz * dz);
    if (!Number.isFinite(len) || len < 1e-3) continue;
    const mid = new THREE.Vector3((ax + bx) / 2, 0, (az + bz) / 2);
    const angle = Math.atan2(dx, dz); // rotate around Y so that local +Z aligns with segment
    segments.push({ mid, angle, len });
  }
  return segments;
}

const SEG_TMP_OBJ = new THREE.Object3D();

const BoxSegments = ({
  polylines,
  width,
  height,
  y,
  color,
}: {
  polylines: Coord3[][];
  width: number;
  height: number;
  y: number;
  color: string;
}) => {
  const segments = useMemo(() => {
    const all: Array<{ mid: THREE.Vector3; angle: number; len: number }> = [];
    for (const line of polylines) all.push(...polylineToSegments(line));
    return all;
  }, [polylines]);

  const geometry = useMemo(
    () => new THREE.BoxGeometry(width, height, 1),
    [width, height]
  );
  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color,
        // ✅ 让车辆正确遮挡车道线/边界线/道路线
        // 之前 depthTest=false 会导致这些线永远画在最上层，看起来“压在车上”
        depthTest: true,
        depthWrite: false,
      }),
    [color]
  );

  const meshRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    for (let i = 0; i < segments.length; i++) {
      const s = segments[i];
      SEG_TMP_OBJ.position.set(s.mid.x, y, s.mid.z);
      SEG_TMP_OBJ.rotation.set(0, s.angle, 0);
      SEG_TMP_OBJ.scale.set(1, 1, s.len);
      SEG_TMP_OBJ.updateMatrix();
      mesh.setMatrixAt(i, SEG_TMP_OBJ.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
    // 提升剔除/阴影稳定性
    mesh.frustumCulled = false;
  }, [segments, y]);

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, Math.max(segments.length, 1)]}
      renderOrder={20}
      frustumCulled={false}
    />
  );
};

// 定义车辆数据类型（基于后端实际数据格式）
interface VehicleData {
  id: number;
  x: number; // X坐标（沿道路方向）
  y: number; // Y坐标（横向方向）
  vx: number; // X方向速度
  vy: number; // Y方向速度
  heading: number; // 车辆朝向（弧度）
  length?: number; // 车辆长度（米）
  width?: number; // 车辆宽度（米）
  type?: string; // 车辆类型（Car/Truck等）
}

// 单个车辆的组件（使用 React.memo 优化性能）
const Vehicle = React.memo(
  ({ data }: { data: VehicleData }) => {
    const ref = useRef<THREE.Mesh>(null!);

    // 🚗 车辆尺寸：使用实际数据，如果没有则使用默认值
    const vehicleLength = data.length || 4.5; // 长度（沿道路方向）
    const vehicleWidth = data.width || 2.0; // 宽度（横向）
    const vehicleHeight = data.type === "Truck" ? 3.5 : 1.8; // 高度（卡车更高）

    // 🔧 坐标系转换：2D车辆数据 -> 3D Three.js坐标
    // 车辆数据: (x, y) 在2D平面上，x是沿道路方向，y是横向
    // Three.js: x-右, y-上, z-深度（右手坐标系）
    // 转换: 车辆x -> Three.js x, 车辆y -> Three.js z, 高度 -> Three.js y
    // ⚠️ 车辆高度：使用实际车辆高度的一半，让车辆"站"在地面上
    const position: [number, number, number] = [
      data.x, // X坐标（沿道路方向）
      vehicleHeight / 2, // Y坐标（车辆高度的一半，让车辆"站"在地面上）
      data.y, // Z坐标（横向方向，与地图坐标系一致）
    ];

    // 🧭 旋转调整：heading角度绕y轴（垂直轴）旋转
    const rotation: [number, number, number] = [
      0, // 不绕X轴旋转
      data.heading, // 绕Y轴旋转（车辆朝向）
      0, // 不绕Z轴旋转
    ];

    // ✅ 我们的场景约定：
    // - X 轴：沿道路方向（longitudinal）
    // - Z 轴：横向（lateral）
    // 因此车辆“长度”应当沿 X 轴，车辆“宽度”沿 Z 轴。
    const dimensions: [number, number, number] = [
      vehicleLength, // x轴：长度（沿道路方向）
      vehicleHeight, // y轴：高度
      vehicleWidth, // z轴：宽度（横向）
    ];

    // 🎨 根据车辆类型和速度计算颜色
    const speed = Math.sqrt(data.vx ** 2 + data.vy ** 2);
    let color: string;

    if (data.type === "Truck") {
      // Truck：蓝色系（与 Car 明显区分），根据速度调整亮度
      color = speed > 15 ? "#2563eb" : speed > 8 ? "#3b82f6" : "#93c5fd";
    } else {
      // Car：红/橙/绿系，根据速度变化
      color = speed > 15 ? "#ef4444" : speed > 8 ? "#f97316" : "#22c55e";
    }

    return (
      <mesh
        ref={ref}
        position={position}
        rotation={rotation}
        castShadow
        receiveShadow
      >
        <boxGeometry args={dimensions} />
        <meshStandardMaterial color={color} roughness={0.4} metalness={0.1} />
      </mesh>
    );
  },
  (prevProps, nextProps) => {
    // 自定义比较函数：只有当车辆的关键属性变化时才重新渲染
    return (
      prevProps.data.id === nextProps.data.id &&
      prevProps.data.x === nextProps.data.x &&
      prevProps.data.y === nextProps.data.y &&
      prevProps.data.heading === nextProps.data.heading &&
      prevProps.data.vx === nextProps.data.vx &&
      prevProps.data.vy === nextProps.data.vy &&
      prevProps.data.length === nextProps.data.length &&
      prevProps.data.width === nextProps.data.width &&
      prevProps.data.type === nextProps.data.type
    );
  }
);

Vehicle.displayName = "Vehicle";

// 地图数据类型
interface MapDataRoad {
  properties: {
    id: string;
    width: number;
    color: string;
  };
  coordinates: Array<[number, number, number]>;
}

interface MapDataLane {
  properties: {
    id: string;
    color?: string;
    dashed?: boolean;
  };
  coordinates: Array<[number, number, number]>;
}

interface MapDataBoundary {
  properties: {
    id: string;
    color?: string;
  };
  coordinates: Array<[number, number, number]>;
}

interface MapDataType {
  roads: MapDataRoad[];
  lanes?: MapDataLane[];
  boundaries?: MapDataBoundary[];
  metadata?: Record<string, unknown>;
}

// 地图组件
const Map = ({ mapData }: { mapData: MapDataType | null }) => {
  // 计算地图边界，用于生成路面（必须在 early return 之前调用 hook）
  const rawBounds = useMemo(() => {
    if (!mapData || !mapData.roads || mapData.roads.length === 0) {
      return { minX: -200, maxX: 200, minZ: -30, maxZ: 30 };
    }

    let minX = Infinity,
      maxX = -Infinity;
    let minZ = Infinity,
      maxZ = -Infinity;

    mapData.roads.forEach((road: MapDataRoad) => {
      road.coordinates.forEach((coord: [number, number, number]) => {
        minX = Math.min(minX, coord[0]);
        maxX = Math.max(maxX, coord[0]);
        minZ = Math.min(minZ, coord[2]);
        maxZ = Math.max(maxZ, coord[2]);
      });
    });

    return {
      minX,
      maxX,
      minZ,
      maxZ,
    };
  }, [mapData]);

  if (!mapData || !mapData.roads) return null;

  const planeWidth = rawBounds.maxX - rawBounds.minX;
  const planeDepth = rawBounds.maxZ - rawBounds.minZ;
  const planeCenterX = (rawBounds.minX + rawBounds.maxX) / 2;
  const planeCenterZ = (rawBounds.minZ + rawBounds.maxZ) / 2;

  return (
    <group>
      {/* 渲染路面：灰色沥青路面 */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[
          planeCenterX,
          -0.02, // 稍微低于车道线，防止Z-fighting
          planeCenterZ,
        ]}
        receiveShadow
      >
        <planeGeometry
          args={[Math.max(planeWidth, 1), Math.max(planeDepth, 1)]}
        />
        {/* ✅ 更明显的灰色路面，模拟沥青道路 */}
        <meshStandardMaterial color="#52525b" roughness={0.9} metalness={0} />
      </mesh>

      {/* 道路线：细长方块段（3D mesh） */}
      <BoxSegments
        polylines={mapData.roads.map((r) => r.coordinates)}
        width={0.12}
        height={0.03}
        y={0.05}
        color={"#a1a1aa"}
      />

      {/* 车道线：按颜色分两批 instancing（白/黄） */}
      <BoxSegments
        polylines={(mapData.lanes || [])
          .filter((l) => (l.properties.color || "yellow") === "white")
          .map((l) => l.coordinates)}
        width={0.18}
        height={0.03}
        y={0.06}
        color={"#ffffff"}
      />
      <BoxSegments
        polylines={(mapData.lanes || [])
          .filter((l) => (l.properties.color || "yellow") !== "white")
          .map((l) => l.coordinates)}
        width={0.18}
        height={0.03}
        y={0.06}
        color={"#facc15"}
      />

      {/* 边界线：细长方块段（更粗一点） */}
      <BoxSegments
        polylines={(mapData.boundaries || []).map((b) => b.coordinates)}
        width={0.25}
        height={0.04}
        y={0.07}
        color={"#9ca3af"}
      />
    </group>
  );
};

// 环境组件 - 地面和网格（根据场景大小自适应）
const Environment = ({ sceneSize }: { sceneSize: number }) => {
  // 根据场景大小动态调整地面和网格大小
  // sceneSize 是场景的最大尺寸（maxX - minX 或 maxZ - minZ 的最大值）
  // ⚠️ 重要：必须对网格分割数做上限，否则当坐标尺度很大（例如 OSM 误判导致百万级坐标）会直接把浏览器/GPU 撑爆
  const clamp = (v: number, min: number, max: number) =>
    Math.max(min, Math.min(max, v));

  const safeSceneSize = clamp(sceneSize, 0, 10000); // 环境只需要“视觉参考”，不需要无限大
  const groundSize = clamp(Math.max(safeSceneSize * 2, 2000), 2000, 20000);
  const gridSize = clamp(Math.max(safeSceneSize * 1.5, 1000), 1000, 15000);
  const gridDivisions = clamp(Math.floor(gridSize / 100), 10, 200); // 上限 200，避免性能灾难

  return (
    <group>
      {/* 无限延伸的地面，接收阴影 */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.1, 0]}
        receiveShadow
      >
        <planeGeometry args={[groundSize, groundSize]} />
        <meshStandardMaterial
          color="#151515" // 地面颜色：比背景稍亮一点的黑
          roughness={1}
        />
      </mesh>

      {/* 网格辅助线 - 帮助理解空间关系 */}
      <gridHelper
        args={[gridSize, gridDivisions, "#333", "#111"]}
        position={[0, 0.01, 0]}
      />
    </group>
  );
};

// 相机自适应组件
const AdaptiveCamera = ({
  mapBounds,
  controlsRef,
}: {
  mapBounds: { minX: number; maxX: number; minZ: number; maxZ: number };
  controlsRef: React.RefObject<OrbitControlsImpl | null>;
}) => {
  const { camera, size } = useThree();
  const initializedRef = useRef(false);

  // ✅ 使用 useEffect（不是 useLayoutEffect）：确保 OrbitControls 已挂载后再设置相机
  React.useEffect(() => {
    // 只初始化一次
    if (initializedRef.current) return;
    initializedRef.current = true;

    const sceneWidth = mapBounds.maxX - mapBounds.minX;
    const sceneDepth = mapBounds.maxZ - mapBounds.minZ;
    const sceneSize = Math.max(sceneWidth, sceneDepth);

    // 只显示道路长度的 ~1/3
    const desiredVisibleX = Math.max(sceneWidth / 3, 120);
    const desiredVisibleZ = Math.max(sceneDepth * 1.2, 60);
    const halfX = desiredVisibleX / 2;
    const halfZ = desiredVisibleZ / 2;

    const perspective = camera as unknown as THREE.PerspectiveCamera;
    const fovDeg = typeof perspective.fov === "number" ? perspective.fov : 45;
    const fovRad = (fovDeg * Math.PI) / 180;
    const aspect =
      size.width > 0 && size.height > 0 ? size.width / size.height : 1;
    const hFovRad = 2 * Math.atan(Math.tan(fovRad / 2) * aspect);

    const heightForZ = halfZ / Math.tan(fovRad / 2);
    const heightForX = halfX / Math.tan(hFovRad / 2);
    const cameraHeight = Math.max(heightForX, heightForZ, 200);

    // ✅ 俯视：相机在正上方，稍微偏移 Z 避免 up 向量奇异点
    // 使用默认 up 向量 [0, 1, 0]，这样 OrbitControls 行为正常
    camera.position.set(0, cameraHeight, 0.1);
    camera.up.set(0, 1, 0); // 使用默认 up 向量

    // 设置 OrbitControls 的 target
    if (controlsRef.current) {
      controlsRef.current.target.set(0, 0, 0);
      // 强制设置 OrbitControls 的极角为接近 0（俯视）
      controlsRef.current.minPolarAngle = 0.01; // 接近 0 但不是 0，避免奇异点
      controlsRef.current.maxPolarAngle = 0.01;
      controlsRef.current.update();
    }
    camera.lookAt(0, 0, 0);

    camera.near = 0.1;
    camera.far = Math.max(cameraHeight * 20, sceneSize * 20, 5000);
    camera.updateProjectionMatrix();
  }, [camera, mapBounds, controlsRef, size.height, size.width]);

  return null;
};

// 主可视化组件
const Visualization = ({
  mapData,
  frameData,
}: {
  mapData: MapDataType | null;
  frameData: { vehicles?: VehicleData[] } | null;
}) => {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const lockedFocusBoundsRef = useRef<{
    minX: number;
    maxX: number;
    minZ: number;
    maxZ: number;
  } | null>(null);
  // 计算地图边界
  const mapBounds = useMemo(() => {
    if (!mapData || !mapData.roads || mapData.roads.length === 0) {
      return { minX: -200, maxX: 200, minZ: -30, maxZ: 30 };
    }

    let minX = Infinity,
      maxX = -Infinity;
    let minZ = Infinity,
      maxZ = -Infinity;

    mapData.roads.forEach((road: MapDataRoad) => {
      road.coordinates.forEach((coord: [number, number, number]) => {
        minX = Math.min(minX, coord[0]);
        maxX = Math.max(maxX, coord[0]);
        minZ = Math.min(minZ, coord[2]);
        maxZ = Math.max(maxZ, coord[2]);
      });
    });

    const padding = 50;
    return {
      minX: minX - padding,
      maxX: maxX + padding,
      minZ: minZ - padding,
      maxZ: maxZ + padding,
    };
  }, [mapData]);

  // ✅ 大坐标场景的关键修复：把地图中心平移到 (0,0,0) 附近，避免浮点精度问题导致“看不到车/抖动/线条闪烁”
  // 缓存车辆列表，避免不必要的重新渲染
  const vehicles = useMemo(() => {
    return frameData?.vehicles || [];
  }, [frameData?.vehicles]);

  // 计算当前帧车辆边界（用于诊断“车不在地图附近/被相机错过”的情况）
  const vehicleBounds = useMemo(() => {
    if (!vehicles || vehicles.length === 0) return null;
    let minX = Infinity,
      maxX = -Infinity;
    let minZ = Infinity,
      maxZ = -Infinity;
    for (const v of vehicles) {
      minX = Math.min(minX, v.x);
      maxX = Math.max(maxX, v.x);
      minZ = Math.min(minZ, v.y); // VehicleData.y -> Three.js z
      maxZ = Math.max(maxZ, v.y);
    }
    return { minX, maxX, minZ, maxZ };
  }, [vehicles]);

  // 将“相机关注范围”锁定到：mapBounds 与首次出现车辆的 vehicleBounds 的并集
  // 这样可以保证：就算地图和车辆坐标系暂时不一致，也至少能把车拍进视野（便于继续排查对齐问题）
  const focusBounds = useMemo(() => {
    const vb = vehicleBounds;
    const base = { ...mapBounds };
    if (vb) {
      return {
        minX: Math.min(base.minX, vb.minX),
        maxX: Math.max(base.maxX, vb.maxX),
        minZ: Math.min(base.minZ, vb.minZ),
        maxZ: Math.max(base.maxZ, vb.maxZ),
      };
    }
    return base;
  }, [mapBounds, vehicleBounds]);

  if (!lockedFocusBoundsRef.current) {
    lockedFocusBoundsRef.current = focusBounds;
  } else if (vehicleBounds) {
    // 只有首次出现车辆时才扩展锁定范围，避免每帧抖动
    const cur = lockedFocusBoundsRef.current;
    lockedFocusBoundsRef.current = {
      minX: Math.min(cur.minX, focusBounds.minX),
      maxX: Math.max(cur.maxX, focusBounds.maxX),
      minZ: Math.min(cur.minZ, focusBounds.minZ),
      maxZ: Math.max(cur.maxZ, focusBounds.maxZ),
    };
  }

  // ✅ 道路位置固定：只用地图中心计算 sceneCenter
  const sceneCenter = useMemo(() => {
    return {
      x: (mapBounds.minX + mapBounds.maxX) / 2,
      z: (mapBounds.minZ + mapBounds.maxZ) / 2,
    };
  }, [mapBounds]);

  // ✅ 计算车辆偏移量：把车辆坐标平移到地图坐标系
  // 只在第一次拿到车辆数据时计算一次，之后锁定不变
  const vehicleOffsetRef = useRef<{ x: number; z: number } | null>(null);

  // 计算车辆中心
  const vehicleCenter = useMemo(() => {
    if (!vehicleBounds) return null;
    return {
      x: (vehicleBounds.minX + vehicleBounds.maxX) / 2,
      z: (vehicleBounds.minZ + vehicleBounds.maxZ) / 2,
    };
  }, [vehicleBounds]);

  // 第一次拿到车辆数据时计算偏移量并锁定
  if (!vehicleOffsetRef.current && vehicleCenter) {
    vehicleOffsetRef.current = {
      x: sceneCenter.x - vehicleCenter.x,
      z: sceneCenter.z - vehicleCenter.z,
    };
  }

  // ✅ 调整后的车辆数组：把偏移量加到每辆车的坐标上
  // 注意：直接在 useMemo 内部读取 ref，避免依赖问题
  const adjustedVehicles = useMemo(() => {
    const offset = vehicleOffsetRef.current;
    if (!offset || (offset.x === 0 && offset.z === 0)) {
      return vehicles;
    }
    return vehicles.map((v) => ({
      ...v,
      x: v.x + offset.x,
      y: v.y + offset.z, // VehicleData.y 对应 Three.js 的 z
    }));
  }, [vehicles]);

  // 计算场景大小（用于环境组件/阴影/相机距离）
  const lockedFocusBounds = lockedFocusBoundsRef.current ?? focusBounds;
  const sceneSize = useMemo(() => {
    const width = lockedFocusBounds.maxX - lockedFocusBounds.minX;
    const depth = lockedFocusBounds.maxZ - lockedFocusBounds.minZ;
    return Math.max(width, depth);
  }, [lockedFocusBounds]);

  // 环境（地面/网格）只跟地图尺寸走，避免坐标不一致时被 vehicleBounds 拉爆
  const mapSceneSize = useMemo(() => {
    const width = mapBounds.maxX - mapBounds.minX;
    const depth = mapBounds.maxZ - mapBounds.minZ;
    return Math.max(width, depth);
  }, [mapBounds]);

  // 计算阴影相机范围（根据场景大小自适应）
  const shadowCameraSize = useMemo(() => {
    const baseSize = Math.max(sceneSize * 0.6, 200);
    return {
      far: baseSize * 2,
      left: -baseSize,
      right: baseSize,
      top: baseSize,
      bottom: -baseSize,
    };
  }, [sceneSize]);

  return (
    <div className="relative w-full h-full">
      <Canvas
        shadows
        // ✅ 初始相机：俯视位置（Y 很高，Z 稍微偏移避免 up 向量奇异点）
        camera={{ position: [0, 500, 0.1], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, logarithmicDepthBuffer: true }}
        style={{ width: "100%", height: "100%", background: "#0a0a0a" }}
      >
        {/* 自适应相机位置 */}
        <AdaptiveCamera
          // ✅ 只用“地图范围”初始化相机：避免点击“运行”后由于车辆边界出现/扩展导致相机再次重置
          // （lockedFocusBounds 会在数据流开始时变化，从而触发 AdaptiveCamera 重算）
          mapBounds={mapBounds}
          controlsRef={controlsRef}
        />
        {/* 灯光系统优化 */}
        <ambientLight intensity={0.4} /> {/* 环境光调暗，制造对比度 */}
        <directionalLight
          position={[50, 100, 50]}
          intensity={1.5}
          castShadow // 主光源产生阴影
          shadow-mapSize={[2048, 2048]} // 阴影清晰度
          shadow-camera-far={shadowCameraSize.far}
          shadow-camera-left={shadowCameraSize.left}
          shadow-camera-right={shadowCameraSize.right}
          shadow-camera-top={shadowCameraSize.top}
          shadow-camera-bottom={shadowCameraSize.bottom}
        />
        <OrbitControls
          ref={controlsRef}
          enableDamping={true}
          dampingFactor={0.05}
          enableZoom={true}
          zoomSpeed={0.8}
          minDistance={20}
          maxDistance={5000}
          screenSpacePanning={false}
          // ✅ 俯视模式：极角锁定在接近 0（0.01 弧度 ≈ 0.6°），避免奇异点
          minPolarAngle={0.01}
          maxPolarAngle={0.01}
        />
        {/* 添加环境（地面和网格）— 仅使用地图尺寸，避免性能灾难 */}
        <Environment sceneSize={mapSceneSize} />
        <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
          <GizmoViewport
            axisColors={["red", "green", "blue"]}
            labelColor="black"
          />
        </GizmoHelper>
        {/* ✅ 将场景平移到原点附近，保证相机/OrbitControls 易用且渲染稳定 */}
        <group position={[-sceneCenter.x, 0, -sceneCenter.z]}>
          {/* 渲染地图 */}
          <Map mapData={mapData} />
          {/* 渲染车辆（已应用偏移量对齐到道路） */}
          {adjustedVehicles.map((vehicle: VehicleData) => (
            <Vehicle key={vehicle.id} data={vehicle} />
          ))}
        </group>
      </Canvas>
    </div>
  );
};

export default Visualization;
