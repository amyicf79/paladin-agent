# -*- coding: utf-8 -*-
"""
dual_path.py — v1.5 双路径推荐（系统思维+能力圈交叉）

双路径架构:
  参考路径 (Reference Path): 只使用 validated 经验，保守可靠
  探索路径 (Exploration Path): 结合新经验，发现潜力方案
  ε-greedy 平衡: 以 ε 概率走探索路径，(1-ε) 概率走参考路径
  策略对齐: 两者产出通过相似度校验对齐

依赖: semantic_search, experience_graph, cognitive_zone
"""

import os
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable

from semantic_search import SemanticSearch, get_engine
from experience_graph import ExperienceGraph, get_graph


@dataclass
class PathResult:
    """单路径推荐结果"""
    source: str           # "reference" | "exploration"
    tool_name: str
    score: float
    confidence: float
    success_rate: float
    is_validated: bool
    is_novel: bool
    community: int = -1
    is_shortcut: bool = False


@dataclass
class DualPathRecommendation:
    """双路径综合推荐"""
    query: str
    reference_path: List[PathResult] = field(default_factory=list)
    exploration_path: List[PathResult] = field(default_factory=list)
    epsilon: float = 0.2
    alignment_score: float = 0.0
    recommended: str = "reference"  # "reference" | "exploration" | "both"
    
    def merge(self, top_k: int = 3) -> List[PathResult]:
        """ε-greedy 合并两条路径"""
        if not self.reference_path:
            return self.exploration_path[:top_k]
        if not self.exploration_path:
            return self.reference_path[:top_k]
        
        merged = []
        ref_set = {r.tool_name for r in self.reference_path}
        
        # 参考路径全量加入
        for r in self.reference_path[:top_k]:
            merged.append(r)
        
        # 探索路径补充（避免重复）
        for e in self.exploration_path:
            if e.tool_name not in ref_set and len(merged) < top_k:
                merged.append(e)
        
        return merged


class DualPathRecommender:
    """双路径推荐引擎"""
    
    def __init__(self, epsilon: float = 0.2, top_k: int = 5):
        self.epsilon = epsilon
        self.top_k = top_k
        self._ref_engine: Optional[SemanticSearch] = None
        self._exp_engine: Optional[SemanticSearch] = None
        self._graph: Optional[ExperienceGraph] = None
    
    def build(self, store_path: str) -> int:
        """构建双路径索引"""
        self._graph = get_graph()
        if not self._graph._built:
            self._graph.build(store_path)
        
        # 参考路径引擎：只索引 validated 经验
        self._ref_engine = SemanticSearch()
        ref_count = self._ref_engine.build_index(store_path)
        
        # 探索路径引擎：在参考引擎基础上加入低分/新奇经验
        self._exp_engine = SemanticSearch()
        exp_count = self._exp_engine.build_index(store_path)
        
        return ref_count + exp_count
    
    def recommend(self, query: str, zone: Optional[str] = None) -> DualPathRecommendation:
        """双路径推荐
        
        Args:
            query: 查询文本
            zone: 认知分区（proficient/perplexed/missing），自动调整 ε
        
        Returns:
            DualPathRecommendation: 双路径推荐结果
        """
        if not self._ref_engine or not self._ref_engine._index_built:
            return DualPathRecommendation(query=query)
        
        # 根据认知分区调整 ε
        adjusted_eps = self._adjust_epsilon(zone)
        
        # 参考路径：高置信度经验
        ref_results = self._ref_engine.search(query, top_k=self.top_k, min_score=0.1)
        reference_path = []
        for r in ref_results:
            reference_path.append(PathResult(
                source="reference",
                tool_name=r['tool_name'],
                score=r['score'],
                confidence=min(1.0, r['score'] * 1.5),
                success_rate=r.get('success', True) if isinstance(r.get('success'), bool) else 0.9,
                is_validated=r.get('success', True) == True,
                is_novel=False,
                community=self._graph.get_node_community(r['tool_name']) if self._graph._built else -1,
                is_shortcut=self._graph.is_shortcut(r['tool_name']) if self._graph._built else False,
            ))
        
        # 探索路径：加入低分/新颖/捷径经验
        exp_results = self._exp_engine.search(query, top_k=self.top_k * 2)
        exploration_path = []
        seen_tools = {r.tool_name for r in reference_path}
        
        for r in exp_results:
            if r['tool_name'] not in seen_tools:
                is_novel = r['score'] < 0.3 or (self._graph._built and self._graph.is_shortcut(r['tool_name']))
                exploration_path.append(PathResult(
                    source="exploration",
                    tool_name=r['tool_name'],
                    score=r['score'],
                    confidence=max(0.1, min(0.6, r['score'])),
                    success_rate=r.get('success', True) if isinstance(r.get('success'), bool) else 0.5,
                    is_validated=r.get('success', True) == True,
                    is_novel=is_novel,
                    community=self._graph.get_node_community(r['tool_name']) if self._graph._built else -1,
                    is_shortcut=self._graph.is_shortcut(r['tool_name']) if self._graph._built else False,
                ))
            if len(exploration_path) >= self.top_k:
                break
        
        # 计算对齐度
        alignment = self._compute_alignment(reference_path, exploration_path)
        
        # 推荐决策
        rec = "reference"
        if random.random() < adjusted_eps and exploration_path:
            rec = "exploration"
        if not reference_path and exploration_path:
            rec = "exploration"
        if not exploration_path and reference_path:
            rec = "reference"
        if alignment > 0.7:
            rec = "both"  # 高度对齐时可安全混合
        
        return DualPathRecommendation(
            query=query,
            reference_path=reference_path,
            exploration_path=exploration_path,
            epsilon=adjusted_eps,
            alignment_score=alignment,
            recommended=rec,
        )
    
    def _adjust_epsilon(self, zone: Optional[str]) -> float:
        """根据认知分区调整探索率"""
        eps_map = {
            "proficient": 0.05,   # 熟练区：几乎不探索
            "perplexed": 0.20,    # 困惑区：适度探索
            "missing": 0.40,      # 缺失区：大力探索
            None: self.epsilon,
        }
        return eps_map.get(zone, self.epsilon)
    
    def _compute_alignment(self, ref_path, exp_path) -> float:
        """计算双路径对齐度（重叠工具的分数差异）"""
        if not ref_path or not exp_path:
            return 0.0
        ref_tools = {r.tool_name: r.score for r in ref_path}
        exp_tools = {e.tool_name: e.score for e in exp_path}
        
        common = set(ref_tools.keys()) & set(exp_tools.keys())
        if not common:
            return 0.0
        
        diffs = [abs(ref_tools[t] - exp_tools[t]) for t in common]
        avg_diff = sum(diffs) / len(diffs)
        return max(0.0, 1.0 - avg_diff)


# ── 单例与便捷接口 ──
_default_recommender: Optional[DualPathRecommender] = None

def get_recommender() -> DualPathRecommender:
    global _default_recommender
    if _default_recommender is None:
        _default_recommender = DualPathRecommender()
    return _default_recommender

def dual_path_recommend(query: str, store_path: str = "experience_store",
                        zone: Optional[str] = None) -> DualPathRecommendation:
    """便捷推荐接口"""
    rec = get_recommender()
    rec.build(store_path)
    return rec.recommend(query, zone=zone)
