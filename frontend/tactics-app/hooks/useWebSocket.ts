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
}

interface ThreeJSFrameData {
  type: string;
  frame: number;
  timestamp: number;
  vehicles: Array<{
    id: number;
    position: { x: number; y: number; z: number };
    rotation: { x: number; y: number; z: number };
    velocity: { x: number; y: number; z: number };
    dimensions: { x: number; y: number; z: number };
    color: string;
    type: string;
  }>;
}

interface MapData {
  type: string;
  roads: Array<{
    type: string;
    coordinates: Array<[number, number, number]>;
    properties: {
      id: string;
      width: number;
      color: string;
    };
  }>;
  lanes: Array<{
    type: string;
    coordinates: Array<[number, number, number]>;
    properties: {
      id: string;
      width: number;
      color: string;
      dashed: boolean;
    };
  }>;
  boundaries: Array<{
    type: string;
    coordinates: Array<[number, number, number]>;
    properties: {
      id: string;
      color: string;
      width: number;
    };
  }>;
  metadata: {
    bounds: any;
    scale: number;
    units: string;
  };
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  frameData: ThreeJSFrameData | null;
  mapData: MapData | null;
  sendMessage: (message: any) => void;
  connect: () => void;
  disconnect: () => void;
  requestFrame: (frame: number, sessionId?: string) => void;
  requestMapHttp: () => Promise<void>; // HTTP地图请求
  startStream: (sessionId?: string, fps?: number) => void;
}

export const useWebSocket = (
  url: string = "ws://localhost:8000/ws/simulation"
): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [frameData, setFrameData] = useState<ThreeJSFrameData | null>(null);
  const [mapData, setMapData] = useState<MapData | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

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

          // 处理不同类型的消息
          switch (message.type) {
            case "frame_data":
            case "simulation_frame":
              setFrameData(message.data as ThreeJSFrameData);
              break;
            case "map_data":
              setMapData(message.data as MapData);
              break;
            case "connected":
              console.log("WebSocket连接确认:", message.message);
              break;
            case "stream_started":
              console.log("数据流开始:", message.message);
              break;
            case "stream_completed":
              console.log("数据流完成:", message.message);
              break;
            case "error":
              console.error("WebSocket错误:", message.message);
              break;
            default:
              console.log("未知消息类型:", message);
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
        console.error("WebSocket error occurred:", {
          type: event.type,
          timeStamp: event.timeStamp,
          url: wsRef.current?.url,
          readyState: wsRef.current?.readyState,
        });
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
      console.warn("WebSocket未连接，无法发送消息");
    }
  }, []);

  const requestFrame = useCallback(
    (frame: number, sessionId: string = "default") => {
      sendMessage({
        type: "get_frame",
        frame,
        session_id: sessionId,
      });
    },
    [sendMessage]
  );

  // HTTP地图数据请求 - 更适合静态地图数据
  const requestMapHttp = useCallback(async () => {
    try {
      console.log("🗺️ [HTTP] 请求地图数据...");
      const response = await fetch("http://localhost:8000/api/map");
      const result = await response.json();

      if (result.success && result.data) {
        setMapData(result.data as MapData);
        console.log("✅ [HTTP] 地图数据加载成功:", {
          source: result.source,
          roads: result.data.roads?.length || 0,
          lanes: result.data.lanes?.length || 0,
          boundaries: result.data.boundaries?.length || 0,
        });
      } else {
        console.error("❌ [HTTP] 地图数据加载失败:", result.error);
      }
    } catch (error) {
      console.error("❌ [HTTP] 地图请求异常:", error);
    }
  }, []);

  const startStream = useCallback(
    (sessionId: string = "default", fps: number = 10) => {
      sendMessage({
        type: "start_stream",
        session_id: sessionId,
        fps,
      });
    },
    [sendMessage]
  );

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    lastMessage,
    frameData,
    mapData,
    sendMessage,
    connect,
    disconnect,
    requestFrame,
    requestMapHttp,
    startStream,
  };
};
