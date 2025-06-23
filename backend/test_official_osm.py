# 用于测试 tactics2d.map.parser.OSMParser 解析 OSM 文件的最小示例
from tactics2d.map.parser import OSMParser

if __name__ == "__main__":
    osm_path = "./app/data/highD_map/highD_2.osm"
    parser = OSMParser()
    try:
        map_ = parser.parse(osm_path)
        print("✅ 解析成功！\n")
        print(f"节点数: {len(map_.nodes)}")
        print(f"道路线数: {len(map_.roadlines)}")
        print(f"区域数: {len(map_.areas)}")
        print(f"车道数: {len(map_.lanes)}")
        print(f"交通规则数: {len(map_.regulations)}")
        # 打印部分节点和道路线示例
        for i, (nid, node) in enumerate(map_.nodes.items()):
            print(f"Node {nid}: (x={node.x}, y={node.y})")
            if i >= 2:
                break
        for i, (rid, roadline) in enumerate(map_.roadlines.items()):
            print(f"RoadLine {rid}: type={roadline.type_}, geometry={roadline.geometry}")
            if i >= 2:
                break
    except Exception as e:
        print(f"❌ 解析失败: {e}")
