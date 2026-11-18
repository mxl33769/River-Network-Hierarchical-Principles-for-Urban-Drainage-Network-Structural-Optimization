import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from swmm_api import read_inp_file
import networkx as nx
import os

# 使用原始字符串表示文件路径
inp_file_path = r'D:\\Ph. D\\Task-2\\Data\\Project 0\\branched.inp'
edge_orders_output_path = r'D:\\Ph. D\\Task-2\\Data\\Project 0\\edge_orders.xlsx'
order_counts_output_path = r'D:\\Ph. D\\Task-2\\Data\\Project 0\\order_counts.xlsx'
rb_output_file_path = r'D:\\Ph. D\\Task-2\\Data\\Project 0\\rb_values.txt'

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

# 添加 CONDUITS 连接并附加属性
for conduit, attributes in inp["CONDUITS"]._data.items():
    inlet_node = attributes.get('from_node') or attributes.get('inlet_node') or attributes.get('inlet')
    outlet_node = attributes.get('to_node') or attributes.get('outlet_node') or attributes.get('outlet')
    if inlet_node in G and outlet_node in G:
        attributes_dict = attributes.__dict__
        G.add_edge(inlet_node, outlet_node, **attributes_dict)

# 获取节点位置
pos = nx.get_node_attributes(G, 'pos')

# 找到网络中的所有终点节点（没有任何出边的节点）
end_nodes = [node for node, out_degree in G.out_degree() if out_degree == 0]
print(f"End nodes: {end_nodes}")

# 初始化边顺序为0
edge_orders = {edge: 0 for edge in G.edges()}

# 定义 Strahler 方法
def mark_edges_strahler(graph, node):
    if graph.out_degree(node) == 0:  # 外部链接，顺序为1
        return 1
    else:
        orders = []
        for u, v in graph.out_edges(node):
            if (u, v) not in edge_orders or edge_orders[(u, v)] == 0:  # 如果尚未标记
                edge_orders[(u, v)] = mark_edges_strahler(graph, v)
            orders.append(edge_orders[(u, v)])
        
        max_order = max(orders)
        if orders.count(max_order) > 1:
            return max_order + 1
        else:
            return max_order

# 从所有终点开始标记边的顺序
for end_node in end_nodes:
    mark_edges_strahler(G.reverse(), end_node)

# 将边的顺序信息导出到Excel表格
edge_orders_df = pd.DataFrame.from_dict(edge_orders, orient='index', columns=['Order'])
edge_orders_df.index = pd.MultiIndex.from_tuples(edge_orders_df.index, names=['From Node', 'To Node'])
edge_orders_df.to_excel(edge_orders_output_path)

print("Edge orders have been exported to edge_orders.xlsx.")

# 读取包含列名的 Excel 文件
edge_orders_df = pd.read_excel(edge_orders_output_path, index_col=[0, 1])

# 定义颜色映射
color_map = {
    1: 'green',
    2: 'blue',
    3: 'orange',
    4: 'purple',
    5: 'red'
}

# 创建一个新的图形
plt.figure(figsize=(12, 12))

# 获取边和它们的顺序
edges_of_order = [(u, v, row['Order']) for (u, v), row in edge_orders_df.iterrows()]

# 计算并打印每个顺序的边数
order_counts = {}
for _, _, order in edges_of_order:
    if order in order_counts:
        order_counts[order] += 1
    else:
        order_counts[order] = 1

# 将结果存储到 DataFrame
order_counts_df = pd.DataFrame(list(order_counts.items()), columns=['Order', 'Count'])
order_counts_df.to_excel(order_counts_output_path, index=False)

for order, count in order_counts.items():
    print(f"{order}: {count} edges")

# 读取存储的 order counts 文件
order_counts_df = pd.read_excel(order_counts_output_path)

# 过滤出整数顺序值并忽略Order 0
sorted_orders = sorted([o for o in order_counts_df['Order'] if isinstance(o, int) and o != 0])

# 计算每个相邻order的Rb值
rb_values = []
rb_output_text = ""
for i in range(len(sorted_orders) - 1):
    nr = order_counts_df.loc[order_counts_df['Order'] == sorted_orders[i], 'Count'].values[0]
    nr_plus_1 = order_counts_df.loc[order_counts_df['Order'] == sorted_orders[i + 1], 'Count'].values[0]
    rb = nr / nr_plus_1
    rb_values.append(rb)
    rb_output_text += f"Rb between Order {sorted_orders[i]} and Order {sorted_orders[i + 1]}: {rb:.2f}\n"
    print(f"Calculated Rb between Order {sorted_orders[i]} and Order {sorted_orders[i + 1]}: {rb}")

# 计算整个网络的平均Rb值
if rb_values:
    avg_rb = sum(rb_values) / len(rb_values)
    rb_output_text += f"Average Rb for the network: {avg_rb:.2f}\n"
    print(f"Average Rb for the network: {avg_rb}")

# 将 Rb 值写入 TXT 文件
with open(rb_output_file_path, 'w') as f:
    f.write(rb_output_text)

print(f"Rb values have been written to {rb_output_file_path}")

# 获取节点位置
pos = nx.get_node_attributes(G, 'pos')

# 绘制节点
nx.draw_networkx_nodes(G, pos, node_size=50)

# 绘制每个顺序的边
for order, color in color_map.items():
    edges = [(u, v) for u, v, ord in edges_of_order if ord == order]
    nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color=color, label=f'Order {order}', arrows=False)

# 手动创建图例
legend_elements = [Line2D([0], [0], color=color, lw=2, label=f'Order {order}') for order, color in color_map.items()]
plt.legend(handles=legend_elements)

# 在图上添加平均 Rb 值
plt.text(0.05, 0.95, f'Average Rb for the network: {avg_rb:.2f}', transform=plt.gca().transAxes,
         fontsize=12, verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))

plt.title('Graph with Edges Colored by Order')
plt.show()