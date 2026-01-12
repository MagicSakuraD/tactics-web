"use client";

import React, { useRef, useMemo } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import {
  OrbitControls,
  Line,
  GizmoHelper,
  GizmoViewport,
} from "@react-three/drei";
import * as THREE from "three";

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

    // Three.js坐标系：x=宽度，y=高度，z=深度（长度）
    // 注意：Three.js的boxGeometry参数是 [width, height, depth]
    // 对应车辆：width=宽度（横向），height=高度（垂直），depth=长度（沿道路方向）
    const dimensions: [number, number, number] = [
      vehicleWidth, // x轴：宽度
      vehicleHeight, // y轴：高度
      vehicleLength, // z轴：长度（沿道路方向）
    ];

    // 🎨 根据车辆类型和速度计算颜色
    const speed = Math.sqrt(data.vx ** 2 + data.vy ** 2);
    let color: string;

    if (data.type === "Truck") {
      // 卡车：灰色系，根据速度调整亮度
      color = speed > 15 ? "#666666" : speed > 8 ? "#888888" : "#aaaaaa";
    } else {
      // 轿车：彩色系，根据速度变化
      color = speed > 15 ? "#ff4444" : speed > 8 ? "#ffaa44" : "#44aa44";
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

    // 添加一些边距
    const padding = 50;
    return {
      minX: minX - padding,
      maxX: maxX + padding,
      minZ: minZ - padding,
      maxZ: maxZ + padding,
    };
  }, [mapData]);

  if (!mapData || !mapData.roads) return null;

  return (
    <group>
      {/* 渲染路面 - 深灰色柏油路面 */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[
          (mapBounds.minX + mapBounds.maxX) / 2,
          -0.05, // 稍微低于车道线，防止Z-fighting
          (mapBounds.minZ + mapBounds.maxZ) / 2,
        ]}
        receiveShadow
      >
        <planeGeometry
          args={[
            mapBounds.maxX - mapBounds.minX,
            mapBounds.maxZ - mapBounds.minZ,
          ]}
        />
        <meshStandardMaterial
          color="#2c2c2c" // 柏油路颜色：深灰
          roughness={0.8}
        />
      </mesh>

      {/* 渲染道路中心线 */}
      {mapData.roads.map((road: MapDataRoad) => (
        <Line
          key={road.properties.id}
          points={road.coordinates.map(
            (c: [number, number, number]) => new THREE.Vector3(c[0], 0.05, c[2]) // 增加Y坐标间距，避免Z-fighting
          )}
          color={road.properties.color || "#ffffff"}
          lineWidth={2}
        />
      ))}

      {/* 渲染车道线 - 白色/黄色标线 */}
      {mapData.lanes &&
        mapData.lanes.map((lane: MapDataLane) => (
          <Line
            key={lane.properties.id}
            points={lane.coordinates.map(
              (c: [number, number, number]) =>
                new THREE.Vector3(c[0], 0.06, c[2]) // 增加Y坐标间距，避免Z-fighting
            )}
            color={
              lane.properties.color === "white"
                ? "#ffffff"
                : lane.properties.color || "#ffcc00"
            }
            lineWidth={lane.properties.dashed ? 1.5 : 2}
          />
        ))}

      {/* 渲染边界 - 路沿 */}
      {mapData.boundaries &&
        mapData.boundaries.map((boundary: MapDataBoundary) => (
          <Line
            key={boundary.properties.id}
            points={boundary.coordinates.map(
              (c: [number, number, number]) =>
                new THREE.Vector3(c[0], 0.07, c[2]) // 增加Y坐标间距，避免Z-fighting
            )}
            color={boundary.properties.color || "#888888"}
            lineWidth={2}
          />
        ))}
    </group>
  );
};

// 环境组件 - 地面和网格（根据场景大小自适应）
const Environment = ({ sceneSize }: { sceneSize: number }) => {
  // 根据场景大小动态调整地面和网格大小
  // sceneSize 是场景的最大尺寸（maxX - minX 或 maxZ - minZ 的最大值）
  const groundSize = Math.max(sceneSize * 2, 2000); // 至少是场景的2倍，最小2000
  const gridSize = Math.max(sceneSize * 1.5, 1000); // 网格至少是场景的1.5倍，最小1000
  const gridDivisions = Math.max(Math.floor(gridSize / 100), 10); // 网格分割数，每100单位一条线

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
}: {
  mapBounds: { minX: number; maxX: number; minZ: number; maxZ: number };
}) => {
  const { camera } = useThree();

  React.useEffect(() => {
    // 计算场景中心点和尺寸
    const centerX = (mapBounds.minX + mapBounds.maxX) / 2;
    const centerZ = (mapBounds.minZ + mapBounds.maxZ) / 2;
    const sceneWidth = mapBounds.maxX - mapBounds.minX;
    const sceneDepth = mapBounds.maxZ - mapBounds.minZ;
    const sceneSize = Math.max(sceneWidth, sceneDepth);

    // 根据场景大小自适应相机位置
    // 相机距离场景中心的距离应该是场景大小的 1.5-2 倍
    const cameraDistance = Math.max(sceneSize * 1.5, 200);
    const cameraHeight = Math.max(sceneSize * 0.8, 150);
    const cameraOffset = Math.max(sceneSize * 0.3, 50);

    camera.position.set(
      centerX + cameraOffset,
      cameraHeight,
      centerZ + cameraDistance
    );
    camera.lookAt(centerX, 0, centerZ);
    camera.updateProjectionMatrix();
  }, [camera, mapBounds]);

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
  // 计算地图边界（用于相机自适应）
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

  // 计算场景大小（用于环境组件）
  const sceneSize = useMemo(() => {
    const width = mapBounds.maxX - mapBounds.minX;
    const depth = mapBounds.maxZ - mapBounds.minZ;
    return Math.max(width, depth);
  }, [mapBounds]);

  // 缓存车辆列表，避免不必要的重新渲染
  const vehicles = useMemo(() => {
    return frameData?.vehicles || [];
  }, [frameData?.vehicles]);

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
        shadows // 开启阴影支持
        camera={{ position: [200, 150, 50], fov: 45 }}
        style={{ width: "100%", height: "100%", background: "#0a0a0a" }} // 背景色：极深灰，减少眼睛疲劳
      >
        {/* 自适应相机位置 */}
        <AdaptiveCamera mapBounds={mapBounds} />
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
          enableDamping={true}
          dampingFactor={0.05}
          screenSpacePanning={false}
          maxPolarAngle={Math.PI / 2}
        />
        {/* 添加环境（地面和网格，根据场景大小自适应） */}
        <Environment sceneSize={sceneSize} />
        <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
          <GizmoViewport
            axisColors={["red", "green", "blue"]}
            labelColor="black"
          />
        </GizmoHelper>
        {/* 渲染地图（包含路面和标线） */}
        <Map mapData={mapData} />
        {/* 渲染车辆（使用缓存的车辆列表） */}
        {vehicles.map((vehicle: VehicleData) => (
          <Vehicle key={vehicle.id} data={vehicle} />
        ))}
      </Canvas>
    </div>
  );
};

export default Visualization;
