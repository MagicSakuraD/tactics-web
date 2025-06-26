// 🔌 WebSocket Hook - React Three Fiber 数据通信
import { useEffect, useRef, useState, useCallback } from "react";
import { toast } from "sonner";

interface WebSocketMessage {
  type: string;
  session_id?: string;
  data?: any;
  timestamp?: number;
  status?: string;
  message?: string;
  // 新增可能存在的字段以解决类型错误
  client_id?: string;
  total_frames?: number;
  fps?: number;
  frame_number?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  frameData: any | null; // 简化为any，因为数据结构在后端已确定
  mapData: any | null; // 简化为any
  sendMessage: (message: any) => void;
  startSessionStream: (sessionId: string, fps?: number) => void;
}

export const useWebSocket = (
  url: string = "ws://localhost:8000/ws/simulation"
): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [frameData, setFrameData] = useState<any | null>(null);
  const [mapData, setMapData] = useState<any | null>(null); // 地图数据不再通过WS获取
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log("WebSocket already connected");
      return;
    }

    try {
      console.log("Connecting to WebSocket:", url);
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected successfully");
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);

          // 核心消息处理逻辑
          switch (message.type) {
            case "simulation_frame":
              // 直接设置帧数据，用于驱动Three.js更新
              setFrameData(message.data);
              break;
            case "connected":
              toast.success(`✅ WebSocket 已连接 (ID: ${message.client_id})`);
              break;
            case "session_stream_started":
              toast.info(`🎬 数据流开始 (共 ${message.total_frames} 帧)`);
              break;
            case "session_stream_completed":
              toast.success("🏁 数据流传输完成");
              break;
            case "error":
              toast.error(`❌ WebSocket 错误: ${message.message}`);
              break;
            default:
              // 对于其他消息类型，只在控制台打印
              console.log("WebSocket Info:", message);
          }
        } catch (error) {
          console.error("解析WebSocket消息失败:", error);
        }
      };

      wsRef.current.onclose = (event) => {
        setIsConnected(false);
        console.log("WebSocket disconnected:", {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
        });
      };

      wsRef.current.onerror = (event) => {
        console.error("WebSocket error occurred:", event);
        setIsConnected(false);
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      setIsConnected(false);
    }
  }, [url]);

  const disconnect = useCallback(() => {
    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      wsRef.current = null;
      setIsConnected(false);
    } catch (error) {
      console.error("Error disconnecting WebSocket:", error);
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket is not connected, cannot send message.");
    }
  }, []);

  // 唯一需要的主动发送函数：开始会话流
  const startSessionStream = useCallback(
    (sessionId: string, fps: number = 10) => {
      // 在发送开始指令前，确保连接是打开的
      const waitForConnection = (
        callback: () => void,
        maxRetries = 10,
        interval = 200
      ) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          callback();
        } else if (maxRetries > 0) {
          setTimeout(
            () => waitForConnection(callback, maxRetries - 1, interval),
            interval
          );
        } else {
          toast.error("WebSocket 连接超时，无法开始数据流");
        }
      };

      // 尝试连接（如果尚未连接）
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
      }

      // 等待连接成功后发送消息
      waitForConnection(() => {
        console.log(
          `🎬 Sending start_session_stream for session: ${sessionId}`
        );
        sendMessage({
          type: "start_session_stream",
          session_id: sessionId,
          fps: fps,
        });
      });
    },
    [connect, sendMessage]
  );

  useEffect(() => {
    // 组件挂载时自动连接
    connect();

    return () => {
      // 组件卸载时断开连接
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    frameData,
    mapData, // 虽然不再通过WS更新，但保留状态以供其他组件使用
    sendMessage, // 保留以备调试之用
    startSessionStream, // 暴露给UI组件调用
  };
};
