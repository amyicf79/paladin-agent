# -*- coding: utf-8 -*-
"""
cognitive_zone.py — v1.4 认知分区（能力圈模型）

将每个查询分为三个认知区域：
  - 熟练区 (Proficient):  高置信度，可直接执行
  - 困惑区 (Perplexed):   部分覆盖，需检索+验证
  - 缺失区 (Missing):     无覆盖，需生成+探索

依赖: semantic_search, experience_graph
"""

import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

from semantic_search import SemanticSearch, get_engine


# ── 分区阈值（可调） ──

THRESHOLDS = {
    "proficient_min_top1": 0.40,      # top1 >= 0.4 → 熟练候选
    "proficient_min_mean": 0.12,      # mean >= 0.12 → 熟练候选
    "proficient_min_success": 0.80,   # 历史成功率 >= 80%
    "perplexed_min_top1": 0.15,       # top1 >= 0.15 → 困惑
    "perplexed_min_mean": 0.05,       # mean >= 0.05 → 困惑
    "missing_max_top1": 0.15,         # top1 < 0.15 → 缺失候选
}


@dataclass
class ZoneResult:
    """认知分区评估结果"""
    zone: str                          # "proficient" | "perplexed" | "missing"
    confidence: float                  # 置信度 0-1
    top1_score: float                  # 最高相似度
    mean_score: float                  # 平均相似度
    coverage_count: int                # 覆盖条目数（similarity > 0.1）
    history_success_rate: float = 0.0  # 历史成功率
    reason: str = ""                   # 判定理由


class CognitiveZoneClassifier:
    """认知分区分类器
    
    用法:
        czc = CognitiveZoneClassifier()
        result = czc.classify("读取CSV文件并统计行数")
        # -> ZoneResult(zone="proficient", confidence=0.85, ...)
        
        if result.zone == "proficient":
            execute_directly()
        elif result.zone == "perplexed":
            retrieve_and_verify()
        else:
            generate_and_explore()
    """
    
    def __init__(self, thresholds: Optional[Dict] = None):
        self.thresholds = {**THRESHOLDS, **(thresholds or {})}
        self._engine = None
    
    def _get_engine(self) -> SemanticSearch:
        if self._engine is None:
            self._engine = get_engine()
        return self._engine
    
    def classify(
        self,
        query: str,
        store_path: str = "experience_store",
    ) -> ZoneResult:
        """对查询进行认知分区"""
        engine = self._get_engine()
        if not engine._index_built:
            engine.build_index(store_path)
        
        # 1. 获取相似度分布
        dist = engine.get_score_distribution(query)
        
        top1 = dist.get('top1', 0.0)
        mean = dist.get('mean', 0.0)
        coverage = sum(1 for s in dist.get('top5', []) if s > 0.1)
        
        # 2. 获取历史成功率（从top匹配的经验中推断）
        top_results = engine.search(query, top_k=5)
        success_count = sum(1 for r in top_results if r.get('success', True))
        total_count = len(top_results)
        success_rate = success_count / max(total_count, 1)
        
        # 3. 判定分区
        zone, confidence, reason = self._decide_zone(
            top1, mean, coverage, success_rate
        )
        
        return ZoneResult(
            zone=zone,
            confidence=round(confidence, 3),
            top1_score=round(top1, 4),
            mean_score=round(mean, 4),
            coverage_count=coverage,
            history_success_rate=round(success_rate, 3),
            reason=reason,
        )
    
    def _decide_zone(
        self,
        top1: float,
        mean: float,
        coverage: int,
        success_rate: float,
    ) -> Tuple[str, float, str]:
        """三态判定逻辑"""
        t = self.thresholds
        
        # 熟练区: 高相似度 + 高覆盖率 + 高成功率
        if (top1 >= t["proficient_min_top1"]
                and mean >= t["proficient_min_mean"]
                and coverage >= 1
                and success_rate >= t["proficient_min_success"]):
            conf = min(1.0, (top1 + mean + success_rate) / 2.5)
            return "proficient", conf, (
                f"top1={top1:.2f}>={t['proficient_min_top1']}, "
                f"成功率{success_rate:.0%}>={t['proficient_min_success']:.0%}"
            )
        
        # 缺失区: 低相似度 + 低覆盖率
        if top1 < t["missing_max_top1"] and coverage == 0:
            conf = max(0.5, 1.0 - top1 * 3)
            return "missing", conf, (
                f"top1={top1:.2f}<{t['missing_max_top1']}, 无覆盖"
            )
        
        # 困惑区: 中间地带
        if top1 >= t["perplexed_min_top1"] or mean >= t["perplexed_min_mean"]:
            # 越接近熟练区，置信度越高
            progress = min(1.0, max(0, (top1 - t["perplexed_min_top1"]) 
                                     / (t["proficient_min_top1"] - t["perplexed_min_top1"] + 0.01)))
            conf = 0.4 + progress * 0.35
            return "perplexed", conf, (
                f"top1={top1:.2f}介于{t['perplexed_min_top1']}-{t['proficient_min_top1']}, "
                f"覆盖{coverage}条"
            )
        
        # 兜底: 缺失区
        return "missing", 0.5, f"top1={top1:.2f}过低, 无法确定"
    
    def get_zone_stats(self, store_path: str = "experience_store") -> Dict:
        """扫描经验库，统计各分区分布"""
        engine = self._get_engine()
        if not engine._index_built:
            engine.build_index(store_path)
        
        zones = {"proficient": 0, "perplexed": 0, "missing": 0}
        zone_details = {"proficient": [], "perplexed": [], "missing": []}
        
        # 对每个经验工具做一次查询
        for meta in engine._doc_meta:
            query = f"{meta['tool_name']} {meta['error_type']} {meta['error_message'][:30]}"
            result = self.classify(query, store_path)
            zones[result.zone] += 1
            zone_details[result.zone].append({
                "tool": meta['tool_name'],
                "confidence": result.confidence,
            })
        
        total = sum(zones.values())
        return {
            "total_queries": total,
            "zone_distribution": {
                k: {"count": v, "pct": round(v / total * 100, 1) if total > 0 else 0}
                for k, v in zones.items()
            },
            "zone_details": zone_details,
        }


# ── 便捷接口 ──

_default_classifier = None

def get_classifier() -> CognitiveZoneClassifier:
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = CognitiveZoneClassifier()
    return _default_classifier

def classify_query(query: str, store_path: str = "experience_store") -> ZoneResult:
    """便捷分类接口"""
    return get_classifier().classify(query, store_path)
