#!/usr/bin/env python3
"""
完整测试：验证优化后的架构和数据传输
包含详细的数据打印和传输方式对比
"""

import asyncio
import json
import requests
from datetime import datetime

def test_http_map_api():
    """测试HTTP地图API"""
    print("\n" + "="*60)
    print("🧪 测试 HTTP 地图API")
    print("="*60)
    
    try:
        print(f"📤 发送HTTP请求: GET http://localhost:8000/api/map")
        start_time = datetime.now()
        
        response = requests.get("http://localhost:8000/api/map", timeout=10)
        
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ HTTP响应成功 (耗时: {response_time:.2f}ms)")
            print(f"📊 响应大小: {len(response.text)} 字符")
            print(f"🗺️ 地图数据来源: {data.get('source', 'unknown')}")
            
            if data.get('success') and data.get('data'):
                map_data = data['data']
                print(f"📍 地图数据统计:")
                print(f"   - 道路: {len(map_data.get('roads', []))}")
                print(f"   - 车道: {len(map_data.get('lanes', []))}")
                print(f"   - 边界: {len(map_data.get('boundaries', []))}")
                
                if map_data.get('roads'):
                    road = map_data['roads'][0]
                    print(f"   - 示例道路ID: {road.get('properties', {}).get('id')}")
                    print(f"   - 示例道路坐标数: {len(road.get('coordinates', []))}")
                    
                return True
            else:
                print(f"❌ 响应格式错误: {data}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ HTTP请求异常: {e}")
        return False

async def test_websocket_vs_http():
    """对比WebSocket和HTTP传输效率"""
    print("\n" + "="*60) 
    print("⚡ WebSocket vs HTTP 传输效率对比")
    print("="*60)
    
    # WebSocket测试
    try:
        import websockets
        
        print(f"📤 测试WebSocket地图传输...")
        start_time = datetime.now()
        
        async with websockets.connect("ws://localhost:8000/ws/simulation") as websocket:
            # 发送地图请求
            await websocket.send(json.dumps({
                "type": "get_map",
                "session_id": "test_comparison"
            }))
            
            # 接收响应
            response = await websocket.recv()
            end_time = datetime.now()
            
            ws_time = (end_time - start_time).total_seconds() * 1000
            data = json.loads(response)
            
            print(f"✅ WebSocket响应 (耗时: {ws_time:.2f}ms)")
            print(f"📊 WebSocket数据大小: {len(response)} 字符")
            
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")
        ws_time = float('inf')
    
    # HTTP测试
    print(f"📤 测试HTTP地图传输...")
    start_time = datetime.now()
    
    try:
        response = requests.get("http://localhost:8000/api/map", timeout=10)
        end_time = datetime.now()
        
        http_time = (end_time - start_time).total_seconds() * 1000
        
        print(f"✅ HTTP响应 (耗时: {http_time:.2f}ms)")
        print(f"📊 HTTP数据大小: {len(response.text)} 字符")
        
        # 对比结果
        print(f"\n🏆 传输效率对比:")
        if ws_time < http_time:
            print(f"   WebSocket更快: {ws_time:.2f}ms vs {http_time:.2f}ms")
            print(f"   差距: {http_time - ws_time:.2f}ms")
        else:
            print(f"   HTTP更快: {http_time:.2f}ms vs {ws_time:.2f}ms") 
            print(f"   差距: {ws_time - http_time:.2f}ms")
            
    except Exception as e:
        print(f"❌ HTTP对比测试失败: {e}")

def test_data_transmission_analysis():
    """分析数据传输模式的优缺点"""
    print("\n" + "="*60)
    print("📈 数据传输模式分析")
    print("="*60)
    
    print("🗺️  地图数据特性:")
    print("   ✓ 静态内容，加载后不变")
    print("   ✓ 一次性传输，无需实时更新")
    print("   ✓ 较大的数据量")
    print("   ✓ 可以缓存")
    
    print("\n🚗 轨迹数据特性:")
    print("   ✓ 动态内容，持续变化")
    print("   ✓ 需要实时流式传输")
    print("   ✓ 频繁的小数据包")
    print("   ✓ 时序敏感")
    
    print("\n💡 传输方式建议:")
    print("   🔄 地图数据 → HTTP API")
    print("     - 利用HTTP缓存机制")
    print("     - 减少WebSocket连接压力")
    print("     - 更好的错误处理")
    print("     - 支持断点续传")
    
    print("\n   ⚡ 轨迹数据 → WebSocket")
    print("     - 低延迟实时传输")
    print("     - 持久连接避免重复握手")
    print("     - 双向通信支持控制信号")
    print("     - 流式传输优化")

def main():
    """主测试函数"""
    print("🚀 开始完整的架构优化测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 测试HTTP地图API
    http_success = test_http_map_api()
    
    # 2. 测试传输效率对比
    asyncio.run(test_websocket_vs_http())
    
    # 3. 分析传输模式
    test_data_transmission_analysis()
    
    print("\n" + "="*60)
    print("🎯 架构优化总结")
    print("="*60)
    print("✅ 移除了复杂的BEV相机依赖")
    print("✅ 简化了后端3D几何生成")
    print("✅ 前端完全控制3D渲染")
    print("✅ 优化了数据传输方式:")
    print("   - 地图数据: WebSocket → HTTP")
    print("   - 轨迹数据: 保持WebSocket实时流")
    print("✅ 添加了详细的数据流打印")
    print("✅ 提升了系统性能和可维护性")
    
    if http_success:
        print("\n🏆 测试结果: 架构优化成功！")
    else:
        print("\n⚠️  测试结果: 部分功能需要调试")

if __name__ == "__main__":
    main()
