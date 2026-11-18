# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 15:39:59 2025

@author: mxl33
"""

import re
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# 解析 INP 文件
def parse_inp(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    node_data, conduit_data, diameter_data = [], [], []
    in_junction_section, in_conduit_section, in_xsections_section = False, False, False

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

    nodes_df = pd.DataFrame(node_data, columns=['Node', 'InvertElev'])
    conduits_df = pd.DataFrame(conduit_data, columns=['Link', 'FromNode', 'ToNode'])
    diameters_df = pd.DataFrame(diameter_data, columns=['Link', 'Diameter'])

    conduits_df = pd.merge(conduits_df, diameters_df, on='Link', how='left')
    conduits_df['AdjustedDiameter'] = conduits_df['Diameter']

    return nodes_df, conduits_df

# 获取最低自然高程
def get_lowest_natural_elevation(nodes_df):
    min_elevation = nodes_df[nodes_df['InvertElev'] > 0]['InvertElev'].min()
    print(f"\nLowest Natural Elevation: {min_elevation:.3f}")
    return min_elevation

# 传播式调整高程（BFS）
def adjust_node_elevations_with_propagation(nodes_df, conduits_df, selected_nodes, min_slope=0.005):
    nodes_df = nodes_df.copy()
    min_elevation = get_lowest_natural_elevation(nodes_df)
    elevation_changes = []
    queue = selected_nodes[:]

    for node in selected_nodes:
        if node in nodes_df['Node'].values:
            old_elev = nodes_df.loc[nodes_df['Node'] == node, 'InvertElev'].values[0]
            nodes_df.loc[nodes_df['Node'] == node, 'InvertElev'] = min_elevation
            elevation_changes.append((node, old_elev, min_elevation))

    while queue:
        current_node = queue.pop(0)
        current_elev = nodes_df.loc[nodes_df['Node'] == current_node, 'InvertElev'].values[0]
        downstream_nodes = conduits_df[conduits_df['FromNode'] == current_node]['ToNode'].values

        for downstream in downstream_nodes:
            if downstream in nodes_df['Node'].values:
                old_downstream_elev = nodes_df.loc[nodes_df['Node'] == downstream, 'InvertElev'].values[0]
                new_elev = max(min_elevation, current_elev + min_slope)

                if old_downstream_elev > new_elev:
                    nodes_df.loc[nodes_df['Node'] == downstream, 'InvertElev'] = new_elev
                    elevation_changes.append((downstream, old_downstream_elev, new_elev))
                    queue.append(downstream)

    print("\nModified Node Elevations:")
    for change in elevation_changes:
        print(f"Node {change[0]}: {change[1]:.3f} → {change[2]:.3f}")

    return nodes_df, elevation_changes

# 仅调整受影响管道直径
def adjust_pipe_diameters(conduits_df, affected_nodes, growth_factor=1.2):
    conduits_df = conduits_df.copy()
    diameter_changes = []

    for idx, row in conduits_df.iterrows():
        from_node, to_node = row['FromNode'], row['ToNode']

        if from_node in affected_nodes or to_node in affected_nodes:
            old_diameter = row['Diameter']
            new_diameter = old_diameter * growth_factor
            conduits_df.at[idx, 'AdjustedDiameter'] = new_diameter
            diameter_changes.append((row['Link'], old_diameter, new_diameter))

    print("\nModified Conduit Diameters:")
    for change in diameter_changes:
        print(f"Conduit {change[0]}: {change[1]:.3f} → {change[2]:.3f}")

    return conduits_df

# 确保流向正确
def correct_flow_direction(conduits_df, nodes_df):
    conduits_df = conduits_df.copy()
    nodes_df['Node'] = nodes_df['Node'].astype(str)
    conduits_df['FromNode'] = conduits_df['FromNode'].astype(str)
    conduits_df['ToNode'] = conduits_df['ToNode'].astype(str)

    for idx, row in conduits_df.iterrows():
        from_node, to_node = row['FromNode'], row['ToNode']

        if from_node not in nodes_df['Node'].values or to_node not in nodes_df['Node'].values:
            print(f"Skipping conduit {row['Link']}: {from_node} → {to_node} (one of the nodes is missing)")
            continue

        from_elev = nodes_df.loc[nodes_df['Node'] == from_node, 'InvertElev'].values[0]
        to_elev = nodes_df.loc[nodes_df['Node'] == to_node, 'InvertElev'].values[0]

        if from_elev < to_elev:
            conduits_df.at[idx, 'FromNode'], conduits_df.at[idx, 'ToNode'] = to_node, from_node
            print(f"Flow reversed: {row['Link']} ({from_node} → {to_node}) → ({to_node} → {from_node})")

    return conduits_df

# 主程序
if __name__ == "__main__":
    file_path = r'D:\Ph. D\Paper 3\网络设计\branched.inp'
    nodes_df, conduits_df = parse_inp(file_path)

    selected_outlets = ['341', '346']
    print(f"\nSelected Nodes as Outlets: {selected_outlets}")

    nodes_df, elevation_changes = adjust_node_elevations_with_propagation(nodes_df, conduits_df, selected_outlets, min_slope=0.005)
    affected_nodes = [node[0] for node in elevation_changes]

    adjusted_conduits_df = adjust_pipe_diameters(conduits_df, affected_nodes, growth_factor=1.2)
    corrected_conduits_df = correct_flow_direction(adjusted_conduits_df, nodes_df)


