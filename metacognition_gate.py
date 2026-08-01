# -*- coding: utf-8 -*-
"""
metacognition_gate.py — v1.6 元认知门控（逆向思维）

功能:
  1. assess(task_signature) → GateDecision: 从目标倒推可行性
  2. 结构化拒答: 当置信度不足时输出结构化拒答信号
  3. 门控审计日志: 每次调用记录到 gate_audit.jsonl

依赖: cognitive_zone, dual_path, semantic_search, strategy_similarity
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from cognitive_zone import CognitiveZoneClassifier, get_classifier
from dual_path import DualPathRecommender, get_recommender
from semantic_search import SemanticSearch, get_engine
from strategy_similarity import strategy_similarity_check


REQUIRED_THRESHOLD = 0.5  # 困惑区最低置信度阈值
AUDIT_DIR = Path(__file__).resolve().parent / "gate_audit"


@dataclass
class GateDecision:
    """门控决策"""
    allow: bool
    confidence: float
    recommended_path: str     # "reference" | "exploration" | "human"
    reason: str
    uncertainty_factors: List[str] = field(default_factory=list)
    suggestion: str = ""
    zone: str = ""
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


class MetacognitionGate:
    """元认知门控
    
    逆向推演：不问"我有什么经验"，而问"这个任务需要什么置信度"
    """
    
    def __init__(self, audit_enabled: bool = True):
        self.audit_enabled = audit_enabled
        self._classifier: Optional[CognitiveZoneClassifier] = None
        self._recommender: Optional[DualPathRecommender] = None
        self._engine: Optional[SemanticSearch] = None
        self._audit_log: List[dict] = []
        
        # 确保审计目录存在
        if audit_enabled:
            AUDIT_DIR.mkdir(exist_ok=True)
    
    def assess(self, task_signature: str, 
               risk_level: str = "normal",
               code_context: str = "") -> GateDecision:
        """元认知门控评估
        
        Args:
            task_signature: 任务描述（自然语言）
            risk_level: 风险等级 ("low" | "normal" | "high")
            code_context: 代码上下文（用于策略相似度校验）
        
        Returns:
            GateDecision: 门控决策
        """
        # 1. 认知分区
        zone = self._get_zone(task_signature)
        
        # 2. 聚合多维信号
        signals = self._aggregate_signals(task_signature, code_context)
        
        # 3. 逆向推演：从目标倒推所需置信度
        required_conf = self._risk_threshold(risk_level)
        
        # 4. 决策逻辑
        decision = self._decide(zone, signals, required_conf, risk_level)
        
        # 5. 审计日志
        if self.audit_enabled:
            self._log_audit(task_signature, decision, signals, risk_level)
        
        return decision
    
    def _get_zone(self, task: str) -> str:
        """获取认知分区"""
        if self._classifier is None:
            self._classifier = get_classifier()
        store_path = str(AUDIT_DIR.parent / "experience_store")
        result = self._classifier.classify(task, store_path)
        return result.zone
    
    def _aggregate_signals(self, task: str, code_context: str) -> dict:
        """聚合多维度信号"""
        if self._recommender is None:
            self._recommender = get_recommender()
        if self._engine is None:
            self._engine = get_engine()
        
        store_path = str(AUDIT_DIR.parent / "experience_store")
        self._recommender.build(store_path)
        
        # 覆盖度
        self._engine.build_index(store_path)
        search_results = self._engine.search(task, top_k=5)
        coverage = len(search_results) / 5.0 if self._engine._doc_count > 0 else 0.0
        
        # 历史成功率（用平均相似度估算）
        historical_success = 0.0
        if search_results:
            historical_success = sum(r['score'] for r in search_results) / len(search_results)
        
        # 双路径置信度
        rec_result = self._recommender.recommend(task)
        ref_conf = 0.0
        exp_conf = 0.0
        if rec_result.reference_path:
            ref_conf = sum(r.confidence for r in rec_result.reference_path) / len(rec_result.reference_path)
        if rec_result.exploration_path:
            exp_conf = sum(e.confidence for e in rec_result.exploration_path) / len(rec_result.exploration_path)
        
        return {
            "coverage": round(coverage, 4),
            "historical_success": round(historical_success, 4),
            "verifier_health": 0.85,  # 模拟值，由 Executor 在运行时更新
            "reference_confidence": round(ref_conf, 4),
            "exploratory_confidence": round(exp_conf, 4),
            "search_results_count": len(search_results),
        }
    
    def _risk_threshold(self, risk_level: str) -> float:
        """风险等级 → 所需置信度阈值"""
        thresholds = {
            "low": 0.3,
            "normal": 0.5,
            "high": 0.8,
        }
        return thresholds.get(risk_level, 0.5)
    
    def _decide(self, zone: str, signals: dict, 
                required_conf: float, risk_level: str) -> GateDecision:
        """核心决策逻辑"""
        ref_conf = signals["reference_confidence"]
        coverage = signals["coverage"]
        
        # 熟练区：直接执行
        if zone == "proficient":
            return GateDecision(
                allow=True,
                confidence=ref_conf,
                recommended_path="reference",
                reason="熟练区，直接执行",
                zone=zone,
                timestamp=datetime.now().isoformat(),
            )
        
        # 缺失区：无覆盖则拒答，有覆盖则探索
        if zone == "missing":
            if coverage < 0.2:
                return GateDecision(
                    allow=False,
                    confidence=0.0,
                    recommended_path="human",
                    reason=f"缺失区且经验覆盖不足（覆盖率 {coverage:.2f} < 0.2），建议人工介入",
                    uncertainty_factors=[
                        f"经验覆盖度: {coverage:.2f}",
                        f"参考路径置信度: {ref_conf:.2f}",
                    ],
                    suggestion="建议人工介入或提供更多上下文",
                    zone=zone,
                    timestamp=datetime.now().isoformat(),
                )
            return GateDecision(
                allow=True,
                confidence=ref_conf,
                recommended_path="exploration",
                reason=f"缺失区但有经验覆盖（{signals['search_results_count']}条相关），启用探索路径",
                zone=zone,
                timestamp=datetime.now().isoformat(),
            )
        
        # 困惑区：核心战场
        if zone == "perplexed":
            if ref_conf < required_conf:
                return GateDecision(
                    allow=False,
                    confidence=ref_conf,
                    recommended_path="human",
                    reason=f"困惑区置信度 {ref_conf:.2f} < 阈值 {required_conf:.2f}，拒答",
                    uncertainty_factors=[
                        f"参考路径置信度: {ref_conf:.2f} (< {required_conf:.2f})",
                        f"经验覆盖度: {coverage:.2f}",
                        f"历史成功率: {signals['historical_success']:.2f}",
                    ],
                    suggestion="建议人工介入或降低任务风险等级",
                    zone=zone,
                    timestamp=datetime.now().isoformat(),
                )
            return GateDecision(
                allow=True,
                confidence=ref_conf,
                recommended_path="reference",
                reason=f"困惑区校准通过（{ref_conf:.2f} >= {required_conf:.2f}）",
                zone=zone,
                timestamp=datetime.now().isoformat(),
            )
        
        # 未知分区：保守拒答
        return GateDecision(
            allow=False,
            confidence=0.0,
            recommended_path="human",
            reason=f"未知认知分区（{zone}），保守拒答",
            uncertainty_factors=[f"未知分区: {zone}"],
            suggestion="请检查认知分区分类器",
            zone=zone,
            timestamp=datetime.now().isoformat(),
        )
    
    def _log_audit(self, task: str, decision: GateDecision,
                   signals: dict, risk_level: str):
        """写入门控审计日志"""
        record = {
            "timestamp": decision.timestamp,
            "task": task[:200],
            "risk_level": risk_level,
            "zone": decision.zone,
            "allow": decision.allow,
            "confidence": decision.confidence,
            "recommended_path": decision.recommended_path,
            "signals": signals,
            "uncertainty_factors": decision.uncertainty_factors,
        }
        self._audit_log.append(record)
        
        # 追加到 jsonl 文件
        log_file = AUDIT_DIR / "gate_audit.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def get_audit_log(self, n: int = 20) -> List[dict]:
        """获取最近 n 条审计记录"""
        return self._audit_log[-n:]
    
    def get_stats(self) -> dict:
        """获取门控统计"""
        total = len(self._audit_log)
        allowed = sum(1 for r in self._audit_log if r['allow'])
        refused = total - allowed
        return {
            "total_assessments": total,
            "allowed": allowed,
            "refused": refused,
            "refusal_rate": round(refused/total, 3) if total > 0 else 0.0,
            "path_distribution": {
                p: sum(1 for r in self._audit_log if r['recommended_path'] == p)
                for p in set(r['recommended_path'] for r in self._audit_log)
            },
        }


# ── 单例与便捷接口 ──
_default_gate: Optional[MetacognitionGate] = None

def get_gate() -> MetacognitionGate:
    global _default_gate
    if _default_gate is None:
        _default_gate = MetacognitionGate()
    return _default_gate

def assess_task(task_signature: str, risk_level: str = "normal") -> GateDecision:
    """便捷评估接口"""
    return get_gate().assess(task_signature, risk_level=risk_level)
