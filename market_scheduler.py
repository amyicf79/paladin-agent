# -*- coding: utf-8 -*-
"""
market_scheduler.py — v3.0 市场调度器

功能:
  - 接收任务 → 收集报价 → 加权评分 → 选最优 Agent
  - 熔断机制 (连续 N 次失败暂停投标权)
  - 信誉系统接入
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

from agent_bid import AgentBid, collect_bids


MELTDOWN_THRESHOLD = 3   # 连续失败 N 次触发熔断
_MELTDOWN_FILE = None


def _get_meltdown_path() -> Path:
    global _MELTDOWN_FILE
    if _MELTDOWN_FILE is None:
        _MELTDOWN_FILE = Path(__file__).resolve().parent / "meltdown_state.json"
    return _MELTDOWN_FILE


@dataclass
class ScheduleResult:
    """调度结果"""
    agent_name: str
    task: str
    bid_score: float
    reputation: float
    final_score: float
    reason: str
    explore: bool = False


class MarketScheduler:
    """市场调度器"""

    def __init__(self, epsilon: float = 0.1):
        self._epsilon = epsilon
        self._explore_count = 0
        self._exploit_count = 0
        self._meltdown: Dict[str, int] = {}
        self._load_meltdown()

    def schedule(self, registry, task_signature: str,
                 reputation=None, arbiter=None,
                 agents: Optional[List[str]] = None,
                 zone_map: Optional[dict] = None) -> Optional[ScheduleResult]:
        """调度：收集报价 → 过滤熔断 → 加权评分 → 仲裁 → 选择

        Args:
            registry: AgentRegistry 实例
            task_signature: 任务描述
            reputation: ReputationTracker 实例 (可选)
            arbiter: MultiAgentArbiter 实例 (可选)
            agents: 指定参与竞标的 Agent (None=全部)
            zone_map: Agent→Zone 映射

        Returns:
            ScheduleResult 或 None (无可用 Agent)
        """
        # 1. 收集报价
        bids = collect_bids(registry, task_signature, agents, zone_map)
        if not bids:
            return None

        # 2. 过滤熔断态的 Agent
        active_bids = [
            b for b in bids
            if self._meltdown.get(b.agent_name, 0) < MELTDOWN_THRESHOLD
        ]
        if not active_bids:
            return None

        # 3. 加权评分
        scored: List[Tuple[float, AgentBid]] = []
        for b in active_bids:
            rep_score = reputation.get_score(b.agent_name) if reputation else 0.5
            final = b.score(rep_score)
            scored.append((final, b))

        # 4. 排序
        scored.sort(key=lambda x: -x[0])
        best_score, best_bid = scored[0]

        reason = f"报价={best_bid.confidence}, 信誉={reputation.get_score(best_bid.agent_name) if reputation else 0.5:.2f}"

        # 5. 如果有仲裁器且有多个候选，仲裁决定
        if arbiter and len(scored) > 1:
            from multi_agent_arbiter import AgentProposal
            proposals = [
                AgentProposal(
                    agent_name=b.agent_name,
                    strategy=b.agent_name,
                    confidence=s,
                    task_type=task_signature,
                )
                for s, b in scored[:3]
            ]
            arb_result = arbiter.arbitrate(proposals)
            if arb_result.winner:
                for s, b in scored:
                    if b.agent_name == arb_result.winner:
                        best_bid = b
                        best_score = s
                        reason += f", 仲裁胜出(加权{arb_result.confidence})"
                        break

        # v3.3: 自适应 ε 校准（数据≥50条后自动调优）
        try:
            from adaptive_epsilon import apply_epsilon
            apply_epsilon(self)
        except Exception:
            pass

        # v3.1: ε-greedy 探索-利用
        self._exploit_count += 1
        import random
        if random.random() < self._epsilon and len(scored) > 1:
            candidates = [(s, b) for s, b in scored if b.agent_name != best_bid.agent_name]
            if candidates:
                cs, cb = random.choice(candidates)
                self._explore_count += 1
                return ScheduleResult(
                    agent_name=cb.agent_name,
                    explore=True,
                    task=task_signature,
                    bid_score=cb.confidence,
                    reputation=reputation.get_score(cb.agent_name) if reputation else 0.5,
                    final_score=round(cs, 3),
                    reason=reason + f" | ε={self._epsilon}探索",
                )

        return ScheduleResult(
            agent_name=best_bid.agent_name,
            task=task_signature,
            bid_score=best_bid.confidence,
            reputation=reputation.get_score(best_bid.agent_name) if reputation else 0.5,
            final_score=round(best_score, 3),
            reason=reason,
        )

    def _save(self) -> None:
        ...
    
    def record_success(self, agent_name: str, explore: bool = False) -> None:
        """记录成功，重置熔断计数"""
        if explore:
            self._explore_success = getattr(self, '_explore_success', 0) + 1
            self._explore_total = getattr(self, '_explore_total', 0) + 1
        else:
            self._exploit_success = getattr(self, '_exploit_success', 0) + 1
            self._exploit_total = getattr(self, '_exploit_total', 0) + 1
        if agent_name in self._meltdown:
            del self._meltdown[agent_name]
        self._save_meltdown()

    def record_failure(self, agent_name: str) -> None:
        """记录失败，递增熔断计数"""
        self._meltdown[agent_name] = self._meltdown.get(agent_name, 0) + 1
        self._save_meltdown()

    def is_melted(self, agent_name: str) -> bool:
        """检查是否已熔断"""
        return self._meltdown.get(agent_name, 0) >= MELTDOWN_THRESHOLD

    def reset_breaker(self, agent_name: str) -> None:
        """手动重置熔断"""
        if agent_name in self._meltdown:
            del self._meltdown[agent_name]
        self._save_meltdown()

    def get_meltdown_stats(self) -> dict:
        return {
            "threshold": MELTDOWN_THRESHOLD,
            "melted_agents": [k for k, v in self._meltdown.items() if v >= MELTDOWN_THRESHOLD],
            "all_strikes": dict(self._meltdown),
            "epsilon": self._epsilon,
            "explore_count": self._explore_count,
            "exploit_count": self._exploit_count,
            "explore_rate": round(self._explore_count / max(self._explore_count + self._exploit_count, 1), 3),
            "explore_total": getattr(self, '_explore_total', 0),
            "exploit_total": getattr(self, '_exploit_total', 0),
            "explore_success": getattr(self, '_explore_success', 0),
            "exploit_success": getattr(self, '_exploit_success', 0),
            "explore_success_rate": round(getattr(self, '_explore_success', 0) / max(getattr(self, '_explore_total', 0), 1), 3),
            "exploit_success_rate": round(getattr(self, '_exploit_success', 0) / max(getattr(self, '_exploit_total', 0), 1), 3),
        }

    def _load_meltdown(self) -> None:
        path = _get_meltdown_path()
        if path.exists():
            with open(path, 'r') as f:
                self._meltdown = json.load(f)

    def _save_meltdown(self) -> None:
        path = _get_meltdown_path()
        with open(path, 'w') as f:
            json.dump(self._meltdown, f, indent=2)


_default_scheduler: Optional[MarketScheduler] = None


def get_scheduler() -> MarketScheduler:
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = MarketScheduler()
    return _default_scheduler


def schedule_task(registry, task: str, **kwargs) -> Optional[ScheduleResult]:
    return get_scheduler().schedule(registry, task, **kwargs)
