# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 17:40:19 2025

@author: mxl33
"""

import re
import pandas as pd
import random
import time  # For dynamic seed

# Function to parse the .inp file and extract node and conduit data
def parse_inp(file_path):
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
    
    # Extract conduit data from the [CONDUITS] section
    conduit_data = []
    in_conduit_section = False
    for line in lines:
        if line.startswith('[CONDUITS]'):
            in_conduit_section = True
            continue
        if in_conduit_section and line.startswith('['):
            break
        if in_conduit_section and not line.startswith(';') and line.strip():
            parts = re.split(r'\s+', line.strip())
            from_node = parts[1]
            to_node = parts[2]
            conduit_data.append((from_node, to_node))
    
    return (
        pd.DataFrame(node_data, columns=['Node', 'InvertElev']),
        pd.DataFrame(conduit_data, columns=['FromNode', 'ToNode'])
    )

# Function to calculate the global lowest elevation
def calculate_global_lowest_elevation(nodes_df):
    if 'Node' not in nodes_df.columns:
        nodes_df = nodes_df.reset_index()
    lowest_elevation = nodes_df['InvertElev'].min()
    lowest_node = nodes_df.loc[nodes_df['InvertElev'].idxmin(), 'Node']
    print(f"\nGlobal lowest elevation: {lowest_elevation} (Node: {lowest_node})")
    return lowest_elevation

# Adjust elevations with global lowest elevation
def adjust_elevations_with_global_min(nodes_df, conduits_df, candidate_nodes, selected_nodes, slope=0.005):
    nodes_df = nodes_df.copy()
    nodes_df.set_index('Node', inplace=True)
    nodes_df['Modified'] = False

    # Calculate the global lowest elevation
    global_lowest_elevation = calculate_global_lowest_elevation(nodes_df)

    for selected_node in selected_nodes:
        if selected_node not in nodes_df.index:
            print(f"Warning: Node {selected_node} not found in nodes_df!")
            continue

        # Set selected node elevation to the global lowest elevation
        nodes_df.at[selected_node, 'InvertElev'] = global_lowest_elevation
        nodes_df.at[selected_node, 'Modified'] = True
        print(f"\nSetting {selected_node} elevation to global lowest elevation: {global_lowest_elevation}")

        # Adjust downstream nodes
        to_process = [selected_node]
        visited = set()
        while to_process:
            current_node = to_process.pop(0)
            if current_node in visited:
                continue
            visited.add(current_node)

            downstream_nodes = conduits_df[conduits_df['FromNode'] == current_node]['ToNode']
            if downstream_nodes.empty:
                print(f"No downstream nodes for {current_node}.")
                continue

            for downstream_node in downstream_nodes:
                if downstream_node not in nodes_df.index:
                    print(f"Info: Downstream node {downstream_node} is likely an outlet and not in nodes_df.")
                    continue

                downstream_elevation = nodes_df.at[downstream_node, 'InvertElev']
                current_elevation = nodes_df.at[current_node, 'InvertElev']

                new_elevation = current_elevation - slope
                if new_elevation < downstream_elevation:
                    print(f"Adjusting {downstream_node} from {downstream_elevation} to {new_elevation}")
                    nodes_df.at[downstream_node, 'InvertElev'] = new_elevation
                    nodes_df.at[downstream_node, 'Modified'] = True

                to_process.append(downstream_node)

    return nodes_df.reset_index()

if __name__ == "__main__":
    # Load and parse the .inp file
    file_path = r'D:\Ph. D\Paper 3\网络设计\branched.inp'  # Replace with your actual file path
    nodes_df, conduits_df = parse_inp(file_path)

    # Candidate nodes
    candidate_nodes = ['341', '342', '343', '344', '345', '346', '348', '349', '350']

    # Dynamic seed for random selection
    random.seed(time.time())  # Set a dynamic seed
    selected_nodes = random.sample(candidate_nodes, random.randint(1, len(candidate_nodes)))

    print("\nSelected Nodes for Adjustment:", selected_nodes)

    # Adjust elevations with global lowest elevation
    adjusted_nodes_df = adjust_elevations_with_global_min(nodes_df, conduits_df, candidate_nodes, selected_nodes)

    # Output results
    print("\nAdjusted Node Elevations (with changes marked):")
    print(adjusted_nodes_df)










