#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修正后的官方 OSMParser API 使用
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.tactics2d_wrapper import tactics2d_wrapper

def test_fixed_official_api():
    """测试修正后的官方API"""
    print("🧪 测试修正后的官方 OSMParser API")
    print("=" * 60)
    
    osm_path = "./data/highD_map/highD_2.osm"
    
    try:
        # 测试官方方法
        print(f"📁 解析文件: {osm_path}")
        map_data = tactics2d_wrapper.parse_osm_map_with_official_method(osm_path)
        
        print("✅ 官方API解析成功!")
        print(f"📊 解析结果统计:")
        print(f"   - 道路: {len(map_data.get('roads', []))}")
        print(f"   - 车道: {len(map_data.get('lanes', []))}")
        print(f"   - 边界: {len(map_data.get('boundaries', []))}")
        print(f"   - 区域: {len(map_data.get('areas', []))}")
        
        # 显示边界信息
        boundary = map_data.get('boundary', {})
        if boundary:
            print(f"   - 边界: {boundary}")
        
        # 显示第一个道路信息
        roads = map_data.get('roads', [])
        if roads:
            print(f"   - 第一个道路: {roads[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 官方API解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_complete_parsing_flow():
    """测试完整的解析流程（包括回退机制）"""
    print("\n🔄 测试完整解析流程")
    print("=" * 60)
    
    osm_path = "./data/highD_map/highD_2.osm"
    
    try:
        # 使用主要解析方法（包含回退机制）
        print(f"📁 解析文件: {osm_path}")
        map_data = tactics2d_wrapper.parse_osm_map_simple(osm_path)
        
        print("✅ 完整解析流程成功!")
        print(f"📊 解析结果统计:")
        print(f"   - 道路: {len(map_data.get('roads', []))}")
        print(f"   - 车道: {len(map_data.get('lanes', []))}")
        print(f"   - 边界: {len(map_data.get('boundaries', []))}")
        print(f"   - 区域: {len(map_data.get('areas', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ 完整解析流程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 测试修正后的 OSM 解析功能")
    print("=" * 60)
    
    # 测试修正的官方API
    result1 = test_fixed_official_api()
    
    # 测试完整解析流程
    result2 = test_complete_parsing_flow()
    
    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print(f"   官方API: {'✅ 成功' if result1 else '❌ 失败'}")
    print(f"   完整流程: {'✅ 成功' if result2 else '❌ 失败'}")
    
    if result1 and result2:
        print("\n🎉 所有测试通过！FastAPI 后端可以正常使用官方 OSM 解析 API")
    elif result2:
        print("\n⚠️  官方API有问题，但回退机制有效")
    else:
        print("\n💔 测试失败，需要进一步调试")
    
    print("\n测试完成")
