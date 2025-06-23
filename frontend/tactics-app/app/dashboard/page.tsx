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
  const { isConnected, startStream } = useWebSocket(
    "ws://localhost:8000/ws/simulation"
  );

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

  const handlePlayPause = () => {
    if (simulationStatus === "running") {
      setSimulationStatus("paused");
    } else {
      setSimulationStatus("running");
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

        <div className="flex flex-1 flex-col gap-6 p-6">
          {/* 可视化区域 - 现在占用更多空间 */}
          <Card className="flex-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                轨迹可视化
              </CardTitle>
              <CardDescription>Three.js轨迹可视化将在这里显示</CardDescription>
            </CardHeader>
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
