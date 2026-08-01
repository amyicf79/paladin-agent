# -*- coding: utf-8 -*-
"""
cascade_scheduler.py — 级联调度器

功能:
  - mode(n_steps) → "hybrid" | "cascade"
  - adapt(recent) → 根据mode调用对应策略
  - 切换条件: n_steps >= 50 → cascade
"""

from __future__ import annotations
from typing import List, Optional, Tuple


# 环境→最优策略映射（基于基准数据）
_ENV_STRATEGY = {
    "stable": "window",
    "trend": "pid",
    "shock": "window",
    "dual_scale": "ema",
}


class CascadeScheduler:
    """级联调度器：hybrid → cascade 自动切换"""

    def __init__(self, switch_threshold: int = 50):
        self.switch_threshold = switch_threshold
        self._governance = None
        self._classifier = None
        self._n_calls = 0

    def _lazy_load(self):
        if self._governance is not None:
            return
        from env_classifier import EnvironmentClassifier
        from adaptive_governance import get_governance
        self._classifier = EnvironmentClassifier()
        self._governance = get_governance()

    def mode(self, n_steps: Optional[int] = None,
               recent: Optional[List[dict]] = None) -> str:
        """返回当前模式: hybrid(冷启动) / cascade(数据充足)

        cascade 条件: n_steps >= threshold AND 信号质量达标
        质量条件: 最近30步的波动率<0.4 且 |趋势斜率|>0.003
        """
        steps = n_steps if n_steps is not None else self._n_calls
        if steps < self.switch_threshold:
            return "hybrid"
        if recent is not None and self._quality_ok(recent):
            return "cascade"
        if recent is None:
            return "cascade"
        return "hybrid"

    @staticmethod
    def _quality_ok(recent: List[dict]) -> bool:
        """信号质量检查: 调用标准化 DataQualityGate"""
        try:
            from quality_gate import score
            return score(recent) > 0.5
        except ImportError:
            return True  # 无quality_gate时不阻断

    def adapt(self, recent: List[dict],
              n_steps: Optional[int] = None) -> float:
        """根据模式调优门控阈值"""
        self._lazy_load()
        self._n_calls += 1
        current_mode = self.mode(n_steps, recent)

        if current_mode == "hybrid":
            return self._governance.adapt_hybrid(recent)

        # cascade 模式: 分类 → 选策略 → 调阈值
        result = self._classifier.classify(recent)
        if len(result) == 3:
            env, conf, is_confident = result
        else:
            env, conf = result[0], result[1]
            is_confident = True
        if not is_confident:
            return self._governance.adapt_hybrid(recent)
        strategy = _ENV_STRATEGY.get(env, "pid")
        return self._governance.adapt_gate_threshold(
            recent, strategy=strategy
        )

    def get_stats(self) -> dict:
        return {
            "mode": self.mode(),
            "threshold": self.switch_threshold,
            "n_calls": self._n_calls,
        }


_default_scheduler: Optional[CascadeScheduler] = None


def get_scheduler() -> CascadeScheduler:
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = CascadeScheduler()
    return _default_scheduler


def adapt(recent: List[dict], n_steps: Optional[int] = None) -> float:
    return get_scheduler().adapt(recent, n_steps)
