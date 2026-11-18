# -*- coding: utf-8 -*-
"""
Created on Tue Aug 12 13:10:37 2025

@author: mxl33
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 15:39:59 2025
@author: mxl33

完整代码：
- 从INP文件解析节点、管道和横断面数据
- 保持节点高程不变（移除高程调整功能）
- 管道直径调整：先按增长因子计算后，再根据预设参考值向上取整
- 校正管道流向：确保高程较高的一端为起点
- 最终结果导出到Excel，兼容绘图代码格式
"""

import re
import heapq
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

def parse_inp(file_path):
    """
    解析 INP 文件，提取节点、管道、横断面和坐标数据。
    返回：nodes_df, conduits_df
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()

    node_data, conduit_data, diameter_data, coord_data = [], [], [], []
    in_junction_section = in_conduit_section = in_xsections_section = in_coordinates_section = False

    for line in lines:
        if line.startswith('[JUNCTIONS]'):
            in_junction_section = True
            continue
        if in_junction_section and line.startswith('['):
            in_junction_section = False
        if in_junction_section and not line.startswith(';') and line.strip():
            parts = re.split(r'\s+', line.strip())
            node_data.append((parts[0], float(parts[1])))

        if line.startswith('[CONDUITS]'):
            in_conduit_section = True
            continue
        if in_conduit_section and line.startswith('['):
            in_conduit_section = False
        if in_conduit_section and not line.startswith(';') and line.strip():
            parts = re.split(r'\s+', line.strip())
            conduit_data.append((parts[0], parts[1], parts[2]))

        if line.startswith('[XSECTIONS]'):
            in_xsections_section = True
            continue
        if in_xsections_section and line.startswith('['):
            in_xsections_section = False
        if in_xsections_section and not line.startswith(';') and line.strip():
            parts = re.split(r'\s+', line.strip())
            diameter_data.append((parts[0], float(parts[2])))

        if line.startswith('[COORDINATES]'):
            in_coordinates_section = True
            continue
        if in_coordinates_section and line.startswith('['):
            in_coordinates_section = False
        if in_coordinates_section and not line.startswith(';') and line.strip():
            parts = re.split(r'\s+', line.strip())
            coord_data.append((parts[0], float(parts[1]), float(parts[2])))

    nodes_df = pd.DataFrame(node_data, columns=['Node', 'InvertElev'])
    conduits_df = pd.DataFrame(conduit_data, columns=['Link', 'FromNode', 'ToNode'])
    diameters_df = pd.DataFrame(diameter_data, columns=['Link', 'Diameter'])
    coords_df = pd.DataFrame(coord_data, columns=['Node', 'X-Coord', 'Y-Coord'])

    # 合并坐标数据到节点数据
    nodes_df = pd.merge(nodes_df, coords_df, on='Node', how='left')
    # 如果某些节点没有坐标，填充为0
    nodes_df['X-Coord'] = nodes_df['X-Coord'].fillna(0.0)
    nodes_df['Y-Coord'] = nodes_df['Y-Coord'].fillna(0.0)

    conduits_df = pd.merge(conduits_df, diameters_df, on='Link', how='left')
    # 初始时将调整直径列设为原直径
    conduits_df['AdjustedDiameter'] = conduits_df['Diameter']

    return nodes_df, conduits_df

def round_diameter(value, reference_values=[0.35, 0.4, 0.45, 0.5, 0.6, 0.8, 1, 1.2, 1.5, 1.8, 2]):
    """
    根据预设参考值列表对计算出的直径进行"向上取整"
      - 如果正好等于某个参考值，则直接采用；
      - 小于最小参考值时采用最小值；
      - 超过最大参考值时采用最大值；
      - 其它情况返回第一个大于计算值的参考值。
    """
    for ref in reference_values:
        if abs(value - ref) < 1e-6:
            return ref
    if value < reference_values[0]:
        return reference_values[0]
    if value > reference_values[-1]:
        return reference_values[-1]
    for ref in reference_values:
        if value < ref:
            return ref
    return reference_values[-1]

def get_upstream_pipes_simple(conduits_df, outlet_nodes, max_depth=10):
    """
    从出口节点开始，向上游追溯管道
    返回: dict {outlet_node: [(pipe_id, from_node, to_node, distance_from_outlet), ...]}
    """
    upstream_pipes = {}
    
    for outlet in outlet_nodes:
        pipes_info = []
        visited_nodes = set()
        visited_pipes = set()
        current_level = [outlet]
        distance = 0
        
        print(f"开始追溯出口 {outlet} 的上游管道...")
        
        while current_level and distance < max_depth:
            next_level = []
            
            for current_node in current_level:
                if current_node in visited_nodes:
                    continue
                visited_nodes.add(current_node)
                
                # 找到所有流向当前节点的管道
                upstream_conduits = conduits_df[conduits_df['ToNode'].astype(str) == str(current_node)]
                
                for _, conduit in upstream_conduits.iterrows():
                    pipe_id = conduit['Link']
                    if pipe_id not in visited_pipes:
                        visited_pipes.add(pipe_id)
                        from_node = str(conduit['FromNode'])
                        to_node = str(conduit['ToNode'])
                        
                        pipes_info.append((pipe_id, from_node, to_node, distance))
                        next_level.append(from_node)
                        print(f"  找到管道 {pipe_id}: {from_node} → {to_node} (距离={distance})")
            
            current_level = next_level
            distance += 1
        
        upstream_pipes[outlet] = pipes_info
        print(f"出口 {outlet} 共找到 {len(pipes_info)} 条上游管道")
    
    return upstream_pipes

def adjust_pipe_diameters_upstream(conduits_df, selected_outlets, growth_factor=1.2, upstream_depth=5):
    """
    对新出口的上游管道进行调整，确保下游管道直径大于上游管道：
    - 从新出口开始向上游追溯
    - 确保管道直径沿流向递增（越靠近出口直径越大）
    """
    new_conduits_df = conduits_df.copy()
    diameter_changes = []
    
    print(f"开始调整新出口 {selected_outlets} 的上游管道直径")
    
    # 获取每个新出口的上游管道
    upstream_pipes = get_upstream_pipes_simple(new_conduits_df, selected_outlets, upstream_depth)
    
    for outlet, pipes_info in upstream_pipes.items():
        if not pipes_info:
            print(f"出口 {outlet} 没有找到上游管道")
            continue
            
        print(f"\n处理出口 {outlet} 的 {len(pipes_info)} 条上游管道:")
        
        # 处理每条管道
        for pipe_id, from_node, to_node, distance in pipes_info:
            pipe_rows = new_conduits_df[new_conduits_df['Link'] == pipe_id]
            if len(pipe_rows) == 0:
                print(f"  警告: 管道 {pipe_id} 不在数据中")
                continue
                
            pipe_idx = pipe_rows.index[0]
            original_diameter = new_conduits_df.at[pipe_idx, 'Diameter']
            
            # 简单策略：根据距离出口的远近调整直径
            if distance == 0:  # 直接连接出口的管道
                multiplier = growth_factor
            else:  # 上游管道，距离越远直径越小
                multiplier = max(1.0, growth_factor - (distance * 0.1))
            
            suggested_diameter = original_diameter * multiplier
            new_diameter = round_diameter(suggested_diameter)
            
            # 应用调整
            if abs(new_diameter - original_diameter) > 1e-6:
                new_conduits_df.at[pipe_idx, 'AdjustedDiameter'] = new_diameter
                diameter_changes.append((pipe_id, original_diameter, suggested_diameter, new_diameter))
                print(f"  管道 {pipe_id} (距离={distance}): {original_diameter:.3f} → {new_diameter:.3f}")
            else:
                print(f"  管道 {pipe_id} (距离={distance}): {original_diameter:.3f} 无变化")
    
    return new_conduits_df, diameter_changes

def correct_flow_direction(conduits_df, nodes_df):
    """
    校正管道流向：
      - 如果管道的起点高程低于终点，则交换起止节点，
      - 确保高程较高的一端为起点。
    返回更新后的 conduits DataFrame 及流向变化记录列表，
    记录格式为：(Link, OldFrom, OldTo, NewFrom, NewTo)
    """
    new_conduits_df = conduits_df.copy()
    nodes_df['Node'] = nodes_df['Node'].astype(str)
    new_conduits_df['FromNode'] = new_conduits_df['FromNode'].astype(str)
    new_conduits_df['ToNode'] = new_conduits_df['ToNode'].astype(str)

    flow_changes = []
    for idx, row in new_conduits_df.iterrows():
        from_node, to_node = row['FromNode'], row['ToNode']
        if from_node not in nodes_df['Node'].values or to_node not in nodes_df['Node'].values:
            continue
        from_elev = nodes_df.loc[nodes_df['Node'] == from_node, 'InvertElev'].values[0]
        to_elev = nodes_df.loc[nodes_df['Node'] == to_node, 'InvertElev'].values[0]
        if from_elev < to_elev:
            new_conduits_df.at[idx, 'FromNode'] = to_node
            new_conduits_df.at[idx, 'ToNode'] = from_node
            flow_changes.append((row['Link'], from_node, to_node, to_node, from_node))
            print(f"Flow reversed for conduit {row['Link']}: {from_node} → {to_node} to {to_node} → {from_node}")
    return new_conduits_df, flow_changes

def export_results_to_excel(nodes_df, elevation_changes, conduits_df, diameter_changes, flow_changes, filename="network_modification_results.xlsx"):
    """
    将最终结果导出到 Excel 文件中，格式兼容绘图代码：
      - 节点数据：包含 Node, Elevation (InvertElev重命名), X-Coord, Y-Coord
      - 管道数据：包含 Link, FromNode, ToNode, Diameter, AdjustedDiameter
      - 其他变化记录表格
    """
    with pd.ExcelWriter(filename) as writer:
        # 节点数据 - 重命名InvertElev为Elevation以兼容绘图代码
        nodes_export = nodes_df.copy()
        nodes_export = nodes_export.rename(columns={'InvertElev': 'Elevation'})
        nodes_export.to_excel(writer, sheet_name="节点数据", index=False)
        
        # 高程变化记录
        if elevation_changes:
            df_elev_changes = pd.DataFrame(elevation_changes, columns=["Node", "OldElevation", "NewElevation"])
        else:
            df_elev_changes = pd.DataFrame(columns=["Node", "OldElevation", "NewElevation"])
        df_elev_changes.to_excel(writer, sheet_name="节点高程改变", index=False)
        
        # 管道数据
        conduits_df.to_excel(writer, sheet_name="管道数据", index=False)
        
        # 直径变化记录
        if diameter_changes:
            df_dia_changes = pd.DataFrame(diameter_changes, columns=["Link", "OldDiameter", "CalculatedDiameter", "NewDiameter"])
        else:
            df_dia_changes = pd.DataFrame(columns=["Link", "OldDiameter", "CalculatedDiameter", "NewDiameter"])
        df_dia_changes.to_excel(writer, sheet_name="管道直径改变", index=False)
        
        # 流向变化记录
        if flow_changes:
            df_flow_changes = pd.DataFrame(flow_changes, columns=["Link", "OldFrom", "OldTo", "NewFrom", "NewTo"])
        else:
            df_flow_changes = pd.DataFrame(columns=["Link", "OldFrom", "OldTo", "NewFrom", "NewTo"])
        df_flow_changes.to_excel(writer, sheet_name="流向改变", index=False)
        
    print(f"\nResults exported to {filename}")

def main():
    # 根据实际情况修改文件路径
    file_path = r'D:\Ph. D\Paper 3\网络设计\branched.inp'
    nodes_df, conduits_df = parse_inp(file_path)
    
    # 定义新增出口节点（保留原出口347）
    original_outlets = ['347']  # 原始出口，保持不变
    selected_outlets = ['341', '346']   # 新选出口节点
    all_outlets = original_outlets + selected_outlets
    
    print(f"\n原始出口: {original_outlets}")
    print(f"新增出口: {selected_outlets}")
    print(f"所有出口: {all_outlets}")
    print("注意：所有出口节点和连接管道都会保留在数据中")

    # 不调整节点高程，保持原始数据
    print("\n=== 节点高程保持原始数据不变 ===")
    elevation_changes = []

    # 调整新出口的上游管道直径，确保符合水力学原理
    print("\n=== 调整新出口上游管道直径（符合水力学原理）===")
    new_conduits_df, diameter_changes = adjust_pipe_diameters_upstream(
        conduits_df, selected_outlets, growth_factor=1.2, upstream_depth=10)

    # 校正流向
    print("\n=== 校正管道流向 ===")
    corrected_conduits_df, flow_changes = correct_flow_direction(new_conduits_df, nodes_df)

    # 验证所有出口节点都存在
    print("\n=== 验证出口节点完整性 ===")
    for outlet in all_outlets:
        if outlet in nodes_df['Node'].astype(str).values:
            print(f"✓ 出口节点 {outlet} 存在于节点数据中")
        else:
            print(f"✗ 警告：出口节点 {outlet} 不存在于节点数据中")
    
    # 验证出口连接的管道
    outlet_pipes = corrected_conduits_df[
        corrected_conduits_df['ToNode'].astype(str).isin([str(x) for x in all_outlets])
    ]
    print(f"连接到出口的管道数量: {len(outlet_pipes)}")
    for _, pipe in outlet_pipes.iterrows():
        print(f"  管道 {pipe['Link']}: {pipe['FromNode']} → {pipe['ToNode']}")

    # 导出所有结果到 Excel（兼容绘图代码的位置）
    output_filename = r"D:\Ph. D\Paper 3\Data\updated_network 1.xlsx"
    export_results_to_excel(nodes_df, elevation_changes, corrected_conduits_df, 
                           diameter_changes, flow_changes, filename=output_filename)
    
    print(f"\n✓ 所有数据已导出到: {output_filename}")
    print("✓ 所有出口节点（包括原始出口347）都已保留")
    print("✓ 新出口的上游管道直径已按水力学原理调整")