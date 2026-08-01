# -*- coding: utf-8 -*-
"""
reputation_tracker.py — v3.0 Agent 信誉系统

基于 Trace 审计日志计算每个 Agent 的历史成功率。
当 trace 数据不足时，回退到默认信誉分。
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


_REPUTATION_FILE = None


def _get_reputation_path() -> Path:
    global _REPUTATION_FILE
    if _REPUTATION_FILE is None:
        _REPUTATION_FILE = Path(__file__).resolve().parent / "reputation_data.json"
    return _REPUTATION_FILE


class ReputationTracker:
    """Agent 信誉跟踪器"""

    def __init__(self):
        self._scores: Dict[str, float] = {}
        self._history: Dict[str, list] = {}
        self._load()

    def get_score(self, agent_name: str) -> float:
        """获取 Agent 当前信誉分 (0.0~1.0)"""
        # 优先返回缓存分
        if agent_name in self._scores:
            return self._scores[agent_name]
        return 0.5  # 默认

    def record_outcome(self, agent_name: str, success: bool) -> None:
        """记录一次执行结果"""
        if agent_name not in self._history:
            self._history[agent_name] = []
        self._history[agent_name].append(1.0 if success else 0.0)
        # 更新信誉分：最近 20 条加权平均
        recent = self._history[agent_name][-20:]
        weights = [0.5 + 0.5 * (i / max(len(recent)-1, 1)) for i in range(len(recent))]
        weighted = sum(w * r for w, r in zip(weights, recent))
        self._scores[agent_name] = round(weighted / (sum(weights) or 1), 3)
        self._save()

    def sync_from_trace(self, trace_stats: dict) -> int:
        """从 Trace 审计数据同步信誉分"""
        by_agent = trace_stats.get("by_agent", {})
        total = trace_stats.get("total_events", 0)
        if total < 10:
            return 0  # 数据不足，仍用默认分
        for agent, count in by_agent.items():
            self._scores[agent] = round(min(1.0, count / max(total, 1) * 3), 3)
        self._save()
        return len(by_agent)

    def get_stats(self) -> dict:
        return {
            "tracked_agents": list(self._scores.keys()),
            "scores": self._scores,
            "history_counts": {k: len(v) for k, v in self._history.items()},
        }

    def _load(self) -> None:
        path = _get_reputation_path()
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._scores = data.get("scores", {})
            self._history = data.get("history", {})

    def _save(self) -> None:
        path = _get_reputation_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"scores": self._scores, "history": self._history},
                      f, indent=2, ensure_ascii=False)


_default_tracker: Optional[ReputationTracker] = None


def get_reputation() -> ReputationTracker:
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = ReputationTracker()
    return _default_tracker


def get_score(agent_name: str) -> float:
    return get_reputation().get_score(agent_name)


def record(agent_name: str, success: bool) -> None:
    get_reputation().record_outcome(agent_name, success)
