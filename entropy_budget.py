# -*- coding: utf-8 -*-
"""
entropy_budget.py — v1.7 熵预算与耗散（复利思维）

功能:
  1. 经验库熵值跟踪：多样性、冗余度、覆盖度
  2. 耗散调度：基于门控审计日志驱动淘汰/校准/扩张
  3. 衰退检测：标记陈旧经验，降低其权重
  4. 扩张推荐：识别缺失区，推荐优先扩张方向

依赖: semantic_search, experience_graph, cognitive_zone, metacognition_gate
"""

import json
import os
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from semantic_search import SemanticSearch, get_engine
from experience_graph import ExperienceGraph, get_graph
from cognitive_zone import CognitiveZoneClassifier, get_classifier

# v1.7.1: 熵预算上限与隔离区
MODULE_CAP = 1000           # 每个模块经验上限
QUARANTINE_FILE = None



@dataclass
class EntropyReport:
    """熵预算报告"""
    total_experiences: int
    entropy_score: float          # 整体熵值 [0, 1]
    diversity_score: float        # 多样性 [0, 1]
    redundancy_score: float       # 冗余度 [0, 1]（越高越冗余）
    coverage_score: float         # 覆盖度 [0, 1]
    decay_count: int              # 衰退经验数
    expansion_suggestions: List[str] = field(default_factory=list)
    zone_distribution: dict = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class DissipationAction:
    """耗散动作"""
    action: str                   # "keep" | "archive" | "recalibrate" | "expand"
    tool_name: str
    reason: str
    priority: int                 # 1-5 (5=最高)


