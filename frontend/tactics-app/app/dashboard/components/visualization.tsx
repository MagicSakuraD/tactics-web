"use client";

import React, { useEffect, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { map } from "zod";

// 定义车辆数据类型
interface VehicleData {
  id: number;
  position: { x: number; y: number; z: number };
  rotation: { x: number; y: number; z: number };
  velocity: { x: number; y: number; z: number };
  dimensions: { x: number; y: number; z: number };
  color: string;
  type: string;
}

// 单个车辆的组件
const Vehicle = ({ data }: { data: VehicleData }) => {
  const ref = useRef<THREE.Mesh>(null!);

  // 直接使用来自后端的数据更新位置和旋转
  // Three.js/React Three Fiber 会处理渲染优化
  return (
    <mesh
      ref={ref}
      position={[data.position.x, data.position.y, data.position.z]}
      // 假设后端提供了四元数或欧拉角用于旋转
      // rotation={[data.rotation.x, data.rotation.y, data.rotation.z]}
    >
      <boxGeometry
        args={[data.dimensions.y, data.dimensions.x, data.dimensions.z]}
      />
      <meshStandardMaterial color={data.color} />
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
const Visualization = () => {
  const {
    connect,
    disconnect,
    isConnected,
    frameData,
    mapData,
    requestMapHttp, // HTTP地图请求
    startStream,
  } = useWebSocket("ws://localhost:8000/ws/simulation");

  console.log(mapData, "mapData");

  useEffect(() => {
    // 组件加载时连接WebSocket，卸载时断开
    connect();
    toast.info("WebSocket connecting...");

    return () => {
      disconnect();
      toast.info("WebSocket disconnected.");
    };
  }, [connect, disconnect]);

  useEffect(() => {
    if (isConnected) {
      toast.success("WebSocket connected successfully.");
    }
  }, [isConnected]);

  // 自动加载地图数据
  useEffect(() => {
    const loadMapData = async () => {
      toast.info("Auto-loading map data...");
      await requestMapHttp();
    };

    loadMapData();
  }, []); // 只在组件挂载时执行一次

  const handleRequestMapHttp = async () => {
    toast.info("Requesting map data via HTTP...");
    await requestMapHttp();
  };

  const handleStartStream = () => {
    toast.info("Starting data stream...");
    startStream();
  };

  return (
    <div className="relative w-full h-full">
      {/* 移除了控制按钮和相机控制，使用默认鸟瞰视角 */}

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
        <gridHelper args={[500, 100, "#444", "#888"]} />

        <Map mapData={mapData} />

        {frameData &&
          frameData.vehicles.map((vehicle) => (
            <Vehicle key={vehicle.id} data={vehicle} />
          ))}
      </Canvas>
    </div>
  );
};

export default Visualization;
