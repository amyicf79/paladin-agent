# -*- coding: utf-8 -*-
"""
quality_gate.py — 数据质量评分器

3指标加权输出 0~1 质量分:
  - entropy: 分布多样性 (高熵=数据丰富)
  - coverage: 极值覆盖率 (两端覆盖=代表性强)
  - stability: 连续一致性 (低波动=稳定)
"""

from __future__ import annotations
import math
from typing import List


class DataQualityGate:
    """数据质量评分器"""

    @staticmethod
    def entropy(errors: List[float], bins: int = 4) -> float:
        """分布熵: 越高表示数据越多样化"""
        if not errors:
            return 0.0
        n = len(errors)
        if n < bins:
            return 0.0
        width = 1.0 / bins
        counts = [0] * bins
        for e in errors:
            idx = min(int(e / width), bins - 1)
            counts[idx] += 1
        probs = [c / n for c in counts if c > 0]
        return -sum(p * math.log(p) for p in probs) / math.log(bins) if probs else 0.0

    @staticmethod
    def coverage(errors: List[float]) -> float:
        """极值覆盖率: 0.0~0.2 和 0.8~1.0 区间是否都有数据"""
        if not errors:
            return 0.0
        has_low = any(e < 0.2 for e in errors)
        has_high = any(e > 0.8 for e in errors)
        return 1.0 if has_low and has_high else 0.0

    @staticmethod
    def stability(errors: List[float]) -> float:
        """稳定性: 波动率越低越稳定 (1 - 归一化std)"""
        if len(errors) < 2:
            return 0.0
        mean = sum(errors) / len(errors)
        std = (sum((e - mean) ** 2 for e in errors) / len(errors)) ** 0.5
        return max(0.0, 1.0 - std * 2)

    def score(self, errors: List[float]) -> float:
        """综合质量分 [0, 1]: 0.5+ 表示可切换 cascade"""
        if len(errors) < 5:
            return 0.0
        ent = self.entropy(errors)
        cov = self.coverage(errors)
        stab = self.stability(errors)
        # 加权: entropy 0.4, coverage 0.3, stability 0.3
        raw = ent * 0.4 + cov * 0.3 + stab * 0.3
        return round(raw, 4)


def score(recent: List[dict]) -> float:
    """便捷接口: 从带标签数据打分"""
    errors = [1.0 if d.get("correct", False) else 0.0 for d in recent]
    return DataQualityGate().score(errors)
