#!/usr/bin/env python3
"""
测试OSM解析修复
"""

import sys
import os
from pathlib import Path

# 添加app目录到Python路径
sys.path.append(str(Path(__file__).parent / "app"))

from app.utils.tactics2d_wrapper import tactics2d_wrapper

def test_osm_preprocessing():
    """测试OSM预处理功能"""
    osm_file = "/home/quinn/APP/Code/tactics2d-web/backend/data/highD_map/highD_2.osm"
    
    if not Path(osm_file).exists():
        print(f"❌ OSM文件不存在: {osm_file}")
        return False
    
    print(f"🧪 开始测试OSM预处理: {osm_file}")
    
    try:
        # 测试预处理
        processed_file = tactics2d_wrapper._preprocess_osm_file(osm_file)
        
        print(f"✅ 预处理完成: {processed_file}")
        
        # 检查预处理后的文件内容
        with open(processed_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '<bounds' in content:
                print("✅ 成功添加了bounds标签")
                # 显示bounds内容
                import re
                bounds_match = re.search(r'<bounds[^>]*>', content)
                if bounds_match:
                    print(f"   bounds内容: {bounds_match.group()}")
            else:
                print("❌ 未找到bounds标签")
                
        return True
        
    except Exception as e:
        print(f"❌ 预处理失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

def test_osm_parsing():
    """测试OSM解析功能"""
    osm_file = "/home/quinn/APP/Code/tactics2d-web/backend/data/highD_map/highD_2.osm"
    
    if not Path(osm_file).exists():
        print(f"❌ OSM文件不存在: {osm_file}")
        return False
    
    print(f"🧪 开始测试OSM解析: {osm_file}")
    
    try:
        # 测试OSM解析
        map_data = tactics2d_wrapper.parse_osm_map_simple(osm_file)
        
        print(f"✅ OSM解析成功!")
        print(f"   - 道路数量: {len(map_data.get('roads', []))}")
        print(f"   - 车道数量: {len(map_data.get('lanes', []))}")
        print(f"   - 边界数量: {len(map_data.get('boundaries', []))}")
        print(f"   - 区域数量: {len(map_data.get('areas', []))}")
        
        # 显示一些样本数据
        if map_data.get('roads'):
            print(f"   - 第一条道路: {map_data['roads'][0]['id']}")
        if map_data.get('lanes'):
            print(f"   - 第一条车道: {map_data['lanes'][0]['id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ OSM解析失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

def test_official_osm_parsing():
    """测试官方方法OSM解析功能"""
    osm_file = "/home/quinn/APP/Code/tactics2d-web/backend/data/highD_map/highD_2.osm"
    
    if not Path(osm_file).exists():
        print(f"❌ OSM文件不存在: {osm_file}")
        return False
    
    print(f"🧪 开始测试官方方法OSM解析: {osm_file}")
    
    try:
        # 测试官方方法解析
        map_data = tactics2d_wrapper.parse_osm_map_with_official_method(osm_file)
        
        print(f"✅ 官方方法解析成功!")
        print(f"   - 道路数量: {len(map_data.get('roads', []))}")
        print(f"   - 车道数量: {len(map_data.get('lanes', []))}")
        print(f"   - 边界数量: {len(map_data.get('boundaries', []))}")
        print(f"   - 区域数量: {len(map_data.get('areas', []))}")
        
        # 显示一些样本数据
        if map_data.get('roads'):
            print(f"   - 第一条道路: {map_data['roads'][0]['id']}")
        if map_data.get('lanes'):
            print(f"   - 第一条车道: {map_data['lanes'][0]['id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 官方方法解析失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("OSM解析修复测试")
    print("=" * 50)
    
    # 检查tactics2d是否可用
    if not tactics2d_wrapper.is_available():
        print("❌ Tactics2D不可用")
        sys.exit(1)
    
    # 首先测试预处理
    print("\n1. 测试预处理功能")
    preprocess_success = test_osm_preprocessing()
    
    print("\n2. 测试解析功能")
    # 测试解析
    parse_success = test_osm_parsing()
    
    print("\n3. 测试官方方法解析功能")
    official_parse_success = test_official_osm_parsing()
    
    print("=" * 50)
    if preprocess_success and parse_success and official_parse_success:
        print("✅ 所有测试通过")
    else:
        print("❌ 部分测试失败")
    print("=" * 50)
