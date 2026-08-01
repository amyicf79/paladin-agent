# -*- coding: utf-8 -*-
"""
adaptive_epsilon.py — 自适应 ε 推荐器

逻辑:
  - 数据 < 50 条 → return None (不调整)
  - 探索成功率 > 利用率×1.2 → +0.03
  - 探索成功率 < 利用率×0.8 → -0.02
  - 其他 → ±0 (维持)
"""

from __future__ import annotations
from typing import Optional


MIN_SAMPLES = 50
ADJUST_UP = 0.03
ADJUST_DOWN = -0.02
RATIO_UP = 1.2
RATIO_DOWN = 0.8


class AdaptiveEpsilon:
    """自适应 ε 推荐器"""

    @staticmethod
    def recommend(
        explore_success_rate: float,
        exploit_success_rate: float,
        total_explore: int,
    ) -> Optional[float]:
        """返回 ε 调整量, None=数据不足不调整"""
        if total_explore < MIN_SAMPLES:
            return None

        if explore_success_rate == 0 and exploit_success_rate == 0:
            return None

        if exploit_success_rate > 0 and explore_success_rate > exploit_success_rate * RATIO_UP:
            return ADJUST_UP
        if exploit_success_rate > 0 and explore_success_rate < exploit_success_rate * RATIO_DOWN:
            return ADJUST_DOWN
        return 0.0

    @staticmethod
    def apply(scheduler) -> None:
        """从 scheduler 读取统计数据, 自动调 ε"""
        md = scheduler.get_meltdown_stats()
        exp_rate = md.get("explore_success_rate", 0)
        expl_rate = md.get("exploit_success_rate", 0)
        exp_total = md.get("explore_total", 0)

        delta = AdaptiveEpsilon.recommend(exp_rate, expl_rate, exp_total)
        if delta is not None:
            scheduler._epsilon = round(max(0.01, min(0.5, scheduler._epsilon + delta)), 3)
            return True
        return False


def apply_epsilon(scheduler) -> bool:
    return AdaptiveEpsilon.apply(scheduler)
