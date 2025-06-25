"use client";

import React, { useEffect, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";

// 定义车辆数据类型（基于后端实际数据格式）
interface VehicleData {
  id: number;
  x: number; // X坐标（沿道路方向）
  y: number; // Y坐标（横向方向）
  vx: number; // X方向速度
  vy: number; // Y方向速度
  heading: number; // 车辆朝向（弧度）
}

// 单个车辆的组件
const Vehicle = ({ data }: { data: VehicleData }) => {
  const ref = useRef<THREE.Mesh>(null!);

  // 🔧 坐标系转换：2D车辆数据 -> 3D Three.js坐标
  // 车辆数据: (x, y) 在2D平面上，x是沿道路方向，y是横向
  // Three.js: x-右, y-上, z-深度（右手坐标系）
  // 转换: 车辆x -> Three.js x, 车辆y -> Three.js z, 高度 -> Three.js y
  const position: [number, number, number] = [
    data.x, // X坐标（沿道路方向）
    0.9, // Y坐标（车辆高度的一半，让车辆"站"在地面上）
    data.y, // Z坐标（横向方向，与地图坐标系一致）
  ];

  // 🧭 旋转调整：heading角度绕y轴（垂直轴）旋转
  const rotation: [number, number, number] = [
    0, // 不绕X轴旋转
    data.heading, // 绕Y轴旋转（车辆朝向）
    0, // 不绕Z轴旋转
  ];

  // 🚗 车辆尺寸：典型轿车尺寸（长x高x宽）米
  const dimensions: [number, number, number] = [4.5, 1.8, 2.0];

  // 🎨 根据速度计算颜色
  const speed = Math.sqrt(data.vx ** 2 + data.vy ** 2);
  const color = speed > 15 ? "#ff4444" : speed > 8 ? "#ffaa44" : "#44aa44";

  return (
    <mesh ref={ref} position={position} rotation={rotation}>
      <boxGeometry args={dimensions} />
      <meshStandardMaterial color={color} />
    </mesh>
  );
};

// 地图数据类型
interface MapDataRoad {
  properties: {
    id: string;
    width: number;
    color: string;
  };
  coordinates: Array<[number, number, number]>;
}

interface MapDataType {
  roads: MapDataRoad[];
  lanes?: any[];
  boundaries?: any[];
  metadata?: any;
}

// 地图组件
const Map = ({ mapData }: { mapData: MapDataType | null }) => {
  if (!mapData || !mapData.roads) return null;

  return (
    <group>
      {/* 渲染道路 */}
      {mapData.roads.map((road: MapDataRoad) => (
        <Line
          key={road.properties.id}
          points={road.coordinates.map(
            (c: [number, number, number]) => new THREE.Vector3(c[0], c[1], c[2])
          )}
          color={road.properties.color}
          lineWidth={2}
        />
      ))}

      {/* 渲染车道线 */}
      {mapData.lanes &&
        mapData.lanes.map((lane: any) => (
          <Line
            key={lane.properties.id}
            points={lane.coordinates.map(
              (c: [number, number, number]) =>
                new THREE.Vector3(c[0], c[1], c[2])
            )}
            color={lane.properties.color}
            lineWidth={lane.properties.dashed ? 1 : 2}
          />
        ))}

      {/* 渲染边界 */}
      {mapData.boundaries &&
        mapData.boundaries.map((boundary: any) => (
          <Line
            key={boundary.properties.id}
            points={boundary.coordinates.map(
              (c: [number, number, number]) =>
                new THREE.Vector3(c[0], c[1], c[2])
            )}
            color={boundary.properties.color}
            lineWidth={1}
          />
        ))}
    </group>
  );
};

// 主可视化组件
const Visualization = ({
  mapData,
  frameData,
}: {
  mapData: any;
  frameData: any;
}) => {
  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{ position: [200, 50, 50], fov: 50 }} // 调整摄像机位置到场景中心
        style={{ width: "100%", height: "100%", background: "#1a1a1a" }}
      >
        <ambientLight intensity={1.5} />
        <directionalLight position={[10, 20, 5]} intensity={1} />
        <OrbitControls
          enableDamping={true}
          dampingFactor={0.05}
          screenSpacePanning={false}
          maxPolarAngle={Math.PI / 2}
        />
        <gridHelper args={[800, 40, "#444", "#888"]} />{" "}
        {/* 增大网格以覆盖更大的范围 */}
        <Map mapData={mapData} />
        {frameData &&
          frameData.vehicles &&
          frameData.vehicles.map((vehicle: VehicleData) => (
            <Vehicle key={vehicle.id} data={vehicle} />
          ))}
      </Canvas>
    </div>
  );
};

export default Visualization;
