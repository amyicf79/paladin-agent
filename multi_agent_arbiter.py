# -*- coding: utf-8 -*-
"""
multi_agent_arbiter.py — v2.5 多 Agent 仲裁

功能:
  - 冲突结论仲裁（N>2 路径比较）
  - 加权投票（置信度 × 历史可信度）
  - 低置信升级转人工
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import List, Optional, Any
from datetime import datetime


ARBITRATION_THRESHOLD = 0.5


@dataclass
class AgentProposal:
    """单个 Agent 的提案"""
    agent_name: str
    strategy: str
    confidence: float
    task_type: str = ""
    trust_score: float = 1.0
    evidence: str = ""


@dataclass
class ArbitrationResult:
    """仲裁结果"""
    winner: Optional[str]
    confidence: float
    escalate_to_human: bool
    details: dict = field(default_factory=dict)


_ARBITER: Optional["MultiAgentArbiter"] = None


class MultiAgentArbiter:
    """多 Agent 仲裁器"""

    def __init__(self):
        self.audit_api = None
        try:
            from trace import get_trace
            self.audit_api = get_trace()
        except ImportError:
            pass

    def arbitrate(self, proposals: List[AgentProposal]) -> ArbitrationResult:
        """仲裁 N>2 个冲突提案"""
        if not proposals:
            return ArbitrationResult(
                winner=None, confidence=0.0,
                escalate_to_human=True,
                details={"reason": "无提案"}
            )

        # 1. 获取历史可信度
        for p in proposals:
            if self.audit_api is not None:
                try:
                    stats = self.audit_api.get_stats()
                    agent_counts = stats.get("by_agent", {})
                    total = agent_counts.get(p.agent_name, 1)
                    # 简单可信度：该 Agent 出现次数 / 总事件数
                    all_total = stats.get("total_events", 1)
                    p.trust_score = min(1.0, total / max(all_total, 1) * 2)
                except Exception:
                    p.trust_score = 0.5
            else:
                p.trust_score = 0.5

        # 2. 加权投票：置信度 × 可信度
        scored = [
            (p.confidence * p.trust_score, p)
            for p in proposals
        ]
        scored.sort(key=lambda x: -x[0])
        best_score, best_proposal = scored[0]

        # 3. 检查是否需升级
        escalate = best_score < ARBITRATION_THRESHOLD

        return ArbitrationResult(
            winner=best_proposal.strategy if not escalate else None,
            confidence=round(best_score, 3),
            escalate_to_human=escalate,
            details={
                "proposals": [
                    {
                        "agent": p.agent_name,
                        "strategy": p.strategy,
                        "confidence": p.confidence,
                        "trust_score": round(p.trust_score, 3),
                        "weighted": round(p.confidence * p.trust_score, 3),
                    }
                    for p in proposals
                ],
                "threshold": ARBITRATION_THRESHOLD,
            }
        )

    def get_stats(self) -> dict:
        return {
            "threshold": ARBITRATION_THRESHOLD,
            "audit_connected": self.audit_api is not None,
        }


def get_arbiter() -> MultiAgentArbiter:
    global _ARBITER
    if _ARBITER is None:
        _ARBITER = MultiAgentArbiter()
    return _ARBITER


def arbitrate(proposals: List[AgentProposal]) -> ArbitrationResult:
    """便捷仲裁接口"""
    return get_arbiter().arbitrate(proposals)
