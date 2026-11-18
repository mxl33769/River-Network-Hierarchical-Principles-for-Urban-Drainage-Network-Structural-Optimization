# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 17:07:27 2025

@author: mxl33
"""

import re
import pandas as pd

# Function to parse the .inp file and extract node data
def parse_inp_for_nodes(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Extract node data from the [JUNCTIONS] section
    node_data = []
    in_junction_section = False
    for line in lines:
        if line.startswith('[JUNCTIONS]'):
            in_junction_section = True
            continue
        if in_junction_section and line.startswith('['):
            break
        if in_junction_section and not line.startswith(';') and line.strip():
            parts = re.split(r'\s+', line.strip())
            node_id = parts[0]
            invert_elev = float(parts[1])
            node_data.append((node_id, invert_elev))
    
    return pd.DataFrame(node_data, columns=['Node', 'InvertElev'])

# Load and parse the .inp file
file_path = r'D:\Ph. D\Paper 3\网络设计\branched.inp'  # Replace with your actual file path
nodes_df = parse_inp_for_nodes(file_path)

# Find the global natural lowest point in the network
lowest_point = nodes_df.loc[nodes_df['InvertElev'].idxmin()]

# Output the results
print("All Nodes Data:")
print(nodes_df)
print("\nNatural Lowest Point in the Network:")
print(lowest_point)