class EntropyBudget:
    """熵预算管理器
    
    复利思维的工程落地——不是优化单次决策，而是让系统本身持续变好。
    """
    
    def __init__(self, store_path: str = ""):
        if not store_path:
            base = Path(__file__).resolve().parent
            store_path = str(base / "experience_store")
        self.store_path = store_path
        self._engine: Optional[SemanticSearch] = None
        self._graph: Optional[ExperienceGraph] = None
        self._classifier: Optional[CognitiveZoneClassifier] = None
    
    def compute_entropy(self) -> EntropyReport:
        """计算经验库熵值"""
        self._ensure_initialized()
        
        store_dir = self.store_path
        experiences = self._load_experiences()
        total = len(experiences)
        
        if total == 0:
            return EntropyReport(
                total_experiences=0, entropy_score=0.0,
                diversity_score=0.0, redundancy_score=0.0,
                coverage_score=0.0, decay_count=0,
            )
        
        # 1. 多样性：不同工具名称的比例
        tools = set(e.get("tool_name", "") for e in experiences)
        diversity = min(1.0, len(tools) / max(total, 1))
        
        # 2. 冗余度：同名工具的平均重复次数
        tool_counts = Counter(e.get("tool_name", "") for e in experiences)
        if tools:
            redundancy = sum(c - 1 for c in tool_counts.values()) / total
        else:
            redundancy = 0.0
        
        # 3. 覆盖度：语义检索的平均召回率
        coverage = self._estimate_coverage(experiences, tools)
        
        # 4. 衰退检测
        decay_count = self._detect_decay(experiences)
        
        # 5. 整体熵值 = 多样性 × (1 - 冗余度) × 覆盖度
        entropy = diversity * (1 - redundancy * 0.5) * coverage
        
        # 6. 扩张建议
        suggestions = self._generate_suggestions(experiences, tools)
        
        # 7. 认知分区分布
        zone_dist = self._zone_distribution(experiences)
        
        return EntropyReport(
            total_experiences=total,
            entropy_score=round(entropy, 4),
            diversity_score=round(diversity, 4),
            redundancy_score=round(redundancy, 4),
            coverage_score=round(coverage, 4),
            decay_count=decay_count,
            expansion_suggestions=suggestions,
            zone_distribution=zone_dist,
            timestamp=datetime.now().isoformat(),
        )
    
    def compute_dissipation(self) -> List[DissipationAction]:
        """基于门控审计日志计算耗散动作"""
        actions = []
        
        # 读取门控审计日志
        audit_log = self._load_audit_log()
        if not audit_log:
            return actions

        # v1.7.1: 模块上限耗散
        for tool in tool_counts:
            if tool_counts[tool] >= MODULE_CAP:
                actions.append(DissipationAction(
                    action="archive",
                    tool_name=tool,
                    reason=f"超上限({tool_counts[tool]}/{MODULE_CAP})",
                    priority=5,
                ))

        # v2.1: 自动晋升降级
        tiers = self._compute_experience_tier()
        for tool, info in tiers.items():
            tier = info.get("tier", "neutral")
            streak = info.get("streak", 0)
            if tier == "validated":
                actions.append(DissipationAction(
                    action="promote",
                    tool_name=tool,
                    reason=f"连续{streak}次正增益 → 晋升",
                    priority=4,
                ))
            elif tier == "archived":
                actions.append(DissipationAction(
                    action="demote",
                    tool_name=tool,
                    reason=f"连续{streak}次负增益 → 降级",
                    priority=4,
                ))

        
        # 分析审计日志中的模式
        zone_counts = Counter(r.get('zone', '?') for r in audit_log)
        refused_tasks = [r for r in audit_log if not r.get('allow', True)]
        allowed_low_conf = [
            r for r in audit_log 
            if r.get('allow', False) and (r.get('confidence', 1.0) or 0) < 0.5
        ]
        
        # 1. 被拒答的任务 → 标记缺失区 → 扩张
        for r in refused_tasks[:5]:
            task = r.get('task', '')[:50]
            actions.append(DissipationAction(
                action="expand",
                tool_name=task,
                reason=f"门控拒答: {r.get('reason', '')[:50]}",
                priority=5,
            ))
        
        # 2. 低置信通过的任务 → 校准
        for r in allowed_low_conf[:5]:
            task = r.get('task', '')[:50]
            actions.append(DissipationAction(
                action="recalibrate",
                tool_name=task,
                reason=f"低置信通过: conf={r.get('confidence', 0):.2f}",
                priority=3,
            ))
        
        # 3. 高冗余的经验 → 归档
        store_dir = self.store_path
        experiences = self._load_experiences()
        tool_counts = Counter(e.get("tool_name", "") for e in experiences)
        for tool, count in tool_counts.most_common(3):
            if count > 2:
                actions.append(DissipationAction(
                    action="archive",
                    tool_name=tool,
                    reason=f"高冗余: {count}条同名经验",
                    priority=2,
                ))
        
        return actions
    
    def _ensure_initialized(self):
        """确保引擎已初始化"""
        if self._engine is None:
            self._engine = get_engine()
            self._engine.build_index(self.store_path)
        if self._graph is None:
            self._graph = get_graph()
            if not self._graph._built:
                self._graph.build(self.store_path)
        if self._classifier is None:
            self._classifier = get_classifier()
    

    def _get_quarantine_path(self) -> Path:
        """隔离区文件路径"""
        global QUARANTINE_FILE
        if QUARANTINE_FILE is None:
            base = Path(__file__).resolve().parent
            QUARANTINE_FILE = base / "quarantine.json"
        return QUARANTINE_FILE

    def _check_module_cap(self, tool_name: str) -> bool:
        """检查某工具的经验是否超限，超限则触发耗散"""
        count = sum(1 for e in self._load_experiences()
                    if e.get("tool_name", "") == tool_name)
        return count >= MODULE_CAP

    def _add_to_quarantine(self, tool_name: str, reason: str = "hallucination") -> None:
        """将经验加入隔离区"""
        qpath = self._get_quarantine_path()
        entries = []
        if qpath.exists():
            with open(qpath, "r", encoding="utf-8") as f:
                entries = json.load(f)
        entries.append({
            "tool_name": tool_name,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        with open(qpath, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)

    def get_quarantine_report(self) -> dict:
        """获取隔离区报告"""
        qpath = self._get_quarantine_path()
        if not qpath.exists():
            return {"total": 0, "entries": []}
        with open(qpath, "r", encoding="utf-8") as f:
            entries = json.load(f)
        return {"total": len(entries), "entries": entries[-20:]}

    def _load_experiences(self) -> List[dict]:
        """加载经验库"""
        store_dir = self.store_path
        if not os.path.isdir(store_dir):
            return []
        experiences = []
        for f in sorted(os.listdir(store_dir)):
            if not f.endswith('.json') or f == 'index.json':
                continue
            fp = os.path.join(store_dir, f)
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                experiences.append(data)
            except (json.JSONDecodeError, IOError):
                continue
        return experiences
    
    def _estimate_coverage(self, experiences: List[dict], tools: set) -> float:
        """估算经验库覆盖度"""
        if not experiences or not self._engine or not self._engine._index_built:
            return 0.0
        
        # 用每个工具名作为查询，测试是否能被召回
        hit_count = 0
        for tool in tools:
            results = self._engine.search(tool, top_k=3)
            if any(r['tool_name'] == tool for r in results):
                hit_count += 1
        
        return hit_count / max(len(tools), 1)
    
    def _detect_decay(self, experiences: List[dict]) -> int:
        """检测衰退经验（超过30天未更新的）"""
        cutoff = datetime.now() - timedelta(days=30)
        decay_count = 0
        for e in experiences:
            ts_str = e.get('timestamp', '')
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts < cutoff:
                        decay_count += 1
                except (ValueError, TypeError):
                    decay_count += 1
        return decay_count
    
    def _generate_suggestions(self, experiences: List[dict], tools: set) -> List[str]:
        """生成扩张建议"""
        suggestions = []
        
        # 检查有无缺失的高频工具类型
        all_tool_names = [e.get("tool_name", "") for e in experiences]
        name_parts = Counter()
        for name in all_tool_names:
            for part in name.replace('_', ' ').split():
                name_parts[part] += 1
        
        # 检查覆盖缺口
        if not tools:
            suggestions.append("经验库为空，建议从基础工具开始积累")
        elif len(tools) < 5:
            suggestions.append(f"工具种类偏少（{len(tools)}种），建议扩展更多工具类型")
        if self._detect_decay(experiences) > len(experiences) * 0.3:
            suggestions.append("超过30%的经验已衰退，建议更新或淘汰")
        
        return suggestions
    
    def _zone_distribution(self, experiences: List[dict]) -> dict:
        """计算认知分区分布"""
        # 简单的基于工具名的分区
        zones = {"proficient": 0, "perplexed": 0, "missing": 0}
        for e in experiences:
            tool = e.get("tool_name", "")
            if self._classifier:
                r = self._classifier.classify(tool, self.store_path)
                zone = r.zone
                if zone in zones:
                    zones[zone] += 1
                else:
                    zones["missing"] += 1
        total = max(sum(zones.values()), 1)
        return {k: {"count": v, "pct": round(v/total*100, 1)} for k, v in zones.items()}
    
    def _load_hs_episodes(self) -> list:
        """加载 HS Paladin episodes"""
        hs_path = Path(__file__).resolve().parent.parent / "hs_next" / "finance" / "evolution"
        ep_file = hs_path / "episodes.jsonl"
        if not ep_file.exists():
            return []
        episodes = []
        with open(ep_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        episodes.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return episodes

    def _compute_experience_tier(self) -> dict:
        """计算每条经验的晋升/降级状态\n\n        规则: 连续3次增益>0.1→validated, 连续5次负增益→archived"""
        episodes = self._load_hs_episodes()
        if not episodes:
            return {}
        from collections import defaultdict
        tool_gains = defaultdict(list)
        for ep in episodes:
            code = ep.get("metadata", {}).get("code", "unknown")
            score = ep.get("metadata", {}).get("score", 0)
            success = ep.get("success", False)
            gain = score - 45 if success else -(score + 10)
            tool_gains[code].append(gain)
        tiers = {}
        for tool, gains in tool_gains.items():
            recent = gains[-10:]
            if len(recent) < 3:
                tiers[tool] = {"tier": "neutral", "streak": 0}
                continue
            pos_streak = 0
            neg_streak = 0
            for g in reversed(recent):
                if g > 0.1:
                    pos_streak += 1; neg_streak = 0
                elif g < -0.1:
                    neg_streak += 1; pos_streak = 0
                else:
                    break
            if pos_streak >= 3:
                tiers[tool] = {"tier": "validated", "streak": pos_streak}
            elif neg_streak >= 5:
                tiers[tool] = {"tier": "archived", "streak": neg_streak}
            else:
                tiers[tool] = {"tier": "neutral", "streak": max(pos_streak, neg_streak)}
        return tiers

    def _load_audit_log(self) -> List[dict]:
        """加载门控审计日志"""
        base = Path(__file__).resolve().parent
        log_file = base / "gate_audit" / "gate_audit.jsonl"
        if not log_file.exists():
            return []
        records = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records


# ── 单例与便捷接口 ──
_default_budget: Optional[EntropyBudget] = None

def get_budget() -> EntropyBudget:
    global _default_budget
    if _default_budget is None:
        _default_budget = EntropyBudget()
    return _default_budget

def compute_entropy() -> EntropyReport:
    """便捷熵值计算"""
    return get_budget().compute_entropy()

def compute_dissipation() -> List[DissipationAction]:
    """便捷耗散计算"""
    return get_budget().compute_dissipation()
