#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于官方示例代码测试 OSMParser API 是否有问题
"""

from tactics2d.map.parser import OSMParser
import xml.etree.ElementTree as ET
import json
import pkg_resources

def load_official_config():
    """加载官方配置文件"""
    try:
        config_path = pkg_resources.resource_filename('tactics2d', 'dataset_parser/map.config')
        with open(config_path, 'r') as f:
            config_content = f.read()
            # 移除JSON中的注释（// 开头的行）
            config_lines = []
            for line in config_content.split('\n'):
                if not line.strip().startswith('//'):
                    config_lines.append(line)
            clean_config = '\n'.join(config_lines)
            return json.loads(clean_config)
    except Exception as e:
        print(f"❌ 加载官方配置失败: {e}")
        return {}

def test_official_api_method1():
    """测试方法1: 按照用户提供的官方示例"""
    print("\n🧪 方法1: 按照用户提供的官方示例")
    
    osm_path = "./data/highD_map/highD_2.osm"
    HIGHD_MAP_CONFIG = load_official_config()
    
    try:
        map_parser = OSMParser(lanelet2=True)
        
        if "highD_2" in HIGHD_MAP_CONFIG:
            config = HIGHD_MAP_CONFIG["highD_2"]
            print(f"使用配置: {config}")
        else:
            print("未找到 highD_2 配置，使用空配置")
            config = {}
        
        # 按照用户示例直接传文件路径
        map_ = map_parser.parse(osm_path, config)
        
        print("✅ 方法1成功!")
        print(f"解析结果类型: {type(map_)}")
        return map_
        
    except Exception as e:
        print(f"❌ 方法1失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def test_official_api_method2():
    """测试方法2: 先解析XML再传给parser"""
    print("\n🧪 方法2: 先解析XML再传给parser (基于真实API签名)")
    
    osm_path = "./data/highD_map/highD_2.osm"
    HIGHD_MAP_CONFIG = load_official_config()
    
    try:
        # 先解析XML文件
        tree = ET.parse(osm_path)
        xml_root = tree.getroot()
        print(f"XML根元素: {xml_root.tag}")
        
        map_parser = OSMParser(lanelet2=True)
        
        if "highD_2" in HIGHD_MAP_CONFIG:
            config = HIGHD_MAP_CONFIG["highD_2"]
            print(f"使用配置: {config}")
            
            # 提取project_rule和gps_origin
            project_rule = config.get("project_rule", {})
            gps_origin = tuple(config.get("gps_origin", [0.0, 0.0]))
            
            print(f"投影规则: {project_rule}")
            print(f"GPS原点: {gps_origin}")
            
            # 使用正确的API签名
            map_ = map_parser.parse(xml_root, project_rule, gps_origin, config)
        else:
            print("使用默认参数")
            map_ = map_parser.parse(xml_root)
        
        print("✅ 方法2成功!")
        print(f"解析结果类型: {type(map_)}")
        return map_
        
    except Exception as e:
        print(f"❌ 方法2失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def test_different_osm_files():
    """测试不同的OSM文件，看是否是文件特定问题"""
    print("\n🧪 测试不同OSM文件")
    
    osm_files = [
        "./data/highD_map/highD_1.osm",
        "./data/highD_map/highD_2.osm", 
        "./data/highD_map/highD_3.osm"
    ]
    
    for osm_path in osm_files:
        print(f"\n测试文件: {osm_path}")
        try:
            # 检查文件是否存在
            import os
            if not os.path.exists(osm_path):
                print(f"⚠️  文件不存在: {osm_path}")
                continue
                
            # 简单测试
            tree = ET.parse(osm_path)
            xml_root = tree.getroot()
            
            map_parser = OSMParser(lanelet2=True)
            map_ = map_parser.parse(xml_root)
            
            print(f"✅ {osm_path} 解析成功")
            if hasattr(map_, 'nodes'):
                print(f"  节点数: {len(map_.nodes)}")
                
        except Exception as e:
            print(f"❌ {osm_path} 解析失败: {e}")

def analyze_error_source():
    """分析错误的具体来源"""
    print("\n🔍 分析错误来源")
    
    osm_path = "./data/highD_map/highD_2.osm"
    
    try:
        tree = ET.parse(osm_path)
        xml_root = tree.getroot()
        
        # 检查XML结构
        print(f"XML根标签: {xml_root.tag}")
        print(f"XML属性: {xml_root.attrib}")
        
        # 查找bounds元素
        bounds_elements = xml_root.findall('bounds')
        print(f"Bounds元素数量: {len(bounds_elements)}")
        
        if bounds_elements:
            for i, bounds in enumerate(bounds_elements):
                print(f"Bounds {i}: {bounds.attrib}")
        else:
            print("⚠️  没有找到bounds元素")
            
        # 查找nodes
        nodes = xml_root.findall('node')
        print(f"Node元素数量: {len(nodes)}")
        if nodes:
            print(f"第一个node: {nodes[0].attrib}")
            
        return xml_root
        
    except Exception as e:
        print(f"❌ XML分析失败: {e}")
        return None

if __name__ == "__main__":
    print("🚀 测试官方 OSMParser API")
    print("=" * 60)
    
    # 1. 分析错误来源
    xml_root = analyze_error_source()
    
    # 2. 测试官方示例方法
    result1 = test_official_api_method1()
    
    # 3. 测试修正的API调用方法
    result2 = test_official_api_method2()
    
    # 4. 测试不同文件
    test_different_osm_files()
    
    print("\n" + "=" * 60)
    print("📊 测试结论:")
    
    if result1:
        print("✅ 官方示例方法可用")
    else:
        print("❌ 官方示例方法不可用")
        
    if result2:
        print("✅ 修正的API调用方法可用")
    else:
        print("❌ 修正的API调用方法也不可用")
        
    if not result1 and not result2:
        print("\n💡 结论: 官方 OSMParser API 确实存在问题")
        print("   错误位置: tactics2d/map/parser/parse_osm.py 第171行")
        print("   错误原因: 'int' object has no attribute 'get'")
        print("   建议: 继续使用手动解析方案")
    else:
        print("\n💡 结论: API可用，可能是使用方式问题")
        
    print("\n测试完成")