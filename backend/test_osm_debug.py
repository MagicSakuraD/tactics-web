#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试官方 OSMParser 的使用方法和错误原因
"""

from tactics2d.map.parser import OSMParser
import traceback
import inspect

def test_osm_parser_methods():
    """测试 OSMParser 类的方法签名和使用"""
    print("🔍 检查 OSMParser 类的方法和签名:")
    
    # 检查 OSMParser 类的所有方法
    parser = OSMParser()
    methods = [method for method in dir(parser) if not method.startswith('_')]
    print(f"可用方法: {methods}")
    
    # 检查 parse 方法的签名
    if hasattr(parser, 'parse'):
        parse_method = getattr(parser, 'parse')
        sig = inspect.signature(parse_method)
        print(f"\n📋 parse 方法签名: {sig}")
        print(f"参数: {list(sig.parameters.keys())}")
        
        # 打印每个参数的详细信息
        for param_name, param in sig.parameters.items():
            print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else '无类型注解'}")
            print(f"    默认值: {param.default if param.default != inspect.Parameter.empty else '无默认值'}")
    
    return parser

def test_different_parse_methods():
    """测试不同的 parse 方法调用方式"""
    osm_path = "/home/quinn/APP/Code/tactics2d-web/backend/data/highD_map/highD_2.osm"
    
    print(f"\n🧪 测试文件: {osm_path}")
    
    # 方法1: 只传文件路径
    print("\n方法1: parser.parse(osm_path)")
    try:
        parser = OSMParser()
        map_ = parser.parse(osm_path)
        print("✅ 成功!")
        print(f"解析结果类型: {type(map_)}")
        if hasattr(map_, 'nodes'):
            print(f"节点数: {len(map_.nodes)}")
        return map_
    except Exception as e:
        print(f"❌ 失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        traceback.print_exc()
    
    # 方法2: 传递 file_path 参数
    print("\n方法2: parser.parse(file_path=osm_path)")
    try:
        parser = OSMParser()
        map_ = parser.parse(file_path=osm_path)
        print("✅ 成功!")
        return map_
    except Exception as e:
        print(f"❌ 失败: {e}")
        traceback.print_exc()
    
    # 方法3: 传递配置参数
    print("\n方法3: parser.parse(osm_path, config)")
    try:
        parser = OSMParser()
        config = {}  # 空配置
        map_ = parser.parse(osm_path, config)
        print("✅ 成功!")
        return map_
    except Exception as e:
        print(f"❌ 失败: {e}")
        traceback.print_exc()
    
    # 方法4: 使用 lanelet2 参数
    print("\n方法4: OSMParser(lanelet2=True)")
    try:
        parser = OSMParser(lanelet2=True)
        map_ = parser.parse(osm_path)
        print("✅ 成功!")
        return map_
    except Exception as e:
        print(f"❌ 失败: {e}")
        traceback.print_exc()
    
    # 方法5: 尝试其他初始化参数
    print("\n方法5: OSMParser(lanelet2=False)")
    try:
        parser = OSMParser(lanelet2=False)
        map_ = parser.parse(osm_path)
        print("✅ 成功!")
        return map_
    except Exception as e:
        print(f"❌ 失败: {e}")
        traceback.print_exc()
    
    return None

def analyze_osm_file():
    """分析 OSM 文件内容，看是否有格式问题"""
    osm_path = "/home/quinn/APP/Code/tactics2d-web/backend/data/highD_map/highD_2.osm"
    
    print(f"\n📄 分析 OSM 文件: {osm_path}")
    
    try:
        with open(osm_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        print(f"文件大小: {len(content)} 字符")
        print(f"行数: {len(lines)}")
        print(f"前5行:")
        for i, line in enumerate(lines[:5]):
            print(f"  {i+1}: {line}")
        
        # 检查是否包含基本OSM元素
        has_nodes = '<node' in content
        has_ways = '<way' in content
        has_relations = '<relation' in content
        has_bounds = '<bounds' in content
        
        print(f"\n📊 OSM元素检查:")
        print(f"  节点 (nodes): {'✅' if has_nodes else '❌'}")
        print(f"  路径 (ways): {'✅' if has_ways else '❌'}")
        print(f"  关系 (relations): {'✅' if has_relations else '❌'}")
        print(f"  边界 (bounds): {'✅' if has_bounds else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 文件分析失败: {e}")
        return False

def test_xml_root_parsing():
    """测试正确的XML解析方式 - 传递XML根元素"""
    import xml.etree.ElementTree as ET
    osm_path = "/home/quinn/APP/Code/tactics2d-web/backend/data/highD_map/highD_2.osm"
    
    print("\n🧪 测试XML解析方式: 传递XML根元素")
    
    try:
        # 先解析XML文件
        tree = ET.parse(osm_path)
        xml_root = tree.getroot()
        
        # 然后传递根元素到parser.parse
        parser = OSMParser()
        project_rule = {}
        gps_origin = (0.0, 0.0)
        configs = {}
        
        print("🔍 XML根元素类型:", type(xml_root))
        print("🔍 XML根元素标签:", xml_root.tag)
        
        map_obj = parser.parse(xml_root, project_rule, gps_origin, configs)
        print("✅ 成功!")
        
        # 检查解析结果
        print(f"解析结果类型: {type(map_obj)}")
        
        if hasattr(map_obj, 'nodes'):
            print(f"节点数: {len(map_obj.nodes)}")
        if hasattr(map_obj, 'roadlines'):
            print(f"道路线数: {len(map_obj.roadlines)}")
        if hasattr(map_obj, 'relations'):
            print(f"关系数: {len(map_obj.relations)}")
        
        return map_obj
    
    except Exception as e:
        print(f"❌ 失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 开始调试 OSMParser API 使用")
    print("=" * 60)
    
    # 1. 检查方法签名
    parser = test_osm_parser_methods()
    
    # 2. 分析OSM文件
    analyze_osm_file()
    
    # 3. 测试不同的调用方式（传递文件路径 - 旧方式，预期会失败）
    # result = test_different_parse_methods()
    
    # 4. 测试正确的调用方式（传递XML根元素）
    result = test_xml_root_parsing()
    
    if result:
        print("\n🎉 找到了可工作的方法!")
        print(f"解析结果: {type(result)}")
        if hasattr(result, '__dict__'):
            attrs = [attr for attr in dir(result) if not attr.startswith('_')]
            print(f"可用属性: {attrs[:10]}...")  # 只显示前10个
    else:
        print("\n💔 所有方法都失败了")
    
    print("\n" + "=" * 60)
    print("调试完成")
