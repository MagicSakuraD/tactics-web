"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";

import { toast } from "sonner";
import { useWebSocket } from "@/hooks/useWebSocket";
import { AppSidebar } from "@/components/app-sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Card, CardContent } from "@/components/ui/card";
import Visualization from "./components/visualization";

export default function DashboardPage() {
  const [simulationStatus, setSimulationStatus] = useState<
    "idle" | "running" | "paused" | "stopped"
  >("idle");
  const [currentFrame, setCurrentFrame] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [participantCount, setParticipantCount] = useState(0);
  const [mapData, setMapData] = useState(null);

  // 从URL查询参数中获取会话信息
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");

  // 使用简化后的WebSocket hook
  const { isConnected, frameData, startSessionStream } = useWebSocket(
    "ws://localhost:8000/ws/simulation"
  );

  // 效果1: 通过 HTTP API 获取会话数据（包括地图数据和会话信息）
  useEffect(() => {
    if (!sessionId) {
      toast.error("❌ 缺少会话ID，请返回主页重新配置");
      return;
    }

    // 发送 HTTP GET 请求获取会话数据
    const fetchSessionData = async () => {
      try {
        toast.info("🔄 正在获取会话数据...");

        const response = await fetch(
          `http://localhost:8000/api/simulation/session/${sessionId}`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const sessionData = await response.json();

        // 设置地图数据
        if (sessionData.map_data) {
          setMapData(sessionData.map_data);
          toast.success("🗺️ 地图数据加载成功");
        }

        // 设置轨迹元数据
        if (sessionData.trajectory_metadata) {
          setTotalFrames(sessionData.trajectory_metadata.total_frames || 0);
          toast.success(
            `� 轨迹元数据加载成功 (${sessionData.trajectory_metadata.total_frames} 帧)`
          );
        }

        console.log("会话数据加载完成:", sessionData);
      } catch (error) {
        console.error("获取会话数据失败:", error);
        const errorMessage =
          error instanceof Error ? error.message : "未知错误";
        toast.error(`❌ 获取会话数据失败: ${errorMessage}`);

        // 回退到 localStorage（作为后备方案）
        const storedMapData = localStorage.getItem(`map_data_${sessionId}`);
        if (storedMapData) {
          try {
            const parsedMapData = JSON.parse(storedMapData);
            setMapData(parsedMapData);
            toast.warning("🗺️ 使用缓存的地图数据");
          } catch (parseError) {
            console.error("解析缓存数据失败:", parseError);
            toast.error("❌ 缓存数据也已损坏，请重新配置");
          }
        }
      }
    };

    fetchSessionData();
  }, [sessionId]);

  // 效果2: 监听WebSocket帧数据更新
  useEffect(() => {
    if (frameData) {
      setCurrentFrame(frameData.frame_number || 0);
      setParticipantCount(frameData.vehicles?.length || 0);
    }
  }, [frameData]);

  const handlePlayPause = () => {
    if (!sessionId) {
      toast.error("错误：缺少会话ID，无法开始播放");
      return;
    }

    if (simulationStatus === "idle" || simulationStatus === "stopped") {
      toast.info("▶️ 开始播放...");
      startSessionStream(sessionId, 10); // 以25 FPS开始流
      setSimulationStatus("running");
    } else if (simulationStatus === "running") {
      // 注意：当前的WebSocket实现不支持暂停/继续
      // 这里只是一个UI状态切换的例子
      toast("⏸️ 暂停（前端UI状态，流仍在继续）");
      setSimulationStatus("paused");
    } else if (simulationStatus === "paused") {
      toast.info("▶️ 恢复（前端UI状态）");
      setSimulationStatus("running");
    }
  };

  const handleStop = () => {
    toast.error("⏹️ 停止播放");
    setSimulationStatus("stopped");
    // 注意：这不会停止后端的流，只是重置前端状态
    setCurrentFrame(0);
  };

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "350px",
        } as React.CSSProperties
      }
    >
      <AppSidebar
        simulationStatus={simulationStatus}
        currentFrame={currentFrame}
        totalFrames={totalFrames} // totalFrames可以从session_stream_started消息中获取
        participantCount={participantCount}
        onPlayPause={handlePlayPause}
        onStop={handleStop}
        isConnected={isConnected}
        onStartStream={() => {
          if (sessionId) {
            toast.info("▶️ 开始播放...");
            startSessionStream(sessionId, 25);
            setSimulationStatus("running");
          } else {
            toast.error("错误：缺少会话ID，无法开始播放");
          }
        }}
      />
      <SidebarInset>
        <header className="bg-background sticky top-0 flex shrink-0 items-center gap-2 border-b p-4">
          <SidebarTrigger className="-ml-1" />
          <Separator
            orientation="vertical"
            className="mr-2 data-[orientation=vertical]:h-4"
          />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem className="hidden md:block">
                <BreadcrumbLink href="/">Tactics2D</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>轨迹可视化控制台</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </header>

        <div className="flex flex-1 flex-col gap-3 p-3">
          <Card className="flex-1">
            <CardContent className="p-0">
              <div className="h-[700px] rounded-lg overflow-hidden">
                {mapData ? (
                  <Visualization mapData={mapData} frameData={frameData} />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-muted">
                    <p className="text-muted-foreground">正在加载地图数据...</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
