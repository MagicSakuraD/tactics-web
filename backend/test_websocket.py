#!/usr/bin/env python3
"""
测试WebSocket连接和数据格式
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/simulation"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")
            
            # 测试地图数据请求
            map_request = {
                "type": "get_map",
                "session_id": "test_session"
            }
            
            await websocket.send(json.dumps(map_request))
            print("📤 发送地图请求:", map_request)
            
            # 接收地图数据
            response = await websocket.recv()
            data = json.loads(response)
            print("📥 收到地图响应:")
            print(f"   类型: {data.get('type')}")
            print(f"   状态: {data.get('status')}")
            if data.get('data'):
                map_data = data['data']
                print(f"   道路数量: {len(map_data.get('roads', []))}")
                print(f"   车道数量: {len(map_data.get('lanes', []))}")
                print(f"   边界数量: {len(map_data.get('boundaries', []))}")
                
                # 检查数据格式
                if map_data.get('roads'):
                    road = map_data['roads'][0]
                    print(f"   第一条道路格式: {list(road.keys())}")
                    print(f"   坐标示例: {road.get('coordinates', [])[:2]}")
            
            # 测试轨迹数据流
            stream_request = {
                "type": "start_stream",
                "session_id": "test_session",
                "fps": 10
            }
            
            await websocket.send(json.dumps(stream_request))
            print("📤 发送数据流请求:", stream_request)
            
            # 接收几帧数据
            for i in range(3):
                response = await websocket.recv()
                data = json.loads(response)
                print(f"📥 收到第{i+1}帧数据:")
                print(f"   类型: {data.get('type')}")
                if data.get('data'):
                    frame_data = data['data']
                    if 'vehicles' in frame_data:
                        print(f"   车辆数量: {len(frame_data['vehicles'])}")
                        if frame_data['vehicles']:
                            vehicle = frame_data['vehicles'][0]
                            print(f"   第一辆车位置: {vehicle.get('position')}")
                            print(f"   第一辆车属性: {list(vehicle.keys())}")
            
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
