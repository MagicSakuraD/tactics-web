"use client";

import { useState, useEffect } from "react";
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
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Car,
  Play,
  Pause,
  Square,
  BarChart3,
  Settings,
  MapPin,
} from "lucide-react";
import Visualization from "./components/visualization";

export default function DashboardPage() {
  const [simulationStatus, setSimulationStatus] = useState<
    "idle" | "running" | "paused" | "stopped"
  >("idle");
  const [currentFrame, setCurrentFrame] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [participantCount, setParticipantCount] = useState(0);

  // WebSocket hook for simulation control
  const { isConnected, startStream, startSessionStream, parseDataset } =
    useWebSocket("ws://localhost:8000/ws/simulation");

  // 当前会话状态
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<any>(null);

  useEffect(() => {
    // 检查后端状态
    checkSimulationStatus();
  }, []);

  const checkSimulationStatus = async () => {
    try {
      const response = await fetch(
        "http://localhost:8000/api/simulation/status"
      );
      if (response.ok) {
        const data = await response.json();
        toast.success("后端连接正常，数据已准备就绪");
        setParticipantCount(data.participant_count || 0);
        setTotalFrames(data.total_frames || 0);
      }
    } catch (error) {
      toast.error("后端连接失败，请检查FastAPI服务是否启动");
    }
  };

  const handlePlayPause = async () => {
    if (simulationStatus === "idle") {
      // 如果是空闲状态，首先解析数据集创建会话
      if (!currentSessionId) {
        try {
          toast.info("正在解析数据集...");

          // 解析数据集配置 - 这里使用硬编码，实际项目中应该来自表单
          const datasetConfig = {
            dataset: "highD",
            file_id: 1,
            dataset_path:
              "/home/quinn/APP/Code/tactics2d-web/backend/data/LevelX/highD/data",
            max_duration_ms: 5000, // 5秒数据
          };

          const session = await parseDataset(datasetConfig);
          setCurrentSessionId(session.session_id);
          setSessionData(session);
          setTotalFrames(session.total_frames);
          setParticipantCount(session.participant_count);

          toast.success(
            `数据集解析成功！共${session.participant_count}个参与者，${session.total_frames}帧数据`
          );

          // 开始会话数据流
          startSessionStream(session.session_id, 25);
          setSimulationStatus("running");
        } catch (error) {
          toast.error("数据集解析失败: " + error);
          return;
        }
      } else {
        // 如果已有会话，直接开始流
        startSessionStream(currentSessionId, 25);
        setSimulationStatus("running");
      }
    } else if (simulationStatus === "running") {
      // 如果正在运行，暂停
      setSimulationStatus("paused");
    } else if (simulationStatus === "paused") {
      // 如果已暂停，继续播放
      if (currentSessionId) {
        startSessionStream(currentSessionId, 25);
      }
      setSimulationStatus("running");
    } else if (simulationStatus === "stopped") {
      // 如果已停止，重新开始
      if (currentSessionId) {
        startSessionStream(currentSessionId, 25);
        setSimulationStatus("running");
      } else {
        // 没有会话，回到空闲状态
        setSimulationStatus("idle");
      }
    }
  };

  const handleStop = () => {
    setSimulationStatus("stopped");
    setCurrentFrame(0);
  };

  const handleStartStream = () => {
    toast.info("Starting data stream...");
    startStream();
    setSimulationStatus("running");
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
        totalFrames={totalFrames}
        participantCount={participantCount}
        onPlayPause={handlePlayPause}
        onStop={handleStop}
        isConnected={isConnected}
        onStartStream={handleStartStream}
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
          {/* 可视化区域 - 现在占用更多空间 */}
          <Card className="flex-1">
            <CardContent className="p-0">
              <div className="h-[700px] rounded-lg overflow-hidden">
                <Visualization />
              </div>
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
