# -*- coding: utf-8 -*-
"""
adaptive_governance.py — v3.5 自适应治理

功能:
  - 门控阈值自适应：根据历史拒答准确率自动调优
  - 仲裁权重自适应：根据仲裁结果的长期表现自动调整
  - 角色边界自适应：根据 Trace 数据自动扩缩权限范围
  - 治理健康度监控
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_ADAPTIVE_FILE = None


def _get_path() -> Path:
    global _ADAPTIVE_FILE
    if _ADAPTIVE_FILE is None:
        _ADAPTIVE_FILE = Path(__file__).resolve().parent / "adaptive_state.json"
    return _ADAPTIVE_FILE


class StrategySelector:
    """多策略调度器 — 3种算法竞争，运行时选最优"""

    def __init__(self):
        self._strategies = {}
        self._history = {}

    def register(self, name: str, fn) -> None:
        self._strategies[name] = fn
        self._history.setdefault(name, [])

    def select(self) -> str:
        if not self._history or all(len(h) < 3 for h in self._history.values()):
            return "pid"
        scores = {n: sum(h[-3:]) / min(len(h[-3:]), 3) for n, h in self._history.items()}
        return max(scores, key=scores.get)

    def record(self, name: str, accuracy: float) -> None:
        self._history.setdefault(name, []).append(accuracy)
        if len(self._history[name]) > 20:
            self._history[name] = self._history[name][-20:]

    def get_stats(self) -> dict:
        return {
            "strategies": list(self._strategies.keys()),
            "scores": {n: round(sum(h[-5:]) / min(len(h[-5:]), 1), 3) for n, h in self._history.items()},
        }


class AdaptiveGovernance:
    """自适应治理引擎"""

    def __init__(self):
        self._conf_threshold: float = 0.5      # 门控置信度阈值
        self._arb_weights: Dict[str, float] = {}  # Agent→仲裁权重
        self._history: List[dict] = []
        self._selector = StrategySelector()
        self._selector.register("pid", lambda x: x)
        self._selector.register("ema", lambda x: x)
        self._selector.register("window", lambda x: x)
        self._load()

    def adapt_gate_threshold(self, recent_decisions: List[dict],
                               strategy: Optional[str] = None) -> float:
        """多策略门控阈值调优 (pid/ema/window)"""
        if not recent_decisions:
            return self._conf_threshold
        correct = sum(1 for d in recent_decisions if d.get("correct", False))
        total = len(recent_decisions)
        accuracy = correct / max(total, 1)
        chosen = strategy or self._selector.select()
        old_val = self._conf_threshold
        if chosen == "pid":
            if accuracy < 0.7:
                self._conf_threshold = max(0.2, old_val - 0.05)
            elif accuracy > 0.9:
                self._conf_threshold = min(0.8, old_val + 0.05)
        elif chosen == "ema":
            alpha = 0.3
            target = 0.5 + (accuracy - 0.5) * 0.3
            self._conf_threshold = alpha * target + (1 - alpha) * old_val
        elif chosen == "window":
            window_acc = sum(1 for d in recent_decisions[-5:] if d.get("correct", False)) / max(min(len(recent_decisions), 5), 1)
            if window_acc < 0.5:
                self._conf_threshold = max(0.2, old_val - 0.1)
            elif window_acc > 0.85:
                self._conf_threshold = min(0.8, old_val + 0.03)
        self._selector.record(chosen, accuracy)
        self._save()
        return round(self._conf_threshold, 2)

    def adapt_hybrid(self, recent_decisions: List[dict]) -> float:
        """混合策略：pid/ema/window 加权融合

        权重 = 各策略最近5次误差的反比，
        环境快速切换时自动平滑过渡。
        """
        if not recent_decisions:
            return self._conf_threshold
        correct = sum(1 for d in recent_decisions if d.get("correct", False))
        total = len(recent_decisions)
        accuracy = correct / max(total, 1)
        old_val = self._conf_threshold

        # 1) 各策略独立计算输出
        def _pid(old: float, acc: float) -> float:
            if acc < 0.7:
                return max(0.2, old - 0.05)
            elif acc > 0.9:
                return min(0.8, old + 0.05)
            return old
        def _ema(old: float, acc: float) -> float:
            alpha = 0.3
            target = 0.5 + (acc - 0.5) * 0.3
            return alpha * target + (1 - alpha) * old
        def _window(old: float, acc: float) -> float:
            window_acc = sum(1 for d in recent_decisions[-5:] if d.get("correct", False)) / max(min(len(recent_decisions), 5), 1)
            if window_acc < 0.5:
                return max(0.2, old - 0.1)
            elif window_acc > 0.85:
                return min(0.8, old + 0.03)
            return old

        outputs = {"pid": _pid(old_val, accuracy),
                   "ema": _ema(old_val, accuracy),
                   "window": _window(old_val, accuracy)}

        # 2) 权重 = 最近误差反比（数据不足时均匀）
        weights = {}
        for name in ["pid", "ema", "window"]:
            history = self._selector._history.get(name, [])
            if len(history) >= 3:
                error = 1.0 - sum(history[-5:]) / max(len(history[-5:]), 1)
                weights[name] = max(0.01, 1.0 - error)
            else:
                weights[name] = 1.0

        total_w = sum(weights.values())
        normalized = {n: w / total_w for n, w in weights.items()}

        # 3) 加权融合
        hybrid_val = sum(normalized[n] * outputs[n] for n in normalized)
        self._conf_threshold = round(hybrid_val, 4)
        self._save()
        return self._conf_threshold

    def adapt_arb_weights(self, outcomes: List[dict]) -> Dict[str, float]:
        """根据仲裁结果调整 Agent 权重"""
        for o in outcomes:
            agent = o.get("agent", "")
            correct = o.get("correct", False)
            current = self._arb_weights.get(agent, 1.0)
            if correct:
                self._arb_weights[agent] = min(2.0, current + 0.1)
            else:
                self._arb_weights[agent] = max(0.1, current - 0.2)
        self._save()
        return dict(self._arb_weights)

    def adapt_role_boundary(self, trace_data: dict) -> List[str]:
        """根据 Trace 数据建议权限扩缩"""
        suggestions = []
        by_agent = trace_data.get("by_agent", {})
        for agent, count in by_agent.items():
            if count > 50:
                suggestions.append(f"{agent}: 频繁调用 → 考虑扩权")
            elif count < 3:
                suggestions.append(f"{agent}: 极少调用 → 考虑缩权")
        return suggestions

    def get_health(self) -> dict:
        return {
            "gate_threshold": round(self._conf_threshold, 2),
            "arb_weights": dict(self._arb_weights),
            "history_count": len(self._history),
        }

    def _load(self) -> None:
        path = _get_path()
        if path.exists():
            with open(path, "r") as f:
                data = json.load(f)
            self._conf_threshold = data.get("conf_threshold", 0.5)
            self._arb_weights = data.get("arb_weights", {})

    def _save(self) -> None:
        path = _get_path()
        with open(path, "w") as f:
            json.dump({
                "conf_threshold": self._conf_threshold,
                "arb_weights": self._arb_weights,
            }, f, indent=2)


_default_gov: Optional[AdaptiveGovernance] = None


def get_governance() -> AdaptiveGovernance:
    global _default_gov
    if _default_gov is None:
        _default_gov = AdaptiveGovernance()
    return _default_gov


def get_health() -> dict:
    return get_governance().get_health()
