# -*- coding: utf-8 -*-
"""
experience_graph.py — v1.3 小世界拓扑引擎

将经验库从扁平列表重构为图结构，支持：
  - 社区检测（功能模块聚类）
  - 捷径发现（跨社区桥梁经验）
  - 拓扑排序检索（社区内优先→捷径扩展→跨社区）
  - 指标度量（聚类系数、捷径比例、社区结构）

依赖: semantic_search (字n-gram TF-IDF)
"""

import json
import os
import math
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime

from semantic_search import SemanticSearch, _char_ngrams, _l2_normalize, _cosine_similarity, _build_search_text


# ── 配置 ──
COMMUNITY_SIM_THRESHOLD = 0.15    # 社区内边最小相似度
SHORTCUT_PERCENTILE = 0.03        # 长程捷径比例 (top 3%)
MIN_COMMUNITY_SIZE = 2            # 最小社区大小


# ── 图数据结构 ──

class ExperienceNode:
    """经验节点"""
    __slots__ = ('filename', 'tool_name', 'error_type', 'error_message',
                 'action', 'success', 'community', 'is_shortcut', 'degree')
    
    def __init__(self, filename: str, tool_name: str = '', error_type: str = '',
                 error_message: str = '', action: str = '', success: bool = True):
        self.filename = filename
        self.tool_name = tool_name
        self.error_type = error_type
        self.error_message = error_message
        self.action = action
        self.success = success
        self.community: int = -1    # 社区ID
        self.is_shortcut: bool = False
        self.degree: int = 0


