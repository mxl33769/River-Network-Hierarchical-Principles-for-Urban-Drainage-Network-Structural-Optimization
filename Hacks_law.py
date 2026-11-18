"""
Created on July 09, 05:55:21 2024

@author: Xiliang Mao, Qiong Zhang
"""




import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from swmm_api import read_inp_file
import networkx as nx
import os

# 使用原始字符串表示文件路径
inp_file_path = r'D:\Ph. D\Task-2\Data\Project 0\branched.inp'
output_file_path = r'D:\Ph. D\Task-2\Data\Project 0\subcatchments_and_conduits_summary.xlsx'

# 读取 inp 文件
inp = read_inp_file(inp_file_path)

# 创建 NetworkX 图
G = nx.DiGraph()

# 添加 JUNCTIONS 节点并附加属性
for node, attributes in inp["JUNCTIONS"]._data.items():
    coord = inp["COORDINATES"]._data.get(node)
    if coord:
        attributes_dict = attributes.__dict__
        G.add_node(node, pos=(coord['x'], coord['y']), **attributes_dict)

# 添加 OUTFALLS 节点并附加属性
for node, attributes in inp["OUTFALLS"]._data.items():
    coord = inp["COORDINATES"]._data.get(node)
    if coord:
        attributes_dict = attributes.__dict__
        G.add_node(node, pos=(coord['x'], coord['y']), **attributes_dict)

# 添加 SUBCATCHMENTS 节点并附加属性
subcatchments_total_area = 0
subcatchment_areas = {}
if "POLYGONS" in inp.keys():
    for subcatchment, attributes in inp["SUBCATCHMENTS"]._data.items():
        polygon = inp["POLYGONS"]._data.get(subcatchment)
        if polygon:
            first_point = polygon.polygon[0]
            x_coord = first_point[0]
            y_coord = first_point[1]
            attributes_dict = attributes.__dict__
            G.add_node(subcatchment, pos=(x_coord, y_coord), **attributes_dict)

            # 连接 SUBCATCHMENTS 与它们的 outlet
            outlet = attributes.outlet
            if outlet in G:
                G.add_edge(subcatchment, outlet)

            # 累加 subcatchments 的总面积
            subcatchments_total_area += attributes.area
            subcatchment_areas[subcatchment] = attributes.area

else:
    print("No 'POLYGONS' section found in the inp file.")

# 添加 CONDUITS 连接并附加属性
conduits_total_length = 0
for conduit, attributes in inp["CONDUITS"]._data.items():
    inlet_node = attributes.get('from_node') or attributes.get('inlet_node') or attributes.get('inlet')
    outlet_node = attributes.get('to_node') or attributes.get('outlet_node') or attributes.get('outlet')
    if inlet_node in G and outlet_node in G:
        attributes_dict = attributes.__dict__
        G.add_edge(inlet_node, outlet_node, **attributes_dict)

        # 累加 conduits 的总长度
        conduits_total_length += attributes.length

# 获取出水口节点列表
outfalls = list(inp["OUTFALLS"]._data.keys())

# 计算每个节点到所有出水口的最短路径长度和路径
shortest_paths = {}
for node in G.nodes:
    shortest_path_length = float('inf')
    best_path = None
    for outfall in outfalls:
        try:
            path = nx.shortest_path(G, source=node, target=outfall, weight='length')
            path_length = nx.shortest_path_length(G, source=node, target=outfall, weight='length')
            if path_length < shortest_path_length:
                shortest_path_length = path_length
                best_path = path
        except nx.NetworkXNoPath:
            continue
    if shortest_path_length < float('inf'):
        shortest_paths[node] = (shortest_path_length, best_path)

# 提取与 subcatchment 连接的节点
subcatchment_paths = {subcatchment: shortest_paths[subcatchment] for subcatchment in inp["SUBCATCHMENTS"]._data.keys() if subcatchment in shortest_paths}

# 准备数据导出到 Excel
data = []
for subcatchment, (length, path) in subcatchment_paths.items():
    path_str = " -> ".join(path)
    area = subcatchment_areas.get(subcatchment, 'N/A')
    data.append([subcatchment, area, length, path_str])

# 总结信息
summary_data = {
    "Total Subcatchment Area": [subcatchments_total_area],
    "Total Conduit Length": [conduits_total_length]
}

# 将结果导出为 Excel 文件
df = pd.DataFrame(data, columns=['Subcatchment', 'Area', 'Shortest Path Length to Outfall', 'Path'])
summary_df = pd.DataFrame(summary_data)

with pd.ExcelWriter(output_file_path) as writer:
    df.to_excel(writer, sheet_name='Paths', index=False)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

# 检查文件是否生成
if os.path.exists(output_file_path):
    print(f"Results have been saved to '{output_file_path}'")
else:
    print(f"Failed to save the file to '{output_file_path}'")

# Load the data from the Excel file for further analysis
data = pd.read_excel(output_file_path, sheet_name='Paths')

# Extract the relevant columns
areas_ac = data['Area'].values
lengths_ft = data['Shortest Path Length to Outfall'].values

# Convert area from acres to square feet
areas_ft2 = areas_ac * 43560

# Define the model function
def model(a, h):
    return a**h

# Perform the curve fitting
params, _ = curve_fit(model, areas_ft2, lengths_ft)
h = params[0]

# Print the result
print(f"Calculated h: {h}")

# Plot the data points
plt.scatter(areas_ft2, lengths_ft, label='Data Points')

# Plot the fitted curve
areas_range = np.linspace(min(areas_ft2), max(areas_ft2), 100)
fitted_lengths = model(areas_range, h)
plt.plot(areas_range, fitted_lengths, color='red', label=f'Fitted Curve: $h = {h:.2f}$')

# Add labels and title
plt.xlabel('Area (ft²)')
plt.ylabel('Length (ft)')
plt.title("Hack's Law")
plt.legend()

# Annotate data points
for i, txt in enumerate(data['Subcatchment']):
    plt.annotate(txt, (areas_ft2[i], lengths_ft[i]), fontsize=8)

# Show the plot
plt.show()













