"use client";

import * as React from "react";
import Link from "next/link";
import {
  Car,
  Play,
  Square,
  BarChart3,
  Home,
  Monitor,
  ChevronRight,
} from "lucide-react";

import { NavUser } from "@/components/nav-user";
import { ModeToggle } from "@/components/mode-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

// Tactics2D 项目数据
const data = {
  user: {
    name: "Tactics2D User",
    email: "user@tactics2d.com",
    avatar: "/logo2.jpg",
  },
  navMain: [
    {
      title: "首页",
      url: "/",
      icon: Home,
      isActive: false,
    },
    {
      title: "控制台",
      url: "/dashboard",
      icon: Monitor,
      isActive: true,
    },
  ],
};

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  simulationStatus?: "idle" | "running" | "paused" | "stopped";
  currentFrame?: number;
  totalFrames?: number;
  participantCount?: number;
  // 兼容旧调用方：后端暂不支持暂停，AppSidebar 内不会再使用该回调
  onPlayPause?: () => void;
  onStop?: () => void;
  isConnected?: boolean;
  onStartStream?: () => void;
}

export function AppSidebar({
  simulationStatus = "idle",
  // 这些 props 可能仍会从父组件传入，但不应该透传到底层 Sidebar DOM
  currentFrame: _currentFrame, // eslint-disable-line @typescript-eslint/no-unused-vars
  totalFrames: _totalFrames, // eslint-disable-line @typescript-eslint/no-unused-vars
  onPlayPause: _onPlayPause, // eslint-disable-line @typescript-eslint/no-unused-vars
  participantCount = 0,
  onStop,
  isConnected = false,
  onStartStream,
  ...props
}: AppSidebarProps) {
  const [isControlPanelOpen, setIsControlPanelOpen] = React.useState(false);

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/">
                <div className="bg-blue-600 text-white flex aspect-square size-8 items-center justify-center rounded-lg">
                  <Car className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Tactics2D</span>
                  <span className="truncate text-xs">轨迹可视化</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* 导航菜单 */}
        <SidebarGroup>
          <SidebarGroupLabel>导航</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {data.navMain.map((item) => (
                <SidebarMenuItem key={item.title}>
                  {item.title === "控制台" ? (
                    <Collapsible
                      open={isControlPanelOpen}
                      onOpenChange={setIsControlPanelOpen}
                    >
                      <CollapsibleTrigger asChild>
                        <SidebarMenuButton
                          isActive={item.isActive}
                          tooltip={item.title}
                          className="w-full"
                        >
                          <item.icon />
                          <span>{item.title}</span>
                          <ChevronRight
                            className={`ml-auto h-4 w-4 transition-transform duration-200 ${
                              isControlPanelOpen ? "rotate-90" : ""
                            }`}
                          />
                        </SidebarMenuButton>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="space-y-2">
                        {/* 仿真控制面板 */}
                        <div className="ml-6 mt-2 space-y-4">
                          <Card className="border shadow-sm">
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm flex items-center gap-2">
                                <Car className="h-4 w-4 text-blue-600" />
                                播放控制
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                              {/* 智能播放控制按钮 */}
                              <div className="flex space-x-2">
                                <Button
                                  onClick={() => {
                                    // ✅ 后端暂不支持暂停/继续：只允许在 idle/stopped 时启动流
                                    if (
                                      simulationStatus === "idle" ||
                                      simulationStatus === "stopped"
                                    ) {
                                      onStartStream?.();
                                    }
                                  }}
                                  disabled={!isConnected}
                                  variant={
                                    simulationStatus === "running"
                                      ? "default"
                                      : "outline"
                                  }
                                  size="sm"
                                  className="flex-1"
                                >
                                  {simulationStatus === "idle" ||
                                  simulationStatus === "stopped" ? (
                                    <>
                                      <Play className="h-3 w-3 mr-1" />
                                      开始
                                    </>
                                  ) : (
                                    <>
                                      <Play className="h-3 w-3 mr-1" />
                                      运行中
                                    </>
                                  )}
                                </Button>
                                <Button
                                  onClick={onStop}
                                  variant="outline"
                                  size="sm"
                                  disabled={
                                    simulationStatus === "idle" ||
                                    simulationStatus === "stopped"
                                  }
                                >
                                  <Square className="h-3 w-3" />
                                </Button>
                              </div>
                              <div className="text-xs text-muted-foreground text-center">
                                {simulationStatus === "running"
                                  ? "运行中"
                                  : "待机"}
                              </div>
                            </CardContent>
                          </Card>

                          {/* 数据统计 */}
                          <div className="space-y-2">
                            <Card className="border shadow-sm">
                              <CardContent className="p-3">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <BarChart3 className="h-4 w-4 text-green-600" />
                                    <span className="text-sm">参与者</span>
                                  </div>
                                  <span className="text-lg font-bold">
                                    {participantCount}
                                  </span>
                                </div>
                              </CardContent>
                            </Card>

                            {/* <Card className="border shadow-sm">
                              <CardContent className="p-3">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center space-x-2">
                                    <MapPin className="h-4 w-4 text-purple-600" />
                                    <span className="text-sm">当前帧</span>
                                  </div>
                                  <span className="text-lg font-bold">
                                    {currentFrame}
                                  </span>
                                </div>
                                <div className="mt-2 text-xs text-muted-foreground">
                                  总帧数: {totalFrames}
                                </div>
                                <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                                  <div
                                    className="bg-purple-600 h-1.5 rounded-full transition-all duration-300"
                                    style={{
                                      width: `${
                                        totalFrames > 0
                                          ? (currentFrame / totalFrames) * 100
                                          : 0
                                      }%`,
                                    }}
                                  ></div>
                                </div>
                              </CardContent>
                            </Card> */}
                          </div>
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ) : (
                    <SidebarMenuButton
                      asChild
                      isActive={item.isActive}
                      tooltip={item.title}
                    >
                      <Link href={item.url}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* 主题切换 */}
        <SidebarGroup>
          <SidebarGroupLabel>系统</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton tooltip="主题切换">
                  {/* <Settings />
                  <span>设置</span> */}
                  <div className="flex items-center justify-between pl-0">
                    <ModeToggle />
                    <span className="text-sm pl-2">主题切换</span>
                  </div>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  );
}