class ExperienceGraph:
    """小世界经验网络
    
    用法:
        eg = ExperienceGraph()
        eg.build("experience_store")
        print(eg.get_stats())
        results = eg.topo_search("读取CSV文件")
    """
    
    def __init__(self, sim_threshold: float = COMMUNITY_SIM_THRESHOLD):
        self.sim_threshold = sim_threshold
        self._nodes: Dict[str, ExperienceNode] = {}     # filename -> node
        self._edges: List[Tuple[str, str, float]] = []  # (f1, f2, weight)
        self._adj: Dict[str, List[Tuple[str, float]]] = defaultdict(list)  # adjacency list
        self._community_count: int = 0
        self._shortcut_edges: List[Tuple[str, str, float]] = []
        self._built = False
        
        # 语义检索引擎（复用）
        self._ss = SemanticSearch()
    
    def build(self, store_path: str) -> int:
        """从经验库构建小世界网络，返回节点数"""
        base = os.path.dirname(os.path.abspath(__file__))
        store_dir = store_path if os.path.isabs(store_path) else os.path.join(base, store_path)
        
        if not os.path.isdir(store_dir):
            return 0
        
        # 1. 先用语义引擎构建索引（获取相似度矩阵）
        self._ss.build_index(store_dir)
        if self._ss._doc_count == 0:
            return 0
        
        # 2. 创建节点
        self._nodes = {}
        for meta in self._ss._doc_meta:
            n = ExperienceNode(
                filename=meta['filename'],
                tool_name=meta['tool_name'],
                error_type=meta['error_type'],
                error_message=meta['error_message'],
                action=meta['action'],
                success=meta['success'],
            )
            self._nodes[meta['filename']] = n
        
        filenames = list(self._nodes.keys())
        n = len(filenames)
        
        # 3. 构建边（基于语义相似度）
        self._edges = []
        self._adj = defaultdict(list)
        
        for i in range(n):
            f1 = filenames[i]
            for j in range(i + 1, n):
                f2 = filenames[j]
                # 复用语义引擎的向量计算相似度
                sim = self._compute_similarity(f1, f2)
                if sim >= self.sim_threshold:
                    self._edges.append((f1, f2, round(sim, 4)))
                    self._adj[f1].append((f2, sim))
                    self._adj[f2].append((f1, sim))
                    self._nodes[f1].degree += 1
                    self._nodes[f2].degree += 1
        
        # 4. 社区检测（Louvain-like 贪心）
        self._detect_communities()
        
        # 5. 捷径发现
        self._find_shortcuts()
        
        self._built = True
        return n
    
    def _compute_similarity(self, f1: str, f2: str) -> float:
        """计算两个经验之间的相似度"""
        if not self._ss._index_built:
            return 0.0
        
        idx1, idx2 = -1, -1
        for i, meta in enumerate(self._ss._doc_meta):
            if meta['filename'] == f1:
                idx1 = i
            if meta['filename'] == f2:
                idx2 = i
        
        if idx1 < 0 or idx2 < 0:
            return 0.0
        
        return _cosine_similarity(
            self._ss._doc_vectors[idx1],
            self._ss._doc_vectors[idx2]
        )
    
    def _detect_communities(self):
        """贪心社区检测（Louvain-like）"""
        filenames = list(self._nodes.keys())
        
        # 每个节点初始属于自己
        for f, node in self._nodes.items():
            node.community = hash(f) % 100000  # 用哈希做唯一初始ID
        
        # 合并阶段
        changed = True
        max_iter = 10
        it = 0
        while changed and it < max_iter:
            changed = False
            it += 1
            # 用社区ID到文件名列表的映射
            comm_map = defaultdict(list)
            for f in filenames:
                comm_map[self._nodes[f].community].append(f)
            
            # 对每个社区，检查其节点是否应合并到邻居社区
            new_communities = {}
            for f in filenames:
                node = self._nodes[f]
                best_comm = node.community
                best_strength = 0.0
                
                # 检查每个邻居的社区
                neighbor_comms = defaultdict(list)
                for neighbor, weight in self._adj[f]:
                    nc = self._nodes[neighbor].community
                    neighbor_comms[nc].append(weight)
                
                for nc, weights in neighbor_comms.items():
                    if nc == node.community:
                        continue
                    avg_weight = sum(weights) / len(weights)
                    if avg_weight > best_strength:
                        best_strength = avg_weight
                        best_comm = nc
                
                if best_comm != node.community:
                    changed = True
                new_communities[f] = best_comm
            
            for f, c in new_communities.items():
                self._nodes[f].community = c
        
        # 重新编号社区（0, 1, 2, ...）
        unique_comms = sorted(set(n.community for n in self._nodes.values()))
        comm_map = {old: new for new, old in enumerate(unique_comms)}
        for node in self._nodes.values():
            node.community = comm_map[node.community]
        
        self._community_count = len(unique_comms)
    
    def _find_shortcuts(self):
        """发现长程捷径（跨社区高相似度边）"""
        # 收集所有跨社区边
        cross_edges = []
        for f1, f2, weight in self._edges:
            if self._nodes[f1].community != self._nodes[f2].community:
                cross_edges.append((f1, f2, weight))
        
        if not cross_edges:
            self._shortcut_edges = []
            return
        
        # 按权重排序，取 top percentile
        cross_edges.sort(key=lambda x: -x[2])
        k = max(1, int(len(cross_edges) * SHORTCUT_PERCENTILE))
        self._shortcut_edges = cross_edges[:k]
        
        # 标记捷径节点
        shortcut_nodes = set()
        for f1, f2, _ in self._shortcut_edges:
            shortcut_nodes.add(f1)
            shortcut_nodes.add(f2)
        for f in shortcut_nodes:
            self._nodes[f].is_shortcut = True
    
    def topo_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """拓扑感知的检索：社区内优先 → 捷径扩展 → 跨社区
        
        排序规则:
          1. 同社区且高相似度 (权重最高)
          2. 桥梁经验 (捷径节点，可跨社区发现)
          3. 同社区中低相似度
          4. 跨社区普通边
        """
        if not self._built:
            return []
        
        # 先用语义引擎检索
        results = self._ss.search(query, top_k=len(self._nodes) * 2)
        if not results:
            return []
        
        # 找出查询最匹配的社区
        if results:
            top_filename = results[0]['filename']
            top_community = self._nodes.get(top_filename, None)
            query_community = top_community.community if top_community else -1
        else:
            query_community = -1
        
        # 拓扑排序
        scored_results = []
        for r in results:
            f = r['filename']
            node = self._nodes.get(f)
            if not node:
                continue
            
            base_score = r['score']
            
            # 拓扑加成
            bonus = 0.0
            if node.community == query_community:
                bonus += 0.15  # 同社区优先
            if node.is_shortcut:
                bonus += 0.10  # 桥梁经验+分
            if node.degree >= 3:
                bonus += 0.05  # 高连通节点
            
            scored_results.append({
                **r,
                'community': node.community,
                'is_shortcut': node.is_shortcut,
                'degree': node.degree,
                'topo_score': round(base_score + bonus, 4),
            })
        
        scored_results.sort(key=lambda x: -x['topo_score'])
        return scored_results[:top_k]
    
    def get_node_community(self, tool_name: str) -> int:
        """获取工具所在社区ID"""
        for fn, node in self._nodes.items():
            if node.tool_name == tool_name:
                return node.community
        return -1
    
    def is_shortcut(self, tool_name: str) -> bool:
        """判断工具是否为捷径节点"""
        for fn, node in self._nodes.items():
            if node.tool_name == tool_name:
                return node.is_shortcut
        return False
    
    def get_community_stats(self) -> Dict:
        """社区统计"""
        if not self._built:
            return {}
        
        community_sizes = Counter(n.community for n in self._nodes.values())
        # 按社区列出工具
        community_tools = defaultdict(set)
        for node in self._nodes.values():
            community_tools[node.community].add(node.tool_name)
        
        return {
            'community_count': self._community_count,
            'community_sizes': dict(sorted(community_sizes.items())),
            'community_tools': {
                str(c): sorted(tools)
                for c, tools in sorted(community_tools.items())
            },
        }
    
    def get_stats(self) -> Dict:
        """获取网络统计指标"""
        if not self._built:
            return {"built": False}
        
        n = len(self._nodes)
        m = len(self._edges)
        shortcuts = len(self._shortcut_edges)
        
        # 计算平均聚类系数（简化版）
        clustering_coeffs = []
        for f, node in self._nodes.items():
            neighbors = [n for n, _ in self._adj[f]]
            k = len(neighbors)
            if k < 2:
                clustering_coeffs.append(0.0)
                continue
            # 计算邻居之间的边数
            neighbor_set = set(neighbors)
            inter_edges = 0
            for n1 in neighbors:
                for n2, _ in self._adj[n1]:
                    if n2 in neighbor_set and n2 != n1:
                        inter_edges += 1
            # 无向图，每条边被算了两次
            inter_edges //= 2
            max_edges = k * (k - 1) / 2
            cc = inter_edges / max_edges if max_edges > 0 else 0
            clustering_coeffs.append(cc)
        
        avg_cc = sum(clustering_coeffs) / len(clustering_coeffs) if clustering_coeffs else 0
        
        # 社区统计
        cs = self.get_community_stats()
        
        return {
            'engine': 'experience_graph',
            'version': '1.3',
            'built': True,
            'nodes': n,
            'edges': m,
            'shortcuts': shortcuts,
            'shortcut_ratio': round(shortcuts / m, 4) if m > 0 else 0,
            'avg_degree': round(2 * m / n, 2) if n > 0 else 0,
            'avg_clustering': round(avg_cc, 4),
            'community_count': self._community_count,
            'edge_density': round(m / (n * (n - 1) / 2), 4) if n > 1 else 0,
            **cs,
        }


# ── 便捷接口 ──

_default_graph = None

def get_graph() -> ExperienceGraph:
    global _default_graph
    if _default_graph is None:
        _default_graph = ExperienceGraph()
    return _default_graph

def rebuild_graph(store_path: str = "experience_store") -> int:
    """重建并返回节点数"""
    g = get_graph()
    return g.build(store_path)
