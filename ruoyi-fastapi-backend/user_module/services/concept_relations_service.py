# -*- coding: utf-8 -*-
import pandas as pd
import os
from collections import defaultdict

def build_parent_child_model_from_excel(file_path, min_overlap=0.4, max_overlap=1.0):
    """
    从Excel文件构建父子关系模型，支持overlap过滤
    参数:
    file_path: Excel文件路径
    min_overlap: 最小重叠度阈值 (0.0-1.0)
    max_overlap: 最大重叠度阈值 (0.0-1.0)
    返回:
    包含节点信息和关系的字典
    """
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    required_columns = ['parent', 'parent_name', 'parent_size',
                        'child', 'child_name', 'child_size',
                        'cluster_id', 'overlap']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Excel文件中缺少必需的列: {col}")
    filtered_df = df[(df['overlap'] >= min_overlap) & (df['overlap'] <= max_overlap)]
    parent_to_children = defaultdict(list)
    child_to_parents = defaultdict(list)
    node_info = {}
    for _, row in filtered_df.iterrows():
        parent = row['parent']
        child = row['child']
        node_info[parent] = {'name': row['parent_name'], 'size': row['parent_size']}
        node_info[child] = {'name': row['child_name'], 'size': row['child_size']}
        parent_to_children[parent].append({
            'child': child,
            'overlap': row['overlap']
        })
        child_to_parents[child].append({
            'parent': parent,
            'overlap': row['overlap']
        })
    root_nodes = [node for node in node_info if node not in child_to_parents]
    return {
        'node_info': node_info,
        'parent_to_children': dict(parent_to_children),
        'child_to_parents': dict(child_to_parents),
        'root_nodes': root_nodes,
        'min_overlap': min_overlap,
        'max_overlap': max_overlap
    }

def analyze_overlap_distribution(model):
    """分析overlap分布情况"""
    all_overlaps = []
    for parent, children in model['parent_to_children'].items():
        for child in children:
            all_overlaps.append(child['overlap'])
    if not all_overlaps:
        return None
    min_val = min(all_overlaps)
    max_val = max(all_overlaps)
    mean_val = sum(all_overlaps) / len(all_overlaps)
    sorted_overlaps = sorted(all_overlaps)
    median_val = sorted_overlaps[len(sorted_overlaps) // 2]
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    hist = [0] * (len(bins) - 1)
    for val in all_overlaps:
        for i in range(len(bins) - 1):
            if bins[i] <= val < bins[i + 1]:
                hist[i] += 1
                break
    return {
        'min': min_val,
        'max': max_val,
        'mean': mean_val,
        'median': median_val,
        'hist': hist,
        'bins': bins,
        'total': len(all_overlaps)
    }

def get_concept_model(min_overlap=0.4, max_overlap=1.0):
    """
    获取概念父子关系模型，适配本项目路径
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, '../analyzer/concept_parent_child_relations.xlsx')
    return build_parent_child_model_from_excel(excel_path, min_overlap, max_overlap)

# 其他分析、可视化等函数可根据需要添加 