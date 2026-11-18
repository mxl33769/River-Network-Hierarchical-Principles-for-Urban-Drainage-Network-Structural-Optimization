"""
Created on July 16, 18:42:35 2024

@author: Xiliang Mao, Qiong Zhang
"""




import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from swmm_api import read_inp_file
import networkx as nx

# 使用原始字符串表示文件路径
inp_file_path = r'D:\Ph. D\Task-2\Data\Project 0\branched.inp'
output_excel_path = r'D:\Ph. D\Task-2\Data\Project 0\node_subcatchment_areas.xlsx'

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
subcatchment_areas = {}  # 用于存储每个 subcatchment 的面积
if "POLYGONS" in inp.keys():
    for subcatchment, attributes in inp["SUBCATCHMENTS"]._data.items():
        polygon = inp["POLYGONS"]._data.get(subcatchment)
        if polygon:
            first_point = polygon.polygon[0]
            x_coord = first_point[0]
            y_coord = first_point[1]
            attributes_dict = attributes.__dict__
            G.add_node(subcatchment, pos=(x_coord, y_coord), **attributes_dict)
            subcatchment_areas[subcatchment] = attributes.area

            # 连接 SUBCATCHMENTS 与它们的 outlet
            outlet = attributes.outlet
            if outlet in G:
                G.add_edge(subcatchment, outlet)

# 添加 CONDUITS 连接并附加属性
for conduit, attributes in inp["CONDUITS"]._data.items():
    inlet_node = attributes.get('from_node') or attributes.get('inlet_node') or attributes.get('inlet')
    outlet_node = attributes.get('to_node') or attributes.get('outlet_node') or attributes.get('outlet')
    if inlet_node in G and outlet_node in G:
        attributes_dict = attributes.__dict__
        G.add_edge(inlet_node, outlet_node, **attributes_dict)

# 查找流向目标节点的所有 subcatchment，并计算总面积
def find_subcatchments_and_total_area(graph, target_node, subcatchment_areas):
    total_area = 0.0
    subcatchments = []

    # 反向遍历节点以查找所有流向目标节点的 subcatchment
    for node in nx.dfs_predecessors(graph.reverse(), target_node):
        if node in subcatchment_areas:
            subcatchments.append(node)
            total_area += subcatchment_areas[node]

    return subcatchments, total_area

# 查找流向每个节点的所有 subcatchment，并将流向每个节点的 subcatchment 的 'Area' 相加
node_subcatchment_areas = {}
for node in G.nodes:
    subcatchments, total_area = find_subcatchments_and_total_area(G, node, subcatchment_areas)
    node_subcatchment_areas[node] = total_area

# 将数据存储到 DataFrame 中
df = pd.DataFrame(list(node_subcatchment_areas.items()), columns=["Node", "Total Subcatchment Area"])

# 将 DataFrame 输出为 Excel 文件
df.to_excel(output_excel_path, index=False)
print(f"Data has been written to {output_excel_path}")

# 筛选非零面积，并找到最大值和最小值
non_zero_df = df[df['Total Subcatchment Area'] > 0]
max_area = non_zero_df['Total Subcatchment Area'].max()
min_area = non_zero_df['Total Subcatchment Area'].min()

# 计算 P(A >= delta) for delta in the range [min_area, max_area]
delta_values = np.linspace(min_area, max_area, 100)
p_values = []
a = 0.95

for delta in delta_values:
    p = (non_zero_df['Total Subcatchment Area'] >= delta).sum() / len(non_zero_df)
    p_values.append(p)

p_values = np.array(p_values)

# 定义拟合函数
def model(delta, epsilon, c):
    return a * delta**(-epsilon) * np.exp(-c * delta)

# 初始猜测值
initial_guess = [1, 1]

# 拟合参数
params, covariance = curve_fit(model, delta_values, p_values, p0=initial_guess)
epsilon, c = params

print(f"Calculated ε: {epsilon}")
print(f"Calculated c: {c}")

# 绘制拟合曲线
plt.scatter(delta_values, p_values, label='Data')
plt.plot(delta_values, model(delta_values, epsilon, c), color='red', label=f'Fitted curve: ε={epsilon:.2f}, c={c:.2f}')
plt.xlabel('δ')
plt.ylabel('P(A ≥ δ)')
plt.title('Pareto Distribution')

# 翻转y轴和x轴
plt.gca().invert_yaxis()
plt.gca().invert_xaxis()

# 调整图例位置
plt.legend(loc='lower right')

plt.show()

