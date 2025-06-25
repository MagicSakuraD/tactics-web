"use client";

import React, { useEffect, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";

// 定义车辆数据类型（基于后端实际数据格式）
interface VehicleData {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  heading: number;
}

// 单个车辆的组件
const Vehicle = ({ data }: { data: VehicleData }) => {
  const ref = useRef<THREE.Mesh>(null!);

  // 从后端的平面数据格式转换为Three.js所需的3D格式
  // 使用默认的车辆尺寸
  const position: [number, number, number] = [data.x || 0, data.y || 0, 0.5];
  const rotation: [number, number, number] = [0, 0, data.heading || 0];
  const dimensions: [number, number, number] = [4.5, 2.0, 1.8]; // 长x宽x高（米）
  
  // 根据速度计算颜色
  const speed = Math.sqrt((data.vx || 0) ** 2 + (data.vy || 0) ** 2);
  const color = speed > 15 ? "#ff4444" : speed > 8 ? "#ffaa44" : "#44aa44";

  return (
    <mesh
      ref={ref}
      position={position}
      rotation={rotation}
    >
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
        camera={{ position: [0, 100, 150], fov: 50 }}
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
        <gridHelper args={[100, 20, "#444", "#888"]} />

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
